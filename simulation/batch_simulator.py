"""
배치 시뮬레이터
===============
다중 시나리오 배치 실행 + 결과 비교 + 통계.

사용법:
    bs = BatchSimulator()
    bs.add_scenario("sc1", params={"drones": 50})
    results = bs.run_all(run_func)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np


@dataclass
class ScenarioConfig:
    """시나리오 설정"""
    scenario_id: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchResult:
    """배치 결과"""
    scenario_id: str
    success: bool
    metrics: dict[str, float] = field(default_factory=dict)
    duration_ms: float = 0.0
    error: str = ""


class BatchSimulator:
    """다중 시나리오 배치 실행."""

    def __init__(self) -> None:
        self._scenarios: dict[str, ScenarioConfig] = {}
        self._results: dict[str, BatchResult] = {}

    def add_scenario(self, scenario_id: str, params: dict[str, Any] | None = None) -> ScenarioConfig:
        sc = ScenarioConfig(scenario_id=scenario_id, params=params or {})
        self._scenarios[scenario_id] = sc
        return sc

    def run_all(
        self, run_func: Callable[[dict[str, Any]], dict[str, float]],
    ) -> dict[str, BatchResult]:
        """모든 시나리오 실행"""
        import time
        results = {}
        for sid, sc in self._scenarios.items():
            start = time.perf_counter()
            try:
                metrics = run_func(sc.params)
                elapsed = (time.perf_counter() - start) * 1000
                result = BatchResult(
                    scenario_id=sid, success=True,
                    metrics=metrics, duration_ms=elapsed,
                )
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                result = BatchResult(
                    scenario_id=sid, success=False,
                    duration_ms=elapsed, error=str(e),
                )
            results[sid] = result
            self._results[sid] = result
        return results

    def run_single(
        self, scenario_id: str,
        run_func: Callable[[dict[str, Any]], dict[str, float]],
    ) -> BatchResult | None:
        sc = self._scenarios.get(scenario_id)
        if not sc:
            return None
        import time
        start = time.perf_counter()
        try:
            metrics = run_func(sc.params)
            elapsed = (time.perf_counter() - start) * 1000
            result = BatchResult(scenario_id=scenario_id, success=True, metrics=metrics, duration_ms=elapsed)
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            result = BatchResult(scenario_id=scenario_id, success=False, duration_ms=elapsed, error=str(e))
        self._results[scenario_id] = result
        return result

    def compare(self, metric: str) -> dict[str, float]:
        """특정 메트릭 비교"""
        return {
            sid: r.metrics.get(metric, 0)
            for sid, r in self._results.items() if r.success
        }

    def statistics(self, metric: str) -> dict[str, float]:
        """메트릭 통계"""
        values = [r.metrics.get(metric, 0) for r in self._results.values() if r.success]
        if not values:
            return {}
        arr = np.array(values)
        return {
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "median": float(np.median(arr)),
        }

    def success_rate(self) -> float:
        if not self._results:
            return 0.0
        return sum(1 for r in self._results.values() if r.success) / len(self._results) * 100

    def summary(self) -> dict[str, Any]:
        return {
            "scenarios": len(self._scenarios),
            "completed": len(self._results),
            "success_rate": round(self.success_rate(), 1),
            "avg_duration_ms": round(
                np.mean([r.duration_ms for r in self._results.values()]) if self._results else 0, 1
            ),
        }
