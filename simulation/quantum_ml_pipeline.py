"""
Phase 471: Quantum Machine Learning Pipeline
양자 머신러닝 — QNN, Quantum Kernel, 양자 서포트 벡터 분류.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple


class QMLMethod(Enum):
    QNN = "qnn"
    QSVC = "qsvc"
    QKERNEL = "qkernel"
    VQC = "vqc"


@dataclass
class QuantumFeatureMap:
    n_qubits: int
    depth: int
    params: np.ndarray

    @staticmethod
    def create(n_features: int, depth: int = 2, rng: Optional[np.random.Generator] = None) -> 'QuantumFeatureMap':
        rng = rng or np.random.default_rng(42)
        return QuantumFeatureMap(n_features, depth, rng.uniform(0, 2 * np.pi, (depth, n_features)))


@dataclass
class QNNLayer:
    n_qubits: int
    weights: np.ndarray
    bias: np.ndarray

    def forward(self, x: np.ndarray) -> np.ndarray:
        rotated = np.cos(self.weights @ x + self.bias)
        return rotated / (np.linalg.norm(rotated) + 1e-10)


class QuantumKernel:
    """Quantum kernel for SVM-like classification."""

    def __init__(self, n_qubits: int = 4, seed: int = 42):
        self.n_qubits = n_qubits
        self.rng = np.random.default_rng(seed)
        self.feature_map = QuantumFeatureMap.create(n_qubits, rng=self.rng)

    def _encode(self, x: np.ndarray) -> np.ndarray:
        state = np.zeros(2 ** self.n_qubits)
        state[0] = 1.0
        for d in range(self.feature_map.depth):
            angles = self.feature_map.params[d] * x[:self.n_qubits]
            for i, angle in enumerate(angles):
                idx = 1 << i
                c, s = np.cos(angle / 2), np.sin(angle / 2)
                new_state = state.copy()
                for j in range(len(state)):
                    if j & idx:
                        new_state[j] = c * state[j] + s * state[j ^ idx]
                        new_state[j ^ idx] = c * state[j ^ idx] - s * state[j]
                state = new_state
        return state / (np.linalg.norm(state) + 1e-10)

    def compute(self, x1: np.ndarray, x2: np.ndarray) -> float:
        s1, s2 = self._encode(x1), self._encode(x2)
        return float(np.abs(np.dot(s1, s2)) ** 2)

    def gram_matrix(self, X: np.ndarray) -> np.ndarray:
        n = len(X)
        K = np.zeros((n, n))
        for i in range(n):
            for j in range(i, n):
                k = self.compute(X[i], X[j])
                K[i, j] = K[j, i] = k
        return K


class QuantumNeuralNetwork:
    """Variational quantum neural network simulator."""

    def __init__(self, n_qubits: int = 4, n_layers: int = 3, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_qubits = n_qubits
        self.layers = []
        for _ in range(n_layers):
            w = self.rng.standard_normal((n_qubits, n_qubits)) * 0.1
            b = self.rng.standard_normal(n_qubits) * 0.01
            self.layers.append(QNNLayer(n_qubits, w, b))

    def predict(self, x: np.ndarray) -> np.ndarray:
        h = x[:self.n_qubits] if len(x) > self.n_qubits else np.pad(x, (0, self.n_qubits - len(x)))
        for layer in self.layers:
            h = layer.forward(h)
        return h

    def predict_class(self, x: np.ndarray) -> int:
        h = self.predict(x)
        return int(np.argmax(np.abs(h[:2])))


class QSVC:
    """Quantum Support Vector Classifier."""

    def __init__(self, n_qubits: int = 4, seed: int = 42):
        self.kernel = QuantumKernel(n_qubits, seed)
        self.rng = np.random.default_rng(seed)
        self.support_vectors: Optional[np.ndarray] = None
        self.alphas: Optional[np.ndarray] = None
        self.labels: Optional[np.ndarray] = None
        self.bias = 0.0

    def fit(self, X: np.ndarray, y: np.ndarray, max_iter: int = 100, lr: float = 0.01) -> None:
        n = len(X)
        self.support_vectors = X
        self.labels = y.astype(float)
        self.alphas = np.zeros(n)
        K = self.kernel.gram_matrix(X)

        for _ in range(max_iter):
            for i in range(n):
                decision = np.sum(self.alphas * self.labels * K[i]) + self.bias
                if self.labels[i] * decision < 1:
                    self.alphas[i] += lr
                    self.bias += lr * self.labels[i]

    def predict(self, x: np.ndarray) -> int:
        if self.support_vectors is None:
            return 0
        decision = self.bias
        for i in range(len(self.support_vectors)):
            k = self.kernel.compute(x, self.support_vectors[i])
            decision += self.alphas[i] * self.labels[i] * k
        return 1 if decision > 0 else -1


class QuantumMLPipeline:
    """End-to-end quantum ML pipeline."""

    def __init__(self, method: QMLMethod = QMLMethod.QNN, n_qubits: int = 4, seed: int = 42):
        self.method = method
        self.n_qubits = n_qubits
        self.rng = np.random.default_rng(seed)
        self.model = self._build_model(seed)
        self.training_history: List[float] = []

    def _build_model(self, seed: int):
        if self.method == QMLMethod.QNN:
            return QuantumNeuralNetwork(self.n_qubits, seed=seed)
        elif self.method == QMLMethod.QSVC:
            return QSVC(self.n_qubits, seed=seed)
        elif self.method == QMLMethod.QKERNEL:
            return QuantumKernel(self.n_qubits, seed=seed)
        return QuantumNeuralNetwork(self.n_qubits, seed=seed)

    def train(self, X: np.ndarray, y: np.ndarray) -> Dict:
        if self.method == QMLMethod.QSVC:
            self.model.fit(X, y)
            preds = [self.model.predict(x) for x in X]
            acc = np.mean(np.array(preds) == y)
            self.training_history.append(float(acc))
            return {"accuracy": float(acc), "samples": len(X)}
        else:
            losses = []
            for x, label in zip(X, y):
                pred = self.model.predict(x)
                loss = float(np.mean((pred[:1] - label) ** 2))
                losses.append(loss)
            avg_loss = float(np.mean(losses))
            self.training_history.append(avg_loss)
            return {"loss": avg_loss, "samples": len(X)}

    def predict(self, x: np.ndarray):
        if self.method == QMLMethod.QSVC:
            return self.model.predict(x)
        elif self.method == QMLMethod.QNN:
            return self.model.predict_class(x)
        else:
            return self.model.compute(x, x)

    def summary(self) -> Dict:
        return {
            "method": self.method.value,
            "n_qubits": self.n_qubits,
            "training_steps": len(self.training_history),
            "last_metric": self.training_history[-1] if self.training_history else 0,
        }
