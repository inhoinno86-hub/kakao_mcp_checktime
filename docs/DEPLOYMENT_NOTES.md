# DEPLOYMENT NOTES

이 문서는 로컬 MCP adapter 를 원격 HTTP endpoint 후보로 옮길 때의 준비 메모다. 이번 Phase는 `GET /mcp SSE Policy Smoke Alignment` 이며, 실제 카카오 클라우드 배포와 실제 PlayMCP 등록은 이번 작업 범위가 아니다.

## Phase 2E 범위

- 기존 Docker 검증이 완료된 MCP HTTP server 가 PlayMCP in KC 의 `Git 소스 빌드` 방식에 맞는지 점검
- 수동 등록 입력값 템플릿 문서화
- Endpoint URL 획득 후 remote smoke 절차 문서화
- 실제 PlayMCP 등록, 심사 요청, 전체 공개 전환은 미수행 유지

## local mode 실행

```bash
CHECKTIME_AUTH_MODE=off \
PYTHONPATH=src python3 -m checktime_mcp.mcp_server --transport http --host 127.0.0.1 --port 8000
```

health:

```bash
curl http://127.0.0.1:8000/health
```

## remote candidate mode 실행

```bash
CHECKTIME_AUTH_MODE=bearer \
CHECKTIME_BEARER_TOKEN=<set-at-runtime> \
CHECKTIME_ALLOWED_ORIGINS=<confirm-origin-before-use> \
CHECKTIME_REQUEST_TIMEOUT_SECONDS=10 \
CHECKTIME_MAX_BODY_BYTES=1048576 \
PORT=8080 \
PYTHONPATH=src python3 -m checktime_mcp.mcp_server --transport http --host 0.0.0.0
```

## 환경변수 목록

- `CHECKTIME_AUTH_MODE`
  - `off`
  - `bearer`
- `CHECKTIME_BEARER_TOKEN`
- `CHECKTIME_ALLOWED_ORIGINS`
- `CHECKTIME_REQUEST_TIMEOUT_SECONDS`
- `CHECKTIME_MAX_BODY_BYTES`
- `PORT`
- `CHECKTIME_MCP_DATA_DIR`

설치형 runtime 주의:

- `pip install .` 형태로 실행하면 기본 data 경로가 repo root 기준이 아닐 수 있다.
- Docker/runtime 에서는 `CHECKTIME_MCP_DATA_DIR=/app/data` 같이 명시 주입하는 편이 안전하다.

예시 템플릿:

- [`config/deployment.env.example`](/home/inno/repo/kakao_mcp_checktime/config/deployment.env.example)

## 포트 / path

- 기본 host: `127.0.0.1`
- 기본 port: `8000`
- remote candidate 예시 port: `8080`
- MCP path: `/mcp`
- health path: `/health`

## auth 설정

- local only: `CHECKTIME_AUTH_MODE=off`
- remote candidate: `CHECKTIME_AUTH_MODE=bearer`
- `Authorization: Bearer <token>` 불일치 시 요청 차단
- token 값은 문서, git, Docker image 에 직접 기록하지 않는다
- 실제 PlayMCP 인증 방식은 확인 필요

## origin 설정

예시:

```bash
CHECKTIME_ALLOWED_ORIGINS=https://playmcp.kakao.com,https://*.kakao.com
```

정책:

- allowlist 지정 시 `Origin` header 와 비교
- 불일치 시 `403`
- `Origin` header 가 없으면 현재는 server-to-server candidate 로 허용
- 실제 PlayMCP Origin 값은 확인 필요

## timeout / payload limit 설정

- `CHECKTIME_REQUEST_TIMEOUT_SECONDS`
  - 기본값 `10`
- `CHECKTIME_MAX_BODY_BYTES`
  - 기본값 `1048576`

운영 전에는 reverse proxy 와 app timeout 값을 함께 맞춘다.

## HTTP header 정책

`POST /mcp`

- `Content-Type: application/json`
- `Accept: application/json, text/event-stream`
- `MCP-Protocol-Version: 2025-06-18`

legacy fallback policy:

- `MCP-Protocol-Version` 미지정 시 `2025-03-26` 으로 간주

`GET /mcp`

- SSE 후보 경로
- `Accept: text/event-stream` 이 없으면 `406 unsupported_accept_header`
- `Accept: text/event-stream` 이 있으면 현재는 `405 sse_not_implemented`
- local Docker 와 PlayMCP in KC remote endpoint 에서 동일 정책 확인

`OPTIONS /mcp`

- `204`
- `Access-Control-Allow-Methods: POST, GET, OPTIONS`
- `Access-Control-Allow-Headers: Content-Type, Accept, Authorization, MCP-Protocol-Version`

## Docker build/run 후보

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

smoke:

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

메모:

- `--bearer-token` 은 local `CHECKTIME_AUTH_MODE` 와 무관하게 Authorization header 를 보낸다.
- remote HTTPS 배포 전에는 위 Docker smoke 를 선행한다.
- 현재 Codex 실행 환경에서는 `docker.sock` 권한 부족으로 위 명령을 재실행하지 못했다.

## PlayMCP in KC Git source build 적합성

확인 결과:

- `Dockerfile` 위치: 저장소 루트
- clean checkout build 전제 파일:
  - 포함: `pyproject.toml`, `README.md`, `src/`, `data/`
  - 미포함: `tests/`, `docs/`, `scripts/`
