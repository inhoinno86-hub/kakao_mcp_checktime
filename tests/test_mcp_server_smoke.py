from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from checktime_mcp.health import get_health_status
from checktime_mcp.mcp_adapter import PROTOCOL_VERSION
from checktime_mcp.mcp_server import create_http_server, default_http_port
from checktime_mcp.runtime_config import RuntimeConfig


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


def mcp_headers(**extra: str) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": PROTOCOL_VERSION,
    }
    headers.update(extra)
    return headers


def header_value(headers: dict[str, str], name: str) -> str | None:
    target = name.lower()
    for key, value in headers.items():
        if key.lower() == target:
            return value
    return None


def run_server(runtime_config: RuntimeConfig | None = None) -> tuple[object, threading.Thread, str]:
    server = create_http_server(port=0, runtime_config=runtime_config)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return server, thread, f"http://{host}:{port}"


def stop_server(server: object, thread: threading.Thread) -> None:
    server.shutdown()
    thread.join(timeout=2)
    server.server_close()


def test_health_fails_when_required_data_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("CHECKTIME_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("CHECKTIME_AUTH_MODE", raising=False)
    (tmp_path / "disclaimers.json").write_text("{}", encoding="utf-8")
    payload = get_health_status(tmp_path)
    assert payload["ok"] is False
    assert payload["data_status"] == "missing_files"
    assert payload["transport_status"]["get_mcp_behavior"] == "405_when_sse_not_supported"
    assert payload["security_status"]["auth_mode"] == "off"
    assert "timeline_rules.json" in payload["missing_data_files"]


def test_default_http_port_reads_port_env(monkeypatch) -> None:
    monkeypatch.setenv("PORT", "8080")
    assert default_http_port() == 8080
    monkeypatch.setenv("PORT", "bad-value")
    assert default_http_port() == 8000


def test_http_server_supports_initialize_ping_tools_list_and_call() -> None:
    server, thread, base_url = run_server()
    try:
        status, headers, payload = http_request(
            f"{base_url}/mcp",
            method="POST",
            headers=mcp_headers(),
            payload={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        assert status == 200
        assert headers["MCP-Protocol-Version"] == PROTOCOL_VERSION
        assert payload["result"]["protocolVersion"] == PROTOCOL_VERSION

        status, _, payload = http_request(
            f"{base_url}/mcp",
            method="POST",
            headers=mcp_headers(),
            payload={"jsonrpc": "2.0", "id": 2, "method": "ping", "params": {}},
        )
        assert status == 200
        assert payload["result"] == {}

        status, _, payload = http_request(
            f"{base_url}/mcp",
            method="POST",
            headers=mcp_headers(),
            payload={"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}},
        )
        assert status == 200
        assert len(payload["result"]["tools"]) == 6

        status, _, payload = http_request(
            f"{base_url}/mcp",
            method="POST",
            headers=mcp_headers(),
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
        assert status == 200
        assert payload["result"]["structuredContent"]["ok"] is True
        assert "disclaimer" in payload["result"]["structuredContent"]
    finally:
        stop_server(server, thread)


def test_http_server_rejects_invalid_json_and_unknown_method() -> None:
    server, thread, base_url = run_server()
    try:
        status, _, payload = http_request(
            f"{base_url}/mcp",
            method="POST",
            headers=mcp_headers(),
            raw_data=b"{bad json",
        )
        assert status == 400
        assert payload["error"]["code"] == -32700
        assert payload["error"]["data"]["error"]["code"] == "parse_error"

        status, _, payload = http_request(
            f"{base_url}/mcp",
            method="POST",
            headers=mcp_headers(),
            payload={"jsonrpc": "2.0", "id": 5, "method": "unknown/method", "params": {}},
        )
        assert status == 200
        assert payload["error"]["code"] == -32601

        status, _, payload = http_request(
            f"{base_url}/mcp",
            method="POST",
            headers=mcp_headers(),
            payload={"jsonrpc": "2.0", "method": "ping", "params": {}},
        )
        assert status == 202
        assert payload == {}
    finally:
        stop_server(server, thread)


def test_http_server_rejects_unsupported_headers() -> None:
    server, thread, base_url = run_server()
    try:
        status, _, payload = http_request(
            f"{base_url}/mcp",
            method="POST",
            headers={
                "Content-Type": "text/plain",
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": PROTOCOL_VERSION,
            },
            raw_data=b"{}",
        )
        assert status == 415
        assert payload["error"]["data"]["error"]["code"] == "unsupported_content_type"

        status, _, payload = http_request(
            f"{base_url}/mcp",
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "MCP-Protocol-Version": PROTOCOL_VERSION,
            },
            payload={"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}},
        )
        assert status == 406
        assert payload["error"]["data"]["error"]["code"] == "unsupported_accept_header"

        status, _, payload = http_request(
            f"{base_url}/mcp",
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": "2024-11-05",
            },
            payload={"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}},
        )
        assert status == 400
        assert payload["error"]["data"]["error"]["code"] == "unsupported_protocol_version"
    finally:
        stop_server(server, thread)


def test_http_server_supports_legacy_missing_protocol_header_policy() -> None:
    server, thread, base_url = run_server()
    try:
        status, _, payload = http_request(
            f"{base_url}/mcp",
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            payload={"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}},
        )
        assert status == 200
        assert payload["result"] == {}
    finally:
        stop_server(server, thread)


def test_http_server_handles_get_options_origin_auth_and_payload_limits(monkeypatch) -> None:
    runtime_config = RuntimeConfig(
        auth_mode="bearer",
        bearer_token="local-test-token",
        allowed_origins=("http://localhost:3000",),
        request_timeout_seconds=1,
        max_body_bytes=64,
    )
    server, thread, base_url = run_server(runtime_config)
    try:
        status, _, payload = http_request(
            f"{base_url}/mcp",
            method="GET",
            headers={"Accept": "application/json", "Origin": "http://localhost:3000"},
        )
        assert status == 406
        assert payload["ok"] is False
        assert payload["error"]["code"] == "unsupported_accept_header"
        assert "message" in payload["error"]
        assert "disclaimer" in payload
        assert "traceback" not in json.dumps(payload, ensure_ascii=False).lower()

        status, headers, payload = http_request(
            f"{base_url}/mcp",
            method="GET",
            headers={"Accept": "text/event-stream", "Origin": "http://localhost:3000"},
        )
        assert status == 405
        assert header_value(headers, "Allow") == "POST, GET, OPTIONS"
        assert payload["ok"] is False
        assert payload["error"]["code"] == "sse_not_implemented"
        assert "message" in payload["error"]
        assert "disclaimer" in payload
        assert "traceback" not in json.dumps(payload, ensure_ascii=False).lower()

        status, headers, payload = http_request(
            f"{base_url}/mcp",
            method="OPTIONS",
            headers={"Origin": "http://localhost:3000"},
        )
        assert status == 204
        assert header_value(headers, "Access-Control-Allow-Methods") == "POST, GET, OPTIONS"
        assert header_value(headers, "Access-Control-Allow-Headers") == "Content-Type, Accept, Authorization, MCP-Protocol-Version"

        status, _, payload = http_request(
            f"{base_url}/mcp",
            method="POST",
            headers=mcp_headers(Origin="http://evil.example"),
            payload={"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}},
        )
        assert status == 403
        assert payload["error"]["data"]["error"]["code"] == "forbidden_origin"

        status, _, payload = http_request(
            f"{base_url}/mcp",
            method="POST",
            headers=mcp_headers(Origin="http://localhost:3000"),
            payload={"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}},
        )
        assert status == 401
        assert payload["error"]["data"]["error"]["code"] == "unauthorized"

        status, _, payload = http_request(
            f"{base_url}/mcp",
            method="POST",
            headers=mcp_headers(
                Origin="http://localhost:3000",
                Authorization="Bearer local-test-token",
            ),
            payload={"jsonrpc": "2.0", "id": 2, "method": "ping", "params": {}},
        )
        assert status == 200
        assert payload["result"] == {}

        oversized_payload = {"jsonrpc": "2.0", "id": 3, "method": "ping", "params": {"pad": "x" * 200}}
        status, _, payload = http_request(
            f"{base_url}/mcp",
            method="POST",
            headers=mcp_headers(
                Origin="http://localhost:3000",
                Authorization="Bearer local-test-token",
            ),
            payload=oversized_payload,
        )
        assert status == 413
        assert payload["error"]["data"]["error"]["code"] == "payload_too_large"
    finally:
        stop_server(server, thread)


def test_http_server_returns_timeout_response(monkeypatch) -> None:
    def slow_handler(message: dict) -> dict:
        time.sleep(2)
        return {"jsonrpc": "2.0", "id": message["id"], "result": {}}

    monkeypatch.setattr("checktime_mcp.mcp_server.handle_jsonrpc_message", slow_handler)
    runtime_config = RuntimeConfig(
        auth_mode="off",
        bearer_token=None,
        allowed_origins=(),
        request_timeout_seconds=1,
        max_body_bytes=1024,
    )
    server, thread, base_url = run_server(runtime_config)
    try:
        status, _, payload = http_request(
            f"{base_url}/mcp",
            method="POST",
            headers=mcp_headers(),
            payload={"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}},
        )
        assert status == 408
        assert payload["error"]["data"]["error"]["code"] == "request_timeout"
    finally:
        stop_server(server, thread)
