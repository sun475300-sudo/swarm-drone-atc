# 해외 파일럿 제안서 적합성 게이트 (ODYSSEY Phase 411)

> Global Expansion 트랙(Phase 401-420) · 밴드 411-420("해외 파일럿 제안서 3종 —
> 아세안 도서 배송·EU U-space 데모·미국 대학 연구 협력")의 칸.
> 실행 가능 명세: [`simulation/overseas_pilot_proposal.py`](../../simulation/overseas_pilot_proposal.py)
> (본 문서는 규칙을 *서술*만 하며 판정 로직을 중복하지 않는다 — 진리표·요건의
> 유일 권위 출처는 모듈의 `CRITERIA`·`POLICY_MATRIX` 이고 테스트가 일치를 강제한다.)

## 1. 목적

SDACS 를 해외 현지에서 실증할 **파일럿 제안서**가 상대 관할·기관에 제출될 형식·
근거 요건을 갖췄는지를 사람이 매번 직관으로 점검하지 않도록 **결정적 게이트**로
명문화한다. 같은 제안서 상태는 항상 같은 판정을 낸다. 본 게이트는 제안서를
*제출하지 않는다* — 현 후보의 적합성만 판정한다(자문, 부수효과 0).

### 인접 모듈과의 경계 (중복 회피)

| 모듈 | 평가 대상 | 한 줄 |
|---|---|---|
| Phase 404 EN 완역 | 문서 산출물 자체 | "영문 문서가 있나" |
| Phase 405 국제 벤치마크 | 성능 비교 매트릭스(BlueSky·U-TRAFMAN) | "성능이 어떤가" |
| Phase 410 `gutma_contribution` | GUTMA 작업 항목 ↔ SDACS 자산 대응 | "무엇을 기여할 수 있나" |
| **Phase 411 `overseas_pilot_proposal`** | 특정 해외 실증 제안의 제출 준비도 | "이 제안서를 지금 보내도 되나" |

## 2. 요건 6종 (필수 4 · 권장 2)

각 기준은 추측이 아니라 해외 무인기 실증을 규율하는 공개 규제·관행에서 도출하고
명문 근거를 결속한다.

| ID | 심각도 | 요건 | 권위 근거 |
|---|---|---|---|
| **PP-01** | CRITICAL | 대상 관할의 규제 운영 근거 식별 | EASA 2019/947+U-space 2021/664 · FAA 14 CFR Part 107+COA/BEYOND · CAAS Unmanned Aircraft Act |
| **PP-02** | CRITICAL | 유스케이스 ↔ SDACS 기능 커버리지 | 제안 유스케이스를 뒷받침할 실재 기능 자산 필요 — 인용 모듈은 디스크 실재로 결속 |
| **PP-03** | CRITICAL | 현지 호스트/파트너 식별 | 해외 실증은 현지 책임 주체(보험·책임·현장 운용)가 필수 |
| **PP-04** | CRITICAL | 대상 언어(영문) 산출물 준비 | 상대 기관 작업 언어 산출물 없이는 접수·검토 불가(Phase 404 연계) |
| **PP-05** | RECOMMENDED | 데이터 거주·개인정보 적합 | EU GDPR 등 관할별 개인정보·데이터 이전 규율 |
| **PP-06** | RECOMMENDED | 자금·일정 계획 | 예산·마일스톤 명시가 실행 가능성·신뢰도 향상 |

각 기준의 충족 상태는 `MET` · `PARTIAL` · `UNMET` 셋 중 하나다.

## 3. 판정 규칙 (우선순위)

`POLICY_MATRIX` `(critical_unmet, critical_partial, any_incomplete) → verdict` 가
유일 권위 진리표이며 테스트(`test_policy_matrix_matches_assess`)가 `assess` 와
정확 일치를 강제한다.

1. CRITICAL 한 칸이라도 `UNMET` → **`NOT_READY`** (제출 부적합)
2. CRITICAL 미충족은 없으나 어떤 기준이든 MET 미만(CRITICAL PARTIAL 또는 권장
   PARTIAL/UNMET) → **`NEEDS_WORK`**
3. 전부 `MET` → **`READY_TO_PROPOSE`**

점수는 가중 충족 비율(필수 weight 2 · 권장 weight 1, `PARTIAL` = 절반, 소수
넷째 자리 반올림)로 결정적이다.

## 4. 현 후보 3종 정직 공시

`shipped_proposals()` 는 검토 중인 실제 후보 3종을 격상 없이 판정한다. **세
후보 모두 현지 호스트/파트너(PP-03) 미확보가 공통 CRITICAL 결격**이라 전부
`NOT_READY` 다 — 해외 실증의 실제 병목을 드러낸다.

| 제안 | 관할 | 판정 | 점수 | 주요 결격 |
|---|---|---|---|---|
| 아세안 도서 의약품 배송 | ASEAN | NOT_READY | 30% | PP-03·PP-04 미충족, PP-01 부분 |
| EU U-space 디컨플릭션 데모 | EU | NOT_READY | 55% | PP-03 미충족, PP-04 부분 |
| 미국 대학 UAS 연구 협력 | US | NOT_READY | 50% | PP-03 미충족, PP-01·PP-04 부분 |

기능 커버리지(PP-02)는 리포에 실재하는 모듈을 인용해 결속한다
(`test_shipped_module_refs_exist_on_disk` 가 디스크 실재 강제). `most_ready()` 는
가장 준비도가 높은 EU U-space 데모를 가리키나, PP-03 결격으로 여전히 제출
불가임을 동일하게 공시한다.

## 5. CLI

```bash
python -m simulation.overseas_pilot_proposal --criteria   # 요건 매트릭스
python -m simulation.overseas_pilot_proposal --status     # 현 후보 3종 판정
python -m simulation.overseas_pilot_proposal --policy     # 판정 진리표
python -m simulation.overseas_pilot_proposal --manifest   # JSON 매니페스트
```

## 6. 설계 불변식

- **자문이지 집행 아님** — 제안서를 제출하지 않는다(부수효과 0).
- **정직성 결속** — PP-02 MET/PARTIAL 후보는 실재 모듈을 인용해야 한다.
- **무작위성 0 · 결정적** — 같은 입력은 항상 같은 판정.
- **중복 로직 0** — 판정의 유일 명세는 코드, 본 문서는 서술만.
