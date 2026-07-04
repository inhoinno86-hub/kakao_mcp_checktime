from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from checktime_mcp.mcp_adapter import PROTOCOL_VERSION  # noqa: E402
from checktime_mcp.mcp_server import create_http_server  # noqa: E402

SAFE_PREVIEW_LIMIT = 240


def http_request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    payload: dict | None = None,
    raw_data: bytes | None = None,
) -> tuple[int, dict[str, str], dict]:
    data = raw_data
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    request = Request(url, method=method, data=data, headers=headers or {})
    try:
        with urlopen(request) as response:
            body = response.read().decode("utf-8")
            return response.status, dict(response.headers.items()), json.loads(body) if body else {}
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, dict(exc.headers.items()), json.loads(body) if body else {}


def mcp_headers(
    *,
    content_type: str = "application/json",
    accept: str = "application/json, text/event-stream",
    protocol_version: str | None = PROTOCOL_VERSION,
    origin: str | None = None,
    authorization: str | None = None,
) -> dict[str, str]:
    headers = {
        "Content-Type": content_type,
        "Accept": accept,
    }
    if protocol_version is not None:
        headers["MCP-Protocol-Version"] = protocol_version
    if origin:
        headers["Origin"] = origin
    if authorization:
        headers["Authorization"] = authorization
    return headers


def health_url_from_base(base_url: str) -> str:
    parts = urlsplit(base_url)
    return urlunsplit((parts.scheme, parts.netloc, "/health", "", ""))


def safe_preview(payload: object) -> str:
    text = json.dumps(payload, ensure_ascii=False)
    text = text.replace("\n", " ")
    if len(text) > SAFE_PREVIEW_LIMIT:
        text = text[:SAFE_PREVIEW_LIMIT] + "..."
    return text


