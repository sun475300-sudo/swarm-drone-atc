"""
Autoencoder-based anomaly detector.
===================================
Simple NumPy autoencoder for tabular telemetry reconstruction error scoring.
"""
from __future__ import annotations

from typing import Any

import numpy as np


class AnomalyAutoencoder:
    def __init__(
        self,
        input_dim: int,
        latent_dim: int = 4,
        learning_rate: float = 0.01,
        seed: int = 42,
    ) -> None:
        self._rng = np.random.default_rng(seed)
        self.input_dim = input_dim
        self.latent_dim = max(1, latent_dim)
        self.lr = learning_rate

        self.w_enc = self._rng.normal(0, 0.1, (self.input_dim, self.latent_dim))
        self.b_enc = np.zeros(self.latent_dim)
        self.w_dec = self._rng.normal(0, 0.1, (self.latent_dim, self.input_dim))
        self.b_dec = np.zeros(self.input_dim)

        self._threshold = 0.0
        self._trained_steps = 0

    def _encode(self, x: np.ndarray) -> np.ndarray:
        return np.tanh(x @ self.w_enc + self.b_enc)

    def _decode(self, z: np.ndarray) -> np.ndarray:
        return z @ self.w_dec + self.b_dec

    def _forward(self, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        z = self._encode(x)
        recon = self._decode(z)
        return z, recon

    def fit(self, samples: list[list[float]], epochs: int = 50) -> dict[str, Any]:
        x = np.array(samples, dtype=np.float64)
        if x.ndim != 2 or x.shape[1] != self.input_dim:
            raise ValueError("samples shape must be (n, input_dim)")

        losses: list[float] = []
        n = x.shape[0]
        for _ in range(max(1, epochs)):
            z, recon = self._forward(x)
            err = recon - x
            loss = float(np.mean(err**2))
            losses.append(loss)

            d_recon = (2.0 / n) * err
            dw_dec = z.T @ d_recon
            db_dec = d_recon.sum(axis=0)

            d_z = (d_recon @ self.w_dec.T) * (1.0 - z**2)
            dw_enc = x.T @ d_z
            db_enc = d_z.sum(axis=0)

            self.w_dec -= self.lr * dw_dec
            self.b_dec -= self.lr * db_dec
            self.w_enc -= self.lr * dw_enc
            self.b_enc -= self.lr * db_enc
            self._trained_steps += 1

        train_errors = self.reconstruction_error(samples)
        mu = float(np.mean(train_errors))
        sigma = float(np.std(train_errors))
        self._threshold = mu + 3.0 * sigma

        return {
            "loss": round(losses[-1], 6),
            "threshold": round(self._threshold, 6),
            "epochs": len(losses),
        }

    def reconstruction_error(self, samples: list[list[float]]) -> list[float]:
        x = np.array(samples, dtype=np.float64)
        _, recon = self._forward(x)
        return [float(v) for v in np.mean((recon - x) ** 2, axis=1)]

    def detect(self, sample: list[float]) -> dict[str, Any]:
        error = self.reconstruction_error([sample])[0]
        is_anomaly = error > self._threshold if self._threshold > 0 else False
        return {
            "error": round(error, 6),
            "threshold": round(self._threshold, 6),
            "is_anomaly": is_anomaly,
        }

    def summary(self) -> dict[str, Any]:
        return {
            "input_dim": self.input_dim,
            "latent_dim": self.latent_dim,
            "trained_steps": self._trained_steps,
            "threshold": round(self._threshold, 6),
        }
