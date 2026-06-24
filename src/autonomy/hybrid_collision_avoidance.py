"""GENESIS Phase 362: Hybrid APF + RL Collision Avoidance Module.

규칙 기반 APF(Artificial Potential Field)와 학습 기반 RL(PPO) 정책 출력을
가중 블렌딩하되, 안전 임계 거리 이내에서는 APF가 100% 제어권을 확보하는
규칙 우선 안전 보증(rule-priority safety guarantee) 하이브리드 모듈.

APF 계산은 apf_engine/apf.py의 FIRAS 모델과 동일한 수식을 자체 구현하여
모듈 간 결합도를 제거함.

사용 예:
    python -m src.autonomy.hybrid_collision_avoidance --evaluate --seed 42 --drones 10 --steps 200
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

import numpy as np

# --- 물리 상수 (ppo_collision.py와 동일) ---
DT_S: float = 0.1  # 10Hz 제어 주기
WORLD_SIZE_M: float = 100.0  # 스폰/목표 정육면체 한 변
MAX_SPEED_MS: float = 10.0  # 드론 속도 클램프
NEIGHBOR_CRUISE_MS: float = 5.0  # 이웃 등속 순항 속도
COLLISION_DIST: float = 1.5  # 충돌 판정 거리 (m)
NEAR_MISS_DIST: float = 5.0  # 니어미스 판정 거리 (m)
GOAL_RADIUS_M: float = 3.0  # 목표 도달 판정 반경

# --- APF 기본 파라미터 (apf.py APF_PARAMS와 동일) ---
DEFAULT_K_ATT: float = 1.0  # 인력 게인
DEFAULT_K_REP: float = 2.5  # 드론 간 척력 게인
DEFAULT_D0: float = 50.0  # 드론 간 영향 거리 (m)
DEFAULT_MAX_FORCE: float = 10.0  # 최대 합력 (m/s^2)


@dataclass(frozen=True)
class HybridConfig:
    """하이브리드 블렌딩 설정."""

    apf_weight: float = 0.7  # APF 비율 [0, 1]
    rl_weight: float = 0.3  # RL 비율 (1 - apf_weight)
    safety_override_dist_m: float = 5.0  # 이 거리 이하 APF 100% 제어
    rl_action_scale: float = 2.0  # [-1,1] RL 출력 → m/s^2 변환 스케일

    def __post_init__(self) -> None:
        if self.apf_weight < 0 or self.rl_weight < 0:
            raise ValueError("가중치는 0 이상이어야 합니다")
        if self.safety_override_dist_m <= 0:
            raise ValueError("safety_override_dist_m은 양수여야 합니다")
        if abs(self.apf_weight + self.rl_weight - 1.0) > 1e-9:
            raise ValueError(
                f"가중치 합이 1.0이어야 합니다 (현재: {self.apf_weight + self.rl_weight})"
            )
        if self.rl_action_scale <= 0:
            raise ValueError("rl_action_scale은 양수여야 합니다")


@dataclass(frozen=True)
class HybridAction:
    """블렌딩된 충돌 회피 행동 결과."""

    force: tuple[float, float, float]  # 블렌딩된 가속도 벡터
    apf_contribution: tuple[float, float, float]  # APF 성분
    rl_contribution: tuple[float, float, float]  # RL 성분
    mode: str  # "hybrid" | "safety_override" | "apf_only"
    min_neighbor_dist_m: float  # 최근접 이웃 거리
    blend_ratio: float  # 실제 사용된 APF 가중치 (safety override 시 1.0)


@dataclass(frozen=True)
class EpisodeResult:
    """에피소드 평가 결과."""

    collisions: int
    near_misses: int
    goals_reached: int
    total_steps: int
    safety_overrides: int  # 안전 오버라이드 발동 횟수
    mean_min_dist_m: float  # 평균 최소 이웃 거리


def _attractive_force(
    pos: np.ndarray, goal: np.ndarray, k_att: float = DEFAULT_K_ATT
) -> np.ndarray:
    """목표 방향 인력 (apf.py 수식 동일)."""
    diff = goal - pos
    dist = float(np.linalg.norm(diff))
    if dist < 0.1:
        return np.zeros(3)
    d_t = 10.0
    if dist <= d_t:
        return k_att * diff  # 이차 인력 (근거리)
    return k_att * diff / dist * d_t  # 단위 벡터 기반 (원거리)


def _repulsive_force(
    own_pos: np.ndarray,
    other_pos: np.ndarray,
    own_vel: np.ndarray,
    other_vel: np.ndarray,
    k_rep: float = DEFAULT_K_REP,
    d0: float = DEFAULT_D0,
) -> np.ndarray:
    """FIRAS 척력 모델 (apf.py repulsive_force_drone 동일)."""
    diff = own_pos - other_pos
    dist = float(np.linalg.norm(diff))

    if dist < 1e-3 or dist >= d0:
        return np.zeros(3)

    n = diff / dist
    mag = k_rep * (1.0 / dist - 1.0 / d0) / (dist**2)

    # 속도 기반 접근 보정
    relative_vel = own_vel - other_vel
    closing_speed = float(-np.dot(relative_vel, n))
    if closing_speed > 0:
        amplification = min(1.0 + closing_speed / 3.0, 3.0)
        mag *= amplification

    return mag * n


class HybridCollisionAvoidance:
    """APF + RL 하이브리드 충돌 회피 모듈."""

    def __init__(self, config: HybridConfig | None = None) -> None:
        self._config = config if config is not None else HybridConfig()

    @property
    def config(self) -> HybridConfig:
        return self._config

    def compute(
        self,
        drone_pos: np.ndarray,
        drone_vel: np.ndarray,
        goal_pos: np.ndarray,
        neighbor_positions: list[np.ndarray],
        neighbor_velocities: list[np.ndarray],
        obstacle_positions: list[np.ndarray] | None = None,
        rl_action: np.ndarray | None = None,
    ) -> HybridAction:
        """블렌딩된 충돌 회피 힘 계산.

        Args:
            drone_pos: 자기 드론 위치 [x, y, z]
            drone_vel: 자기 드론 속도 [vx, vy, vz]
            goal_pos: 목표 위치 [x, y, z]
            neighbor_positions: 이웃 드론 위치 리스트
            neighbor_velocities: 이웃 드론 속도 리스트
            obstacle_positions: 장애물 위치 리스트 (미사용 시 None)
            rl_action: RL 정책 출력 [-1, 1]^3 (None이면 APF 단독)

        Returns:
            HybridAction: 블렌딩 결과
        """
        pos = np.asarray(drone_pos, dtype=np.float64)
        vel = np.asarray(drone_vel, dtype=np.float64)
        goal = np.asarray(goal_pos, dtype=np.float64)

        # APF 합력 계산
        apf_force = _attractive_force(pos, goal)
        for i, n_pos in enumerate(neighbor_positions):
            n_vel = (
                neighbor_velocities[i]
                if i < len(neighbor_velocities)
                else np.zeros(3)
            )
            apf_force = apf_force + _repulsive_force(
                pos, np.asarray(n_pos), vel, np.asarray(n_vel)
            )

        # 최근접 이웃 거리
        if neighbor_positions:
            dists = [
                float(np.linalg.norm(pos - np.asarray(n_pos)))
                for n_pos in neighbor_positions
            ]
            min_dist = min(dists)
        else:
            min_dist = float("inf")

        # 모드 결정 및 블렌딩
        if rl_action is None:
            mode = "apf_only"
            rl_force = np.zeros(3)
            blend_ratio = 1.0
            total = apf_force.copy()
        elif min_dist < self._config.safety_override_dist_m:
            mode = "safety_override"
            rl_force = (
                np.clip(np.asarray(rl_action, dtype=np.float64), -1.0, 1.0)
                * self._config.rl_action_scale
            )
            blend_ratio = 1.0
            total = apf_force.copy()
        else:
            mode = "hybrid"
            rl_force = (
                np.clip(np.asarray(rl_action, dtype=np.float64), -1.0, 1.0)
                * self._config.rl_action_scale
            )
            blend_ratio = self._config.apf_weight
            total = (
                self._config.apf_weight * apf_force
                + self._config.rl_weight * rl_force
            )

        # 최대 합력 클램프
        mag = float(np.linalg.norm(total))
        if mag > DEFAULT_MAX_FORCE:
            total = total / mag * DEFAULT_MAX_FORCE

        return HybridAction(
            force=(float(total[0]), float(total[1]), float(total[2])),
            apf_contribution=(
                float(apf_force[0]),
                float(apf_force[1]),
                float(apf_force[2]),
            ),
            rl_contribution=(
                float(rl_force[0]),
                float(rl_force[1]),
                float(rl_force[2]),
            ),
            mode=mode,
            min_neighbor_dist_m=min_dist,
            blend_ratio=blend_ratio,
        )

    def evaluate_episode(
        self,
        n_drones: int = 10,
        n_steps: int = 200,
        seed: int = 42,
        rl_actions: np.ndarray | None = None,
    ) -> EpisodeResult:
        """포인트매스 역학으로 에피소드 평가.

        Args:
            n_drones: 드론 수 (0번이 자기 드론)
            n_steps: 최대 스텝 수
            seed: 재현용 시드
            rl_actions: (n_steps, 3) RL 행동 시퀀스 (None이면 APF 단독)

        Returns:
            EpisodeResult: 에피소드 결과 통계
        """
        rng = np.random.default_rng(seed)

        positions = rng.uniform(0.0, WORLD_SIZE_M, size=(n_drones, 3))
        goals = rng.uniform(0.0, WORLD_SIZE_M, size=(n_drones, 3))

        # 이웃 등속 순항 속도 초기화
        velocities = np.zeros((n_drones, 3))
        for i in range(1, n_drones):
            delta = goals[i] - positions[i]
            norm = float(np.linalg.norm(delta))
            if norm > 1e-9:
                velocities[i] = delta / norm * NEIGHBOR_CRUISE_MS

        # 자기 드론 정지 시작
        velocities[0] = 0.0

        collisions = 0
        near_misses = 0
        goals_reached = 0
        safety_overrides = 0
        min_dists: list[float] = []

        for step in range(n_steps):
            # 이웃 위치/속도 수집
            neighbor_positions = [positions[i].copy() for i in range(1, n_drones)]
            neighbor_velocities = [velocities[i].copy() for i in range(1, n_drones)]

            # RL 행동 선택
            rl_action = None
            if rl_actions is not None and step < len(rl_actions):
                rl_action = rl_actions[step]

            # 하이브리드 계산
            action = self.compute(
                drone_pos=positions[0],
                drone_vel=velocities[0],
                goal_pos=goals[0],
                neighbor_positions=neighbor_positions,
                neighbor_velocities=neighbor_velocities,
                rl_action=rl_action,
            )

            if action.mode == "safety_override":
                safety_overrides += 1

            # 자기 드론 적분
            accel = np.array(action.force)
            velocities[0] = velocities[0] + accel * DT_S
            speed = float(np.linalg.norm(velocities[0]))
            if speed > MAX_SPEED_MS:
                velocities[0] = velocities[0] / speed * MAX_SPEED_MS

            # 이웃 드론 등속 이동 (매 스텝 목표 방향 재정렬)
            for i in range(1, n_drones):
                delta = goals[i] - positions[i]
                norm = float(np.linalg.norm(delta))
                if norm > 1e-9:
                    velocities[i] = delta / norm * NEIGHBOR_CRUISE_MS
                else:
                    velocities[i] = np.zeros(3)

            # 전체 위치 업데이트
            positions = positions + velocities * DT_S

            # 최근접 이웃 거리
            if n_drones > 1:
                deltas = positions[1:] - positions[0]
                dists_arr = np.linalg.norm(deltas, axis=1)
                min_dist = float(np.min(dists_arr))
            else:
                min_dist = float("inf")

            min_dists.append(min_dist)

            # 충돌/니어미스 판정
            if min_dist < COLLISION_DIST:
                collisions += 1
            elif min_dist < NEAR_MISS_DIST:
                near_misses += 1

            # 목표 도달 판정
            goal_dist = float(np.linalg.norm(goals[0] - positions[0]))
            if goal_dist < GOAL_RADIUS_M:
                goals_reached += 1
                break

        mean_min_dist = float(np.mean(min_dists)) if min_dists else 0.0
        actual_steps = len(min_dists)

        return EpisodeResult(
            collisions=collisions,
            near_misses=near_misses,
            goals_reached=goals_reached,
            total_steps=actual_steps,
            safety_overrides=safety_overrides,
            mean_min_dist_m=mean_min_dist,
        )


def main() -> None:
    """CLI 엔트리포인트."""
    parser = argparse.ArgumentParser(
        description="GENESIS Phase 362: Hybrid APF+RL Collision Avoidance"
    )
    parser.add_argument("--evaluate", action="store_true", help="에피소드 평가 실행")
    parser.add_argument("--seed", type=int, default=42, help="난수 시드")
    parser.add_argument("--drones", type=int, default=10, help="드론 수")
    parser.add_argument("--steps", type=int, default=200, help="최대 스텝 수")
    args = parser.parse_args()

    if not args.evaluate:
        parser.print_help()
        sys.exit(0)

    hca = HybridCollisionAvoidance()
    result = hca.evaluate_episode(
        n_drones=args.drones,
        n_steps=args.steps,
        seed=args.seed,
    )

    print(f"=== Hybrid Collision Avoidance Evaluation (Phase 362) ===")
    print(f"Drones: {args.drones}, Steps: {result.total_steps}, Seed: {args.seed}")
    print(f"Collisions:        {result.collisions}")
    print(f"Near Misses:       {result.near_misses}")
    print(f"Goals Reached:     {result.goals_reached}")
    print(f"Safety Overrides:  {result.safety_overrides}")
    print(f"Mean Min Dist (m): {result.mean_min_dist_m:.2f}")


if __name__ == "__main__":
    main()
