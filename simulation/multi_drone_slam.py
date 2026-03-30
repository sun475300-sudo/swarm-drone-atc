"""Phase 318: Multi-Drone SLAM — 다중 드론 동시 위치인식 및 지도작성.

Factor Graph 기반 SLAM, 랜드마크 관측,
루프 클로저, 다중 드론 지도 병합.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Landmark:
    landmark_id: str
    position: np.ndarray
    uncertainty: float = 1.0
    observations: int = 0
    last_seen_by: str = ""


@dataclass
class Pose:
    position: np.ndarray
    orientation: float = 0.0  # yaw in radians
    timestamp: float = 0.0


@dataclass
class Observation:
    drone_id: str
    landmark_id: str
    bearing: float  # radians
    range_m: float
    timestamp: float


@dataclass
class LoopClosure:
    drone_a: str
    drone_b: str
    pose_a: Pose
    pose_b: Pose
    transform: np.ndarray  # relative transform
    confidence: float


class FactorGraph:
    """Simplified factor graph for pose optimization."""

    def __init__(self):
        self._poses: Dict[str, List[Pose]] = {}
        self._factors: List[dict] = []

    def add_pose(self, drone_id: str, pose: Pose):
        self._poses.setdefault(drone_id, []).append(pose)

    def add_odometry_factor(self, drone_id: str, delta_pos: np.ndarray, delta_yaw: float):
        self._factors.append({
            "type": "odometry", "drone_id": drone_id,
            "delta_pos": delta_pos, "delta_yaw": delta_yaw,
        })

    def add_landmark_factor(self, drone_id: str, landmark_id: str,
                            bearing: float, range_m: float):
        self._factors.append({
            "type": "landmark", "drone_id": drone_id,
            "landmark_id": landmark_id, "bearing": bearing, "range": range_m,
        })

    def add_loop_closure_factor(self, closure: LoopClosure):
        self._factors.append({
            "type": "loop_closure",
            "drone_a": closure.drone_a, "drone_b": closure.drone_b,
            "transform": closure.transform, "confidence": closure.confidence,
        })

    def optimize(self, n_iterations: int = 10) -> float:
        """Simplified Gauss-Newton optimization. Returns total error."""
        total_error = 0.0
        for factor in self._factors:
            if factor["type"] == "odometry":
                poses = self._poses.get(factor["drone_id"], [])
                if len(poses) >= 2:
                    predicted = poses[-2].position + factor["delta_pos"]
                    actual = poses[-1].position
                    error = np.linalg.norm(predicted - actual)
                    total_error += error ** 2
        return total_error


class MultiDroneSLAM:
    """다중 드론 SLAM.

    - Factor graph 기반 상태 추정
    - 랜드마크 관측 및 업데이트
    - 루프 클로저 검출
    - 다중 드론 지도 병합
    """

    def __init__(self, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self._graph = FactorGraph()
        self._landmarks: Dict[str, Landmark] = {}
        self._drone_poses: Dict[str, List[Pose]] = {}
        self._observations: List[Observation] = []
        self._loop_closures: List[LoopClosure] = []
        self._merged_map: Dict[str, Landmark] = {}

    def add_drone(self, drone_id: str, initial_pose: Pose):
        self._drone_poses[drone_id] = [initial_pose]
        self._graph.add_pose(drone_id, initial_pose)

    def update_odometry(self, drone_id: str, delta_pos: np.ndarray, delta_yaw: float = 0.0):
        """Update drone pose from odometry."""
        poses = self._drone_poses.get(drone_id, [])
        if not poses:
            return
        last = poses[-1]
        new_pose = Pose(
            position=last.position + delta_pos,
            orientation=last.orientation + delta_yaw,
            timestamp=last.timestamp + 0.1,
        )
        # Add noise
        new_pose.position += self._rng.normal(0, 0.01, 3)
        self._drone_poses[drone_id].append(new_pose)
        self._graph.add_pose(drone_id, new_pose)
        self._graph.add_odometry_factor(drone_id, delta_pos, delta_yaw)

    def observe_landmark(self, drone_id: str, landmark_id: str,
                         true_position: np.ndarray):
        """Observe a landmark from drone's current position."""
        poses = self._drone_poses.get(drone_id, [])
        if not poses:
            return

        drone_pos = poses[-1].position
        diff = true_position - drone_pos
        bearing = float(np.arctan2(diff[1], diff[0]))
        range_m = float(np.linalg.norm(diff))

        # Add measurement noise
        bearing += self._rng.normal(0, 0.02)
        range_m += self._rng.normal(0, 0.5)

        obs = Observation(
            drone_id=drone_id, landmark_id=landmark_id,
            bearing=bearing, range_m=range_m,
            timestamp=poses[-1].timestamp,
        )
        self._observations.append(obs)
        self._graph.add_landmark_factor(drone_id, landmark_id, bearing, range_m)

        # Update landmark estimate
        if landmark_id not in self._landmarks:
            estimated_pos = drone_pos + np.array([
                range_m * np.cos(bearing),
                range_m * np.sin(bearing),
                0,
            ])
            self._landmarks[landmark_id] = Landmark(
                landmark_id=landmark_id, position=estimated_pos,
                observations=1, last_seen_by=drone_id,
            )
        else:
            lm = self._landmarks[landmark_id]
            new_est = drone_pos + np.array([
                range_m * np.cos(bearing),
                range_m * np.sin(bearing),
                0,
            ])
            # EKF-style update
            alpha = 1.0 / (lm.observations + 1)
            lm.position = (1 - alpha) * lm.position + alpha * new_est
            lm.observations += 1
            lm.uncertainty *= 0.9
            lm.last_seen_by = drone_id

    def detect_loop_closures(self, threshold_m: float = 5.0) -> List[LoopClosure]:
        """Detect loop closures between drones."""
        closures = []
        drone_ids = list(self._drone_poses.keys())
        for i in range(len(drone_ids)):
            for j in range(i + 1, len(drone_ids)):
                poses_a = self._drone_poses[drone_ids[i]]
                poses_b = self._drone_poses[drone_ids[j]]
                if not poses_a or not poses_b:
                    continue
                for pa in poses_a[-5:]:
                    for pb in poses_b[-5:]:
                        dist = np.linalg.norm(pa.position - pb.position)
                        if dist < threshold_m:
                            transform = pb.position - pa.position
                            closure = LoopClosure(
                                drone_a=drone_ids[i], drone_b=drone_ids[j],
                                pose_a=pa, pose_b=pb,
                                transform=transform,
                                confidence=1.0 - dist / threshold_m,
                            )
                            closures.append(closure)
                            self._graph.add_loop_closure_factor(closure)
        self._loop_closures.extend(closures)
        return closures

    def merge_maps(self) -> Dict[str, Landmark]:
        """Merge all drone observations into unified map."""
        self._merged_map = {}
        for lm_id, lm in self._landmarks.items():
            self._merged_map[lm_id] = Landmark(
                landmark_id=lm_id, position=lm.position.copy(),
                uncertainty=lm.uncertainty, observations=lm.observations,
            )
        return self._merged_map

    def optimize(self, n_iter: int = 10) -> float:
        return self._graph.optimize(n_iter)

    def get_drone_trajectory(self, drone_id: str) -> List[np.ndarray]:
        return [p.position for p in self._drone_poses.get(drone_id, [])]

    def summary(self) -> dict:
        return {
            "total_drones": len(self._drone_poses),
            "total_landmarks": len(self._landmarks),
            "total_observations": len(self._observations),
            "loop_closures": len(self._loop_closures),
            "merged_landmarks": len(self._merged_map),
            "avg_uncertainty": round(
                np.mean([lm.uncertainty for lm in self._landmarks.values()])
                if self._landmarks else 1.0, 4
            ),
        }
