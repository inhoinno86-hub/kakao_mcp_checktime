from __future__ import annotations

from checktime_mcp.mcp_adapter import PROTOCOL_VERSION, handle_jsonrpc_message
from checktime_mcp.schemas import ALLOWED_DOCUMENT_STAGES


def call(method: str, params: dict | None = None, request_id: int = 1) -> dict:
    return handle_jsonrpc_message(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }
    )


def test_initialize_returns_server_capabilities() -> None:
    response = call("initialize")
    assert response["result"]["protocolVersion"] == PROTOCOL_VERSION
    assert "tools" in response["result"]["capabilities"]


def test_tools_list_exposes_all_required_tools() -> None:
    response = call("tools/list")
    tools = response["result"]["tools"]
    tool_map = {tool["name"]: tool for tool in tools}
    names = {tool["name"] for tool in tools}
    assert names == {
        "generate_pre_contract_checklist",
        "generate_post_contract_timeline",
        "generate_required_documents",
        "generate_calendar_items",
        "flag_expert_review_points",
        "get_today_tasks",
    }
    for tool in tools:
        assert "description" in tool
        assert "inputSchema" in tool
        assert "집계약 체크타임" in tool["description"]
        assert tool["annotations"]["openWorldHint"] is False
    assert set(tool_map["generate_pre_contract_checklist"]["inputSchema"]["properties"]) == {
        "transaction_type",
        "user_role",
    }
    assert set(tool_map["generate_required_documents"]["inputSchema"]["properties"]) == {
        "transaction_type",
        "user_role",
        "stage",
    }
    assert set(tool_map["flag_expert_review_points"]["inputSchema"]["properties"]) == {
        "transaction_type",
        "user_role",
        "context",
    }
    assert tool_map["flag_expert_review_points"]["inputSchema"]["properties"]["context"]["type"] == "array"
    document_tool = tool_map["generate_required_documents"]
    assert document_tool["inputSchema"]["properties"]["stage"]["enum"] == sorted(ALLOWED_DOCUMENT_STAGES)


def test_tools_call_wraps_existing_tool_response() -> None:
    response = call(
        "tools/call",
        {
            "name": "generate_pre_contract_checklist",
            "arguments": {
                "transaction_type": "lease_jeonse",
                "user_role": "tenant",
                "contract_date": "2026-07-12",
                "move_in_date": "2026-08-10",
            },
        },
    )
    result = response["result"]
    structured = result["structuredContent"]
    assert result["isError"] is False
    assert structured["ok"] is True
    assert "disclaimer" in structured
    assert "source_status_summary" in structured


def test_tools_call_propagates_sensitive_input_error() -> None:
    response = call(
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
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is True
    assert structured["error"]["code"] == "sensitive_input_detected"
    assert "disclaimer" in structured


def test_tools_call_propagates_invalid_date_error() -> None:
    response = call(
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
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is True
    assert structured["error"]["code"] == "invalid_date_format"


def test_tools_call_propagates_documents_not_ready_error() -> None:
    response = call(
        "tools/call",
        {
            "name": "generate_required_documents",
            "arguments": {
                "transaction_type": "home_purchase",
                "user_role": "buyer",
                "stage": "before_move_in",
            },
        },
    )
    structured = response["result"]["structuredContent"]
    assert response["result"]["isError"] is True
    assert structured["error"]["code"] == "documents_not_ready"
