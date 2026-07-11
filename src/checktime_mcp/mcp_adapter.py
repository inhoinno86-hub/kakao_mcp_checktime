from __future__ import annotations

import json
from typing import Any

from . import __version__
from .health import SERVICE_NAME
from .response_policy import error_response
from .runtime_config import LEGACY_PROTOCOL_VERSION
from .schemas import (
    ALLOWED_CALENDAR_STYLES,
    ALLOWED_DOCUMENT_STAGES,
    ALLOWED_STAGES,
    ALLOWED_TRANSACTION_TYPES,
    ALLOWED_USER_ROLES,
)
from .tools import TOOL_REGISTRY, handle_tool


PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOL_VERSIONS = {LEGACY_PROTOCOL_VERSION, PROTOCOL_VERSION}

JSONRPC_INVALID_REQUEST = -32600
JSONRPC_PARSE_ERROR = -32700
JSONRPC_METHOD_NOT_FOUND = -32601
JSONRPC_INVALID_PARAMS = -32602
JSONRPC_INTERNAL_ERROR = -32603


def build_tool_definitions() -> list[dict[str, Any]]:
    common_properties = {
        "transaction_type": {
            "type": "string",
            "enum": sorted(ALLOWED_TRANSACTION_TYPES),
            "description": "거래 유형. home_purchase, lease_jeonse, lease_monthly 중 하나.",
        },
        "user_role": {
            "type": "string",
            "enum": sorted(ALLOWED_USER_ROLES),
            "description": "사용자 역할. buyer 또는 tenant.",
        },
        "contract_date": {"type": "string", "description": "YYYY-MM-DD 형식의 계약일."},
        "move_in_date": {"type": "string", "description": "YYYY-MM-DD 형식의 입주일."},
        "closing_date": {"type": "string", "description": "YYYY-MM-DD 형식의 잔금일."},
        "lease_end_date": {"type": "string", "description": "YYYY-MM-DD 형식의 임대차 종료일."},
        "deposit_amount_range": {"type": "string", "description": "정확한 액수 대신 범위 문자열."},
        "region": {"type": "string", "description": "시/군/구 수준까지만 허용. 상세주소 금지."},
        "current_date": {"type": "string", "description": "YYYY-MM-DD 형식의 기준일."},
        "stage": {
            "type": "string",
            "enum": sorted(ALLOWED_STAGES),
            "description": "문서 또는 단계 구분.",
        },
        "context": {
            "oneOf": [
                {"type": "string"},
                {"type": "array", "items": {"type": "string"}},
            ],
            "description": "전문가 검토 트리거용 문맥 태그.",
        },
        "calendar_style": {
            "type": "string",
            "enum": sorted(ALLOWED_CALENDAR_STYLES),
            "description": "캘린더 출력 스타일.",
        },
    }
    output_schema = {
        "type": "object",
        "properties": {
            "ok": {"type": "boolean"},
            "data": {"type": "object"},
            "error": {"type": "object"},
            "disclaimer": {"type": "string"},
            "source_status_summary": {"type": "string"},
            "unknowns": {"type": "array", "items": {"type": "string"}},
            "expert_review_points": {"type": "array", "items": {"type": "object"}},
        },
        "required": [
            "ok",
            "disclaimer",
            "source_status_summary",
            "unknowns",
            "expert_review_points",
        ],
    }
    definitions = [
        {
            "name": "generate_pre_contract_checklist",
            "title": "계약 전 체크리스트 생성",
            "description": "집계약 체크타임에서 거래 유형과 역할 기준으로 계약 전 확인 항목 후보를 반환합니다.",
            "required": ["transaction_type", "user_role"],
        },
        {
            "name": "generate_post_contract_timeline",
            "title": "계약 후 일정 후보 생성",
            "description": "집계약 체크타임에서 기준 날짜를 바탕으로 계약 후 일정 후보를 계산합니다.",
            "required": ["transaction_type", "user_role"],
        },
        {
            "name": "generate_required_documents",
            "title": "단계별 준비서류 생성",
            "description": "집계약 체크타임에서 거래 유형, 역할, 단계 기준으로 준비서류 후보를 반환합니다. 현재 지원 단계는 home_purchase/buyer 의 contract_day, after_contract 와 lease_jeonse·lease_monthly/tenant 의 before_move_in 입니다.",
            "required": ["transaction_type", "user_role", "stage"],
            "properties_override": {
                "stage": {
                    "type": "string",
                    "enum": sorted(ALLOWED_DOCUMENT_STAGES),
                    "description": "준비서류 단계 구분. 현재 generate_required_documents 는 contract_day, before_move_in, after_contract 만 지원합니다.",
                }
            },
        },
        {
            "name": "generate_calendar_items",
            "title": "캘린더 항목 생성",
            "description": "집계약 체크타임에서 타임라인을 캘린더 입력용 항목으로 변환합니다.",
            "required": ["transaction_type", "user_role"],
        },
        {
            "name": "flag_expert_review_points",
            "title": "전문가 검토 포인트 추출",
            "description": "집계약 체크타임에서 context 태그를 기준으로 전문가 재확인 포인트를 반환합니다.",
            "required": ["transaction_type", "user_role", "context"],
        },
        {
            "name": "get_today_tasks",
            "title": "오늘 해야 할 일 후보 생성",
            "description": "집계약 체크타임에서 기준일과 일정 후보를 조합해 오늘 해야 할 일과 임박 일정 후보를 반환합니다.",
            "required": ["transaction_type", "user_role"],
        },
    ]
    return [
        {
            "name": item["name"],
            "title": item["title"],
            "description": item["description"],
            "inputSchema": {
                "type": "object",
                "properties": {**common_properties, **item.get("properties_override", {})},
                "required": item["required"],
                "additionalProperties": False,
            },
            "outputSchema": output_schema,
            "annotations": {
                "title": item["title"],
                "readOnlyHint": True,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        }
        for item in definitions
    ]


TOOL_DEFINITIONS = build_tool_definitions()
TOOL_DEFINITION_MAP = {tool["name"]: tool for tool in TOOL_DEFINITIONS}


def list_tools_result() -> dict[str, Any]:
    return {"tools": TOOL_DEFINITIONS}


def call_tool_result(tool_name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    response = handle_tool(tool_name, arguments or {})
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(response, ensure_ascii=False, indent=2),
            }
        ],
        "structuredContent": response,
        "isError": not response.get("ok", False),
    }