- 운영 runtime 에 필요한 데이터 경로는 `CHECKTIME_MCP_DATA_DIR=/app/data` 로 보강됨
- HTTP bind host 는 `0.0.0.0` 로 실행 가능
- listen port 는 `PORT` 환경변수 또는 기본 `8000`
- endpoint path 는 `/mcp`
- health path 는 `/health`
- auth off / bearer mode 둘 다 로컬 smoke 기준 PASS

해석:

- PlayMCP in KC 의 Git source build 는 Dockerfile 기반이므로, 문서/테스트 스크립트가 이미지 안에 없어도 배포 runtime 자체에는 문제가 없다.
- 다만 remote smoke 는 로컬 repo 의 `scripts/smoke_http_server.py` 로 외부에서 수행해야 한다.

official_check_needed:

- PlayMCP in KC 가 `Authorization` header 를 그대로 전달하는지
- `MCP-Protocol-Version` header 가 그대로 전달되는지
- `Content-Type` / `Accept` header 가 그대로 전달되는지
- proxy timeout 과 payload size 제한
- Endpoint URL 이 `/mcp` 를 포함하는지 여부
- 별도 health/readiness URL 접근 가능 여부

## PlayMCP in KC 등록 입력값 템플릿

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

- repository public/private 상태
- 실제 Git URL 사용 가능 여부
- PlayMCP in KC 에서 branch 대신 commit ref 지정이 필요한지 여부

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
10. private repo 면 PAT 를 사용자가 직접 입력
11. public repo 면 PAT 는 비움
12. `등록하기` 클릭
13. Status 가 `Starting` 에서 `Active` 로 바뀔 때까지 대기
14. 상세 정보에서 Endpoint URL 복사
15. Endpoint URL 로 remote smoke 수행

주의:

- MCP 서버는 최대 2개까지 등록 가능
- 불필요한 중복 생성 주의
- 삭제 후 복구 불가
- PAT, token, secret 은 문서와 로그에 기록 금지
- 실제 등록은 사용자 수동 단계

## health / smoke test 명령

```bash
PYTHONPATH=src python3 -m checktime_mcp.mcp_server --health
pytest
python3 scripts/run_fixtures.py
python3 scripts/smoke_mcp_adapter.py
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

remote smoke:

```bash
python3 scripts/smoke_http_server.py --base-url https://<DEPLOYED_HOST>/mcp --strict
```

remote bearer smoke:

```bash
python3 scripts/smoke_http_server.py \
  --base-url https://<DEPLOYED_HOST>/mcp \
  --bearer-token <RUNTIME_OR_TEST_TOKEN> \
  --origin <CONFIRMED_ORIGIN_IF_NEEDED> \
  --strict
```

Endpoint URL path 기준:

- Endpoint URL 이 host 까지만 주어지면 base-url 은 `<endpoint-url>/mcp`
- Endpoint URL 이 이미 `/mcp` 를 포함하면 그대로 사용

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

- missing token 에서는 `401` 또는 안전한 HTTP error
- invalid token 에서는 `401` 또는 `403` 과 같은 안전한 HTTP error
- token 원문, PAT, stack trace 는 response/log 에 노출되지 않음

## 로그 / 민감정보 원칙

- stack trace 를 외부 응답에 노출하지 않는다
- 주민등록번호, 계좌번호, 상세주소, 계약서 원문을 로그에 남기지 않는다
- token 을 로그에 남기지 않는다
- health/readiness 로 transport/security/limits 상태만 확인한다

## 배포 후 PlayMCP 임시 등록 전 확인 절차

1. HTTPS endpoint 로 `/health` 확인
2. remote smoke 로 `/mcp` 확인
3. `POST /mcp` initialize / ping / tools/list / tools/call 확인
4. `GET /mcp` without `Accept: text/event-stream` 는 `406`, with `Accept: text/event-stream` 는 `405` 인지 확인
5. `OPTIONS /mcp` preflight 확인
6. bearer / origin 값 확인
7. reverse proxy timeout / body limit 확인
8. PlayMCP 개발자 콘솔 필드 확인
9. 임시 등록 테스트

## 로그 확인 방법

- 로컬 직접 실행: stderr 의 `Serving MCP HTTP on ...` 확인
- Docker 사용 시: `docker logs <container>`
- Docker socket 권한이 없으면 `sudo docker ...` 또는 docker group 설정 상태를 먼저 확인한다
- 배포 플랫폼 사용 시: ingress / app log 에서 HTTP status 와 `Origin` 확인
- token, 주민등록번호, 계좌번호, 상세주소, 계약서 원문은 로그에 남기지 않는다

## rollback / config 변경 절차

- auth 문제면 `CHECKTIME_AUTH_MODE`, `CHECKTIME_BEARER_TOKEN` 만 먼저 조정
- origin 문제면 `CHECKTIME_ALLOWED_ORIGINS` 만 갱신 후 재배포
- timeout/body limit 문제면 `CHECKTIME_REQUEST_TIMEOUT_SECONDS`, `CHECKTIME_MAX_BODY_BYTES`, reverse proxy 제한을 함께 수정
- 기능 회귀가 아니면 코드 변경보다 config 조정을 우선
- Phase 2D 기준 Docker `tools/call` 실패의 주요 원인은 누락된 `CHECKTIME_MCP_DATA_DIR` 또는 잘못된 data path 였다

## 확인 필요

- PlayMCP 개발자 콘솔 최신 필수 필드
- PlayMCP 인증 방식
- PlayMCP bearer token 지원 여부
- PlayMCP Origin 규칙
- PlayMCP timeout / header 규칙
- PlayMCP payload size 제한
- 카카오 클라우드 권장 배포 방식
