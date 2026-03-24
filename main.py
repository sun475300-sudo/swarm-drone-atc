"""
SDACS — 군집드론 공역통제 자동화 시스템
메인 진입점

사용법:
    python main.py simulate              # 기본 시뮬레이션 1회 실행
    python main.py scenario --list       # 시나리오 목록
    python main.py scenario weather_disturbance --runs 3
    python main.py monte-carlo --mode quick
    python main.py visualize             # 3D 대시보드 실행
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s │ %(name)-20s │ %(levelname)-5s │ %(message)s",
        datefmt="%H:%M:%S",
    )


# ── simulate ─────────────────────────────────────────────────

def cmd_simulate(args: argparse.Namespace) -> None:
    _setup_logging(getattr(args, "log_level", "INFO"))
    from simulation.engine import SimulationEngine

    duration = args.duration
    seed = args.seed
    drones = getattr(args, "drones", 100)
    print(f"\n🛸 시뮬레이션 시작: seed={seed}, drones={drones}, duration={duration}s\n")

    engine = SimulationEngine(seed=seed, duration_s=duration, drone_count=drones)
    metrics = engine.run()

    print(metrics.summary_table())
    print(f"\n✅ 시뮬레이션 완료 ({duration:.0f}s, {drones}기)\n")


# ── scenario ─────────────────────────────────────────────────

def cmd_scenario(args: argparse.Namespace) -> None:
    _setup_logging(getattr(args, "log_level", "INFO"))
    from simulation.scenario_runner import list_scenarios, run_scenario, aggregate_results

    if args.list or not args.name:
        scenarios = list_scenarios()
        print()
        print("  ┌──────────────────────────┬────────────────────────────────────────────────┐")
        print("  │ 시나리오                  │ 설명                                           │")
        print("  ├──────────────────────────┼────────────────────────────────────────────────┤")
        for s in scenarios:
            n = s["name"]
            d = s["description"][:44]
            print(f"  │ {n:<24} │ {d:<46} │")
        print("  └──────────────────────────┴────────────────────────────────────────────────┘")
        print()
        return

    name = args.name
    runs = args.runs
    seed = args.seed
    print(f"\n🚀 시나리오 [{name}] — {runs}회 실행 (seed={seed})\n")

    results = run_scenario(name, runs=runs, base_seed=seed)

    for i, m in enumerate(results):
        print(f"── Run #{i+1} ──")
        print(m.summary_table())
        print()

    if runs > 1:
        agg = aggregate_results(results)
        print("━━━━ 집계 결과 ━━━━")
        for k, v in agg.items():
            print(f"  {k}: {v}")
        print()


# ── monte-carlo ──────────────────────────────────────────────

def cmd_monte_carlo(args: argparse.Namespace) -> None:
    _setup_logging(getattr(args, "log_level", "INFO"))
    from simulation.monte_carlo import run_monte_carlo, summarize_results

    mode = args.mode
    print(f"\n🎲 Monte Carlo [{mode}] 스윕 시작...\n")

    results = run_monte_carlo(mode=mode)

    print(f"\n총 {len(results)}회 실행 완료\n")
    print(summarize_results(results))
    print()


# ── visualize ────────────────────────────────────────────────

def cmd_visualize(args: argparse.Namespace) -> None:
    _setup_logging(getattr(args, "log_level", "INFO"))
    from simulation.engine import SimulationEngine
    from visualization.dashboard import launch_dashboard

    port = getattr(args, "port", 8050)
    seed = getattr(args, "seed", 42)
    duration = getattr(args, "duration", 120)
    drones = getattr(args, "drones", 30)

    print(f"\n🛸 데모 시뮬레이션 실행 중 ({drones}기, {duration}s)...")
    engine = SimulationEngine(seed=seed, duration_s=duration, drone_count=drones)
    metrics = engine.run()

    print(metrics.summary_table())
    print(f"\n🌐 대시보드 시작: http://127.0.0.1:{port}\n")
    launch_dashboard(metrics.trajectory_log, port=port)


# ── main ─────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="sdacs",
        description="군집드론 공역통제 자동화 시스템 (SDACS)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── simulate ────────────────────────────────────────────────
    p_sim = sub.add_parser("simulate", help="단일 시뮬레이션 실행")
    p_sim.add_argument("--duration", type=float, default=600.0, help="시뮬레이션 시간 (초)")
    p_sim.add_argument("--seed",     type=int,   default=42, help="랜덤 시드")
    p_sim.add_argument("--drones",   type=int,   default=100, help="드론 수")
    p_sim.add_argument("--log-level", default="INFO")

    # ── scenario ────────────────────────────────────────────────
    p_sc = sub.add_parser("scenario", help="명명된 시나리오 실행")
    p_sc.add_argument("name", nargs="?", help="시나리오 이름")
    p_sc.add_argument("--list",  "-l", action="store_true")
    p_sc.add_argument("--runs",  "-n", type=int, default=1, help="반복 횟수")
    p_sc.add_argument("--seed",        type=int, default=42, help="기본 시드")
    p_sc.add_argument("--log-level", default="INFO")

    # ── monte-carlo ─────────────────────────────────────────────
    p_mc = sub.add_parser("monte-carlo", help="Monte Carlo 파라미터 스윕")
    p_mc.add_argument("--mode",      default="quick", choices=["quick", "full"])
    p_mc.add_argument("--log-level", default="INFO")

    # ── visualize ───────────────────────────────────────────────
    p_vis = sub.add_parser("visualize", help="3D 대시보드 실행 (Dash/Plotly)")
    p_vis.add_argument("--port",     type=int,   default=8050, help="대시보드 포트")
    p_vis.add_argument("--seed",     type=int,   default=42)
    p_vis.add_argument("--duration", type=float, default=120, help="데모 시뮬레이션 시간")
    p_vis.add_argument("--drones",   type=int,   default=30, help="데모 드론 수")
    p_vis.add_argument("--log-level", default="INFO")

    args = parser.parse_args()

    dispatch = {
        "simulate":    cmd_simulate,
        "scenario":    cmd_scenario,
        "monte-carlo": cmd_monte_carlo,
        "visualize":   cmd_visualize,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
