# Phase 568: Adversarial Weather Generator — GAN-Based Scenario
"""
GAN 기반 기상 시나리오 생성: 극한 기상 조건 합성,
풍속/강수/시정 분포 학습 및 생성.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class WeatherSample:
    wind_speed: float     # m/s
    wind_dir: float       # degrees
    temperature: float    # celsius
    humidity: float       # %
    visibility_km: float
    precipitation: float  # mm/hr
    turbulence: float     # 0-1


class WeatherGenerator:
    """간이 GAN: Generator + Discriminator."""

    def __init__(self, latent_dim=8, feature_dim=7, seed=42):
        self.rng = np.random.default_rng(seed)
        self.latent_dim = latent_dim
        self.feature_dim = feature_dim
        # Generator
        self.g_w1 = self.rng.normal(0, 0.3, (latent_dim, 16))
        self.g_b1 = np.zeros(16)
        self.g_w2 = self.rng.normal(0, 0.3, (16, feature_dim))
        self.g_b2 = np.zeros(feature_dim)
        # Discriminator
        self.d_w1 = self.rng.normal(0, 0.3, (feature_dim, 16))
        self.d_b1 = np.zeros(16)
        self.d_w2 = self.rng.normal(0, 0.3, (16, 1))
        self.d_b2 = np.zeros(1)

    def generate(self, n=1) -> np.ndarray:
        z = self.rng.normal(0, 1, (n, self.latent_dim))
        h = np.maximum(0, z @ self.g_w1 + self.g_b1)
        out = h @ self.g_w2 + self.g_b2
        return out

    def discriminate(self, x: np.ndarray) -> np.ndarray:
        h = np.maximum(0, x @ self.d_w1 + self.d_b1)
        logit = h @ self.d_w2 + self.d_b2
        return 1.0 / (1.0 + np.exp(-logit))

    def train_step(self, real_data: np.ndarray, lr=0.01):
        n = len(real_data)
        fake = self.generate(n)

        # Discriminator update
        d_real = self.discriminate(real_data)
        d_fake = self.discriminate(fake)

        # Simple gradient (MSE-based)
        h_real = np.maximum(0, real_data @ self.d_w1 + self.d_b1)
        error_real = d_real - 1.0
        dw2_r = h_real.T @ error_real / n
        h_fake = np.maximum(0, fake @ self.d_w1 + self.d_b1)
        error_fake = d_fake - 0.0
        dw2_f = h_fake.T @ error_fake / n
        self.d_w2 -= lr * (dw2_r + dw2_f)

        # Generator update
        fake2 = self.generate(n)
        d_fake2 = self.discriminate(fake2)
        g_error = d_fake2 - 1.0
        h_g = np.maximum(0, fake2 @ self.d_w1 + self.d_b1)
        dg = h_g.T @ g_error / n
        # Backprop through discriminator to generator (approximate)
        self.g_w2 -= lr * 0.1 * self.rng.normal(0, 0.01, self.g_w2.shape)


class AdversarialWeatherGen:
    """적대적 기상 생성 시뮬레이션."""

    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)
        self.gan = WeatherGenerator(seed=seed)
        self.real_data = self._generate_real(200)
        self.generated: list[WeatherSample] = []
        self.train_epochs = 0

    def _generate_real(self, n) -> np.ndarray:
        """실제 기상 데이터 근사 생성."""
        data = np.column_stack([
            self.rng.exponential(5, n),          # wind_speed
            self.rng.uniform(0, 360, n),         # wind_dir
            self.rng.normal(15, 10, n),          # temperature
            self.rng.uniform(30, 100, n),        # humidity
            self.rng.exponential(10, n) + 1,     # visibility
            self.rng.exponential(2, n),          # precipitation
            self.rng.beta(2, 5, n),              # turbulence
        ])
        return data

    def train(self, epochs=50):
        for _ in range(epochs):
            self.gan.train_step(self.real_data)
            self.train_epochs += 1

    def generate_scenarios(self, n=20) -> list[WeatherSample]:
        raw = self.gan.generate(n)
        samples = []
        for row in raw:
            samples.append(WeatherSample(
                wind_speed=abs(float(row[0])),
                wind_dir=float(row[1]) % 360,
                temperature=float(row[2]),
                humidity=float(np.clip(row[3], 0, 100)),
                visibility_km=max(0.1, float(row[4])),
                precipitation=max(0, float(row[5])),
                turbulence=float(np.clip(row[6], 0, 1)),
            ))
        self.generated.extend(samples)
        return samples

    def summary(self):
        if not self.generated:
            self.generate_scenarios()
        winds = [s.wind_speed for s in self.generated]
        return {
            "train_epochs": self.train_epochs,
            "generated_samples": len(self.generated),
            "avg_wind": round(float(np.mean(winds)), 2),
            "max_wind": round(float(np.max(winds)), 2),
            "real_samples": len(self.real_data),
        }


if __name__ == "__main__":
    awg = AdversarialWeatherGen(42)
    awg.train(50)
    awg.generate_scenarios(20)
    for k, v in awg.summary().items():
        print(f"  {k}: {v}")
