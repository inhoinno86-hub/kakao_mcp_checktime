# PLAYMCP PRECHECK

이 문서는 PlayMCP 임시 등록 직전의 로컬 preflight 체크리스트다. 이번 Phase는 `PlayMCP in KC Git Source Deployment Readiness` 이며, 실제 PlayMCP 등록, 실제 PlayMCP in KC 서버 생성, 실제 카카오 클라우드 배포, 실제 심사 요청은 이번 작업 범위가 아니다.

## 현재 상태

- 로컬 MCP adapter smoke 결과: PASS
- 로컬 HTTP endpoint smoke 결과: PASS
- Streamable HTTP 후보 구현 상태: candidate
- `POST /mcp` 지원 상태: implemented
- `GET /mcp` SSE 미지원 상태: `405 Method Not Allowed`
- `OPTIONS /mcp` 상태: implemented
- `Accept` header 처리 상태: implemented
- `Content-Type` 처리 상태: implemented
- `MCP-Protocol-Version` 처리 상태:
  - `2025-06-18` 지원
  - header 미지정 시 legacy fallback policy 적용
  - 그 외 최신 PlayMCP 필수값은 확인 필요
- Origin allowlist 상태: implemented as candidate
- Auth mode 상태: `off` / `bearer` candidate
- timeout / payload size limit 상태: implemented as candidate
- Docker 실행 후보: 문서화 완료
- PlayMCP in KC Git source build 입력값 템플릿: 문서화 완료
- PlayMCP in KC 수동 등록 절차: 문서화 완료
- 실제 PlayMCP 등록: 미수행
- 실제 PlayMCP in KC 서버 생성: 미수행
- 실제 카카오 클라우드 배포: 미수행
- 실제 심사 요청: 미수행
- 전체 공개 전환: 미수행

## 로컬 검증 명령

```bash
pytest
python3 scripts/run_fixtures.py
python3 scripts/smoke_mcp_adapter.py
python3 scripts/smoke_http_server.py
PYTHONPATH=src python3 -m checktime_mcp.mcp_server --health
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

## Streamable HTTP 후보 체크리스트

- `POST /mcp`
  - `initialize`: PASS
  - `ping`: PASS
  - `tools/list`: PASS
  - `tools/call`: PASS
  - 민감정보 입력 차단: PASS
  - 잘못된 날짜 형식 차단: PASS
  - invalid JSON 처리: PASS
  - unknown method 처리: PASS
  - missing `id` 처리: notification policy `202 Accepted`
  - unsupported `Content-Type`: PASS
  - unsupported `Accept`: PASS
  - unsupported `MCP-Protocol-Version`: PASS
- `GET /mcp`
  - `Accept: text/event-stream` -> `405`
  - `sse_get_stream: not_implemented`
- `OPTIONS /mcp`
  - preflight candidate 응답 구현

## transport / security / limits

환경변수:

- `CHECKTIME_AUTH_MODE`
- `CHECKTIME_BEARER_TOKEN`
- `CHECKTIME_ALLOWED_ORIGINS`
- `CHECKTIME_REQUEST_TIMEOUT_SECONDS`
- `CHECKTIME_MAX_BODY_BYTES`
- `CHECKTIME_MCP_DATA_DIR`

정책:

- local mode 에서는 `CHECKTIME_AUTH_MODE=off`
- remote candidate mode 에서는 `CHECKTIME_AUTH_MODE=bearer` 권장
- `Origin` header 가 있으면 allowlist 와 비교
- `Origin` header 가 없으면 현재는 server-to-server candidate 로 허용
- request timeout 기본값 `10`
- body size 기본값 `1048576`

remote candidate 예시:

```bash
CHECKTIME_AUTH_MODE=bearer \
CHECKTIME_BEARER_TOKEN=<set-at-runtime> \
CHECKTIME_ALLOWED_ORIGINS=<confirm-origin-before-use> \
CHECKTIME_REQUEST_TIMEOUT_SECONDS=10 \
CHECKTIME_MAX_BODY_BYTES=1048576 \
PORT=8080 \
PYTHONPATH=src python3 -m checktime_mcp.mcp_server --transport http --host 0.0.0.0
```

## Docker 실행 후보

```bash
docker build -t checktime-mcp:local .
docker run --rm -p 8080:8080 -e CHECKTIME_AUTH_MODE=off checktime-mcp:local
python3 scripts/smoke_http_server.py --base-url http://127.0.0.1:8080/mcp
python3 scripts/smoke_http_server.py --base-url http://127.0.0.1:8080/mcp --strict
python3 scripts/smoke_http_server.py --base-url http://127.0.0.1:8080/mcp --bearer-token <RUNTIME_OR_TEST_TOKEN> --strict
```

주의:

- Codex 실행 환경에서 Docker build/run 가능 여부는 별도 확인 필요
- token 은 Docker image 에 bake 하지 않는다
- remote HTTPS 배포 전에 Docker smoke 를 먼저 통과시킨다

## 카카오 클라우드 배포 전 확인 사항

- 카카오 클라우드 MCP 서버 생성 필요
- HTTPS endpoint 준비 필요
- reverse proxy / ingress timeout 정책 확인 필요
- 로그에 민감정보가 남지 않는지 확인 필요
- 환경변수 주입 방식 확인 필요

## PlayMCP in KC Git source build 입력값 후보

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

confirmation_required:

- Git remote URL 의 실제 사용 가능 여부
- repository public/private 상태
- PAT 필요 여부

## PlayMCP in KC 수동 등록 절차

1. `https://playmcp.kakaocloud.io` 접속
2. PlayMCP 가입 카카오 계정으로 로그인
3. `+ 새 MCP 서버 등록` 클릭
4. `Git 소스 빌드` 선택
5. MCP 서버 이름 입력
6. 설명 입력
7. Git URL 입력
8. 브랜치/ref 입력
9. Dockerfile 경로 입력
10. private repo 라면 PAT 입력
11. public repo 라면 PAT 비움
12. `등록하기` 클릭
13. Status 가 `Starting` 에서 `Active` 로 바뀔 때까지 대기
14. 상세 정보에서 Endpoint URL 확인
15. Endpoint URL 기준 remote smoke 수행

