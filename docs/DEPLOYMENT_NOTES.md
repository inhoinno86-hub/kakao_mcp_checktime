# DEPLOYMENT NOTES

이 문서는 로컬 MCP adapter 를 원격 HTTP endpoint 후보로 옮길 때의 준비 메모다. 실제 카카오 클라우드 배포와 실제 PlayMCP 등록은 이번 작업 범위가 아니다.

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

- `Accept: text/event-stream`
- 현재는 SSE 미구현으로 `405`

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

## 로그 / 민감정보 원칙

- stack trace 를 외부 응답에 노출하지 않는다
- 주민등록번호, 계좌번호, 상세주소, 계약서 원문을 로그에 남기지 않는다
- token 을 로그에 남기지 않는다
- health/readiness 로 transport/security/limits 상태만 확인한다

## 배포 후 PlayMCP 임시 등록 전 확인 절차

1. HTTPS endpoint 로 `/health` 확인
2. remote smoke 로 `/mcp` 확인
3. `POST /mcp` initialize / ping / tools/list / tools/call 확인
4. `GET /mcp` 가 SSE 미지원이면 `405` 인지 확인
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
