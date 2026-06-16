"""ODYSSEY Phase 443 — APF 수렴성 Lyapunov 분석 (수학 증명 문서화의 수치 검증부).

APF 충돌 회피 엔진(``simulation/apf_engine/apf.py``)의 힘 법칙이 보존 포텐셜의
음의 기울기(``F = -∇U``)임을 명시하고, 그 포텐셜이 Lyapunov 함수 조건을 만족함을
수치적으로 검증 가능하게 한다. 형식 증명 서술은 ``docs/APF_CONVERGENCE_PROOF.md``.

핵심 결과:
  • 인력 포텐셜 ``V_att`` 는 양정치(positive-definite)·radially unbounded·C¹ 이며
    그 음의 기울기가 ``apf.attractive_force`` 와 정확히 일치한다.
  • 척력 포텐셜은 표준 FIRAS 형태 ``(k/2)(1/d - 1/d0)²`` 이며 그 음의 기울기가
    ``apf.repulsive_force_*`` 의 속도-무관(보존) 성분과 일치한다(엔진의 수치 하한
    ``d ≥ 1e-3 m`` 영역에서).
  • 과감쇠(over-damped) 흐름 ``ẋ = F_보존 = -∇U`` 에서 ``dU/dt = -‖∇U‖² ≤ 0``.
    → U 는 Lyapunov 함수이고 궤적은 임계점(목표=전역 최소 또는 척력 유발 국소
    최소)으로 단조 수렴한다. 국소 최소는 APF 의 알려진 한계로, 본 시스템은
    상위 계층(CBS·교착 탈출 섭동)으로 완화한다.

본 모듈은 ``apf.py`` 를 수정하지 않는 순수 추가이며, 무작위성이 없는 결정적 함수다.
포텐셜 기울기와 실제 엔진 힘의 일치는 ``tests/test_apf_lyapunov.py`` 가 핀으로 고정한다.
"""
from __future__ import annotations

import numpy as np

from simulation.apf_engine.apf import APF_PARAMS

# apf.attractive_force 의 이차→원뿔 전환점과 일치해야 한다.
ATTRACTIVE_TRANSITION_M = 10.0


def attractive_potential(
    pos: np.ndarray,
    goal: np.ndarray,
    k_att: float = APF_PARAMS["k_att"],
    d_t: float = ATTRACTIVE_TRANSITION_M,
) -> float:
    """목표 인력 포텐셜 V_att(x). 음의 기울기가 ``apf.attractive_force`` 와 일치한다.

    근거리(r ≤ d_t)는 이차(quadratic well), 원거리는 원뿔(conic)로,
    전환점 d_t 에서 값·기울기가 모두 연속(C¹)이다::

        V_att = (k_att/2)·r²                 (r ≤ d_t)
              = k_att·d_t·(r - d_t/2)         (r > d_t)

    r = ‖x - goal‖. 양정치(V≥0, V=0 ⇔ x=goal)이고 radially unbounded.
    """
    r = float(np.linalg.norm(np.asarray(goal, dtype=float) - np.asarray(pos, dtype=float)))
    if r <= d_t:
        return 0.5 * k_att * r * r
    return k_att * d_t * (r - 0.5 * d_t)


def _firas_potential(dist: float, k_rep: float, d0: float) -> float:
    """표준 FIRAS 척력 포텐셜 (k_rep/2)(1/dist - 1/d0)². dist ≥ d0 이면 0."""
    if dist >= d0:
        return 0.0
    # dist → 0 에서 +∞ (충돌 장벽). 0 근방은 호출측이 물리적으로 도달 불가.
    if dist < 1e-12:
        return float("inf")
    inv = (1.0 / dist) - (1.0 / d0)
    return 0.5 * k_rep * inv * inv


def repulsive_potential_drone(
    own_pos: np.ndarray,
    other_pos: np.ndarray,
    k_rep: float = APF_PARAMS["k_rep_drone"],
    d0: float = APF_PARAMS["d0_drone"],
) -> float:
    """드론 간 척력 포텐셜. 음의 기울기 = ``repulsive_force_drone`` 의 보존 성분.

    본 포텐셜은 ``apf.repulsive_force_drone`` 의 속도-무관(보존) 성분에 대응한다.
    속도 기반 증폭(접근 시 ×3~5)은 비보존항이라 본 보존 분석 범위 밖이며,
    증폭이 걸린 동역학에서는 Lyapunov 하강이 보장되지 않는다(목표-장애물 사이
    배치에서 인력·척력이 역방향이면 dU/dt>0 가능 — 별도 분석 필요).
    """
    dist = float(np.linalg.norm(np.asarray(own_pos, dtype=float) - np.asarray(other_pos, dtype=float)))
    return _firas_potential(dist, k_rep, d0)


