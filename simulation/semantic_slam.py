# Phase 536: Semantic SLAM — Landmark-Based Map Building
"""
의미론적 SLAM: 랜드마크 감지, 포즈 그래프 최적화,
의미 태그(건물/도로/장애물)가 포함된 지도 작성.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum


class LandmarkType(Enum):
    BUILDING = "building"
    ROAD = "road"
    TREE = "tree"
    OBSTACLE = "obstacle"
    LANDING_PAD = "landing_pad"
    UNKNOWN = "unknown"


@dataclass
class Landmark:
    landmark_id: str
    ltype: LandmarkType
    position: np.ndarray  # [x, y, z]
    confidence: float
    observations: int = 1


@dataclass
class Pose:
    pose_id: int
    position: np.ndarray  # [x, y, z]
    heading: float  # rad
    timestamp: float


@dataclass
class Observation:
    pose_id: int
    landmark_id: str
    bearing: float
    distance: float
    ltype: LandmarkType


class PoseGraph:
    """포즈 그래프: 간이 최적화."""

    def __init__(self):
        self.poses: list[Pose] = []
        self.edges: list[tuple[int, int, np.ndarray]] = []  # (from, to, delta)

    def add_pose(self, pose: Pose):
        if self.poses:
            delta = pose.position - self.poses[-1].position
            self.edges.append((len(self.poses) - 1, len(self.poses), delta))
        self.poses.append(pose)

    def optimize(self, iterations=5, lr=0.1):
        """간이 그래디언트 기반 최적화."""
        for _ in range(iterations):
            for i, j, delta in self.edges:
                actual_delta = self.poses[j].position - self.poses[i].position
                error = actual_delta - delta
                self.poses[j].position -= lr * error * 0.5
                self.poses[i].position += lr * error * 0.5


class LandmarkMap:
    """의미론적 랜드마크 지도."""

    def __init__(self):
        self.landmarks: dict[str, Landmark] = {}

    def update(self, obs: Observation, observer_pos: np.ndarray):
        bearing_rad = obs.bearing
        dx = obs.distance * np.cos(bearing_rad)
        dy = obs.distance * np.sin(bearing_rad)
        est_pos = observer_pos + np.array([dx, dy, 0.0])

        if obs.landmark_id in self.landmarks:
            lm = self.landmarks[obs.landmark_id]
            # 가중 평균 업데이트
            w = lm.observations / (lm.observations + 1)
            lm.position = w * lm.position + (1 - w) * est_pos
            lm.observations += 1
            lm.confidence = min(0.99, lm.confidence + 0.05)
        else:
            self.landmarks[obs.landmark_id] = Landmark(
                obs.landmark_id, obs.ltype, est_pos, 0.5
            )

    def query_nearby(self, pos: np.ndarray, radius=50.0) -> list[Landmark]:
        result = []
        for lm in self.landmarks.values():
            if np.linalg.norm(lm.position - pos) <= radius:
                result.append(lm)
        return result


class SemanticSLAM:
    """의미론적 SLAM 시뮬레이션."""

    def __init__(self, n_landmarks=40, seed=42):
        self.rng = np.random.default_rng(seed)
        self.graph = PoseGraph()
        self.lmap = LandmarkMap()
        self.n_landmarks = n_landmarks
        self.true_landmarks: list[tuple[str, LandmarkType, np.ndarray]] = []
        self._generate_landmarks()

    def _generate_landmarks(self):
        types = list(LandmarkType)
        for i in range(self.n_landmarks):
            pos = self.rng.uniform(-200, 200, 3)
            pos[2] = self.rng.uniform(0, 30)
            ltype = types[int(self.rng.integers(0, len(types)))]
            self.true_landmarks.append((f"LM_{i:04d}", ltype, pos))

    def run_trajectory(self, n_steps=50, speed=3.0):
        """드론 궤적 시뮬레이션 + 랜드마크 관측."""
        pos = np.array([0.0, 0.0, 50.0])
        heading = 0.0

        for step in range(n_steps):
            heading += self.rng.normal(0, 0.1)
            delta = speed * np.array([np.cos(heading), np.sin(heading), self.rng.normal(0, 0.2)])
            pos = pos + delta
            pose = Pose(step, pos.copy(), heading, float(step))
            self.graph.add_pose(pose)

            # 근방 랜드마크 관측
            for lm_id, ltype, lm_pos in self.true_landmarks:
                dist = np.linalg.norm(pos[:2] - lm_pos[:2])
                if dist < 100.0 and self.rng.random() < 0.6:
                    bearing = np.arctan2(lm_pos[1] - pos[1], lm_pos[0] - pos[0])
                    bearing += self.rng.normal(0, 0.05)  # noise
                    dist += self.rng.normal(0, 2.0)
                    obs = Observation(step, lm_id, bearing, max(1.0, dist), ltype)
                    self.lmap.update(obs, pos)

    def optimize(self):
        self.graph.optimize(iterations=5)

    def summary(self):
        return {
            "poses": len(self.graph.poses),
            "landmarks_mapped": len(self.lmap.landmarks),
            "landmarks_true": self.n_landmarks,
            "avg_confidence": float(np.mean([l.confidence for l in self.lmap.landmarks.values()]))
                if self.lmap.landmarks else 0.0,
            "avg_observations": float(np.mean([l.observations for l in self.lmap.landmarks.values()]))
                if self.lmap.landmarks else 0.0,
        }


if __name__ == "__main__":
    slam = SemanticSLAM(40, 42)
    slam.run_trajectory(80)
    slam.optimize()
    s = slam.summary()
    for k, v in s.items():
        print(f"  {k}: {v}")