주의:

- MCP 서버는 최대 2개까지 등록 가능
- 삭제 후 복구 불가
- PAT/token/secret 은 문서와 로그에 기록 금지
- 실제 등록과 Endpoint URL 획득은 사용자 수동 단계

## PlayMCP 개발자 콘솔에서 확인할 항목

- 최신 필수 입력 필드: 확인 필요
- 등록 URL 형식: 확인 필요
- 필수 transport 유형: 확인 필요
- 필수 protocol version: 확인 필요
- 인증 방식: 확인 필요
- bearer token 지원 여부: 확인 필요
- 필수 request header: 확인 필요
- `Accept` header 처리 방식: 확인 필요
- `Content-Type` 요구사항: 확인 필요
- 필수 header 규칙: 확인 필요
- timeout 규칙: 확인 필요
- Origin 규칙: 확인 필요
- payload size 제한: 확인 필요
- `MCP-Protocol-Version` 요구값: 확인 필요
- CORS/preflight 요구사항: 확인 필요
- `tools/list` 호출 방식: 확인 필요
- `tools/call` 호출 방식: 확인 필요
- health endpoint 요구 여부: 확인 필요
- 로그 또는 테스트 결과 확인 위치: 확인 필요
- 임시 등록 후 전체 공개 전환 조건: 확인 필요
- 심사 요청 조건: 확인 필요
- 제출 1회 제한 관련 주의사항: 확인 필요

## HTTPS endpoint smoke 절차

1. `https://<DEPLOYED_HOST>/health` 응답 확인
2. `python3 scripts/smoke_http_server.py --base-url https://<DEPLOYED_HOST>/mcp --strict` 실행
3. bearer auth 사용 시 아래 명령으로 재검증

```bash
python3 scripts/smoke_http_server.py \
  --base-url https://<DEPLOYED_HOST>/mcp \
  --bearer-token <RUNTIME_OR_TEST_TOKEN> \
  --origin <CONFIRMED_ORIGIN_IF_NEEDED> \
  --strict
```

4. `GET /mcp` 가 SSE 미지원이면 `405` 인지 확인
5. `OPTIONS /mcp` 가 `204` 인지 확인
6. JSON-RPC error response 에 stack trace 가 없는지 확인
7. 민감정보 입력 차단 응답이 유지되는지 확인

