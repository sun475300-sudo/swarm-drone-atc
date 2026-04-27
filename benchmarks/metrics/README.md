# Benchmark Metrics

Metric **definitions** live in [`../../docs/paper/EVALUATION_METRICS.md`](../../docs/paper/EVALUATION_METRICS.md).
Metric **implementations** live in [`../../src/analytics/metrics.py`](../../src/analytics/metrics.py).
Metric **tests** live in [`../../tests/analytics/test_metrics.py`](../../tests/analytics/test_metrics.py).

## Quick reference

The 14 metrics this suite evaluates (every direction listed):

| # | Metric | Section | Direction | Unit |
|---|--------|---------|-----------|------|
| 1 | NMR — Near-Miss Rate | §1.1 | ↓ | events/(pair·s) |
| 2 | MSD — Min Separation Distance | §1.2 | ↑ | m |
| 3 | TTC distribution | §1.3 | ↑ | s |
| 4 | PE — Path Efficiency | §2.1 | ↑ | [1] |
| 5 | MS — Makespan | §2.2 | ↓ | s |
| 6 | FT — Flowtime | §2.3 | ↓ | drone-s |
| 7 | AU — Airspace Utilization | §3.1 | context | [1] |
| 8 | VCU — Voronoi Cell Utilization | §3.2 | — | [1] / Hz |
| 9 | RID-CR — Remote-ID Compliance Rate | §4.1 | ↑ | [1] |
| 10 | LAANC latency | §4.2 | ↓ | ms |
| 11 | Geofence violations | §4.3 | ↓ | count (target = 0) |
| 12 | RTF — Real-Time Factor | §5.1 | ↑ | [1] |
| 13 | Per-tick latency p50/p95/p99 | §5.2 | ↓ | ms |
| 14 | Memory peak | §5.3 | ↓ | MB |

## Producing a metric report

```bash
python -m src.analytics.metrics path/to/trace.json -o result.json
```

Aggregate over all (scenario × method × seed) runs:

```bash
python scripts/reproduce/aggregate.py results/<timestamp>/ -o summary.parquet
```
