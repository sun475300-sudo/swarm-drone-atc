# Phase 646: Anomaly Detector — Isolation Forest for Drone Behavior
"""
Isolation Forest 기반 이상 비행 탐지.
비정상 궤적, 속도 이상, 배터리 급강하 등 다변량 이상 검출.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class AnomalyScore:
    drone_id: str
    score: float  # 0-1, 높을수록 이상
    features: dict = field(default_factory=dict)
    is_anomaly: bool = False


class IsolationTree:
    def __init__(self, max_depth: int = 8):
        self.max_depth = max_depth
        self.split_feature: int | None = None
        self.split_value: float | None = None
        self.left: IsolationTree | None = None
        self.right: IsolationTree | None = None
        self.size: int = 0
        self.depth: int = 0

    def fit(self, X: np.ndarray, depth: int = 0, rng: np.random.Generator | None = None) -> None:
        self.size = len(X)
        self.depth = depth
        if rng is None:
            rng = np.random.default_rng(42)

        if depth >= self.max_depth or len(X) <= 1:
            return

        n_features = X.shape[1]
        self.split_feature = int(rng.integers(0, n_features))
        col = X[:, self.split_feature]
        lo, hi = float(col.min()), float(col.max())

        if lo == hi:
            return

        self.split_value = float(rng.uniform(lo, hi))
        left_mask = X[:, self.split_feature] < self.split_value
        right_mask = ~left_mask

        if left_mask.sum() > 0 and right_mask.sum() > 0:
            self.left = IsolationTree(self.max_depth)
            self.left.fit(X[left_mask], depth + 1, rng)
            self.right = IsolationTree(self.max_depth)
            self.right.fit(X[right_mask], depth + 1, rng)

    def path_length(self, x: np.ndarray) -> float:
        if self.left is None or self.split_feature is None:
            return float(self.depth) + self._c(self.size)
        if x[self.split_feature] < self.split_value:
            return self.left.path_length(x)
        return self.right.path_length(x)

    @staticmethod
    def _c(n: int) -> float:
        if n <= 1:
            return 0.0
        return 2.0 * (np.log(n - 1) + 0.5772156649) - 2.0 * (n - 1) / n


class IsolationForest:
    def __init__(self, n_trees: int = 50, max_depth: int = 8, seed: int = 42):
        self.n_trees = n_trees
        self.max_depth = max_depth
        self.rng = np.random.default_rng(seed)
        self.trees: list[IsolationTree] = []
        self._n_samples: int = 0

    def fit(self, X: np.ndarray) -> None:
        self._n_samples = len(X)
        sample_size = min(256, len(X))
        self.trees = []
        for _ in range(self.n_trees):
            idx = self.rng.choice(len(X), sample_size, replace=False) if len(X) > sample_size else np.arange(len(X))
            tree = IsolationTree(self.max_depth)
            tree.fit(X[idx], rng=self.rng)
            self.trees.append(tree)

    def score(self, x: np.ndarray) -> float:
        if not self.trees:
            return 0.0
        avg_path = np.mean([t.path_length(x) for t in self.trees])
        c_n = IsolationTree._c(self._n_samples)
        return float(2 ** (-avg_path / max(c_n, 1e-9)))

    def predict(self, X: np.ndarray, threshold: float = 0.6) -> np.ndarray:
        scores = np.array([self.score(x) for x in X])
        return scores > threshold


class DroneAnomalyDetector:
    def __init__(self, seed: int = 42, threshold: float = 0.6):
        self.rng = np.random.default_rng(seed)
        self.threshold = threshold
        self.forest = IsolationForest(seed=seed)
        self._history: dict[str, list[np.ndarray]] = {}

    def record(self, drone_id: str, features: np.ndarray) -> None:
        if drone_id not in self._history:
            self._history[drone_id] = []
        self._history[drone_id].append(features)

    def train(self) -> None:
        all_data = []
        for feats in self._history.values():
            all_data.extend(feats)
        if len(all_data) >= 10:
            self.forest.fit(np.array(all_data))

    def detect(self, drone_id: str) -> AnomalyScore:
        if drone_id not in self._history or not self._history[drone_id]:
            return AnomalyScore(drone_id, 0.0)
        latest = self._history[drone_id][-1]
        score = self.forest.score(latest)
        return AnomalyScore(
            drone_id=drone_id,
            score=score,
            features={"raw": latest.tolist()},
            is_anomaly=score > self.threshold,
        )

    def simulate(self, n_drones: int = 30, n_steps: int = 50) -> list[AnomalyScore]:
        # Generate normal data
        for i in range(n_drones):
            did = f"D-{i:04d}"
            for _ in range(n_steps):
                feat = self.rng.normal([0, 0, 60, 5, 80], [10, 10, 5, 2, 5])
                self.record(did, feat)

        # Inject anomalies
        for i in range(3):
            did = f"D-ANM-{i}"
            for _ in range(n_steps):
                feat = self.rng.normal([500, 500, 200, 50, 10], [5, 5, 2, 1, 1])
                self.record(did, feat)

        self.train()
        results = []
        for did in self._history:
            results.append(self.detect(did))
        return results


if __name__ == "__main__":
    detector = DroneAnomalyDetector(42)
    results = detector.simulate()
    anomalies = [r for r in results if r.is_anomaly]
    print(f"Total drones: {len(results)}, Anomalies detected: {len(anomalies)}")
    for a in anomalies:
        print(f"  {a.drone_id}: score={a.score:.3f}")
