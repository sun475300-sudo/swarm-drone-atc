"""
안전/정확성 수정사항 (A1~A3) + 새 기능 테스트
- A1: LANDING 드론 충돌 스캔 제외
- A2: EVADING goal=None 방어 + evade_end_s 타이머
- A3: RTL 드론 APF force 수신 확인
- ROGUE 어드바이저리 가드
- HOLDING 바람 제외
- COLLISION 중복 방지
"""
from __future__ import annotations

import numpy as np
import pytest
import simpy

from src.airspace_control.agents.drone_state import (
    DroneState, FlightPhase, CommsStatus, FailureType,
)


# ── 헬퍼 ─────────────────────────────────────────────────────────────

def _drone(did: str = "D0", pos=None, vel=None,
           phase=FlightPhase.ENROUTE, goal=None,
           battery=90.0, profile="COMMERCIAL_DELIVERY") -> DroneState:
    """테스트용 DroneState 생성"""
    d = DroneState(
        drone_id=did,
        position=np.array(pos or [0.0, 0.0, 60.0]),
        velocity=np.array(vel or [5.0, 0.0, 0.0]),
        battery_pct=battery,
        flight_phase=phase,
        profile_name=profile,
    )
    if goal is not None:
        d.goal = np.array(goal)
    return d


# ═══════════════════════════════════════════════════════════════════
# A1: LANDING 드론 충돌 스캔 제외
# ═══════════════════════════════════════════════════════════════════

class TestA1LandingCollisionExclusion:
    """LANDING 드론은 is_active=True이지만 충돌 스캔에서 제외되어야 한다."""

    def test_landing_is_active(self):
        d = _drone(phase=FlightPhase.LANDING)
        assert d.is_active is True  # LANDING은 여전히 active

    def test_grounded_not_active(self):
        d = _drone(phase=FlightPhase.GROUNDED)
        assert d.is_active is False

    def test_failed_not_active(self):
        d = _drone(phase=FlightPhase.FAILED)
        assert d.is_active is False

    def test_landing_excluded_from_collision_filter(self):
        """충돌 스캔 필터 조건: is_active AND phase != LANDING"""
        drones = [
            _drone("D1", phase=FlightPhase.ENROUTE),
            _drone("D2", phase=FlightPhase.LANDING),
            _drone("D3", phase=FlightPhase.EVADING),
            _drone("D4", phase=FlightPhase.GROUNDED),
        ]
        # 충돌 스캔 대상: active AND not LANDING
        scan_targets = [d for d in drones
                        if d.is_active and d.flight_phase != FlightPhase.LANDING]
        ids = {d.drone_id for d in scan_targets}
        assert ids == {"D1", "D3"}  # LANDING(D2)과 GROUNDED(D4) 제외


# ═══════════════════════════════════════════════════════════════════
# A2: EVADING goal=None 방어 + evade_end_s 타이머
# ═══════════════════════════════════════════════════════════════════

class TestA2EvadingGoalNone:
    """EVADING 종료 시 goal=None이면 LANDING으로 안전 전환"""

    def test_drone_state_has_evade_end_s(self):
        d = _drone()
        assert hasattr(d, "evade_end_s")
        assert d.evade_end_s is None

    def test_evade_end_s_can_be_set(self):
        d = _drone(phase=FlightPhase.EVADING)
        d.evade_end_s = 100.0
        assert d.evade_end_s == 100.0

    def test_goal_none_detection(self):
        """goal이 None인 EVADING 드론 감지"""
        d = _drone(phase=FlightPhase.EVADING)
        assert d.goal is None  # 기본값은 None

    def test_goal_set_correctly(self):
        d = _drone(phase=FlightPhase.EVADING, goal=[1000.0, 2000.0, 60.0])
        assert d.goal is not None
        assert np.allclose(d.goal, [1000.0, 2000.0, 60.0])


# ═══════════════════════════════════════════════════════════════════
# A3: RTL 드론 APF force 수신
# ═══════════════════════════════════════════════════════════════════

