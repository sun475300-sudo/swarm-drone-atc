# P706 Contribution Comparison Report

Generated: 2026-05-31 21:12:40

## NMR (lower is better)

| Scenario | cbs | orca | sdacs_hybrid | vo |
|---|---|---|---|---|
| 01_corridor_crossing | 0.0056 +/- 0.0000 | 0.0056 +/- 0.0000 | 0.0056 +/- 0.0000 | **0.0000 +/- 0.0000** |

## MSD (higher is better)

| Scenario | cbs | orca | sdacs_hybrid | vo |
|---|---|---|---|---|
| 01_corridor_crossing | 0.0000 +/- 0.0000 | 1.2942 +/- 0.0000 | 1.2942 +/- 0.0000 | **9.4321 +/- 0.0000** |

## PE (higher is better)

| Scenario | cbs | orca | sdacs_hybrid | vo |
|---|---|---|---|---|
| 01_corridor_crossing | **1.0000 +/- 0.0000** | 1.0000 +/- 0.0000 | 1.0000 +/- 0.0000 | 0.7456 +/- 0.0000 |

## MS_s (lower is better)

| Scenario | cbs | orca | sdacs_hybrid | vo |
|---|---|---|---|---|
| 01_corridor_crossing | **69.0000 +/- 0.0000** | 71.0000 +/- 0.0000 | 71.0000 +/- 0.0000 | 180.0000 +/- 0.0000 |

## FT_drone_s (lower is better)

| Scenario | cbs | orca | sdacs_hybrid | vo |
|---|---|---|---|---|
| 01_corridor_crossing | **276.0000 +/- 0.0000** | 284.0000 +/- 0.0000 | 284.0000 +/- 0.0000 | 527.0000 +/- 0.0000 |

## AU (higher is better)

| Scenario | cbs | orca | sdacs_hybrid | vo |
|---|---|---|---|---|
| 01_corridor_crossing | 0.3944 +/- 0.0000 | 0.4000 +/- 0.0000 | 0.4000 +/- 0.0000 | **0.7347 +/- 0.0000** |

## RTF (higher is better)

| Scenario | cbs | orca | sdacs_hybrid | vo |
|---|---|---|---|---|
| 01_corridor_crossing | **275426.7494 +/- 117648.0137** | 269213.4678 +/- 10517.2085 | 231349.2117 +/- 4855.8454 | 14607.1030 +/- 70.6080 |

## Statistical Significance (SDACS vs Baselines)

| Scenario | Metric | vs | SDACS mean | Baseline mean | p-value | Sig. | Wins |
|---|---|---|---|---|---|---|---|
| 01_corridor_crossing | NMR | orca | 0.0056 | 0.0056 | 1.0000 | No | N |
| 01_corridor_crossing | MSD | orca | 1.2942 | 1.2942 | 1.0000 | No | N |
| 01_corridor_crossing | PE | orca | 1.0000 | 1.0000 | 1.0000 | No | N |
| 01_corridor_crossing | MS_s | orca | 71.0000 | 71.0000 | 1.0000 | No | N |
| 01_corridor_crossing | FT_drone_s | orca | 284.0000 | 284.0000 | 1.0000 | No | N |
| 01_corridor_crossing | AU | orca | 0.4000 | 0.4000 | 1.0000 | No | N |
| 01_corridor_crossing | RTF | orca | 231349.2117 | 269213.4678 | 0.1213 | No | N |
| 01_corridor_crossing | NMR | vo | 0.0056 | 0.0000 | 0.1213 | No | N |
| 01_corridor_crossing | MSD | vo | 1.2942 | 9.4321 | 0.1213 | No | N |
| 01_corridor_crossing | PE | vo | 1.0000 | 0.7456 | 0.1213 | No | Y |
| 01_corridor_crossing | MS_s | vo | 71.0000 | 180.0000 | 0.1213 | No | Y |
| 01_corridor_crossing | FT_drone_s | vo | 284.0000 | 527.0000 | 0.1213 | No | Y |
| 01_corridor_crossing | AU | vo | 0.4000 | 0.7347 | 0.1213 | No | N |
| 01_corridor_crossing | RTF | vo | 231349.2117 | 14607.1030 | 0.1213 | No | Y |
| 01_corridor_crossing | NMR | cbs | 0.0056 | 0.0056 | 1.0000 | No | N |
| 01_corridor_crossing | MSD | cbs | 1.2942 | 0.0000 | 0.1213 | No | Y |
| 01_corridor_crossing | PE | cbs | 1.0000 | 1.0000 | 1.0000 | No | N |
| 01_corridor_crossing | MS_s | cbs | 71.0000 | 69.0000 | 0.1213 | No | N |
| 01_corridor_crossing | FT_drone_s | cbs | 284.0000 | 276.0000 | 0.1213 | No | N |
| 01_corridor_crossing | AU | cbs | 0.4000 | 0.3944 | 0.1213 | No | Y |
| 01_corridor_crossing | RTF | cbs | 231349.2117 | 275426.7494 | 1.0000 | No | N |

**Summary:** SDACS significantly outperforms baselines in 0/21 comparisons (p < 0.05).
