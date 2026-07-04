from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from checktime_mcp.guardrails import BANNED_OUTPUT_TERMS  # noqa: E402
from checktime_mcp.mcp_adapter import handle_jsonrpc_message  # noqa: E402


SUCCESS_CASES = [
    (
        "generate_pre_contract_checklist",
        {
            "transaction_type": "lease_jeonse",
            "user_role": "tenant",
            "contract_date": "2026-07-12",
            "move_in_date": "2026-08-10",
        },
    ),
    (
        "generate_post_contract_timeline",
        {
            "transaction_type": "home_purchase",
            "user_role": "buyer",
            "contract_date": "2026-07-01",
            "closing_date": "2026-07-25",
            "move_in_date": "2026-07-26",
        },
    ),
    (
        "generate_required_documents",
        {
            "transaction_type": "lease_monthly",
            "user_role": "tenant",
            "stage": "before_move_in",
        },
    ),
    (
        "generate_calendar_items",
        {
            "transaction_type": "lease_jeonse",
            "user_role": "tenant",
            "move_in_date": "2026-08-10",
        },
    ),
    (
        "flag_expert_review_points",
        {
            "transaction_type": "home_purchase",
            "user_role": "buyer",
            "context": ["proxy_contract_possible"],
        },
    ),
    (
        "get_today_tasks",
        {
            "transaction_type": "lease_jeonse",
            "user_role": "tenant",
            "contract_date": "2026-07-12",
            "move_in_date": "2026-08-10",
            "current_date": "2026-08-08",
        },
    ),
]


def rpc_call(request_id: int, method: str, params: dict) -> dict:
    response = handle_jsonrpc_message(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }
    )
    if response is None:
        raise RuntimeError(f"unexpected notification response for {method}")
    return response


def main() -> int:
    failures = 0

    list_response = rpc_call(1, "tools/list", {})
    tools = list_response["result"]["tools"]
    print(f"PASS tools/list -> {len(tools)} tools")
    if len(tools) != 6:
        failures += 1

    for index, (tool_name, arguments) in enumerate(SUCCESS_CASES, start=2):
        response = rpc_call(index, "tools/call", {"name": tool_name, "arguments": arguments})
        structured = response["result"]["structuredContent"]
        rendered = json.dumps(structured, ensure_ascii=False)
        ok = (
            structured.get("ok") is True
            and "disclaimer" in structured
            and "source_status_summary" in structured
            and not any(term in rendered for term in BANNED_OUTPUT_TERMS)
        )
        print(f"{'PASS' if ok else 'FAIL'} tools/call -> {tool_name}")
        if not ok:
            failures += 1

    sensitive_response = rpc_call(
        99,
        "tools/call",
        {
            "name": "flag_expert_review_points",
            "arguments": {
                "transaction_type": "home_purchase",
                "user_role": "buyer",
                "context": "계약서 원문 업로드 가능 여부",
            },
        },
    )
    sensitive_ok = (
        sensitive_response["result"]["isError"] is True
        and sensitive_response["result"]["structuredContent"]["error"]["code"] == "sensitive_input_detected"
    )
    print(f"{'PASS' if sensitive_ok else 'FAIL'} sensitive input block")
    if not sensitive_ok:
        failures += 1

    invalid_date_response = rpc_call(
        100,
        "tools/call",
        {
            "name": "generate_pre_contract_checklist",
            "arguments": {
                "transaction_type": "lease_jeonse",
                "user_role": "tenant",
                "contract_date": "2026/07/12",
            },
        },
    )
    invalid_date_ok = (
        invalid_date_response["result"]["isError"] is True
        and invalid_date_response["result"]["structuredContent"]["error"]["code"] == "invalid_date_format"
    )
    print(f"{'PASS' if invalid_date_ok else 'FAIL'} invalid date block")
    if not invalid_date_ok:
        failures += 1

    return failures


if __name__ == "__main__":
    raise SystemExit(main())
