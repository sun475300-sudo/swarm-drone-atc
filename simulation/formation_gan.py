"""
Phase 516: Formation GAN
GAN 기반 최적 대형 생성, 적대적 훈련, 대형 평가.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple


class FormationType(Enum):
    LINE = "line"
    V_SHAPE = "v_shape"
    CIRCLE = "circle"
    GRID = "grid"
    DIAMOND = "diamond"
    SPIRAL = "spiral"
    RANDOM = "random"


@dataclass
class Formation:
    formation_id: str
    ftype: FormationType
    positions: np.ndarray  # (n_drones, 3)
    fitness: float = 0.0
    generated: bool = False


@dataclass
class GANMetrics:
    epoch: int
    g_loss: float
    d_loss: float
    diversity: float
    quality: float


class Generator:
    """Neural formation generator (simplified MLP)."""

    def __init__(self, latent_dim: int = 16, n_drones: int = 10, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.latent_dim = latent_dim
        self.n_drones = n_drones
        self.W1 = self.rng.standard_normal((latent_dim, 64)) * 0.1
        self.b1 = np.zeros(64)
        self.W2 = self.rng.standard_normal((64, n_drones * 3)) * 0.1
        self.b2 = np.zeros(n_drones * 3)

    def forward(self, z: np.ndarray) -> np.ndarray:
        h = np.tanh(z @ self.W1 + self.b1)
        out = h @ self.W2 + self.b2
        return out.reshape(-1, self.n_drones, 3) * 50

    def generate(self, n_samples: int = 1) -> np.ndarray:
        z = self.rng.standard_normal((n_samples, self.latent_dim))
        return self.forward(z)

    def update(self, grad_scale: float = 0.01):
        self.W1 += self.rng.standard_normal(self.W1.shape) * grad_scale
        self.W2 += self.rng.standard_normal(self.W2.shape) * grad_scale


class Discriminator:
    """Formation quality discriminator."""

    def __init__(self, n_drones: int = 10, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.W1 = self.rng.standard_normal((n_drones * 3, 32)) * 0.1
        self.b1 = np.zeros(32)
        self.W2 = self.rng.standard_normal((32, 1)) * 0.1
        self.b2 = np.zeros(1)

    def forward(self, formations: np.ndarray) -> np.ndarray:
        x = formations.reshape(-1, self.n_drones * 3)
        h = np.tanh(x @ self.W1 + self.b1)
        out = h @ self.W2 + self.b2
        return 1 / (1 + np.exp(-out))  # sigmoid

    def update(self, grad_scale: float = 0.01):
        self.W1 += self.rng.standard_normal(self.W1.shape) * grad_scale
        self.W2 += self.rng.standard_normal(self.W2.shape) * grad_scale


class FormationEvaluator:
    """Evaluate formation quality metrics."""

    def __init__(self):
        pass

    def separation_score(self, positions: np.ndarray) -> float:
        n = len(positions)
        if n < 2:
            return 1.0
        min_dist = float('inf')
        for i in range(n):
            for j in range(i + 1, n):
                d = np.linalg.norm(positions[i] - positions[j])
                min_dist = min(min_dist, d)
        return min(1.0, min_dist / 5.0)

    def coverage_score(self, positions: np.ndarray) -> float:
        spread = np.std(positions, axis=0)
        return min(1.0, np.mean(spread) / 30)

    def symmetry_score(self, positions: np.ndarray) -> float:
        center = np.mean(positions, axis=0)
        dists = np.linalg.norm(positions - center, axis=1)
        return max(0, 1 - np.std(dists) / (np.mean(dists) + 1e-8))

    def evaluate(self, positions: np.ndarray) -> float:
        s1 = self.separation_score(positions)
        s2 = self.coverage_score(positions)
        s3 = self.symmetry_score(positions)
        return round(0.4 * s1 + 0.3 * s2 + 0.3 * s3, 4)


class FormationGAN:
    """GAN-based optimal formation generation."""

    def __init__(self, n_drones: int = 10, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.generator = Generator(16, n_drones, seed)
        self.discriminator = Discriminator(n_drones, seed + 1)
        self.evaluator = FormationEvaluator()
        self.metrics: List[GANMetrics] = []
        self.formations: List[Formation] = []
        self._counter = 0

    def _make_real(self, ftype: FormationType) -> np.ndarray:
        n = self.n_drones
        if ftype == FormationType.CIRCLE:
            angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
            r = 30
            return np.column_stack([r * np.cos(angles), r * np.sin(angles), np.full(n, 50)])
        elif ftype == FormationType.V_SHAPE:
            pos = np.zeros((n, 3))
            for i in range(n):
                side = 1 if i % 2 == 0 else -1
                idx = (i + 1) // 2
                pos[i] = [idx * 10 * side, -idx * 8, 50]
            return pos
        else:
            return self.rng.uniform(-50, 50, (n, 3))

    def train_epoch(self, batch_size: int = 16) -> GANMetrics:
        real = np.stack([self._make_real(self.rng.choice(
            [FormationType.CIRCLE, FormationType.V_SHAPE, FormationType.GRID]))
            for _ in range(batch_size)])
        fake = self.generator.generate(batch_size)

        d_real = self.discriminator.forward(real)
        d_fake = self.discriminator.forward(fake)
        d_loss = -np.mean(np.log(d_real + 1e-8) + np.log(1 - d_fake + 1e-8))
        g_loss = -np.mean(np.log(d_fake + 1e-8))

        self.discriminator.update(0.005)
        self.generator.update(0.005)

        diversity = np.mean(np.std(fake, axis=0))
        quality = np.mean([self.evaluator.evaluate(f) for f in fake])

        m = GANMetrics(len(self.metrics) + 1, round(float(g_loss), 4),
                      round(float(d_loss), 4), round(float(diversity), 4),
                      round(float(quality), 4))
        self.metrics.append(m)
        return m

    def generate_formation(self, ftype: FormationType = FormationType.RANDOM) -> Formation:
        self._counter += 1
        positions = self.generator.generate(1)[0]
        fitness = self.evaluator.evaluate(positions)
        f = Formation(f"FRM-{self._counter:04d}", ftype, positions, fitness, True)
        self.formations.append(f)
        return f

    def train(self, epochs: int = 20) -> List[GANMetrics]:
        return [self.train_epoch() for _ in range(epochs)]

    def summary(self) -> Dict:
        return {
            "n_drones": self.n_drones,
            "epochs_trained": len(self.metrics),
            "formations_generated": len(self.formations),
            "avg_quality": round(
                np.mean([m.quality for m in self.metrics]) if self.metrics else 0, 4),
        }
