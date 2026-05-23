"""
Phase 462: Object Tracking System for Moving Target Following
"""

import time
from dataclasses import dataclass

import numpy as np


@dataclass
class TrackedObject:
    object_id: str
    position: np.ndarray
    velocity: np.ndarray
    last_seen: float
    confidence: float


class ObjectTrackingSystem:
    def __init__(self):
        self.tracked_objects: dict[str, TrackedObject] = {}
        self.track_history: dict[str, list] = {}

    def update(self, detections: list[dict]) -> list[TrackedObject]:
        for det in detections:
            obj_id = det.get("id", f"obj_{det['class_id']}")

            if obj_id in self.tracked_objects:
                obj = self.tracked_objects[obj_id]
                obj.position = np.array(det["position"])
                obj.velocity = np.array(det.get("velocity", [0, 0, 0]))
                obj.last_seen = time.time()
                obj.confidence = det.get("confidence", 0.8)
            else:
                self.tracked_objects[obj_id] = TrackedObject(
                    object_id=obj_id,
                    position=np.array(det["position"]),
                    velocity=np.array(det.get("velocity", [0, 0, 0])),
                    last_seen=time.time(),
                    confidence=det.get("confidence", 0.8),
                )

        return list(self.tracked_objects.values())

    def predict_position(self, object_id: str, dt: float) -> np.ndarray:
        if object_id not in self.tracked_objects:
            return np.zeros(3)

        obj = self.tracked_objects[object_id]
        return obj.position + obj.velocity * dt
