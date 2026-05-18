"""
임베디드 시뮬레이션 루프 — Dash 시각화용 물리 엔진.

_in_nfz, _assign_goal, _step, _update, _sim_loop
"""

from __future__ import annotations

import math
import time
from typing import TYPE_CHECKING

import numpy as np

from simulation.apf_engine.apf import APFState, batch_compute_forces, force_to_velocity
from simulation.spatial_hash import SpatialHash
from src.airspace_control.agents.drone_state import DroneState, FailureType, FlightPhase
from src.airspace_control.agents.drone_profiles import DRONE_PROFILES
from visualization._scene_traces import (
    ALT_MAX,
    ALT_MIN,
    BOUNDS_M,
    CRUISE_ALT,
    NFZ_X,
    NFZ_Y,
    _NFZ_OBSTACLES,
    _PAD_LIST,
)

if TYPE_CHECKING:
    from visualization._domain import SimState


def _in_nfz(pos: np.ndarray) -> bool:
    return (NFZ_X[0] < pos[0] < NFZ_X[1]
            and NFZ_Y[0] < pos[1] < NFZ_Y[1])


def _assign_goal(drone: DroneState, rng: np.random.Generator | None = None) -> None:
    """착륙 후 새 목적지 무작위 배정"""
    rng = rng or np.random.default_rng()
    goal = _PAD_LIST[rng.integers(len(_PAD_LIST))].copy()
    for _ in range(10):
        if np.linalg.norm(goal[:2] - drone.position[:2]) > 1500:
            break
        goal = _PAD_LIST[rng.integers(len(_PAD_LIST))].copy()
    goal[2] = CRUISE_ALT
    if abs(goal[0]) < 700 and abs(goal[1]) < 700:
        goal[0] += float(rng.choice([-900.0, 900.0]))
    drone.goal = goal


def _step(sim: SimState) -> None:
    """시뮬레이션 틱 1회"""
    with sim.lock:
        drones = sim.drones
        dt = sim.dt

        # EVADING 드론에 대한 APF 배치 계산
        evading = [d for d in drones.values()
                   if d.flight_phase == FlightPhase.EVADING and d.goal is not None]
        if evading:
            apf_states = [APFState(d.position.copy(), d.velocity.copy(), d.drone_id)
                          for d in evading]
            goals_map  = {d.drone_id: d.goal.copy() for d in evading}
            forces = batch_compute_forces(apf_states, goals_map, _NFZ_OBSTACLES)
        else:
            forces = {}

        for drone in drones.values():
            _update(drone, forces, sim, dt)

        # 근접/충돌 감지 — SpatialHash O(N·k)
        if not hasattr(sim, '_spatial_hash'):
            sim._spatial_hash = SpatialHash(cell_size=50.0)
        if not hasattr(sim, '_active_conflict_pairs'):
            sim._active_conflict_pairs = set()

        sh = sim._spatial_hash
        sh.clear()
        for did, d in drones.items():
            if d.is_active:
                sh.insert(did, d.position)

        current_conflicts = set()
        for id_a, id_b, dist in sh.query_pairs_with_dist(50.0):
            pair = frozenset((id_a, id_b))
            if dist < 5.0:
                sim.collisions += 1
                drones[id_a].flight_phase = FlightPhase.FAILED
                drones[id_b].flight_phase = FlightPhase.FAILED
            elif dist < 10.0:
                if pair not in sim._active_conflict_pairs:
                    sim.near_misses += 1
                current_conflicts.add(pair)
            else:
                current_conflicts.add(pair)
                if pair not in sim._active_conflict_pairs:
                    sim.conflicts += 1
                    sim.advisories += 1
                    if drones[id_a].flight_phase == FlightPhase.ENROUTE:
                        drones[id_a].flight_phase = FlightPhase.EVADING
                    if drones[id_b].flight_phase == FlightPhase.ENROUTE:
                        drones[id_b].flight_phase = FlightPhase.EVADING
        sim._active_conflict_pairs = current_conflicts

        sim.t += dt

        # 틱 성능 기록
        _tick_end = time.perf_counter()
        if hasattr(sim, '_tick_start'):
            tick_ms = (_tick_end - sim._tick_start) * 1000
            sim.tick_times_ms.append(tick_ms)
            if len(sim.tick_times_ms) > sim.max_tick_history:
                sim.tick_times_ms = sim.tick_times_ms[-sim.max_tick_history:]
        sim._tick_start = _tick_end

        # 메트릭 수집 (매 1초 = 10틱)
        if int(sim.t * 10) % 10 == 0:
            sim.metrics.record(
                t=sim.t,
                drones=list(drones.values()),
                conflicts=sim.conflicts,
                collisions=sim.collisions,
                near_misses=sim.near_misses,
                advisories=sim.advisories,
                dt=dt,
            )

            # 위협 평가 (매 1초)
            evading_cnt = sum(1 for d in drones.values()
                              if d.flight_phase == FlightPhase.EVADING)
            failed_cnt = sum(1 for d in drones.values()
                             if d.flight_phase == FlightPhase.FAILED)
            low_bat_cnt = sum(1 for d in drones.values()
                              if d.battery_pct < 20 and d.is_active)
            wind_spd = float(np.linalg.norm(sim.wind[:2]))

            threats = sim.threat_engine.assess(
                collision_count=sim.collisions,
                near_miss_count=sim.near_misses,
                wind_speed=wind_spd,
                failure_count=failed_cnt,
                low_battery_count=low_bat_cnt,
                evading_count=evading_cnt,
            )
            sim.threat_matrix = sim.threat_engine.priority_matrix(threats)

            # 구역 업데이트
            for did, d in drones.items():
                if d.is_active:
                    sim.sector_mgr.update_drone_position(did, d.position)

            # SLA 체크
            active_cnt = sum(1 for d in drones.values() if d.is_active)
            cr_rate = 1.0 - (sim.collisions / max(sim.conflicts + sim.collisions, 1))
            violations = sim.sla_monitor.check(
                collision_rate=sim.collisions / max(active_cnt, 1),
                resolution_rate=cr_rate,
                near_miss_rate=sim.near_misses / max(active_cnt, 1),
            )
            if violations:
                sim.sla_violations = violations

            # 이벤트 타임라인 기록
            if sim.collisions > 0 and (not sim.timeline._events or
                    sim.timeline._events[-1].details.get("count") != sim.collisions):
                sim.timeline.add(
                    event_type="COLLISION",
                    t=sim.t,
                    severity="CRITICAL",
                    details={"count": sim.collisions},
                )
            if evading_cnt > 0:
                sim.timeline.add(
                    event_type="EVADING",
                    t=sim.t,
                    severity="HIGH" if evading_cnt >= 3 else "MEDIUM",
                    details={"count": evading_cnt},
                )


