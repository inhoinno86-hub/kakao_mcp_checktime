from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import socket
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .health import get_health_status
from .mcp_adapter import (
    JSONRPC_INTERNAL_ERROR,
    JSONRPC_INVALID_REQUEST,
    JSONRPC_PARSE_ERROR,
    PROTOCOL_VERSION,
    SUPPORTED_PROTOCOL_VERSIONS,
    handle_jsonrpc_message,
    jsonrpc_error_response,
)
from .response_policy import error_response
from .runtime_config import LEGACY_PROTOCOL_VERSION, RuntimeConfig, is_origin_allowed, parse_positive_int


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_PATH = "/mcp"
ALLOW_METHODS = "POST, GET, OPTIONS"
ALLOW_HEADERS = "Content-Type, Accept, Authorization, MCP-Protocol-Version"
REQUEST_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=4)


class MCPHTTPRequestHandler(BaseHTTPRequestHandler):
    server_version = "ChecktimeMCP/0.1"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            payload = get_health_status()
            self._send_json(HTTPStatus.OK if payload["ok"] else HTTPStatus.SERVICE_UNAVAILABLE, payload)
            return

        if self.path == self.server.mcp_path:
            if not self._check_origin():
                return
            if not self._accepts(self.headers.get("Accept"), {"text/event-stream"}):
                self._send_plain_error(
                    HTTPStatus.NOT_ACCEPTABLE,
                    "unsupported_accept_header",
                    "GET /mcp 는 Accept: text/event-stream 이 필요합니다.",
                )
                return
            self._send_plain_error(
                HTTPStatus.METHOD_NOT_ALLOWED,
                "sse_not_implemented",
                "SSE stream not implemented",
                extra_headers={"Allow": ALLOW_METHODS},
            )
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != self.server.mcp_path:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})
            return

        if not self._check_origin():
            return
        if not self._check_auth():
            return
        if not self._check_protocol_version():
            return
        if not self._check_accept_header():
            return
        if not self._check_content_type():
            return

        raw_body = self._read_request_body()
        if raw_body is None:
            return

        try:
            message = json.loads(raw_body) if raw_body else {}
        except json.JSONDecodeError:
            self._send_jsonrpc_error(
                HTTPStatus.BAD_REQUEST,
                None,
                JSONRPC_PARSE_ERROR,
                "Parse error",
                "parse_error",
            )
            return

        try:
            future = REQUEST_EXECUTOR.submit(handle_jsonrpc_message, message)
            response = future.result(timeout=self.server.runtime_config.request_timeout_seconds)
        except concurrent.futures.TimeoutError:
            self._send_jsonrpc_error(
                HTTPStatus.REQUEST_TIMEOUT,
                message.get("id") if isinstance(message, dict) else None,
                JSONRPC_INTERNAL_ERROR,
                "Request timeout",
                "request_timeout",
            )
            return
        except Exception:
            self._send_jsonrpc_error(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                message.get("id") if isinstance(message, dict) else None,
                JSONRPC_INTERNAL_ERROR,
                "Internal server error",
                "server_error",
            )
            return

        if response is None:
            self.send_response(HTTPStatus.ACCEPTED)
            self._send_common_headers()
            self.end_headers()
            return

        self._send_json(HTTPStatus.OK, response, content_type="application/json")

    def do_OPTIONS(self) -> None:  # noqa: N802
        if self.path != self.server.mcp_path:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})
            return
        if not self._check_origin(preflight=True):
            return
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_common_headers()
        self.send_header("Allow", ALLOW_METHODS)
        self.send_header("Access-Control-Allow-Methods", ALLOW_METHODS)
        self.send_header("Access-Control-Allow-Headers", ALLOW_HEADERS)
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any], content_type: str = "application/json") -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._send_common_headers()
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_common_headers(self) -> None:
        self.send_header("MCP-Protocol-Version", PROTOCOL_VERSION)
        origin = self.headers.get("Origin")
        if origin and is_origin_allowed(origin, self.server.runtime_config.allowed_origins):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    def _send_plain_error(
        self,
        status: HTTPStatus,
        code: str,
        message: str,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        payload = error_response(code, message)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._send_common_headers()
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_jsonrpc_error(
        self,
        status: HTTPStatus,
        request_id: str | int | None,
        jsonrpc_code: int,
        message: str,
        error_code: str,
    ) -> None:
        payload = jsonrpc_error_response(
            request_id,
            jsonrpc_code,
            message,
            data=error_response(error_code, message),
        )
        self._send_json(status, payload)

    def _check_origin(self, preflight: bool = False) -> bool:
        origin = self.headers.get("Origin")
        if not origin:
            return True
        if is_origin_allowed(origin, self.server.runtime_config.allowed_origins):
            return True
        if preflight:
            self._send_plain_error(HTTPStatus.FORBIDDEN, "forbidden_origin", "Origin is not allowed.")
            return False
        self._send_jsonrpc_error(
            HTTPStatus.FORBIDDEN,
            None,
            JSONRPC_INVALID_REQUEST,
            "Origin is not allowed.",
            "forbidden_origin",
        )
        return False

    def _check_auth(self) -> bool:
        config = self.server.runtime_config
        if config.auth_mode == "off":
            return True
        if config.auth_mode != "bearer" or not config.auth_ready:
            self._send_jsonrpc_error(
                HTTPStatus.SERVICE_UNAVAILABLE,
                None,
                JSONRPC_INTERNAL_ERROR,
                "Server auth configuration is not ready.",
                "server_error",
            )
            return False
        authorization = self.headers.get("Authorization", "")
        expected = f"Bearer {config.bearer_token}"
        if not authorization:
            self._send_jsonrpc_error(
                HTTPStatus.UNAUTHORIZED,
                None,
                JSONRPC_INVALID_REQUEST,
                "Authorization header is required.",
                "unauthorized",
            )
            return False
        if authorization != expected:
            self._send_jsonrpc_error(
                HTTPStatus.FORBIDDEN,
                None,
                JSONRPC_INVALID_REQUEST,
                "Authorization token mismatch.",
                "unauthorized",
            )
            return False
        return True

    def _check_protocol_version(self) -> bool:
        raw_version = self.headers.get("MCP-Protocol-Version")
        protocol_version = raw_version.strip() if raw_version else LEGACY_PROTOCOL_VERSION
        if protocol_version in SUPPORTED_PROTOCOL_VERSIONS:
            return True
        self._send_jsonrpc_error(
            HTTPStatus.BAD_REQUEST,
            None,
            JSONRPC_INVALID_REQUEST,
            f"Unsupported MCP protocol version: {protocol_version}",
            "unsupported_protocol_version",
        )
        return False

    def _check_accept_header(self) -> bool:
        accept_header = self.headers.get("Accept")
        if self._accepts(accept_header, {"application/json", "text/event-stream"}):
            return True
        self._send_jsonrpc_error(
            HTTPStatus.NOT_ACCEPTABLE,
            None,
            JSONRPC_INVALID_REQUEST,
            "Accept header must include application/json and text/event-stream.",
            "unsupported_accept_header",
        )
        return False

    def _check_content_type(self) -> bool:
        content_type = self.headers.get_content_type()
        if content_type == "application/json":
            return True
        self._send_jsonrpc_error(
            HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            None,
            JSONRPC_INVALID_REQUEST,
            "Content-Type must be application/json.",
            "unsupported_content_type",
        )
        return False

    def _read_request_body(self) -> str | None:
        content_length = self.headers.get("Content-Length")
        limit = self.server.runtime_config.max_body_bytes
        self.connection.settimeout(self.server.runtime_config.request_timeout_seconds)
        try:
            if content_length is not None:
                length = int(content_length)
                if length > limit:
                    self.close_connection = True
                    self._send_jsonrpc_error(
                        HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                        None,
                        JSONRPC_INVALID_REQUEST,
                        "Request body exceeds max body size.",
                        "payload_too_large",
                    )
                    return None
                raw_body = self.rfile.read(length)
            else:
                raw_body = self.rfile.read(limit + 1)
                if len(raw_body) > limit:
                    self.close_connection = True
                    self._send_jsonrpc_error(
                        HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                        None,
                        JSONRPC_INVALID_REQUEST,
                        "Request body exceeds max body size.",
                        "payload_too_large",
                    )
                    return None
        except (OSError, ValueError, socket.timeout):
            self._send_jsonrpc_error(
                HTTPStatus.REQUEST_TIMEOUT,
                None,
                JSONRPC_INTERNAL_ERROR,
                "Request timeout",
                "request_timeout",
            )
            return None
        try:
            return raw_body.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            self._send_jsonrpc_error(
                HTTPStatus.BAD_REQUEST,
                None,
                JSONRPC_PARSE_ERROR,
                "Parse error",
                "parse_error",
            )
            return None

    @staticmethod
    def _accepts(header_value: str | None, required_types: set[str]) -> bool:
        if not header_value:
            return False
        accepted_types = {
            item.split(";", 1)[0].strip()
            for item in header_value.split(",")
            if item.strip()
        }
        return required_types.issubset(accepted_types)


def create_http_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    path: str = DEFAULT_PATH,
    runtime_config: RuntimeConfig | None = None,
) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), MCPHTTPRequestHandler)
    server.mcp_path = path
    server.runtime_config = runtime_config or RuntimeConfig.from_env()
    return server


def default_http_port() -> int:
    return parse_positive_int(os.environ.get("PORT"), DEFAULT_PORT)


def serve_stdio() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            payload = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }
            sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
            sys.stdout.flush()
            continue

        response = handle_jsonrpc_message(message)
        if response is None:
            continue
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="MCP protocol server for checktime tools")
    parser.add_argument("--health", action="store_true", help="Print readiness JSON and exit")
    parser.add_argument("--transport", choices=("stdio", "http"), default="stdio")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=default_http_port())
    parser.add_argument("--path", default=DEFAULT_PATH)
    args = parser.parse_args()

    if args.health:
        payload = get_health_status()
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0 if payload["ok"] else 1

    if args.transport == "stdio":
        return serve_stdio()

    server = create_http_server(args.host, args.port, args.path)
    print(f"Serving MCP HTTP on http://{args.host}:{args.port}{args.path}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
