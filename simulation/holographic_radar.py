"""
Phase 473: Holographic Radar Simulation
SAR 이미징 + 위상배열 빔포밍 + 도플러 처리.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple


class RadarMode(Enum):
    SEARCH = "search"
    TRACK = "track"
    SAR = "sar"
    WEATHER = "weather"


@dataclass
class RadarTarget:
    target_id: str
    x: float; y: float; z: float
    vx: float = 0; vy: float = 0; vz: float = 0
    rcs: float = 1.0  # radar cross section m²


@dataclass
class RadarDetection:
    target_id: str
    range_m: float
    azimuth_deg: float
    elevation_deg: float
    doppler_hz: float
    snr_db: float
    timestamp: float


@dataclass
class AntennaElement:
    x: float; y: float; z: float
    weight: complex = 1.0 + 0j


class PhasedArray:
    """Phased array antenna for beam steering."""

    def __init__(self, n_elements: int = 16, spacing: float = 0.015,
                 freq_hz: float = 10e9):
        self.freq = freq_hz
        self.wavelength = 3e8 / freq_hz
        self.elements = []
        side = int(np.sqrt(n_elements))
        for i in range(side):
            for j in range(side):
                self.elements.append(AntennaElement(i * spacing, j * spacing, 0))

    def steer(self, az_deg: float, el_deg: float) -> None:
        az, el = np.radians(az_deg), np.radians(el_deg)
        k = 2 * np.pi / self.wavelength
        for elem in self.elements:
            phase = k * (elem.x * np.sin(az) * np.cos(el) + elem.y * np.sin(el))
            elem.weight = np.exp(-1j * phase)

    def gain(self, az_deg: float, el_deg: float) -> float:
        az, el = np.radians(az_deg), np.radians(el_deg)
        k = 2 * np.pi / self.wavelength
        af = 0 + 0j
        for elem in self.elements:
            phase = k * (elem.x * np.sin(az) * np.cos(el) + elem.y * np.sin(el))
            af += elem.weight * np.exp(1j * phase)
        return float(np.abs(af) ** 2 / len(self.elements) ** 2)


class HolographicRadar:
    """Holographic radar with SAR and phased array."""

    def __init__(self, freq_hz: float = 10e9, power_w: float = 100,
                 n_elements: int = 16, seed: int = 42):
        self.freq = freq_hz
        self.power = power_w
        self.wavelength = 3e8 / freq_hz
        self.antenna = PhasedArray(n_elements, freq_hz=freq_hz)
        self.rng = np.random.default_rng(seed)
        self.position = np.array([0.0, 0.0, 50.0])
        self.mode = RadarMode.SEARCH
        self.targets: Dict[str, RadarTarget] = {}
        self.detections: List[RadarDetection] = []
        self.scan_count = 0

    def add_target(self, target: RadarTarget) -> None:
        self.targets[target.target_id] = target

    def _range_to(self, target: RadarTarget) -> float:
        return float(np.sqrt((target.x - self.position[0])**2 +
                             (target.y - self.position[1])**2 +
                             (target.z - self.position[2])**2))

    def _angles_to(self, target: RadarTarget) -> Tuple[float, float]:
        dx = target.x - self.position[0]
        dy = target.y - self.position[1]
        dz = target.z - self.position[2]
        r = np.sqrt(dx**2 + dy**2 + dz**2)
        az = np.degrees(np.arctan2(dy, dx))
        el = np.degrees(np.arcsin(dz / max(r, 1e-10)))
        return az, el

    def _doppler(self, target: RadarTarget) -> float:
        dx = target.x - self.position[0]
        dy = target.y - self.position[1]
        dz = target.z - self.position[2]
        r = max(np.sqrt(dx**2 + dy**2 + dz**2), 1e-10)
        v_radial = (dx * target.vx + dy * target.vy + dz * target.vz) / r
        return 2 * v_radial * self.freq / 3e8

    def _snr(self, target: RadarTarget, gain: float) -> float:
        r = self._range_to(target)
        # Simplified radar equation
        numerator = self.power * gain * target.rcs * self.wavelength**2
        denominator = (4 * np.pi)**3 * r**4 * 1e-21  # noise floor
        snr_linear = numerator / max(denominator, 1e-30)
        return float(10 * np.log10(max(snr_linear, 1e-10)))

    def scan(self, timestamp: float = 0.0) -> List[RadarDetection]:
        self.scan_count += 1
        new_detections = []

        for target in self.targets.values():
            az, el = self._angles_to(target)
            self.antenna.steer(az, el)
            gain = self.antenna.gain(az, el)
            snr = self._snr(target, gain)

            # Detection threshold
            if snr > 10:
                noise_az = self.rng.standard_normal() * 0.5
                noise_el = self.rng.standard_normal() * 0.5
                noise_r = self.rng.standard_normal() * 5

                det = RadarDetection(
                    target_id=target.target_id,
                    range_m=self._range_to(target) + noise_r,
                    azimuth_deg=az + noise_az,
                    elevation_deg=el + noise_el,
                    doppler_hz=self._doppler(target),
                    snr_db=snr,
                    timestamp=timestamp
                )
                new_detections.append(det)
                self.detections.append(det)

        return new_detections

    def sar_image(self, grid_size: int = 32, area_m: float = 500) -> np.ndarray:
        """Generate simplified SAR image."""
        image = np.zeros((grid_size, grid_size))
        for target in self.targets.values():
            gx = int((target.x / area_m + 0.5) * grid_size)
            gy = int((target.y / area_m + 0.5) * grid_size)
            if 0 <= gx < grid_size and 0 <= gy < grid_size:
                r = self._range_to(target)
                intensity = target.rcs / max(r**2, 1) * 1000
                image[gy, gx] += intensity
                # PSF spread
                for di in range(-1, 2):
                    for dj in range(-1, 2):
                        ni, nj = gy + di, gx + dj
                        if 0 <= ni < grid_size and 0 <= nj < grid_size:
                            image[ni, nj] += intensity * 0.2
        return image

    def summary(self) -> Dict:
        return {
            "mode": self.mode.value,
            "freq_ghz": self.freq / 1e9,
            "power_w": self.power,
            "elements": len(self.antenna.elements),
            "targets": len(self.targets),
            "total_detections": len(self.detections),
            "scans": self.scan_count,
        }
