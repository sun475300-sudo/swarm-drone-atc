"""
SimPy 기반 군집드론 시뮬레이션 엔진
  - 드론 N기 랜덤 배치 + APF 충돌 회피
  - CommunicationBus 텔레메트리
  - 매 스텝 근접 위반 / 충돌 감지
  - config YAML 파라미터 적용
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import simpy
import yaml

from simulation.apf_engine import APFState, batch_compute_forces, force_to_velocity
from simulation.metrics import SimulationMetrics
from simulation.weather import WindModel, build_wind_models
from src.airspace_control.agents.drone_state import (
    DroneState, FlightPhase, CommsStatus, FailureType,
)
from src.airspace_control.agents.drone_profiles import DRONE_PROFILES
from src.airspace_control.comms.communication_bus import CommunicationBus
from src.airspace_control.planning.flight_path_planner import FlightPathPlanner
from src.airspace_control.planning.waypoint import Waypoint

logger = logging.getLogger("sdacs.engine")

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _default_config() -> dict:
    return _load_yaml(CONFIG_DIR / "default_simulation.yaml")


# ─── 드론 초기 배치 ────────────────────────────────────────────

def _random_position(rng: np.random.Generator, bounds: dict) -> np.ndarray:
    x = rng.uniform(bounds["x"][0], bounds["x"][1])
    y = rng.uniform(bounds["y"][0], bounds["y"][1])
    z = rng.uniform(30.0, 120.0)
    return np.array([x, y, z])


def _assign_profile(rng: np.random.Generator,
                    distribution: Optional[dict] = None) -> str:
    if distribution is None:
        distribution = {
            "COMMERCIAL_DELIVERY": 0.6,
            "SURVEILLANCE": 0.3,
            "EMERGENCY": 0.1,
        }
    names = list(distribution.keys())
    probs = np.array(list(distribution.values()), dtype=float)
    probs /= probs.sum()
    return str(rng.choice(names, p=probs))


# ─── 시뮬레이션 엔진 ──────────────────────────────────────────

class SimulationEngine:
    """SimPy 이산 사건 시뮬레이션 엔진"""

    def __init__(
        self,
        seed: int = 42,
        duration_s: float = 600.0,
        drone_count: int = 100,
        config: Optional[dict] = None,
        scenario_overrides: Optional[dict] = None,
    ):
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.config = config or _default_config()
        self.scenario_overrides = scenario_overrides or {}

        # merge overrides
        sim_cfg = self.config.get("simulation", {})
        self.duration_s = duration_s or sim_cfg.get("duration_minutes", 10) * 60
        self.dt = 1.0 / sim_cfg.get("time_step_hz", 10)
        self.control_dt = 1.0 / sim_cfg.get("control_hz", 1)

        drone_cfg = self.config.get("drones", {})
        self.drone_count = self.scenario_overrides.get(
            "drone_count",
            self.scenario_overrides.get("base_drone_count", drone_count)
        )
        self.max_speed = drone_cfg.get("max_speed_ms", 15.0)
        self.comm_range = drone_cfg.get("comm_range_m", 2000.0)

        sep_cfg = self.config.get("separation_standards", {})
        self.lateral_min = sep_cfg.get("lateral_min_m", 50.0)
        self.near_miss_lateral = sep_cfg.get("near_miss_lateral_m", 10.0)

        airspace = self.config.get("airspace", {})
        bounds_km = airspace.get("bounds_km", {"x": [-5, 5], "y": [-5, 5], "z": [0, 0.12]})
        self.bounds_m = {
            "x": [bounds_km["x"][0] * 1000, bounds_km["x"][1] * 1000],
            "y": [bounds_km["y"][0] * 1000, bounds_km["y"][1] * 1000],
        }

        # SimPy
        self.env = simpy.Environment()
        self.metrics = SimulationMetrics()

        # Comms
        self.comm_bus = CommunicationBus(
            env=self.env, rng=self.rng,
            comm_range_m=self.comm_range,
        )

        # Planner
        self.planner = FlightPathPlanner(
            airspace_bounds={
                "x": self.bounds_m["x"], "y": self.bounds_m["y"],
                "z": [-120.0, 0.0],
            },
            no_fly_zones=[{"center": np.array([0, 0, 0]), "radius_m": 500.0}],
        )

        # 드론 상태
        self.drones: dict[str, DroneState] = {}

        # 기상 모델 (WindModel 사용)
        self.wind_models: list[WindModel] = []
        self._failure_schedule: list[dict] = []
        # 충돌 추적: 감지된 쌍 → 해결 여부 추적
        self._active_conflicts: dict[frozenset, float] = {}  # pair → first_detected_t

        logger.info(
            "SimulationEngine 초기화: seed=%d, drones=%d, duration=%.0fs",
            self.seed, self.drone_count, self.duration_s,
        )

    # ── 초기화 ────────────────────────────────────────────────

    def _init_drones(self):
        profile_dist = self.scenario_overrides.get(
            "drone_profile_distribution", None
        )
        for i in range(self.drone_count):
            did = f"D-{i:04d}"
            pos = _random_position(self.rng, self.bounds_m)
            profile_name = _assign_profile(self.rng, profile_dist)
            profile = DRONE_PROFILES.get(profile_name)

            # 랜덤 목표
            goal = _random_position(self.rng, self.bounds_m)

            self.drones[did] = DroneState(
                drone_id=did,
                position=pos,
                velocity=np.zeros(3),
                battery_pct=100.0,
                flight_phase=FlightPhase.ENROUTE,
                profile_name=profile_name,
                goal=goal,
            )
            self.comm_bus.update_position(did, pos)
            self.metrics.routes_total += 1

            # 계획 거리 기록
            planned_dist = float(np.linalg.norm(goal - pos))
            self.drones[did].planned_distance_m = planned_dist
            self.metrics.total_planned_distance_m += planned_dist

    # ── 시나리오 이벤트 주입 ──────────────────────────────────

    def apply_scenario(self, scenario_params: dict):
        """시나리오별 특수 설정 적용"""
        self.scenario_overrides.update(scenario_params)

        # 기상 교란 — WindModel 통합
        weather = scenario_params.get("weather", {})
        self.wind_models = build_wind_models(weather, self.rng)

        # 장애 주입 스케줄
        failure = scenario_params.get("failure_injection", {})
        if failure:
            start_s = failure.get("start_time_min", 3) * 60
            end_s = failure.get("end_time_min", 7) * 60
            rate = failure.get("failure_rate_pct", 5) / 100
            n_fail = max(1, int(self.drone_count * rate))
            self._failure_schedule.append({
                "start_s": start_s, "end_s": end_s,
                "count": n_fail, "injected": False,
            })

        # duration override
        if "simulation_duration_s" in scenario_params:
            self.duration_s = scenario_params["simulation_duration_s"]
        elif "simulation_duration_min" in scenario_params:
            self.duration_s = scenario_params["simulation_duration_min"] * 60

        # drone count override
        for key in ("drone_count", "base_drone_count", "base_traffic"):
            if key in scenario_params:
                val = scenario_params[key]
                if isinstance(val, dict):
                    self.drone_count = val.get("drone_count", self.drone_count)
                else:
                    self.drone_count = val

    # ── 메인 시뮬레이션 루프 ─────────────────────────────────

    def _physics_step(self):
        """APF 기반 물리 스텝 (제너레이터)"""
        step = 0
        record_interval = max(1, int(1.0 / self.dt / 2))  # 0.5초마다 기록

        while True:
            yield self.env.timeout(self.dt)
            t = self.env.now

            # 장애 주입 확인
            self._check_failure_injection(t)

            # APF 상태 구성
            active_drones = [
                d for d in self.drones.values()
                if d.flight_phase == FlightPhase.ENROUTE
            ]
            if not active_drones:
                continue

            apf_states = [
                APFState(d.position.copy(), d.velocity.copy(), d.drone_id)
                for d in active_drones
            ]
            goals = {d.drone_id: d.goal for d in active_drones if d.goal is not None}
            obstacles = [np.array([0, 0, 60])]  # NFZ 중심

            # APF 합력 배치 계산
            forces = batch_compute_forces(
                apf_states, goals, obstacles,
                comm_range=self.comm_range,
            )

            # 위치 / 속도 업데이트
            for drone in active_drones:
                f = forces.get(drone.drone_id, np.zeros(3))
                # 기상 영향 (WindModel 기반)
                wind = sum(
                    (m.get_wind_vector(drone.position, t) for m in self.wind_models),
                    np.zeros(3),
                )
                f += wind * 0.3  # 바람 → 가속도 변환 스케일

                drone.velocity = force_to_velocity(
                    drone.velocity, f, self.dt, self.max_speed
                )
                old_pos = drone.position.copy()
                drone.position = drone.position + drone.velocity * self.dt

                # 경계 클램핑
                drone.position[0] = np.clip(
                    drone.position[0], self.bounds_m["x"][0], self.bounds_m["x"][1]
                )
                drone.position[1] = np.clip(
                    drone.position[1], self.bounds_m["y"][0], self.bounds_m["y"][1]
                )
                drone.position[2] = np.clip(drone.position[2], 30.0, 120.0)

                # 비행 거리 / 배터리
                dist_delta = float(np.linalg.norm(drone.position - old_pos))
                drone.distance_flown_m += dist_delta
                drone.flight_time_s = t
                drone.battery_pct -= dist_delta * 0.001  # 간이 소모 모델

                if drone.battery_pct <= 0:
                    drone.battery_pct = 0
                    drone.flight_phase = FlightPhase.FAILED
                    drone.failure_type = FailureType.BATTERY_CRITICAL
                    self.metrics.battery_depleted_count += 1

                # 목표 도달 확인
                if drone.goal is not None:
                    if np.linalg.norm(drone.position - drone.goal) < 30.0:
                        drone.flight_phase = FlightPhase.LANDING
                        self.metrics.routes_completed += 1
                        self.metrics.total_actual_distance_m += drone.distance_flown_m
                        # 새 목표 부여
                        drone.goal = _random_position(self.rng, self.bounds_m)
                        drone.planned_distance_m = float(
                            np.linalg.norm(drone.goal - drone.position)
                        )
                        self.metrics.total_planned_distance_m += drone.planned_distance_m
                        self.metrics.routes_total += 1
                        drone.distance_flown_m = 0
                        drone.flight_phase = FlightPhase.ENROUTE

                self.comm_bus.update_position(drone.drone_id, drone.position)

            # 근접 위반 / 충돌 감지
            self._check_separation(active_drones, t)

            # 궤적 기록
            if step % record_interval == 0:
                for drone in active_drones:
                    self.metrics.record_trajectory(
                        t, drone.drone_id,
                        drone.position, drone.velocity,
                        drone.battery_pct, drone.flight_phase.name,
                    )

            step += 1

    def _check_separation(self, drones: list[DroneState], t: float):
        """드론 쌍 간 이격 거리 확인 + 충돌 해결률 추적"""
        positions = np.array([d.position for d in drones])
        n = len(drones)
        if n < 2:
            return

        current_conflicts: set[frozenset] = set()

        for i in range(n):
            for j in range(i + 1, n):
                dist = float(np.linalg.norm(positions[i] - positions[j]))
                pair = frozenset((drones[i].drone_id, drones[j].drone_id))

                if dist < self.near_miss_lateral:
                    self.metrics.record_event(
                        t, "collision",
                        drone_a=drones[i].drone_id,
                        drone_b=drones[j].drone_id,
                        distance_m=dist,
                    )
                elif dist < self.lateral_min:
                    self.metrics.record_event(
                        t, "near_miss",
                        drone_a=drones[i].drone_id,
                        drone_b=drones[j].drone_id,
                        distance_m=dist,
                    )
                    current_conflicts.add(pair)
                    # 새로 감지된 충돌만 카운트
                    if pair not in self._active_conflicts:
                        self._active_conflicts[pair] = t
                        self.metrics.record_event(t, "conflict_detected")

        # 이전에 활성이었으나 현재 해소된 쌍 → conflict_resolved
        resolved_pairs = [p for p in self._active_conflicts if p not in current_conflicts]
        for pair in resolved_pairs:
            self.metrics.record_event(t, "conflict_resolved")
            del self._active_conflicts[pair]

    def _check_failure_injection(self, t: float):
        for sched in self._failure_schedule:
            if sched["injected"]:
                continue
            if t >= sched["start_s"]:
                sched["injected"] = True
                drone_ids = list(self.drones.keys())
                chosen = self.rng.choice(
                    drone_ids,
                    size=min(sched["count"], len(drone_ids)),
                    replace=False,
                )
                for did in chosen:
                    self.drones[did].flight_phase = FlightPhase.FAILED
                    self.drones[did].failure_type = FailureType.MOTOR_FAILURE
                    self.metrics.record_event(t, "drone_failure", drone_id=did)
                    self.metrics.emergency_response_times_s.append(
                        self.rng.uniform(0.5, 5.0)
                    )
                logger.info("장애 주입: %d기 at t=%.1f", len(chosen), t)

    # ── 실행 ─────────────────────────────────────────────────

    def run(self) -> SimulationMetrics:
        """시뮬레이션 실행 후 메트릭 반환"""
        self._init_drones()
        self.env.process(self._physics_step())
        self.env.run(until=self.duration_s)

        # 최종 배터리 통계
        batteries = [d.battery_pct for d in self.drones.values()]
        self.metrics.avg_battery_remaining_pct = float(np.mean(batteries))

        # 미완료 드론 실제 거리 포함
        for d in self.drones.values():
            if d.flight_phase == FlightPhase.ENROUTE:
                self.metrics.total_actual_distance_m += d.distance_flown_m

        logger.info("시뮬레이션 완료: %.0fs, %d기", self.duration_s, self.drone_count)
        return self.metrics
