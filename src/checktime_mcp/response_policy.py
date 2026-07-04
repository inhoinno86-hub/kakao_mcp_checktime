from __future__ import annotations

import json
from typing import Any

from .data_loader import load_disclaimer
from .guardrails import assert_safe_output


def success_response(
    data: dict[str, Any],
    source_status_summary: str,
    unknowns: list[str] | None = None,
    expert_review_points: list[Any] | None = None,
    disclaimer_key: str = "general_information_only",
) -> dict[str, Any]:
    response = {
        "ok": True,
        "data": data,
        "disclaimer": load_disclaimer(disclaimer_key),
        "source_status_summary": source_status_summary,
        "unknowns": unknowns or [],
        "expert_review_points": expert_review_points or [],
    }
    assert_safe_output(json.dumps(response, ensure_ascii=False))
    return response


def error_response(
    code: str,
    message: str,
    disclaimer_key: str = "general_information_only",
) -> dict[str, Any]:
    response = {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
        },
        "disclaimer": load_disclaimer(disclaimer_key),
        "source_status_summary": "service_curated",
        "unknowns": [],
        "expert_review_points": [],
    }
    return response
