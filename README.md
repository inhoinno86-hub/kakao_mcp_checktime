# kakao_mcp_checktime

`부동산 체크타임 MCP`의 로컬 검증 및 MCP adapter 준비 repo다. 현재 목표는 기존 Python tool 로직을 MCP 표준 `tools/list`, `tools/call` 흐름과 연결하고, PlayMCP 임시 등록 전에 필요한 로컬 smoke test와 readiness 점검 경로를 갖추는 것이다.

## 프로젝트 목적

- 부동산 계약 전후 체크리스트와 일정 후보를 `MCP tool` 형태로 노출
- 민감정보 차단, disclaimer 강제, 금지 표현 self-check 유지
- PlayMCP 등록 전 로컬 adapter / server / smoke test 준비

## 현재 구현 범위

- 로컬 tool runner CLI
- MCP JSON-RPC adapter
- stdio transport server
- HTTP POST 기반 MCP endpoint 후보
- health/readiness check
- 공통 입력 검증과 case builder / normalizer
- 정적 JSON seed 데이터
- 핵심 tool 6개
- fixture 테스트, adapter 테스트, HTTP smoke 테스트

## 구현 제외 범위

- 실제 PlayMCP 등록
- 실제 카카오 클라우드 배포
- 심사 요청, 전체 공개 전환, Player 예선 최종 제출
- Kakao Tools Widget 구현
- 톡캘린더 직접 연동
- 외부 부동산 API / 실시간 법령 API
- 개인정보 저장, 상세주소 저장, 문서 업로드, 계약서 원문 분석
- 법률/세무 판단, 거래 안전성 판단, 매물 추천, 중개/매칭

## 설치

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

설치 없이 바로 실행하려면 `PYTHONPATH=src` 를 붙인다.

## 로컬 Tool 실행 방법

stdin 입력:

```bash
printf '%s\n' '{"transaction_type":"lease_jeonse","user_role":"tenant","contract_date":"2026-07-12","move_in_date":"2026-08-10"}' \
  | PYTHONPATH=src python3 -m checktime_mcp.server generate_pre_contract_checklist
```

fixture 파일 입력:

```bash
PYTHONPATH=src python3 -m checktime_mcp.server generate_required_documents --input tests/fixtures/scenario_monthly_documents.json
```

## MCP adapter 실행 방법

stdio server:

```bash
PYTHONPATH=src python3 -m checktime_mcp.mcp_server --transport stdio
```

HTTP server:

```bash
PYTHONPATH=src python3 -m checktime_mcp.mcp_server --transport http --host 127.0.0.1 --port 8000
```

health/readiness:

```bash
PYTHONPATH=src python3 -m checktime_mcp.mcp_server --health
```

## Tool 목록

- `generate_pre_contract_checklist`
- `generate_post_contract_timeline`
- `generate_required_documents`
- `generate_calendar_items`
- `flag_expert_review_points`
- `get_today_tasks`

## 테스트 실행 방법

fixture runner:

```bash
python3 scripts/run_fixtures.py
```

pytest:

```bash
pytest
```

adapter smoke test:

```bash
python3 scripts/smoke_mcp_adapter.py
```

HTTP server smoke test:

```bash
python3 scripts/smoke_http_server.py
```

금지 표현 / 민감정보 유도 grep:

```bash
bash scripts/grep_risk_terms.sh
```

## PlayMCP 등록 전 남은 단계

- 카카오 클라우드 MCP 서버 생성
- PlayMCP 개발자 콘솔 접근
- transport, 인증, timeout, endpoint field 세부 규칙 확인 필요
- 임시 등록 테스트
- 최종 제출용 서버 심사 요청
- 심사 통과 후 전체 공개 전환
- Player 예선 최종 제출

## 안전 / 리스크 정책 요약

- 상세주소, 주민등록번호, 계좌번호, 신분증 이미지, 계약서 원문 입력 차단
- 모든 응답에 disclaimer 포함
- 금지 표현 출력 self-check 적용
- 공식 재검증이 끝나지 않은 일정/제도 항목은 `official_check_needed` 또는 `confirmation_required` 유지

## known limitations

- 현재 서버는 로컬 smoke test 기준의 MCP adapter 준비 상태다. 실제 PlayMCP 등록 완료 상태가 아니다.
- HTTP endpoint 는 `application/json` 응답 중심의 최소 Streamable HTTP 후보 구현이다. GET 기반 SSE stream은 구현하지 않았다.
- PlayMCP 개발자 콘솔의 최신 필수 필드, 인증 방식, 응답 시간 제한은 별도 확인이 필요하다.
- `generate_contract_day_checklist` 는 이번 Phase에서 구현하지 않았다.

관련 문서:

- [docs/IMPLEMENTATION_NOTES.md](/home/inno/repo/kakao_mcp_checktime/docs/IMPLEMENTATION_NOTES.md)
- [docs/PLAYMCP_PRECHECK.md](/home/inno/repo/kakao_mcp_checktime/docs/PLAYMCP_PRECHECK.md)
- [docs/DEPLOYMENT_NOTES.md](/home/inno/repo/kakao_mcp_checktime/docs/DEPLOYMENT_NOTES.md)
