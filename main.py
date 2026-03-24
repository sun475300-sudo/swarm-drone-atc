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
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def cmd_simulate(args: argparse.Namespace) -> None:
    from simulation.simulator import SwarmSimulator
    print(f"[simulate] config={args.config}  duration={args.duration}s  seed={args.seed}")
    sim = SwarmSimulator(config_path=args.config, seed=args.seed)
    result = sim.run(duration_s=args.duration)
    d = result.to_dict()
    print("\n결과 요약")
    print(f"  드론 수:          {d['n_drones']}")
    print(f"  충돌:             {d['collision_count']}")
    print(f"  Near-miss:        {d['near_miss_count']}")
    print(f"  충돌 해결률:      {d['conflict_resolution_rate_pct']:.2f}%")
    print(f"  경로 효율(평균):  {d['route_efficiency_mean']:.3f}")
    print(f"  어드바이저리P50:  {d['advisory_latency_p50']:.3f}s")
    print(f"  어드바이저리P99:  {d['advisory_latency_p99']:.3f}s")


def cmd_scenario(args: argparse.Namespace) -> None:
    from simulation.scenario_runner import run_scenario, list_scenarios
    if args.list or not args.name:
        import yaml
        from pathlib import Path
        print("사용 가능한 시나리오:")
        for name in list_scenarios():
            p = Path(_ROOT) / "config" / "scenario_params" / f"{name}.yaml"
            with open(p, encoding="utf-8") as f:
                raw = yaml.safe_load(f)
            print(f"  {name:<40} {raw.get('description', '').replace(chr(0x2014), '-')}")
        return
    run_scenario(args.name, n_runs=args.runs, seed=args.seed)


def cmd_monte_carlo(args: argparse.Namespace) -> None:
    from simulation.monte_carlo_runner import run_monte_carlo
    run_monte_carlo(
        config_path=args.mc_config,
        sim_config_path=args.config,
        mode=args.mode,
        n_workers=args.workers,
        duration_s=args.duration,
    )


def cmd_visualize(args: argparse.Namespace) -> None:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "simulator_3d",
        os.path.join(_ROOT, "visualization", "simulator_3d.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # simulator_3d.py는 실행 시 Dash 서버를 시작함


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="sdacs",
        description="군집드론 공역통제 자동화 시스템 (SDACS)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── simulate ────────────────────────────────────────────────
    p_sim = sub.add_parser("simulate", help="단일 시뮬레이션 실행")
    p_sim.add_argument("--config",   default="config/default_simulation.yaml")
    p_sim.add_argument("--duration", type=float, default=600.0)
    p_sim.add_argument("--seed",     type=int,   default=42)

    # ── scenario ────────────────────────────────────────────────
    p_sc = sub.add_parser("scenario", help="명명된 시나리오 실행")
    p_sc.add_argument("name", nargs="?", help="시나리오 이름")
    p_sc.add_argument("--list",  "-l", action="store_true")
    p_sc.add_argument("--runs",  "-n", type=int, default=1)
    p_sc.add_argument("--seed",        type=int, default=42)

    # ── monte-carlo ─────────────────────────────────────────────
    p_mc = sub.add_parser("monte-carlo", help="Monte Carlo 파라미터 스윕")
    p_mc.add_argument("--mode",      default="quick", choices=["quick", "full"])
    p_mc.add_argument("--config",    default="config/default_simulation.yaml")
    p_mc.add_argument("--mc-config", default="config/monte_carlo.yaml")
    p_mc.add_argument("--workers",   type=int, default=None)
    p_mc.add_argument("--duration",  type=float, default=600.0)

    # ── visualize ───────────────────────────────────────────────
    sub.add_parser("visualize", help="3D 실시간 대시보드 실행 (Dash/Plotly)")

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
