from checktime_mcp.guardrails import ToolError, assert_safe_output, validate_payload


def test_validate_payload_rejects_rrn() -> None:
    try:
        validate_payload(
            {
                "transaction_type": "lease_jeonse",
                "user_role": "tenant",
                "context": "900101-1234567",
            },
            required_fields=["transaction_type", "user_role"],
        )
    except ToolError as exc:
        assert exc.code == "sensitive_input_detected"
    else:
        raise AssertionError("ToolError was expected")


def test_assert_safe_output_rejects_banned_term() -> None:
    try:
        assert_safe_output("이 응답은 안전합니다")
    except ToolError as exc:
        assert exc.code == "unsafe_output_detected"
    else:
        raise AssertionError("ToolError was expected")
