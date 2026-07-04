from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from checktime_mcp.mcp_server import create_http_server  # noqa: E402


def post_json(url: str, payload: dict) -> dict:
    request = Request(
        url,
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    server = create_http_server(port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    url = f"http://{host}:{port}/mcp"

    try:
        list_response = post_json(
            url,
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        )
        print(f"PASS tools/list -> {len(list_response['result']['tools'])} tools")

        call_response = post_json(
            url,
            {
                "jsonrpc": "2.0",
                "id": 2,
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
        ok = call_response["result"]["structuredContent"]["ok"] is True
        print(f"{'PASS' if ok else 'FAIL'} tools/call -> generate_required_documents")
        return 0 if ok else 1
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
