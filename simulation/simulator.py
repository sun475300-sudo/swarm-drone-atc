"""
군집드론 공역통제 메인 시뮬레이터
==================================
SimPy 기반 이산 이벤트 시뮬레이션.

구성 요소:
  SwarmSimulator   — 최상위 오케스트레이터
  _DroneAgent      — 드론 1기의 10 Hz SimPy 프로세스

실행 예시:
  from simulation.simulator import SwarmSimulator
  sim = SwarmSimulator("config/default_simulation.yaml")
  result = sim.run()
  print(result.to_dict())
"""

from __future__ import annotations

import logging
import os
import sys

import numpy as np
import simpy
import yaml

# 프로젝트 루트를 sys.path에 추가 (직접 실행 지원)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from simulation.analytics import SimulationAnalytics, SimulationResult
from simulation.apf_engine.apf import (
    APFState,
    batch_compute_forces,
)
from simulation.drone_agent import DroneAgent as _DroneAgent
from simulation.spatial_hash import SpatialHash
from simulation.weather import WindModel, build_wind_models
from src.airspace_control.agents.drone_profiles import DRONE_PROFILES
from src.airspace_control.agents.drone_state import (
    CommsStatus,
    DroneState,
    FailureType,
    FlightPhase,
)
from src.airspace_control.avoidance.resolution_advisory import AdvisoryGenerator
from src.airspace_control.comms.communication_bus import CommMessage, CommunicationBus
from src.airspace_control.comms.message_types import (
    ClearanceRequest,
)
from src.airspace_control.controller.airspace_controller import AirspaceController
from src.airspace_control.controller.priority_queue import FlightPriorityQueue
from src.airspace_control.planning.flight_path_planner import FlightPathPlanner

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# 유틸리티
# ─────────────────────────────────────────────────────────────


