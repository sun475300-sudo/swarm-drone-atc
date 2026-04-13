"""
APF GPU 가속 엔진 — PyTorch 텐서 기반 벡터화 연산

전체 드론 쌍 거리·힘 계산을 행렬 연산으로 일괄 처리.
CUDA GPU 사용 가능 시 자동 활용, 없으면 CPU 텐서로 폴백.

batch_compute_forces 대체: O(N) Python 루프 → O(1) 텐서 연산
"""

from __future__ import annotations

import numpy as np

try:
    import torch

    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False

from .apf import (
    APF_PARAMS,
    APF_PARAMS_HIGH_DENSITY,
    APF_PARAMS_WINDY,
    APFState,
)


def _select_device() -> "torch.device":
    """CUDA > CPU 자동 선택."""
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def _get_device_info() -> dict:
    """현재 디바이스 정보 반환."""
    if not _TORCH_AVAILABLE:
        return {"backend": "numpy", "device": "cpu", "gpu": None}
    device = _select_device()
    info = {"backend": "torch", "device": str(device), "gpu": None}
    if device.type == "cuda":
        info["gpu"] = torch.cuda.get_device_name(0)
        info["vram_gb"] = round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1)
    return info


def gpu_batch_compute_forces(
    states: list[APFState],
    goals: dict[str, np.ndarray],
    obstacles: list[np.ndarray],
    comm_range: float = 2000.0,
    params: dict | None = None,
    wind_speeds: dict[str, float] | None = None,
    neighbor_states: list[APFState] | None = None,
) -> dict[str, np.ndarray]:
    """
    PyTorch 텐서 기반 APF 배치 연산.

    batch_compute_forces와 동일한 API, 동일한 반환값.
    전체 드론 쌍 거리 행렬을 한 번의 텐서 연산으로 계산.
    """
    if not _TORCH_AVAILABLE or len(states) == 0:
        return {}

    device = _select_device()
    dtype = torch.float32
    n = len(states)

    if wind_speeds is None:
        wind_speeds = {}

    # --- 입력 텐서 구성 ---
    pool = neighbor_states if neighbor_states is not None else states
    m = len(pool)

    ids = [s.drone_id for s in states]
    positions = torch.as_tensor(np.array([s.position for s in states]), dtype=dtype, device=device)   # (N, 3)
    velocities = torch.as_tensor(np.array([s.velocity for s in states]), dtype=dtype, device=device)  # (N, 3)
    pool_pos = torch.as_tensor(np.array([s.position for s in pool]), dtype=dtype, device=device)      # (M, 3)
    pool_vel = torch.as_tensor(np.array([s.velocity for s in pool]), dtype=dtype, device=device)      # (M, 3)
    pool_ids = [s.drone_id for s in pool]

    goal_tensors = torch.zeros((n, 3), dtype=dtype, device=device)
    has_goal = torch.zeros(n, dtype=torch.bool, device=device)
    for i, sid in enumerate(ids):
        g = goals.get(sid)
        if g is not None:
            goal_tensors[i] = torch.tensor(g, dtype=dtype, device=device)
            has_goal[i] = True

    # 장애물 텐서
    if obstacles:
        obs_tensor = torch.tensor(np.array(obstacles), dtype=dtype, device=device)  # (K, 3)
    else:
        obs_tensor = torch.zeros((0, 3), dtype=dtype, device=device)

    # 바람 속도 텐서
    wind_tensor = torch.zeros(n, dtype=dtype, device=device)
    for i, sid in enumerate(ids):
        wind_tensor[i] = wind_speeds.get(sid, 0.0)

    # --- 파라미터 선택 (드론별) ---
    # 이웃 수 기반 고밀도 감지: 80m 이내 이웃 카운트
    # (N, M) 거리 행렬
    diff_nm = positions.unsqueeze(1) - pool_pos.unsqueeze(0)  # (N, M, 3)
    dist_nm = torch.linalg.norm(diff_nm, dim=2)               # (N, M)

    # 자기 자신 마스킹
    self_mask = torch.zeros((n, m), dtype=torch.bool, device=device)
    for i, sid in enumerate(ids):
        for j, pid in enumerate(pool_ids):
            if sid == pid:
                self_mask[i, j] = True

    dist_nm_masked = dist_nm.clone()
    dist_nm_masked[self_mask] = float('inf')

    neighbor_count_80 = ((dist_nm_masked < 80.0) & (~self_mask)).sum(dim=1)  # (N,)

    # 파라미터 텐서 (드론별 선택)
    p_keys = ["k_att", "k_rep_drone", "k_rep_obs", "d0_drone", "d0_obs", "max_force", "altitude_k"]
    p_normal = torch.tensor([APF_PARAMS[k] for k in p_keys], dtype=dtype, device=device)
    p_windy = torch.tensor([APF_PARAMS_WINDY[k] for k in p_keys], dtype=dtype, device=device)
    p_hd = torch.tensor([APF_PARAMS_HIGH_DENSITY[k] for k in p_keys], dtype=dtype, device=device)

    # (N, 7) 파라미터 행렬
    if params is not None:
        param_vec = torch.tensor([params[k] for k in p_keys], dtype=dtype, device=device)
        params_all = param_vec.unsqueeze(0).expand(n, -1)
    else:
        is_hd = neighbor_count_80 >= 3                     # (N,)
        is_windy = wind_tensor > 12.0                      # (N,)
        is_blend = (wind_tensor > 6.0) & (~is_windy)       # (N,)

        t = ((wind_tensor - 6.0) / 6.0).clamp(0, 1)       # (N,)

        params_all = p_normal.unsqueeze(0).expand(n, -1).clone()

        # 블렌딩 구간
        blend_mask = is_blend.unsqueeze(1).expand(-1, len(p_keys))
        blended = p_normal.unsqueeze(0) * (1 - t.unsqueeze(1)) + p_windy.unsqueeze(0) * t.unsqueeze(1)
        params_all = torch.where(blend_mask, blended, params_all)

        # 강풍
        windy_mask = is_windy.unsqueeze(1).expand(-1, len(p_keys))
        params_all = torch.where(windy_mask, p_windy.unsqueeze(0).expand(n, -1), params_all)

        # 고밀도 (최우선)
        hd_mask = is_hd.unsqueeze(1).expand(-1, len(p_keys))
        params_all = torch.where(hd_mask, p_hd.unsqueeze(0).expand(n, -1), params_all)

    # 파라미터 분리
    k_att = params_all[:, 0]          # (N,)
    k_rep_drone = params_all[:, 1]    # (N,)
    k_rep_obs = params_all[:, 2]      # (N,)
    d0_drone = params_all[:, 3]       # (N,)
    d0_obs = params_all[:, 4]         # (N,)
    max_force = params_all[:, 5]      # (N,)
    altitude_k = params_all[:, 6]     # (N,)

    F_total = torch.zeros((n, 3), dtype=dtype, device=device)

    # === 1. 인력 (목표 방향) ===
    goal_diff = goal_tensors - positions                     # (N, 3)
    goal_dist = torch.linalg.norm(goal_diff, dim=1, keepdim=True).clamp(min=1e-6)  # (N, 1)

    d_t = 10.0
    near_goal = (goal_dist.squeeze() <= d_t) & (goal_dist.squeeze() >= 0.1)
    far_goal = goal_dist.squeeze() > d_t

    F_att = torch.zeros_like(F_total)
    F_att[near_goal] = k_att[near_goal].unsqueeze(1) * goal_diff[near_goal]
    F_att[far_goal] = k_att[far_goal].unsqueeze(1) * goal_diff[far_goal] / goal_dist[far_goal] * d_t

    too_close = goal_dist.squeeze() < 0.1
    F_att[too_close] = 0.0
    F_att[~has_goal] = 0.0

    F_total += F_att

    # === 2. 드론 간 척력 (벡터화) ===
    # diff_nm: (N, M, 3), dist_nm_masked: (N, M)
    in_range = (dist_nm_masked < d0_drone.unsqueeze(1)) & (dist_nm_masked > 1e-3)  # (N, M)

    if in_range.any():
        # 단위 법선 벡터
        n_hat = diff_nm / dist_nm_masked.unsqueeze(2).clamp(min=1e-6)  # (N, M, 3)

        # 척력 크기: k_rep * (1/dist - 1/d0) / dist²
        inv_dist = 1.0 / dist_nm_masked.clamp(min=1e-6)
        inv_d0 = 1.0 / d0_drone.unsqueeze(1)
        mag = k_rep_drone.unsqueeze(1) * (inv_dist - inv_d0) * inv_dist ** 2  # (N, M)

        # 속도 기반 증폭
        rel_vel = velocities.unsqueeze(1) - pool_vel.unsqueeze(0)  # (N, M, 3)
        closing_speed = -(rel_vel * n_hat).sum(dim=2)               # (N, M)
        closing_speed = closing_speed.clamp(min=0.0)

        max_amp = torch.where(d0_drone > 100, torch.tensor(5.0, device=device), torch.tensor(3.0, device=device))
        amplification = (1.0 + closing_speed / 3.0).clamp(max=max_amp.unsqueeze(1))
        mag = mag * amplification

        # 범위 밖 마스킹
        mag = mag * in_range.float()

        F_rep_drone = (mag.unsqueeze(2) * n_hat).sum(dim=1)  # (N, 3)
        F_total += F_rep_drone

    # === 3. 장애물 척력 (벡터화) ===
    if obs_tensor.shape[0] > 0:
        obs_diff = positions.unsqueeze(1) - obs_tensor.unsqueeze(0)  # (N, K, 3)
        obs_dist = torch.linalg.norm(obs_diff, dim=2)                # (N, K)

        obs_in_range = (obs_dist < d0_obs.unsqueeze(1)) & (obs_dist > 1e-3)

        if obs_in_range.any():
            obs_n = obs_diff / obs_dist.unsqueeze(2).clamp(min=1e-6)
            obs_inv_d = 1.0 / obs_dist.clamp(min=1e-6)
            obs_inv_d0 = 1.0 / d0_obs.unsqueeze(1)
            obs_mag = k_rep_obs.unsqueeze(1) * (obs_inv_d - obs_inv_d0) * obs_inv_d ** 2
            obs_mag = obs_mag * obs_in_range.float()

            F_rep_obs = (obs_mag.unsqueeze(2) * obs_n).sum(dim=1)
            F_total += F_rep_obs

    # === 4. 고도 보정 ===
    target_alt = 60.0
    alt_error = target_alt - positions[:, 2]
    F_total[:, 2] += altitude_k * alt_error

    # 4a. 지면 회피
    ground_clearance = positions[:, 2]
    ground_danger = ground_clearance < 5.0
    if ground_danger.any():
        gc = ground_clearance[ground_danger].clamp(min=0.1)
        ground_rep = k_rep_obs[ground_danger] * (1.0 / gc - 1.0 / 5.0)
        F_total[ground_danger, 2] += ground_rep

    # === 5. 교착 탈출 ===
    f_mag = torch.linalg.norm(F_total, dim=1)
    g_dist = torch.linalg.norm(goal_diff, dim=1)
    stuck = (f_mag < 0.5) & (g_dist > 20.0) & has_goal

    if stuck.any():
        goal_dir = goal_diff[stuck] / g_dist[stuck].unsqueeze(1).clamp(min=1e-3)
        perp = torch.zeros_like(goal_dir)
        perp[:, 0] = -goal_dir[:, 1]
        perp[:, 1] = goal_dir[:, 0]
        perp_mag = torch.linalg.norm(perp, dim=1, keepdim=True).clamp(min=1e-3)
        perp = perp / perp_mag

        # 드론 ID 해시 기반 방향
        signs = torch.tensor(
            [1.0 if hash(ids[i]) % 2 == 0 else -1.0 for i in range(n) if stuck[i]],
            dtype=dtype, device=device
        )
        F_total[stuck] += signs.unsqueeze(1) * perp * k_att[stuck].unsqueeze(1) * 2.0

    # === 6. 최대 합력 클리핑 ===
    f_mag = torch.linalg.norm(F_total, dim=1, keepdim=True)
    clip_mask = f_mag.squeeze() > max_force
    if clip_mask.any():
        F_total[clip_mask] = F_total[clip_mask] / f_mag[clip_mask] * max_force[clip_mask].unsqueeze(1)

    # 목표 없는 드론 → 제로 벡터
    F_total[~has_goal] = 0.0

    # --- numpy 변환 반환 ---
    forces_np = F_total.cpu().numpy()
    return {ids[i]: forces_np[i] for i in range(n)}
