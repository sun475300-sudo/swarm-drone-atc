# P717 Load Test Report

Generated: 2026-05-31 20:04:44
Duration: 30.0s per run

## Throughput Summary

| Drones | Wall Time | RTF | Collisions | Resolution | Memory | Status |
|--------|-----------|-----|------------|------------|--------|--------|
|     20 | 19.2s +/- 1.8s | 1.6x | 0 | 100.0% | 8 MB | Acceptable |
|     50 | 56.7s +/- 15.2s | 0.6x | 0 | 100.0% | 9 MB | Below real-time |
|    100 | 111.4s +/- 18.7s | 0.3x | 3 | 98.7% | 11 MB | Below real-time |

## Key Metrics

### 20 Drones
- Real-time factor: **1.56x** (+/- 0.15)
- Collision count: 0.0
- Conflict resolution rate: 100.0%
- Clearances/sec: 0.33
- Peak memory: 8.7 MB

### 50 Drones
- Real-time factor: **0.55x** (+/- 0.14)
- Collision count: 0.0
- Conflict resolution rate: 100.0%
- Clearances/sec: 0.81
- Peak memory: 9.4 MB

### 100 Drones
- Real-time factor: **0.28x** (+/- 0.05)
- Collision count: 3.0
- Conflict resolution rate: 98.72%
- Clearances/sec: 1.63
- Peak memory: 11.9 MB
