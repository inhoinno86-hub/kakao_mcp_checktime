# TROUBLESHOOTING

이 문서는 `부동산 체크타임 MCP` Streamable HTTP 후보 endpoint의 로컬/원격 preflight 진단 메모다. 실제 PlayMCP 등록 결과와 카카오 클라우드 동작은 별도 수동 확인이 필요하다.

## POST /mcp 415

- 증상: `POST /mcp` 가 `415 Unsupported Media Type` 반환
- 가능 원인: `Content-Type: application/json` 누락 또는 다른 타입 사용
- 확인 명령: `curl -i https://<HOST>/mcp -H 'Content-Type: text/plain' -H 'Accept: application/json, text/event-stream' --data '{}'`
- 해결 후보: `Content-Type: application/json` 고정
- 확인 필요 항목: PlayMCP가 추가 `Content-Type` 파라미터를 붙이는지 여부

## POST /mcp 406

- 증상: `POST /mcp` 가 `406 Not Acceptable` 반환
- 가능 원인: `Accept` 에 `application/json, text/event-stream` 둘 다 없거나 일부만 존재
- 확인 명령: `curl -i https://<HOST>/mcp -H 'Content-Type: application/json' -H 'Accept: application/json' --data '{"jsonrpc":"2.0","id":1,"method":"ping","params":{}}'`
- 해결 후보: 클라이언트가 두 MIME type을 모두 보내도록 조정
- 확인 필요 항목: PlayMCP 콘솔 또는 gateway가 실제로 보내는 `Accept` 값

## POST /mcp 400 unsupported protocol version

- 증상: `unsupported_protocol_version`
- 가능 원인: `MCP-Protocol-Version` 값 불일치
- 확인 명령: `curl -i https://<HOST>/mcp -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -H 'MCP-Protocol-Version: 2024-11-05' --data '{"jsonrpc":"2.0","id":1,"method":"ping","params":{}}'`
- 해결 후보: `2025-06-18` 사용, 또는 초기화 후 협상값과 일치시키기
- 확인 필요 항목: PlayMCP의 최신 요구 protocol version

## GET /mcp 405

- 증상: `GET /mcp` 가 `405 Method Not Allowed` 반환
- 가능 원인: 현재 서버는 SSE stream 미구현
- 확인 명령: `curl -i https://<HOST>/mcp -H 'Accept: text/event-stream'`
- 해결 후보: 현재 후보 구현에서는 `405` 를 정상 후보 동작으로 취급
- 확인 필요 항목: PlayMCP가 GET SSE를 필수로 요구하는지 여부

## OPTIONS /mcp 실패

- 증상: preflight 가 `204` 가 아니거나 CORS 헤더가 비어 있음
- 가능 원인: reverse proxy가 `OPTIONS` 를 차단, origin allowlist 불일치
- 확인 명령: `curl -i -X OPTIONS https://<HOST>/mcp -H 'Origin: https://example.com'`
- 해결 후보: upstream 에 `OPTIONS` 전달, origin allowlist 수정
- 확인 필요 항목: PlayMCP 실제 Origin 값과 preflight 사용 여부

## 401 unauthorized

- 증상: `Authorization header is required`
- 가능 원인: `CHECKTIME_AUTH_MODE=bearer` 이고 토큰 미전달
- 확인 명령: `python3 scripts/smoke_http_server.py --base-url https://<HOST>/mcp --bearer-token <TOKEN> --skip-origin-negative`
- 해결 후보: runtime secret 주입, header 전달 경로 확인
- 확인 필요 항목: PlayMCP가 bearer auth를 지원하는지 여부

## 403 forbidden origin

- 증상: `forbidden_origin`
- 가능 원인: `CHECKTIME_ALLOWED_ORIGINS` 불일치
- 확인 명령: `python3 scripts/smoke_http_server.py --base-url https://<HOST>/mcp --origin https://wrong.example`
- 해결 후보: 실제 허용 origin만 allowlist 에 추가
- 확인 필요 항목: PlayMCP 또는 중간 gateway가 보내는 정확한 `Origin`

## payload too large

- 증상: `413` 또는 `payload_too_large`
- 가능 원인: `CHECKTIME_MAX_BODY_BYTES` 보다 큰 body
- 확인 명령: `python3 scripts/smoke_http_server.py --base-url https://<HOST>/mcp`
- 해결 후보: payload 축소, proxy/body limit 정렬
- 확인 필요 항목: PlayMCP payload size 제한

## request timeout

- 증상: `408` 또는 `request_timeout`
- 가능 원인: app timeout, proxy timeout, cold start, upstream stall
- 확인 명령: `/health` 의 `limits.request_timeout_seconds` 확인, proxy timeout 설정 확인
- 해결 후보: 앱과 reverse proxy timeout 값을 함께 조정
- 확인 필요 항목: PlayMCP request timeout 제한

## tools/list 실패

- 증상: `tools/list` 에서 빈 결과 또는 오류
- 가능 원인: 초기화 누락, path 오기입, protocol/header 불일치
- 확인 명령: `python3 scripts/smoke_http_server.py --base-url https://<HOST>/mcp --strict`
- 해결 후보: `initialize` -> `tools/list` 순서와 header 재검증
- 확인 필요 항목: PlayMCP 내부 테스트가 initialization 순서를 강제하는지 여부

