# RL 일반화(미학습 시나리오 전이) 평가 프로토콜 적합성 게이트 — ODYSSEY Phase 452

SDACS 의 강화학습(RL) 정책이 "학습하지 않은 시나리오로 일반화된다" 는 **주장을 방어
가능하게** 하려면 어떤 평가 프로토콜 요건이 충족돼야 하는지를 결정적 게이트로 명문화하고,
현 RL 자산을 그 요건에 *정직하게* 비추는 기준 문서입니다. 정본 데이터는
`simulation/rl_generalization_protocol.py` 가 보유하며, 본 문서는 그 요약과 활용 맥락을
제공합니다. ODYSSEY Track 🔬 Formal & Research Frontier(451-460)의 두 번째 산출물입니다.

> **정직 공시**: 본 게이트는 *자문* 이며 어떤 모델도 학습·평가하지 않고 어떤 파일도
> 변경하지 않습니다(부수효과 0). Phase 451(`easa_ai_conformance`)이 핵심 갭으로 지목한
> `LA:LM-03` "미학습 시나리오 전이 검증 프로토콜 부재" 를 *메우는* 것이 아니라, 그 갭을
> 채우려면 무엇이 필요한지의 **합격 기준 명세**입니다. SDACS 의 RL 은 **연구 수준** 이므로
> 다수 필수 요건이 미충족이며 현 판정은 `NOT_DEFENSIBLE (38.5%)` 입니다 — 낮은 점수는
> 결함이 아니라 인증 경로상 현 위치의 정직한 보고이며, 안전은 RL 의 일반화가 아니라
> 결정적 APF+CBS 5계층 안전망이 보장합니다.

## 451 진단 → 452 합격 기준

| Phase | 역할 | 답하는 질문 |
|---|---|---|
| 451 `easa_ai_conformance` | 진단 | ML 인증 경로에서 *무엇이* 빠졌는가 (빌딩 블록 단위) |
| **452** `rl_generalization_protocol` | 합격 기준 명세 | 그중 일반화 검증 갭을 *어떻게* 채워야 방어 가능한가 (요건 단위) |

## 근거 (권위 있는 출처)

- **EASA Learning Assurance — W-shaped 프로세스** — 독립 데이터에 의한 학습 프로세스 검증
  (Phase 451 이 지목한 `LA:LM-03` 의 정렬 대상).
- **Henderson et al. 2018, *Deep Reinforcement Learning that Matters*** — 시드 분산·통계적
  유의성 보고의 필요성.
- **Tobin et al. 2017 / Peng et al. 2018 — Domain Randomization·Sim-to-Real 전이** — 학습
  분포 확장과 운용 영역 커버리지.
- **Quiñonero-Candela et al. — Dataset Shift** — 공변량 변화의 정량화.

## 평가 차원 (6종)

| 차원 id | 라벨 |
|---|---|
| `data_partitioning` | 학습/미학습 시나리오 분리 |
| `distribution_coverage` | 미학습 ODD·공변량 변화 정량화 |
| `statistical_rigor` | 다중 시드·유의성·신뢰구간 |
| `baseline_ablation` | 결정적 baseline 대비·ablation |
| `reproducibility` | 시드·설정·산출물 추적 |
| `safety_bounding` | 전이 실패의 안전 영향 차단 |

## 충족 상태 (4값) · 정직성 결속

- `MET` (가중 1.0) — 완전 충족, **실재 증거 경로 인용 필수**
- `PARTIAL` (가중 0.5) — 부분 충족, **실재 증거 경로 인용 필수**
- `UNMET` (가중 0.0) — 미충족, **증거 인용 금지(None)**
- `N/A` — 비적용, 게이트·분모에서 제외, 증거 인용 금지

`MET`/`PARTIAL` ⟺ 증거 경로 인용 결속을 `RequirementState.__post_init__` 가 강제하며,
인용한 모든 경로의 디스크 실재를 테스트(`test_shipped_evidence_paths_exist_on_disk`)가
강제합니다 — 근거 없는 충족 주장을 구조적으로 금지합니다.

## 판정 우선순위 (`assess`)

1. CRITICAL 요건이 하나라도 UNMET → **`NOT_DEFENSIBLE`**
2. CRITICAL 요건이 하나라도 PARTIAL → **`EVIDENCE_INSUFFICIENT`**
3. (비-CRITICAL 포함) UNMET·PARTIAL 잔여 → **`EVIDENCE_INSUFFICIENT`**
4. 그 외(전부 MET·N/A) → **`TRANSFER_CLAIM_DEFENSIBLE`**

알 수 없는 상태 값은 sentinel 로 흡수하지 않고 `ValueError` 로 즉시 거부합니다(결정성·
정직성 우선). `POLICY_MATRIX` 6칸을 테스트가 `assess` 와 정확 일치하도록 강제합니다.

## 현 자산 판정 (정직한 자가 공시)

`NOT_DEFENSIBLE (38.5%)` — 결격 3건(필수 UNMET): `RG-02` 데이터 누수 차단 · `RG-05` 다중
시드 평가 · `RG-06` 통계적 유의성 검정.

| 요건 | 상태 | 증거 |
|---|---|---|
| RG-01 미학습 시나리오 분리 (필수) | PARTIAL | `config/scenario_params` |
| RG-02 데이터 누수 차단 (필수) | UNMET | — |
| RG-03 미학습 ODD 커버리지 정량화 (필수) | PARTIAL | `src/training/domain_rand.py` |
| RG-04 공변량 변화 측정 | PARTIAL | `src/training/sim_real_gap.py` |
| RG-05 다중 시드 평가 (필수) | UNMET | — |
| RG-06 통계적 유의성 검정 (필수) | UNMET | — |
| RG-07 신뢰구간 보고 | UNMET | — |
| RG-08 결정적 baseline 대비 (필수) | PARTIAL | `simulation/path_deconflict.py` |
| RG-09 구성요소 제거 실험 | UNMET | — |
| RG-10 시드 통제(결정적 RNG) (필수) | MET | `src/training/domain_rand.py` |
| RG-11 설정·산출물 캡처 | PARTIAL | `config/default_simulation.yaml` |
| RG-12 자문 한정 권한 (필수) | MET | `simulation/emergency_protocol.py` |
| RG-13 런타임 영역 이탈 감시 | PARTIAL | `simulation/compliance_checker.py` |

유일한 `MET` 두 건(RG-10 시드 통제·RG-12 자문 한정 권한)은 SDACS 의 진짜 강점입니다:
재현성은 프로젝트 전반에 강제된 시드 고정 RNG 가, 안전은 RL 전이 실패가 안전-크리티컬
결정으로 이어지지 못하게 하는 결정적 안전망이 떠받칩니다.

## CLI

```bash
python -m simulation.rl_generalization_protocol --requirements  # 요건 목록
python -m simulation.rl_generalization_protocol --status        # 현 자산 판정
python -m simulation.rl_generalization_protocol --gaps          # 미충족 요건
python -m simulation.rl_generalization_protocol --policy        # 결정 매트릭스
python -m simulation.rl_generalization_protocol --manifest      # 매니페스트(JSON)
```
