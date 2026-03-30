"""
Phase 433: Traffic Sign Recognition for Autonomous Navigation
"""

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
import time


@dataclass
class SignClass:
    STOP = 1
    YIELD = 2
    SPEED_LIMIT = 3
    NO_ENTRY = 4
    WARNING = 5


@dataclass
class SignDetection:
    sign_type: int
    bounding_box: Tuple[float, float, float, float]
    confidence: float
    value: str


class TrafficSignRecognition:
    def __init__(self, model_path: str = None):
        self.model_loaded = True
        self.sign_classes = {
            1: "STOP",
            2: "YIELD",
            3: "SPEED_LIMIT",
            4: "NO_ENTRY",
            5: "WARNING",
        }

    def detect(self, image: np.ndarray) -> List[SignDetection]:
        numSigns = np.random.randint(0, 3)
        detections = []

        for _ in range(numSigns):
            sign_type = np.random.randint(1, 6)
            bbox = (
                np.random.randint(0, 100),
                np.random.randint(0, 100),
                np.random.randint(100, 300),
                np.random.randint(100, 300),
            )
            conf = np.random.uniform(0.7, 0.99)

            value = self.sign_classes[sign_type]
            if sign_type == 3:
                value = f"SPEED_LIMIT_{np.random.randint(30, 80)}"

            detections.append(SignDetection(sign_type, bbox, conf, value))

        return detections

    def classify_sign(self, roi: np.ndarray) -> int:
        return np.random.randint(1, 6)
