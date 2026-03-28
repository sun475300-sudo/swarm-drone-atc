"""
시뮬레이션 성능 프로파일러

SwarmSimulator.run() 실행을 cProfile로 측정하고
병목 지점 Top-N을 자동 보고한다.

사용법:
    from simulation.profiler import profile_simulation
    report = profile_simulation(duration_s=60, n_drones=100, top_n=20)
    print(report)
"""
from __future__ import annotations

import cProfile
import io
import pstats
import time
from dataclasses import dataclass, field


@dataclass
class ProfileReport:
    """프로파일링 결과"""
    wall_time_s: float = 0.0
    total_calls: int = 0
    top_functions: list[dict] = field(default_factory=list)
    raw_stats: str = ""

    def summary(self) -> str:
        lines = [
            f"{'='*70}",
            f"  SDACS 시뮬레이션 성능 프로파일 보고서",
            f"{'='*70}",
            f"  총 실행 시간:  {self.wall_time_s:.2f}초",
            f"  총 함수 호출:  {self.total_calls:,}회",
            f"{'='*70}",
            f"  {'순위':<4} {'누적시간(s)':<12} {'호출수':<12} {'함수':<40}",
            f"  {'-'*68}",
        ]
        for i, fn in enumerate(self.top_functions, 1):
            lines.append(
                f"  {i:<4} {fn['cumtime']:<12.4f} {fn['ncalls']:<12} {fn['name']:<40}"
            )
        lines.append(f"{'='*70}")
        return "\n".join(lines)


def profile_simulation(
    duration_s: float = 60.0,
    n_drones: int = 100,
    seed: int = 42,
    top_n: int = 20,
) -> ProfileReport:
    """
    SwarmSimulator를 cProfile로 프로파일링.

    Parameters
    ----------
    duration_s : 시뮬레이션 시간 (초)
    n_drones : 드론 수
    seed : 랜덤 시드
    top_n : 보고할 상위 함수 수

    Returns
    -------
    ProfileReport : 프로파일 결과
    """
    from simulation.simulator import SwarmSimulator

    sim = SwarmSimulator(
        seed=seed,
        scenario_cfg={"drones": {"default_count": n_drones}},
    )

    profiler = cProfile.Profile()
    t0 = time.perf_counter()
    profiler.enable()
    sim.run(duration_s=duration_s)
    profiler.disable()
    wall_time = time.perf_counter() - t0

    # 통계 추출
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.strip_dirs()
    stats.sort_stats("cumulative")
    stats.print_stats(top_n)

    raw_output = stream.getvalue()

    # 파싱
    top_functions = []
    for fn_stat in stats.stats.items():
        (file, line, name), (cc, nc, tt, ct, callers) = fn_stat
        top_functions.append({
            "name": f"{file}:{line}({name})",
            "ncalls": nc,
            "tottime": tt,
            "cumtime": ct,
        })

    # cumtime 기준 정렬 후 top_n
    top_functions.sort(key=lambda x: x["cumtime"], reverse=True)
    top_functions = top_functions[:top_n]

    return ProfileReport(
        wall_time_s=wall_time,
        total_calls=sum(s[1] for s in stats.stats.values()),
        top_functions=top_functions,
        raw_stats=raw_output,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SDACS 시뮬레이션 프로파일러")
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--drones", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args()

    report = profile_simulation(
        duration_s=args.duration,
        n_drones=args.drones,
        seed=args.seed,
        top_n=args.top,
    )
    print(report.summary())
