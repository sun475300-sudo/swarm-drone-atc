# Phase 538: Swarm Immune System — Artificial Immune System (AIS)
"""
인공면역계 기반 이상 탐지 및 자가 치유:
Negative Selection, Clonal Selection, 위험 이론 기반 방어.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum


class ThreatLevel(Enum):
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    DANGEROUS = "dangerous"
    CRITICAL = "critical"


@dataclass
class Antibody:
    ab_id: str
    pattern: np.ndarray  # 탐지 패턴
    affinity_threshold: float
    matches: int = 0
    age: int = 0


@dataclass
class Antigen:
    ag_id: str
    features: np.ndarray
    is_threat: bool
    threat_level: ThreatLevel = ThreatLevel.SAFE


@dataclass
class ImmuneResponse:
    detected: int
    missed: int
    false_positive: int
    true_negative: int
    healed: int


class NegativeSelection:
    """네거티브 셀렉션: 자기(self) 패턴 학습 → 비자기 탐지."""

    def __init__(self, self_patterns: np.ndarray, threshold=0.5, seed=42):
        self.rng = np.random.default_rng(seed)
        self.self_patterns = self_patterns
        self.threshold = threshold
        self.detectors: list[Antibody] = []

    def generate_detectors(self, n=30, dim=5):
        candidates = self.rng.normal(0, 1, (n * 3, dim))
        for i, cand in enumerate(candidates):
            if len(self.detectors) >= n:
                break
            # self 패턴과 매칭 안 되는 것만 채택
            is_self = any(
                np.linalg.norm(cand - sp) < self.threshold
                for sp in self.self_patterns
            )
            if not is_self:
                self.detectors.append(Antibody(
                    f"DET-{len(self.detectors):04d}",
                    cand, self.threshold
                ))

    def detect(self, antigen: np.ndarray) -> bool:
        for det in self.detectors:
            if np.linalg.norm(det.pattern - antigen) < det.affinity_threshold:
                det.matches += 1
                return True
        return False


class ClonalSelection:
    """클론 선택: 성공적 항체 증식 및 초돌연변이."""

    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)

    def select_and_clone(self, antibodies: list[Antibody], top_k=5) -> list[Antibody]:
        sorted_abs = sorted(antibodies, key=lambda a: a.matches, reverse=True)
        clones = []
        for ab in sorted_abs[:top_k]:
            n_clones = max(1, ab.matches)
            for j in range(min(n_clones, 3)):
                mutated = ab.pattern + self.rng.normal(0, 0.1, ab.pattern.shape)
                clones.append(Antibody(
                    f"{ab.ab_id}-C{j}", mutated, ab.affinity_threshold
                ))
        return clones


class DangerTheory:
    """위험 이론: 위험 신호 기반 면역 활성화."""

    def __init__(self, danger_threshold=0.7):
        self.threshold = danger_threshold
        self.danger_signals: list[float] = []

    def signal(self, value: float):
        self.danger_signals.append(value)

    def is_danger_zone(self) -> bool:
        if not self.danger_signals:
            return False
        recent = self.danger_signals[-10:]
        return float(np.mean(recent)) > self.threshold

    def threat_level(self) -> ThreatLevel:
        if not self.danger_signals:
            return ThreatLevel.SAFE
        avg = float(np.mean(self.danger_signals[-10:]))
        if avg > 0.9:
            return ThreatLevel.CRITICAL
        if avg > 0.7:
            return ThreatLevel.DANGEROUS
        if avg > 0.4:
            return ThreatLevel.SUSPICIOUS
        return ThreatLevel.SAFE


class SwarmImmuneSystem:
    """군집 면역계 시뮬레이션."""

    def __init__(self, n_drones=20, seed=42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.dim = 5

        # 정상 패턴 (self) 생성
        self.self_patterns = self.rng.normal(0, 0.3, (n_drones, self.dim))

        self.neg_sel = NegativeSelection(self.self_patterns, 0.8, seed)
        self.neg_sel.generate_detectors(30, self.dim)
        self.clonal = ClonalSelection(seed)
        self.danger = DangerTheory(0.6)

        self.antigens: list[Antigen] = []
        self.response: ImmuneResponse | None = None
        self.healed = 0

    def generate_antigens(self, n_normal=30, n_threat=10):
        self.antigens.clear()
        for i in range(n_normal):
            feat = self.self_patterns[int(self.rng.integers(0, self.n_drones))] + self.rng.normal(0, 0.1, self.dim)
            self.antigens.append(Antigen(f"AG-N{i}", feat, False, ThreatLevel.SAFE))
        for i in range(n_threat):
            feat = self.rng.normal(2, 1, self.dim)  # 비정상 패턴
            level = self.rng.choice([ThreatLevel.SUSPICIOUS, ThreatLevel.DANGEROUS, ThreatLevel.CRITICAL])
            self.antigens.append(Antigen(f"AG-T{i}", feat, True, level))

    def run_detection(self) -> ImmuneResponse:
        detected = 0
        missed = 0
        fp = 0
        tn = 0
        for ag in self.antigens:
            is_detected = self.neg_sel.detect(ag.features)
            if ag.is_threat:
                if is_detected:
                    detected += 1
                    self.danger.signal(0.9)
                else:
                    missed += 1
                    self.danger.signal(0.3)
            else:
                if is_detected:
                    fp += 1
                    self.danger.signal(0.4)
                else:
                    tn += 1
                    self.danger.signal(0.1)

        # 클론 선택으로 탐지기 강화
        clones = self.clonal.select_and_clone(self.neg_sel.detectors)
        self.neg_sel.detectors.extend(clones[:10])

        # 자가 치유
        healed = detected  # 탐지된 위협은 치유됨
        self.healed += healed
        self.response = ImmuneResponse(detected, missed, fp, tn, healed)
        return self.response

    def summary(self):
        total = len(self.antigens)
        threats = sum(1 for a in self.antigens if a.is_threat)
        return {
            "drones": self.n_drones,
            "detectors": len(self.neg_sel.detectors),
            "antigens": total,
            "threats": threats,
            "detected": self.response.detected if self.response else 0,
            "missed": self.response.missed if self.response else 0,
            "false_positives": self.response.false_positive if self.response else 0,
            "healed": self.healed,
            "threat_level": self.danger.threat_level().value,
        }


if __name__ == "__main__":
    ais = SwarmImmuneSystem(20, 42)
    ais.generate_antigens(30, 10)
    ais.run_detection()
    s = ais.summary()
    for k, v in s.items():
        print(f"  {k}: {v}")
