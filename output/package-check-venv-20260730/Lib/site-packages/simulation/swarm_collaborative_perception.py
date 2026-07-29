"""
Phase 430: Swarm Collaborative Perception for Extended Sensing
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np


class PerceptionModality(Enum):
    """``PerceptionModality`` 관련 기능을 제공한다."""
    VISUAL = "visual"
    THERMAL = "thermal"
    LIDAR = "lidar"
    RADAR = "radar"
    ACOUSTIC = "acoustic"


@dataclass
class PerceptionFrame:
    """``PerceptionFrame`` 관련 기능을 제공한다."""
    frame_id: str
    drone_id: str
    modality: PerceptionModality
    data: np.ndarray
    timestamp: float
    position: np.ndarray


@dataclass
class FusedPerception:
    """``FusedPerception`` 관련 기능을 제공한다."""
    frame_id: str
    fused_data: np.ndarray
    confidence_map: np.ndarray
    contributing_drones: list[str]
    timestamp: float


class SwarmCollaborativePerception:
    """``SwarmCollaborativePerception`` 관련 기능을 제공한다."""
    def __init__(self, fusion_range_m: float = 100.0):
        """인스턴스를 초기화한다."""
        self.fusion_range_m = fusion_range_m

        self.perception_frames: dict[
            tuple[str, PerceptionModality], PerceptionFrame
        ] = {}
        self.fusion_cache: list[FusedPerception] = []

        self.coverage_map: np.ndarray = np.zeros((1000, 1000))

    def add_frame(self, frame: PerceptionFrame):
        """`frame` 항목을 추가한다."""
        key = (frame.drone_id, frame.modality)
        self.perception_frames[key] = frame

        self._update_coverage(frame)

    def _update_coverage(self, frame: PerceptionFrame):
        px = int(frame.position[0] + 500)
        py = int(frame.position[1] + 500)

        if 0 <= px < 1000 and 0 <= py < 1000:
            self.coverage_map[px, py] = 1.0

    def fuse_frames(
        self, modality: PerceptionModality, reference_drone: str
    ) -> FusedPerception | None:
        """``fuse_frames`` 동작을 수행한다."""
        reference_key = (reference_drone, modality)

        if reference_key not in self.perception_frames:
            return None

        reference_frame = self.perception_frames[reference_key]

        contributing = [reference_drone]

        for (drone_id, mod), frame in self.perception_frames.items():
            if mod != modality or drone_id == reference_drone:
                continue

            distance = np.linalg.norm(frame.position - reference_frame.position)

            if distance <= self.fusion_range_m:
                contributing.append(drone_id)

        if len(contributing) < 2:
            return None

        fused_data = np.random.randn(224, 224, 3)
        confidence_map = np.random.rand(224, 224)

        fused = FusedPerception(
            frame_id=f"fused_{int(time.time())}",
            fused_data=fused_data,
            confidence_map=confidence_map,
            contributing_drones=contributing,
            timestamp=time.time(),
        )

        self.fusion_cache.append(fused)

        return fused

    def get_coverage_stats(self) -> dict[str, Any]:
        """`coverage stats` 정보를 조회한다."""
        covered_cells = np.sum(self.coverage_map > 0)
        total_cells = self.coverage_map.size

        return {
            "coverage_percentage": covered_cells / total_cells * 100,
            "covered_cells": int(covered_cells),
            "total_cells": total_cells,
            "active_modalities": len(
                {f.modality for f in self.perception_frames.values()}
            ),
        }

    def estimate_occlusion(
        self, viewpoint: np.ndarray, target_position: np.ndarray
    ) -> float:
        """`occlusion` 결과를 계산하거나 판정한다."""
        occlusion_score = np.random.uniform(0.0, 0.3)

        return occlusion_score
