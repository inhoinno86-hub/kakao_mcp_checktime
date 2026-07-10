from __future__ import annotations

ALLOWED_TRANSACTION_TYPES = {
    "home_purchase",
    "lease_jeonse",
    "lease_monthly",
}

ALLOWED_USER_ROLES = {
    "buyer",
    "tenant",
}

ALLOWED_STAGES = {
    "pre_contract",
    "contract_day",
    "before_move_in",
    "after_contract",
    "after_move_in",
}

ALLOWED_CALENDAR_STYLES = {
    "talk_calendar_short",
    "talk_calendar_detailed",
}

ALLOWED_SOURCE_STATUS = {
    "official_verified",
    "official_check_needed",
    "confirmation_required",
    "service_curated",
}

ALLOWED_INPUT_FIELDS = {
    "transaction_type",
    "user_role",
    "contract_date",
    "move_in_date",
    "closing_date",
    "lease_end_date",
    "deposit_amount_range",
    "monthly_rent_range",
    "region",
    "current_date",
    "stage",
    "context",
    "calendar_style",
}

DATE_FIELDS = {
    "contract_date",
    "move_in_date",
    "closing_date",
    "lease_end_date",
    "current_date",
}

ERROR_MESSAGES = {
    "invalid_transaction_type": "지원하지 않는 거래 유형입니다.",
    "unsupported_user_role": "지원하지 않는 사용자 역할입니다.",
    "invalid_date_format": "날짜는 YYYY-MM-DD 형식으로 입력해야 합니다.",
    "missing_required_field": "필수 입력값이 누락되었습니다.",
    "sensitive_input_detected": "상세주소, 주민등록번호, 계좌번호, 계약서 원문 등 민감정보는 입력하지 말고 시/군/구와 날짜 중심으로 다시 입력하세요.",
    "unsafe_output_detected": "응답 생성 중 안전하지 않은 표현이 감지되어 결과를 반환하지 않았습니다.",
    "insufficient_milestones": "일정 계산에 필요한 기준 날짜가 부족합니다.",
    "timeline_not_ready": "현재 입력만으로는 일정 후보를 만들기 어렵습니다.",
    "documents_not_ready": "현재 입력한 거래 유형, 역할, 단계 조합으로는 준비서류 후보를 제공하기 어렵습니다.",
    "case_not_found": "요청한 케이스를 찾을 수 없습니다.",
    "unsupported_stage": "지원하지 않는 단계입니다.",
    "mcp_adapter_error": "MCP adapter 처리 중 오류가 발생했습니다.",
    "unsupported_transport": "지원하지 않는 transport 입니다.",
    "server_not_ready": "서버 준비 상태 확인에 실패했습니다.",
}
