# RL 일반화 평가 프로토콜 적합성 게이트 — ODYSSEY Phase 452

SDACS 의 강화학습 충돌 회피 정책(`src/rl/ppo_collision.py`)에 대한 *신뢰할 수 있는
일반화 주장* 이 성립하려면 평가 프로토콜이 무엇을 갖춰야 하는가를 결정적 요건 카탈로그로
명문화하고, 각 요건이 리포 내 **실재 증거 산출물** 로 떠받쳐지는가를 감사해 종합 판정을
내리는 기준 문서입니다. 정본 데이터는 `simulation/rl_generalization_protocol.py` 가
보유하며, 본 문서는 그 요약과 활용 맥락을 제공합니다. ODYSSEY Track 🔬 Formal &
Research Frontier(451-460)의 두 번째 산출물입니다.

> **정직 공시**: 본 게이트는 *일반화 실험을 신뢰성 있게 돌릴 골격* 의 준비도만 판정하며
> **일반화 자체를 측정하지 않습니다** — 실제 일반화 수치는 GPU 학습·평가 실행(사용자
> 환경)에 의존합니다. SDACS 의 RL 은 **연구 수준** 이므로 본 평가는 보수적입니다.
> 임계 요건 미충족이 남아 있어도 안전은 ML 이 아니라 결정적 5계층 안전망이 보장하며,
> RL 일반화 실패는 자문 불변식에 의해 **무해**합니다.

## 451 과의 관계

Phase 451(`easa_ai_conformance`)이 SDACS 의 ML 자산을 EASA 6개 블록으로 폭넓게
진단하며 *핵심 연구 갭* 으로 지목한 항목이 `learning_process_verification` —
"미학습 시나리오 전이(일반화) 검증 프로토콜 없음" 이었습니다. 본 모듈은 그 갭 한 축을
깊게 파고들어 "어떤 증거가 있어야 일반화를 주장할 *자격* 이 생기는가" 를 답합니다.

## 근거 (학술 출처)

- **Cobbe et al., "Quantifying Generalization in RL"** (ICML 2019) — 학습/평가 환경
  분리·보류(held-out) 레벨 평가가 RL 일반화 측정의 전제.
- **Kirk et al., "A Survey of Generalisation in Deep RL"** (JAIR 2023) — 분포 변화·
  평가 프로토콜·통계적 엄밀성·베이스라인 기준화 분류 체계를 *단계(stage)* 축에 차용.
- **Henderson et al., "Deep RL that Matters"** (AAAI 2018) — 다중 시드·유의성·음성
  결과 공시의 필요성.

## 프로토콜 단계 (5종)

| 단계 id | 라벨 |
|---|---|
| `split_protocol` | 학습/평가 분리·보류 시나리오 |
| `distribution_shift` | OOD 조건 평가·리얼리티 갭 |
| `statistical_rigor` | 다중 시드·유의성·신뢰구간 |
| `baseline_grounding` | 결정적 베이스라인 대조·자문 불변식 |
| `reporting_integrity` | 음성 결과 공시·일반화 지표 정의 |

## 충족 상태 (3값)

- `satisfied` (가중 1.0) — 완전 충족, 실재 증거 경로 필수
- `partial` (가중 0.5) — 부분 충족, 실재 증거 경로 필수
- `absent` (가중 0.0) — 미충족, **증거 없음(None)**

`absent` ⟺ `evidence is None` 정직성 결속을 dataclass `__post_init__` 가 강제하며,
인용한 모든 경로의 디스크 실재를 테스트(`test_cited_evidence_exists_on_disk`)가 강제합니다.

## 종합 판정 (verdict)

- **임계(critical) 요건이 하나라도 미충족(absent)이면 `NOT_ESTABLISHED`** — 일반화를
  주장할 자격이 없습니다(전제 미성립). 가중 점수가 높아도 임계 미충족이면
  NOT_ESTABLISHED 이며, **점수가 판정을 앞당기지 않습니다.**
- 모든 요건이 완전 충족이면 `ESTABLISHED`.
- 임계는 전부 충족됐으나 부분/비임계 미충족이 남으면 `PARTIAL`.

## 현 리포 판정 (스냅샷)

| 지표 | 값 |
|---|---|
| 판정 | **NOT_ESTABLISHED** |
| 가중 점수 | **36%** (충족 1 · 부분 6 · 갭 4 / 총 11) |
| 임계 요건 | **1/7** 완전 충족 · 미충족 **2건** |

단계별 (충족/부분/갭):

| 단계 | 충족 | 부분 | 갭 |
|---|:-:|:-:|:-:|
| split_protocol | 0 | 1 | 1 |
| distribution_shift | 0 | 1 | 1 |
| statistical_rigor | 0 | 3 | 0 |
| baseline_grounding | **1** | 1 | 0 |
| reporting_integrity | 0 | 0 | 2 |

## 핵심 해석

- **두 임계 갭이 일반화 주장 자체를 막고 있습니다**: 학습/평가 시나리오의 서로소 분할
  기록 부재(`disjoint_train_eval_split`)와 일반화 지표의 결정적 정의 부재
  (`generalization_metric_definition`). 측정의 1차 전제와 측정 대상이 둘 다 미정의이므로
  현 상태에서는 어떤 일반화 수치도 신뢰할 수 없습니다.
- **통계적 골격은 이미 상당 부분 갖춰져 있습니다**: `simulation/uncertainty.py`(MC
  신뢰구간)·`simulation/power_analysis.py`(검정력)·`src/training/domain_rand.py`(도메인
  무작위화)가 부분 충족을 떠받칩니다 — 비어 있는 것은 *도구* 가 아니라 *RL 정책 평가에의
  적용* 입니다.
- **SDACS 의 강점은 일반화 증명이 아니라 일반화 실패의 무해화입니다**
  (`advisory_only_invariant`, 유일한 완전 충족). RL 은 항상 자문이고 안전-결정권은
  결정적 안전망(`simulation/emergency_protocol.py`)이 보유하므로, RL 이 미학습 상황에서
  틀려도 안전 위반으로 전이되지 않습니다. 이 불변식은 일반화 *증명* 의 부재와 독립적으로
  시스템을 안전하게 만듭니다.

## CLI

```bash
python simulation/rl_generalization_protocol.py --report   # 종합 판정 요약
python simulation/rl_generalization_protocol.py --matrix   # 전체 요건 매트릭스
python simulation/rl_generalization_protocol.py --stage distribution_shift
python simulation/rl_generalization_protocol.py --gaps     # 미충족(갭) 요건
python simulation/rl_generalization_protocol.py --critical # 임계(필수) 요건
```
