# Phase 608: Drone Reputation System — Bayesian Trust
"""
드론 평판 시스템: 베타 분포 기반 베이지안 신뢰,
평판 갱신, 악의적 드론 탐지.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class Reputation:
    drone_id: int
    alpha: float = 1.0  # 성공 (Beta prior)
    beta_param: float = 1.0   # 실패
    observations: int = 0

    @property
    def trust_score(self) -> float:
        return self.alpha / (self.alpha + self.beta_param)

    @property
    def uncertainty(self) -> float:
        total = self.alpha + self.beta_param
        return float(np.sqrt(self.alpha * self.beta_param / (total**2 * (total + 1))))


class BayesianReputation:
    def __init__(self, n_drones: int, seed=42):
        self.rng = np.random.default_rng(seed)
        self.n = n_drones
        self.reputations = {i: Reputation(i) for i in range(n_drones)}
        self.malicious = set()

    def set_malicious(self, drone_ids: list[int]):
        self.malicious = set(drone_ids)

    def observe(self, drone_id: int, success: bool):
        rep = self.reputations[drone_id]
        if success:
            rep.alpha += 1
        else:
            rep.beta_param += 1
        rep.observations += 1

    def simulate_interaction(self, drone_id: int) -> bool:
        if drone_id in self.malicious:
            return self.rng.random() < 0.3  # 악의적: 30% 성공
        return self.rng.random() < 0.9  # 정상: 90% 성공

    def detect_malicious(self, threshold=0.5) -> list[int]:
        return [d for d, r in self.reputations.items() if r.trust_score < threshold and r.observations > 5]


class DroneReputationSystem:
    def __init__(self, n_drones=20, n_malicious=3, seed=42):
        self.rng = np.random.default_rng(seed)
        self.system = BayesianReputation(n_drones, seed)
        self.n = n_drones
        mal_ids = list(self.rng.choice(n_drones, n_malicious, replace=False))
        self.system.set_malicious(mal_ids)
        self.interactions = 0

    def run(self, rounds=50):
        for _ in range(rounds):
            for d in range(self.n):
                success = self.system.simulate_interaction(d)
                self.system.observe(d, success)
                self.interactions += 1

    def summary(self):
        detected = self.system.detect_malicious()
        actual = self.system.malicious
        tp = len(set(detected) & actual)
        fp = len(set(detected) - actual)
        scores = [r.trust_score for r in self.system.reputations.values()]
        return {
            "drones": self.n,
            "malicious_actual": len(actual),
            "malicious_detected": len(detected),
            "true_positives": tp,
            "false_positives": fp,
            "interactions": self.interactions,
            "avg_trust": round(float(np.mean(scores)), 4),
        }


if __name__ == "__main__":
    drs = DroneReputationSystem(20, 3, 42)
    drs.run(50)
    for k, v in drs.summary().items():
        print(f"  {k}: {v}")