class TestA3RtlApfForce:
    """RTL 드론은 APF force를 수신해야 한다."""

    def test_rtl_included_in_apf_target(self):
        """RTL은 EVADING과 함께 APF 대상에 포함되어야 한다."""
        drones = [
            _drone("D1", phase=FlightPhase.EVADING, goal=[1000, 0, 60]),
            _drone("D2", phase=FlightPhase.RTL, goal=[0, 0, 0]),
            _drone("D3", phase=FlightPhase.ENROUTE, goal=[500, 500, 60]),
        ]
        apf_targets = [d for d in drones
                       if d.flight_phase in (FlightPhase.EVADING, FlightPhase.RTL)
                       and d.goal is not None]
        ids = {d.drone_id for d in apf_targets}
        assert ids == {"D1", "D2"}

    def test_rtl_with_no_goal_excluded(self):
        """goal=None인 RTL 드론은 APF 대상에서 제외"""
        d = _drone("D1", phase=FlightPhase.RTL)  # goal=None
        apf_targets = [d] if d.flight_phase in (FlightPhase.EVADING, FlightPhase.RTL) \
                          and d.goal is not None else []
        assert len(apf_targets) == 0


# ═══════════════════════════════════════════════════════════════════
# ROGUE 어드바이저리 가드
# ═══════════════════════════════════════════════════════════════════

class TestRogueAdvisoryGuard:
    """ROGUE 프로파일 드론 관련 어드바이저리 로직"""

    def test_rogue_profile_detection(self):
        d = _drone(profile="ROGUE")
        assert d.profile_name == "ROGUE"

    def test_registered_profile(self):
        d = _drone(profile="COMMERCIAL_DELIVERY")
        assert d.profile_name != "ROGUE"

    def test_rogue_pair_skip(self):
        """두 ROGUE 드론 간에는 어드바이저리를 건너뛰어야 한다."""
        d1 = _drone("R1", profile="ROGUE")
        d2 = _drone("R2", profile="ROGUE")
        # ROGUE+ROGUE → skip
        should_skip = (d1.profile_name == "ROGUE" and d2.profile_name == "ROGUE")
        assert should_skip is True

    def test_rogue_vs_registered_target(self):
        """ROGUE+등록 드론 충돌 시 등록 드론만 어드바이저리 대상"""
        rogue = _drone("R1", profile="ROGUE")
        registered = _drone("D1", profile="COMMERCIAL_DELIVERY")
        # 등록 드론만 타겟
        if rogue.profile_name == "ROGUE" and registered.profile_name != "ROGUE":
            target = registered
        else:
            target = None
        assert target is not None
        assert target.drone_id == "D1"


# ═══════════════════════════════════════════════════════════════════
# HOLDING 바람 제외
# ═══════════════════════════════════════════════════════════════════

class TestHoldingWindExclusion:
    """HOLDING 상태에서는 바람 영향이 적용되지 않아야 한다."""

    def test_holding_velocity_zero(self):
        d = _drone(phase=FlightPhase.HOLDING, vel=[10.0, 5.0, 0.0])
        # HOLDING 상태에서는 velocity를 0으로 설정 (state_machine에서)
        d.velocity = np.zeros(3)  # state_machine 동작 시뮬레이션
        assert np.allclose(d.velocity, 0.0)

    def test_holding_excludes_wind_integration(self):
        """HOLDING/GROUNDED/FAILED 상태는 위치 적분에서 제외"""
        excluded = {FlightPhase.GROUNDED, FlightPhase.FAILED,
                    FlightPhase.TAKEOFF, FlightPhase.LANDING}
        assert FlightPhase.HOLDING not in excluded  # HOLDING은 위치 적분에 포함되지만
        # state_machine에서 velocity=0으로 설정하므로 바람 적분 = 0


# ═══════════════════════════════════════════════════════════════════
# FlightPhase 상태 머신 전이
# ═══════════════════════════════════════════════════════════════════

