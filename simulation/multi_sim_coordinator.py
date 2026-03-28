"""
다중 시뮬레이터 조율
===================
병렬 시뮬 실행 + 결과 집계 + 분산 시드 관리.

사용법:
    msc = MultiSimCoordinator(n_sims=10, base_seed=42)
    msc.register_scenario("high_density", params={"drones": 200})
    results = msc.run_all(runner_fn)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np


@dataclass
class SimConfig:
    """시뮬레이션 설정"""
    scenario: str
    params: dict[str, Any]
    seed: int


@dataclass
class SimResult:
    """시뮬레이션 결과"""
    scenario: str
    seed: int
    metrics: dict[str, float]
    success: bool = True
    error: str = ""


class MultiSimCoordinator:
    """다중 시뮬레이터 조율."""

    def __init__(self, n_sims: int = 10, base_seed: int = 42) -> None:
        self.n_sims = n_sims
        self.base_seed = base_seed
        self._scenarios: dict[str, dict[str, Any]] = {}
        self._results: list[SimResult] = []

    def register_scenario(self, name: str, params: dict[str, Any] | None = None) -> None:
        self._scenarios[name] = params or {}

    def generate_seeds(self, n: int | None = None) -> list[int]:
        rng = np.random.default_rng(self.base_seed)
        return [int(s) for s in rng.integers(0, 10**6, size=n or self.n_sims)]

    def generate_configs(self, scenario: str) -> list[SimConfig]:
        params = self._scenarios.get(scenario, {})
        seeds = self.generate_seeds()
        return [SimConfig(scenario=scenario, params=dict(params), seed=s) for s in seeds]

    def run_all(
        self, runner_fn: Callable[[SimConfig], dict[str, float]] | None = None,
    ) -> list[SimResult]:
        """모든 시나리오 실행"""
        results = []
        for scenario in self._scenarios:
            configs = self.generate_configs(scenario)
            for cfg in configs:
                try:
                    if runner_fn:
                        metrics = runner_fn(cfg)
                    else:
                        metrics = {"placeholder": 0.0}
                    results.append(SimResult(
                        scenario=scenario, seed=cfg.seed,
                        metrics=metrics, success=True,
                    ))
                except Exception as e:
                    results.append(SimResult(
                        scenario=scenario, seed=cfg.seed,
                        metrics={}, success=False, error=str(e),
                    ))
        self._results.extend(results)
        return results

    def aggregate(self, metric: str) -> dict[str, dict[str, float]]:
        """시나리오별 메트릭 집계"""
        by_scenario: dict[str, list[float]] = {}
        for r in self._results:
            if r.success and metric in r.metrics:
                if r.scenario not in by_scenario:
                    by_scenario[r.scenario] = []
                by_scenario[r.scenario].append(r.metrics[metric])

        return {
            scenario: {
                "mean": round(float(np.mean(vals)), 4),
                "std": round(float(np.std(vals)), 4),
                "min": round(float(np.min(vals)), 4),
                "max": round(float(np.max(vals)), 4),
                "n": len(vals),
            }
            for scenario, vals in by_scenario.items()
        }

    def success_rate(self) -> float:
        if not self._results:
            return 0.0
        return round(sum(1 for r in self._results if r.success) / len(self._results) * 100, 1)

    def summary(self) -> dict[str, Any]:
        return {
            "scenarios": len(self._scenarios),
            "total_runs": len(self._results),
            "success_rate": self.success_rate(),
        }
