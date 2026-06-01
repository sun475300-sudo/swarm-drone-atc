# P706 Contribution Comparison Report

Generated: 2026-06-01 23:24:51

## NMR (lower is better)

| Scenario | cbs | orca | sdacs_hybrid | vo |
|---|---|---|---|---|
| 01_corridor_crossing | 0.0056 +/- 0.0000 | 0.0056 +/- 0.0000 | 0.0019 +/- 0.0000 | **0.0000 +/- 0.0000** |
| 08_stress_high_density | 0.0000 +/- 0.0000 | 0.0000 +/- 0.0000 | **0.0000 +/- 0.0000** | 0.0000 +/- 0.0000 |

## MSD (higher is better)

| Scenario | cbs | orca | sdacs_hybrid | vo |
|---|---|---|---|---|
| 01_corridor_crossing | 0.0000 +/- 0.0000 | 1.2942 +/- 0.0000 | 4.8204 +/- 0.0000 | **9.4321 +/- 0.0000** |
| 08_stress_high_density | 0.1570 +/- 0.0000 | 1.5572 +/- 0.0000 | **2.4348 +/- 0.0000** | 1.7733 +/- 0.0000 |

## PE (higher is better)

| Scenario | cbs | orca | sdacs_hybrid | vo |
|---|---|---|---|---|
| 01_corridor_crossing | **1.0000 +/- 0.0000** | 1.0000 +/- 0.0000 | 0.9698 +/- 0.0000 | 0.7456 +/- 0.0000 |
| 08_stress_high_density | **1.0000 +/- 0.0000** | 1.0000 +/- 0.0000 | 0.9775 +/- 0.0000 | 0.4036 +/- 0.0000 |

## MS_s (lower is better)

| Scenario | cbs | orca | sdacs_hybrid | vo |
|---|---|---|---|---|
| 01_corridor_crossing | **69.0000 +/- 0.0000** | 71.0000 +/- 0.0000 | 77.0000 +/- 0.0000 | 180.0000 +/- 0.0000 |
| 08_stress_high_density | **87.0000 +/- 0.0000** | 89.0000 +/- 0.0000 | 174.0000 +/- 0.0000 | 300.0000 +/- 0.0000 |

## FT_drone_s (lower is better)

| Scenario | cbs | orca | sdacs_hybrid | vo |
|---|---|---|---|---|
| 01_corridor_crossing | **276.0000 +/- 0.0000** | 284.0000 +/- 0.0000 | 304.0000 +/- 0.0000 | 527.0000 +/- 0.0000 |
| 08_stress_high_density | **10136.0000 +/- 0.0000** | 10390.0000 +/- 0.0000 | 20656.0000 +/- 0.0000 | 39404.0000 +/- 0.0000 |

## AU (higher is better)

| Scenario | cbs | orca | sdacs_hybrid | vo |
|---|---|---|---|---|
| 01_corridor_crossing | 0.3944 +/- 0.0000 | 0.4000 +/- 0.0000 | **1.0000 +/- 0.0000** | 0.7347 +/- 0.0000 |
| 08_stress_high_density | 0.1756 +/- 0.0000 | 0.1765 +/- 0.0000 | **1.0000 +/- 0.0000** | 0.6587 +/- 0.0000 |

## RTF (higher is better)

| Scenario | cbs | orca | sdacs_hybrid | vo |
|---|---|---|---|---|
| 01_corridor_crossing | **191865.7452 +/- 0.0000** | 191342.1911 +/- 0.0000 | 10209.2244 +/- 0.0000 | 10894.7389 +/- 0.0000 |
| 08_stress_high_density | **14894.5466 +/- 0.0000** | 12508.6795 +/- 0.0000 | 226.7267 +/- 0.0000 | 7.1621 +/- 0.0000 |

## Statistical Significance (SDACS vs Baselines)

| Scenario | Metric | vs | SDACS mean | Baseline mean | p-value | Sig. | Wins |
|---|---|---|---|---|---|---|---|

**Summary:** SDACS significantly outperforms baselines in 0/0 comparisons (p < 0.05).
