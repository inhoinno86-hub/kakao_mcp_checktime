# IMPLEMENTATION NOTES

## 설치 방법

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 로컬 실행 방법

```bash
printf '%s\n' '{"transaction_type":"lease_jeonse","user_role":"tenant","contract_date":"2026-07-12","move_in_date":"2026-08-10"}' \
  | PYTHONPATH=src python3 -m checktime_mcp.server generate_pre_contract_checklist
```

```bash
PYTHONPATH=src python3 -m checktime_mcp.server generate_calendar_items --input tests/fixtures/scenario_calendar_items.json
```

## fixture 테스트 실행 방법

```bash
python3 scripts/run_fixtures.py
pytest
```

## MCP adapter / server 실행 방법

```bash
PYTHONPATH=src python3 -m checktime_mcp.mcp_server --health
```

```bash
PYTHONPATH=src python3 -m checktime_mcp.mcp_server --transport stdio
```

```bash
PYTHONPATH=src python3 -m checktime_mcp.mcp_server --transport http --host 127.0.0.1 --port 8000
```

```bash
python3 scripts/smoke_mcp_adapter.py
python3 scripts/smoke_http_server.py
```

## Tool 예시 입력

### `generate_pre_contract_checklist`

```json
{
  "transaction_type": "lease_jeonse",
  "user_role": "tenant",
  "contract_date": "2026-07-12",
  "move_in_date": "2026-08-10",
  "region": "seoul_songpa"
}
```

### `generate_post_contract_timeline`

```json
{
  "transaction_type": "home_purchase",
  "user_role": "buyer",
  "contract_date": "2026-07-01",
  "closing_date": "2026-07-25",
  "move_in_date": "2026-07-26"
}
```

### `generate_required_documents`

```json
{
  "transaction_type": "lease_monthly",
  "user_role": "tenant",
  "stage": "before_move_in"
}
```

- 지원 `stage` 값이어도 해당 `transaction_type` / `user_role` 조합에 매칭 문서가 없으면 `documents_not_ready` 오류를 반환한다.
- 현재 정상 응답 보장 조합:
  - `home_purchase` + `buyer` -> `contract_day`, `after_contract`
  - `lease_jeonse` + `tenant` -> `before_move_in`
  - `lease_monthly` + `tenant` -> `before_move_in`

### `generate_calendar_items`

```json
{
  "transaction_type": "lease_jeonse",
  "user_role": "tenant",
  "move_in_date": "2026-08-10",
  "calendar_style": "talk_calendar_short"
}
```

### `flag_expert_review_points`

```json
{
  "transaction_type": "home_purchase",
  "user_role": "buyer",
  "context": ["proxy_contract_possible", "complex_rights_unclear"]
}
```

### `get_today_tasks`

```json
{
  "transaction_type": "lease_jeonse",
  "user_role": "tenant",
  "contract_date": "2026-07-12",
  "move_in_date": "2026-08-10",
  "current_date": "2026-08-08"
}
```

## Tool 예시 출력

```json
{
  "ok": true,
  "data": {
    "items": [
      {
        "item_id": "ljt_pre_001",
        "stage": "pre_contract",
        "title": "임대인 표시와 공식 서류의 일치 여부를 다시 확인하세요.",
        "priority": "high",
        "needs_expert_review": true,
        "source_status": "official_check_needed",
        "source_name": null,
        "last_reviewed_at": null,
        "disclaimer_key": "general_information_only"
      }
    ]
  },
  "disclaimer": "부동산 체크타임 MCP는 부동산 계약 전후에 사용자가 챙겨야 할 체크리스트와 일정 후보를 정리하는 생활형 도구입니다. 이 서비스는 공인중개, 법률자문, 세무자문, 등기업무 대행, 계약서 작성 또는 안전성 판단을 제공하지 않습니다. 구체적인 권리관계, 계약 조건, 세금, 등기, 분쟁 가능성은 공인중개사, 법무사, 변호사, 세무사 등 전문가와 공식 기관을 통해 확인해야 합니다.",
  "source_status_summary": "confirmation_required + official_check_needed + service_curated",
  "unknowns": [
    "일부 일정과 제도 항목은 공식 기관 안내를 다시 확인해야 합니다."
  ],
  "expert_review_points": []
}
```

## PlayMCP 등록 전 확인해야 할 사항

- 카카오 클라우드 MCP 서버 생성 필요
- PlayMCP 개발자 콘솔 접근 필요
- PlayMCP transport / 인증 / timeout 세부 규칙 확인 필요
- 임시 등록 테스트 필요
- 최종 제출용 서버 심사 요청 필요
- 심사 통과 후 전체 공개 전환 필요
- Player 예선 참여 최종 제출 필요

## 현재 구현 제외 범위

- 실제 PlayMCP 등록/배포
- 톡캘린더 직접 연동
- Kakao Tools / Widget
- 외부 API 연동
- 법률/세무 판단
- 계약서 원문/개인정보 처리

## known limitations

- 현재 일정 데이터는 정적 seed 기반이며 공식 기관 확인이 필요한 항목이 남아 있다.
- `generate_contract_day_checklist` 는 이번 Phase에서 구현하지 않았다.
- HTTP endpoint 는 최소 MCP JSON-RPC adapter + `tools/list` / `tools/call` / `health` 기준으로만 구현했다.
- GET 기반 SSE stream transport 는 아직 구현하지 않았다.

## TODO

- `generate_contract_day_checklist` 는 adapter, smoke test, 배포 문서 정리 후 후속 Phase에서 검토