def _update(drone: DroneState, forces: dict, sim: SimState, dt: float) -> None:
    """드론 1기 상태 머신 업데이트"""
    profile = DRONE_PROFILES.get(drone.profile_name,
                                  DRONE_PROFILES["COMMERCIAL_DELIVERY"])

    # 배터리 소모 (비행 중)
    if drone.flight_phase not in (FlightPhase.GROUNDED, FlightPhase.FAILED):
        rate = 100.0 / (profile.endurance_min * 60.0 / dt)
        drone.battery_pct = max(0.0, drone.battery_pct - rate)
        if drone.battery_pct < 5.0 and drone.failure_type == FailureType.NONE:
            drone.failure_type = FailureType.BATTERY_CRITICAL
            drone.flight_phase = FlightPhase.LANDING

    phase = drone.flight_phase

    # ── 지상 대기
    if phase == FlightPhase.GROUNDED:
        if drone.battery_pct > 20.0 and sim.rng.random() < 0.015:
            drone.flight_phase = FlightPhase.TAKEOFF

    # ── 이륙
    elif phase == FlightPhase.TAKEOFF:
        if drone.position[2] < CRUISE_ALT - 2.0:
            drone.velocity = np.array([0.0, 0.0, 3.5])
            drone.position += drone.velocity * dt
        else:
            drone.position[2] = CRUISE_ALT
            drone.velocity    = np.zeros(3)
            drone.flight_phase = FlightPhase.ENROUTE

    # ── 비행
    elif phase == FlightPhase.ENROUTE:
        if drone.goal is None:
            drone.flight_phase = FlightPhase.LANDING
            return

        # NFZ 진입 직전 회피 전환
        lookahead = drone.position + drone.velocity * 3.0
        if _in_nfz(lookahead) or _in_nfz(drone.position):
            drone.flight_phase = FlightPhase.EVADING
            return

        diff = drone.goal - drone.position
        dist_xy = float(np.linalg.norm(diff[:2]))

        if dist_xy < 80.0:
            drone.flight_phase = FlightPhase.LANDING
        else:
            spd = profile.cruise_speed_ms
            norm = float(np.linalg.norm(diff))
            if norm < 0.1:
                drone.flight_phase = FlightPhase.LANDING
                return
            direction = diff / norm
            drone.velocity = direction * spd + sim.wind
            # 고도 유지
            drone.velocity[2] += (CRUISE_ALT - drone.position[2]) * 0.4
            drone.position += drone.velocity * dt
            drone.position[0] = float(np.clip(drone.position[0], -BOUNDS_M, BOUNDS_M))
            drone.position[1] = float(np.clip(drone.position[1], -BOUNDS_M, BOUNDS_M))
            drone.position[2] = float(np.clip(drone.position[2], ALT_MIN, ALT_MAX))
            drone.distance_flown_m += float(np.linalg.norm(drone.velocity[:2])) * dt
            if np.linalg.norm(drone.velocity[:2]) > 0.1:
                drone.heading = math.degrees(
                    math.atan2(float(drone.velocity[1]), float(drone.velocity[0]))
                )

    # ── APF 회피 기동
    elif phase == FlightPhase.EVADING:
        force = forces.get(drone.drone_id, np.zeros(3))
        drone.velocity = force_to_velocity(
            drone.velocity, force, dt, profile.max_speed_ms
        )
        drone.velocity += sim.wind
        drone.position += drone.velocity * dt
        drone.position[0] = float(np.clip(drone.position[0], -BOUNDS_M, BOUNDS_M))
        drone.position[1] = float(np.clip(drone.position[1], -BOUNDS_M, BOUNDS_M))
        drone.position[2] = float(np.clip(drone.position[2], ALT_MIN, ALT_MAX))
        drone.distance_flown_m += float(np.linalg.norm(drone.velocity[:2])) * dt

        # NFZ 밖이면 ENROUTE 복귀 (evade_end_s 타이머 또는 확률적 전환)
        should_exit = False
        if hasattr(drone, 'evade_end_s') and drone.evade_end_s is not None and sim.t >= drone.evade_end_s:
            should_exit = True
            drone.evade_end_s = None
        elif not _in_nfz(drone.position) and sim.rng.random() < 0.04 * dt * 10:
            should_exit = True

        if should_exit:
            if drone.goal is None:
                drone.flight_phase = FlightPhase.LANDING
            else:
                drone.flight_phase = FlightPhase.ENROUTE

    # ── 착륙
    elif phase == FlightPhase.LANDING:
        if drone.position[2] > 1.5:
            drone.velocity = np.array([0.0, 0.0, -2.5])
            drone.position += drone.velocity * dt
        else:
            drone.position[2] = 0.0
            drone.velocity    = np.zeros(3)
            drone.flight_phase = FlightPhase.GROUNDED
            drone.failure_type = FailureType.NONE
            # 배터리 부분 충전
            drone.battery_pct = min(100.0, drone.battery_pct + 40.0)
            _assign_goal(drone, sim.rng)

    # ── 공중 대기 (HOLDING) — Lost-Link Phase 1
    elif phase == FlightPhase.HOLDING:
        drone.velocity = np.zeros(3)
        # 5초 후 고도 상승(RTL 준비)으로 전이
        if not hasattr(drone, 'hold_start_s') or drone.hold_start_s is None:
            drone.hold_start_s = sim.t
        if sim.t > drone.hold_start_s + 5.0:
            drone.hold_start_s = None
            drone.flight_phase = FlightPhase.RTL

    # ── 귀환 (RTL)
    elif phase == FlightPhase.RTL:
        # 가장 가까운 착륙 패드로 귀환
        if drone.goal is None or drone.goal[2] > 0.1:
            nearest = min(_PAD_LIST, key=lambda p: float(np.linalg.norm(p[:2] - drone.position[:2])))
            drone.goal = nearest.copy()
            drone.goal[2] = 0.0

        diff = drone.goal - drone.position
        dist = float(np.linalg.norm(diff[:2]))
        if dist < 50.0:
            drone.flight_phase = FlightPhase.LANDING
        else:
            spd = profile.cruise_speed_ms * 0.7  # 감속 귀환
            norm = float(np.linalg.norm(diff))
            if norm < 0.1:
                drone.flight_phase = FlightPhase.LANDING
                return
            direction = diff / norm
            drone.velocity = direction * spd
            drone.position += drone.velocity * dt
            drone.position[0] = float(np.clip(drone.position[0], -BOUNDS_M, BOUNDS_M))
            drone.position[1] = float(np.clip(drone.position[1], -BOUNDS_M, BOUNDS_M))
            drone.position[2] = float(np.clip(drone.position[2], ALT_MIN, ALT_MAX))
            drone.distance_flown_m += float(np.linalg.norm(drone.velocity[:2])) * dt

    # ── 장애 발생
    elif phase == FlightPhase.FAILED:
        if drone.position[2] > 0.0:
            drone.position[2] = max(0.0, drone.position[2] - 1.5 * dt)

    drone.last_update_s = sim.t
    if drone.flight_phase not in (FlightPhase.GROUNDED, FlightPhase.FAILED):
        drone.flight_time_s += dt

    # 트레일 갱신
    trail = sim.trails.get(drone.drone_id, [])
    trail.append((float(drone.position[0]),
                  float(drone.position[1]),
                  float(drone.position[2])))
    if len(trail) > sim.trail_len:
        trail = trail[-sim.trail_len:]
    sim.trails[drone.drone_id] = trail


def _sim_loop(sim: SimState) -> None:
    """백그라운드 시뮬레이션 스레드 (20 Hz 기준, 속도 배율 적용)"""
    while True:
        if sim.running:
            spd = max(0.25, sim.speed_multiplier)
            for _ in range(max(1, int(spd))):
                _step(sim)
        time.sleep(0.05 / max(0.25, sim.speed_multiplier))