## tools/call 실패

- 증상: `tools/call` 에서 `isError` 또는 JSON-RPC 오류
- 가능 원인: tool 이름 오타, 입력 schema 불일치, guardrail 차단
- 확인 명령: `python3 scripts/smoke_mcp_adapter.py` 와 `python3 scripts/smoke_http_server.py`
- 해결 후보: tool name / arguments / fixture 재검증
- 확인 필요 항목: PlayMCP가 tool input validation 에 추가 제약을 두는지 여부

## Docker RemoteDisconnected / ConnectionResetError

- 증상: Docker 에서는 `initialize` / `ping` / `tools/list` 까지 통과한 뒤 `tools/call` 에서 연결이 끊기거나 bearer smoke 초기에 실패
- 가능 원인 1: installed package runtime 이 repo root 대신 site-packages 상위 경로를 기본 data dir 로 계산
- 가능 원인 2: smoke client 가 `--bearer-token` 을 받았지만 Authorization header 를 보내지 않음
- 확인 명령:
  - `python3 -m venv .tmp && . .tmp/bin/activate && pip install -q . && python -c "from checktime_mcp.data_loader import get_data_dir; print(get_data_dir())"`
  - `python3 scripts/smoke_http_server.py --base-url http://127.0.0.1:8080/mcp --bearer-token <TOKEN> --strict`
- 해결 후보:
  - runtime 에 `CHECKTIME_MCP_DATA_DIR=/app/data` 주입
  - app 에 working directory 기준 `data/` fallback 유지
  - smoke client 는 `--bearer-token` 지정 시 Authorization header 를 항상 전송
- 확인 필요 항목: Docker daemon 권한이 없으면 `sudo docker` 또는 docker group 설정 필요

## PlayMCP에서 endpoint 접근 실패

- 증상: 콘솔 테스트 또는 임시 등록 단계에서 endpoint 연결 실패
- 가능 원인: HTTPS 미적용, 외부 공개 안 됨, DNS/방화벽 문제, 헤더 mismatch
- 확인 명령: `curl -i https://<HOST>/health` 와 `curl -i https://<HOST>/mcp -H 'Accept: text/event-stream'`
- 해결 후보: 공개 DNS, TLS, ingress, header 정책, auth 정책 재확인
- 확인 필요 항목: PlayMCP 콘솔의 최신 접근 테스트 방식과 실패 로그 위치

## HTTPS 인증서 문제

- 증상: TLS handshake 실패 또는 인증서 경고
- 가능 원인: 자체 서명 인증서, 체인 누락, 만료
- 확인 명령: `curl -Iv https://<HOST>/health`
- 해결 후보: 공인 인증서, 중간 체인, hostname 일치 확인
- 확인 필요 항목: PlayMCP가 특정 TLS 정책을 요구하는지 여부

## Origin mismatch

- 증상: 브라우저/console 경유 요청에서만 실패
- 가능 원인: 문서에 적은 예시 origin 과 실제 요청 origin 불일치
- 확인 명령: 서버 access log 또는 reverse proxy header log에서 `Origin` 확인
- 해결 후보: 추정값 대신 실측 origin 으로 allowlist 갱신
- 확인 필요 항목: PlayMCP 실제 origin, gateway 재작성 여부

## Bearer token mismatch

- 증상: `403` 또는 `Authorization token mismatch`
- 가능 원인: deploy secret 과 테스트 secret 혼용, prefix 누락
- 확인 명령: `python3 scripts/smoke_http_server.py --base-url https://<HOST>/mcp --bearer-token <TOKEN> --skip-origin-negative`
- 해결 후보: runtime secret 재주입, `Bearer ` prefix 포함 여부 확인
- 확인 필요 항목: PlayMCP bearer token 입력 필드 존재 여부

## Docker container port mismatch

- 증상: 컨테이너는 실행되지만 `curl` 또는 smoke가 연결 실패
- 가능 원인: host mapping 과 내부 `PORT` 불일치
- 확인 명령: `docker run --rm -p 8080:8080 checktime-mcp:local` 후 `curl http://127.0.0.1:8080/health`
- 해결 후보: 내부 `PORT=8080`, host `-p 8080:8080` 정렬
- 확인 필요 항목: 실제 배포 플랫폼이 `PORT` 환경변수를 강제하는지 여부

## server bind host 문제

- 증상: 로컬에서는 동작하지만 외부에서 접근 불가
- 가능 원인: `127.0.0.1` 에만 bind
- 확인 명령: 실행 로그의 `Serving MCP HTTP on ...` 확인
- 해결 후보: remote candidate 는 `--host 0.0.0.0`
- 확인 필요 항목: 실제 배포 플랫폼의 ingress/bind 제약

## health/readiness 실패

- 증상: `/health` 가 실패하거나 `ok: false`
- 가능 원인: data 파일 누락, guardrail self-check 실패, 배포 경로 오기입
- 확인 명령: `PYTHONPATH=src python3 -m checktime_mcp.mcp_server --health`
- 해결 후보: data 파일 포함 여부, `CHECKTIME_MCP_DATA_DIR` 경로, 배포 artifact 확인
- 확인 필요 항목: PlayMCP가 별도 health endpoint 를 요구하는지 여부
