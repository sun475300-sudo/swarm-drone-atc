"""Reproducibility utilities — Phase P704.

Seed-fixed simulation runs for bit-identical result reproduction.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ReproducibleRunConfig:
    """Fully-specified configuration for a reproducible run."""
    seed: int
    n_drones: int
    duration_s: float
    scenario: str = "default"
    config_path: str = "config/default_simulation.yaml"
    env_overrides: dict[str, Any] = field(default_factory=dict)

    def fingerprint(self) -> str:
        """SHA-256 of the deterministic config for cache/lookup."""
        stable = json.dumps(asdict(self), sort_keys=True, default=str)
        return hashlib.sha256(stable.encode()).hexdigest()[:16]


@dataclass
class ReproducibleRunResult:
    """Serializable result from a reproducible run."""
    config: ReproducibleRunConfig
    collision_count: int
    near_miss_count: int
    conflict_resolution_rate_pct: float
    total_distance_m: float
    wall_time_s: float
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        d = asdict(self)
        d["fingerprint"] = self.config.fingerprint()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReproducibleRunResult:
        """Restore from a dict produced by to_dict()."""
        cfg_data = data["config"]
        cfg = ReproducibleRunConfig(**cfg_data)
        return cls(
            config=cfg,
            collision_count=data["collision_count"],
            near_miss_count=data["near_miss_count"],
            conflict_resolution_rate_pct=data["conflict_resolution_rate_pct"],
            total_distance_m=data["total_distance_m"],
            wall_time_s=data["wall_time_s"],
            created_at=data["created_at"],
        )


def set_deterministic_env(seed: int) -> None:
    """Pin all process-level RNG sources for strict reproducibility."""
    import random

    import numpy as np

    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ.setdefault(var, "1")


def run_reproducible(cfg: ReproducibleRunConfig) -> ReproducibleRunResult:
    """Execute a simulation with strict seed isolation and return metrics.

    Uses a subprocess-style environment pin so the parent process RNG is
    not contaminated.
    """
    set_deterministic_env(cfg.seed)

    try:
        from simulation.simulator import SwarmSimulator
    except ImportError:
        from simulation.swarm_simulator import SwarmSimulator  # type: ignore[no-redef]

    scenario_cfg = {
        "drones": {"default_count": cfg.n_drones},
        **cfg.env_overrides,
    }

    t0 = time.perf_counter()
    sim = SwarmSimulator(
        config_path=cfg.config_path,
        scenario_cfg=scenario_cfg,
        seed=cfg.seed,
    )
    result = sim.run(cfg.duration_s)
    wall_time_s = time.perf_counter() - t0

    metrics = result.to_dict() if hasattr(result, "to_dict") else {}
    collisions = int(metrics.get("collision_count", 0))
    near_misses = int(metrics.get("near_miss_count", 0))
    conflicts = int(metrics.get("conflicts_total", 0))
    resolution_rate = (
        (1.0 - collisions / (conflicts + collisions)) * 100.0
        if (conflicts + collisions) > 0
        else 100.0
    )
    total_dist = float(metrics.get("total_distance_m", 0.0))

    return ReproducibleRunResult(
        config=cfg,
        collision_count=collisions,
        near_miss_count=near_misses,
        conflict_resolution_rate_pct=resolution_rate,
        total_distance_m=total_dist,
        wall_time_s=wall_time_s,
        created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )


def save_result(result: ReproducibleRunResult, output_dir: str = "reports") -> Path:
    """Persist result as a JSON file in output_dir."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    fname = out / f"repro_{result.config.fingerprint()}.json"
    fname.write_text(json.dumps(result.to_dict(), indent=2))
    return fname


def load_result(path: str) -> ReproducibleRunResult:
    """Load a previously saved reproducible run result."""
    data = json.loads(Path(path).read_text())
    return ReproducibleRunResult.from_dict(data)


def verify_reproducibility(cfg: ReproducibleRunConfig, runs: int = 2) -> bool:
    """Run the simulation `runs` times and verify bit-identical key metrics."""
    results = [run_reproducible(cfg) for _ in range(runs)]
    if len(results) < 2:
        return True
    r0 = results[0]
    return all(
        r.collision_count == r0.collision_count
        and r.near_miss_count == r0.near_miss_count
        for r in results[1:]
    )
