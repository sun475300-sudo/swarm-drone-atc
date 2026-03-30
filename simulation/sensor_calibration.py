"""
Sensor Calibration System
Phase 391 - IMU, Compass, Barometer Calibration
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class CalibrationData:
    raw: np.ndarray
    calibrated: np.ndarray
    offset: np.ndarray
    scale: np.ndarray


class IMUCalibrator:
    def __init__(self):
        self.offset = np.zeros(3)
        self.scale = np.ones(3)

    def calibrate(self, samples: list) -> CalibrationData:
        data = np.array(samples)
        self.offset = np.mean(data, axis=0)
        std = np.std(data, axis=0)
        self.scale = 1.0 / (std + 1e-6)

        calibrated = (data - self.offset) * self.scale
        return CalibrationData(data, calibrated, self.offset, self.scale)


def simulate_calibration():
    print("=== Sensor Calibration ===")
    calib = IMUCalibrator()
    samples = [np.random.randn(3) * 2 + [1, 2, 3] for _ in range(100)]
    result = calib.calibrate(samples)
    print(f"Offset: {result.offset}")
    return {"offset": result.offset.tolist()}


if __name__ == "__main__":
    simulate_calibration()
