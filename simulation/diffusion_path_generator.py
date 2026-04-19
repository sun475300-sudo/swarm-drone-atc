"""Phase 662: Diffusion Model 기반 경로 생성."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import torch
import torch.nn as nn

DEFAULT_TIMESTEPS = 100
PATH_DIM = 3  # x, y, z


@dataclass
class DiffusionStats:
    train_steps: int = 0
    total_loss: float = 0.0
    losses: List[float] = field(default_factory=list)

    @property
    def mean_loss(self) -> float:
        return self.total_loss / max(self.train_steps, 1)


class NoiseScheduler:
    """Linear beta noise schedule for diffusion process."""

    def __init__(
        self,
        num_timesteps: int = DEFAULT_TIMESTEPS,
        beta_start: float = 1e-4,
        beta_end: float = 0.02,
    ) -> None:
        self.num_timesteps = num_timesteps
        self.betas = np.linspace(beta_start, beta_end, num_timesteps, dtype=np.float32)
        self.alphas = 1.0 - self.betas
        self.alpha_bars = np.cumprod(self.alphas)
        self.alpha_bars_tensor = torch.from_numpy(self.alpha_bars)

    def add_noise(
        self, x_0: torch.Tensor, t: torch.Tensor, noise: Optional[torch.Tensor] = None
    ) -> tuple:
        """Add noise to clean data at timestep t.

        Args:
            x_0: clean data (batch, path_len, 3)
            t: timestep indices (batch,)
            noise: optional pre-generated noise

        Returns:
            (noisy_sample, noise_used)
        """
        if noise is None:
            noise = torch.randn_like(x_0)

        alpha_bar = self.alpha_bars_tensor.to(t.device)[t].float()
        while alpha_bar.dim() < x_0.dim():
            alpha_bar = alpha_bar.unsqueeze(-1)

        sqrt_ab = torch.sqrt(alpha_bar)
        sqrt_one_minus_ab = torch.sqrt(1.0 - alpha_bar)

        noisy = sqrt_ab * x_0 + sqrt_one_minus_ab * noise
        return noisy, noise


class TimeEmbedding(nn.Module):
    """Sinusoidal time step embedding."""

    def __init__(self, dim: int) -> None:
        super().__init__()
        self.dim = dim

    def forward(self, t: torch.Tensor) -> torch.Tensor:
        half = self.dim // 2
        freqs = torch.exp(
            -np.log(10000.0) * torch.arange(half, device=t.device).float() / half
        )
        args = t.float().unsqueeze(-1) * freqs.unsqueeze(0)
        return torch.cat([torch.sin(args), torch.cos(args)], dim=-1)


class DenoisingNetwork(nn.Module):
    """MLP-based denoising network for path diffusion."""

    def __init__(
        self,
        path_length: int = 20,
        path_dim: int = PATH_DIM,
        hidden_dim: int = 128,
        time_dim: int = 32,
    ) -> None:
        super().__init__()
        self.path_length = path_length
        self.path_dim = path_dim
        flat_dim = path_length * path_dim

        self.time_embed = TimeEmbedding(time_dim)

        self.net = nn.Sequential(
            nn.Linear(flat_dim + time_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, flat_dim),
        )

    def forward(self, x: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
        """Predict noise from noisy path and timestep.

        Args:
            x: (batch, path_length, path_dim) noisy paths
            t: (batch,) timestep indices

        Returns:
            (batch, path_length, path_dim) predicted noise
        """
        batch = x.shape[0]
        x_flat = x.view(batch, -1)
        t_emb = self.time_embed(t)
        inp = torch.cat([x_flat, t_emb], dim=-1)
        out = self.net(inp)
        return out.view(batch, self.path_length, self.path_dim)


class DiffusionPathGenerator:
    """Denoising diffusion model for generating drone flight paths."""

    def __init__(
        self,
        path_length: int = 20,
        num_timesteps: int = DEFAULT_TIMESTEPS,
        hidden_dim: int = 128,
        lr: float = 1e-3,
        seed: int = 42,
    ) -> None:
        self.rng = np.random.default_rng(seed)
        self.path_length = path_length
        self.num_timesteps = num_timesteps
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.scheduler = NoiseScheduler(num_timesteps=num_timesteps)
        self.model = DenoisingNetwork(
            path_length=path_length, hidden_dim=hidden_dim
        ).to(self.device)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        self.loss_fn = nn.MSELoss()
        self.stats = DiffusionStats()

    def train_step(self, clean_paths: np.ndarray) -> float:
        """Single training step on clean path data.

        Args:
            clean_paths: (batch, path_length, 3)

        Returns:
            loss value
        """
        self.model.train()
        x_0 = torch.from_numpy(clean_paths).float().to(self.device)
        batch = x_0.shape[0]

        t = torch.randint(0, self.num_timesteps, (batch,), device=self.device)
        noisy, noise = self.scheduler.add_noise(x_0, t)

        self.optimizer.zero_grad()
        pred_noise = self.model(noisy, t)
        loss = self.loss_fn(pred_noise, noise)
        loss.backward()
        self.optimizer.step()

        loss_val = loss.item()
        self.stats.train_steps += 1
        self.stats.total_loss += loss_val
        self.stats.losses.append(loss_val)
        return loss_val

    @torch.no_grad()
    def sample(self, num_paths: int = 1, path_length: Optional[int] = None) -> np.ndarray:
        """Generate paths by reverse diffusion.

        Args:
            num_paths: number of paths to generate
            path_length: override path length (uses default if None)

        Returns:
            (num_paths, path_length, 3) generated paths
        """
        self.model.eval()
        pl = path_length or self.path_length
        x = torch.randn(num_paths, pl, PATH_DIM, device=self.device)

        for t_idx in reversed(range(self.num_timesteps)):
            t = torch.full((num_paths,), t_idx, device=self.device, dtype=torch.long)
            pred_noise = self.model(x, t)

            alpha = self.scheduler.alphas[t_idx]
            alpha_bar = self.scheduler.alpha_bars[t_idx]
            beta = self.scheduler.betas[t_idx]

            coeff = beta / np.sqrt(1.0 - alpha_bar)
            x = (x - coeff * pred_noise) / np.sqrt(alpha)

            if t_idx > 0:
                noise = torch.randn_like(x)
                x = x + np.sqrt(beta) * noise

        return x.cpu().numpy()

    @torch.no_grad()
    def generate(
        self, start_pos: np.ndarray, end_pos: np.ndarray, num_steps: int = 20
    ) -> np.ndarray:
        """Generate a path conditioned on start and end positions.

        Args:
            start_pos: (3,) start position
            end_pos: (3,) end position
            num_steps: number of waypoints

        Returns:
            (num_steps, 3) generated path
        """
        raw = self.sample(num_paths=1, path_length=num_steps)[0]

        # Condition: pin start and end, interpolate conditioning
        raw[0] = start_pos
        raw[-1] = end_pos

        for i in range(1, num_steps - 1):
            alpha = i / (num_steps - 1)
            baseline = (1 - alpha) * start_pos + alpha * end_pos
            raw[i] = 0.5 * raw[i] + 0.5 * baseline

        return raw

    def get_stats(self) -> Dict[str, float]:
        return {
            "train_steps": self.stats.train_steps,
            "mean_loss": self.stats.mean_loss,
            "latest_loss": self.stats.losses[-1] if self.stats.losses else 0.0,
        }
