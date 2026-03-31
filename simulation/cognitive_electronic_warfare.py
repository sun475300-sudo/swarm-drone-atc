"""
Phase 486: Cognitive Electronic Warfare
적응형 재밍 대응, 스펙트럼 전쟁, 인지 레이더.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple


class SpectrumBand(Enum):
    VHF = (30e6, 300e6)
    UHF = (300e6, 3e9)
    L_BAND = (1e9, 2e9)
    S_BAND = (2e9, 4e9)
    C_BAND = (4e9, 8e9)
    X_BAND = (8e9, 12e9)
    KU_BAND = (12e9, 18e9)


class ThreatType(Enum):
    BARRAGE_JAM = "barrage_jammer"
    SPOT_JAM = "spot_jammer"
    SWEEP_JAM = "sweep_jammer"
    DECEPTIVE_JAM = "deceptive_jammer"
    RADAR_LOCK = "radar_lock"


class CountermeasureType(Enum):
    FREQ_HOP = "frequency_hopping"
    SPREAD_SPECTRUM = "spread_spectrum"
    POWER_MANAGEMENT = "power_management"
    BEAM_NULL = "beam_nulling"
    DECOY = "decoy_emission"
    SILENCE = "radio_silence"


@dataclass
class SpectrumSample:
    frequency_hz: float
    power_dbm: float
    timestamp: float
    is_threat: bool = False
    threat_type: Optional[ThreatType] = None


@dataclass
class EWEngagement:
    engagement_id: str
    threat: ThreatType
    countermeasure: CountermeasureType
    success: bool
    snr_before: float
    snr_after: float
    response_time_ms: float


class SpectrumAnalyzer:
    """Real-time spectrum monitoring and threat detection."""

    def __init__(self, bands: List[SpectrumBand] = None, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.bands = bands or [SpectrumBand.L_BAND, SpectrumBand.S_BAND, SpectrumBand.C_BAND]
        self.noise_floor_dbm = -90.0
        self.history: List[SpectrumSample] = []

    def scan(self, n_points: int = 256, time: float = 0.0) -> List[SpectrumSample]:
        samples = []
        for band in self.bands:
            freqs = np.linspace(band.value[0], band.value[1], n_points // len(self.bands))
            for f in freqs:
                power = self.noise_floor_dbm + self.rng.standard_normal() * 3
                is_threat = False
                threat_type = None
                if self.rng.random() < 0.02:
                    power += self.rng.uniform(20, 50)
                    is_threat = True
                    threat_type = self.rng.choice(list(ThreatType))
                sample = SpectrumSample(f, round(power, 1), time, is_threat, threat_type)
                samples.append(sample)
        self.history.extend(samples)
        return samples

    def detect_threats(self, samples: List[SpectrumSample],
                       threshold_dbm: float = -60) -> List[SpectrumSample]:
        return [s for s in samples if s.power_dbm > threshold_dbm]

    def classify_jammer(self, threat_samples: List[SpectrumSample]) -> Optional[ThreatType]:
        if not threat_samples:
            return None
        freqs = [s.frequency_hz for s in threat_samples]
        bandwidth = max(freqs) - min(freqs) if len(freqs) > 1 else 0
        avg_power = np.mean([s.power_dbm for s in threat_samples])

        if bandwidth > 500e6:
            return ThreatType.BARRAGE_JAM
        elif bandwidth < 10e6 and avg_power > -30:
            return ThreatType.SPOT_JAM
        elif len(freqs) > 3 and np.std([s.timestamp for s in threat_samples]) > 0.1:
            return ThreatType.SWEEP_JAM
        return ThreatType.DECEPTIVE_JAM


class CognitiveEW:
    """Cognitive electronic warfare engine with adaptive countermeasures."""

    def __init__(self, n_drones: int = 10, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.analyzer = SpectrumAnalyzer(seed=seed)
        self.engagements: List[EWEngagement] = []
        self.time = 0.0
        self._engagement_counter = 0
        self.operating_freqs: Dict[int, float] = {}
        self.freq_hop_table: Dict[int, List[float]] = {}

        for i in range(n_drones):
            base = 2.4e9 + i * 5e6
            self.operating_freqs[i] = base
            self.freq_hop_table[i] = [base + j * 1e6 for j in range(20)]

        self._countermeasure_map: Dict[ThreatType, List[CountermeasureType]] = {
            ThreatType.BARRAGE_JAM: [CountermeasureType.SPREAD_SPECTRUM, CountermeasureType.POWER_MANAGEMENT],
            ThreatType.SPOT_JAM: [CountermeasureType.FREQ_HOP, CountermeasureType.BEAM_NULL],
            ThreatType.SWEEP_JAM: [CountermeasureType.FREQ_HOP, CountermeasureType.SILENCE],
            ThreatType.DECEPTIVE_JAM: [CountermeasureType.DECOY, CountermeasureType.SPREAD_SPECTRUM],
            ThreatType.RADAR_LOCK: [CountermeasureType.DECOY, CountermeasureType.SILENCE],
        }

    def _select_countermeasure(self, threat: ThreatType) -> CountermeasureType:
        options = self._countermeasure_map.get(threat, [CountermeasureType.FREQ_HOP])
        success_rates = {}
        for eng in self.engagements[-50:]:
            if eng.threat == threat:
                key = eng.countermeasure
                if key not in success_rates:
                    success_rates[key] = []
                success_rates[key].append(1.0 if eng.success else 0.0)

        best = options[0]
        best_rate = 0.0
        for cm in options:
            if cm in success_rates and len(success_rates[cm]) >= 3:
                rate = np.mean(success_rates[cm])
                if rate > best_rate:
                    best_rate = rate
                    best = cm
            elif cm not in success_rates:
                best = cm
                break
        return best

    def _apply_countermeasure(self, threat: ThreatType,
                              cm: CountermeasureType) -> Tuple[bool, float, float]:
        snr_before = self.rng.uniform(-5, 10)
        base_effectiveness = {
            CountermeasureType.FREQ_HOP: 0.8,
            CountermeasureType.SPREAD_SPECTRUM: 0.75,
            CountermeasureType.POWER_MANAGEMENT: 0.6,
            CountermeasureType.BEAM_NULL: 0.7,
            CountermeasureType.DECOY: 0.65,
            CountermeasureType.SILENCE: 0.9,
        }
        prob = base_effectiveness.get(cm, 0.5)
        success = self.rng.random() < prob
        snr_after = snr_before + (self.rng.uniform(10, 25) if success else self.rng.uniform(-5, 5))
        response_time = self.rng.exponential(50) + 10
        return success, snr_before, snr_after

    def engage(self, threat: ThreatType) -> EWEngagement:
        self._engagement_counter += 1
        cm = self._select_countermeasure(threat)
        success, snr_before, snr_after = self._apply_countermeasure(threat, cm)
        response_time = self.rng.exponential(50) + 10

        engagement = EWEngagement(
            f"EW-{self._engagement_counter:04d}", threat, cm,
            success, round(snr_before, 1), round(snr_after, 1),
            round(response_time, 1))
        self.engagements.append(engagement)
        return engagement

    def run_cycle(self, n_scans: int = 10) -> Dict:
        results = {"scans": n_scans, "threats": 0, "engagements": 0, "successful": 0}
        for _ in range(n_scans):
            self.time += 0.1
            samples = self.analyzer.scan(time=self.time)
            threats = self.analyzer.detect_threats(samples)
            if threats:
                results["threats"] += len(threats)
                jammer_type = self.analyzer.classify_jammer(threats)
                if jammer_type:
                    eng = self.engage(jammer_type)
                    results["engagements"] += 1
                    if eng.success:
                        results["successful"] += 1
        return results

    def summary(self) -> Dict:
        return {
            "drones": self.n_drones,
            "total_engagements": len(self.engagements),
            "success_rate": round(
                sum(1 for e in self.engagements if e.success) / max(len(self.engagements), 1), 4),
            "avg_snr_improvement": round(float(np.mean(
                [e.snr_after - e.snr_before for e in self.engagements])), 2) if self.engagements else 0,
        }