Endpoint URL path 규칙:

- Endpoint URL 이 `https://example.playmcp...` 이면 base-url 은 `https://example.playmcp.../mcp`
- Endpoint URL 이 `https://example.playmcp.../mcp` 이면 그대로 사용

bearer endpoint env 예시:

```bash
export CHECKTIME_REMOTE_BASE_URL='<endpoint-url-or-endpoint-url-with-mcp>'
export CHECKTIME_REMOTE_BEARER_TOKEN='<deployment-token>'

python3 scripts/smoke_http_server.py \
  --base-url "$CHECKTIME_REMOTE_BASE_URL" \
  --bearer-token "$CHECKTIME_REMOTE_BEARER_TOKEN" \
  --strict
```

negative smoke:

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
- response/log 에 token 원문 노출 없음
- stack trace 노출 없음

## PlayMCP in KC header / origin / timeout 확인 항목

- `Authorization` header 전달 여부: `official_check_needed`
- `MCP-Protocol-Version` header 전달 여부: `official_check_needed`
- `Content-Type` / `Accept` header 전달 여부: `official_check_needed`
- `CHECKTIME_ALLOWED_ORIGINS` 를 비워둘지 특정 Origin 만 허용할지: `confirmation_required`
- PlayMCP 호출 Origin 값: `official_check_needed`
- proxy timeout 이 `tools/call` 응답 시간보다 충분한지: `official_check_needed`
- payload size limit 이 서버 설정과 충돌하지 않는지: `official_check_needed`
- Endpoint URL 뒤에 `/mcp` 를 붙여야 하는지: `confirmation_required`
- health/readiness URL 을 별도 확인할 수 있는지: `official_check_needed`

## PlayMCP 임시 등록 전 체크리스트

1. 카카오 클라우드 또는 동등한 HTTPS endpoint 준비
2. HTTPS 적용 확인
3. `POST /mcp` smoke 확인
4. `GET /mcp` 405 또는 SSE 동작 확인
5. `OPTIONS /mcp` 확인
6. health/readiness 확인
7. auth mode 결정
8. Origin allowlist 결정
9. PlayMCP 개발자 콘솔 접근
10. MCP 서버 등록 URL 입력
11. 인증 방식 입력 또는 확인
12. protocol/header 요구사항 확인
13. timeout 제한 확인
14. `tools/list` 확인
15. `tools/call` 확인
16. 민감정보 차단 확인
17. 에러 응답 확인
18. 임시 등록 결과 기록
19. 실패 시 원인 분류
20. 최종 심사 요청 전 남은 작업 정리

실패 시 원인 분류 후보:

- HTTPS/TLS
- endpoint path 오기입
- `Accept` / `Content-Type` / `MCP-Protocol-Version` 불일치
- auth mismatch
- Origin mismatch
- timeout / payload limit
- GET SSE 요구 여부
- PlayMCP 콘솔 필수 필드 누락

## 최종 심사 요청 전 남은 작업

- 실제 배포
- 실제 PlayMCP 임시 등록
- 콘솔 요구값 재확인
- remote smoke test
- 최종 제출용 서버 심사 요청
- 심사 통과 후 전체 공개 전환
- Player 예선 최종 제출
- 제출 1회 제한 주의

## 현재 한계

- PlayMCP 개발자 콘솔 최신 필수 필드: 확인 필요
- PlayMCP 인증 방식: 확인 필요
- PlayMCP bearer token 지원 여부: 확인 필요
- PlayMCP timeout/header 규칙: 확인 필요
- PlayMCP in KC Git source build console 의 상태 화면에서 `Starting -> Active` 전환 시간: 확인 필요
- 정확한 PlayMCP Origin 값: 확인 필요
- remote HTTPS endpoint 준비: 미완료
- Docker build/run: 현재 Codex 실행 환경에서는 `docker.sock` 권한 부족으로 재검증 못 함
- SSE stream 구현: 미구현
- 실제 카카오 클라우드 배포: 미수행
- 실제 PlayMCP 임시 등록: 미수행
- 실제 심사 요청: 미수행
- 전체 공개 전환: 미수행
- `generate_contract_day_checklist`: 미구현
