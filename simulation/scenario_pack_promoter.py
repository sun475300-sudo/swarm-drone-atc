"""
시나리오 팩 프로모터 — 시뮬레이션 결과를 검증된 시나리오 팩으로 승격
"""
from __future__ import annotations

from datetime import datetime, timezone


class ScenarioPackPromoter:
    """시나리오 실행 결과를 검증하여 배포 가능한 팩으로 승격"""

    PACK_VERSION = "1.0"

    def promote(
        self,
        scenario_name: str,
        seed: int,
        n_drones: int = 20,
        collision_count: int = 0,
        resolution_rate_pct: float = 100.0,
    ) -> dict:
        validated = resolution_rate_pct >= 95.0
        return {
            "scenario": scenario_name,
            "seed": seed,
            "n_drones": n_drones,
            "collision_count": collision_count,
            "resolution_rate_pct": resolution_rate_pct,
            "validated": validated,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "pack_version": self.PACK_VERSION,
        }

    def promote_batch(self, runs: list[dict]) -> list[dict]:
        return [self.promote(**run) for run in runs]
