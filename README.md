# kakao_mcp_checktime

`부동산 체크타임 MCP`의 로컬 검증 및 MCP adapter 준비 repo다.

현재 상태는 PlayMCP 임시 등록 전 remote deployment candidate / HTTPS smoke preflight 준비 단계다. 실제 PlayMCP 등록, 실제 카카오 클라우드 배포, 심사 요청, 전체 공개 전환, Player 예선 최종 제출은 수행하지 않았다.

PlayMCP 임시 등록 전 Streamable HTTP transport 후보를 보강했고, 로컬 HTTP endpoint smoke test를 통과한 상태다. 다만 PlayMCP 개발자 콘솔의 최신 필수 필드, 인증 방식, timeout/header 규칙은 수동 확인이 필요하다.

## 프로젝트 목적

- 부동산 계약 전후 체크리스트와 일정 후보를 `MCP tool` 형태로 노출
- 민감정보 차단, disclaimer 강제, 금지 표현 self-check 유지
- PlayMCP 임시 등록 전 MCP adapter / HTTP endpoint / smoke test / readiness 경로 준비

## 현재 구현 범위

- 로컬 tool runner CLI
- MCP JSON-RPC adapter
- stdio transport server
- HTTP `POST /mcp` 기반 Streamable HTTP 후보 endpoint
- `GET /mcp` SSE 미지원 시 `405`
- `OPTIONS /mcp` preflight 후보 처리
- `Origin` allowlist 후보
- `Bearer` auth 후보와 local auth off 모드
- request timeout / payload size limit 후보
- health/readiness check
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
- `generate_contract_day_checklist`

## 설치

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

설치 없이 바로 실행하려면 `PYTHONPATH=src` 를 붙인다.

## 로컬 Tool 실행 방법

```bash
printf '%s\n' '{"transaction_type":"lease_jeonse","user_role":"tenant","contract_date":"2026-07-12","move_in_date":"2026-08-10"}' \
  | PYTHONPATH=src python3 -m checktime_mcp.server generate_pre_contract_checklist
```

```bash
PYTHONPATH=src python3 -m checktime_mcp.server generate_required_documents --input tests/fixtures/scenario_monthly_documents.json
```

## MCP adapter / HTTP server 실행 방법

stdio:

```bash
PYTHONPATH=src python3 -m checktime_mcp.mcp_server --transport stdio
```

local HTTP:

```bash
PYTHONPATH=src python3 -m checktime_mcp.mcp_server --transport http --host 127.0.0.1 --port 8000
```

remote candidate HTTP:

```bash
CHECKTIME_AUTH_MODE=bearer \
CHECKTIME_BEARER_TOKEN=<set-at-runtime> \
CHECKTIME_ALLOWED_ORIGINS=<confirm-origin-before-use> \
CHECKTIME_REQUEST_TIMEOUT_SECONDS=10 \
CHECKTIME_MAX_BODY_BYTES=1048576 \
PORT=8080 \
PYTHONPATH=src python3 -m checktime_mcp.mcp_server --transport http --host 0.0.0.0
```

health/readiness:

```bash
PYTHONPATH=src python3 -m checktime_mcp.mcp_server --health
```

## HTTP endpoint 정책

기본 endpoint:

- MCP path: `/mcp`
- health path: `/health`
- 기본 응답 transport: `application/json`

`POST /mcp`

- `Content-Type: application/json` 필요
- `Accept: application/json, text/event-stream` 포함 필요
- `MCP-Protocol-Version` 지원값:
  - `2025-06-18`
  - legacy fallback policy: header 미지정 시 `2025-03-26` 으로 간주
- JSON-RPC 2.0 `initialize`, `ping`, `tools/list`, `tools/call` 처리
- 잘못된 JSON은 parse error 반환
- 미지원 method 는 method not found 반환
- `id` 없는 요청은 notification policy로 `202 Accepted`

`GET /mcp`

