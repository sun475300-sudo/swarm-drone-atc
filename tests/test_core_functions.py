"""
핵심 함수 단위 테스트 — _estimate_power_w, simulator_3d._update 상태 전이
"""
from __future__ import annotations

import numpy as np
import pytest

from src.airspace_control.agents.drone_state import (
    DroneState, FlightPhase, CommsStatus, FailureType,
)
from src.airspace_control.agents.drone_profiles import DRONE_PROFILES
from simulation.simulator import _estimate_power_w

pytestmark = pytest.mark.unit


# ── _estimate_power_w 테스트 ──────────────────────────────────


class TestEstimatePowerW:
    """정밀 동력 모델 단위 테스트"""

    PROFILE = DRONE_PROFILES["COMMERCIAL_DELIVERY"]

    def test_hover_baseline(self):
        """속도 0, 기본 고도 → 호버 전력만"""
        p = _estimate_power_w(0.0, self.PROFILE)
        assert p > 0
        # 호버 전력 = battery_wh * 3600 / (endurance_min * 60)
        expected_hover = self.PROFILE.battery_wh * 3600.0 / (self.PROFILE.endurance_min * 60.0)
        # 고도 보정 포함이므 약간 높아야 함
        assert p >= expected_hover * 0.99

    def test_speed_increases_power(self):
        """속도 증가 → 전력 증가"""
        p0 = _estimate_power_w(0.0, self.PROFILE)
        p5 = _estimate_power_w(5.0, self.PROFILE)
        p15 = _estimate_power_w(15.0, self.PROFILE)
        assert p5 > p0
        assert p15 > p5

    def test_headwind_increases_power(self):
        """역풍 → 실효 속도 증가 → 전력 증가"""
        p_no_wind = _estimate_power_w(10.0, self.PROFILE, headwind_ms=0.0)
        p_headwind = _estimate_power_w(10.0, self.PROFILE, headwind_ms=10.0)
        assert p_headwind > p_no_wind

    def test_altitude_correction(self):
        """고도 증가 → 공기밀도 저하 → 전력 증가"""
        p_low = _estimate_power_w(10.0, self.PROFILE, altitude_m=30.0)
        p_high = _estimate_power_w(10.0, self.PROFILE, altitude_m=120.0)
        assert p_high > p_low

    def test_climb_adds_power(self):
        """상승 → 추가 전력"""
        p_level = _estimate_power_w(10.0, self.PROFILE, climb_rate_ms=0.0)
        p_climb = _estimate_power_w(10.0, self.PROFILE, climb_rate_ms=3.0)
        assert p_climb > p_level

    def test_descent_reduces_power(self):
        """하강 → 전력 약간 감소 (회수)"""
        p_level = _estimate_power_w(10.0, self.PROFILE, climb_rate_ms=0.0)
        p_desc = _estimate_power_w(10.0, self.PROFILE, climb_rate_ms=-2.0)
        assert p_desc < p_level

    def test_never_negative(self):
        """전력은 항상 0 이상"""
        p = _estimate_power_w(0.0, self.PROFILE, climb_rate_ms=-10.0)
        assert p >= 0.0

    def test_zero_endurance_safe(self):
        """endurance_min=0 프로파일 → ZeroDivision 없음"""
        from dataclasses import replace
        zero_profile = replace(self.PROFILE, endurance_min=0.0)
        p = _estimate_power_w(10.0, zero_profile)
        assert p > 0  # endurance_s가 max(0, 1.0)으로 클램핑됨

    def test_all_profiles(self):
        """모든 드론 프로파일에서 크래시 없이 계산"""
        for name, profile in DRONE_PROFILES.items():
            p = _estimate_power_w(profile.cruise_speed_ms, profile)
            assert p > 0, f"{name} profile failed"


# ── simulator_3d._update 상태 전이 테스트 ────────────────────


