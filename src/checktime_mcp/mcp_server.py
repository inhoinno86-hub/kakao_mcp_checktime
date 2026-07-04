from __future__ import annotations

import argparse
import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .health import get_health_status
from .mcp_adapter import handle_jsonrpc_message


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_PATH = "/mcp"


class MCPHTTPRequestHandler(BaseHTTPRequestHandler):
    server_version = "ChecktimeMCP/0.1"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            payload = get_health_status()
            self._send_json(HTTPStatus.OK if payload["ok"] else HTTPStatus.SERVICE_UNAVAILABLE, payload)
            return

        if self.path == self.server.mcp_path:
            self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
            self.send_header("Allow", "POST")
            self.end_headers()
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != self.server.mcp_path:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8") if content_length else ""

        try:
            message = json.loads(raw_body)
        except json.JSONDecodeError:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"},
                },
            )
            return

        response = handle_jsonrpc_message(message)
        if response is None:
            self.send_response(HTTPStatus.ACCEPTED)
            self.end_headers()
            return

        self._send_json(HTTPStatus.OK, response, content_type="application/json")

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any], content_type: str = "application/json") -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def create_http_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, path: str = DEFAULT_PATH) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), MCPHTTPRequestHandler)
    server.mcp_path = path
    return server


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
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
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
