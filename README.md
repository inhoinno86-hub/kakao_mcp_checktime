# kakao_mcp_checktime

`부동산 체크타임 MCP`의 로컬 검증 및 MCP adapter 준비 repo다.

현재 상태는 Phase 2H `PlayMCP Console Asset & Metadata Preparation` 단계다. 실제 PlayMCP 등록, 실제 PlayMCP in KC 서버 생성, 실제 카카오 클라우드 배포, 심사 요청, 전체 공개 전환, Player 예선 최종 제출은 수행하지 않았다.

Phase 2D baseline 로컬 검증은 PASS 상태를 유지했고, PlayMCP in KC remote endpoint에서도 local 과 동일한 `GET /mcp` 정책이 확인됐다. 이번 Phase에서는 서버 정책을 바꾸지 않고 representative image, MCP identifier 후보, conversation examples, auth 권장안과 기존 registration field 문서를 함께 정리했다.

관련 문서:

- [docs/PLAYMCP_CONSOLE_ASSETS.md](/home/inno/repo/kakao_mcp_checktime/docs/PLAYMCP_CONSOLE_ASSETS.md)
- [docs/PLAYMCP_REGISTRATION_FIELDS.md](/home/inno/repo/kakao_mcp_checktime/docs/PLAYMCP_REGISTRATION_FIELDS.md)
- [docs/PLAYMCP_PRECHECK.md](/home/inno/repo/kakao_mcp_checktime/docs/PLAYMCP_PRECHECK.md)

## 프로젝트 목적

- 부동산 계약 전후 체크리스트와 일정 후보를 `MCP tool` 형태로 노출
- 민감정보 차단, disclaimer 강제, 금지 표현 self-check 유지
- PlayMCP 임시 등록 전 MCP adapter / HTTP endpoint / smoke test / readiness 경로 준비

## 현재 구현 범위

- 로컬 tool runner CLI
- MCP JSON-RPC adapter
- stdio transport server
- HTTP `POST /mcp` 기반 Streamable HTTP 후보 endpoint
- `GET /mcp` without `Accept: text/event-stream` 시 `406`
- `GET /mcp` with `Accept: text/event-stream` 시 `405`
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

주의:

- `generate_required_documents` 의 현재 정상 응답 범위:
  - `home_purchase` + `buyer` -> `contract_day`, `after_contract`
  - `lease_jeonse` + `tenant` -> `before_move_in`
  - `lease_monthly` + `tenant` -> `before_move_in`
- 그 외 단계 조합은 성공 빈 배열 대신 `documents_not_ready` 오류를 반환한다.

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

- SSE 후보 경로다.
- `Accept: text/event-stream` 이 없으면 `406 unsupported_accept_header`
- `Accept: text/event-stream` 이 있으면 현재는 `405 sse_not_implemented`
- body exact match 대신 `ok: false`, `error.code`, `error.message` 중심으로 검증한다.
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

## PlayMCP in KC Git Source Deployment Readiness

이번 Phase는 PlayMCP 최종 등록이나 심사 요청이 아니라, `https://playmcp.kakaocloud.io` 의 `Git 소스 빌드` 방식으로 배포할 준비 상태를 점검하고 수동 등록 절차를 문서화하는 작업이다.

현재 확인된 적합성:

- 저장소 루트에 `Dockerfile` 이 있다.
- `Dockerfile` 은 `pyproject.toml`, `README.md`, `src/`, `data/` 를 이미지에 포함한다.
- 컨테이너 기본 환경변수로 `PORT=8080`, `CHECKTIME_MCP_DATA_DIR=/app/data` 를 주입한다.
- HTTP 서버는 `PORT` 환경변수를 읽고 기본 endpoint 를 `/mcp` 로 노출한다.
- `PYTHONPATH=src python3 -m checktime_mcp.mcp_server --health` 결과에서 `playmcp_registration_status: manual_step_required` 와 `ok: true` 를 확인했다.
- `.dockerignore` 는 `tests`, `docs`, `scripts` 를 제외한다. 운영 runtime 에 필요한 `src/` 와 `data/` 는 제외하지 않는다.

실행 한계:

- 현재 Codex 세션은 `docker.sock` 권한이 없어 Docker build/run 을 재실행하지 못했다.
- 따라서 Phase 2D의 Docker PASS 이력은 유지 문맥으로 취급하고, 이번 Phase에서는 Dockerfile/런타임 구조와 로컬 baseline PASS를 다시 확인했다.

## PlayMCP in KC 등록 입력값 템플릿

실제 등록은 사용자가 수동으로 수행한다. PAT, token, secret, 실제 endpoint URL 은 문서나 로그에 기록하지 않는다.

```text
MCP 서버 이름:
  checktime-mcp

설명:
  부동산 직거래 당사자를 위한 계약 전/후 체크리스트, 준비서류, 일정, 전문가 검토 포인트 안내용 MCP 서버입니다. 법률 판단, 계약서 작성, 거래 안전성 판단은 수행하지 않습니다.

Git URL:
  <user-confirmed-git-url>
  current remote candidate: https://github.com/inhoinno86-hub/kakao_mcp_checktime.git

브랜치 / ref:
  <user-confirmed-branch-or-main>
  current local branch: main

Dockerfile 경로:
  Dockerfile

PAT:
  public repository라면 비워둠
  private repository라면 사용자가 직접 입력
  문서/로그/보고서에는 절대 기록하지 않음
```

확인 필요:

- 현재 `origin` remote 는 잡혀 있지만, 실제 PlayMCP in KC 에서 사용할 Git URL 과 public/private 상태는 사용자가 최종 확인해야 한다.
- repository 가 private 이면 PAT 가 필요하다.
- repository 가 public 이면 PAT 는 비워둘 수 있다.

## PlayMCP in KC 수동 등록 절차

1. 브라우저에서 `https://playmcp.kakaocloud.io` 접속
2. PlayMCP 에 가입된 카카오 계정으로 로그인
3. `+ 새 MCP 서버 등록` 클릭
4. `Git 소스 빌드` 선택
5. MCP 서버 이름 입력
6. 설명 입력
7. Git URL 입력
8. 브랜치/ref 입력
9. Dockerfile 경로 입력
10. private repo 라면 PAT 를 사용자가 직접 입력
11. public repo 라면 PAT 는 비움
12. `등록하기` 클릭
13. Status 가 `Starting` 에서 `Active` 로 바뀔 때까지 대기
14. 상세 정보에서 Endpoint URL 복사
15. Endpoint URL 기준으로 remote smoke 수행

주의:

- MCP 서버는 최대 2개까지 등록 가능하므로 중복 생성에 주의한다.
- 삭제 후 복구 불가다.
- PAT, token, secret 은 문서와 로그에 남기지 않는다.
- Endpoint URL 은 공개 가능 여부를 판단한 뒤에만 공유한다.
- Endpoint URL 획득 후 PlayMCP 최종 등록 전에 smoke test 를 먼저 수행한다.

## Endpoint URL 획득 후 remote smoke

auth off candidate:

```bash
python3 scripts/smoke_http_server.py \
  --base-url '<endpoint-url>/mcp' \
  --strict
```

Endpoint URL 이 이미 `/mcp` 를 포함하는 경우:

- `https://example.playmcp...` 이면 base-url 은 `https://example.playmcp.../mcp`
- `https://example.playmcp.../mcp` 이면 base-url 은 그대로 사용

bearer candidate:

```bash
python3 scripts/smoke_http_server.py \
  --base-url '<endpoint-url-or-endpoint-url-with-mcp>' \
  --bearer-token '<deployment-token>' \
  --strict
```

명령 히스토리 노출을 줄이려면 env 사용:

```bash
export CHECKTIME_REMOTE_BASE_URL='<endpoint-url-or-endpoint-url-with-mcp>'
export CHECKTIME_REMOTE_BEARER_TOKEN='<deployment-token>'

python3 scripts/smoke_http_server.py \
  --base-url "$CHECKTIME_REMOTE_BASE_URL" \
  --bearer-token "$CHECKTIME_REMOTE_BEARER_TOKEN" \
  --strict
```

negative smoke 는 bearer mode endpoint 에서만 수행:

```bash
python3 scripts/smoke_http_server.py \
  --base-url "$CHECKTIME_REMOTE_BASE_URL" \
  --strict
```

```bash
python3 - <<'PY'
import json
import os
import urllib.request
import urllib.error

url = os.environ["CHECKTIME_REMOTE_BASE_URL"]

payload = json.dumps({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {}
}).encode("utf-8")

req = urllib.request.Request(
    url,
    data=payload,
    method="POST",
    headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
        "MCP-Protocol-Version": "2025-06-18",
        "Authorization": "Bearer invalid-token"
    },
)

try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        print("status", resp.status)
        print(resp.read().decode("utf-8", errors="replace"))
except urllib.error.HTTPError as exc:
    print("HTTPError", exc.code)
    print(exc.read().decode("utf-8", errors="replace"))
except Exception as exc:
    print(type(exc).__name__, exc)
PY
```

기대 결과:

- connection reset 이 아니라 `401` 또는 안전한 HTTP error
- response 에 token 원문 노출 없음
- log 에 token 원문 노출 없음
- stack trace 노출 없음

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
- 실제 PlayMCP 등록, 실제 PlayMCP in KC 서버 생성, 실제 카카오 클라우드 배포, 심사 요청은 수행하지 않았다.
- GET 기반 SSE stream은 구현하지 않았다.
- PlayMCP 개발자 콘솔의 최신 필수 필드, transport 선택값, 인증 방식, timeout/header 규칙, 실제 Origin 값은 수동 확인이 필요하다.
- Endpoint URL 획득 전에는 remote smoke 를 수행할 수 없다.
- `Authorization`, `MCP-Protocol-Version`, `Content-Type`, `Accept`, timeout, payload size, `/mcp` path 처리 방식은 PlayMCP in KC 에서 `official_check_needed` 상태다.
- `generate_contract_day_checklist` 는 이번 Phase에서 구현하지 않았다.

관련 문서:

- [docs/IMPLEMENTATION_NOTES.md](/home/inno/repo/kakao_mcp_checktime/docs/IMPLEMENTATION_NOTES.md)
- [docs/PLAYMCP_REGISTRATION_FIELDS.md](/home/inno/repo/kakao_mcp_checktime/docs/PLAYMCP_REGISTRATION_FIELDS.md)
- [docs/PLAYMCP_PRECHECK.md](/home/inno/repo/kakao_mcp_checktime/docs/PLAYMCP_PRECHECK.md)
- [docs/DEPLOYMENT_NOTES.md](/home/inno/repo/kakao_mcp_checktime/docs/DEPLOYMENT_NOTES.md)
- [docs/TROUBLESHOOTING.md](/home/inno/repo/kakao_mcp_checktime/docs/TROUBLESHOOTING.md)