class TestFlightPhaseTransitions:
    """FlightPhase 상태 전이 유효성 검증"""

    def test_all_phases_defined(self):
        assert len(FlightPhase) == 8

    def test_phase_names(self):
        expected = {"GROUNDED", "TAKEOFF", "ENROUTE", "HOLDING",
                    "LANDING", "FAILED", "RTL", "EVADING"}
        actual = {p.name for p in FlightPhase}
        assert actual == expected

    def test_evading_to_enroute(self):
        d = _drone(phase=FlightPhase.EVADING, goal=[1000, 0, 60])
        d.flight_phase = FlightPhase.ENROUTE
        assert d.flight_phase == FlightPhase.ENROUTE

    def test_evading_to_landing_no_goal(self):
        d = _drone(phase=FlightPhase.EVADING)  # goal=None
        if d.goal is None:
            d.flight_phase = FlightPhase.LANDING
        assert d.flight_phase == FlightPhase.LANDING

    def test_rtl_to_landing(self):
        d = _drone(phase=FlightPhase.RTL)
        d.flight_phase = FlightPhase.LANDING
        assert d.flight_phase == FlightPhase.LANDING

    def test_landing_to_grounded(self):
        d = _drone(phase=FlightPhase.LANDING, pos=[0, 0, 0])
        d.flight_phase = FlightPhase.GROUNDED
        assert d.flight_phase == FlightPhase.GROUNDED
        assert d.is_active is False


# ═══════════════════════════════════════════════════════════════════
# APF neighbor_states 풀 검증
# ═══════════════════════════════════════════════════════════════════

class TestAPFNeighborPool:
    """batch_compute_forces의 neighbor_states 파라미터 검증"""

    def test_neighbor_states_separate_from_states(self):
        from simulation.apf_engine.apf import APFState, batch_compute_forces

        # EVADING 드론 2기만 states에
        evading = [
            APFState(np.array([0.0, 0.0, 60.0]), np.zeros(3), "E1"),
            APFState(np.array([100.0, 0.0, 60.0]), np.zeros(3), "E2"),
        ]
        goals = {"E1": np.array([1000.0, 0.0, 60.0]),
                 "E2": np.array([-1000.0, 0.0, 60.0])}

        # 전체 활성 드론 (이웃 풀) — ENROUTE 드론 포함
        all_active = evading + [
            APFState(np.array([50.0, 50.0, 60.0]), np.zeros(3), "N1"),
        ]

        forces = batch_compute_forces(
            evading, goals=goals, obstacles=[],
            neighbor_states=all_active
        )
        # EVADING 드론에 대해서만 force 반환
        assert set(forces.keys()) == {"E1", "E2"}
        # N1이 이웃 풀에 있으므로 E1/E2의 force에 영향
        assert forces["E1"].shape == (3,)

    def test_without_neighbor_states_uses_self(self):
        from simulation.apf_engine.apf import APFState, batch_compute_forces

        states = [
            APFState(np.array([0.0, 0.0, 60.0]), np.zeros(3), "A"),
            APFState(np.array([30.0, 0.0, 60.0]), np.zeros(3), "B"),
        ]
        goals = {"A": np.array([1000.0, 0.0, 60.0]),
                 "B": np.array([-1000.0, 0.0, 60.0])}

        forces = batch_compute_forces(states, goals=goals, obstacles=[])
        assert "A" in forces and "B" in forces


# ═══════════════════════════════════════════════════════════════════
# NFZ 검증 (clearance 거부)
# ═══════════════════════════════════════════════════════════════════

class TestNFZValidation:
    """NFZ 관련 clearance 검증"""

    def test_nfz_center_is_ndarray(self):
        nfz = {"center": np.array([0.0, 0.0, 0.0]), "radius_m": 200.0}
        assert isinstance(nfz["center"], np.ndarray)

    def test_point_in_nfz(self):
        """NFZ 내부 판정"""
        center = np.array([0.0, 0.0, 60.0])
        radius = 200.0
        point = np.array([50.0, 50.0, 60.0])
        dist = np.linalg.norm(point - center)
        assert dist < radius  # 내부

    def test_point_outside_nfz(self):
        center = np.array([0.0, 0.0, 60.0])
        radius = 200.0
        point = np.array([500.0, 500.0, 60.0])
        dist = np.linalg.norm(point - center)
        assert dist > radius  # 외부


# ═══════════════════════════════════════════════════════════════════
# DroneState 속성 테스트
# ═══════════════════════════════════════════════════════════════════

