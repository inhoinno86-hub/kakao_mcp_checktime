from __future__ import annotations

import re
from datetime import date
from typing import Any

from .schemas import (
    ALLOWED_CALENDAR_STYLES,
    ALLOWED_INPUT_FIELDS,
    ALLOWED_STAGES,
    ALLOWED_TRANSACTION_TYPES,
    ALLOWED_USER_ROLES,
    DATE_FIELDS,
    ERROR_MESSAGES,
)


class ToolError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        self.message = message or ERROR_MESSAGES.get(code, code)
        super().__init__(self.message)


RRN_PATTERN = re.compile(r"\b\d{6}-?[1-4]\d{6}\b")
ACCOUNT_PATTERN = re.compile(r"\b\d{10,14}\b")
DETAIL_ADDRESS_PATTERN = re.compile(
    r"((로|길)\s?\d{1,4}(-\d{1,4})?|(\d{1,4}층|\d{1,4}호)|아파트|빌라|오피스텔)"
)
RAW_CONTRACT_PATTERN = re.compile(
    r"(계약서\s*(원문|전체|전문|업로드)|특약\s*(전문|원문)|조항\s*(전문|원문)|등기부\s*(전체|원문))"
)

BANNED_OUTPUT_TERMS = [
    "안전합니다",
    "문제 없습니다",
    "계약해도 됩니다",
    "법적으로 문제없습니다",
    "보증금을 반드시 지킬 수 있습니다",
    "등기부상 위험이 없습니다",
    "이 집은 거래해도 됩니다",
    "이 특약을 넣으면 됩니다",
]


def validate_payload(payload: dict[str, Any], required_fields: list[str]) -> None:
    if not isinstance(payload, dict):
        raise ToolError("missing_required_field")

    unknown_fields = sorted(set(payload) - ALLOWED_INPUT_FIELDS)
    if unknown_fields:
        raise ToolError(
            "sensitive_input_detected",
            f"허용되지 않은 입력 필드가 있습니다: {', '.join(unknown_fields)}",
        )

    detect_sensitive_input(payload)

    for field in required_fields:
        value = payload.get(field)
        if value is None or value == "":
            raise ToolError(
                "missing_required_field",
                f"필수 입력값 `{field}` 이(가) 누락되었습니다.",
            )

    transaction_type = payload.get("transaction_type")
    if transaction_type and transaction_type not in ALLOWED_TRANSACTION_TYPES:
        raise ToolError("invalid_transaction_type")

    user_role = payload.get("user_role")
    if user_role and user_role not in ALLOWED_USER_ROLES:
        raise ToolError("unsupported_user_role")

    stage = payload.get("stage")
    if stage and stage not in ALLOWED_STAGES:
        raise ToolError("unsupported_stage")

    calendar_style = payload.get("calendar_style")
    if calendar_style and calendar_style not in ALLOWED_CALENDAR_STYLES:
        raise ToolError(
            "missing_required_field",
            "지원하지 않는 calendar_style 입니다.",
        )

    for field in DATE_FIELDS:
        value = payload.get(field)
        if value:
            validate_date(value)


def validate_date(value: str) -> None:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ToolError("invalid_date_format") from exc


def detect_sensitive_input(payload: Any) -> None:
    for text in iter_strings(payload):
        if RRN_PATTERN.search(text):
            raise ToolError("sensitive_input_detected")
        if ACCOUNT_PATTERN.search(text):
            raise ToolError("sensitive_input_detected")
        if DETAIL_ADDRESS_PATTERN.search(text):
            raise ToolError("sensitive_input_detected")
        if RAW_CONTRACT_PATTERN.search(text):
            raise ToolError("sensitive_input_detected")
        if len(text) > 300 and any(token in text for token in ("계약서", "특약", "등기부")):
            raise ToolError("sensitive_input_detected")


def iter_strings(value: Any) -> list[str]:
    results: list[str] = []
    if isinstance(value, str):
        results.append(value)
    elif isinstance(value, dict):
        for nested in value.values():
            results.extend(iter_strings(nested))
    elif isinstance(value, list):
        for nested in value:
            results.extend(iter_strings(nested))
    return results


def assert_safe_output(text: str) -> None:
    for term in BANNED_OUTPUT_TERMS:
        if term in text:
            raise ToolError("unsafe_output_detected")
