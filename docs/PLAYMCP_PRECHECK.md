# PLAYMCP PRECHECK

## 현재 구현 상태

- 핵심 tool 6개가 로컬 tool runner와 MCP adapter 양쪽에서 호출 가능
- `tools/list` 와 `tools/call` 로컬 smoke test 가능
- `stdio` transport 지원
- HTTP POST 기반 MCP endpoint 후보 구현
- `GET /health` readiness check 가능
- guardrail, disclaimer, unknowns, expert review points 유지
- 실제 PlayMCP 등록은 아직 수행하지 않음
- 실제 카카오 클라우드 배포는 아직 수행하지 않음
- 실제 심사 요청은 아직 수행하지 않음

## 로컬 검증 명령

```bash
pytest
python3 scripts/run_fixtures.py
python3 scripts/smoke_mcp_adapter.py
python3 scripts/smoke_http_server.py
PYTHONPATH=src python3 -m checktime_mcp.mcp_server --health
```

## MCP adapter smoke test 명령

```bash
python3 scripts/smoke_mcp_adapter.py
```

## health / readiness check 명령

```bash
PYTHONPATH=src python3 -m checktime_mcp.mcp_server --health
```

## 배포 전 확인할 환경 변수

- `CHECKTIME_MCP_DATA_DIR`
  - 선택 사항
  - 기본값은 repo의 `data/`
  - 배포 환경에서 data 경로를 다르게 둘 때만 사용
- 인증 관련 환경 변수: 확인 필요
- PlayMCP 등록용 별도 키/토큰 요구 여부: 확인 필요

## 배포 전 확인할 포트 / transport

- 기본 로컬 포트: `8000`
- MCP path 기본값: `/mcp`
- health path: `/health`
- transport:
  - `stdio`: 로컬 검증 가능
  - HTTP POST 기반 MCP endpoint: 로컬 검증 가능
  - GET 기반 SSE stream: 미구현
- PlayMCP 등록 시 요구 transport 세부 사항:
  - Kakao tech 공개 글 기준 `Streamable HTTP` 언급 확인
  - PlayMCP 개발자 콘솔의 최신 필수 transport / header / auth / timeout 규칙은 확인 필요

## 수동 등록 전 체크리스트

- 카카오 클라우드 MCP 서버 생성 필요
- PlayMCP 개발자 콘솔 접근 필요
- 공식 가이드 세부 내용 확인 필요
- 임시 등록 테스트 필요
- 최종 제출용 서버 심사 요청 필요
- 심사 통과 후 전체 공개 전환 필요
- Player 예선 참여 최종 제출 필요
- 제출 1회 제한 주의

## 현재 한계

- 실제 PlayMCP 임시 등록 미수행
- 실제 카카오 클라우드 배포 미수행
- 서버 인증 방식 결정 안 됨
- PlayMCP 개발자 콘솔 입력 필드 최신 규칙 확인 필요
- 서버 응답 시간 제한 / payload 제한 확인 필요
- `generate_contract_day_checklist` 미구현

## 비고

- 실제 등록/배포는 이번 작업에서 수행하지 않음
- 로컬에서 MCP adapter smoke test 통과와 실제 PlayMCP 등록 가능은 동일하지 않음