class TestSimulator3dUpdate:
    """simulator_3d._update 함수의 비행 단계 전이 테스트"""

    def _make_drone(self, phase=FlightPhase.GROUNDED, **kwargs):
        defaults = dict(
            drone_id="TEST_001",
            position=np.array([1000.0, 1000.0, 0.0]),
            velocity=np.zeros(3),
            profile_name="COMMERCIAL_DELIVERY",
            flight_phase=phase,
            battery_pct=80.0,
        )
        defaults.update(kwargs)
        d = DroneState(**defaults)
        d.goal = np.array([-3000.0, -3000.0, 60.0])
        return d

    def _make_sim(self):
        """최소한의 SimState mock"""
        from collections import deque

        class MinimalSim:
            wind = np.zeros(3)
            rng = np.random.default_rng(42)
            t = 10.0
            dt = 0.1
            trails = {}
            trail_len = 40
        return MinimalSim()

    def _call_update(self, drone, sim=None, forces=None):
        from visualization.simulator_3d import _update
        if sim is None:
            sim = self._make_sim()
        if forces is None:
            forces = {}
        _update(drone, forces, sim, sim.dt)

    def test_takeoff_reaches_cruise(self):
        """이륙 → 순항고도 도달 시 ENROUTE 전환"""
        drone = self._make_drone(
            phase=FlightPhase.TAKEOFF,
            position=np.array([1000.0, 1000.0, 59.0]),
        )
        self._call_update(drone)
        assert drone.flight_phase == FlightPhase.ENROUTE

    def test_enroute_near_goal_transitions_to_landing(self):
        """비행 중 목적지 근처 → LANDING 전환"""
        drone = self._make_drone(
            phase=FlightPhase.ENROUTE,
            position=np.array([-3000.0, -3000.0, 60.0]),
        )
        self._call_update(drone)
        assert drone.flight_phase == FlightPhase.LANDING

    def test_enroute_no_goal_transitions_to_landing(self):
        """goal=None → LANDING"""
        drone = self._make_drone(phase=FlightPhase.ENROUTE)
        drone.goal = None
        self._call_update(drone)
        assert drone.flight_phase == FlightPhase.LANDING

    def test_landing_touches_ground(self):
        """착륙 → 고도 0 도달 시 GROUNDED 전환"""
        drone = self._make_drone(
            phase=FlightPhase.LANDING,
            position=np.array([1000.0, 1000.0, 1.0]),
        )
        self._call_update(drone)
        assert drone.flight_phase == FlightPhase.GROUNDED
        assert drone.position[2] == 0.0

    def test_battery_critical_forces_landing(self):
        """배터리 4% → BATTERY_CRITICAL → LANDING"""
        drone = self._make_drone(
            phase=FlightPhase.ENROUTE,
            battery_pct=4.5,
            position=np.array([1000.0, 1000.0, 60.0]),
        )
        self._call_update(drone)
        assert drone.failure_type == FailureType.BATTERY_CRITICAL
        assert drone.flight_phase == FlightPhase.LANDING

    def test_grounded_no_battery_drain(self):
        """지상 대기 시 배터리 소모 없음"""
        drone = self._make_drone(phase=FlightPhase.GROUNDED, battery_pct=50.0)
        initial_bat = drone.battery_pct
        sim = self._make_sim()
        sim.rng = np.random.default_rng(999)  # 이륙 확률 0에 가깝도록
        # 여러 번 호출해도 배터리 유지
        for _ in range(10):
            self._call_update(drone, sim)
            if drone.flight_phase != FlightPhase.GROUNDED:
                break
        # 여전히 GROUNDED라면 배터리 변동 없음
        if drone.flight_phase == FlightPhase.GROUNDED:
            assert drone.battery_pct == initial_bat

    def test_holding_to_rtl(self):
        """HOLDING 5초 후 → RTL 전환"""
        drone = self._make_drone(
            phase=FlightPhase.HOLDING,
            position=np.array([1000.0, 1000.0, 60.0]),
        )
        drone.hold_start_s = 0.0  # 10초 전에 시작
        sim = self._make_sim()
        sim.t = 10.0
        self._call_update(drone, sim)
        assert drone.flight_phase == FlightPhase.RTL

    def test_failed_descends(self):
        """FAILED → 서서히 하강"""
        drone = self._make_drone(
            phase=FlightPhase.FAILED,
            position=np.array([1000.0, 1000.0, 50.0]),
        )
        initial_alt = drone.position[2]
        self._call_update(drone)
        assert drone.position[2] < initial_alt
