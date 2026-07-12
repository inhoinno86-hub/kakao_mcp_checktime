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
        data={
            "items": items,
            "timeline_checklist": build_pre_contract_timeline_checklist(case, items),
            "case": minimal_case(case),
        },
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
    action_timeline = build_action_timeline(case, timeline_items)
    expert_points = collect_expert_points(case, always_only=True)
    return success_response(
        data={
            "timeline_items": timeline_items,
            "action_timeline": action_timeline,
            "case": minimal_case(case),
        },
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
        data={
            "documents": documents,
            "timeline_checklist": build_document_timeline_checklist(case, documents),
            "case": minimal_case(case),
        },
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


def build_pre_contract_timeline_checklist(
    case: dict[str, Any],
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    contract_date = case["milestones"].get("contract_date")
    if not contract_date or not items:
        return []
    return build_relative_groups(
        anchor_date=contract_date,
        label="계약일",
        basis_prefix="contract_date",
        items=items,
        serializer=serialize_checklist_item,
        offsets=pre_contract_offsets(items),
    )


def build_document_timeline_checklist(
    case: dict[str, Any],
    documents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not documents:
        return []
    stage = case.get("stage")
    milestone_config = {
        "contract_day": ("contract_date", "계약일에 준비할 서류", "contract_date_same_day"),
        "before_move_in": ("move_in_date", "입주일 전까지 준비할 서류", "move_in_date_on_or_before"),
        "after_contract": ("contract_date", "계약 후 정리할 서류", "contract_date_after"),
    }
    config = milestone_config.get(stage)
    if not config:
        return []
    milestone_name, timing_label, date_basis = config
    anchor_date = case["milestones"].get(milestone_name)
    if not anchor_date:
        return []
    if stage == "contract_day":
        offsets = [0 for _ in documents]
        label = "계약일"
    elif stage == "before_move_in":
        offsets = before_move_in_document_offsets(documents)
        label = "입주일"
    else:
        offsets = after_contract_document_offsets(documents)
        label = "계약일"
    groups = build_relative_groups(
        anchor_date=anchor_date,
        label=label,
        basis_prefix=date_basis,
        items=documents,
        serializer=serialize_document_item,
        offsets=offsets,
    )
    if len(groups) == 1:
        groups[0]["timing_label"] = timing_label
    return groups


def build_action_timeline(
    case: dict[str, Any],
    timeline_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    action_items: list[dict[str, Any]] = []
    for item in timeline_items:
        action_items.append(
            {
                "title": item["title"],
                "date": item["date"],
                "date_type": item["status"],
                "timing_label": item["title"],
                "date_basis": item["date_basis"],
                "source_status": item["source_status"],
                "source_name": item.get("source_name"),
                "last_reviewed_at": item.get("last_reviewed_at"),
                "disclaimer_key": item.get("disclaimer_key", "general_information_only"),
                "action_type": "timeline_event",
            }
        )

    pre_contract_items = [
        item
        for item in load_checklist(case["transaction_type"], case["user_role"])
        if item["stage"] == "pre_contract"
    ]
    for group in build_pre_contract_timeline_checklist(case, pre_contract_items):
        for checklist_item in group["checklist_items"]:
            action_items.append(
                {
                    "title": checklist_item["title"],
                    "date": group["date"],
                    "date_type": group["date_type"],
                    "timing_label": group["timing_label"],
                    "date_basis": group["date_basis"],
                    "source_status": checklist_item["source_status"],
                    "source_name": checklist_item.get("source_name"),
                    "last_reviewed_at": checklist_item.get("last_reviewed_at"),
                    "disclaimer_key": checklist_item.get("disclaimer_key", "general_information_only"),
                    "action_type": "checklist_item",
                    "priority": checklist_item["priority"],
                    "needs_expert_review": checklist_item["needs_expert_review"],
                }
            )

    before_move_in_documents = [
        item
        for item in load_documents(case["transaction_type"], case["user_role"])
        if item["stage"] == "before_move_in"
    ]
    for group in build_document_timeline_checklist(
        {**case, "stage": "before_move_in"},
        before_move_in_documents,
    ):
        for checklist_item in group["checklist_items"]:
            action_items.append(
                {
                    "title": checklist_item["title"],
                    "date": group["date"],
                    "date_type": group["date_type"],
                    "timing_label": group["timing_label"],
                    "date_basis": group["date_basis"],
                    "source_status": checklist_item["source_status"],
                    "source_name": checklist_item.get("source_name"),
                    "last_reviewed_at": checklist_item.get("last_reviewed_at"),
                    "disclaimer_key": checklist_item.get("disclaimer_key", "general_information_only"),
                    "action_type": "document_item",
                    "priority": checklist_item["priority"],
                    "note": checklist_item.get("note"),
                }
            )

    return sorted(action_items, key=lambda item: (item["date"], item["title"]))


def build_relative_groups(
    *,
    anchor_date: str,
    label: str,
    basis_prefix: str,
    items: list[dict[str, Any]],
    serializer: Callable[[dict[str, Any]], dict[str, Any]],
    offsets: list[int],
) -> list[dict[str, Any]]:
    anchor = date.fromisoformat(anchor_date)
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for item, offset in zip(items, offsets):
        target_date = (anchor + timedelta(days=offset)).isoformat()
        timing_label = relative_timing_label(label, offset)
        date_basis = f"{basis_prefix}_{relative_basis_suffix(offset)}"
        grouped.setdefault(
            (target_date, timing_label, date_basis),
            [],
        ).append(serializer(item))
    return [
        {
            "date": target_date,
            "date_type": "candidate_due_date",
            "timing_label": timing_label,
            "date_basis": date_basis,
            "checklist_items": grouped[(target_date, timing_label, date_basis)],
        }
        for target_date, timing_label, date_basis in sorted(grouped)
    ]


def pre_contract_offsets(items: list[dict[str, Any]]) -> list[int]:
    base = []
    fallback = [-7, -3, -1, -1]
    for index, item in enumerate(items):
        if item["priority"] == "high":
            candidates = [-7, -3]
        elif item["priority"] == "medium":
            candidates = [-3, -1]
        else:
            candidates = [-1]
        offset = candidates[min(index, len(candidates) - 1)]
        if index < len(fallback):
            offset = fallback[index]
        base.append(offset)
    return base


def before_move_in_document_offsets(documents: list[dict[str, Any]]) -> list[int]:
    pattern = [-7, -3, -1]
    return [pattern[min(index, len(pattern) - 1)] for index, _ in enumerate(documents)]


def after_contract_document_offsets(documents: list[dict[str, Any]]) -> list[int]:
    pattern = [1, 3, 7]
    return [pattern[min(index, len(pattern) - 1)] for index, _ in enumerate(documents)]


def serialize_checklist_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": item["title"],
        "priority": item["priority"],
        "needs_expert_review": item["needs_expert_review"],
        "source_status": item["source_status"],
        "source_name": item.get("source_name"),
        "last_reviewed_at": item.get("last_reviewed_at"),
        "disclaimer_key": item.get("disclaimer_key", "general_information_only"),
    }


def serialize_document_item(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": document["name"],
        "priority": document["required_level"],
        "note": document.get("note"),
        "source_status": document["source_status"],
        "source_name": document.get("source_name"),
        "last_reviewed_at": document.get("last_reviewed_at"),
        "disclaimer_key": document.get("disclaimer_key", "general_information_only"),
    }


def relative_timing_label(label: str, offset: int) -> str:
    if offset < 0:
        return f"{label} {abs(offset)}일 전"
    if offset == 0:
        return f"{label} 당일"
    return f"{label} {offset}일 후"


def relative_basis_suffix(offset: int) -> str:
    if offset < 0:
        return f"minus_{abs(offset)}d"
    if offset == 0:
        return "same_day"
    return f"plus_{offset}d"


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
