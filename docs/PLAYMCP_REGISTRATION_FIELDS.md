# PlayMCP Registration Field Verification

## 1. Status

- Phase: `KAKAO_MCP Phase 2G - PlayMCP Registration Field Verification Wrap-up`
- Repository: `inhoinno86-hub/kakao_mcp_checktime`
- Endpoint: `https://checktime-mcp.playmcp-endpoint.kakaocloud.io/mcp`
- Verification date: `2026-07-05` (Asia/Seoul)
- Actual registration: not performed
- Review request: not performed
- Public release: not performed
- Scope note: 이번 Phase는 PlayMCP Registration Field Verification 작업이다.

필수 사실 유지:

- 실제 PlayMCP 등록은 수행하지 않았다.
- 심사 요청은 수행하지 않았다.
- 전체 공개 전환은 수행하지 않았다.
- `generate_contract_day_checklist`는 구현하지 않았다.

Phase 2H console asset / metadata 준비 문서는 [docs/PLAYMCP_CONSOLE_ASSETS.md](/home/inno/repo/kakao_mcp_checktime/docs/PLAYMCP_CONSOLE_ASSETS.md) 를 기준으로 추가 관리한다.

## 2. Candidate Registration Fields

PlayMCP 콘솔의 실제 필드명과 선택지는 repo에서 확정할 수 없으므로, 아래는 repo 기준 후보값이다.

| Field | Candidate Value | Source | Confidence | Notes |
|---|---|---|---|---|
| Service name | `부동산 체크타임 MCP` | `README.md`, disclaimer text, tool scope | high | user-facing 이름 후보 |
| English/system name | `checktime-mcp` | `README.md`, deployment docs | high | slug 또는 internal display 후보 |
| One-line summary | 주택 매매·전세·월세 계약 준비용 체크리스트와 타임라인을 제공하는 MCP 서버 | `README.md`, `docs/PLAYMCP_PRECHECK.md` | high | timeline 중심 가치가 드러나도록 조정 |
| Detailed description | 주택 매매·전세·월세 계약을 준비하는 매수인과 임차인을 위한 MCP 서버. 계약 전 확인사항, 계약 후 일정 후보, 오늘 확인할 일, 전문가 재확인 포인트를 JSON-RPC MCP tool로 제공하며, 날짜가 입력되면 `timeline_checklist` 와 `action_timeline` 형태로 계약일·입주일·잔금일 기준의 due-date 감각이 보이도록 정리한다. 준비서류 tool은 현재 일부 단계 조합만 지원한다. 민감정보 입력을 차단하며 법률, 세무, 중개, 거래 안전성 판단은 제공하지 않음. | `README.md`, `src/checktime_mcp/mcp_adapter.py`, `src/checktime_mcp/guardrails.py` | high | 등록 설명 후보 |
| Category | `official_check_needed` | repo-only | low | PlayMCP 콘솔 실제 카테고리/옵션 미확인 |
| Endpoint URL | `https://checktime-mcp.playmcp-endpoint.kakaocloud.io/mcp` | user-provided remote smoke result, remote recheck | high | 현재 remote smoke 통과 URL |
| Transport | `POST /mcp` JSON-RPC 2.0, Streamable HTTP candidate | `README.md`, `src/checktime_mcp/mcp_server.py`, `src/checktime_mcp/mcp_adapter.py` | high | 실제 콘솔 transport 필드명은 `official_check_needed` |
| Protocol version | `2025-06-18` | `src/checktime_mcp/mcp_adapter.py`, smoke tests | high | strict smoke 기준. legacy fallback는 local/server policy |
| Auth mode | current remote endpoint behaves as no-bearer-required endpoint | remote strict smoke recheck | medium | strict smoke가 token 없이 PASS. 콘솔 최종 auth 선택값은 `manual_console_check_needed` |
| Representative image | `assets/playmcp/checktime-representative.png` | repo asset | high | `1024x1024` PNG, source SVG 별도 보관 |
| MCP identifier recommendation | `checktimeMCP` | Phase 2H console asset doc | high | 영문/숫자 only candidate |
| Conversation examples | see console asset doc | Phase 2H console asset doc | high | 콘솔 입력용 3개 문구 준비 |
| Health URL | `https://checktime-mcp.playmcp-endpoint.kakaocloud.io/health` | server convention, smoke health/readiness path | medium | remote strict smoke에서 health/readiness PASS. 직접 공개 문서 필드 여부는 `manual_console_check_needed` |
| Developer / owner field | `manual_console_check_needed` | console-only | low | 콘솔 UI 확인 필요 |
| Visibility / public release field | `manual_console_check_needed` | console-only | low | 이번 Phase에서 전체 공개 전환 미수행 |
| Review submission field | `manual_console_check_needed` | console-only | low | 이번 Phase에서 심사 요청 미수행 |

