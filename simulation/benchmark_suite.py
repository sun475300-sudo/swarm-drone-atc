"""
시뮬레이션 벤치마크
===================
성능 벤치마크 스위트 + 결과 비교 + 회귀 탐지.

사용법:
    bs = BenchmarkSuite()
    bs.run_benchmark("collision_scan", func, n=1000)
    report = bs.compare_with_baseline()
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np


@dataclass
class BenchmarkResult:
    """벤치마크 결과"""
    name: str
    iterations: int
    mean_ms: float
    std_ms: float
    min_ms: float
    max_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    throughput: float  # ops/sec


class BenchmarkSuite:
    """성능 벤치마크 스위트."""

    def __init__(self) -> None:
        self._results: dict[str, BenchmarkResult] = {}
        self._baselines: dict[str, BenchmarkResult] = {}
        self._history: list[tuple[str, BenchmarkResult]] = []

    def run_benchmark(
        self,
        name: str,
        func: Callable[[], Any],
        iterations: int = 100,
        warmup: int = 5,
    ) -> BenchmarkResult:
        """벤치마크 실행"""
        # 워밍업
        for _ in range(warmup):
            func()

        timings = []
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            elapsed = (time.perf_counter() - start) * 1000  # ms
            timings.append(elapsed)

        arr = np.array(timings)
        result = BenchmarkResult(
            name=name,
            iterations=iterations,
            mean_ms=float(np.mean(arr)),
            std_ms=float(np.std(arr)),
            min_ms=float(np.min(arr)),
            max_ms=float(np.max(arr)),
            p50_ms=float(np.percentile(arr, 50)),
            p95_ms=float(np.percentile(arr, 95)),
            p99_ms=float(np.percentile(arr, 99)),
            throughput=1000.0 / max(float(np.mean(arr)), 0.001),
        )

        self._results[name] = result
        self._history.append((name, result))
        return result

    def set_baseline(self, name: str, result: BenchmarkResult | None = None) -> None:
        """기준선 설정"""
        if result:
            self._baselines[name] = result
        elif name in self._results:
            self._baselines[name] = self._results[name]

    def compare_with_baseline(self, name: str) -> dict[str, Any] | None:
        """기준선과 비교"""
        current = self._results.get(name)
        baseline = self._baselines.get(name)
        if not current or not baseline:
            return None

        speedup = baseline.mean_ms / max(current.mean_ms, 0.001)
        regression = current.mean_ms > baseline.mean_ms * 1.1

        return {
            "name": name,
            "baseline_mean_ms": baseline.mean_ms,
            "current_mean_ms": current.mean_ms,
            "speedup": round(speedup, 2),
            "regression": regression,
            "p95_change": round(
                (current.p95_ms - baseline.p95_ms) / max(baseline.p95_ms, 0.001) * 100, 1
            ),
        }

    def detect_regressions(self, threshold: float = 1.1) -> list[str]:
        """성능 회귀 탐지"""
        regressions = []
        for name in self._results:
            if name in self._baselines:
                current = self._results[name].mean_ms
                baseline = self._baselines[name].mean_ms
                if current > baseline * threshold:
                    regressions.append(name)
        return regressions

    def get_result(self, name: str) -> BenchmarkResult | None:
        return self._results.get(name)

    def all_results(self) -> dict[str, BenchmarkResult]:
        return dict(self._results)

    def report(self) -> str:
        """텍스트 리포트"""
        lines = ["=" * 60, "  벤치마크 결과", "=" * 60]
        for name, r in self._results.items():
            lines.append(f"\n  {name}:")
            lines.append(f"    반복: {r.iterations}")
            lines.append(f"    평균: {r.mean_ms:.3f} ms (±{r.std_ms:.3f})")
            lines.append(f"    P50: {r.p50_ms:.3f} ms | P95: {r.p95_ms:.3f} ms | P99: {r.p99_ms:.3f} ms")
            lines.append(f"    처리량: {r.throughput:.0f} ops/sec")

            if name in self._baselines:
                comp = self.compare_with_baseline(name)
                if comp:
                    status = "⚠ REGRESSION" if comp["regression"] else "✓ OK"
                    lines.append(f"    vs 기준선: {comp['speedup']:.2f}x {status}")

        return "\n".join(lines)

    def summary(self) -> dict[str, Any]:
        return {
            "total_benchmarks": len(self._results),
            "baselines_set": len(self._baselines),
            "regressions": len(self.detect_regressions()),
        }
