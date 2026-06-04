# P717 Load Test Report

Generated: 2026-05-31 20:12:42
Duration: 30.0s per run

## Throughput Summary

| Drones | Wall Time | RTF | Collisions | Resolution | Memory | Status |
|--------|-----------|-----|------------|------------|--------|--------|
|     20 | 14.7s +/- 6.3s | 2.4x | 0 | 100.0% | 8 MB | Acceptable |
|     50 | 63.9s +/- 12.6s | 0.5x | 0 | 100.0% | 9 MB | Below real-time |
|    100 | 117.8s +/- 13.4s | 0.3x | 2 | 99.1% | 11 MB | Below real-time |
|    200 | 198.9s +/- 13.4s | 0.1x | 3 | 99.8% | 15 MB | Below real-time |

## Key Metrics

### 20 Drones
- Real-time factor: **2.43x** (+/- 1.37)
- Collision count: 0.0
- Conflict resolution rate: 100.0%
- Clearances/sec: 0.32
- Peak memory: 8.7 MB

### 50 Drones
- Real-time factor: **0.48x** (+/- 0.1)
- Collision count: 0.0
- Conflict resolution rate: 100.0%
- Clearances/sec: 0.82
- Peak memory: 9.4 MB

### 100 Drones
- Real-time factor: **0.26x** (+/- 0.03)
- Collision count: 2.3
- Conflict resolution rate: 99.06%
- Clearances/sec: 1.62
- Peak memory: 12.0 MB

### 200 Drones
- Real-time factor: **0.15x** (+/- 0.01)
- Collision count: 3.0
- Conflict resolution rate: 99.85%
- Clearances/sec: 3.27
- Peak memory: 16.5 MB
