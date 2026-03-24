"""군집드론 공역통제 시뮬레이션 패키지"""
# 순환 import 방지를 위해 하위 모듈은 필요 시 직접 import하세요.
# 예: from simulation.simulator import SwarmSimulator

__all__ = [
    "SwarmSimulator",
    "SimulationAnalytics",
    "SimulationResult",
    "run_scenario",
    "list_scenarios",
]


def __getattr__(name: str):
    if name in ("SwarmSimulator",):
        from simulation.simulator import SwarmSimulator
        return SwarmSimulator
    if name in ("SimulationAnalytics", "SimulationResult"):
        from simulation import analytics as _a
        return getattr(_a, name)
    if name == "run_scenario":
        from simulation.scenario_runner import run_scenario
        return run_scenario
    if name == "list_scenarios":
        from simulation.scenario_runner import list_scenarios
        return list_scenarios
    raise AttributeError(f"module 'simulation' has no attribute {name!r}")
