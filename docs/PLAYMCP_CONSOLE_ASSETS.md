# PlayMCP Console Asset & Metadata Preparation

## 1. Status

- Phase: `KAKAO_MCP Phase 2H - PlayMCP Console Asset & Metadata Preparation`
- Repository: `inhoinno86-hub/kakao_mcp_checktime`
- Prepared date: `2026-07-05` (Asia/Seoul)
- Actual registration: not performed
- Review request: not performed
- Public release: not performed
- Scope note: 이번 Phase는 PlayMCP Console Asset & Metadata Preparation 작업이다.

필수 사실 유지:

- 실제 PlayMCP 등록은 수행하지 않았다.
- 심사 요청은 수행하지 않았다.
- 전체 공개 전환은 수행하지 않았다.
- `generate_contract_day_checklist`는 구현하지 않았다.

## 2. Representative Image

- Purpose: PlayMCP 홈/상세 화면용 대표 이미지 준비
- Source file: [`assets/playmcp/checktime-representative.svg`](/home/inno/repo/kakao_mcp_checktime/assets/playmcp/checktime-representative.svg)
- Export file: [`assets/playmcp/checktime-representative.png`](/home/inno/repo/kakao_mcp_checktime/assets/playmcp/checktime-representative.png)
- Build script: [`scripts/generate_playmcp_assets.py`](/home/inno/repo/kakao_mcp_checktime/scripts/generate_playmcp_assets.py)
- Size: `1024x1024`
- Format:
  - source: `svg`
  - export: `png`
- Design intent:
  - 집 + 체크리스트 + 문서/일정 보드 조합으로 "생활형 계약 준비 도구" 인상을 준다.
  - 법률 사무소, 중개사무소, 보증/안전 인증 마크처럼 보이지 않도록 단순 product icon 스타일로 유지한다.
  - 텍스트는 `Checktime MCP`만 사용해 과한 브랜딩이나 확정적 표현을 피한다.

## 3. MCP Identifier Candidates

MCP 식별자는 영문/숫자만 허용되므로 camelCase 후보로 정리한다.

| Candidate | Recommended | Reason | Notes |
|---|---|---|---|
| `checktimeMCP` | yes | 서비스명 연결성이 높고 tool prefix로 붙여도 짧고 읽기 쉽다. | repo slug `checktime-mcp`와도 자연스럽게 연결된다. |
| `realEstateChecktime` | no | 서비스 도메인을 더 직접적으로 드러낸다. | 길이가 더 길고 tool prefix로 반복될 때 다소 무겁다. |
| `checktimeChecklist` | no | 체크리스트 중심 인상을 준다. | 일정/캘린더/오늘 할 일 범위를 충분히 담지 못한다. |
| `propertyChecktime` | no | 영어권 표현으로는 이해 가능하다. | 현재 한글 서비스명과 repo 문맥에서 상대적으로 이질적이다. |

최종 권장안: `checktimeMCP`

선정 사유:

- `checktime` 핵심 브랜드를 유지한다.
- tool prefix로 붙였을 때 길이가 과하지 않다.
- 너무 일반적인 단어 하나만 쓰는 경우보다 중복 가능성을 줄인다.
- 영문/숫자 조건을 만족한다.

예시 prefix:

- `checktimeMCP_generatePreContractChecklist`
- `checktimeMCP_getTodayTasks`

## 4. Conversation Examples

1. "전세 계약 전에 임차인 입장에서 확인할 체크리스트를 정리해줘."
2. "월세 계약일이 2026-07-20일일 때 계약 후 챙길 일정 후보를 캘린더 기준으로 정리해줘."
3. "매매 계약을 준비 중인 매수인 입장에서 필요한 서류와 오늘 우선 확인할 일, 전문가에게 다시 물어볼 포인트를 알려줘."

내부 매핑 메모:

- 예시 1 -> `generate_pre_contract_checklist`
- 예시 2 -> `generate_post_contract_timeline` 또는 `generate_calendar_items`
- 예시 3 -> `generate_required_documents` + `get_today_tasks` + `flag_expert_review_points`

## 5. Authentication Setting Recommendation

현재 기술적 관찰:

- remote strict smoke에서 `https://checktime-mcp.playmcp-endpoint.kakaocloud.io/mcp` endpoint가 bearer token 없이 PASS했다.
- repo에는 `off` / `bearer` auth mode 후보 구현이 모두 존재한다.
- OAuth 인증 흐름은 현재 repo에 구현되어 있지 않다.

콘솔 선택지별 판단:

| Console option | Repo 기준 판단 | Notes |
|---|---|---|
| 인증 사용하지 않음 | 권장 | 현재 remote strict smoke 관찰과 가장 잘 맞는다. |
| OAuth 인증 | 비권장 | 현재 구현 없음. 이번 등록 후보 범위 밖이다. |
| Key/Token 인증 방식 | 보류 | repo에는 bearer candidate가 있지만 현재 공개 endpoint 관찰과는 다르다. 운영 정책 변경 시 재검토 가능하다. |

권장안:

- 현재 등록 검증 단계 권장 설정은 `인증 사용하지 않음`

근거:

- 현재 공개 endpoint는 bearer token 없이 strict smoke를 통과했다.
- PlayMCP 콘솔 auth 의미와 운영 정책은 별도일 수 있으므로, 문서상 권장안은 "현재 관찰된 동작 기준"으로만 제시한다.

추후 변경 가능성:

- 운영 정책상 인증이 필요해지면 `Key/Token 인증 방식`으로 전환 검토 가능
- OAuth 인증은 구현 전까지 선택하지 않음

## 6. How To Use In PlayMCP Console

1. 대표 이미지로 [`assets/playmcp/checktime-representative.png`](/home/inno/repo/kakao_mcp_checktime/assets/playmcp/checktime-representative.png) 업로드
2. MCP 식별자에 `checktimeMCP` 입력
3. 대화 예시 3개를 그대로 입력
4. 인증 방식은 현재 검증 기준으로 `인증 사용하지 않음` 선택
5. endpoint/transport 세부값은 [docs/PLAYMCP_REGISTRATION_FIELDS.md](/home/inno/repo/kakao_mcp_checktime/docs/PLAYMCP_REGISTRATION_FIELDS.md) 기준으로 입력
6. 등록 후 `tools/list` 와 대표 `tools/call` 1건 이상 수동 확인

## 7. Notes / Limitations

- 이번 문서는 실제 등록 완료 상태를 의미하지 않는다.
- 대표 이미지는 등록 가능한 최소 품질 자산을 repo에 남기는 목적이다.
- 콘솔 UI의 최종 필드명, validation, prefix 노출 형식은 수동 확인이 필요하다.
- 대화 예시는 현재 구현된 tool 범위만 반영했다.
- 법률 판단, 세무 판단, 거래 안전성 판단, 민감정보 입력 유도 문구는 포함하지 않는다.
