"""
Phase 513: Cooperative Perception
다중 드론 협력 인식, 분산 물체 추적, 뷰 퓨전.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple


class ObjectClass(Enum):
    VEHICLE = "vehicle"
    PEDESTRIAN = "pedestrian"
    DRONE = "drone"
    BUILDING = "building"
    UNKNOWN = "unknown"


@dataclass
class Detection:
    detector_id: str
    object_id: str
    obj_class: ObjectClass
    position: np.ndarray
    confidence: float
    timestamp: float
    bbox: Tuple[float, float, float, float] = (0, 0, 0, 0)


@dataclass
class TrackedObject:
    track_id: str
    obj_class: ObjectClass
    position: np.ndarray
    velocity: np.ndarray
    detections: int
    confidence: float
    last_seen: float


class MultiViewFusion:
    """Fuse detections from multiple drone viewpoints."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.association_threshold = 10.0  # meters

    def fuse(self, detections: List[Detection]) -> List[TrackedObject]:
        if not detections:
            return []
        clusters: List[List[Detection]] = []
        used = set()

        for i, d in enumerate(detections):
            if i in used:
                continue
            cluster = [d]
            used.add(i)
            for j in range(i + 1, len(detections)):
                if j in used:
                    continue
                dist = np.linalg.norm(d.position - detections[j].position)
                if dist < self.association_threshold:
                    cluster.append(detections[j])
                    used.add(j)
            clusters.append(cluster)

        tracks = []
        for idx, cluster in enumerate(clusters):
            weights = np.array([d.confidence for d in cluster])
            weights /= weights.sum() + 1e-10
            pos = sum(w * d.position for w, d in zip(weights, cluster))
            conf = 1 - np.prod([1 - d.confidence for d in cluster])
            cls_votes = {}
            for d in cluster:
                cls_votes[d.obj_class] = cls_votes.get(d.obj_class, 0) + d.confidence
            best_cls = max(cls_votes, key=cls_votes.get)

            tracks.append(TrackedObject(
                f"T-{idx:04d}", best_cls, pos, np.zeros(3),
                len(cluster), round(float(conf), 4), cluster[-1].timestamp))
        return tracks


class DistributedTracker:
    """Multi-object tracking across drone swarm."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.tracks: Dict[str, TrackedObject] = {}
        self._track_counter = 0

    def update(self, new_tracks: List[TrackedObject]) -> Dict[str, TrackedObject]:
        for nt in new_tracks:
            matched = False
            for tid, existing in self.tracks.items():
                dist = np.linalg.norm(existing.position - nt.position)
                if dist < 15 and existing.obj_class == nt.obj_class:
                    alpha = 0.7
                    existing.velocity = (nt.position - existing.position) / 0.1
                    existing.position = alpha * nt.position + (1 - alpha) * existing.position
                    existing.confidence = max(existing.confidence, nt.confidence)
                    existing.detections += nt.detections
                    existing.last_seen = nt.last_seen
                    matched = True
                    break
            if not matched:
                self._track_counter += 1
                tid = f"GT-{self._track_counter:05d}"
                nt.track_id = tid
                self.tracks[tid] = nt
        return self.tracks


class CooperativePerception:
    """Multi-drone cooperative perception system."""

    def __init__(self, n_drones: int = 6, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.fusion = MultiViewFusion(seed)
        self.tracker = DistributedTracker(seed)
        self.drone_positions = self.rng.uniform(-200, 200, (n_drones, 3))
        self.drone_positions[:, 2] = self.rng.uniform(30, 100, n_drones)
        self._det_counter = 0

    def simulate_detections(self, n_objects: int = 20) -> List[Detection]:
        objects = self.rng.uniform(-150, 150, (n_objects, 3))
        objects[:, 2] = 0
        classes = self.rng.choice(list(ObjectClass)[:-1], n_objects)
        detections = []

        for drone_idx in range(self.n_drones):
            for obj_idx in range(n_objects):
                dist = np.linalg.norm(self.drone_positions[drone_idx] - objects[obj_idx])
                if dist > 200:
                    continue
                detect_prob = max(0.3, 1 - dist / 250)
                if self.rng.random() > detect_prob:
                    continue
                self._det_counter += 1
                noise = self.rng.standard_normal(3) * (dist / 100)
                pos_est = objects[obj_idx] + noise
                conf = max(0.2, detect_prob - self.rng.uniform(0, 0.2))
                detections.append(Detection(
                    f"drone_{drone_idx}", f"obj_{obj_idx}",
                    classes[obj_idx], pos_est, round(conf, 3), 0.0))
        return detections

    def perceive(self, n_objects: int = 20) -> Dict:
        dets = self.simulate_detections(n_objects)
        fused = self.fusion.fuse(dets)
        self.tracker.update(fused)
        return {
            "raw_detections": len(dets),
            "fused_tracks": len(fused),
            "global_tracks": len(self.tracker.tracks),
        }

    def summary(self) -> Dict:
        return {
            "drones": self.n_drones,
            "total_detections": self._det_counter,
            "active_tracks": len(self.tracker.tracks),
            "avg_confidence": round(
                np.mean([t.confidence for t in self.tracker.tracks.values()])
                if self.tracker.tracks else 0, 4),
        }