def assert_pass(condition: bool, label: str, detail: str = "", payload: object | None = None) -> None:
    if condition:
        print(f"PASS {label}{detail}")
        return
    suffix = f" :: {safe_preview(payload)}" if payload is not None else ""
    print(f"FAIL {label}{detail}{suffix}")
    raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test MCP HTTP endpoint hardening")
    parser.add_argument("--base-url", help="Existing MCP endpoint URL. If omitted, start an in-process server.")
    parser.add_argument("--bearer-token", help="Bearer token for positive auth smoke. Overrides env when set.")
    parser.add_argument("--origin", help="Origin header for positive smoke. Defaults to first allowlisted origin.")
    parser.add_argument("--strict", action="store_true", help="Skip legacy compatibility-only checks.")
    parser.add_argument(
        "--skip-origin-negative",
        action="store_true",
        help="Skip negative Origin mismatch check even when allowlist is configured.",
    )
    parser.add_argument(
        "--skip-auth-negative",
        action="store_true",
        help="Skip negative missing-token check even when bearer auth is enabled.",
    )
    args = parser.parse_args()

    auth_mode = os.environ.get("CHECKTIME_AUTH_MODE", "off").strip().lower() or "off"
    bearer_token = args.bearer_token or os.environ.get("CHECKTIME_BEARER_TOKEN", "local-test-token")
    bearer_expected = auth_mode == "bearer" or args.bearer_token is not None
    allowed_origins = [
        item.strip()
        for item in os.environ.get("CHECKTIME_ALLOWED_ORIGINS", "").split(",")
        if item.strip()
    ]
    success_origin = args.origin or (allowed_origins[0] if allowed_origins else None)
    auth_header = f"Bearer {bearer_token}" if bearer_expected else None

    server = None
    thread = None
    if args.base_url:
        url = args.base_url
    else:
        server = create_http_server(port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        url = f"http://{host}:{port}/mcp"

    try:
        status, _, payload = http_request(
            url,
            method="POST",
            headers=mcp_headers(origin=success_origin, authorization=auth_header),
            payload={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        assert_pass(
            status == 200 and payload["result"]["protocolVersion"] == PROTOCOL_VERSION,
            "POST /mcp initialize",
            payload={"status": status, "body": payload},
        )

        status, _, payload = http_request(
            url,
            method="POST",
            headers=mcp_headers(origin=success_origin, authorization=auth_header),
            payload={"jsonrpc": "2.0", "id": 2, "method": "ping", "params": {}},
        )
        assert_pass(status == 200 and payload["result"] == {}, "POST /mcp ping", payload={"status": status, "body": payload})

        status, _, payload = http_request(
            url,
            method="POST",
            headers=mcp_headers(origin=success_origin, authorization=auth_header),
            payload={"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}},
        )
        assert_pass(
            status == 200 and len(payload["result"]["tools"]) == 6,
            "POST /mcp tools/list",
            payload={"status": status, "body": payload},
        )

        status, _, payload = http_request(
            url,
            method="POST",
            headers=mcp_headers(origin=success_origin, authorization=auth_header),
            payload={
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "generate_required_documents",
                    "arguments": {
                        "transaction_type": "lease_monthly",
                        "user_role": "tenant",
                        "stage": "before_move_in",
                    },
                },
            },
        )
        assert_pass(
            payload["result"]["structuredContent"]["ok"] is True,
            "POST /mcp tools/call normal",
            payload={"status": status, "body": payload},
        )

        status, _, payload = http_request(
            url,
            method="POST",
            headers=mcp_headers(origin=success_origin, authorization=auth_header),
            payload={
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "flag_expert_review_points",
                    "arguments": {
                        "transaction_type": "home_purchase",
                        "user_role": "buyer",
                        "context": "계약서 원문 업로드 가능 여부",
                    },
                },
            },
        )
        assert_pass(
            payload["result"]["structuredContent"]["error"]["code"] == "sensitive_input_detected",
            "POST /mcp tools/call sensitive input denied",
            payload={"status": status, "body": payload},
        )

        status, _, payload = http_request(
            url,
            method="POST",
            headers=mcp_headers(origin=success_origin, authorization=auth_header),
            payload={
                "jsonrpc": "2.0",
                "id": 6,
                "method": "tools/call",
                "params": {
                    "name": "generate_pre_contract_checklist",
                    "arguments": {
                        "transaction_type": "lease_jeonse",
                        "user_role": "tenant",
                        "contract_date": "2026/07/12",
                    },
                },
            },
        )
        assert_pass(
            payload["result"]["structuredContent"]["error"]["code"] == "invalid_date_format",
            "POST /mcp tools/call invalid date denied",
            payload={"status": status, "body": payload},
        )

        status, _, payload = http_request(
            url,
            method="POST",
            headers=mcp_headers(origin=success_origin, authorization=auth_header),
            raw_data=b"{bad json",
        )
        assert_pass(
            status == 400 and payload["error"]["data"]["error"]["code"] == "parse_error",
            "POST /mcp invalid JSON",
            payload={"status": status, "body": payload},
        )

        status, _, payload = http_request(
            url,
            method="POST",
            headers=mcp_headers(origin=success_origin, authorization=auth_header),
            payload={"jsonrpc": "2.0", "id": 7, "method": "unknown/method", "params": {}},
        )
        assert_pass(
            status == 200 and payload["error"]["code"] == -32601,
            "POST /mcp unknown method",
            payload={"status": status, "body": payload},
        )

        status, _, payload = http_request(
            url,
            method="POST",
            headers=mcp_headers(origin=success_origin, authorization=auth_header),
            payload={"jsonrpc": "2.0", "method": "ping", "params": {}},
        )
        assert_pass(
            status == 202 and payload == {},
            "POST /mcp missing id notification policy",
            payload={"status": status, "body": payload},
        )

        status, _, payload = http_request(
            url,
            method="POST",
            headers=mcp_headers(
                content_type="text/plain",
                origin=success_origin,
                authorization=auth_header,
            ),
            raw_data=b"{}",
        )
        assert_pass(
            status == 415 and payload["error"]["data"]["error"]["code"] == "unsupported_content_type",
            "POST /mcp unsupported Content-Type",
            payload={"status": status, "body": payload},
        )

        status, _, payload = http_request(
            url,
            method="POST",
            headers=mcp_headers(
                accept="application/json",
                origin=success_origin,
                authorization=auth_header,
            ),
            payload={"jsonrpc": "2.0", "id": 8, "method": "ping", "params": {}},
        )
        assert_pass(
            status == 406 and payload["error"]["data"]["error"]["code"] == "unsupported_accept_header",
            "POST /mcp unsupported Accept",
            payload={"status": status, "body": payload},
        )

        status, _, payload = http_request(
            url,
            method="POST",
            headers=mcp_headers(
                protocol_version="2024-11-05",
                origin=success_origin,
                authorization=auth_header,
            ),
            payload={"jsonrpc": "2.0", "id": 9, "method": "ping", "params": {}},
        )
        assert_pass(
            status == 400 and payload["error"]["data"]["error"]["code"] == "unsupported_protocol_version",
            "POST /mcp unsupported MCP-Protocol-Version",
            payload={"status": status, "body": payload},
        )

        if args.strict:
            print("SKIP POST /mcp missing MCP-Protocol-Version legacy policy (--strict)")
        else:
            status, _, payload = http_request(
                url,
                method="POST",
                headers=mcp_headers(
                    protocol_version=None,
                    origin=success_origin,
                    authorization=auth_header,
                ),
                payload={"jsonrpc": "2.0", "id": 10, "method": "ping", "params": {}},
            )
            assert_pass(
                status == 200 and payload["result"] == {},
                "POST /mcp missing MCP-Protocol-Version legacy policy",
                payload={"status": status, "body": payload},
            )

        status, headers, payload = http_request(
            url,
            method="GET",
            headers={"Accept": "text/event-stream", **({"Origin": success_origin} if success_origin else {})},
        )
        assert_pass(
            status == 405 and headers.get("Allow") == "POST, GET, OPTIONS" and payload["error"]["code"] == "sse_not_implemented",
            "GET /mcp SSE unsupported policy",
            payload={"status": status, "body": payload, "headers": {"Allow": headers.get("Allow")}},
        )

        status, headers, _ = http_request(
            url,
            method="OPTIONS",
            headers={"Origin": success_origin} if success_origin else {},
        )
        assert_pass(
            status == 204
            and headers.get("Access-Control-Allow-Methods") == "POST, GET, OPTIONS"
            and headers.get("Access-Control-Allow-Headers") == "Content-Type, Accept, Authorization, MCP-Protocol-Version",
            "OPTIONS /mcp",
            payload={
                "status": status,
                "headers": {
                    "Access-Control-Allow-Methods": headers.get("Access-Control-Allow-Methods"),
                    "Access-Control-Allow-Headers": headers.get("Access-Control-Allow-Headers"),
                },
            },
        )

        if allowed_origins and not args.skip_origin_negative:
            status, _, payload = http_request(
                url,
                method="POST",
                headers=mcp_headers(origin="http://evil.example", authorization=auth_header),
                payload={"jsonrpc": "2.0", "id": 11, "method": "ping", "params": {}},
            )
            assert_pass(
                status == 403 and payload["error"]["data"]["error"]["code"] == "forbidden_origin",
                "Origin mismatch 403",
                payload={"status": status, "body": payload},
            )
        else:
            reason = "--skip-origin-negative" if args.skip_origin_negative else "CHECKTIME_ALLOWED_ORIGINS not set"
            print(f"SKIP Origin mismatch 403 ({reason})")

        if bearer_expected and not args.skip_auth_negative:
            status, _, payload = http_request(
                url,
                method="POST",
                headers=mcp_headers(origin=success_origin),
                payload={"jsonrpc": "2.0", "id": 12, "method": "ping", "params": {}},
            )
            assert_pass(
                status == 401 and payload["error"]["data"]["error"]["code"] == "unauthorized",
                "Bearer auth missing token",
                payload={"status": status, "body": payload},
            )

        elif bearer_expected:
            print("SKIP Bearer auth missing token (--skip-auth-negative)")
        else:
            print("SKIP Bearer auth smoke (no bearer token requested)")

        if bearer_expected:
            status, _, payload = http_request(
                url,
                method="POST",
                headers=mcp_headers(origin=success_origin, authorization=auth_header),
                payload={"jsonrpc": "2.0", "id": 13, "method": "ping", "params": {}},
            )
            assert_pass(
                status == 200 and payload["result"] == {},
                "Bearer auth token match",
                payload={"status": status, "body": payload},
            )

        status, _, payload = http_request(
            url,
            method="POST",
            headers=mcp_headers(origin=success_origin, authorization=auth_header),
            payload={"jsonrpc": "2.0", "id": 14, "method": "ping", "params": {"pad": "x" * 1100000}},
        )
        assert_pass(
            status == 413 and payload["error"]["data"]["error"]["code"] == "payload_too_large",
            "payload too large",
            payload={"status": status, "body": payload},
        )

        status, _, payload = http_request(health_url_from_base(url), method="GET")
        assert_pass(
            status == 200
            and payload["transport_status"]["streamable_http"] == "candidate"
            and payload["playmcp_registration_status"] == "manual_step_required",
            "health/readiness",
            payload={"status": status, "body": payload},
        )
        return 0
    finally:
        if server:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
