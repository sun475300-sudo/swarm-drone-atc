"""P736: PPO 기반 충돌 회피 정책 학습 — Stable-Baselines3 wrapper.

규칙 기반 APF·CBS와 동등 안전성 + 효율 개선 검증 목표.

환경(`SDACSGymEnv`)은 SimPy 엔진과 독립적인 경량 point-mass 운동학 모델로,
GPU/SB3 없이도 reset/step/observation/reward 계약이 완전히 동작한다.
학습(`train`)·평가(`evaluate`)만 stable-baselines3 + torch를 요구한다.

실행:
    python -m src.rl.ppo_collision train --steps 50000 --output models/ppo_v1.zip
    python -m src.rl.ppo_collision eval --model models/ppo_v1.zip --scenarios 10

의존성(학습 전용): stable-baselines3, gymnasium, torch.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

# --- 환경 물리 상수 (모든 단위 SI) ---
DT_S: float = 0.1  # 10Hz 제어 주기, DroneAgent와 동일
WORLD_SIZE_M: float = 100.0  # 스폰/목표 정육면체 한 변
MAX_ACCEL_MS2: float = 2.0  # 행동 [-1,1] → 가속도 스케일
MAX_SPEED_MS: float = 10.0  # 자기 드론 속도 클램프
NEIGHBOR_CRUISE_MS: float = 5.0  # 이웃 드론 등속 순항 속도
NEAR_MISS_DIST: float = 5.0  # 이 거리 미만 = near-miss
COLLISION_DIST: float = 1.5  # 이 거리 미만 = 충돌(종료)
GOAL_RADIUS_M: float = 3.0  # 목표 도달 판정 반경
COLLISION_PENALTY: float = 10.0  # 충돌 보상 가중치
PROGRESS_WEIGHT: float = 0.1  # 목표 접근 보상 가중치
DEFAULT_MAX_STEPS: int = 1000  # 에피소드 truncation 한계
FEATURES_PER_ENTITY: int = 7  # [x,y,z,vx,vy,vz,phase]


@dataclass(frozen=True)
class PPOConfig:
    """PPO 학습 하이퍼파라미터."""

    learning_rate: float = 3e-4
    n_steps: int = 2048
    batch_size: int = 64
    n_epochs: int = 10
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_range: float = 0.2
    ent_coef: float = 0.0
    vf_coef: float = 0.5
    max_grad_norm: float = 0.5


@dataclass
class TrainingStats:
    """학습 통계 추적."""

    total_timesteps: int = 0
    episodes: int = 0
    mean_reward: float = 0.0
    near_miss_rate: float = 0.0
    collision_rate: float = 0.0
    rewards_history: list[float] = field(default_factory=list)


class SDACSGymEnv:
    """SwarmSimulator의 충돌 회피 의사결정을 모사하는 경량 Gym 환경.

    자기 드론(index 0)을 행동으로 제어하여 목표까지 이동시키되,
    등속 순항하는 이웃 드론들과의 near-miss·충돌을 회피해야 한다.

    Observation: 자기 + 가장 가까운 N대 이웃의 [x, y, z, vx, vy, vz, phase].
        자기 항목의 위치는 목표 상대 좌표(목표 방향 신호), 이웃 항목은 자기 상대 좌표.
    Action: [ax, ay, az] continuous (-1, 1) → MAX_ACCEL 스케일 가속도.
    Reward: -(near_miss + COLLISION_PENALTY·collision) + PROGRESS_WEIGHT·progress.
    """

    def __init__(
        self,
        scenario: str = "default",
        n_drones: int = 50,
        max_neighbors: int = 8,
        seed: int | None = None,
        max_steps: int = DEFAULT_MAX_STEPS,
    ) -> None:
        """SDACSGymEnv 인스턴스를 초기화한다."""
        if n_drones < 1:
            raise ValueError("n_drones must be >= 1")
        self.scenario = scenario
        self.n_drones = n_drones
        self.max_neighbors = max_neighbors
        self.max_steps = max_steps
        self._seed = seed
        self._rng = np.random.default_rng(seed)
        self._step_count = 0
        self._positions = np.zeros((n_drones, 3))
        self._velocities = np.zeros((n_drones, 3))
        self._goals = np.zeros((n_drones, 3))
        self._prev_goal_dist = 0.0
        self.episode_near_misses = 0
        self.episode_collisions = 0
        self.min_separation = float("inf")
        self.observation_space, self.action_space = self._make_spaces()

    # --- Gym 핵심 API ---

    def reset(self, *, seed: int | None = None) -> tuple[np.ndarray, dict[str, Any]]:
        """환경을 초기 상태로 리셋."""
        # 명시적 seed가 오면 재시드, 아니면 기존 RNG를 advance한다(Gym 시맨틱).
        # 생성자 seed는 __init__에서 한 번만 적용 — 동일 seed 환경은 첫 에피소드를 재현하되
        # 학습 중 반복 reset은 서로 다른 에피소드를 생성한다.
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        self._step_count = 0
        self.episode_near_misses = 0
        self.episode_collisions = 0
        self.min_separation = float("inf")
        self._positions = self._rng.uniform(0.0, WORLD_SIZE_M, size=(self.n_drones, 3))
        self._goals = self._rng.uniform(0.0, WORLD_SIZE_M, size=(self.n_drones, 3))
        # 이웃 드론은 자기 목표를 향해 등속 순항. 자기 드론은 정지 상태로 시작(에이전트 제어).
        self._velocities = self._cruise_velocities()
        self._velocities[0] = 0.0
        self._prev_goal_dist = self._goal_distance()
        return self._build_observation(), {}

    def step(self, action: Any) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        """한 스텝 진행 + reward 계산."""
        self._step_count += 1
        self._integrate(np.asarray(action, dtype=np.float64).reshape(3))

        sep = self._nearest_separation()
        self.min_separation = min(self.min_separation, sep)
        is_collision = sep < COLLISION_DIST
        is_near_miss = (not is_collision) and sep < NEAR_MISS_DIST
        if is_near_miss:
            self.episode_near_misses += 1
        if is_collision:
            self.episode_collisions += 1

        goal_dist = self._goal_distance()
        progress = self._prev_goal_dist - goal_dist
        self._prev_goal_dist = goal_dist
        reached_goal = goal_dist < GOAL_RADIUS_M

        reward = -(float(is_near_miss) + COLLISION_PENALTY * float(is_collision))
        reward += PROGRESS_WEIGHT * progress

        terminated = bool(is_collision or reached_goal)
        truncated = self._step_count >= self.max_steps
        info = {
            "collision": bool(is_collision),
            "near_miss": bool(is_near_miss),
            "reached_goal": bool(reached_goal),
            "separation": float(sep),
        }
        return self._build_observation(), float(reward), terminated, truncated, info

    # --- 내부 운동학 ---

    def _cruise_velocities(self) -> np.ndarray:
        """각 드론이 자기 목표를 향하는 등속 순항 속도."""
        delta = self._goals - self._positions
        norms = np.linalg.norm(delta, axis=1, keepdims=True)
        unit = np.divide(delta, norms, out=np.zeros_like(delta), where=norms > 1e-9)
        return unit * NEIGHBOR_CRUISE_MS

    def _integrate(self, action: np.ndarray) -> None:
        """자기 드론은 행동 가속, 이웃은 등속 순항으로 1스텝 적분.

        성능 핫루프이므로 상태 배열을 in-place로 갱신한다(불변성 규칙의 의도적 예외).
        """
        accel = np.clip(action, -1.0, 1.0) * MAX_ACCEL_MS2
        self._velocities[0] += accel * DT_S
        speed = np.linalg.norm(self._velocities[0])
        if speed > MAX_SPEED_MS:
            self._velocities[0] *= MAX_SPEED_MS / speed
        if self.n_drones > 1:
            # 이웃은 매 스텝 목표 방향으로 재정렬(등속).
            self._velocities[1:] = self._cruise_velocities()[1:]
        self._positions += self._velocities * DT_S

    def _goal_distance(self) -> float:
        """자기 드론과 목표 사이 거리."""
        return float(np.linalg.norm(self._goals[0] - self._positions[0]))

    def _nearest_separation(self) -> float:
        """자기 드론과 가장 가까운 이웃 사이 거리."""
        if self.n_drones < 2:
            return float("inf")
        deltas = self._positions[1:] - self._positions[0]
        return float(np.min(np.linalg.norm(deltas, axis=1)))

    def _build_observation(self) -> np.ndarray:
        """자기 + 최근접 N 이웃 상태를 평탄화한 관측 벡터."""
        obs = np.zeros(FEATURES_PER_ENTITY * (self.max_neighbors + 1), dtype=np.float32)
        # 자기 항목: 목표 상대 위치 + 속도.
        obs[0:3] = self._goals[0] - self._positions[0]
        obs[3:6] = self._velocities[0]
        obs[6] = 0.0  # phase: cruise

        if self.n_drones > 1:
            deltas = self._positions[1:] - self._positions[0]
            dists = np.linalg.norm(deltas, axis=1)
            order = np.argsort(dists)[: self.max_neighbors]
            for slot, idx in enumerate(order):
                neighbor = idx + 1
                base = FEATURES_PER_ENTITY * (slot + 1)
                obs[base : base + 3] = self._positions[neighbor] - self._positions[0]
                obs[base + 3 : base + 6] = self._velocities[neighbor] - self._velocities[0]
                obs[base + 6] = 0.0
        return obs

    def _make_spaces(self) -> tuple[Any, Any]:
        """gymnasium 설치 시 Box 공간, 아니면 (None, None) 반환."""
        try:
            from gymnasium import spaces  # type: ignore[import-not-found]
        except ImportError:
            return None, None
        obs_dim = FEATURES_PER_ENTITY * (self.max_neighbors + 1)
        observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32
        )
        action_space = spaces.Box(low=-1.0, high=1.0, shape=(3,), dtype=np.float32)
        return observation_space, action_space


def train(cfg: PPOConfig, env: SDACSGymEnv, total_timesteps: int = 50_000) -> TrainingStats:
    """PPO 정책 학습 + 통계 반환."""
    stats = TrainingStats()
    try:
        from stable_baselines3 import PPO  # type: ignore[import-not-found]
    except ImportError as e:
        raise RuntimeError("stable-baselines3 필요: pip install stable-baselines3") from e

    if env.observation_space is None or env.action_space is None:
        raise RuntimeError("gymnasium 필요: pip install gymnasium")

    model = PPO(
        "MlpPolicy",
        env=env,
        learning_rate=cfg.learning_rate,
        n_steps=cfg.n_steps,
        batch_size=cfg.batch_size,
        n_epochs=cfg.n_epochs,
        gamma=cfg.gamma,
        gae_lambda=cfg.gae_lambda,
        clip_range=cfg.clip_range,
        ent_coef=cfg.ent_coef,
        vf_coef=cfg.vf_coef,
        max_grad_norm=cfg.max_grad_norm,
        verbose=1,
    )
    model.learn(total_timesteps=total_timesteps)
    stats.total_timesteps = total_timesteps
    return stats


def rollout(env: SDACSGymEnv, policy: Any | None = None, seed: int | None = None) -> dict[str, float]:
    """단일 에피소드 실행 후 안전·효율 메트릭 집계.

    policy가 None이면 무행동(0 가속) 정책으로 평가한다. SB3 모델이면 predict 사용.
    """
    obs, _ = env.reset(seed=seed)
    steps = 0
    total_reward = 0.0
    while True:
        if policy is None:
            action: Any = np.zeros(3, dtype=np.float32)
        elif hasattr(policy, "predict"):
            action, _ = policy.predict(obs, deterministic=True)
        else:
            action = policy(obs)
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        steps += 1
        if terminated or truncated:
            break
    return {
        "steps": float(steps),
        "total_reward": float(total_reward),
        "near_misses": float(env.episode_near_misses),
        "collisions": float(env.episode_collisions),
        "min_separation": float(env.min_separation),
        "reached_goal": float(info["reached_goal"]),
    }


def evaluate(model_path: str | None = None, scenarios: int = 10, seeds: int = 5) -> dict[str, float]:
    """학습된 모델(또는 무행동 기준선)을 N 시나리오 × M seed로 평가.

    model_path가 None이면 무행동 기준선을 평가한다(샌드박스/CI에서 SB3 불필요).
    반환: NMR(near-miss/step), MSD(평균 최소분리), collision_rate, success_rate, FT(평균 비행 스텝).
    """
    policy = None
    if model_path is not None:
        from stable_baselines3 import PPO  # type: ignore[import-not-found]

        policy = PPO.load(model_path)

    results: list[dict[str, float]] = []
    for s in range(scenarios):
        for m in range(seeds):
            env = SDACSGymEnv(seed=s * seeds + m)
            results.append(rollout(env, policy=policy))

    total_steps = sum(r["steps"] for r in results) or 1.0
    total_near_misses = sum(r["near_misses"] for r in results)
    total_collisions = sum(r["collisions"] for r in results)
    return {
        "NMR": total_near_misses / total_steps,
        "MSD": float(np.mean([r["min_separation"] for r in results])),
        "collision_rate": total_collisions / len(results),
        "success_rate": float(np.mean([r["reached_goal"] for r in results])),
        "FT": float(np.mean([r["steps"] for r in results])),
    }