- `Accept: text/event-stream` 일 때 현재는 `405 Method Not Allowed`
- body 에 `SSE stream not implemented` 메시지 반환
- 현재 `sse_get_stream: not_implemented`

`OPTIONS /mcp`

- `204 No Content`
- `Access-Control-Allow-Methods: POST, GET, OPTIONS`
- `Access-Control-Allow-Headers: Content-Type, Accept, Authorization, MCP-Protocol-Version`

## Header / auth / origin 설정

환경변수:

- `CHECKTIME_AUTH_MODE`
  - `off`: local only
  - `bearer`: remote candidate
- `CHECKTIME_BEARER_TOKEN`
- `CHECKTIME_ALLOWED_ORIGINS`
  - 예시: `https://playmcp.kakao.com,https://*.kakao.com`
  - 예시는 예시일 뿐이며 실제 허용 Origin 값은 확인 필요
- `CHECKTIME_REQUEST_TIMEOUT_SECONDS`
  - 기본값 `10`
- `CHECKTIME_MAX_BODY_BYTES`
  - 기본값 `1048576`
- `PORT`
  - remote candidate 기본 예시 `8080`
- `CHECKTIME_MCP_DATA_DIR`
  - 선택 사항

local mode 예시:

```bash
CHECKTIME_AUTH_MODE=off \
PYTHONPATH=src python3 -m checktime_mcp.mcp_server --transport http --host 127.0.0.1 --port 8000
```

remote candidate mode 예시:

```bash
CHECKTIME_AUTH_MODE=bearer \
CHECKTIME_BEARER_TOKEN=<set-at-runtime> \
CHECKTIME_ALLOWED_ORIGINS=<confirm-origin-before-use> \
CHECKTIME_REQUEST_TIMEOUT_SECONDS=10 \
CHECKTIME_MAX_BODY_BYTES=1048576 \
PORT=8080 \
PYTHONPATH=src python3 -m checktime_mcp.mcp_server --transport http --host 0.0.0.0
```

주의:

- token 값을 README, git, Docker image 에 직접 기록하지 않는다.
- [`config/deployment.env.example`](/home/inno/repo/kakao_mcp_checktime/config/deployment.env.example) 는 예시 템플릿일 뿐이며 secret 값은 넣지 않는다.
- `Origin` header 가 없으면 현재는 server-to-server candidate 로 허용한다.
- 실제 PlayMCP 인증 방식, bearer token 지원 여부, 필수 Origin 값, 필수 header 규칙은 수동 확인이 필요하다.

## HTTP 호출 예시

```bash
curl -i http://127.0.0.1:8000/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -H 'MCP-Protocol-Version: 2025-06-18' \
  --data '{"jsonrpc":"2.0","id":1,"method":"ping","params":{}}'
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

adapter smoke:

```bash
python3 scripts/smoke_mcp_adapter.py
```

HTTP smoke:

```bash
python3 scripts/smoke_http_server.py
```

auth smoke:

```bash
CHECKTIME_AUTH_MODE=bearer \
CHECKTIME_BEARER_TOKEN=local-test-token \
python3 scripts/smoke_http_server.py
```

origin smoke:

```bash
CHECKTIME_ALLOWED_ORIGINS=http://localhost:3000 \
python3 scripts/smoke_http_server.py
```

remote HTTPS smoke:

```bash
python3 scripts/smoke_http_server.py --base-url https://<DEPLOYED_HOST>/mcp --strict
```

remote HTTPS bearer smoke:

```bash
python3 scripts/smoke_http_server.py \
  --base-url https://<DEPLOYED_HOST>/mcp \
  --bearer-token <RUNTIME_OR_TEST_TOKEN> \
  --origin <CONFIRMED_ORIGIN_IF_NEEDED> \
  --strict
