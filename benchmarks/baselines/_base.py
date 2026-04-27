"""BaselineAdapter Protocol — common contract for ORCA / VO / CBS / SDACS.

Every benchmark run goes through this Protocol. The runner (`scripts/run_one_scenario.py`)
loads a manifest, picks an adapter by name, runs it, and writes the resulting
SimulationTrace JSON to disk.

Design rules:
  * Adapter __init__ is fast and side-effect-free. Heavy setup goes in run().
  * Adapter.run() is synchronous and self-contained (no global state, no env vars).
  * Adapter.run() MUST return within hard_wall_time_s seconds — caller enforces.
  * The returned SimulationTrace is fully populated per src/analytics/types.py.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, runtime_checkable

from src.analytics.types import SimulationTrace


@runtime_checkable
class BaselineAdapter(Protocol):
    """Run a planner/controller on a scenario; return a populated trace.

    Implementations live in benchmarks/baselines/<name>/adapter.py and are
    discovered by name (file directory) by scripts/run_one_scenario.py.
    """

    name: str  # e.g. "orca", "vo", "cbs", "sdacs_hybrid"

    def __init__(self, manifest: Dict[str, Any], seed: int) -> None:
        """Save the manifest and seed; do NOT start work yet."""
        ...

    def run(self, hard_wall_time_s: float = 300.0) -> SimulationTrace:
        """Execute the scenario; return a fully-populated SimulationTrace.

        Args:
            hard_wall_time_s: Caller-enforced ceiling. The adapter itself
                should also try to stop early on this budget but the wrapper
                is final.

        Returns:
            SimulationTrace with all fields filled (per types.py defaults).
            Even on early termination, return a partial trace that the
            evaluator can still process.

        Raises:
            RuntimeError: only if setup is fundamentally broken (e.g. missing
                native dependency). Per-scenario failures should NOT raise —
                instead, set agent.goal_reached_at_s = None for incomplete
                agents and let the metrics report degradation.
        """
        ...


def make_adapter(method: str, manifest: Dict[str, Any], seed: int) -> BaselineAdapter:
    """Factory: import the adapter module by name and construct it."""
    import importlib

    module_name = {
        "sdacs": "sdacs",
        "sdacs_hybrid": "sdacs",
        "orca": "orca",
        "vo": "vo",
        "cbs": "cbs",
    }.get(method, None)
    if module_name is None:
        raise ValueError(
            f"Unknown adapter name {method!r}. "
            "Pick one of: sdacs, sdacs_hybrid, orca, vo, cbs."
        )
    mod = importlib.import_module(f"benchmarks.baselines.{module_name}.adapter")
    cls = getattr(mod, "Adapter", None)
    if cls is None:
        raise RuntimeError(
            f"benchmarks.baselines.{module_name}.adapter has no class `Adapter`"
        )
    return cls(manifest=manifest, seed=seed)


__all__ = ["BaselineAdapter", "make_adapter"]
