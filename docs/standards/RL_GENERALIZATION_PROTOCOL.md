# RL 일반화 평가 프로토콜 적합성 게이트 — ODYSSEY Phase 452

SDACS 의 강화학습(RL) 구성요소가 *미학습 시나리오로의 일반화* 를 검증하는 데 필요한
**평가 프로토콜 요소** 를 어디까지 갖췄는가를 단계 축으로 정렬해 판정하는 기준 문서입니다.
정본 데이터는 `simulation/rl_generalization_protocol.py` 가 보유하며, 본 문서는 그 요약과
활용 맥락을 제공합니다. ODYSSEY Track 🔬 Formal & Research Frontier(451-460,
"RL 일반화 연구 + 인증 가능 ML 조사")의 두 번째 산출물입니다.

> **정직 공시**: 본 게이트는 *프로토콜 준비도* 의 자가 평가이며, RL 정책이 실제로
> 일반화함을 **증명하지 않습니다**. 게이트가 `PROTOCOL_READY` 라도 그것은 "평가할
> 도구가 갖춰졌다" 일 뿐 "정책이 일반화한다" 가 아닙니다 — 준비도와 결과는 독립입니다.
> 일반화 평가 프로토콜은 451-460 트랙의 **미해결 프런티어** 이므로 본 평가는 의도적으로
> 보수적입니다. 낮은 점수는 결함이 아니라 인증 가능 ML 경로의 현 위치를 정직하게
> 보고하는 것입니다.

## 자매 Phase 451 과의 관계

Phase 451(`easa_ai_conformance`)이 *EASA 신뢰 가능 AI* 축에서 핵심 연구 갭 —
`learning_process_verification`("미학습 시나리오 전이(일반화) 검증 프로토콜 없음 —
451-460 트랙의 핵심 연구 갭") — 을 **한 줄로 선언** 했다면, 본 Phase 452 는 *그 빠진
프로토콜이 정확히 어떤 요소로 이루어지며 각 요소가 현 리포에 있는가* 를 차원으로 분해해
판정합니다. 두 모듈은 `parent_gap_traceability` 요소로 역참조 연결됩니다.

## 근거 (권위 있는 출처)

- **Cobbe et al., "Quantifying Generalization in Reinforcement Learning"**
  (ICML 2019) — 학습/평가 환경을 분리된 집합으로 나누고(train/test split) 미학습
  레벨에서 *일반화 갭* 을 정량화하는 방법론.
- **EASA Learning Assurance 목표 LA:LM-03**(Learning process verification /
  generalisation) — 자매 451 이 `gap` 으로 공시한 바로 그 목표이자 본 게이트의 최상위
  추적 대상.

## 프로토콜 단계 (5종)

| 단계 id | 라벨 |
|---|---|
| `evaluation_design` | train/test 분리·held-out 시나리오 |
| `distribution_shift` | 분포 이동 스트레스·sim2real |
| `statistical_rigor` | 다중 시드·신뢰구간·검정력 |
| `baseline_grounding` | 결정적 기준선(APF) 대비·ablation |
| `generalization_analysis` | 일반화 갭·최악 케이스·OOD |

## 프로토콜 상태 (3값)

- `established` (가중 1.0) — 구비, 실재 모듈 근거 필수
- `partial` (가중 0.5) — 부분 구비, 실재 모듈 근거 필수
- `absent` (가중 0.0) — 부재, **근거 모듈 없음(None)**

`absent` ⟺ `evidence is None` 정직성 결속을 dataclass `__post_init__` 가 강제하며,
인용한 모든 경로의 디스크 실재를 테스트(`test_cited_evidence_exists_on_disk`)가 강제합니다.

## 종합 판정 (정직성 결속의 핵심)

`protocol_readiness()` 는 서로소 3단계로 판정합니다:

| 판정 | 조건 |
|---|---|
| `PROTOCOL_READY` | 기반(필수) 요소 **전부** established |
| `PARTIAL_PROTOCOL` | 기반 요소 **일부** established |
| `NO_PROTOCOL` | 기반 요소 **0개** established |

**핵심 정직성 결속:** 유일하게 established 인 요소는 *갭 추적성 자체*
(`parent_gap_traceability`, 비-기반)입니다. 즉 SDACS 가 지금 한 일은 *프로토콜을 갖춘
것* 이 아니라 *프로토콜이 없음을 정직하게 목록화한 것* 뿐입니다. 따라서 종합 판정은
기반 요소가 하나도 established 가 아니면 추적성이 established 여도 `NO_PROTOCOL` 로
고정합니다 — **갭을 카탈로그한 것이 갭을 메운 것으로 둔갑하지 못하게** 막습니다.

## 현 리포 판정 (스냅샷)

| 지표 | 값 |
|---|---|
| 종합 판정 | **NO_PROTOCOL** (기반 0/6 구비) |
| 가중 점수 | **27%** (구비 1 · 부분 6 · 부재 8 / 총 15) |
| 기반(필수) 요소 | **0/6** 구비 (0%) |

단계별 (구비/부분/부재):

| 단계 | 구비 | 부분 | 부재 |
|---|:-:|:-:|:-:|
| evaluation_design | 0 | 1 | 2 |
| distribution_shift | 0 | 2 | 1 |
| statistical_rigor | 0 | 2 | 1 |
| baseline_grounding | 0 | 1 | 1 |
| generalization_analysis | **1** | 0 | 3 |

## 핵심 해석

- **현 established 항목은 갭 추적성(`parent_gap_traceability`) 하나뿐** 이고, 이는
  비-기반입니다. 따라서 종합 판정이 `NO_PROTOCOL` 로 정직히 고정됩니다.
- **부분 구비(partial) 6건은 모두 인프라 재사용 후보** 입니다: 표준 시나리오 스위트
  (`standard_scenarios.py`), 도메인 무작위화(`domain_rand.py`), sim2real 갭
  (`sim_real_gap.py`), 신뢰구간(`uncertainty.py`), 검정력(`power_analysis.py`),
  결정적 APF 기준선(`apf_lyapunov.py`). 일반화 평가 프로토콜은 *새 인프라가 아니라
  이들의 결선* 으로 구축 가능함을 시사합니다.
- **기반 갭 6건이 후속 연구의 작업 목록** 입니다: train/test 분할 지정·평가 프로토콜
  명세·covariate shift 스트레스·다중 시드 평가·ablation 프로토콜·일반화 갭 정량화.

## CLI

```bash
python simulation/rl_generalization_protocol.py --report       # 준비도 요약
python simulation/rl_generalization_protocol.py --matrix       # 전체 매트릭스
python simulation/rl_generalization_protocol.py --stage evaluation_design  # 단계별
python simulation/rl_generalization_protocol.py --absent       # 부재(absent) 요소
python simulation/rl_generalization_protocol.py --foundational # 기반(필수) 요소
python simulation/rl_generalization_protocol.py --verdict      # 종합 준비도 판정
```
