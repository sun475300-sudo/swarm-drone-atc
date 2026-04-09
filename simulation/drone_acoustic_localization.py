# Phase 546: Drone Acoustic Localization — TDOA & Beamforming
"""
음향 위치추정: TDOA(Time Difference of Arrival) 기반 다중 마이크 위치추정,
딜레이-앤-섬 빔포밍, 도플러 보정.
"""

import numpy as np
from dataclasses import dataclass, field


SOUND_SPEED = 343.0  # m/s


@dataclass
class Microphone:
    mic_id: str
    position: np.ndarray  # [x, y, z]


@dataclass
class AcousticSource:
    source_id: str
    position: np.ndarray
    frequency_hz: float
    power_db: float


@dataclass
class TDOAMeasurement:
    mic_pair: tuple  # (mic_i, mic_j)
    tdoa_s: float
    confidence: float


@dataclass
class LocalizationResult:
    estimated_position: np.ndarray
    true_position: np.ndarray
    error_m: float
    method: str


class TDOALocalizer:
    """TDOA 기반 음향 위치추정."""

    def __init__(self, mics: list[Microphone], seed=42):
        self.mics = mics
        self.rng = np.random.default_rng(seed)

    def compute_tdoa(self, source_pos: np.ndarray, noise_std=1e-5) -> list[TDOAMeasurement]:
        measurements = []
        n = len(self.mics)
        for i in range(n):
            for j in range(i + 1, n):
                d_i = np.linalg.norm(source_pos - self.mics[i].position) / SOUND_SPEED
                d_j = np.linalg.norm(source_pos - self.mics[j].position) / SOUND_SPEED
                tdoa = d_i - d_j + self.rng.normal(0, noise_std)
                conf = max(0.3, 1.0 - abs(self.rng.normal(0, 0.1)))
                measurements.append(TDOAMeasurement((i, j), tdoa, conf))
        return measurements

    def localize(self, measurements: list[TDOAMeasurement]) -> np.ndarray:
        """최소자승 TDOA 위치추정 (그리드 탐색 근사)."""
        best_pos = np.zeros(3)
        best_err = float('inf')

        # 그리드 탐색
        for x in np.linspace(-100, 100, 20):
            for y in np.linspace(-100, 100, 20):
                for z in [0, 25, 50, 75]:
                    candidate = np.array([x, y, z])
                    err = 0.0
                    for m in measurements:
                        i, j = m.mic_pair
                        d_i = np.linalg.norm(candidate - self.mics[i].position)
                        d_j = np.linalg.norm(candidate - self.mics[j].position)
                        predicted_tdoa = (d_i - d_j) / SOUND_SPEED
                        err += m.confidence * (predicted_tdoa - m.tdoa_s) ** 2
                    if err < best_err:
                        best_err = err
                        best_pos = candidate
        return best_pos


class Beamformer:
    """딜레이-앤-섬 빔포밍."""

    def __init__(self, mics: list[Microphone]):
        self.mics = mics

    def steer(self, direction: np.ndarray, frequency_hz: float) -> np.ndarray:
        """빔 조향 가중치 계산."""
        direction = direction / (np.linalg.norm(direction) + 1e-10)
        wavelength = SOUND_SPEED / frequency_hz
        weights = []
        for mic in self.mics:
            delay = np.dot(mic.position, direction) / SOUND_SPEED
            phase = 2 * np.pi * frequency_hz * delay
            weights.append(np.exp(-1j * phase))
        return np.array(weights) / len(self.mics)

    def power_map(self, frequency_hz=1000, resolution=10) -> np.ndarray:
        """방위별 빔 파워 맵."""
        powers = []
        for az in range(0, 360, resolution):
            az_rad = np.radians(az)
            direction = np.array([np.cos(az_rad), np.sin(az_rad), 0])
            weights = self.steer(direction, frequency_hz)
            power = float(np.abs(weights.sum()) ** 2)
            powers.append(power)
        return np.array(powers)


class DroneAcousticLocalization:
    """드론 음향 위치추정 시뮬레이션."""

    def __init__(self, n_mics=6, n_sources=5, seed=42):
        self.rng = np.random.default_rng(seed)
        self.mics = [
            Microphone(f"MIC_{i}", self.rng.uniform(-50, 50, 3))
            for i in range(n_mics)
        ]
        self.sources = [
            AcousticSource(f"SRC_{i}", self.rng.uniform(-80, 80, 3),
                           200 + self.rng.uniform(0, 800), 60 + self.rng.uniform(0, 30))
            for i in range(n_sources)
        ]
        self.localizer = TDOALocalizer(self.mics, seed)
        self.beamformer = Beamformer(self.mics)
        self.results: list[LocalizationResult] = []

    def localize_all(self):
        for src in self.sources:
            tdoa = self.localizer.compute_tdoa(src.position)
            est = self.localizer.localize(tdoa)
            err = float(np.linalg.norm(est - src.position))
            self.results.append(LocalizationResult(est, src.position, err, "TDOA"))

    def summary(self):
        if not self.results:
            self.localize_all()
        avg_err = float(np.mean([r.error_m for r in self.results]))
        min_err = float(np.min([r.error_m for r in self.results]))
        return {
            "microphones": len(self.mics),
            "sources": len(self.sources),
            "avg_error_m": round(avg_err, 2),
            "min_error_m": round(min_err, 2),
            "localizations": len(self.results),
        }


if __name__ == "__main__":
    dal = DroneAcousticLocalization(6, 5, 42)
    dal.localize_all()
    for k, v in dal.summary().items():
        print(f"  {k}: {v}")
