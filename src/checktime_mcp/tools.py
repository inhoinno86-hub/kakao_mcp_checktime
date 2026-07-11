from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Callable

from .case_builder import build_case
from .data_loader import (
    default_unknowns,
    load_checklist,
    load_documents,
    load_expert_review_points,
    load_timeline_rules,
    summarize_source_status,
)
from .guardrails import ToolError
from .response_policy import error_response, success_response

SUPPORTED_DOCUMENT_STAGES = {
    ("home_purchase", "buyer"): {"contract_day", "after_contract"},
    ("lease_jeonse", "tenant"): {"before_move_in"},
    ("lease_monthly", "tenant"): {"before_move_in"},
}


def handle_tool(tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    tool = TOOL_REGISTRY.get(tool_name)
    if not tool:
        return error_response("case_not_found", f"지원하지 않는 tool 입니다: {tool_name}")
    try:
        return tool(payload)
    except ToolError as exc:
        return error_response(exc.code, exc.message)
    except FileNotFoundError as exc:
        return error_response(
            "server_not_ready",
            f"필수 데이터 파일을 찾을 수 없습니다: {exc.filename}",
        )
    except Exception:
        return error_response("mcp_adapter_error", "기존 tool 처리 중 예기치 않은 오류가 발생했습니다.")


def generate_pre_contract_checklist(payload: dict[str, Any]) -> dict[str, Any]:
    case = build_case(
        payload,
        required_fields=["transaction_type", "user_role"],
    )
    items = [
        item
        for item in load_checklist(case["transaction_type"], case["user_role"])
        if item["stage"] == "pre_contract"
    ]
    expert_points = collect_expert_points(case, always_only=True)
    return success_response(
        data={"items": items, "case": minimal_case(case)},
        source_status_summary=summarize_source_status(items + expert_points),
        unknowns=default_unknowns(items + expert_points),
        expert_review_points=expert_points,
    )


def generate_post_contract_timeline(payload: dict[str, Any]) -> dict[str, Any]:
    case = build_case(
        payload,
        required_fields=["transaction_type", "user_role"],
    )
    timeline_items, unknowns = build_timeline_items(case)
    if not timeline_items:
        raise ToolError("timeline_not_ready")
    expert_points = collect_expert_points(case, always_only=True)
    return success_response(
        data={"timeline_items": timeline_items, "case": minimal_case(case)},
        source_status_summary=summarize_source_status(timeline_items + expert_points),
        unknowns=merge_unknowns(default_unknowns(timeline_items + expert_points), unknowns),
        expert_review_points=expert_points,
    )


def generate_required_documents(payload: dict[str, Any]) -> dict[str, Any]:
    case = build_case(
        payload,
        required_fields=["transaction_type", "user_role", "stage"],
    )
    validate_document_support(case)
    documents = [
        item
        for item in load_documents(case["transaction_type"], case["user_role"])
        if item["stage"] == payload["stage"]
    ]
    if not documents:
        raise ToolError("documents_not_ready")
    expert_points = collect_expert_points(case, always_only=True)
    return success_response(
        data={"documents": documents, "case": minimal_case(case)},
        source_status_summary=summarize_source_status(documents + expert_points),
        unknowns=default_unknowns(documents + expert_points),
        expert_review_points=expert_points,
    )


def validate_document_support(case: dict[str, Any]) -> None:
    supported_stages = SUPPORTED_DOCUMENT_STAGES.get((case["transaction_type"], case["user_role"]), set())
    if case["stage"] not in supported_stages:
        raise ToolError("documents_not_ready")


def generate_calendar_items(payload: dict[str, Any]) -> dict[str, Any]:
    case = build_case(
        payload,
        required_fields=["transaction_type", "user_role"],
    )
    timeline_items, unknowns = build_timeline_items(case)
    if not timeline_items:
        raise ToolError("timeline_not_ready")
    prefix = {
        "home_purchase": "[매매]",
        "lease_jeonse": "[전세]",
        "lease_monthly": "[월세]",
    }[case["transaction_type"]]
    calendar_items = [
        {
            "title": f"{prefix} {item['title']}",
            "date": item["date"],
            "memo": "적용 여부와 필요 자료는 공식 기관 및 전문가 기준으로 다시 확인하세요.",
            "source_status": item["source_status"],
            "source_name": item.get("source_name"),
            "last_reviewed_at": item.get("last_reviewed_at"),
            "disclaimer_key": item.get("disclaimer_key", "general_information_only"),
        }
        for item in timeline_items
    ]
    expert_points = collect_expert_points(case, always_only=True)
    return success_response(
        data={"calendar_items": calendar_items, "case": minimal_case(case)},
        source_status_summary=summarize_source_status(calendar_items + expert_points),
        unknowns=merge_unknowns(default_unknowns(calendar_items + expert_points), unknowns),
        expert_review_points=expert_points,
    )


def flag_expert_review_points(payload: dict[str, Any]) -> dict[str, Any]:
    case = build_case(
        payload,
        required_fields=["transaction_type", "user_role", "context"],
    )
    expert_points = collect_expert_points(case, always_only=False)
    return success_response(
        data={"expert_review_points": expert_points, "case": minimal_case(case)},
        source_status_summary=summarize_source_status(expert_points),
        unknowns=default_unknowns(expert_points),
        expert_review_points=expert_points,
    )


def get_today_tasks(payload: dict[str, Any]) -> dict[str, Any]:
    case = build_case(
        payload,
        required_fields=["transaction_type", "user_role"],
    )
    current_date = date.fromisoformat(case["current_date"])
    timeline_items, timeline_unknowns = build_timeline_items(case)
    pre_contract_items = [
        item
        for item in load_checklist(case["transaction_type"], case["user_role"])
        if item["stage"] == "pre_contract"
    ]
    before_move_in_documents = [
        item
        for item in load_documents(case["transaction_type"], case["user_role"])
        if item["stage"] == "before_move_in"
    ]

    today_tasks: list[dict[str, Any]] = []
    upcoming_deadlines: list[dict[str, Any]] = []

    contract_date = parse_optional_date(case["milestones"].get("contract_date"))
    move_in_date = parse_optional_date(case["milestones"].get("move_in_date"))

    if contract_date and current_date <= contract_date:
        for item in pre_contract_items[:3]:
            today_tasks.append(
                {
                    "title": item["title"],
                    "urgency": item["priority"],
                    "reason": "계약 전 확인 후보",
                }
            )
    elif move_in_date and current_date <= move_in_date:
        for item in before_move_in_documents[:3]:
            today_tasks.append(
                {
                    "title": item["name"],
                    "urgency": "high" if move_in_date - current_date <= timedelta(days=3) else "medium",
                    "reason": "입주 전 준비서류 후보",
                }
            )

    for item in timeline_items:
        item_date = date.fromisoformat(item["date"])
        days_left = (item_date - current_date).days
        if 0 <= days_left <= 14:
            upcoming_deadlines.append(
                {
                    "title": item["title"],
                    "date": item["date"],
                    "days_left": days_left,
                    "status": item["status"],
                }
            )
            if days_left <= 3:
                today_tasks.append(
                    {
                        "title": item["title"],
                        "urgency": "high",
                        "reason": "임박한 일정 후보",
                    }
                )

    today_tasks = dedupe_by_title(today_tasks)[:3]
    upcoming_deadlines = sorted(upcoming_deadlines, key=lambda item: item["date"])[:5]
    expert_points = collect_expert_points(case, always_only=True)
    aggregate_items = pre_contract_items + before_move_in_documents + timeline_items + expert_points
    return success_response(
        data={
            "today_tasks": today_tasks,
            "upcoming_deadlines": upcoming_deadlines,
            "case": minimal_case(case),
        },
        source_status_summary=summarize_source_status(aggregate_items),
        unknowns=merge_unknowns(default_unknowns(aggregate_items), timeline_unknowns),
        expert_review_points=expert_points,
    )


def build_timeline_items(case: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    items: list[dict[str, Any]] = []
    unknowns: list[str] = []
    rules = [
        rule
        for rule in load_timeline_rules()
        if rule["transaction_type"] == case["transaction_type"]
        and rule["user_role"] == case["user_role"]
    ]

    for rule in rules:
        base_date_value = case["milestones"].get(rule["base_date"])
        if not base_date_value:
            if rule.get("required", True):
                unknowns.append(f"{rule['title']} 계산을 위해 `{rule['base_date']}` 확인이 필요합니다.")
            continue
        base_date = date.fromisoformat(base_date_value)
        target_date = base_date + timedelta(days=rule["offset_days"])
        offset = rule["offset_days"]
        sign = "plus" if offset >= 0 else "minus"
        items.append(
            {
                "title": rule["title"],
                "date": target_date.isoformat(),
                "date_basis": f"{rule['base_date']}_{sign}_{abs(offset)}d",
                "status": rule["date_type"],
                "source_status": rule["source_status"],
                "source_name": rule.get("source_name"),
                "last_reviewed_at": rule.get("last_reviewed_at"),
                "disclaimer_key": rule.get("disclaimer_key", "general_information_only"),
            }
        )
    if not items and unknowns:
        raise ToolError("insufficient_milestones")
    return sorted(items, key=lambda item: item["date"]), dedupe_strings(unknowns)


def collect_expert_points(case: dict[str, Any], always_only: bool) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    context = set(case["context"])
    for item in load_expert_review_points():
        if item["transaction_type"] != case["transaction_type"]:
            continue
        if item["user_role"] != case["user_role"]:
            continue
        if item.get("always_include"):
            selected.append(item)
            continue
        triggers = set(item.get("context_tags", []))
        if not always_only and triggers & context:
            selected.append(item)
    return selected


def minimal_case(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case["case_id"],
        "transaction_type": case["transaction_type"],
        "user_role": case["user_role"],
        "milestones": case["milestones"],
        "region": case["region"],
        "disclaimer_key": case["disclaimer_key"],
        "source_status_summary": case["source_status_summary"],
    }


def parse_optional_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def dedupe_strings(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def merge_unknowns(first: list[str], second: list[str]) -> list[str]:
    return dedupe_strings(first + second)


def dedupe_by_title(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        title = item["title"]
        if title in seen:
            continue
        seen.add(title)
        result.append(item)
    return result


TOOL_REGISTRY: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "generate_pre_contract_checklist": generate_pre_contract_checklist,
    "generate_post_contract_timeline": generate_post_contract_timeline,
    "generate_required_documents": generate_required_documents,
    "generate_calendar_items": generate_calendar_items,
    "flag_expert_review_points": flag_expert_review_points,
    "get_today_tasks": get_today_tasks,
}
