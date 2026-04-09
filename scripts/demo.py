"""
SDACS 발표용 데모 스크립트

사용법:
    python scripts/demo.py              # 전체 데모 (약 2분)
    python scripts/demo.py --quick      # 빠른 데모 (약 30초)
    python scripts/demo.py --scenario   # 시나리오별 데모

발표 시 터미널에서 실행하면 시뮬레이션 결과가 순차적으로 출력됩니다.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _banner(text: str) -> None:
    width = 60
    print()
    print("=" * width)
    print(f"  {text}")
    print("=" * width)


def _section(text: str) -> None:
    print(f"\n--- {text} ---\n")


def demo_basic(duration: int = 30, n_drones: int = 20) -> None:
    """기본 시뮬레이션 데모"""
    _banner(f"Basic Simulation: {n_drones} drones, {duration}s")

    from simulation.simulator import SwarmSimulator

    sim = SwarmSimulator(seed=42)
    sim.configure({"drones": {"default_count": n_drones}})
    result = sim.run(duration_s=float(duration))

    print(f"  Drones:               {n_drones}")
    print(f"  Duration:             {duration}s")
    print(f"  Conflicts detected:   {result.get('conflicts_total', 0)}")
    print(f"  Collisions:           {result.get('collision_count', 0)}")
    print(f"  Near misses:          {result.get('near_miss_count', 0)}")
    print(f"  Advisories issued:    {result.get('advisories_issued', 0)}")
    cr = result.get("conflict_resolution_rate_pct", 0)
    print(f"  Resolution rate:      {cr:.1f}%")
    print(f"  Clearances approved:  {result.get('clearances_approved', 0)}")
    print(f"  Comm messages sent:   {result.get('comm_messages_sent', 0)}")
    print(f"  Comm drop rate:       {result.get('comm_drop_rate', 0):.2%}")


def demo_scenarios() -> None:
    """7대 핵심 시나리오 순차 실행"""
    _banner("7 Core Scenarios")

    from simulation.simulator import SwarmSimulator

    scenarios = [
        ("Normal Operation",      {"drones": {"default_count": 20}}, 30),
        ("High Density",          {"drones": {"default_count": 50}}, 30),
        ("Weather Disturbance",   {"drones": {"default_count": 20}, "weather": {"mode": "variable", "speed_ms": 15}}, 30),
        ("Communication Loss",    {"drones": {"default_count": 20}, "comms": {"loss_rate": 0.3}}, 30),
        ("Emergency Landing",     {"drones": {"default_count": 20}, "failures": {"rate_pct": 5}}, 30),
    ]

    results = []
    for name, config, dur in scenarios:
        _section(name)
        t0 = time.time()
        sim = SwarmSimulator(seed=42)
        sim.configure(config)
        result = sim.run(duration_s=float(dur))
        elapsed = time.time() - t0

        cr = result.get("conflict_resolution_rate_pct", 0)
        collisions = result.get("collision_count", 0)
        conflicts = result.get("conflicts_total", 0)
        print(f"  Conflicts: {conflicts:>6}  |  Collisions: {collisions:>3}  |  CR: {cr:.1f}%  |  Time: {elapsed:.1f}s")
        results.append((name, conflicts, collisions, cr))

    _section("Summary")
    print(f"  {'Scenario':<25} {'Conflicts':>10} {'Collisions':>12} {'CR':>8}")
    print(f"  {'-'*25} {'-'*10} {'-'*12} {'-'*8}")
    for name, conf, coll, cr in results:
        print(f"  {name:<25} {conf:>10} {coll:>12} {cr:>7.1f}%")


def demo_apf() -> None:
    """APF 엔진 데모"""
    _banner("APF Engine Parameters")

    from simulation.apf_engine.apf import APF_PARAMS, APF_PARAMS_WINDY

    print("  [Normal Mode]")
    for k, v in APF_PARAMS.items():
        print(f"    {k:<20}: {v}")

    print("\n  [Windy Mode (>12 m/s)]")
    for k, v in APF_PARAMS_WINDY.items():
        normal = APF_PARAMS.get(k, v)
        change = f"x{v/normal:.1f}" if normal and v != normal else ""
        print(f"    {k:<20}: {v:<10} {change}")


def demo_profiles() -> None:
    """드론 프로파일 출력"""
    _banner("Drone Profiles")

    from src.airspace_control.agents.drone_profiles import DRONE_PROFILES

    print(f"  {'Profile':<22} {'Speed':>7} {'Battery':>9} {'Endurance':>11} {'Priority':>10}")
    print(f"  {'-'*22} {'-'*7} {'-'*9} {'-'*11} {'-'*10}")
    for name, p in DRONE_PROFILES.items():
        print(f"  {name:<22} {p.max_speed_ms:>5.0f}m/s {p.battery_wh:>7.0f}Wh {p.endurance_min:>9.0f}min {p.priority:>10}")


def main() -> None:
    parser = argparse.ArgumentParser(description="SDACS Demo Script")
    parser.add_argument("--quick", action="store_true", help="Quick demo (30s)")
    parser.add_argument("--scenario", action="store_true", help="Run all scenarios")
    parser.add_argument("--apf", action="store_true", help="APF parameters demo")
    parser.add_argument("--profiles", action="store_true", help="Drone profiles demo")
    args = parser.parse_args()

    _banner("SDACS - Swarm Drone Airspace Control System")
    print("  Mokpo National University, Drone Mechanical Engineering")
    print("  Developer: Sunwoo Jang")
    print()

    if args.apf:
        demo_apf()
        return

    if args.profiles:
        demo_profiles()
        return

    if args.scenario:
        demo_scenarios()
        return

    # Default: full demo
    demo_profiles()

    if args.quick:
        demo_basic(duration=15, n_drones=10)
    else:
        demo_basic(duration=30, n_drones=20)
        demo_basic(duration=30, n_drones=50)

    demo_apf()

    _banner("Demo Complete")
    print("  3D Dashboard: python main.py visualize")
    print("  Full test:    pytest tests/ -v --timeout=30")
    print()


if __name__ == "__main__":
    main()
