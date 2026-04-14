"""
SDACS 데모 쇼케이스 — 자동 시나리오 순회 + 결과 출력

실행: python scripts/demo_showcase.py
"""
from __future__ import annotations

import sys
import os
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def main():
    from simulation.apf_engine import get_apf_backend_info
    from simulation.simulator import SwarmSimulator

    backend = get_apf_backend_info()
    gpu = backend.get("gpu", "CPU") or "CPU"

    print("=" * 60)
    print("  SDACS — 군집드론 공역통제 자동화 시스템 데모")
    print(f"  GPU: {gpu} | Backend: {backend['backend']}")
    print("=" * 60)

    # 1. 기본 시뮬레이션
    print("\n[1/4] 기본 시뮬레이션 (100기, 60초)")
    sim = SwarmSimulator(seed=42)
    t0 = time.perf_counter()
    result = sim.run(duration_s=60.0)
    elapsed = time.perf_counter() - t0
    print(f"  충돌: {result.collision_count} | 해결률: {result.conflict_resolution_rate_pct:.1f}%")
    print(f"  실행시간: {elapsed:.1f}초")

    # 2. 대규모 시뮬레이션
    print("\n[2/4] 대규모 시뮬레이션 (500기, 60초)")
    cfg = {"drones": {"default_count": 500}}
    sim = SwarmSimulator(seed=42, scenario_cfg=cfg)
    t0 = time.perf_counter()
    result = sim.run(duration_s=60.0)
    elapsed = time.perf_counter() - t0
    print(f"  충돌: {result.collision_count} | 해결률: {result.conflict_resolution_rate_pct:.1f}%")
    print(f"  실행시간: {elapsed:.1f}초")

    # 3. 7개 시나리오 순회
    print("\n[3/4] 시나리오 순회")
    from simulation.scenario_runner import run_scenario
    scenarios = [
        "high_density", "weather_disturbance", "comms_loss",
        "emergency_failure", "adversarial_intrusion", "mass_takeoff",
        "route_conflict",
    ]
    print(f"  {'시나리오':<25} {'충돌':>6} {'해결률':>8}")
    print("  " + "-" * 45)
    for name in scenarios:
        results = run_scenario(name, n_runs=1, seed=42)
        r = results[0]
        col = r.get("collision_count", 0)
        res = r.get("conflict_resolution_rate", 0)
        print(f"  {name:<25} {col:>6} {res:>7.1f}%")

    # 4. ML 충돌 예측
    print("\n[4/4] ML 충돌 예측 모델")
    try:
        from simulation.collision_predictor import CollisionPredictor, generate_training_data
        data = generate_training_data(2000, seed=42)
        model = CollisionPredictor()
        losses = model.train(data, epochs=20)
        print(f"  학습 완료 (20 에포크, 최종 손실: {losses[-1]:.4f})")
        print(f"  디바이스: {model.device}")
    except Exception as e:
        print(f"  스킵: {e}")

    print("\n" + "=" * 60)
    print("  데모 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
