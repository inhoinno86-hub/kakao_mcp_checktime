from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any


DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
REQUIRED_DATA_FILES = (
    "disclaimers.json",
    "timeline_rules.json",
    "expert_review_points.json",
    "transaction_types.json",
    "user_roles.json",
    "checklists/home_purchase_buyer.json",
    "checklists/lease_jeonse_tenant.json",
    "checklists/lease_monthly_tenant.json",
    "documents/home_purchase_buyer.json",
    "documents/lease_jeonse_tenant.json",
    "documents/lease_monthly_tenant.json",
)


def get_data_dir() -> Path:
    override = os.environ.get("CHECKTIME_MCP_DATA_DIR")
    return Path(override).resolve() if override else DEFAULT_DATA_DIR


def get_data_path(relative_path: str) -> Path:
    return get_data_dir() / relative_path


@lru_cache(maxsize=None)
def load_json(relative_path: str) -> Any:
    path = get_data_path(relative_path)
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def list_missing_data_files(data_dir: Path | None = None) -> list[str]:
    base_dir = data_dir or get_data_dir()
    return [path for path in REQUIRED_DATA_FILES if not (base_dir / path).exists()]


def load_disclaimer(key: str = "general_information_only") -> str:
    disclaimers = load_json("disclaimers.json")
    return disclaimers[key]["text"]


def load_checklist(transaction_type: str, user_role: str) -> list[dict[str, Any]]:
    return load_json(f"checklists/{transaction_type}_{user_role}.json")


def load_documents(transaction_type: str, user_role: str) -> list[dict[str, Any]]:
    return load_json(f"documents/{transaction_type}_{user_role}.json")


def load_timeline_rules() -> list[dict[str, Any]]:
    return load_json("timeline_rules.json")


def load_expert_review_points() -> list[dict[str, Any]]:
    return load_json("expert_review_points.json")


def summarize_source_status(items: list[dict[str, Any]]) -> str:
    statuses = sorted({item.get("source_status", "service_curated") for item in items})
    return " + ".join(statuses) if statuses else "service_curated"


def default_unknowns(items: list[dict[str, Any]]) -> list[str]:
    statuses = {item.get("source_status") for item in items}
    unknowns: list[str] = []
    if "official_check_needed" in statuses:
        unknowns.append("일부 일정과 제도 항목은 공식 기관 안내를 다시 확인해야 합니다.")
    if "confirmation_required" in statuses:
        unknowns.append("상황별 차이가 큰 항목은 거래 조건과 지역 기준으로 다시 확인해야 합니다.")
    return unknowns