def handle_jsonrpc_message(message: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(message, dict):
        return jsonrpc_error_response(None, JSONRPC_INVALID_REQUEST, "유효한 JSON-RPC object가 아닙니다.")

    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}

    if message.get("jsonrpc") != "2.0" or not isinstance(method, str):
        return jsonrpc_error_response(request_id, JSONRPC_INVALID_REQUEST, "jsonrpc=2.0 과 method 가 필요합니다.")

    if request_id is None:
        if method == "notifications/initialized":
            return None
        return None

    try:
        if method == "initialize":
            return jsonrpc_result_response(
                request_id,
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {
                        "tools": {"listChanged": False},
                    },
                    "serverInfo": {
                        "name": SERVICE_NAME,
                        "version": __version__,
                    },
                },
            )
        if method == "ping":
            return jsonrpc_result_response(request_id, {})
        if method == "tools/list":
            return jsonrpc_result_response(request_id, list_tools_result())
        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments") or {}
            if not isinstance(tool_name, str):
                return jsonrpc_error_response(request_id, JSONRPC_INVALID_PARAMS, "`params.name` 이 필요합니다.")
            if not isinstance(arguments, dict):
                return jsonrpc_error_response(
                    request_id,
                    JSONRPC_INVALID_PARAMS,
                    "`params.arguments` 는 object 여야 합니다.",
                )
            return jsonrpc_result_response(request_id, call_tool_result(tool_name, arguments))
        return jsonrpc_error_response(request_id, JSONRPC_METHOD_NOT_FOUND, f"지원하지 않는 method 입니다: {method}")
    except Exception as exc:
        return jsonrpc_error_response(
            request_id,
            JSONRPC_INTERNAL_ERROR,
            "MCP adapter internal error",
            data=error_response("mcp_adapter_error", "기존 tool 처리 중 예기치 않은 오류가 발생했습니다."),
        )


def jsonrpc_result_response(request_id: str | int, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def jsonrpc_error_response(
    request_id: str | int | None,
    code: int,
    message: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
    }
    if data is not None:
        error["data"] = data
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": error,
    }
