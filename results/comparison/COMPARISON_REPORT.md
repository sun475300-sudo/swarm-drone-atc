# P706 Contribution Comparison Report

Generated: 2026-05-31 19:12:06

## NMR (lower is better)

| Scenario | cbs | orca | sdacs_hybrid | vo |
|---|---|---|---|---|
| 01_corridor_crossing | 0.0056 +/- 0.0000 | 0.0056 +/- 0.0000 | 0.0056 +/- 0.0000 | **0.0000 +/- 0.0000** |
| 02_dense_intersection | **0.0000 +/- 0.0000** | 0.0000 +/- 0.0000 | 0.0000 +/- 0.0000 | 0.0000 +/- 0.0000 |

## MSD (higher is better)

| Scenario | cbs | orca | sdacs_hybrid | vo |
|---|---|---|---|---|
| 01_corridor_crossing | 0.0000 +/- 0.0000 | 1.2942 +/- 0.0000 | 1.2942 +/- 0.0000 | **9.4321 +/- 0.0000** |
| 02_dense_intersection | 10.5846 +/- 2.0255 | 11.8487 +/- 1.6882 | 11.8487 +/- 1.6882 | **20.4171 +/- 0.8206** |

## PE (higher is better)

| Scenario | cbs | orca | sdacs_hybrid | vo |
|---|---|---|---|---|
| 01_corridor_crossing | **1.0000 +/- 0.0000** | 1.0000 +/- 0.0000 | 1.0000 +/- 0.0000 | 0.7456 +/- 0.0000 |
| 02_dense_intersection | 1.0000 +/- 0.0000 | **1.0000 +/- 0.0000** | 1.0000 +/- 0.0000 | 0.9216 +/- 0.0254 |

## MS_s (lower is better)

| Scenario | cbs | orca | sdacs_hybrid | vo |
|---|---|---|---|---|
| 01_corridor_crossing | **69.0000 +/- 0.0000** | 71.0000 +/- 0.0000 | 71.0000 +/- 0.0000 | 180.0000 +/- 0.0000 |
| 02_dense_intersection | **124.0000 +/- 15.5563** | 126.0000 +/- 15.5563 | 126.0000 +/- 15.5563 | 181.5000 +/- 82.7315 |

## FT_drone_s (lower is better)

| Scenario | cbs | orca | sdacs_hybrid | vo |
|---|---|---|---|---|
| 01_corridor_crossing | **276.0000 +/- 0.0000** | 284.0000 +/- 0.0000 | 284.0000 +/- 0.0000 | 527.0000 +/- 0.0000 |
| 02_dense_intersection | **1120.5000 +/- 40.3051** | 1140.5000 +/- 40.3051 | 1140.5000 +/- 40.3051 | 1407.5000 +/- 204.3539 |

## AU (higher is better)

| Scenario | cbs | orca | sdacs_hybrid | vo |
|---|---|---|---|---|
| 01_corridor_crossing | 0.3944 +/- 0.0000 | 0.4000 +/- 0.0000 | 0.4000 +/- 0.0000 | **0.7347 +/- 0.0000** |
| 02_dense_intersection | 0.3001 +/- 0.0105 | 0.3012 +/- 0.0105 | 0.3012 +/- 0.0105 | **0.3704 +/- 0.0528** |

## RTF (higher is better)

| Scenario | cbs | orca | sdacs_hybrid | vo |
|---|---|---|---|---|
| 01_corridor_crossing | 253603.4505 +/- 164142.6385 | **254120.9958 +/- 12228.1237** | 237844.3211 +/- 14261.5528 | 13233.7439 +/- 396.7976 |
| 02_dense_intersection | **131663.5269 +/- 1295.3417** | 86964.5725 +/- 23277.5587 | 94618.3064 +/- 1624.6316 | 2290.4259 +/- 346.2346 |

## Statistical Significance (SDACS vs Baselines)

