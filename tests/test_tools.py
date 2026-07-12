from __future__ import annotations

import json
from pathlib import Path

from checktime_mcp.tools import handle_tool


FIXTURE_DIR = Path(__file__).parent / "fixtures"
BANNED_TERMS = [
    "안전합니다",
    "문제 없습니다",
    "계약해도 됩니다",
    "법적으로 문제없습니다",
    "보증금을 반드시 지킬 수 있습니다",
    "등기부상 위험이 없습니다",
    "이 집은 거래해도 됩니다",
    "이 특약을 넣으면 됩니다",
]


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def assert_common_success_shape(response: dict) -> None:
    assert response["ok"] is True
    assert "disclaimer" in response
    assert "source_status_summary" in response
    assert isinstance(response["unknowns"], list)
    assert isinstance(response["expert_review_points"], list)
    rendered = json.dumps(response, ensure_ascii=False)
    for term in BANNED_TERMS:
        assert term not in rendered


def test_fixtures_cover_required_scenarios() -> None:
    for fixture_path in sorted(FIXTURE_DIR.glob("scenario_*.json")):
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        response = handle_tool(fixture["expected_tool"], fixture["input"])
        assert_common_success_shape(response)
        expected_keys = fixture["expected_response_shape"]["data_keys"]
        for key in expected_keys:
            assert key in response["data"]


def test_missing_required_field_returns_error() -> None:
    response = handle_tool(
        "generate_required_documents",
        {
            "transaction_type": "lease_monthly",
            "user_role": "tenant",
        },
    )
    assert response["ok"] is False
    assert response["error"]["code"] == "missing_required_field"


def test_generate_required_documents_returns_error_when_stage_has_no_documents() -> None:
    response = handle_tool(
        "generate_required_documents",
        {
            "transaction_type": "lease_monthly",
            "user_role": "tenant",
            "stage": "after_contract",
        },
    )
    assert response["ok"] is False
    assert response["error"]["code"] == "documents_not_ready"
    assert "home_purchase/buyer -> contract_day, after_contract" in response["error"]["message"]
    assert "lease_monthly/tenant -> before_move_in" in response["error"]["message"]


def test_generate_required_documents_returns_documents_for_supported_stage() -> None:
    response = handle_tool(
        "generate_required_documents",
        {
            "transaction_type": "lease_monthly",
            "user_role": "tenant",
            "stage": "before_move_in",
            "move_in_date": "2026-07-11",
        },
    )
    assert_common_success_shape(response)
    assert response["data"]["documents"]
    assert response["data"]["timeline_checklist"][0]["date"] == "2026-07-04"
    assert response["data"]["timeline_checklist"][0]["timing_label"] == "입주일 7일 전"
    assert response["data"]["timeline_checklist"][-1]["date"] == "2026-07-10"
    assert response["data"]["timeline_checklist"][-1]["timing_label"] == "입주일 1일 전"


def test_invalid_transaction_type_returns_error() -> None:
    response = handle_tool(
        "generate_pre_contract_checklist",
        {
            "transaction_type": "office_lease",
            "user_role": "tenant",
        },
    )
    assert response["ok"] is False
    assert response["error"]["code"] == "invalid_transaction_type"


def test_generate_pre_contract_checklist_includes_timeline_checklist_when_contract_date_exists() -> None:
    response = handle_tool(
        "generate_pre_contract_checklist",
        {
            "transaction_type": "lease_jeonse",
            "user_role": "tenant",
            "contract_date": "2026-07-20",
            "move_in_date": "2026-08-18",
        },
    )
    assert_common_success_shape(response)
    assert response["data"]["timeline_checklist"][0]["date"] == "2026-07-13"
    assert response["data"]["timeline_checklist"][0]["timing_label"] == "계약일 7일 전"
    assert response["data"]["timeline_checklist"][0]["checklist_items"]


def test_generate_post_contract_timeline_includes_action_timeline() -> None:
    response = handle_tool(
        "generate_post_contract_timeline",
        {
            "transaction_type": "lease_jeonse",
            "user_role": "tenant",
            "contract_date": "2026-07-20",
            "move_in_date": "2026-08-18",
        },
    )
    assert_common_success_shape(response)
    action_timeline = response["data"]["action_timeline"]
    assert action_timeline
    assert any(item["action_type"] == "timeline_event" for item in action_timeline)
    assert any(item["action_type"] == "checklist_item" for item in action_timeline)
    assert any(item["action_type"] == "document_item" for item in action_timeline)


def test_sensitive_input_returns_error() -> None:
    response = handle_tool(
        "flag_expert_review_points",
        {
            "transaction_type": "home_purchase",
            "user_role": "buyer",
            "context": "계약서 원문 업로드 가능 여부",
        },
    )
    assert response["ok"] is False
    assert response["error"]["code"] == "sensitive_input_detected"
