"""
P717 — 100기 스웜 부하 테스트
==============================
100대 드론 시뮬레이션 처리량(시뮬레이션 초/실제 초)을 측정한다.
실시간 시각화 60 FPS 유지를 위한 최소 처리량 기준: 60 sim-steps/s.

실행:
    python scripts/load_test_100_drones.py [--drones 100] [--duration 30] [--seed 42]
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class LoadTestResult:
    """부하 테스트 결과"""
    n_drones: int
    sim_duration_s: float
    wall_time_s: float
    throughput_ratio: float      # sim_s / wall_s (>1 = faster than real-time)
    steps_per_second: float      # simulation steps per wall-clock second
    meets_60fps_target: bool     # ≥60 steps/s required for 60 FPS visualization

    def __str__(self) -> str:
        status = "PASS" if self.meets_60fps_target else "FAIL"
        return (
            f"[{status}] {self.n_drones} drones | "
            f"sim={self.sim_duration_s:.1f}s in {self.wall_time_s:.2f}s | "
            f"throughput={self.throughput_ratio:.1f}x | "
            f"steps/s={self.steps_per_second:.1f}"
        )


def run_load_test(
    n_drones: int = 100,
    sim_duration_s: float = 30.0,
    seed: int = 42,
    dt: float = 0.1,
) -> LoadTestResult:
    """지정된 드론 수로 시뮬레이션을 실행하고 처리량을 측정한다."""
    from simulation.simulator import SwarmSimulator

    cfg = {
        "drones": {"default_count": n_drones},
        "simulation": {"hz": 10, "realtime": False},
    }

    sim = SwarmSimulator(scenario_cfg=cfg, seed=seed)

    # 시뮬레이션 실행 (SimPy env.run)
    t0 = time.perf_counter()
    sim.run(duration_s=sim_duration_s)
    wall_time = time.perf_counter() - t0

    # 처리량 계산
    throughput_ratio = sim_duration_s / wall_time
    # 10 Hz 시뮬레이션: duration_s * 10 = total steps
    total_steps = sim_duration_s * 10.0
    steps_per_second = total_steps / wall_time

    # 60 FPS 기준: 60 sim-steps/s (10Hz → ×6 real-time 필요)
    meets_target = steps_per_second >= 60.0

    return LoadTestResult(
        n_drones=n_drones,
        sim_duration_s=sim_duration_s,
        wall_time_s=wall_time,
        throughput_ratio=throughput_ratio,
        steps_per_second=steps_per_second,
        meets_60fps_target=meets_target,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="100-drone swarm load test")
    parser.add_argument("--drones", type=int, default=100, help="드론 수")
    parser.add_argument("--duration", type=float, default=30.0, help="시뮬레이션 시간 (초)")
    parser.add_argument("--seed", type=int, default=42, help="랜덤 시드")
    args = parser.parse_args()

    print(f"Starting load test: {args.drones} drones, {args.duration}s simulation ...")
    result = run_load_test(
        n_drones=args.drones,
        sim_duration_s=args.duration,
        seed=args.seed,
    )
    print(result)

    if not result.meets_60fps_target:
        print(
            f"WARNING: throughput {result.steps_per_second:.1f} steps/s "
            f"< 60 steps/s target for 60 FPS visualization"
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
