"""
GPU 물리 엔진 — 전체 드론 상태를 GPU에 상주시키고 모든 연산을 텐서로 수행

RTX 5070 Ti 16GB 최적화:
  - TF32 행렬 연산 (Ampere+)
  - Mixed Precision (FP16 연산, FP32 누적)
  - Persistent CUDA Streams (비동기 CPU↔GPU 전송)
  - Pre-allocated 텐서 (max_drones 크기, 런타임 재할당 없음)

사용법:
    engine = GPUPhysicsEngine(max_drones=500)
    engine.sync_from_cpu(drones)
    forces = engine.compute_all_forces(wind, nfz_obstacles)
    collisions = engine.detect_collisions()
    engine.update_positions(dt, wind, bounds, alt_range)
    engine.update_batteries(dt, profiles_data)
    engine.sync_to_cpu(drones)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# PyTorch / CUDA 가용성 검사
# ─────────────────────────────────────────────────────────────

try:
    import torch

    _TORCH_AVAILABLE = True

    if torch.cuda.is_available():
        torch.backends.cudnn.benchmark = True
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True

except (ImportError, OSError):
    _TORCH_AVAILABLE = False

from .apf import (
    APF_PARAMS,
    APF_PARAMS_HIGH_DENSITY,
    APF_PARAMS_WINDY,
)

# ─────────────────────────────────────────────────────────────
# FlightPhase 정수 매핑 (GPU 텐서용)
# ─────────────────────────────────────────────────────────────

PHASE_GROUNDED = 0
PHASE_TAKEOFF = 1
PHASE_ENROUTE = 2
PHASE_HOLDING = 3
PHASE_LANDING = 4
PHASE_FAILED = 5
PHASE_RTL = 6
PHASE_EVADING = 7

_PHASE_NAME_TO_INT: dict[str, int] = {
    "GROUNDED": PHASE_GROUNDED,
    "TAKEOFF": PHASE_TAKEOFF,
    "ENROUTE": PHASE_ENROUTE,
    "HOLDING": PHASE_HOLDING,
    "LANDING": PHASE_LANDING,
    "FAILED": PHASE_FAILED,
    "RTL": PHASE_RTL,
    "EVADING": PHASE_EVADING,
}

# 활성 비행 단계 마스크 (GROUNDED, FAILED 제외)
_ACTIVE_PHASES = frozenset({
    PHASE_TAKEOFF, PHASE_ENROUTE, PHASE_HOLDING,
    PHASE_LANDING, PHASE_RTL, PHASE_EVADING,
})


# ─────────────────────────────────────────────────────────────
# GPU 타이밍 유틸리티
# ─────────────────────────────────────────────────────────────

@dataclass
class GPUTimings:
    """GPU 연산별 소요 시간 (ms)."""

    sync_upload_ms: float = 0.0
    forces_ms: float = 0.0
    collision_ms: float = 0.0
    position_ms: float = 0.0
    battery_ms: float = 0.0
    sync_download_ms: float = 0.0


def _select_device() -> "torch.device":
    """VRAM 최대 GPU 자동 선택. GPU 없으면 CPU."""
    if not torch.cuda.is_available():
        return torch.device("cpu")
    n = torch.cuda.device_count()
    if n == 1:
        return torch.device("cuda:0")
    best = max(range(n), key=lambda i: torch.cuda.get_device_properties(i).total_memory)
    return torch.device(f"cuda:{best}")


# ─────────────────────────────────────────────────────────────
# 메인 엔진
# ─────────────────────────────────────────────────────────────


class GPUPhysicsEngine:
    """전체 드론 물리를 GPU 텐서로 처리하는 통합 엔진.

    모든 드론 상태(위치, 속도, 목표, 배터리, 비행 단계)를 GPU 메모리에
    상주시키고, tick마다 CPU↔GPU 동기화는 최소화한다.

    Parameters
    ----------
    max_drones : int
        사전 할당 텐서 크기. 실제 드론 수가 이보다 작으면 슬라이싱 사용.
    device : torch.device | None
        명시적 디바이스. None이면 최적 GPU 자동 선택.
    """

    def __init__(self, max_drones: int = 500, device: Any = None) -> None:
        """인스턴스를 초기화한다."""
        if not _TORCH_AVAILABLE:
            raise RuntimeError(
                "GPUPhysicsEngine requires PyTorch with CUDA. "
                "Install: pip install torch --index-url https://download.pytorch.org/whl/cu124"
            )

        self.device: torch.device = device if device is not None else _select_device()
        self.max_drones = max_drones
        self._n: int = 0  # 현재 활성 드론 수
        self._drone_ids: list[str] = []  # GPU 텐서 인덱스 ↔ drone_id 매핑
        self._id_to_idx: dict[str, int] = {}

        # APF 파라미터 키 순서 (일관성 보장)
        self._param_keys = [
            "k_att", "k_rep_drone", "k_rep_obs",
            "d0_drone", "d0_obs", "max_force", "altitude_k",
        ]

        # ── 사전 할당 GPU 텐서 ──
        fp = torch.float32
        self.positions = torch.zeros((max_drones, 3), dtype=fp, device=self.device)
        self.velocities = torch.zeros((max_drones, 3), dtype=fp, device=self.device)
        self.goals = torch.zeros((max_drones, 3), dtype=fp, device=self.device)
        self.has_goal = torch.zeros(max_drones, dtype=torch.bool, device=self.device)
        self.batteries = torch.zeros(max_drones, dtype=fp, device=self.device)
        self.phases = torch.zeros(max_drones, dtype=torch.int32, device=self.device)
        self.headings = torch.zeros(max_drones, dtype=fp, device=self.device)

        # 드론 프로파일 인덱스 (배터리 계산용)
        self.profile_indices = torch.zeros(max_drones, dtype=torch.int32, device=self.device)

        # 힘 출력 버퍼
        self.forces = torch.zeros((max_drones, 3), dtype=fp, device=self.device)

        # 활성 마스크 (GROUNDED, FAILED 제외)
        self.active_mask = torch.zeros(max_drones, dtype=torch.bool, device=self.device)

        # ── APF 파라미터 텐서 (상수, GPU 상주) ──
        self._p_normal = torch.tensor(
            [APF_PARAMS[k] for k in self._param_keys],
            dtype=fp, device=self.device,
        )
        self._p_windy = torch.tensor(
            [APF_PARAMS_WINDY[k] for k in self._param_keys],
            dtype=fp, device=self.device,
        )
        self._p_hd = torch.tensor(
            [APF_PARAMS_HIGH_DENSITY[k] for k in self._param_keys],
            dtype=fp, device=self.device,
        )

        # ── CUDA 스트림 ──
        self._use_cuda = self.device.type == "cuda"
        if self._use_cuda:
            self._stream_transfer = torch.cuda.Stream(device=self.device)
            self._stream_compute = torch.cuda.Stream(device=self.device)
        else:
            self._stream_transfer = None
            self._stream_compute = None

        # ── 타이밍 ──
        self._timings = GPUTimings()

        # ── 풍속 버퍼 ──
        self._wind_speeds = torch.zeros(max_drones, dtype=fp, device=self.device)

        # ── ID 해시 텐서 (교착 탈출 방향 결정용) ──
        self._id_hashes = torch.zeros(max_drones, dtype=torch.int64, device=self.device)

        logger.info(
            "GPUPhysicsEngine initialized: device=%s, max_drones=%d",
            self.device, max_drones,
        )

    # ─────────────────────────────────────────────────────────
    # 속성
    # ─────────────────────────────────────────────────────────

    @property
    def n(self) -> int:
        """현재 GPU에 로드된 드론 수."""
        return self._n

    @property
    def timings(self) -> GPUTimings:
        """최근 연산 타이밍."""
        return self._timings

    # ─────────────────────────────────────────────────────────
    # CPU → GPU 동기화
    # ─────────────────────────────────────────────────────────

    def sync_from_cpu(self, drones: dict[str, Any]) -> None:
        """CPU DroneState 딕셔너리를 GPU 텐서로 업로드.

        Parameters
        ----------
        drones : dict[str, DroneState]
            {drone_id: DroneState} 전체 드론 상태.
        """
        t_start = self._timer_start()

        drone_list = list(drones.values())
        n = len(drone_list)
        if n > self.max_drones:
            logger.warning(
                "Drone count %d exceeds max_drones %d. Truncating.",
                n, self.max_drones,
            )
            drone_list = drone_list[:self.max_drones]
            n = self.max_drones

        self._n = n
        self._drone_ids = [d.drone_id for d in drone_list]
        self._id_to_idx = {did: i for i, did in enumerate(self._drone_ids)}

        # CPU 측 NumPy 배열 구성 (한 번에 복사)
        pos_np = np.zeros((n, 3), dtype=np.float32)
        vel_np = np.zeros((n, 3), dtype=np.float32)
        goal_np = np.zeros((n, 3), dtype=np.float32)
        has_goal_np = np.zeros(n, dtype=np.bool_)
        bat_np = np.zeros(n, dtype=np.float32)
        phase_np = np.zeros(n, dtype=np.int32)
        heading_np = np.zeros(n, dtype=np.float32)
        hash_np = np.zeros(n, dtype=np.int64)

        for i, d in enumerate(drone_list):
            pos_np[i] = d.position
            vel_np[i] = d.velocity
            heading_np[i] = d.heading

            if d.goal is not None:
                goal_np[i] = d.goal
                has_goal_np[i] = True

            bat_np[i] = d.battery_pct

            phase_name = (
                d.flight_phase.name
                if hasattr(d.flight_phase, "name")
                else str(d.flight_phase)
            )
            phase_np[i] = _PHASE_NAME_TO_INT.get(phase_name, PHASE_GROUNDED)
            hash_np[i] = hash(d.drone_id)

        # GPU 업로드 (비동기 CUDA 스트림)
        ctx = (
            torch.cuda.stream(self._stream_transfer)
            if self._use_cuda
            else _nullcontext()
        )
        with ctx:
            self.positions[:n].copy_(
                torch.from_numpy(pos_np).to(self.device), non_blocking=True
            )
            self.velocities[:n].copy_(
                torch.from_numpy(vel_np).to(self.device), non_blocking=True
            )
            self.goals[:n].copy_(
                torch.from_numpy(goal_np).to(self.device), non_blocking=True
            )
            self.has_goal[:n].copy_(
                torch.from_numpy(has_goal_np).to(self.device), non_blocking=True
            )
            self.batteries[:n].copy_(
                torch.from_numpy(bat_np).to(self.device), non_blocking=True
            )
            self.phases[:n].copy_(
                torch.from_numpy(phase_np).to(self.device), non_blocking=True
            )
            self.headings[:n].copy_(
                torch.from_numpy(heading_np).to(self.device), non_blocking=True
            )
            self._id_hashes[:n].copy_(
                torch.from_numpy(hash_np).to(self.device), non_blocking=True
            )

        # 활성 마스크 갱신
        self._update_active_mask()

        # 전송 완료 동기화
        if self._use_cuda and self._stream_transfer is not None:
            self._stream_transfer.synchronize()

        self._timings.sync_upload_ms = self._timer_end(t_start)

    # ─────────────────────────────────────────────────────────
    # GPU → CPU 동기화
    # ─────────────────────────────────────────────────────────

    def sync_to_cpu(self, drones: dict[str, Any]) -> None:
        """GPU 텐서 결과를 CPU DroneState 객체에 반영.

        Parameters
        ----------
        drones : dict[str, DroneState]
            동일한 드론 딕셔너리. position, velocity, battery_pct,
            heading 필드가 GPU 결과로 갱신된다.
        """
        t_start = self._timer_start()
        n = self._n

        ctx = (
            torch.cuda.stream(self._stream_transfer)
            if self._use_cuda
            else _nullcontext()
        )
        with ctx:
            pos_cpu = self.positions[:n].cpu().numpy()
            vel_cpu = self.velocities[:n].cpu().numpy()
            bat_cpu = self.batteries[:n].cpu().numpy()
            heading_cpu = self.headings[:n].cpu().numpy()

        for i, drone_id in enumerate(self._drone_ids):
            d = drones.get(drone_id)
            if d is None:
                continue
            d.position = pos_cpu[i].astype(np.float64)
            d.velocity = vel_cpu[i].astype(np.float64)
            d.battery_pct = float(np.clip(bat_cpu[i], 0.0, 100.0))
            d.heading = float(heading_cpu[i])

        self._timings.sync_download_ms = self._timer_end(t_start)

    # ─────────────────────────────────────────────────────────
    # GPU APF 합력 계산 (전체 활성 드론)
    # ─────────────────────────────────────────────────────────

    def compute_all_forces(
        self,
        wind_speeds: dict[str, float] | None = None,
        nfz_obstacles: list[np.ndarray] | None = None,
        params: dict | None = None,
    ) -> dict[str, np.ndarray]:
        """모든 활성 드론에 대한 APF 합력을 GPU에서 계산.

        Parameters
        ----------
        wind_speeds : dict[str, float] | None
            {drone_id: wind_speed_ms} 바람 속도.
        nfz_obstacles : list[np.ndarray] | None
            NFZ/장애물 위치 리스트.
        params : dict | None
            APF 파라미터 오버라이드. None이면 바람/밀도 기반 자동 선택.

        Returns
        -------
        dict[str, np.ndarray]
            {drone_id: force_vector[3]} 힘 벡터 딕셔너리.
        """
        t_start = self._timer_start()
        n = self._n
        if n == 0:
            self._timings.forces_ms = 0.0
            return {}

        # 풍속 텐서 구성
        if wind_speeds:
            ws_np = np.array(
                [wind_speeds.get(did, 0.0) for did in self._drone_ids],
                dtype=np.float32,
            )
            self._wind_speeds[:n].copy_(
                torch.from_numpy(ws_np).to(self.device), non_blocking=True
            )
        else:
            self._wind_speeds[:n].zero_()

        # 장애물 텐서
        if nfz_obstacles and len(nfz_obstacles) > 0:
            obs_np = np.array(nfz_obstacles, dtype=np.float32)
            obs_tensor = torch.from_numpy(obs_np).to(self.device)
        else:
            obs_tensor = torch.zeros((0, 3), dtype=torch.float32, device=self.device)

        # Mixed Precision 컨텍스트
        use_amp = self._use_cuda
        amp_ctx = (
            torch.amp.autocast("cuda", dtype=torch.float16)
            if use_amp
            else _nullcontext()
        )

        pos = self.positions[:n]
        vel = self.velocities[:n]
        goals = self.goals[:n]
        has_goal = self.has_goal[:n]
        wind = self._wind_speeds[:n]
        active = self.active_mask[:n]
        id_hashes = self._id_hashes[:n]

        with amp_ctx:
            forces = self._compute_apf_forces(
                pos, vel, goals, has_goal, wind, active,
                obs_tensor, id_hashes, n, params,
            )

        # FP32 보장 및 저장
        self.forces[:n] = forces.float()

        # CPU 반환
        forces_np = self.forces[:n].cpu().numpy()
        result = {
            self._drone_ids[i]: forces_np[i].copy()
            for i in range(n)
        }

        self._timings.forces_ms = self._timer_end(t_start)
        return result

    # ─────────────────────────────────────────────────────────
    # GPU 충돌 감지 (쌍별 거리 행렬)
    # ─────────────────────────────────────────────────────────

    @dataclass
    class CollisionResult:
        """충돌 감지 결과."""

        collisions: list[tuple[str, str, float]]
        near_misses: list[tuple[str, str, float]]
        conflicts: list[tuple[str, str, float]]

    def detect_collisions(
        self,
        collision_dist: float = 5.0,
        near_miss_dist: float = 10.0,
        conflict_dist: float = 50.0,
    ) -> "GPUPhysicsEngine.CollisionResult":
        """GPU 쌍별 거리 행렬로 충돌/근접/충돌위험 감지.

        자기 자신과의 거리는 텐서 인덱스 마스킹으로 제외 (Python 루프 없음).

        Parameters
        ----------
        collision_dist : float
            충돌 판정 거리 (m).
        near_miss_dist : float
            근접 통과 판정 거리 (m).
        conflict_dist : float
            충돌 위험 판정 거리 (m).

        Returns
        -------
        CollisionResult
            세 수준의 이벤트 쌍 리스트.
        """
        t_start = self._timer_start()
        n = self._n

        if n < 2:
            self._timings.collision_ms = 0.0
            return GPUPhysicsEngine.CollisionResult([], [], [])

        pos = self.positions[:n]
        active = self.active_mask[:n]

        # 활성 드론만 추출
        active_indices = torch.where(active)[0]
        n_active = active_indices.shape[0]

        if n_active < 2:
            self._timings.collision_ms = 0.0
            return GPUPhysicsEngine.CollisionResult([], [], [])

        active_pos = pos[active_indices]  # (A, 3)

        # 쌍별 거리 행렬: (A, A)
        diff = active_pos.unsqueeze(1) - active_pos.unsqueeze(0)  # (A, A, 3)
        dist_matrix = torch.linalg.norm(diff, dim=2)  # (A, A)

        # 자기 자신 마스킹 (대각선 → inf) — Python 루프 없음
        diag_mask = torch.eye(n_active, dtype=torch.bool, device=self.device)
        dist_matrix = dist_matrix.masked_fill(diag_mask, float("inf"))

        # 상삼각만 (중복 쌍 제거)
        upper_mask = torch.triu(
            torch.ones(n_active, n_active, dtype=torch.bool, device=self.device),
            diagonal=1,
        )

        # 각 수준별 마스크
        collision_mask = (dist_matrix < collision_dist) & upper_mask
        near_miss_mask = (
            (dist_matrix >= collision_dist)
            & (dist_matrix < near_miss_dist)
            & upper_mask
        )
        conflict_mask = (
            (dist_matrix >= near_miss_dist)
            & (dist_matrix < conflict_dist)
            & upper_mask
        )

        # CPU로 가져와서 쌍 구성
        collisions = self._extract_pairs(
            collision_mask, dist_matrix, active_indices
        )
        near_misses = self._extract_pairs(
            near_miss_mask, dist_matrix, active_indices
        )
        conflicts = self._extract_pairs(
            conflict_mask, dist_matrix, active_indices
        )

        self._timings.collision_ms = self._timer_end(t_start)

        return GPUPhysicsEngine.CollisionResult(
            collisions=collisions,
            near_misses=near_misses,
            conflicts=conflicts,
        )

    # ─────────────────────────────────────────────────────────
    # GPU 위치/속도 적분
    # ─────────────────────────────────────────────────────────

    def update_positions(
        self,
        dt: float,
        wind_vector: np.ndarray | None = None,
        bounds: float = 5000.0,
        alt_range: tuple[float, float] = (0.0, 120.0),
        max_speed: float = 15.0,
    ) -> None:
        """GPU에서 오일러 적분으로 속도/위치 갱신.

        Parameters
        ----------
        dt : float
            시간 간격 (초).
        wind_vector : np.ndarray | None
            전역 풍속 벡터 [wx, wy, wz] (m/s).
        bounds : float
            XY 공역 경계 (±bounds).
        alt_range : tuple[float, float]
            고도 범위 [min_z, max_z] (m).
        max_speed : float
            최대 비행 속도 (m/s).
        """
        t_start = self._timer_start()
        n = self._n
        if n == 0:
            self._timings.position_ms = 0.0
            return

        pos = self.positions[:n]
        vel = self.velocities[:n]
        forces = self.forces[:n]
        active = self.active_mask[:n]
        headings = self.headings[:n]

        dt_t = torch.tensor(dt, dtype=torch.float32, device=self.device)

        # 바람 텐서
        if wind_vector is not None:
            wind_t = torch.tensor(
                wind_vector, dtype=torch.float32, device=self.device
            )
        else:
            wind_t = torch.zeros(3, dtype=torch.float32, device=self.device)

        # ── 속도 갱신: v_new = v + F * dt ──
        new_vel = vel + forces * dt_t

        # 바람 영향 적용 (활성 드론만)
        active_3d = active.unsqueeze(1).expand_as(new_vel)
        new_vel = torch.where(active_3d, new_vel + wind_t * dt_t * 0.1, new_vel)

        # 속도 클램핑
        speed = torch.linalg.norm(new_vel, dim=1, keepdim=True).clamp(min=1e-8)
        over_speed = speed.squeeze(1) > max_speed
        new_vel[over_speed] = (
            new_vel[over_speed] / speed[over_speed] * max_speed
        )

        # 비활성 드론 속도 유지 (변경 없음)
        vel_out = torch.where(active_3d, new_vel, vel)

        # ── 위치 갱신: p_new = p + v * dt ──
        new_pos = pos + vel_out * dt_t

        # 경계 클램핑
        new_pos[:, 0].clamp_(-bounds, bounds)
        new_pos[:, 1].clamp_(-bounds, bounds)
        new_pos[:, 2].clamp_(alt_range[0], alt_range[1])

        # 비활성 드론 위치 유지
        pos_out = torch.where(active_3d, new_pos, pos)

        # 방위각 갱신 (XY 평면 속도 방향)
        vx = vel_out[:, 0]
        vy = vel_out[:, 1]
        speed_xy = torch.sqrt(vx * vx + vy * vy)
        has_speed = (speed_xy > 0.5) & active
        new_heading = torch.atan2(vx, vy) * (180.0 / torch.pi)  # 북 기준 시계 방향
        new_heading = torch.where(new_heading < 0, new_heading + 360.0, new_heading)
        heading_out = torch.where(has_speed, new_heading, headings)

        # 결과 저장
        self.positions[:n] = pos_out
        self.velocities[:n] = vel_out
        self.headings[:n] = heading_out

        self._timings.position_ms = self._timer_end(t_start)

    # ─────────────────────────────────────────────────────────
    # GPU 배터리 감쇠
    # ─────────────────────────────────────────────────────────

    def update_batteries(
        self,
        dt: float,
        profiles_data: dict[str, dict[str, float]] | None = None,
    ) -> None:
        """GPU에서 배터리 잔량 일괄 갱신.

        간략 모델: P = P_hover + 0.5 * speed^2, battery -= P * dt / capacity

        Parameters
        ----------
        dt : float
            시간 간격 (초).
        profiles_data : dict | None
            {profile_name: {"battery_wh": float, "endurance_min": float}}
            None이면 기본 프로파일 사용.
        """
        t_start = self._timer_start()
        n = self._n
        if n == 0:
            self._timings.battery_ms = 0.0
            return

        active = self.active_mask[:n]
        vel = self.velocities[:n]
        bat = self.batteries[:n]

        # 속도 크기
        speed = torch.linalg.norm(vel, dim=1)  # (N,)

        # 기본 프로파일: 80Wh, 30분 체공
        default_battery_wh = 80.0
        default_endurance_s = 30.0 * 60.0

        # 호버 전력 (W) = capacity_J / endurance_s
        p_hover = default_battery_wh * 3600.0 / default_endurance_s

        # 드래그 전력 (W) = 0.5 * speed^2
        p_drag = 0.5 * speed * speed

        # 총 전력 (W)
        total_power = p_hover + p_drag

        # 에너지 소모 (J) = power * dt
        energy_j = total_power * dt

        # 배터리 감소량 (%) = energy_J / capacity_J * 100
        capacity_j = default_battery_wh * 3600.0
        drain_pct = energy_j / capacity_j * 100.0

        # 활성 드론만 감쇠
        new_bat = bat - drain_pct * active.float()
        new_bat = new_bat.clamp(min=0.0, max=100.0)

        self.batteries[:n] = new_bat

        self._timings.battery_ms = self._timer_end(t_start)

    # ─────────────────────────────────────────────────────────
    # GPU 활용 정보
    # ─────────────────────────────────────────────────────────

    def get_gpu_utilization_info(self) -> dict:
        """GPU 메모리/연산 통계 반환 (대시보드 표시용).

        Returns
        -------
        dict
            device, gpu_name, vram_total_gb, vram_used_gb,
            vram_free_gb, vram_utilization_pct, n_drones,
            timings, tf32_enabled 등.
        """
        info: dict[str, Any] = {
            "device": str(self.device),
            "n_drones": self._n,
            "max_drones": self.max_drones,
            "timings": {
                "sync_upload_ms": round(self._timings.sync_upload_ms, 3),
                "forces_ms": round(self._timings.forces_ms, 3),
                "collision_ms": round(self._timings.collision_ms, 3),
                "position_ms": round(self._timings.position_ms, 3),
                "battery_ms": round(self._timings.battery_ms, 3),
                "sync_download_ms": round(self._timings.sync_download_ms, 3),
            },
        }

        if self._use_cuda:
            idx = self.device.index or 0
            props = torch.cuda.get_device_properties(idx)
            mem_alloc = torch.cuda.memory_allocated(idx)
            mem_reserved = torch.cuda.memory_reserved(idx)
            mem_total = props.total_memory

            info.update({
                "gpu_name": props.name,
                "compute_capability": f"{props.major}.{props.minor}",
                "vram_total_gb": round(mem_total / 1e9, 2),
                "vram_allocated_gb": round(mem_alloc / 1e9, 4),
                "vram_reserved_gb": round(mem_reserved / 1e9, 4),
                "vram_free_gb": round((mem_total - mem_reserved) / 1e9, 2),
                "vram_utilization_pct": round(mem_reserved / mem_total * 100, 1),
                "tf32_enabled": torch.backends.cuda.matmul.allow_tf32,
                "cudnn_benchmark": torch.backends.cudnn.benchmark,
                "n_cuda_streams": 2,
            })
        else:
            info.update({
                "gpu_name": None,
                "vram_total_gb": 0,
                "tf32_enabled": False,
            })

        return info

    # ─────────────────────────────────────────────────────────
    # 내부 헬퍼
    # ─────────────────────────────────────────────────────────

    def _update_active_mask(self) -> None:
        """phases 텐서로부터 활성 마스크 갱신."""
        n = self._n
        phases = self.phases[:n]
        # GROUNDED(0)과 FAILED(5) 제외
        self.active_mask[:n] = (phases != PHASE_GROUNDED) & (phases != PHASE_FAILED)
        self.active_mask[n:] = False

    def _compute_apf_forces(
        self,
        pos: "torch.Tensor",
        vel: "torch.Tensor",
        goals: "torch.Tensor",
        has_goal: "torch.Tensor",
        wind: "torch.Tensor",
        active: "torch.Tensor",
        obs_tensor: "torch.Tensor",
        id_hashes: "torch.Tensor",
        n: int,
        params_override: dict | None,
    ) -> "torch.Tensor":
        """GPU APF 합력 텐서 연산 (핵심 커널).

        apf_gpu.py의 로직을 전체 활성 드론으로 확장.
        """
        dtype = torch.float32
        F_total = torch.zeros((n, 3), dtype=dtype, device=self.device)

        # ── 쌍별 거리 행렬 (N, N) ──
        diff_nn = pos.unsqueeze(1) - pos.unsqueeze(0)  # (N, N, 3)
        dist_nn = torch.linalg.norm(diff_nn, dim=2)  # (N, N)

        # 자기 자신 마스킹 — 대각선 inf (Python 루프 없음)
        diag_mask = torch.eye(n, dtype=torch.bool, device=self.device)
        dist_masked = dist_nn.masked_fill(diag_mask, float("inf"))

        # ── 파라미터 선택 (드론별 바람/밀도 기반) ──
        # 150m 이내 이웃 수
        neighbor_count = ((dist_masked < 150.0) & (~diag_mask)).sum(dim=1)  # (N,)

        if params_override is not None:
            param_vec = torch.tensor(
                [params_override[k] for k in self._param_keys],
                dtype=dtype, device=self.device,
            )
            params_all = param_vec.unsqueeze(0).expand(n, -1)
        else:
            is_hd = neighbor_count >= 2
            is_windy = wind > 12.0
            is_blend = (wind > 6.0) & (~is_windy)
            t = ((wind - 6.0) / 6.0).clamp(0, 1)

            n_params = len(self._param_keys)
            params_all = self._p_normal.unsqueeze(0).expand(n, -1).clone()

            # 블렌딩 (6~12 m/s)
            blend_mask = is_blend.unsqueeze(1).expand(-1, n_params)
            blended = (
                self._p_normal.unsqueeze(0) * (1 - t.unsqueeze(1))
                + self._p_windy.unsqueeze(0) * t.unsqueeze(1)
            )
            params_all = torch.where(blend_mask, blended, params_all)

            # 강풍 (>12 m/s)
            windy_mask = is_windy.unsqueeze(1).expand(-1, n_params)
            params_all = torch.where(
                windy_mask, self._p_windy.unsqueeze(0).expand(n, -1), params_all
            )

            # 고밀도 (최우선)
            hd_mask = is_hd.unsqueeze(1).expand(-1, n_params)
            params_all = torch.where(
                hd_mask, self._p_hd.unsqueeze(0).expand(n, -1), params_all
            )

        # 파라미터 분리
        k_att = params_all[:, 0]
        k_rep_drone = params_all[:, 1]
        k_rep_obs = params_all[:, 2]
        d0_drone = params_all[:, 3]
        d0_obs = params_all[:, 4]
        max_force = params_all[:, 5]
        altitude_k = params_all[:, 6]

        # ═══════════════════════════════════════════════════
        # 1. 인력 (목표 방향)
        # ═══════════════════════════════════════════════════
        goal_diff = goals - pos  # (N, 3)
        goal_dist = torch.linalg.norm(goal_diff, dim=1, keepdim=True).clamp(
            min=1e-6
        )

        d_t = 10.0
        near_goal = (goal_dist.squeeze() <= d_t) & (goal_dist.squeeze() >= 0.1)
        far_goal = goal_dist.squeeze() > d_t

        F_att = torch.zeros_like(F_total)
        F_att[near_goal] = k_att[near_goal].unsqueeze(1) * goal_diff[near_goal]
        F_att[far_goal] = (
            k_att[far_goal].unsqueeze(1)
            * goal_diff[far_goal]
            / goal_dist[far_goal]
            * d_t
        )

        too_close = goal_dist.squeeze() < 0.1
        F_att[too_close] = 0.0
        F_att[~has_goal] = 0.0
        F_att[~active] = 0.0

        F_total += F_att

        # ═══════════════════════════════════════════════════
        # 2. 드론 간 척력 (벡터화 행렬 연산)
        # ═══════════════════════════════════════════════════
        in_range = (dist_masked < d0_drone.unsqueeze(1)) & (dist_masked > 1e-3)

        if in_range.any():
            n_hat = diff_nn / dist_masked.unsqueeze(2).clamp(min=1e-6)

            inv_dist = 1.0 / dist_masked.clamp(min=1e-6)
            inv_d0 = 1.0 / d0_drone.unsqueeze(1)
            mag = k_rep_drone.unsqueeze(1) * (inv_dist - inv_d0) * inv_dist ** 2

            # 속도 기반 접근 증폭
            rel_vel = vel.unsqueeze(1) - vel.unsqueeze(0)  # (N, N, 3)
            closing_speed = -(rel_vel * n_hat).sum(dim=2).clamp(min=0.0)

            max_amp = torch.where(
                d0_drone > 100,
                torch.tensor(5.0, device=self.device),
                torch.tensor(3.0, device=self.device),
            )
            amplification = (1.0 + closing_speed / 3.0).clamp(
                max=max_amp.unsqueeze(1)
            )
            mag = mag * amplification * in_range.float()

            F_rep_drone = (mag.unsqueeze(2) * n_hat).sum(dim=1)

            # 비활성 드론은 척력 발생시키지 않음
            active_3d = active.unsqueeze(1).expand_as(F_rep_drone)
            F_total += torch.where(active_3d, F_rep_drone, torch.zeros_like(F_rep_drone))

        # ═══════════════════════════════════════════════════
        # 3. 장애물 척력 (NFZ)
        # ═══════════════════════════════════════════════════
        n_obs = obs_tensor.shape[0]
        if n_obs > 0:
            obs_diff = pos.unsqueeze(1) - obs_tensor.unsqueeze(0)  # (N, K, 3)
            obs_dist = torch.linalg.norm(obs_diff, dim=2)  # (N, K)

            obs_in_range = (obs_dist < d0_obs.unsqueeze(1)) & (obs_dist > 1e-3)

            if obs_in_range.any():
                obs_n = obs_diff / obs_dist.unsqueeze(2).clamp(min=1e-6)
                obs_inv_d = 1.0 / obs_dist.clamp(min=1e-6)
                obs_inv_d0 = 1.0 / d0_obs.unsqueeze(1)
                obs_mag = (
                    k_rep_obs.unsqueeze(1)
                    * (obs_inv_d - obs_inv_d0)
                    * obs_inv_d ** 2
                )
                obs_mag = obs_mag * obs_in_range.float()

                F_rep_obs = (obs_mag.unsqueeze(2) * obs_n).sum(dim=1)
                F_total += F_rep_obs

        # ═══════════════════════════════════════════════════
        # 4. 고도 보정
        # ═══════════════════════════════════════════════════
        target_alt = 60.0
        alt_error = target_alt - pos[:, 2]
        F_total[:, 2] += altitude_k * alt_error * active.float()

        # 4a. 지면 회피 (z < 5m)
        ground_clearance = pos[:, 2]
        ground_danger = (ground_clearance < 5.0) & active
        if ground_danger.any():
            gc = ground_clearance[ground_danger].clamp(min=0.1)
            ground_rep = k_rep_obs[ground_danger] * (1.0 / gc - 1.0 / 5.0)
            F_total[ground_danger, 2] += ground_rep

        # ═══════════════════════════════════════════════════
        # 5. 교착 탈출 (local minima escape)
        # ═══════════════════════════════════════════════════
        f_mag = torch.linalg.norm(F_total, dim=1)
        g_dist = torch.linalg.norm(goal_diff, dim=1)
        stuck = (f_mag < 0.5) & (g_dist > 20.0) & has_goal & active

        if stuck.any():
            stuck_idx = torch.where(stuck)[0]
            goal_dir = goal_diff[stuck] / g_dist[stuck].unsqueeze(1).clamp(min=1e-3)

            perp = torch.zeros_like(goal_dir)
            perp[:, 0] = -goal_dir[:, 1]
            perp[:, 1] = goal_dir[:, 0]
            perp_mag = torch.linalg.norm(perp, dim=1, keepdim=True).clamp(min=1e-3)
            perp = perp / perp_mag

            # ID 해시 기반 방향 (짝수 → +1, 홀수 → -1) — Python 루프 없음
            signs = torch.where(
                id_hashes[stuck] % 2 == 0,
                torch.tensor(1.0, device=self.device),
                torch.tensor(-1.0, device=self.device),
            )
            F_total[stuck] += signs.unsqueeze(1) * perp * k_att[stuck].unsqueeze(1) * 2.0

        # ═══════════════════════════════════════════════════
        # 6. 최대 합력 클리핑
        # ═══════════════════════════════════════════════════
        f_mag = torch.linalg.norm(F_total, dim=1, keepdim=True)
        clip_mask = f_mag.squeeze() > max_force
        if clip_mask.any():
            F_total[clip_mask] = (
                F_total[clip_mask]
                / f_mag[clip_mask]
                * max_force[clip_mask].unsqueeze(1)
            )

        # 목표 없거나 비활성 → 제로
        F_total[~has_goal] = 0.0
        F_total[~active] = 0.0

        return F_total

    def _extract_pairs(
        self,
        mask: "torch.Tensor",
        dist_matrix: "torch.Tensor",
        active_indices: "torch.Tensor",
    ) -> list[tuple[str, str, float]]:
        """마스크에서 (drone_id_a, drone_id_b, distance) 쌍 추출."""
        if not mask.any():
            return []

        indices = torch.nonzero(mask, as_tuple=False)  # (K, 2)
        pairs: list[tuple[str, str, float]] = []

        indices_cpu = indices.cpu().numpy()
        active_cpu = active_indices.cpu().numpy()
        dists_cpu = dist_matrix.cpu().numpy()

        for row in indices_cpu:
            i_local, j_local = int(row[0]), int(row[1])
            i_global = int(active_cpu[i_local])
            j_global = int(active_cpu[j_local])
            dist_val = float(dists_cpu[i_local, j_local])
            pairs.append((
                self._drone_ids[i_global],
                self._drone_ids[j_global],
                dist_val,
            ))

        return pairs

    # ─────────────────────────────────────────────────────────
    # 타이밍 유틸리티
    # ─────────────────────────────────────────────────────────

    def _timer_start(self) -> Any:
        """CUDA Event 또는 CPU 타이머 시작."""
        if self._use_cuda:
            start = torch.cuda.Event(enable_timing=True)
            end = torch.cuda.Event(enable_timing=True)
            start.record()
            return (start, end)
        return time.perf_counter()

    def _timer_end(self, t_start: Any) -> float:
        """경과 시간 (ms) 반환."""
        if self._use_cuda:
            start_evt, end_evt = t_start
            end_evt.record()
            torch.cuda.synchronize()
            return start_evt.elapsed_time(end_evt)
        return (time.perf_counter() - t_start) * 1000.0

    # ─────────────────────────────────────────────────────────
    # 리소스 정리
    # ─────────────────────────────────────────────────────────

    def release(self) -> None:
        """GPU 텐서 메모리 해제."""
        for attr_name in [
            "positions", "velocities", "goals", "has_goal",
            "batteries", "phases", "headings", "forces",
            "active_mask", "profile_indices", "_wind_speeds",
            "_id_hashes",
        ]:
            tensor = getattr(self, attr_name, None)
            if tensor is not None:
                del tensor

        if self._use_cuda:
            torch.cuda.empty_cache()

        logger.info("GPUPhysicsEngine released GPU resources.")


# ─────────────────────────────────────────────────────────────
# Null context manager (CPU fallback)
# ─────────────────────────────────────────────────────────────


class _nullcontext:
    """Python 3.7+ contextlib.nullcontext 대체."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


# ─────────────────────────────────────────────────────────────
# 모듈 수준 팩토리
# ─────────────────────────────────────────────────────────────


def create_gpu_physics_engine(
    max_drones: int = 500,
    device: Any = None,
) -> GPUPhysicsEngine | None:
    """GPUPhysicsEngine 생성. PyTorch/CUDA 없으면 None 반환.

    Parameters
    ----------
    max_drones : int
        사전 할당 드론 수.
    device : torch.device | None
        명시적 디바이스.

    Returns
    -------
    GPUPhysicsEngine | None
        엔진 인스턴스 또는 None (폴백).
    """
    if not _TORCH_AVAILABLE:
        logger.warning(
            "PyTorch not available. GPUPhysicsEngine disabled. "
            "Falling back to CPU computation."
        )
        return None

    try:
        engine = GPUPhysicsEngine(max_drones=max_drones, device=device)
        return engine
    except Exception:
        logger.exception("Failed to create GPUPhysicsEngine. Falling back to CPU.")
        return None
