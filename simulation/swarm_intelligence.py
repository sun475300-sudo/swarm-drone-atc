"""
군집지능 알고리즘
================
Boids(분리/정렬/응집) + PSO(Particle Swarm Optimization) 목표 탐색.
군집 비행의 자율 행동 생성.

사용법:
    swarm = SwarmIntelligence(n_agents=20)
    swarm.update_positions(positions, velocities)
    new_vels = swarm.compute_boids()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class BoidParams:
    """Boids 파라미터"""
    separation_weight: float = 1.5
    alignment_weight: float = 1.0
    cohesion_weight: float = 1.0
    separation_radius: float = 30.0  # m
    neighbor_radius: float = 80.0  # m
    max_speed: float = 15.0  # m/s
    max_force: float = 5.0  # m/s²


@dataclass
class PSOParams:
    """PSO 파라미터"""
    inertia_weight: float = 0.7
    cognitive_weight: float = 1.5  # 개인 최적 가중치
    social_weight: float = 2.0  # 전역 최적 가중치
    max_velocity: float = 10.0


@dataclass
class SwarmState:
    """군집 상태"""
    center_of_mass: np.ndarray
    avg_velocity: np.ndarray
    spread: float  # 분산 (표준편차)
    min_separation: float
    avg_separation: float
    cohesion_index: float  # 0~1 (1=완전 응집)


class SwarmIntelligence:
    """
    군집지능 엔진.

    Boids 행동 규칙 + PSO 목표 탐색.
    """

    def __init__(
        self,
        n_agents: int = 20,
        boid_params: BoidParams | None = None,
        pso_params: PSOParams | None = None,
        rng_seed: int = 42,
    ) -> None:
        self.n_agents = n_agents
        self.boid = boid_params or BoidParams()
        self.pso = pso_params or PSOParams()
        self._rng = np.random.default_rng(rng_seed)

        # 위치/속도 (N x 3)
        self._positions: np.ndarray = np.zeros((n_agents, 3))
        self._velocities: np.ndarray = np.zeros((n_agents, 3))

        # PSO 상태
        self._personal_best_pos: np.ndarray = np.zeros((n_agents, 3))
        self._personal_best_val: np.ndarray = np.full(n_agents, float("inf"))
        self._global_best_pos: np.ndarray = np.zeros(3)
        self._global_best_val: float = float("inf")

        # 목표 (PSO용)
        self._targets: list[np.ndarray] = []

    def update_positions(
        self, positions: np.ndarray, velocities: np.ndarray | None = None
    ) -> None:
        """외부에서 위치/속도 갱신"""
        n = min(len(positions), self.n_agents)
        self._positions[:n] = positions[:n]
        if velocities is not None:
            self._velocities[:n] = velocities[:n]

    def set_target(self, target: tuple[float, float, float]) -> None:
        """PSO 목표 지점 설정"""
        self._targets = [np.array(target, dtype=float)]

    def set_targets(self, targets: list[tuple[float, float, float]]) -> None:
        """다중 목표 설정"""
        self._targets = [np.array(t, dtype=float) for t in targets]

    def compute_boids(self) -> np.ndarray:
        """
        Boids 알고리즘으로 속도 벡터 계산.

        Returns: (N, 3) 새 속도 벡터
        """
        n = self.n_agents
        new_velocities = np.zeros_like(self._velocities)

        for i in range(n):
            sep = self._separation(i)
            ali = self._alignment(i)
            coh = self._cohesion(i)

            force = (
                sep * self.boid.separation_weight
                + ali * self.boid.alignment_weight
                + coh * self.boid.cohesion_weight
            )

            # 힘 제한
            force_mag = float(np.linalg.norm(force))
            if force_mag > self.boid.max_force:
                force = force / force_mag * self.boid.max_force

            new_vel = self._velocities[i] + force
            # 속도 제한
            speed = float(np.linalg.norm(new_vel))
            if speed > self.boid.max_speed:
                new_vel = new_vel / speed * self.boid.max_speed

            new_velocities[i] = new_vel

        self._velocities = new_velocities
        return new_velocities.copy()

    def compute_pso(self, fitness_fn: Any = None) -> np.ndarray:
        """
        PSO 한 스텝 계산.

        fitness_fn: (position) -> float (낮을수록 좋음). None이면 target까지 거리.
        Returns: (N, 3) 새 속도 벡터
        """
        n = self.n_agents

        for i in range(n):
            # 적합도 평가
            if fitness_fn is not None:
                val = fitness_fn(self._positions[i])
            elif self._targets:
                val = min(
                    float(np.linalg.norm(self._positions[i] - t))
                    for t in self._targets
                )
            else:
                val = float(np.linalg.norm(self._positions[i]))

            # 개인 최적 갱신
            if val < self._personal_best_val[i]:
                self._personal_best_val[i] = val
                self._personal_best_pos[i] = self._positions[i].copy()

            # 전역 최적 갱신
            if val < self._global_best_val:
                self._global_best_val = val
                self._global_best_pos = self._positions[i].copy()

        # 속도 갱신
        r1 = self._rng.random((n, 3))
        r2 = self._rng.random((n, 3))

        cognitive = (
            self.pso.cognitive_weight * r1
            * (self._personal_best_pos - self._positions)
        )
        social = (
            self.pso.social_weight * r2
            * (self._global_best_pos - self._positions)
        )

        self._velocities = (
            self.pso.inertia_weight * self._velocities
            + cognitive + social
        )

        # 속도 제한
        speeds = np.linalg.norm(self._velocities, axis=1, keepdims=True)
        mask = speeds.flatten() > self.pso.max_velocity
        if np.any(mask):
            self._velocities[mask] = (
                self._velocities[mask]
                / speeds[mask]
                * self.pso.max_velocity
            )

        return self._velocities.copy()

    def step(self, dt: float = 0.1, mode: str = "boids") -> np.ndarray:
        """한 스텝 실행 (위치 갱신 포함)"""
        if mode == "pso":
            self.compute_pso()
        else:
            self.compute_boids()

        self._positions += self._velocities * dt
        return self._positions.copy()

    def get_state(self) -> SwarmState:
        """현재 군집 상태 분석"""
        com = np.mean(self._positions, axis=0)
        avg_vel = np.mean(self._velocities, axis=0)

        dists_from_com = np.linalg.norm(
            self._positions - com, axis=1
        )
        spread = float(np.std(dists_from_com))

        # 최소/평균 분리 거리
        n = self.n_agents
        min_sep = float("inf")
        sep_sum = 0.0
        count = 0
        for i in range(n):
            for j in range(i + 1, n):
                d = float(np.linalg.norm(
                    self._positions[i] - self._positions[j]
                ))
                min_sep = min(min_sep, d)
                sep_sum += d
                count += 1

        avg_sep = sep_sum / max(count, 1)
        if min_sep == float("inf"):
            min_sep = 0.0

        # 응집 지수 (spread가 작을수록 높음)
        cohesion = max(0.0, 1.0 - spread / max(avg_sep, 1.0))

        return SwarmState(
            center_of_mass=com,
            avg_velocity=avg_vel,
            spread=spread,
            min_separation=min_sep,
            avg_separation=avg_sep,
            cohesion_index=float(min(1.0, cohesion)),
        )

    def _neighbors(self, idx: int, radius: float) -> list[int]:
        """반경 내 이웃 인덱스"""
        neighbors = []
        for j in range(self.n_agents):
            if j == idx:
                continue
            d = float(np.linalg.norm(
                self._positions[idx] - self._positions[j]
            ))
            if d < radius:
                neighbors.append(j)
        return neighbors

    def _separation(self, idx: int) -> np.ndarray:
        """분리 규칙: 너무 가까운 이웃으로부터 멀어짐"""
        neighbors = self._neighbors(idx, self.boid.separation_radius)
        if not neighbors:
            return np.zeros(3)

        steer = np.zeros(3)
        for j in neighbors:
            diff = self._positions[idx] - self._positions[j]
            dist = float(np.linalg.norm(diff))
            if dist > 0:
                steer += diff / (dist * dist)  # 거리 반비례

        return steer / len(neighbors)

    def _alignment(self, idx: int) -> np.ndarray:
        """정렬 규칙: 이웃의 평균 속도 방향으로"""
        neighbors = self._neighbors(idx, self.boid.neighbor_radius)
        if not neighbors:
            return np.zeros(3)

        avg_vel = np.mean(
            [self._velocities[j] for j in neighbors], axis=0
        )
        return avg_vel - self._velocities[idx]

    def _cohesion(self, idx: int) -> np.ndarray:
        """응집 규칙: 이웃의 중심으로 이동"""
        neighbors = self._neighbors(idx, self.boid.neighbor_radius)
        if not neighbors:
            return np.zeros(3)

        center = np.mean(
            [self._positions[j] for j in neighbors], axis=0
        )
        return center - self._positions[idx]

    @property
    def positions(self) -> np.ndarray:
        return self._positions.copy()

    @property
    def velocities(self) -> np.ndarray:
        return self._velocities.copy()

    def summary(self) -> dict[str, Any]:
        state = self.get_state()
        return {
            "n_agents": self.n_agents,
            "center_of_mass": state.center_of_mass.tolist(),
            "spread": round(state.spread, 2),
            "min_separation": round(state.min_separation, 2),
            "avg_separation": round(state.avg_separation, 2),
            "cohesion_index": round(state.cohesion_index, 3),
            "global_best_val": self._global_best_val,
        }