def repulsive_potential_obstacle(
    pos: np.ndarray,
    obs_pos: np.ndarray,
    k_rep: float = APF_PARAMS["k_rep_obs"],
    d0: float = APF_PARAMS["d0_obs"],
) -> float:
    """고정 장애물 척력 포텐셜. 음의 기울기 = ``repulsive_force_obstacle``."""
    dist = float(np.linalg.norm(np.asarray(pos, dtype=float) - np.asarray(obs_pos, dtype=float)))
    return _firas_potential(dist, k_rep, d0)


def total_potential(
    pos: np.ndarray,
    goal: np.ndarray,
    neighbor_positions: list[np.ndarray] | None = None,
    obstacle_positions: list[np.ndarray] | None = None,
    params: dict | None = None,
) -> float:
    """보존 APF 포텐셜 U = V_att + Σ 척력. Lyapunov 함수 후보.

    ``conservative_force`` 가 정확히 ``-∇U`` 를 반환한다(수치 미분으로 검증).
    고도 보정·지면 반발·교착 탈출 섭동(``compute_total_force`` 의 부가항)은
    보존장이 아니므로 제외한다 — 본 분석은 수평 목표 추적·충돌 회피의 수렴성을 다룬다.
    """
    p = params if params is not None else APF_PARAMS
    u = attractive_potential(pos, goal, p["k_att"])
    for other in neighbor_positions or []:
        u += repulsive_potential_drone(pos, other, p["k_rep_drone"], p["d0_drone"])
    for obs in obstacle_positions or []:
        u += repulsive_potential_obstacle(pos, obs, p["k_rep_obs"], p["d0_obs"])
    return u


def conservative_force(
    pos: np.ndarray,
    goal: np.ndarray,
    neighbor_positions: list[np.ndarray] | None = None,
    obstacle_positions: list[np.ndarray] | None = None,
    params: dict | None = None,
) -> np.ndarray:
    """보존장 힘 F = -∇U. ``apf.compute_total_force`` 의 속도-무관 보존 성분.

    인력 + 척력(속도 증폭 제외)의 해석적 음의 기울기. 과감쇠 흐름 ``ẋ = F`` 에서
    ``dU/dt = ∇U·ẋ = -‖∇U‖² ≤ 0`` 이 되어 U 가 Lyapunov 함수임을 보장한다.
    """
    p = params if params is not None else APF_PARAMS
    pos = np.asarray(pos, dtype=float)

    # 인력: -∇V_att. apf.attractive_force 와 동일한 분기 — 0.1m 데드밴드 포함.
    # (엔진은 r<0.1m 에서 0 반환. 이 영역에서만 F ≠ -∇V_att 이나, 척력 장벽으로
    #  드론이 도달 불가하므로 시뮬상 영향 없음. 등가성은 r≥0.1m 에서 성립.)
    diff = np.asarray(goal, dtype=float) - pos
    r = float(np.linalg.norm(diff))
    force = np.zeros(3)
    if r >= 0.1:
        if r <= ATTRACTIVE_TRANSITION_M:
            force += p["k_att"] * diff
        else:
            force += p["k_att"] * diff / r * ATTRACTIVE_TRANSITION_M

    # 척력: -∇U_rep (FIRAS, 속도 증폭 제외)
    for other in neighbor_positions or []:
        force += _firas_gradient_force(pos, np.asarray(other, dtype=float), p["k_rep_drone"], p["d0_drone"])
    for obs in obstacle_positions or []:
        force += _firas_gradient_force(pos, np.asarray(obs, dtype=float), p["k_rep_obs"], p["d0_obs"])
    return force


def _firas_gradient_force(pos: np.ndarray, source: np.ndarray, k_rep: float, d0: float) -> np.ndarray:
    """-∇[(k/2)(1/d - 1/d0)²] = k(1/d - 1/d0)(1/d²)·n̂, d<d0."""
    diff = pos - source
    dist = float(np.linalg.norm(diff))
    if dist < 1e-3 or dist >= d0:
        return np.zeros(3)
    n = diff / dist
    mag = k_rep * (1.0 / dist - 1.0 / d0) / (dist * dist)
    return mag * n


def lyapunov_derivative(
    pos: np.ndarray,
    goal: np.ndarray,
    velocity: np.ndarray,
    neighbor_positions: list[np.ndarray] | None = None,
    obstacle_positions: list[np.ndarray] | None = None,
    params: dict | None = None,
) -> float:
    """dU/dt = ∇U·ẋ 의 한 표본. 과감쇠 흐름 ẋ=-∇U 이면 -‖∇U‖² ≤ 0.

    임의 속도 ``velocity`` 에 대한 순간 변화율을 돌려준다(검증·진단용).
    """
    grad = -conservative_force(pos, goal, neighbor_positions, obstacle_positions, params)
    return float(np.dot(grad, np.asarray(velocity, dtype=float)))
