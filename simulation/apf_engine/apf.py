"""
APF (인공 포텐셜 장) 충돌 회피 엔진
SC2 봇의 Boids 로직을 수학적으로 형식화한 구현

수식:
  F_total = F_goal + Σ F_repulsive(obstacle_i) + Σ F_repulsive(drone_j)

  F_goal      = k_att * (goal - pos) / |goal - pos|        (인력)
  F_repulsive = k_rep * (1/dist - 1/d0) * (1/dist²) * n̂    (척력, dist < d0)
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass


# SC2 14,200회 검증에서 최적화된 파라미터 (공역 단위: 미터)
APF_PARAMS = {
    "k_att": 1.0,           # 인력 게인
    "k_rep_drone": 2.5,     # 드론 간 척력 게인 (SC2 separation_weight에 대응)
    "k_rep_obs": 5.0,       # 장애물 척력 게인
    "d0_drone": 50.0,       # 드론 간 영향 거리 (m) - separation_radius 대응
    "d0_obs": 30.0,         # 장애물 영향 거리 (m)
    "max_force": 10.0,      # 최대 합력 (m/s²)
    "altitude_k": 0.5,      # 고도 보정 게인
    "target_alt": 60.0,     # 순항 고도 (m)
}

# 강풍 조건용 파라미터 (weather_disturbance 시나리오 개선)
# 2차 최적화: 더 공격적인 충돌 회피
APF_PARAMS_WINDY = {
    "k_att": 1.0,           # 인력 게인 (목표 추적, 척력과 균형)
    "k_rep_drone": 6.5,     # 드론 간 척력 게인 (2차 개선: 4.5 → 6.5)
    "k_rep_obs": 7.0,       # 장애물 척력 게인
    "d0_drone": 80.0,       # 드론 간 영향 거리 (m) - 더 조기 회피 (70 → 80)
    "d0_obs": 45.0,         # 장애물 영향 거리 (m)
    "max_force": 22.0,      # 최대 합력 (m/s²) - 강풍 저항 강화 (18 → 22)
    "altitude_k": 1.0,      # 고도 보정 게인 (윈드 시어 대응)
    "target_alt": 60.0,     # 순항 고도 (m)
}


@dataclass
class APFState:
    """드론 상태 (APF 계산용)"""
    position: np.ndarray    # [x, y, z] m
    velocity: np.ndarray    # [vx, vy, vz] m/s
    drone_id: str


def attractive_force(pos: np.ndarray, goal: np.ndarray, k_att: float = APF_PARAMS["k_att"]) -> np.ndarray:
    """
    목표 지점으로의 인력 계산
    F_goal = k_att * (goal - pos) / max(|goal - pos|, ε)
    거리에 무관한 단위 벡터 방향 → 발진 없는 안정적 수렴
    """
    diff = goal - pos
    dist = np.linalg.norm(diff)
    if dist < 0.1:
        return np.zeros(3)
    # 연속 인력: 근거리 이차 → 원거리 단위 벡터로 매끄러운 전환
    # 전환점 d_t=10m에서 양쪽 함수값이 일치: k_att * diff = k_att * diff/dist * dist
    d_t = 10.0
    if dist <= d_t:
        return k_att * diff                 # 이차 인력 (근거리)
    else:
        return k_att * diff / dist * d_t    # 연속 단위 벡터 (크기 보존)


def repulsive_force_drone(
    own_pos: np.ndarray,
    other_pos: np.ndarray,
    own_vel: np.ndarray,
    other_vel: np.ndarray,
    k_rep: float = APF_PARAMS["k_rep_drone"],
    d0: float = APF_PARAMS["d0_drone"],
) -> np.ndarray:
    """
    다른 드론으로부터의 척력 계산 (속도 고려 velocity-obstacle 보정)
    F_rep = k_rep * (1/dist - 1/d0) * (1/dist²) * (pos - other_pos)/dist
    """
    diff = own_pos - other_pos
    dist = np.linalg.norm(diff)

    if dist < 1e-3 or dist >= d0:
        return np.zeros(3)

    n = diff / dist  # 단위 법선 벡터

    # 기본 척력
    mag = k_rep * (1.0 / dist - 1.0 / d0) / (dist ** 2)

    # 속도 기반 보정: 접근 중이면 척력 증폭 (closing speed 기반)
    relative_vel = own_vel - other_vel
    closing_speed = -np.dot(relative_vel, n)  # 양수 = 접근 중
    if closing_speed > 0:
        # 접근 속도에 비례하여 최대 3× 증폭 (기존 2× → 3×)
        amplification = min(1.0 + closing_speed / 4.0, 3.0)
        mag *= amplification

    return mag * n


def repulsive_force_obstacle(
    pos: np.ndarray,
    obs_pos: np.ndarray,
    k_rep: float = APF_PARAMS["k_rep_obs"],
    d0: float = APF_PARAMS["d0_obs"],
) -> np.ndarray:
    """고정 장애물 (건물, NFZ 경계) 척력"""
    diff = pos - obs_pos
    dist = np.linalg.norm(diff)

    if dist < 1e-3 or dist >= d0:
        return np.zeros(3)

    n = diff / dist
    mag = k_rep * (1.0 / dist - 1.0 / d0) / (dist ** 2)
    return mag * n


def compute_total_force(
    own: APFState,
    goal: np.ndarray,
    neighbors: list[APFState],
    obstacles: list[np.ndarray],
    params: dict | None = None,
    wind_speed: float = 0.0,
    target_alt: float | None = None,
) -> np.ndarray:
    """
    드론 1기의 합력 계산 (분산 제어 - 이웃 정보만 사용)

    Args:
        own:       자신의 상태
        goal:      목표 위치 [x, y, z]
        neighbors: 통신 범위 내 이웃 드론 상태 리스트
        obstacles: 장애물 위치 리스트
        params:    APF 파라미터 딕셔너리 (None이면 바람 조건에 따라 자동 선택)
        wind_speed: 현재 바람 속도 (m/s) - 파라미터 자동 선택에 사용

    Returns:
        합력 벡터 [fx, fy, fz] (m/s²)
    """
    # 바람 조건에 따라 파라미터 점진적 블렌딩 (hard switch → smooth interpolation)
    if params is None:
        if wind_speed > 12.0:
            params = APF_PARAMS_WINDY
        elif wind_speed > 6.0:
            # 6~12 m/s 구간: 선형 보간으로 점진 전환
            t = (wind_speed - 6.0) / 6.0  # 0.0 ~ 1.0
            params = {
                k: APF_PARAMS[k] * (1 - t) + APF_PARAMS_WINDY[k] * t
                for k in APF_PARAMS
            }
        else:
            params = APF_PARAMS

    F_total = np.zeros(3)

    # 1. 인력 (목표 방향)
    F_total += attractive_force(own.position, goal, params["k_att"])

    # 2. 드론 간 척력
    for neighbor in neighbors:
        F_total += repulsive_force_drone(
            own.position, neighbor.position,
            own.velocity, neighbor.velocity,
            params["k_rep_drone"], params["d0_drone"]
        )

    # 3. 장애물 척력
    for obs in obstacles:
        F_total += repulsive_force_obstacle(
            own.position, obs,
            params["k_rep_obs"], params["d0_obs"]
        )

    # 4. 고도 보정 (비행 고도 유지)
    _target_alt = target_alt if target_alt is not None else params["target_alt"]
    alt_error = _target_alt - own.position[2]
    F_total[2] += params["altitude_k"] * alt_error

    # 4a. 지면 회피: z < 5m 시 강한 수직 반발력 (CFIT 방지)
    ground_clearance = own.position[2]
    if ground_clearance < 5.0:
        ground_repulsion = params["k_rep_obs"] * (1.0 / max(ground_clearance, 0.1) - 1.0 / 5.0)
        F_total[2] += ground_repulsion

    # 5. 교착 감지 및 탈출 (local minima escape)
    # 합력이 거의 0이지만 목표에 도달하지 않은 경우 → 횡방향 섭동
    mag = np.linalg.norm(F_total)
    goal_dist = np.linalg.norm(goal - own.position)
    if mag < 0.5 and goal_dist > 20.0:
        # 목표 방향과 수직인 벡터로 횡방향 탈출
        goal_dir = (goal - own.position) / max(goal_dist, 1e-3)
        perp = np.array([-goal_dir[1], goal_dir[0], 0.0])
        perp_mag = np.linalg.norm(perp)
        if perp_mag > 1e-3:
            perp /= perp_mag
        else:
            perp = np.array([1.0, 0.0, 0.0])
        # 드론 ID 해시 기반 방향 결정 (일관된 탈출 방향)
        sign = 1.0 if hash(own.drone_id) % 2 == 0 else -1.0
        F_total += sign * perp * params["k_att"] * 2.0

    # 6. 최대 합력 클리핑
    mag = np.linalg.norm(F_total)
    if mag > params["max_force"]:
        F_total = F_total / mag * params["max_force"]

    return F_total


def force_to_velocity(
    current_vel: np.ndarray,
    force: np.ndarray,
    dt: float,
    max_speed: float = 15.0,
) -> np.ndarray:
    """합력 → 새 속도 (오일러 적분)"""
    new_vel = current_vel + force * dt
    speed = np.linalg.norm(new_vel)
    if speed > max_speed:
        new_vel = new_vel / speed * max_speed
    return new_vel


def batch_compute_forces(
    states: list[APFState],
    goals: dict[str, np.ndarray],
    obstacles: list[np.ndarray],
    comm_range: float = 2000.0,
    params: dict | None = None,
    wind_speeds: dict[str, float] | None = None,
    neighbor_states: list[APFState] | None = None,
) -> dict[str, np.ndarray]:
    """
    전체 드론에 대한 APF 합력 배치 계산 (NumPy 벡터화)

    Args:
        wind_speeds:     {drone_id: wind_speed} 딕셔너리 (각 드론 위치의 바람 속도)
        neighbor_states: 이웃 탐색 풀 (None이면 states 자체를 사용).
                         EVADING 드론만 states에 전달할 때 전체 활성 드론을 이웃 풀로
                         지정하여 비-EVADING 드론도 장애물로 인식하게 한다.

    Returns:
        {drone_id: force_vector} 딕셔너리
    """
    forces = {}

    if wind_speeds is None:
        wind_speeds = {}

    # 이웃 탐색 풀: 별도 지정 시 해당 풀, 없으면 states 자체
    pool = neighbor_states if neighbor_states is not None else states
    pool_positions = np.array([s.position for s in pool])    # (M, 3)
    pool_velocities = np.array([s.velocity for s in pool])   # (M, 3)

    for own in states:
        goal = goals.get(own.drone_id)
        if goal is None:
            forces[own.drone_id] = np.zeros(3)
            continue

        # 통신 범위 내 이웃 탐색 (자기 자신 제외)
        diffs = pool_positions - own.position            # (M, 3)
        dists = np.linalg.norm(diffs, axis=1)            # (M,)
        neighbor_indices = [j for j in np.where((dists < comm_range) & (dists > 0))[0]
                            if pool[j].drone_id != own.drone_id]

        neighbors = [
            APFState(pool_positions[j], pool_velocities[j], pool[j].drone_id)
            for j in neighbor_indices
        ]

        # 바람 속도 가져오기
        wind_speed = wind_speeds.get(own.drone_id, 0.0)

        forces[own.drone_id] = compute_total_force(
            own, goal, neighbors, obstacles, params, wind_speed
        )

    return forces
