"""
멀티 모달 센서
=============
카메라/라이다/레이더 통합 + 객체 인식.

사용법:
    ms = MultimodalSensor()
    ms.add_sensor("d1", "CAMERA", accuracy=0.9, range_m=200)
    detections = ms.detect("d1", objects=[{"id":"o1","pos":(100,200,50)}])
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import numpy as np


@dataclass
class Sensor:
    sensor_type: str  # CAMERA, LIDAR, RADAR, IR, ULTRASONIC
    accuracy: float = 0.9
    range_m: float = 200
    fov_deg: float = 120
    active: bool = True


@dataclass
class Detection:
    object_id: str
    sensor_type: str
    position: tuple[float, float, float]
    confidence: float
    distance: float


class MultimodalSensor:
    def __init__(self, seed: int = 42) -> None:
        self._rng = np.random.default_rng(seed)
        self._sensors: dict[str, list[Sensor]] = {}
        self._detections: list[Detection] = []

    def add_sensor(self, drone_id: str, sensor_type: str, accuracy: float = 0.9, range_m: float = 200) -> None:
        if drone_id not in self._sensors:
            self._sensors[drone_id] = []
        self._sensors[drone_id].append(Sensor(sensor_type=sensor_type, accuracy=accuracy, range_m=range_m))

    def detect(self, drone_id: str, drone_pos: tuple[float, float, float] = (0,0,50), objects: list[dict] | None = None) -> list[Detection]:
        sensors = self._sensors.get(drone_id, [])
        if not sensors or not objects:
            return []

        detections = []
        for obj in objects:
            obj_pos = obj.get("pos", (0, 0, 0))
            dist = float(np.sqrt(sum((a-b)**2 for a, b in zip(drone_pos, obj_pos))))

            for sensor in sensors:
                if not sensor.active or dist > sensor.range_m:
                    continue
                if self._rng.random() < sensor.accuracy:
                    noise = self._rng.normal(0, dist * 0.02, size=3)
                    measured_pos = tuple(round(p + n, 1) for p, n in zip(obj_pos, noise))
                    confidence = sensor.accuracy * (1 - dist / sensor.range_m)
                    det = Detection(
                        object_id=obj["id"], sensor_type=sensor.sensor_type,
                        position=measured_pos, confidence=round(confidence, 3),
                        distance=round(dist, 1),
                    )
                    detections.append(det)

        self._detections.extend(detections)
        return detections

    def fuse_detections(self, object_id: str) -> tuple[float, float, float] | None:
        dets = [d for d in self._detections if d.object_id == object_id]
        if not dets:
            return None
        weights = [d.confidence for d in dets]
        total_w = sum(weights)
        if total_w == 0:
            return None
        fused = tuple(
            round(sum(d.position[i] * d.confidence for d in dets) / total_w, 1)
            for i in range(3)
        )
        return fused

    def summary(self) -> dict[str, Any]:
        return {
            "drones_with_sensors": len(self._sensors),
            "total_sensors": sum(len(s) for s in self._sensors.values()),
            "total_detections": len(self._detections),
        }
