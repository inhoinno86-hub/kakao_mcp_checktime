from __future__ import annotations

import json
import threading
from pathlib import Path
from urllib.request import Request, urlopen

from checktime_mcp.health import get_health_status
from checktime_mcp.mcp_server import create_http_server


def test_health_fails_when_required_data_missing(tmp_path: Path) -> None:
    (tmp_path / "disclaimers.json").write_text("{}", encoding="utf-8")
    payload = get_health_status(tmp_path)
    assert payload["ok"] is False
    assert payload["data_status"] == "missing_files"
    assert "timeline_rules.json" in payload["missing_data_files"]


def test_http_server_supports_tools_list_and_call() -> None:
    server = create_http_server(port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    host, port = server.server_address
    base_url = f"http://{host}:{port}"
    try:
        list_request = Request(
            f"{base_url}/mcp",
            method="POST",
            data=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                    "params": {},
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        with urlopen(list_request) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert len(payload["result"]["tools"]) == 6

        call_request = Request(
            f"{base_url}/mcp",
            method="POST",
            data=json.dumps(
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
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        with urlopen(call_request) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert payload["result"]["structuredContent"]["ok"] is True
        assert "disclaimer" in payload["result"]["structuredContent"]
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()