def _load_yaml(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _drone_to_apf(d: DroneState) -> APFState:
    return APFState(
        position=d.position.copy(),
        velocity=d.velocity.copy(),
        drone_id=d.drone_id,
    )



# ─────────────────────────────────────────────────────────────
# 메인 시뮬레이터
# ─────────────────────────────────────────────────────────────


class SwarmSimulator:
    """
    군집드론 공역통제 메인 시뮬레이터.

    Parameters
    ----------
    config_path:  default_simulation.yaml 경로
    scenario_cfg: 시나리오 오버라이드 dict (None이면 기본값 사용)
    seed:         재현성 시드
    """

    LANDING_PADS = {
        "PAD_NW": np.array([-3000.0, 3000.0, 0.0]),
        "PAD_NE": np.array([3000.0, 3000.0, 0.0]),
        "PAD_SW": np.array([-3000.0, -3000.0, 0.0]),
        "PAD_SE": np.array([3000.0, -3000.0, 0.0]),
        "PAD_CENTER": np.array([0.0, 0.0, 0.0]),
    }
    NFZ = [{"center": np.array([0.0, 0.0, 60.0]), "radius_m": 600.0}]

    def __init__(
        self,
        config_path: str = "config/default_simulation.yaml",
        scenario_cfg: dict | None = None,
        seed: int = 42,
    ) -> None:
        """인스턴스를 초기화한다."""
        self.seed = seed
        self.rng = np.random.default_rng(seed)

        # YAML 로드
        base_cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), config_path)
        if not os.path.exists(base_cfg_path):
            base_cfg_path = config_path
        if not os.path.exists(base_cfg_path):
            logger.warning("Config file not found: %s — using defaults", base_cfg_path)
        self.cfg: dict = _load_yaml(base_cfg_path) if os.path.exists(base_cfg_path) else {}
        if scenario_cfg:
            self._deep_merge(self.cfg, scenario_cfg)

        # 공역 경계
        bounds_km = self.cfg.get("airspace", {}).get("bounds_km", {})
        self.bounds_m = abs(float(bounds_km.get("x", [-5, 5])[1])) * 1000.0

        # SimPy
        self.env = simpy.Environment()

        # 서브시스템
        comms_cfg = self.cfg.get("drones", {})
        self.comm_bus = CommunicationBus(
            env=self.env,
            rng=self.rng,
            latency_ms_mean=20.0,
            packet_loss_rate=float(np.clip(float(self.cfg.get("comms_loss_rate", 0.0)), 0.0, 1.0)),
            comm_range_m=float(comms_cfg.get("comm_range_m", 2000.0)),
        )
        airspace_bounds = {
            "x": [-self.bounds_m, self.bounds_m],
            "y": [-self.bounds_m, self.bounds_m],
            "z": [0.0, 120.0],
        }
        self.planner = FlightPathPlanner(
            airspace_bounds=airspace_bounds,
            no_fly_zones=self.NFZ,
        )
        self.advisory_gen = AdvisoryGenerator(
            separation_lateral_m=float(self.cfg.get("separation_standards", {}).get("lateral_min_m", 50.0)),
            separation_vertical_m=float(self.cfg.get("separation_standards", {}).get("vertical_min_m", 15.0)),
        )
        self._sep_lateral = float(
            self.cfg.get("separation_standards", {}).get("lateral_min_m", 50.0))
        self._near_miss_m = float(
            self.cfg.get("separation_standards", {}).get("near_miss_lateral_m", 10.0))
        self.priority_queue = FlightPriorityQueue()
        self.analytics = SimulationAnalytics(self.cfg)
        self.controller = AirspaceController(
            env=self.env,
            comm_bus=self.comm_bus,
            planner=self.planner,
            advisory_gen=self.advisory_gen,
            priority_queue=self.priority_queue,
            config=self.cfg,
            analytics=self.analytics,
        )
        self.wind_models: list[WindModel] = build_wind_models(self.cfg.get("weather", {}), self.rng)
        self.landing_pads = self.LANDING_PADS

        # APF 힘 캐시 (배치 계산 → 각 드론 프로세스 참조)
        self.apf_forces: dict[str, np.ndarray] = {}

        # 고장 주입 설정
        fi = self.cfg.get("failure_injection", {})
        self._failure_rate: float = float(fi.get("drone_failure_rate", 0.0))
        self._comms_loss_rate: float = float(fi.get("comms_loss_rate", 0.0))
        self._failure_types_pool = [FailureType.MOTOR_FAILURE, FailureType.BATTERY_CRITICAL, FailureType.GPS_LOSS]

        # 드론 관리
        self._drones: dict[str, DroneState] = {}
        self._n_drones = int(self.cfg.get("drones", {}).get("default_count", 30))

        self._scenario_name = str(self.cfg.get("scenario", {}).get("name", "default"))

    # ── 공개 API ─────────────────────────────────────────────

    def run(self, duration_s: float | None = None) -> SimulationResult:
        """메인 실행 루프를 수행한다."""
        dur = duration_s or float(self.cfg.get("simulation", {}).get("duration_minutes", 10)) * 60.0

        self._spawn_drones()
        self.env.process(self.controller.run())
        self.env.process(self._apf_batch_loop())
        self.env.process(self._analytics_loop())
        if self._failure_rate > 0 or self._comms_loss_rate > 0:
            self.env.process(self._failure_injection_loop())
        self.env.run(until=dur)

        # 컨트롤러/통신 통계 기록
        self.analytics.record_controller_stats(
            cbs_attempts=self.controller._cbs_attempts,
            cbs_successes=self.controller._cbs_successes,
            astar_count=self.controller._astar_count,
            clearances_per_sec=self.controller._clearances_per_sec,
        )
        comm_stats = self.comm_bus.stats
        self.analytics.record_comm_stats(
            sent=comm_stats["sent"],
            delivered=comm_stats["delivered"],
            dropped=comm_stats["dropped"],
        )

        return self.analytics.finalize(
            seed=self.seed,
            scenario=self._scenario_name,
            duration_s=dur,
            n_drones=self._n_drones,
        )

    # ── 드론 스폰 ────────────────────────────────────────────

    def _spawn_drones(self) -> None:
        dt = 1.0 / float(self.cfg.get("simulation", {}).get("time_step_hz", 10))
        profiles = ["COMMERCIAL_DELIVERY", "SURVEILLANCE", "EMERGENCY", "RECREATIONAL"]
        weights = [0.55, 0.25, 0.10, 0.10]
        pad_list = list(self.LANDING_PADS.values())
        pad_count = max(1, len(pad_list))
        slots_per_pad = int(np.ceil(self._n_drones / pad_count))
        grid_width = max(1, int(np.ceil(np.sqrt(slots_per_pad))))
        configured_spacing_m = float(self.cfg.get("drones", {}).get("launch_spacing_m", 75.0))
        grid_center = (grid_width - 1) / 2.0
        usable_half_extent = max(1.0, self.bounds_m - 300.0)
        launch_spacing_m = (
            min(configured_spacing_m, usable_half_extent / grid_center)
            if grid_center > 0.0
            else configured_spacing_m
        )
        grid_extent_m = grid_center * launch_spacing_m

        scenario_drones = self.cfg.get("scenario", {}).get("drones", {})
        n_rogue = int(scenario_drones.get("n_rogue", 0))

        for i in range(self._n_drones):
            pad = pad_list[i % pad_count].copy()
            pad[:2] = np.clip(
                pad[:2],
                -self.bounds_m + 300.0 + grid_extent_m,
                self.bounds_m - 300.0 - grid_extent_m,
            )
            slot_idx = i // pad_count
            row, col = divmod(slot_idx, grid_width)
            jitter = np.array(
                [
                    (col - grid_center) * launch_spacing_m,
                    (row - grid_center) * launch_spacing_m,
                    0.0,
                ],
                dtype=float,
            )
            jitter[:2] += self.rng.uniform(-launch_spacing_m * 0.05, launch_spacing_m * 0.05, 2)
            start = pad + jitter
            start[2] = 0.0
            start[:2] = np.clip(start[:2], -self.bounds_m + 300, self.bounds_m - 300)

            profile = str(self.rng.choice(profiles, p=weights))
            if i < n_rogue:
                profile = "ROGUE"

            drone = DroneState(
                drone_id=f"DR{i:03d}",
                position=start.copy(),
                velocity=np.zeros(3),
                profile_name=profile,
                flight_phase=FlightPhase.GROUNDED,
                battery_pct=float(self.rng.uniform(70, 100)),
            )
            self._assign_goal(drone)
            self._drones[drone.drone_id] = drone

            agent = _DroneAgent(self.env, drone, self, dt)
            self.env.process(agent.run())

    def add_drone(self, drone_id: str | None = None, position: np.ndarray | None = None,
                  profile: str = "COMMERCIAL_DELIVERY") -> DroneState:
        """시뮬레이션 중 드론 동적 추가."""
        dt = 1.0 / float(self.cfg.get("simulation", {}).get("time_step_hz", 10))
        if drone_id is None:
            drone_id = f"DR{len(self._drones):03d}"
        if position is None:
            pad_list = list(self.LANDING_PADS.values())
            position = pad_list[self.rng.integers(len(pad_list))].copy()
            position[2] = 0.0

        drone = DroneState(
            drone_id=drone_id,
            position=position.copy(),
            velocity=np.zeros(3),
            profile_name=profile,
            flight_phase=FlightPhase.GROUNDED,
            battery_pct=float(self.rng.uniform(70, 100)),
        )
        self._assign_goal(drone)
        self._drones[drone.drone_id] = drone
        self._n_drones += 1

        agent = _DroneAgent(self.env, drone, self, dt)
        self.env.process(agent.run())
        return drone

    def remove_drone(self, drone_id: str) -> bool:
        """시뮬레이션 중 드론 동적 제거 (착륙 처리)."""
        drone = self._drones.get(drone_id)
        if drone is None:
            return False
        drone.flight_phase = FlightPhase.GROUNDED
        drone.velocity = np.zeros(3)
        del self._drones[drone_id]
        self._n_drones -= 1
        return True

    def _assign_goal(self, drone: DroneState) -> None:
        pad_list = list(self.LANDING_PADS.values())
        goal = pad_list[self.rng.integers(len(pad_list))].copy()
        for _ in range(10):
            if np.linalg.norm(goal[:2] - drone.position[:2]) > 1500:
                break
            goal = pad_list[self.rng.integers(len(pad_list))].copy()
        goal[2] = 60.0  # 순항 고도
        # NFZ 회피: 모든 NFZ에 대해 검증
        for nfz in self.NFZ:
            if np.linalg.norm(goal[:2] - nfz["center"][:2]) < nfz["radius_m"]:
                goal[0] += float(self.rng.choice([-900.0, 900.0]))
                break
        # 범위 클램핑
        goal[0] = float(np.clip(goal[0], -self.bounds_m + 200, self.bounds_m - 200))
        goal[1] = float(np.clip(goal[1], -self.bounds_m + 200, self.bounds_m - 200))
        drone.goal = goal
        drone.planned_distance_m = float(np.linalg.norm(goal - drone.position))
        drone.leg_start_distance_m = drone.distance_flown_m  # 이 구간의 실제거리 기준점
        self.analytics.record_planned_distance(drone.drone_id, drone.planned_distance_m)

    def _request_clearance(self, drone: DroneState, t: float) -> None:
        if drone.goal is None:
            return
        self.comm_bus.send(
            CommMessage(
                sender_id=drone.drone_id,
                receiver_id="CONTROLLER",
                payload=ClearanceRequest(
                    drone_id=drone.drone_id,
                    origin=drone.position.copy(),
                    destination=drone.goal.copy(),
                    priority=DRONE_PROFILES.get(drone.profile_name, DRONE_PROFILES["COMMERCIAL_DELIVERY"]).priority,
                    timestamp_s=t,
                    profile_name=drone.profile_name,
                ),
                sent_time=t,
                channel="clearance_req",
            )
        )

    # ── APF 배치 루프 ─────────────────────────────────────────

    def _apf_batch_loop(self):
        """10 Hz: EVADING/RTL 드론에 대해 APF 힘 배치 계산"""
        dt = 0.1
        nfz_centers = [n["center"] for n in self.NFZ]
        while True:
            yield self.env.timeout(dt)
            # L-3: RTL 드론도 APF 회피 대상에 포함
            evading = [
                d
                for d in self._drones.values()
                if d.flight_phase in (FlightPhase.EVADING, FlightPhase.RTL) and d.goal is not None
            ]
            if evading:
                states = [_drone_to_apf(d) for d in evading]
                goals = {d.drone_id: d.goal.copy() for d in evading}

                # 각 드론 위치의 바람 속도 계산 (강풍 조건 APF 파라미터 자동 선택용)
                wind_speeds = {}
                t = float(self.env.now)
                for d in evading:
                    # 모든 wind_models의 바람 벡터를 합산
                    wind_vec = np.zeros(3)
                    for wm in self.wind_models:
                        wind_vec += wm.get_wind_vector(d.position, t)
                    # 바람 속도 (m/s) 계산
                    wind_speeds[d.drone_id] = float(np.linalg.norm(wind_vec))

                # L-2 설계 결정: all_active에 TAKEOFF/LANDING 포함 (이웃 풀로 가시)
                # → 다른 드론이 이착륙 드론을 피하지만, 이착륙 드론 자체는 고정 수직 프로파일 유지
                all_active = [_drone_to_apf(d) for d in self._drones.values() if d.is_active]
                self.apf_forces = batch_compute_forces(
                    states, goals, nfz_centers, wind_speeds=wind_speeds, neighbor_states=all_active
                )
            else:
                self.apf_forces = {}

    # ── 분석 루프 ─────────────────────────────────────────────

    def _failure_injection_loop(self):
        """5초 주기: 확률 기반 고장/통신 두절 자동 주입"""
        INJECT_INTERVAL_S = 5.0
        while True:
            yield self.env.timeout(INJECT_INTERVAL_S)
            t = float(self.env.now)

            for drone in self._drones.values():
                if not drone.is_active or drone.flight_phase in (
                    FlightPhase.GROUNDED,
                    FlightPhase.FAILED,
                    FlightPhase.LANDING,
                ):
                    continue

                # 드론 고장 주입 (매 5초 간격 확률)
                if (
                    self._failure_rate > 0
                    and drone.failure_type == FailureType.NONE
                    and self.rng.random() < self._failure_rate * INJECT_INTERVAL_S / 60.0
                ):
                    failure = self.rng.choice(self._failure_types_pool)
                    drone.failure_type = failure
                    if failure == FailureType.MOTOR_FAILURE:
                        drone.flight_phase = FlightPhase.FAILED
                    elif failure == FailureType.BATTERY_CRITICAL:
                        drone.battery_pct = 3.0
                        drone.flight_phase = FlightPhase.LANDING
                    if self.analytics:
                        self.analytics.record_event(
                            "FAILURE_INJECTED",
                            t,
                            drone_id=drone.drone_id,
                            failure_type=failure.name,
                        )

                # 통신 두절 주입
                if (
                    self._comms_loss_rate > 0
                    and drone.comms_status == CommsStatus.NOMINAL
                    and self.rng.random() < self._comms_loss_rate * INJECT_INTERVAL_S / 60.0
                ):
                    drone.comms_status = CommsStatus.LOST
                    if self.analytics:
                        self.analytics.record_event(
                            "COMMS_LOSS_INJECTED",
                            t,
                            drone_id=drone.drone_id,
                        )

    def _analytics_loop(self):
        """1 Hz: 전체 드론 스냅샷 + 충돌 감지 (Spatial Hash 기반)"""
        sh = SpatialHash(cell_size=50.0)
        while True:
            yield self.env.timeout(1.0)
            t = float(self.env.now)
            self.analytics.record_snapshot(self._drones, t)

            # 컨트롤러에 현재 풍속 전달 → 동적 분리간격 조정
            if self.wind_models:
                avg_wind = np.zeros(3)
                for wm in self.wind_models:
                    avg_wind += wm.get_wind_vector(np.zeros(3), t)
                self.controller.update_wind_speed(float(np.linalg.norm(avg_wind)))

            # Spatial Hash로 충돌 감지 (5 m 이내) — O(N·k)
            # A1: LANDING 드론은 충돌 스캔에서 제외 (착지 중 수직 프로파일은 안전)
            sh.clear()
            for did, d in self._drones.items():
                if d.is_active and d.flight_phase != FlightPhase.LANDING:
                    sh.insert(did, d.position)

            for id_a, id_b, dist in sh.query_pairs_with_dist(self._sep_lateral):
                if dist < 5.0:
                    da = self._drones[id_a]
                    db = self._drones[id_b]
                    self.analytics.record_event(
                        "COLLISION",
                        t,
                        drone_a=id_a,
                        drone_b=id_b,
                        dist_m=dist,
                        phase_a=da.flight_phase.name,
                        phase_b=db.flight_phase.name,
                        alt_a_m=float(da.position[2]),
                        alt_b_m=float(db.position[2]),
                    )
                elif dist < self._near_miss_m:
                    self.analytics.record_event("NEAR_MISS", t,
                                                drone_a=id_a, drone_b=id_b,
                                                dist_m=dist)
                else:
                    self.analytics.record_event("CONFLICT", t,
                                                drone_a=id_a, drone_b=id_b,
                                                dist_m=dist)

    # ── 유틸리티 ─────────────────────────────────────────────

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> None:
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                SwarmSimulator._deep_merge(base[k], v)
            else:
                base[k] = v


# ─────────────────────────────────────────────────────────────
# CLI 진입점
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="군집드론 시뮬레이터")
    parser.add_argument("--config", default="config/default_simulation.yaml")
    parser.add_argument("--duration", type=float, default=None, help="시뮬레이션 시간 (초)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--drones", type=int, default=None)
    args = parser.parse_args()

    override: dict = {}
    if args.drones:
        override = {"drones": {"default_count": args.drones}}

    sim = SwarmSimulator(args.config, scenario_cfg=override or None, seed=args.seed)
    result = sim.run(args.duration)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
