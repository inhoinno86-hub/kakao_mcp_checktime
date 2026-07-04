from checktime_mcp.case_builder import build_case
from checktime_mcp.guardrails import ToolError


def test_build_case_normalizes_region_and_case_id() -> None:
    case = build_case(
        {
            "transaction_type": "lease_jeonse",
            "user_role": "tenant",
            "contract_date": "2026-07-12",
            "move_in_date": "2026-08-10",
            "region": "Seoul Songpa",
        },
        required_fields=["transaction_type", "user_role"],
    )

    assert case["region"] == "seoul_songpa"
    assert case["case_id"].startswith("local_case_")


def test_build_case_rejects_invalid_date() -> None:
    try:
        build_case(
            {
                "transaction_type": "lease_jeonse",
                "user_role": "tenant",
                "contract_date": "2026/07/12",
            },
            required_fields=["transaction_type", "user_role"],
        )
    except ToolError as exc:
        assert exc.code == "invalid_date_format"
    else:
        raise AssertionError("ToolError was expected")


def test_build_case_rejects_sensitive_address() -> None:
    try:
        build_case(
            {
                "transaction_type": "lease_jeonse",
                "user_role": "tenant",
                "region": "서울시 송파구 올림픽로 300 101호",
            },
            required_fields=["transaction_type", "user_role"],
        )
    except ToolError as exc:
        assert exc.code == "sensitive_input_detected"
    else:
        raise AssertionError("ToolError was expected")
