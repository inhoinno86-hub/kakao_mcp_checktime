from __future__ import annotations

import hashlib
from datetime import date
from typing import Any

from .guardrails import ToolError, validate_payload


def build_case(payload: dict[str, Any], required_fields: list[str]) -> dict[str, Any]:
    validate_payload(payload, required_fields)

    region = normalize_region(payload.get("region"))
    milestones = {
        "contract_date": payload.get("contract_date"),
        "move_in_date": payload.get("move_in_date"),
        "closing_date": payload.get("closing_date"),
        "lease_end_date": payload.get("lease_end_date"),
    }

    normalized = {
        "transaction_type": payload.get("transaction_type"),
        "user_role": payload.get("user_role"),
        "milestones": milestones,
        "deposit_amount_range": payload.get("deposit_amount_range"),
        "monthly_rent_range": payload.get("monthly_rent_range"),
        "region": region,
        "stage": payload.get("stage"),
        "calendar_style": payload.get("calendar_style", "talk_calendar_short"),
        "context": normalize_context(payload.get("context")),
        "current_date": payload.get("current_date") or date.today().isoformat(),
        "disclaimer_key": "general_information_only",
        "source_status_summary": "official_check_needed",
    }
    normalized["case_id"] = build_case_id(normalized)
    return normalized


def normalize_region(region: str | None) -> str | None:
    if not region:
        return None
    region = region.strip().lower().replace(" ", "_")
    if region.count("_") > 3:
        raise ToolError("sensitive_input_detected")
    return region


def normalize_context(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    raise ToolError("missing_required_field", "context 는 문자열 또는 문자열 배열이어야 합니다.")


def build_case_id(normalized_case: dict[str, Any]) -> str:
    digest = hashlib.sha1(repr(normalized_case).encode("utf-8")).hexdigest()[:8]
    return f"local_case_{digest}"
