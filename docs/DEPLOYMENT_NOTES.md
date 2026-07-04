# DEPLOYMENT NOTES

## 범위

이 문서는 로컬 MCP adapter를 배포 가능한 형태로 옮기기 위한 메모다. 실제 카카오 클라우드 배포와 실제 PlayMCP 등록은 이번 작업 범위가 아니다.

## 현재 서버 형태

- Python 3.11+
- 의존성 최소화
- `stdio` transport 지원
- HTTP POST 기반 MCP endpoint 후보 지원
- `GET /health` readiness check 지원
- 기본 host: `127.0.0.1`
- 기본 port: `8000`
- 기본 MCP path: `/mcp`

## 로컬 실행

```bash
PYTHONPATH=src python3 -m checktime_mcp.mcp_server --transport http --host 127.0.0.1 --port 8000
```

## Docker 실행

빌드:

```bash
docker build -t checktime-mcp:local .
```

실행:

```bash
docker run --rm -p 8000:8000 checktime-mcp:local
```

health 확인:

```bash
curl http://127.0.0.1:8000/health
```

## 권장 배포 전 점검

- `pytest`
- `python3 scripts/run_fixtures.py`
- `python3 scripts/smoke_mcp_adapter.py`
- `python3 scripts/smoke_http_server.py`
- `PYTHONPATH=src python3 -m checktime_mcp.mcp_server --health`

## 운영 전 확인 필요

- PlayMCP 개발자 콘솔의 최신 등록 필드
- PlayMCP가 요구하는 인증 방식
- Origin 검증 정책
- timeout / body size / concurrency 제한
- HTTPS termination 위치
- 로그에 민감정보가 남지 않는지 확인

## 주의

- 현재 HTTP 구현은 최소 adapter smoke test 목적이다.
- GET 기반 SSE stream은 미구현이다.
- 원격 공개 전에는 인증, Origin 검증, reverse proxy, timeout 정책 보강이 필요하다.