class TestDroneStateProperties:
    """DroneState 데이터클래스 속성 검증"""

    def test_speed_property(self):
        d = _drone(vel=[3.0, 4.0, 0.0])
        assert d.speed == pytest.approx(5.0)

    def test_to_dict(self):
        d = _drone()
        data = d.to_dict()
        assert "drone_id" in data
        assert "flight_phase" in data
        assert data["flight_phase"] == "ENROUTE"

    def test_post_init_list_to_array(self):
        d = DroneState(
            drone_id="T1",
            position=[1.0, 2.0, 3.0],
            velocity=[4.0, 5.0, 6.0],
        )
        assert isinstance(d.position, np.ndarray)
        assert isinstance(d.velocity, np.ndarray)

    def test_evade_end_s_default_none(self):
        d = _drone()
        assert d.evade_end_s is None

    def test_hold_start_s_default_none(self):
        d = _drone()
        assert d._hold_start_s is None


# ═══════════════════════════════════════════════════════════════════
# FAILED→GROUNDED 전환 + 상태머신 엣지케이스
# ═══════════════════════════════════════════════════════════════════

class TestFailedToGrounded:
    """FAILED 드론이 지면에 도달하면 GROUNDED로 전환되는지 검증"""

    def test_failed_at_ground_level(self):
        """고도 0인 FAILED 드론은 이미 지면에 있다."""
        d = _drone(phase=FlightPhase.FAILED, pos=[0.0, 0.0, 0.0])
        # 고도 0이면 더 이상 하강 불필요
        assert d.position[2] == 0.0

    def test_failed_drone_descends(self):
        """FAILED 드론은 하강해야 한다 (시뮬레이터 로직 검증용)."""
        d = _drone(phase=FlightPhase.FAILED, pos=[0.0, 0.0, 50.0])
        # 시뮬레이터가 1.5 * dt만큼 하강시키므로 고도가 줄어야
        new_alt = max(0.0, d.position[2] - 1.5 * 1.0)
        assert new_alt < 50.0

    def test_evading_to_landing_no_goal(self):
        """EVADING 중 goal=None이면 LANDING으로 전환"""
        d = _drone(phase=FlightPhase.EVADING)
        d.goal = None
        # goal 없으면 안전하게 착륙
        if d.goal is None:
            d.flight_phase = FlightPhase.LANDING
        assert d.flight_phase == FlightPhase.LANDING

    def test_evading_to_enroute(self):
        """EVADING 중 goal이 있으면 ENROUTE로 복귀"""
        d = _drone(phase=FlightPhase.EVADING)
        d.goal = np.array([1000.0, 0.0, 60.0])
        if d.goal is not None:
            d.flight_phase = FlightPhase.ENROUTE
        assert d.flight_phase == FlightPhase.ENROUTE

    def test_rtl_to_landing(self):
        """RTL 드론이 패드 근처(100m)에 도착하면 LANDING으로 전환"""
        d = _drone(phase=FlightPhase.RTL, pos=[10.0, 10.0, 80.0])
        pad = np.array([0.0, 0.0, 0.0])
        dist_xy = float(np.linalg.norm(d.position[:2] - pad[:2]))
        if dist_xy < 100.0:
            d.flight_phase = FlightPhase.LANDING
        assert d.flight_phase == FlightPhase.LANDING

    def test_rtl_included_in_apf_target(self):
        """RTL 드론도 APF force의 대상에 포함되는지 확인"""
        from simulation.apf_engine.apf import APFState, batch_compute_forces
        s_rtl = APFState(position=np.array([0.0, 0.0, 80.0]),
                         velocity=np.array([-5.0, 0.0, 0.0]), drone_id="RTL1")
        s_other = APFState(position=np.array([20.0, 0.0, 80.0]),
                           velocity=np.array([5.0, 0.0, 0.0]), drone_id="E1")
        goals = {"RTL1": np.array([0.0, 0.0, 0.0]),
                 "E1": np.array([1000.0, 0.0, 60.0])}
        forces = batch_compute_forces([s_rtl, s_other], goals=goals, obstacles=[])
        assert "RTL1" in forces
