# Safety-Net Ablation Study (Phase 286)

- Seeds: 2 | Drones: 25 | Duration: 90s
- 각 행은 해당 안전망 계층을 제거한 구성의 시드 평균.
- 충돌 해결률 = 1 − collisions / (conflicts + collisions).

| Configuration | Collisions | Near-misses | Conflicts | Resolution Rate (%) |
|---|---:|---:|---:|---:|
| baseline | 1.00 | 2.50 | 38.00 | 98.25 |
| no_apf | 2.50 | 1.50 | 39.50 | 94.50 |
| no_cbs | 1.00 | 2.50 | 38.00 | 98.25 |
| no_apf_no_cbs | 2.50 | 1.50 | 39.50 | 94.50 |
