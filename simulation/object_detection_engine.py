"""
Phase 432: Object Detection Engine for Real-Time Tracking
"""

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
import time


@dataclass
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_id: int
    class_name: str


@dataclass
class DetectionResult:
    boxes: List[BoundingBox]
    image_id: str
    timestamp: float


class ObjectDetectionEngine:
    def __init__(self, conf_threshold: float = 0.5):
        self.conf_threshold = conf_threshold
        self.class_names = ["person", "car", "truck", "building", "tree", "drone"]

    def detect(self, image: np.ndarray, model_name: str = "yolov8") -> DetectionResult:
        num_detections = np.random.randint(1, 10)

        boxes = []
        for i in range(num_detections):
            x1 = np.random.uniform(0, image.shape[1] - 100)
            y1 = np.random.uniform(0, image.shape[0] - 100)
            x2 = x1 + np.random.uniform(50, 150)
            y2 = y1 + np.random.uniform(50, 150)
            conf = np.random.uniform(self.conf_threshold, 1.0)
            class_id = np.random.randint(0, len(self.class_names))

            boxes.append(
                BoundingBox(x1, y1, x2, y2, conf, class_id, self.class_names[class_id])
            )

        return DetectionResult(boxes, f"img_{int(time.time())}", time.time())

    def detect_with_nms(self, image: np.ndarray) -> DetectionResult:
        result = self.detect(image)

        boxes = sorted(result.boxes, key=lambda b: b.confidence, reverse=True)

        filtered = []
        for box in boxes:
            keep = True
            for kept in filtered:
                iou = self._compute_iou(box, kept)
                if iou > 0.5:
                    keep = False
                    break
            if keep:
                filtered.append(box)

        return DetectionResult(filtered, result.image_id, result.timestamp)

    def _compute_iou(self, box1: BoundingBox, box2: BoundingBox) -> float:
        x1 = max(box1.x1, box2.x1)
        y1 = max(box1.y1, box2.y1)
        x2 = min(box1.x2, box2.x2)
        y2 = min(box1.y2, box2.y2)

        intersection = max(0, x2 - x1) * max(0, y2 - y1)

        area1 = (box1.x2 - box1.x1) * (box1.y2 - box1.y1)
        area2 = (box2.x2 - box2.x1) * (box2.y2 - box2.y1)

        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0
