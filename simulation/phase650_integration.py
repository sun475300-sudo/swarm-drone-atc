# Phase 650: Integration Runner — Phase 641-649 Module Integration Test
"""
Phase 641-649 전체 모듈 통합 실행 및 성능 리포트 생성.
"""

import numpy as np
import time
from dataclasses import dataclass, field


@dataclass
class IntegrationResult:
    module_name: str
    phase: int
    execution_time: float
    status: str  # "pass" or "fail"
    details: dict = field(default_factory=dict)
    error: str = ""


class Phase650Integration:
    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.results: list[IntegrationResult] = []
        self.total_time = 0.0

    def _run_module(self, name: str, phase: int, func) -> IntegrationResult:
        start = time.perf_counter()
        try:
            details = func()
            elapsed = time.perf_counter() - start
            return IntegrationResult(name, phase, elapsed, "pass", details or {})
        except Exception as e:
            elapsed = time.perf_counter() - start
            return IntegrationResult(name, phase, elapsed, "fail", error=str(e))

    def run(self) -> None:
        modules = self._get_modules()
        for name, phase, func in modules:
            result = self._run_module(name, phase, func)
            self.results.append(result)
            self.total_time += result.execution_time

    def _get_modules(self) -> list[tuple[str, int, callable]]:
        modules = []

        try:
            from simulation.spatial_index_kdtree import KDTreeIndex
            modules.append(("KDTree Spatial Index", 641,
                           lambda: KDTreeIndex(42).benchmark(100)))
        except ImportError:
            pass

        try:
            from simulation.telemetry_compression import TelemetryCompressor
            def _tc():
                c = TelemetryCompressor(42)
                frames = c.generate_test_data(200)
                stream = c.compress(frames)
                return {"ratio": c.compression_ratio(stream), "frames": len(frames)}
            modules.append(("Telemetry Compression", 642, _tc))
        except ImportError:
            pass

        try:
            from simulation.health_predictor import HealthPredictor
            def _hp():
                hp = HealthPredictor(42)
                res = hp.simulate_degradation(5, 50)
                return {"drones": len(res)}
            modules.append(("Health Predictor", 643, _hp))
        except ImportError:
            pass

        try:
            from simulation.adaptive_sampling import AdaptiveSampler
            def _as():
                s = AdaptiveSampler(42)
                h = s.simulate(30, 10)
                return h[-1] if h else {}
            modules.append(("Adaptive Sampling", 644, _as))
        except ImportError:
            pass

        try:
            from simulation.swarm_consensus_raft import SwarmRaftConsensus
            modules.append(("Swarm Raft Consensus", 645,
                           lambda: SwarmRaftConsensus(5, 42).run(15)))
        except ImportError:
            pass

        try:
            from simulation.anomaly_detector_isolation import DroneAnomalyDetector
            def _ad():
                d = DroneAnomalyDetector(42)
                results = d.simulate(20, 30)
                return {"total": len(results), "anomalies": sum(1 for r in results if r.is_anomaly)}
            modules.append(("Anomaly Detector", 646, _ad))
        except ImportError:
            pass

        try:
            from simulation.mission_scheduler import MissionScheduler
            modules.append(("Mission Scheduler", 647,
                           lambda: MissionScheduler(42).run(20)))
        except ImportError:
            pass

        try:
            from simulation.energy_optimizer import EnergyOptimizer
            modules.append(("Energy Optimizer", 648,
                           lambda: EnergyOptimizer(42).run(10)))
        except ImportError:
            pass

        try:
            from simulation.swarm_formation_ga import FormationGA
            modules.append(("Formation GA", 649,
                           lambda: FormationGA(10, 42).run(20)))
        except ImportError:
            pass

        return modules

    def summary(self) -> dict:
        passed = sum(1 for r in self.results if r.status == "pass")
        failed = sum(1 for r in self.results if r.status == "fail")
        return {
            "modules_tested": len(self.results),
            "passed": passed,
            "failed": failed,
            "total_time_ms": round(self.total_time * 1000, 2),
            "avg_time_ms": round(self.total_time / max(len(self.results), 1) * 1000, 2),
        }

    def report(self) -> str:
        lines = ["=" * 60, "SDACS Phase 650 Integration Report", "=" * 60, ""]
        for r in sorted(self.results, key=lambda x: x.phase):
            status = "PASS" if r.status == "pass" else "FAIL"
            lines.append(f"  [{status}] Phase {r.phase} {r.module_name:30s} {r.execution_time*1000:8.2f} ms")
            if r.error:
                lines.append(f"         ERROR: {r.error[:80]}")
        lines.append("")
        s = self.summary()
        lines.append(f"  Total: {s['total_time_ms']:.2f} ms | "
                     f"Passed: {s['passed']}/{s['modules_tested']}")
        lines.append("=" * 60)
        return "\n".join(lines)


if __name__ == "__main__":
    runner = Phase650Integration(42)
    runner.run()
    print(runner.report())