```

주의:

- `--bearer-token` 을 주면 local `CHECKTIME_AUTH_MODE` 값과 무관하게 `Authorization: Bearer <token>` 헤더를 보낸다.
- 설치형 runtime 과 Docker runtime 에서는 `CHECKTIME_MCP_DATA_DIR` 또는 working directory 기준 `data/` 가 유효해야 한다.

health/readiness:

```bash
PYTHONPATH=src python3 -m checktime_mcp.mcp_server --health
```

금지 표현 / 민감정보 유도 grep:

```bash
bash scripts/grep_risk_terms.sh
```

## Docker 실행 후보

build:

```bash
docker build -t checktime-mcp:local .
```

run:

```bash
docker run --rm -p 8080:8080 \
  -e CHECKTIME_AUTH_MODE=off \
  checktime-mcp:local
```

외부 terminal 에서 smoke:

```bash
python3 scripts/smoke_http_server.py --base-url http://127.0.0.1:8080/mcp
```

strict smoke:

```bash
python3 scripts/smoke_http_server.py --base-url http://127.0.0.1:8080/mcp --strict
```

bearer smoke:

```bash
python3 scripts/smoke_http_server.py \
  --base-url http://127.0.0.1:8080/mcp \
  --bearer-token <RUNTIME_OR_TEST_TOKEN> \
  --strict
```

Phase 2D 메모:

- Docker `tools/call` 실패 원인은 installed package runtime 에서 기본 data 경로가 site-packages 상위 `.../lib/pythonX.Y/data` 로 계산되던 점이다.
- Docker image 는 `CHECKTIME_MCP_DATA_DIR=/app/data` 를 기본 주입하고, app 은 working directory 기준 `data/` fallback 도 사용한다.
- remote HTTPS 배포 전에 위 Docker smoke를 먼저 통과시켜야 한다.

## PlayMCP 등록 전 남은 수동 단계

- 카카오 클라우드 MCP 서버 생성
- HTTPS endpoint 생성
- PlayMCP 개발자 콘솔 접근
- 등록 URL 형식 확인
- 최신 필수 필드 확인
- 인증 방식 확인
- bearer token 지원 여부 확인
- Origin / header / timeout 규칙 확인
- 임시 등록 테스트
- 최종 제출용 서버 심사 요청
- 심사 통과 후 전체 공개 전환
- Player 예선 최종 제출

## 안전 / 리스크 정책 요약

- 상세주소, 주민등록번호, 계좌번호, 신분증 이미지, 계약서 원문 입력 차단
- 모든 응답에 disclaimer 포함
- 금지 표현 출력 self-check 적용
- 공식 재검증이 끝나지 않은 일정/제도 항목은 `official_check_needed` 또는 `confirmation_required` 유지
- HTTP error response 에도 stack trace 와 민감정보 재노출 금지

## known limitations

- 현재 서버는 PlayMCP 임시 등록 전 로컬/HTTP preflight 후보 상태다.
- 실제 PlayMCP 등록, 실제 카카오 클라우드 배포, 심사 요청은 수행하지 않았다.
- GET 기반 SSE stream은 구현하지 않았다.
- PlayMCP 개발자 콘솔의 최신 필수 필드, transport 선택값, 인증 방식, timeout/header 규칙, 실제 Origin 값은 수동 확인이 필요하다.
- `generate_contract_day_checklist` 는 이번 Phase에서 구현하지 않았다.

관련 문서:

- [docs/IMPLEMENTATION_NOTES.md](/home/inno/repo/kakao_mcp_checktime/docs/IMPLEMENTATION_NOTES.md)
- [docs/PLAYMCP_PRECHECK.md](/home/inno/repo/kakao_mcp_checktime/docs/PLAYMCP_PRECHECK.md)
- [docs/DEPLOYMENT_NOTES.md](/home/inno/repo/kakao_mcp_checktime/docs/DEPLOYMENT_NOTES.md)
- [docs/TROUBLESHOOTING.md](/home/inno/repo/kakao_mcp_checktime/docs/TROUBLESHOOTING.md)
