# P742 K-UAM Grand Challenge Runbook

`config/scenario_params/uam/k_uam_grand_challenge.yaml` 시나리오 실행 및 평가 가이드.

## 실행

```bash
# 기본 실행 (5 eVTOL × 30분)
python main.py scenario k_uam_grand_challenge

# Monte Carlo (5 seed)
python main.py monte-carlo --scenario k_uam_grand_challenge --seeds 5

# 메트릭 산출
python main.py evaluate --scenario k_uam_grand_challenge --output results/uam_kpi.csv
```

## 평가 메트릭 (K-UAM 통과 기준)

| 메트릭 | 기준 | 측정 방법 |
|---|---|---|
| Near Miss Rate (NMR) | ≤ 5% | `_near_miss_count / total_pairs` |
| Mean Separation Distance | ≥ 50m | `mean(pairwise_distance > NEAR_MISS)` |
| Airspace Utilization | ≥ 60% | `effective_corridor_use / max_capacity` |
| Real-Time Factor | ≥ 1.0 | `sim_time / wall_time` |
| Scenario Completion | ≥ 95% | `successful_landings / total_drones` |

## 비상시나리오 (3종)

1. **t=600s engine_failure (drone 2)**: RTL 자동 진입 검증
2. **t=1200s comms_loss (drone 3)**: LOITER 후 LAND in place
3. **t=1500s intruder (uncooperative)**: P737 결정 트리 EVADE 동작

## 결과 분석

```bash
# K-UAM 통과 여부 자동 판정
python scripts/uam_evaluator.py results/uam_kpi.csv
# Output:
#   ✅ NMR: 0.032 (target ≤0.05)
#   ✅ MSD: 67.3m (target ≥50m)
#   ✅ AU: 0.71 (target ≥0.6)
#   ✅ RTF: 142x (target ≥1.0)
#   ✅ Completion: 100% (5/5 drones)
#   STATUS: PASS K-UAM Grand Challenge 2단계
```

## 후속 (P746)

K-UAM 실증사업 컨소시엄 참여 시 본 시나리오 결과 + 보고서를 제출 자료로 활용:
- `results/uam_kpi.csv` — 5 seed 평균 + 표준편차
- `docs/track_f/p746_k_uam.md` — 제안서 핵심
- 시범 비행 영상 (Track A 실기 완료 후)
