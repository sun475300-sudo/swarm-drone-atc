"""
Phase 430: Swarm Collaborative Perception for Extended Sensing
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import time


class PerceptionModality(Enum):
    VISUAL = "visual"
    THERMAL = "thermal"
    LIDAR = "lidar"
    RADAR = "radar"
    ACOUSTIC = "acoustic"


@dataclass
class PerceptionFrame:
    frame_id: str
    drone_id: str
    modality: PerceptionModality
    data: np.ndarray
    timestamp: float
    position: np.ndarray


@dataclass
class FusedPerception:
    frame_id: str
    fused_data: np.ndarray
    confidence_map: np.ndarray
    contributing_drones: List[str]
    timestamp: float


class SwarmCollaborativePerception:
    def __init__(self, fusion_range_m: float = 100.0):
        self.fusion_range_m = fusion_range_m

        self.perception_frames: Dict[
            Tuple[str, PerceptionModality], PerceptionFrame
        ] = {}
        self.fusion_cache: List[FusedPerception] = []

        self.coverage_map: np.ndarray = np.zeros((1000, 1000))

    def add_frame(self, frame: PerceptionFrame):
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
    ) -> Optional[FusedPerception]:
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

    def get_coverage_stats(self) -> Dict[str, Any]:
        covered_cells = np.sum(self.coverage_map > 0)
        total_cells = self.coverage_map.size

        return {
            "coverage_percentage": covered_cells / total_cells * 100,
            "covered_cells": int(covered_cells),
            "total_cells": total_cells,
            "active_modalities": len(
                set(f.modality for f in self.perception_frames.values())
            ),
        }

    def estimate_occlusion(
        self, viewpoint: np.ndarray, target_position: np.ndarray
    ) -> float:
        occlusion_score = np.random.uniform(0.0, 0.3)

        return occlusion_score
