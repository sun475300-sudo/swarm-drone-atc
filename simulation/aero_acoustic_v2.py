"""
Phase 507: Aero-Acoustic Analysis V2
프로펠러 소음 모델링, 음향 스텔스, 도심 소음 영향 평가.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple


class NoiseSource(Enum):
    PROPELLER = "propeller"
    MOTOR = "motor"
    AIRFRAME = "airframe"
    PAYLOAD = "payload"


class NoiseRegulation(Enum):
    ICAO_ANNEX16 = "icao_annex16"
    FAA_PART36 = "faa_part36"
    EU_REG_2019 = "eu_2019"
    KUTM_NOISE = "kutm_noise"


@dataclass
class NoiseProfile:
    frequency_hz: np.ndarray
    spl_db: np.ndarray  # Sound Pressure Level
    source: NoiseSource
    rpm: float = 0.0


@dataclass
class NoiseImpact:
    location: np.ndarray
    total_spl_db: float
    dominant_source: NoiseSource
    exceeds_limit: bool
    regulation: NoiseRegulation


class PropellerNoiseModel:
    """BPF-based propeller noise prediction."""

    def __init__(self, n_blades: int = 4, diameter_m: float = 0.3, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_blades = n_blades
        self.diameter = diameter_m
        self.freqs = np.arange(20, 20000, 10)  # Hz

    def predict(self, rpm: float, thrust_n: float = 10.0) -> NoiseProfile:
        bpf = self.n_blades * rpm / 60.0  # Blade Pass Frequency
        harmonics = np.arange(1, 8) * bpf
        spl = np.zeros(len(self.freqs))

        for i, h in enumerate(harmonics):
            if h < 20000:
                idx = np.argmin(np.abs(self.freqs - h))
                base_spl = 70 - 6 * i + 10 * np.log10(thrust_n + 1)
                width = max(5, int(50 / (i + 1)))
                lo = max(0, idx - width)
                hi = min(len(spl), idx + width)
                spl[lo:hi] += base_spl * np.exp(-0.5 * ((np.arange(lo, hi) - idx) / (width / 2)) ** 2)

        broadband = 40 + 10 * np.log10(rpm / 1000 + 1) + self.rng.standard_normal(len(self.freqs)) * 2
        spl = np.maximum(spl, broadband)
        return NoiseProfile(self.freqs, spl, NoiseSource.PROPELLER, rpm)

    def oaspl(self, profile: NoiseProfile) -> float:
        """Overall Sound Pressure Level."""
        p_sq = np.sum(10 ** (profile.spl_db / 10))
        return round(10 * np.log10(p_sq + 1e-10), 1)


class AcousticPropagation:
    """Sound propagation with atmospheric absorption."""

    def __init__(self, temperature_c: float = 20, humidity_pct: float = 50):
        self.temp = temperature_c
        self.humidity = humidity_pct
        self.speed_of_sound = 331.3 + 0.606 * temperature_c

    def attenuate(self, spl_db: float, distance_m: float, frequency_hz: float = 1000) -> float:
        if distance_m <= 0:
            return spl_db
        spreading = 20 * np.log10(distance_m + 1)
        alpha = 0.001 * (frequency_hz / 1000) ** 1.5 * (1 - self.humidity / 100)
        absorption = alpha * distance_m
        return round(spl_db - spreading - absorption, 1)


class AeroAcousticV2:
    """Comprehensive aero-acoustic analysis for drone swarms."""

    def __init__(self, n_drones: int = 10, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.prop_model = PropellerNoiseModel(seed=seed)
        self.propagation = AcousticPropagation()
        self.noise_map: Dict[str, float] = {}
        self.limits = {
            NoiseRegulation.KUTM_NOISE: 65.0,  # dBA at ground
            NoiseRegulation.EU_REG_2019: 60.0,
            NoiseRegulation.FAA_PART36: 70.0,
        }

    def compute_footprint(self, drone_positions: np.ndarray, rpms: np.ndarray,
                          grid_size: int = 10, area_m: float = 500) -> List[NoiseImpact]:
        impacts = []
        grid_x = np.linspace(-area_m / 2, area_m / 2, grid_size)
        grid_y = np.linspace(-area_m / 2, area_m / 2, grid_size)

        for gx in grid_x:
            for gy in grid_y:
                ground = np.array([gx, gy, 0])
                total_energy = 0.0
                for i in range(min(len(drone_positions), len(rpms))):
                    dist = np.linalg.norm(drone_positions[i] - ground)
                    profile = self.prop_model.predict(rpms[i])
                    oaspl = self.prop_model.oaspl(profile)
                    attenuated = self.propagation.attenuate(oaspl, dist)
                    total_energy += 10 ** (attenuated / 10)

                total_spl = 10 * np.log10(total_energy + 1e-10)
                exceeds = total_spl > self.limits.get(NoiseRegulation.KUTM_NOISE, 65)
                impacts.append(NoiseImpact(ground, round(total_spl, 1),
                                          NoiseSource.PROPELLER, exceeds, NoiseRegulation.KUTM_NOISE))
        return impacts

    def stealth_rpm(self, target_spl: float = 55.0) -> float:
        """Find RPM that keeps noise below target."""
        for rpm in range(1000, 10000, 100):
            profile = self.prop_model.predict(rpm)
            oaspl = self.prop_model.oaspl(profile)
            attenuated = self.propagation.attenuate(oaspl, 50)  # 50m distance
            if attenuated > target_spl:
                return max(1000, rpm - 100)
        return 10000

    def summary(self) -> Dict:
        return {
            "drones": self.n_drones,
            "stealth_rpm": self.stealth_rpm(),
            "regulations": len(self.limits),
        }
