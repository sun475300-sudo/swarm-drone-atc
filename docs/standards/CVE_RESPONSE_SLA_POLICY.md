# CVE 대응 SLA + 핀 갱신 정책 (ODYSSEY Phase 488)

> 보안 장기 지원(Continuum 트랙). 취약점(CVE) 한 건이 들어왔을 때 *얼마나 급히
> 대응하고, 의존성 핀(`requirements.lock.txt`)을 갱신해야 하는가* 를 결정적
> 정책으로 명문화한다. 본 문서는 규칙을 **서술**할 뿐, 유일한 실행 가능 명세는
> `simulation/cve_response_policy.py` 다(중복 로직 없음 — 테스트가 일치 강제).

## 위치

- 정책 엔진: [`simulation/cve_response_policy.py`](../../simulation/cve_response_policy.py)
- 테스트: [`tests/test_cve_response_policy.py`](../../tests/test_cve_response_policy.py)
- 기준선 근거: [`SECURITY.md`](../../SECURITY.md)
- 자매 정책: [`simulation/dependency_gate.py`](../../simulation/dependency_gate.py) (Phase 481 — 기능 갱신 자동 머지)

## 자문이지 집행 아님

본 정책은 대응을 **권고**할 뿐, 핀을 실제로 갱신하거나 배포하지 않는다(부수효과 0).
사람/CI 가 결정을 집행한다. 같은 입력은 항상 같은 결정을 낸다(무작위성 0).

## 입력

| 필드 | 의미 |
|---|---|
| `cve_id` | CVE 식별자 |
| `package` | 영향 받는 패키지/액션 |
| `cvss_score` | CVSS v3.1 기반 점수 `[0.0, 10.0]` |
| `exposure` | `runtime`(실제 임포트·핀 대상) · `dev`(개발/테스트/빌드) · `archived`(은퇴 코드) |
| `fix_available` | 상류에 수정 버전이 존재하는지 |
| `fixed_version` | 수정 버전(있으면) — 핀 갱신 절차 근거 |

## CVSS v3.1 정성 등급 (NVD 표준 절단점)

| 점수 | 등급 |
|---|---|
| 0.0 | NONE |
| 0.1 – 3.9 | LOW |
| 4.0 – 6.9 | MEDIUM |
| 7.0 – 8.9 | HIGH |
| 9.0 – 10.0 | CRITICAL |

## SLA (접수 확인 / 해결 시한, 일)

`SECURITY.md` 의 명시 약속(외부 접수 확인 7일·해결 시한 14일)을 **HIGH 내부
기준선**으로 삼고, 심각도에 따라 단조 가감한다. HIGH 의 해결 14일이 SECURITY.md
상한과 일치한다.

| 유효 심각도 | 접수 확인 | 해결 시한 |
|---|:-:|:-:|
| CRITICAL | 1일 | 7일 |
| HIGH | 3일 | 14일 |
| MEDIUM | 7일 | 30일 |
| LOW | 14일 | 90일 |
| NONE | — | — (SLA 없음) |

**노출 차등**: 개발 전용(`dev`) 노출은 프로덕션 경로가 아니므로 유효 심각도를
한 단계 강등해 대응한다(공급망 위험은 남으므로 무시하지 않고 완화만). SLA 는
강등 반영 *유효* 등급 기준으로 계산한다.

## 결정 매트릭스 (수정 버전 존재 전제 · archived → OUT_OF_SCOPE)

| 심각도 | runtime | dev |
|---|---|---|
| CRITICAL | PATCH_NOW (1/7) | PATCH_NOW (3/14) |
| HIGH | PATCH_NOW (3/14) | SCHEDULED (7/30) |
| MEDIUM | SCHEDULED (7/30) | SCHEDULED (14/90) |
| LOW | SCHEDULED (14/90) | MONITOR (SLA 없음) |
| NONE | MONITOR | MONITOR |

> `LOW · dev` 는 강등 바닥(유효 NONE)에 도달해 긴급도가 소멸하므로 MONITOR 로
> 처리한다(SLA·핀 갱신 없음 — NONE 경로와 일관).

## 결정 우선순위 (먼저 매칭되는 규칙이 결과)

1. **archived 노출 → `OUT_OF_SCOPE`** — `SECURITY.md` "Out of Scope"(은퇴 phase/`archive/`). SLA·핀 갱신 없음.
2. **severity NONE → `MONITOR`** — 정보성. SLA·핀 갱신 없음.
3. **dev 강등으로 유효 심각도 NONE → `MONITOR`** — 긴급도 소멸.
4. **유효 심각도 CRITICAL/HIGH → `PATCH_NOW`**.
5. **그 외(MEDIUM/LOW) → `SCHEDULED`**.

## 핀 갱신 절차 (`requirements.lock.txt`)

`pin_refresh_required = True` 는 **상류 수정 버전이 존재하고**(`fix_available`)
노출이 핀 대상(`runtime`·`dev`)일 때만 참이다. 상류 수정이 없으면 핀을 올릴 수
없으므로 사람이 완화책을 적용하고 패치를 추적한다(긴급도는 유지).

핀 갱신이 필요할 때 절차는 `requirements.lock.txt` 헤더 규약을 따른다:

1. `requirements.txt` 의 해당 항목을 수정 버전(`fixed_version`)으로 올린다.
2. `bash scripts/reproduce/make_lock.sh` 로 `requirements.lock.txt` 재생성.
3. 두 파일을 **같은 커밋**에 담는다(헤더 규약).
4. Phase 481(`dependency_gate`) 회귀 게이트 통과를 확인하고 집행한다.

## CLI

```bash
python -m simulation.cve_response_policy --policy     # 정책 매트릭스 출력
python -m simulation.cve_response_policy --demo       # 예시 평가
python -m simulation.cve_response_policy --manifest   # 정책 매니페스트(JSON)
```
