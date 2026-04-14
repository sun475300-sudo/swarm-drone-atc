"""
GPU vs CPU APF 벤치마크 보고서 자동 생성 스크립트

드론 수별 batch_compute_forces 성능을 비교하고
터미널 + docs/gpu_benchmark_report.md에 결과를 출력한다.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simulation.apf_engine import get_apf_backend_info
from simulation.apf_engine.apf import APFState, batch_compute_forces as cpu_batch_compute_forces

# GPU 함수 임포트 시도
_GPU_AVAILABLE = False
try:
    from simulation.apf_engine.apf_gpu import gpu_batch_compute_forces
    _GPU_AVAILABLE = True
except ImportError:
    pass

DRONE_COUNTS = [50, 100, 200, 500, 1000]
CPU_MAX_DRONES = 500
NUM_RUNS = 5
SEED = 42
REPORT_PATH = PROJECT_ROOT / "docs" / "gpu_benchmark_report.md"


def _create_test_data(
    n: int, rng: np.random.Generator
) -> tuple[list[APFState], dict[str, np.ndarray], list[np.ndarray]]:
    """벤치마크용 테스트 데이터 생성."""
    positions = rng.uniform(0, 1000, size=(n, 3))
    velocities = rng.uniform(-5, 5, size=(n, 3))
    states = [
        APFState(
            position=positions[i].copy(),
            velocity=velocities[i].copy(),
            drone_id=f"drone_{i}",
        )
        for i in range(n)
    ]
    goals = {f"drone_{i}": rng.uniform(0, 1000, size=3) for i in range(n)}
    obstacles = [rng.uniform(0, 1000, size=3) for _ in range(5)]
    return states, goals, obstacles


def _benchmark_fn(fn, states, goals, obstacles, num_runs: int) -> float:
    """함수를 num_runs회 실행하고 평균 시간(초)을 반환."""
    # 웜업 1회
    fn(states, goals, obstacles)

    times: list[float] = []
    for _ in range(num_runs):
        start = time.perf_counter()
        fn(states, goals, obstacles)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    return sum(times) / len(times)


def main() -> None:
    # 1. 백엔드 정보 출력
    info = get_apf_backend_info()
    print("=" * 60)
    print("APF Backend Info")
    print("=" * 60)
    for k, v in info.items():
        print(f"  {k}: {v}")
    print()

    if not _GPU_AVAILABLE:
        print("WARNING: GPU backend not available. GPU columns will be N/A.")
    print()

    rng = np.random.default_rng(SEED)

    # 2. 벤치마크 실행
    results: list[dict] = []
    for n in DRONE_COUNTS:
        print(f"Benchmarking {n} drones ...")
        states, goals, obstacles = _create_test_data(n, rng)

        row: dict = {"n": n, "cpu_ms": None, "gpu_ms": None, "speedup": None}

        # CPU (500기까지만)
        if n <= CPU_MAX_DRONES:
            avg = _benchmark_fn(cpu_batch_compute_forces, states, goals, obstacles, NUM_RUNS)
            row["cpu_ms"] = round(avg * 1000, 2)

        # GPU
        if _GPU_AVAILABLE:
            avg = _benchmark_fn(gpu_batch_compute_forces, states, goals, obstacles, NUM_RUNS)
            row["gpu_ms"] = round(avg * 1000, 2)

        # 속도 비율
        if row["cpu_ms"] is not None and row["gpu_ms"] is not None and row["gpu_ms"] > 0:
            row["speedup"] = round(row["cpu_ms"] / row["gpu_ms"], 2)

        results.append(row)

    # 3. 터미널 테이블 출력
    print()
    print("=" * 60)
    print("Benchmark Results (avg of 5 runs)")
    print("=" * 60)
    header = f"{'Drones':>8} | {'CPU (ms)':>10} | {'GPU (ms)':>10} | {'Speedup':>8}"
    sep = "-" * len(header)
    print(header)
    print(sep)
    for r in results:
        cpu_str = f"{r['cpu_ms']:.2f}" if r["cpu_ms"] is not None else "N/A"
        gpu_str = f"{r['gpu_ms']:.2f}" if r["gpu_ms"] is not None else "N/A"
        spd_str = f"{r['speedup']:.2f}x" if r["speedup"] is not None else "-"
        print(f"{r['n']:>8} | {cpu_str:>10} | {gpu_str:>10} | {spd_str:>8}")
    print()

    # 4. 마크다운 보고서 저장
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# GPU Benchmark Report",
        "",
        "## Backend Info",
        "",
    ]
    for k, v in info.items():
        lines.append(f"- **{k}**: {v}")
    lines += [
        "",
        "## Results",
        "",
        f"Each test averaged over {NUM_RUNS} runs. CPU limited to {CPU_MAX_DRONES} drones.",
        "",
        "| Drones | CPU (ms) | GPU (ms) | Speedup |",
        "|-------:|---------:|---------:|--------:|",
    ]
    for r in results:
        cpu_str = f"{r['cpu_ms']:.2f}" if r["cpu_ms"] is not None else "N/A"
        gpu_str = f"{r['gpu_ms']:.2f}" if r["gpu_ms"] is not None else "N/A"
        spd_str = f"{r['speedup']:.2f}x" if r["speedup"] is not None else "-"
        lines.append(f"| {r['n']} | {cpu_str} | {gpu_str} | {spd_str} |")

    lines += [
        "",
        f"*Generated with seed={SEED}*",
        "",
    ]

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report saved to {REPORT_PATH}")


if __name__ == "__main__":
    main()
