# ASTM F38 기고 초안 — 군집 공역 관제 시험 방법 (Swarm Airspace Control Test Methods)

> **ODYSSEY Phase 461 산출물.** 상태: **DRAFT (제안 / proposed)** — ASTM Committee
> F38 (*Unmanned Aircraft Systems*) 채택 전. 본 문서는 기고 초안이며, 임계값은
> SDACS 실측 기준선과 문헌에 근거한 제안값입니다(채택된 표준 아님).

## 1. 범위 (Scope)

본 시험 방법은 **다수 무인기(군집)의 공역 통제(deconfliction) 시스템** 이 안전·
성능 요건을 충족하는지 평가하기 위한, 측정 가능하고 재현 가능한 합격 기준을
정의한다. 단일 기체의 비행 성능이 아니라 *기체 간 상호작용을 관제하는 계층* 의
적합성을 대상으로 한다.

기계 판정 가능한 부분(측정 지표 + 합격 기준)은 `simulation/swarm_test_method.py`
모듈에 결정적으로 인코딩되어, 동일한 시뮬레이션 산출 KPI 에 같은 정의로 같은
판정을 내릴 수 있다.

## 2. 의의 및 용도 (Significance and Use)

군집 관제 시스템은 충돌 회피·분리 유지·복귀 안전망이 *상호작용* 하므로, 단위
지표만으로는 적합성을 단언할 수 없다. 본 시험 방법은 핵심 안전·성능 차원을
서로소(orthogonal) 시험으로 분해해, 각 시험이 한 지표를 한 합격 기준으로 판정
하도록 한다. 적합(CONFORMANT) 판정은 **모든 시험 통과(all-or-nothing)** 를 요구
하며, 측정값 부재는 합격으로 처리하지 않는다(INCONCLUSIVE).

본 시험 방법은 Phase 465(표준 벤치마크 시나리오 스위트)·Phase 466(텔레메트리
오픈 데이터 스키마)와 3축을 이룬다: *무엇을 돌릴지(시나리오)* · *어떻게 기록할지
(데이터 포맷)* · **무엇을 합격으로 볼지(본 문서)**.

## 3. 시험 장치 (Apparatus)

- 결정적 시뮬레이션 엔진(`SwarmSimulator`) 또는 동등한 표준 벤치마크 러너.
- 표준 시나리오 셋(`SDACS-SBS-10`, Phase 465) 또는 합의된 운용 시나리오.
- 텔레메트리 기록은 Phase 466 표준 스키마를 충족.

## 4. 절차 (Procedure)

1. 합의된 시나리오 셋을 고정 시드로 실행한다(재현성 전제).
2. 각 시험 방법의 측정 지표(`metric_key`)를 산출 KPI 에서 수집한다.
3. 각 측정값을 해당 시험의 합격 기준(임계·방향)에 따라 판정한다.
4. 전체 시험 결과를 적합/부적합으로 종합한다.

## 5. 합격 기준 (Acceptance Criteria)

| ID | 시험 방법 | 지표 | 단위 | 합격 기준 | 근거 |
|---|---|---|---|---|---|
| SM-TM-01 | 군집 충돌 해결률 | `conflict_resolution_rate` | ratio | ≥ 0.95 | 1차 안전 지표. 해결률 = 1 − collisions/(conflicts+collisions) |
| SM-TM-02 | 공칭 밀도 무충돌 | `collisions` | count | ≤ 0 | 안전망 절대 하한 |
| SM-TM-03 | 수평 분리 유지 | `min_horizontal_separation_m` | m | ≥ 5.0 | 소형 멀티로터 보수적 분리 버블 |
| SM-TM-04 | 수직 분리 유지 | `min_vertical_separation_m` | m | ≥ 2.0 | 9층 고도 레이어(0~240m) 정합 |
| SM-TM-05 | 저배터리 복귀 성공률 | `rtb_success_rate` | ratio | ≥ 0.99 | 강하/회수 안전망 신뢰성 |
| SM-TM-06 | 평균 해소 지연 | `mean_time_to_deconflict_s` | s | ≤ 3.0 | 1Hz 컨트롤러 + 10Hz 드론 응답 예산 |
| SM-TM-07 | 결정적 재현성 | `reproducible` | bool | ≥ 1.0 | 동일 시드 → 동일 산출 |

> 충돌 해결률 공식은 SDACS 규약 `1 - collisions/(conflicts + collisions)` 와 일치
> (CLAUDE.md §8). 임계값은 **제안** 이며 SDACS 실측 고밀도 기준선 위로 설정.

## 6. 보고 (Report)

각 시험의 판정(PASS/FAIL/INCONCLUSIVE)·측정값·임계·방향과 종합 적합성을 기록
한다. 매니페스트(JSON)는 `--manifest`, 합격 기준표(Markdown)는 `--markdown` 로
출력한다.

## 7. 정직 공시 (Honest Disclosure)

- 본 시험 방법은 **ASTM 채택 전 제안(draft)** 이다. 모든 시험 항목은
  `proposed=True` 로 표시된다.
- 임계값은 SDACS 실측 기준선 + 문헌에 근거한 제안값으로, 위원회 합의 시 조정될
  수 있다.
- 측정값 부재는 합격이 아닌 INCONCLUSIVE 로 판정되어 거짓 적합을 차단한다.

## 8. CLI

```bash
python -m simulation.swarm_test_method --list       # 시험 방법 요약
python -m simulation.swarm_test_method --validate    # 레지스트리 정합성
python -m simulation.swarm_test_method --evaluate     # SDACS 기준선 판정 데모
python -m simulation.swarm_test_method --manifest     # 기고 매니페스트(JSON)
python -m simulation.swarm_test_method --markdown     # 합격 기준표(Markdown)
```
