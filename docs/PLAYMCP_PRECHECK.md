# PLAYMCP PRECHECK

이 문서는 PlayMCP 임시 등록 직전의 로컬 preflight 체크리스트다. 실제 PlayMCP 등록, 실제 카카오 클라우드 배포, 실제 심사 요청은 이번 작업 범위가 아니다.

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
- 실제 PlayMCP 등록: 미수행
- 실제 카카오 클라우드 배포: 미수행
- 실제 심사 요청: 미수행

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
- 정확한 PlayMCP Origin 값: 확인 필요
- remote HTTPS endpoint 준비: 미완료
- Docker build/run: 현재 Codex 실행 환경에서는 `docker` 명령 부재로 미검증 가능성 있음
- SSE stream 구현: 미구현
- 실제 카카오 클라우드 배포: 미수행
- 실제 PlayMCP 임시 등록: 미수행
- 실제 심사 요청: 미수행
- `generate_contract_day_checklist`: 미구현