## 3. Service Summary Candidate

`부동산 체크타임 MCP`는 주택 매매·전세·월세 계약을 준비하는 매수인과 임차인이 계약 전후에 챙겨야 할 체크리스트, 준비서류, 일정 후보, 오늘 확인할 일, 전문가 재확인 포인트를 확인할 수 있도록 돕는 MCP 서버 후보 구현이다.

## 4. Detailed Description Candidate

이 서버는 `POST /mcp` JSON-RPC 2.0 endpoint에서 `tools/list` 와 `tools/call` 을 제공한다. 현재 구현된 tool은 계약 전 체크리스트, 계약 후 일정, 준비서류, 캘린더 항목, 전문가 검토 포인트, 오늘 해야 할 일 후보 생성이다. 날짜가 입력되면 계약 전 체크리스트와 준비서류는 `timeline_checklist` 로, 계약 후 일정은 `action_timeline` 으로도 함께 반환되어 계약일·입주일·잔금일 기준의 due-date 감각이 보이도록 정리된다. 준비서류 tool은 현재 `home_purchase/buyer` 의 `contract_day`, `after_contract` 와 `lease_jeonse·lease_monthly/tenant` 의 `before_move_in` 단계만 정상 응답을 보장한다. 입력은 거래 유형, 사용자 역할, 날짜, 단계, 문맥 태그 등 최소 구조화 필드만 허용하며, 상세주소, 주민등록번호, 계좌번호, 계약서 원문 같은 민감정보는 입력 단계에서 차단한다. 이 서버는 법률 판단, 세무 판단, 중개, 거래 안전성 판단, 계약서 작성, 계약서 원문 분석을 수행하지 않는다.

## 5. Endpoint / Transport

- Primary endpoint: `https://checktime-mcp.playmcp-endpoint.kakaocloud.io/mcp`
- Health endpoint convention: `GET /health`
- MCP request method: `POST /mcp`
- Payload format: JSON-RPC 2.0
- Required request headers for normal MCP POST:
  - `Content-Type: application/json`
  - `Accept: application/json, text/event-stream`
  - `MCP-Protocol-Version: 2025-06-18`
- GET policy:
  - `GET /mcp` without `Accept: text/event-stream` -> `406 unsupported_accept_header`
  - `GET /mcp` with `Accept: text/event-stream` -> `405 sse_not_implemented`
- SSE status: not implemented
- Stdio transport: implemented in repo, but registration 대상 후보는 HTTP endpoint
- Console transport label / option names: `official_check_needed`

## 6. Tool Inventory

`tools/list` 기준 현재 노출 tool은 6개다.

