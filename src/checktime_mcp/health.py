from __future__ import annotations

from pathlib import Path
from typing import Any

from . import __version__
from .data_loader import get_data_dir, list_missing_data_files, load_disclaimer
from .guardrails import BANNED_OUTPUT_TERMS
from .tools import TOOL_REGISTRY


SERVICE_NAME = "real_estate_checktime_mcp"


def get_health_status(data_dir: Path | None = None) -> dict[str, Any]:
    base_dir = data_dir or get_data_dir()
    missing_files = list_missing_data_files(base_dir)
    data_status = "ok" if not missing_files else "missing_files"
    guardrails_status = guardrail_self_check(base_dir, missing_files)

    response: dict[str, Any] = {
        "ok": not missing_files and guardrails_status == "ok",
        "service": SERVICE_NAME,
        "version": __version__,
        "tools": sorted(TOOL_REGISTRY),
        "data_dir": str(base_dir),
        "data_status": data_status,
        "guardrails_status": guardrails_status,
        "playmcp_registration_status": "manual_step_required",
        "transport_readiness": {
            "stdio": "ready",
            "streamable_http": "candidate",
            "sse_get_stream": "not_implemented",
        },
    }
    if missing_files:
        response["missing_data_files"] = missing_files
    return response


def guardrail_self_check(data_dir: Path, missing_files: list[str]) -> str:
    if missing_files:
        return "blocked_by_missing_data"
    disclaimer = load_disclaimer()
    if any(term in disclaimer for term in BANNED_OUTPUT_TERMS):
        return "failed"
    return "ok"
