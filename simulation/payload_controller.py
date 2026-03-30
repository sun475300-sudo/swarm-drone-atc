"""
Payload Controller
Phase 401 - Gimbal, Camera, Cargo Management
"""

import numpy as np


class GimbalController:
    def __init__(self):
        self.roll = 0
        self.pitch = 0
        self.yaw = 0
        self.stabilization = True

    def set_target(self, roll: float, pitch: float, yaw: float):
        self.roll = roll
        self.pitch = pitch
        self.yaw = yaw

    def stabilize(self, drone_attitude):
        if self.stabilization:
            return (0 - drone_attitude[0], 0 - drone_attitude[1], 0 - drone_attitude[2])
        return (self.roll, self.pitch, self.yaw)


class CameraController:
    def __init__(self):
        self.mode = "photo"
        self.resolution = (3840, 2160)
        self.iso = 100
        self.shutter = 1 / 60

    def capture_photo(self) -> dict:
        return {"timestamp": 0, "resolution": self.resolution, "size_mb": 25}

    def start_recording(self):
        self.mode = "video"

    def stop_recording(self) -> dict:
        self.mode = "photo"
        return {"duration_sec": 60, "size_mb": 1500}


class CargoController:
    def __init__(self, max_kg: float = 10.0):
        self.max_payload = max_kg
        self.current_kg = 0.0
        self.release_mechanism = False

    def load(self, weight: float) -> bool:
        if self.current_kg + weight <= self.max_payload:
            self.current_kg += weight
            return True
        return False

    def release(self):
        self.current_kg = 0


print("=== Payload Controller ===")
gc = GimbalController()
gc.set_target(10, 20, 30)
print(f"Gimbal: {gc.roll}, {gc.pitch}, {gc.yaw}")
