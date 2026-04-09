"""Performance benchmark utilities for Phase 172.

Provides latency/throughput summary from sampled execution measurements.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PerfSample:
    duration_ms: float
    success: bool = True


class PerfBenchmark:
    def __init__(self) -> None:
        self._samples: list[PerfSample] = []

    def add_sample(self, duration_ms: float, success: bool = True) -> None:
        self._samples.append(PerfSample(duration_ms=max(0.0, float(duration_ms)), success=bool(success)))

    def add_batch(self, durations_ms: list[float]) -> None:
        for d in durations_ms:
            self.add_sample(d)

    @staticmethod
    def _percentile(sorted_values: list[float], p: float) -> float:
        if not sorted_values:
            return 0.0
        idx = int(round((len(sorted_values) - 1) * p))
        idx = max(0, min(len(sorted_values) - 1, idx))
        return sorted_values[idx]

    def report(self, window_sec: float = 60.0) -> dict[str, Any]:
        durations = [s.duration_ms for s in self._samples]
        sorted_vals = sorted(durations)
        n = len(sorted_vals)
        if n == 0:
            return {
                "samples": 0,
                "avg_ms": 0.0,
                "p50_ms": 0.0,
                "p95_ms": 0.0,
                "p99_ms": 0.0,
                "throughput_rps": 0.0,
                "success_rate": 1.0,
            }

        avg = sum(sorted_vals) / n
        p50 = self._percentile(sorted_vals, 0.50)
        p95 = self._percentile(sorted_vals, 0.95)
        p99 = self._percentile(sorted_vals, 0.99)
        success = sum(1 for s in self._samples if s.success)
        throughput = n / max(0.001, float(window_sec))
        return {
            "samples": n,
            "avg_ms": round(avg, 3),
            "p50_ms": round(p50, 3),
            "p95_ms": round(p95, 3),
            "p99_ms": round(p99, 3),
            "throughput_rps": round(throughput, 3),
            "success_rate": round(success / n, 4),
        }

    def clear(self) -> None:
        self._samples.clear()
