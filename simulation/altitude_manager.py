"""
동적 고도 분리
==============
방향별 고도 레이어 + 혼잡 기반 동적 할당.

사용법:
    am = AltitudeManager()
    alt = am.assign_altitude("d1", heading_deg=90, priority=2)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class AltitudeAssignment:
    """고도 할당"""
    drone_id: str
    altitude_m: float
    layer: int
    heading_band: str  # N, NE, E, SE, S, SW, W, NW
    reason: str


class AltitudeManager:
    """동적 고도 분리 관리."""

    HEADINGS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    BASE_ALTITUDES = [30, 40, 50, 60, 70, 80, 90, 100]  # 방향별 기본 고도

    def __init__(
        self,
        min_altitude: float = 30.0,
        max_altitude: float = 120.0,
        layer_separation: float = 10.0,
    ) -> None:
        self._min_alt = min_altitude
        self._max_alt = max_altitude
        self._separation = layer_separation
        self._assignments: dict[str, AltitudeAssignment] = {}
        self._layer_counts: dict[int, int] = {}

    def _heading_band(self, heading_deg: float) -> tuple[str, int]:
        """방위각 → 8방위 밴드 인덱스"""
        idx = int(((heading_deg + 22.5) % 360) / 45)
        return self.HEADINGS[idx], idx

    def assign_altitude(
        self, drone_id: str, heading_deg: float = 0.0,
        priority: int = 3,
    ) -> AltitudeAssignment:
        """방향 기반 고도 할당"""
        band, band_idx = self._heading_band(heading_deg)
        base_alt = self.BASE_ALTITUDES[band_idx]

        # 우선순위 기반 조정 (높은 우선순위 = 낮은 고도)
        alt = base_alt + (priority - 1) * self._separation
        alt = max(self._min_alt, min(alt, self._max_alt))

        layer = int((alt - self._min_alt) / self._separation)
        self._layer_counts[layer] = self._layer_counts.get(layer, 0) + 1

        assignment = AltitudeAssignment(
            drone_id=drone_id,
            altitude_m=alt,
            layer=layer,
            heading_band=band,
            reason=f"방향 {band}, 우선순위 P{priority}",
        )
        self._assignments[drone_id] = assignment
        return assignment

    def release(self, drone_id: str) -> bool:
        assignment = self._assignments.pop(drone_id, None)
        if assignment:
            layer = assignment.layer
            self._layer_counts[layer] = max(0, self._layer_counts.get(layer, 0) - 1)
            return True
        return False

    def get_assignment(self, drone_id: str) -> AltitudeAssignment | None:
        return self._assignments.get(drone_id)

    def layer_density(self, layer: int) -> int:
        return self._layer_counts.get(layer, 0)

    def congested_layers(self, threshold: int = 5) -> list[int]:
        return [l for l, c in self._layer_counts.items() if c >= threshold]

    def reassign_congested(self, max_per_layer: int = 5) -> list[AltitudeAssignment]:
        """혼잡 레이어의 드론을 재할당"""
        reassigned = []
        congested = self.congested_layers(max_per_layer)
        if not congested:
            return []

        for drone_id, assignment in list(self._assignments.items()):
            if assignment.layer in congested:
                # 덜 혼잡한 인접 레이어로 이동
                for offset in [1, -1, 2, -2]:
                    new_layer = assignment.layer + offset
                    new_alt = self._min_alt + new_layer * self._separation
                    if (self._min_alt <= new_alt <= self._max_alt
                            and self.layer_density(new_layer) < max_per_layer):
                        self.release(drone_id)
                        new_assignment = AltitudeAssignment(
                            drone_id=drone_id, altitude_m=new_alt,
                            layer=new_layer, heading_band=assignment.heading_band,
                            reason=f"혼잡 회피: L{assignment.layer} → L{new_layer}",
                        )
                        self._assignments[drone_id] = new_assignment
                        self._layer_counts[new_layer] = self._layer_counts.get(new_layer, 0) + 1
                        reassigned.append(new_assignment)
                        break

        return reassigned

    def vertical_separation_ok(self, drone_a: str, drone_b: str) -> bool:
        """두 드론 간 수직 분리 확인"""
        a = self._assignments.get(drone_a)
        b = self._assignments.get(drone_b)
        if not a or not b:
            return True
        return abs(a.altitude_m - b.altitude_m) >= self._separation

    def summary(self) -> dict[str, Any]:
        return {
            "total_assigned": len(self._assignments),
            "layers_used": len([l for l, c in self._layer_counts.items() if c > 0]),
            "congested_layers": len(self.congested_layers()),
            "avg_altitude": round(
                np.mean([a.altitude_m for a in self._assignments.values()]) if self._assignments else 0, 1
            ),
        }