| Tool Name | Purpose | Input Summary | Output Summary | Status |
|---|---|---|---|---|
| `generate_pre_contract_checklist` | 계약 전 확인 항목 후보 반환 | `transaction_type`, `user_role`, optional `contract_date`, `move_in_date`, `region` | `items`, `case`, disclaimer, unknowns, expert review points | implemented |
| `generate_post_contract_timeline` | 계약 후 일정 후보 계산 | `transaction_type`, `user_role`, optional `contract_date`, `closing_date`, `move_in_date`, `lease_end_date` | `timeline_items`, `case`, disclaimer, unknowns, expert review points | implemented |
| `generate_required_documents` | 단계별 준비서류 후보 반환 | `transaction_type`, `user_role`, `stage`, optional milestone dates | `documents`, `case`, disclaimer, unknowns, expert review points | implemented, supported stages limited to `home_purchase/buyer -> contract_day, after_contract`, `lease_jeonse·lease_monthly/tenant -> before_move_in` |
| `generate_calendar_items` | 타임라인을 캘린더 입력용 항목으로 변환 | `transaction_type`, `user_role`, optional `contract_date`, `move_in_date`, `closing_date`, `calendar_style` | `calendar_items`, `case`, disclaimer, unknowns, expert review points | implemented |
| `flag_expert_review_points` | 문맥 태그 기반 전문가 재확인 포인트 반환 | `transaction_type`, `user_role`, `context` | `expert_review_points`, `case`, disclaimer, unknowns | implemented |
| `get_today_tasks` | 오늘 해야 할 일과 임박 일정 후보 반환 | `transaction_type`, `user_role`, `current_date`, optional milestone dates | `today_tasks`, `upcoming_deadlines`, `case`, disclaimer, unknowns, expert review points | implemented |

미구현 tool:

- `generate_contract_day_checklist`: not implemented

입력 예시:

```json
{
  "transaction_type": "lease_jeonse",
  "user_role": "tenant",
  "contract_date": "2026-07-12",
  "move_in_date": "2026-08-10",
  "region": "seoul_songpa"
}
```

출력 예시 shape:

```json
{
  "ok": true,
  "data": {
    "items": [],
    "case": {}
  },
  "disclaimer": "...",
  "source_status_summary": "service_curated",
  "unknowns": [],
  "expert_review_points": []
}
```

## 7. Guardrail / Safety Boundary

- 입력 차단 대상:
  - 주민등록번호
  - 상세주소
  - 계좌번호
  - 신분증 이미지
  - 계약서 원문
  - 계약 문서 파일 업로드
  - 실명 기반 민감 계약정보
  - 등기부 전체 원문
  - 계약서 전체 조항 원문
- 허용 입력 범위:
  - 거래 유형
  - 사용자 역할
  - 날짜
  - 단계
  - 시/군/구 수준 지역
  - 일정 계산용 문맥 태그
- 금지 표현 denylist self-check 유지: `src/checktime_mcp/guardrails.py`
- 사용자가 기대할 수 있는 범위:
  - 체크리스트 후보
  - 일정 후보
  - 준비서류 후보
  - 오늘 할 일 후보
  - 전문가 재확인 포인트
- 사용자가 기대하면 안 되는 범위:
  - 거래 안전성 판단
  - 계약 진행 승인
  - 법률 결론
  - 세무 결론
  - 계약서 작성/검토 대행
  - 중개/매칭

## 8. Privacy Boundary

- 서버가 요구하지 않는 정보:
  - 주민등록번호
  - 상세주소
  - 계좌번호
  - 신분증 이미지
  - 계약서 원문
- 입력 스키마는 최소 구조화 필드만 허용한다.
- 민감정보 감지 시 `sensitive_input_detected` 오류를 반환한다.
- 오류 응답은 민감정보를 재노출하지 않는 방향으로 설계돼 있다.
- 개인정보 저장, 계약 문서 파일 업로드 처리, 문서 원문 분석은 이번 repo 범위 밖이다.

## 9. Non-goals

- 실제 PlayMCP 등록
- 심사 요청
- 전체 공개 전환
- Player 예선 최종 제출
- PlayMCP in KC 서버 삭제/재생성
- Kakao Tools Widget 구현
- 톡캘린더 직접 연동
- 카카오맵 연동
- 외부 부동산 API 연동
- 실시간 법령 API 연동
- 개인정보 저장
- 계약서 자동 작성
- 법률 판단
- 세무 판단
- 중개/매칭
- 매물 추천
- 거래 안전성 판단
- 보증금 보호 가능성 판단
- `generate_contract_day_checklist` 구현

