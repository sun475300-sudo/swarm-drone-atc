# Phase 640: System Benchmark — Performance Report Generator
"""
전체 시스템 벤치마크: 모듈 실행 시간 측정,
메모리 사용량, 스루풋 분석, 성능 리포트 생성.
"""

import numpy as np
import time
from dataclasses import dataclass, field


@dataclass
class BenchmarkResult:
    module_name: str
    execution_time: float  # seconds
    status: str  # "pass" or "fail"
    error: str = ""


class SystemBenchmark:
    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)
        self.results: list[BenchmarkResult] = []
        self.total_time = 0.0

    def _bench_module(self, name: str, func) -> BenchmarkResult:
        start = time.perf_counter()
        try:
            func()
            elapsed = time.perf_counter() - start
            return BenchmarkResult(name, elapsed, "pass")
        except Exception as e:
            elapsed = time.perf_counter() - start
            return BenchmarkResult(name, elapsed, "fail", str(e))

    def run(self):
        modules = self._get_module_list()
        for name, func in modules:
            result = self._bench_module(name, func)
            self.results.append(result)
            self.total_time += result.execution_time

    def _get_module_list(self) -> list[tuple[str, callable]]:
        modules = []

        # Phase 601-610
        try:
            from simulation.swarm_topology_control import SwarmTopologyControl
            modules.append(("601_topology", lambda: SwarmTopologyControl(10, 42).run(20)))
        except ImportError:
            pass

        try:
            from simulation.drone_auction_market import DroneAuctionMarket
            modules.append(("602_auction", lambda: DroneAuctionMarket(10, 5, 42).run(10)))
        except ImportError:
            pass

        try:
            from simulation.constraint_satisfaction import ConstraintSatisfaction
            modules.append(("610_csp", lambda: ConstraintSatisfaction(8, 4, 42).run()))
        except ImportError:
            pass

        # Phase 621-630
        try:
            from simulation.digital_pheromone import DigitalPheromone
            modules.append(("622_pheromone", lambda: DigitalPheromone(10, 30, 42).run(50)))
        except ImportError:
            pass

        try:
            from simulation.evolutionary_arch import EvolutionaryArchitecture
            modules.append(("626_neat", lambda: EvolutionaryArchitecture(15, 42).run(20)))
        except ImportError:
            pass

        try:
            from simulation.plasma_physics import PlasmaPhysics
            modules.append(("630_plasma", lambda: PlasmaPhysics(15, 42).run(50)))
        except ImportError:
            pass

        return modules

    def summary(self):
        passed = sum(1 for r in self.results if r.status == "pass")
        failed = sum(1 for r in self.results if r.status == "fail")
        times = [r.execution_time for r in self.results]
        return {
            "modules_tested": len(self.results),
            "passed": passed,
            "failed": failed,
            "total_time": round(self.total_time, 4),
            "avg_time": round(float(np.mean(times)), 4) if times else 0,
            "max_time": round(float(np.max(times)), 4) if times else 0,
            "fastest": min(self.results, key=lambda r: r.execution_time).module_name if self.results else "N/A",
            "slowest": max(self.results, key=lambda r: r.execution_time).module_name if self.results else "N/A",
        }

    def report(self) -> str:
        lines = ["=" * 60, "SDACS Phase 640 System Benchmark Report", "=" * 60, ""]
        for r in sorted(self.results, key=lambda x: x.execution_time):
            status = "PASS" if r.status == "pass" else "FAIL"
            lines.append(f"  [{status}] {r.module_name:30s} {r.execution_time*1000:8.2f} ms")
        lines.append("")
        lines.append(f"  Total: {self.total_time*1000:.2f} ms | Passed: {sum(1 for r in self.results if r.status == 'pass')}/{len(self.results)}")
        lines.append("=" * 60)
        return "\n".join(lines)


if __name__ == "__main__":
    bench = SystemBenchmark(42)
    bench.run()
    print(bench.report())
    print()
    for k, v in bench.summary().items():
        print(f"  {k}: {v}")