| Scenario | Metric | vs | SDACS mean | Baseline mean | p-value | Sig. | Wins |
|---|---|---|---|---|---|---|---|
| 01_corridor_crossing | NMR | orca | 0.0056 | 0.0056 | 1.0000 | No | N |
| 01_corridor_crossing | MSD | orca | 1.2942 | 1.2942 | 1.0000 | No | N |
| 01_corridor_crossing | PE | orca | 1.0000 | 1.0000 | 1.0000 | No | N |
| 01_corridor_crossing | MS_s | orca | 71.0000 | 71.0000 | 1.0000 | No | N |
| 01_corridor_crossing | FT_drone_s | orca | 284.0000 | 284.0000 | 1.0000 | No | N |
| 01_corridor_crossing | AU | orca | 0.4000 | 0.4000 | 1.0000 | No | N |
| 01_corridor_crossing | RTF | orca | 237844.3211 | 254120.9958 | 0.4386 | No | N |
| 01_corridor_crossing | NMR | vo | 0.0056 | 0.0000 | 0.1213 | No | N |
| 01_corridor_crossing | MSD | vo | 1.2942 | 9.4321 | 0.1213 | No | N |
| 01_corridor_crossing | PE | vo | 1.0000 | 0.7456 | 0.1213 | No | Y |
| 01_corridor_crossing | MS_s | vo | 71.0000 | 180.0000 | 0.1213 | No | Y |
| 01_corridor_crossing | FT_drone_s | vo | 284.0000 | 527.0000 | 0.1213 | No | Y |
| 01_corridor_crossing | AU | vo | 0.4000 | 0.7347 | 0.1213 | No | N |
| 01_corridor_crossing | RTF | vo | 237844.3211 | 13233.7439 | 0.1213 | No | Y |
| 01_corridor_crossing | NMR | cbs | 0.0056 | 0.0056 | 1.0000 | No | N |
| 01_corridor_crossing | MSD | cbs | 1.2942 | 0.0000 | 0.1213 | No | Y |
| 01_corridor_crossing | PE | cbs | 1.0000 | 1.0000 | 1.0000 | No | N |
| 01_corridor_crossing | MS_s | cbs | 71.0000 | 69.0000 | 0.1213 | No | N |
| 01_corridor_crossing | FT_drone_s | cbs | 284.0000 | 276.0000 | 0.1213 | No | N |
| 01_corridor_crossing | AU | cbs | 0.4000 | 0.3944 | 0.1213 | No | Y |
| 01_corridor_crossing | RTF | cbs | 237844.3211 | 253603.4505 | 1.0000 | No | N |
| 02_dense_intersection | NMR | orca | 0.0000 | 0.0000 | 1.0000 | No | N |
| 02_dense_intersection | MSD | orca | 11.8487 | 11.8487 | 1.0000 | No | N |
| 02_dense_intersection | PE | orca | 1.0000 | 1.0000 | 1.0000 | No | N |
| 02_dense_intersection | MS_s | orca | 126.0000 | 126.0000 | 1.0000 | No | N |
| 02_dense_intersection | FT_drone_s | orca | 1140.5000 | 1140.5000 | 1.0000 | No | N |
| 02_dense_intersection | AU | orca | 0.3012 | 0.3012 | 1.0000 | No | N |
| 02_dense_intersection | RTF | orca | 94618.3064 | 86964.5725 | 1.0000 | No | Y |
| 02_dense_intersection | NMR | vo | 0.0000 | 0.0000 | 1.0000 | No | N |
| 02_dense_intersection | MSD | vo | 11.8487 | 20.4171 | 0.1213 | No | N |
| 02_dense_intersection | PE | vo | 1.0000 | 0.9216 | 0.1213 | No | Y |
| 02_dense_intersection | MS_s | vo | 126.0000 | 181.5000 | 0.4386 | No | Y |
| 02_dense_intersection | FT_drone_s | vo | 1140.5000 | 1407.5000 | 0.1213 | No | Y |
| 02_dense_intersection | AU | vo | 0.3012 | 0.3704 | 0.1213 | No | N |
| 02_dense_intersection | RTF | vo | 94618.3064 | 2290.4259 | 0.1213 | No | Y |
| 02_dense_intersection | NMR | cbs | 0.0000 | 0.0000 | 1.0000 | No | N |
| 02_dense_intersection | MSD | cbs | 11.8487 | 10.5846 | 0.4386 | No | Y |
| 02_dense_intersection | PE | cbs | 1.0000 | 1.0000 | 0.4386 | No | Y |
| 02_dense_intersection | MS_s | cbs | 126.0000 | 124.0000 | 0.4386 | No | N |
| 02_dense_intersection | FT_drone_s | cbs | 1140.5000 | 1120.5000 | 0.4386 | No | N |
| 02_dense_intersection | AU | cbs | 0.3012 | 0.3001 | 0.4386 | No | Y |
| 02_dense_intersection | RTF | cbs | 94618.3064 | 131663.5269 | 0.1213 | No | N |

**Summary:** SDACS significantly outperforms baselines in 0/42 comparisons (p < 0.05).