## 10. Smoke Verification

Local verification on `2026-07-05`:

- `pytest` -> PASS (`23 passed`)
- `python3 scripts/run_fixtures.py` -> PASS
- `python3 scripts/smoke_mcp_adapter.py` -> PASS (`tools/list -> 6 tools`)
- `python3 scripts/smoke_http_server.py` -> PASS
- `python3 scripts/smoke_http_server.py --strict` -> PASS
- `PYTHONPATH=src python3 -m checktime_mcp.mcp_server --health` -> `ok: true`

Remote verification on `2026-07-05`:

- `python3 scripts/smoke_http_server.py --base-url 'https://checktime-mcp.playmcp-endpoint.kakaocloud.io/mcp' --strict` -> PASS
- `GET /mcp` without SSE `Accept` -> `406 unsupported_accept_header`
- `GET /mcp` with `Accept: text/event-stream` -> `405 sse_not_implemented`
- remote smoke summary:
  - `initialize`, `ping`, `tools/list`, `tools/call`: PASS
  - sensitive input denied: PASS
  - invalid date denied: PASS
  - invalid JSON / unknown method / unsupported headers: PASS
  - health/readiness: PASS

## 11. Manual Console Checklist

- 콘솔 실제 필드명 확인
- 카테고리 선택지 확인
- transport 선택지 이름 확인
- auth 선택지 이름 확인
- review / publish 관련 버튼과 상태명 확인
- endpoint 입력 방식이 host-only 인지 `/mcp` 포함 full URL 인지 확인
- health endpoint 별도 요구 여부 확인
- `MCP-Protocol-Version` 값 또는 console-side override 요구 여부 확인
- PlayMCP 콘솔에서 `initialize` 테스트 로그 위치 확인
- PlayMCP 콘솔에서 `tools/list` / `tools/call` 결과 확인 위치 확인
- 필요 시 bearer token 입력 필드 존재 여부 확인
- Origin allowlist 요구 여부와 실제 Origin 값 확인
- timeout / payload size / retry 정책 확인
- 공개 전환 단계와 심사 요청 단계가 분리되어 있는지 확인

## 12. Known Limitations

- `GET /mcp` SSE stream은 구현하지 않았다.
- `generate_contract_day_checklist`는 구현하지 않았다.
- PlayMCP 콘솔 최신 필드명과 카테고리 체계는 repo에서 확인할 수 없다.
- remote endpoint의 현재 auth 동작은 smoke 기준 추정이며, 콘솔 최종 설정값과 1:1 매핑된다고 단정할 수 없다.
- bearer auth, strict Origin allowlist, Docker remote smoke는 이번 Phase에서 필수 완결 범위가 아니다.
- 법률/세무/중개/거래 안전성 판단은 제공하지 않는다.

## 13. Final Registration Precheck

- endpoint URL이 실제 등록 화면 기대 형식과 일치하는지 확인
- `POST /mcp` 기준 JSON-RPC 호출이 콘솔 테스트에서 실제로 성공하는지 확인
- `tools/list` 에서 6개 tool이 노출되는지 확인
- representative `tools/call` 1건 이상 성공 확인
- 민감정보 입력 차단 응답이 콘솔 경유 호출에서도 유지되는지 확인
- health/readiness 정책이 운영 경로에서 유지되는지 확인
- 실제 등록 전 문서 후보값을 콘솔 실필드에 맞게 마지막 보정
- review request / public release 버튼은 누르지 않기

## 14. Console Asset Linkage

- 대표 이미지, MCP 식별자 후보, 대화 예시 3개, auth 권장안은 [docs/PLAYMCP_CONSOLE_ASSETS.md](/home/inno/repo/kakao_mcp_checktime/docs/PLAYMCP_CONSOLE_ASSETS.md) 를 사용한다.
- 등록 필드값의 상세 근거와 endpoint/transport/tool inventory는 이 문서를 유지 기준으로 삼는다.
