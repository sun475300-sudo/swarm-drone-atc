"""
AdvisoryGenerator 단위 테스트
"""
from __future__ import annotations

import numpy as np
import pytest

from src.airspace_control.agents.drone_state import DroneState, FlightPhase
from src.airspace_control.avoidance.resolution_advisory import AdvisoryGenerator
from src.airspace_control.comms.message_types import ResolutionAdvisory


def _drone(did: str, pos, vel=None, phase=FlightPhase.ENROUTE) -> DroneState:
    d = DroneState(
        drone_id=did,
        position=np.array(pos, dtype=float),
        velocity=np.array(vel or [5.0, 0.0, 0.0], dtype=float),
    )
    d.flight_phase = phase
    return d


class TestAdvisoryGenerator:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.gen = AdvisoryGenerator()

    def test_generate_returns_advisory(self):
        own    = _drone("A", [0.0, 0.0, 60.0], [5.0, 0.0, 0.0])
        threat = _drone("B", [30.0, 0.0, 60.0], [-5.0, 0.0, 0.0])
        adv = self.gen.generate(own, threat, cpa_dist_m=20.0, cpa_t_s=5.0, now=0.0)
        assert isinstance(adv, ResolutionAdvisory)
        assert adv.target_drone_id == "A"

    def test_urgent_cpa_triggers_evade_apf(self):
        """CPA 시간 < 10s 이면 EVADE_APF 어드바이저리가 발령되어야 한다."""
        own    = _drone("A", [0.0, 0.0, 60.0])
        threat = _drone("B", [20.0, 0.0, 60.0], [-8.0, 0.0, 0.0])
        adv = self.gen.generate(own, threat, cpa_dist_m=5.0, cpa_t_s=3.0, now=0.0)
        assert adv.advisory_type == "EVADE_APF"

    def test_failed_partner_triggers_hold(self):
        """파트너가 FAILED 상태이면 HOLD를 발령해야 한다."""
        own    = _drone("A", [0.0, 0.0, 60.0])
        threat = _drone("B", [40.0, 0.0, 60.0], phase=FlightPhase.FAILED)
        adv = self.gen.generate(own, threat, cpa_dist_m=30.0, cpa_t_s=30.0, now=0.0)
        assert adv.advisory_type == "HOLD"

    def test_advisory_has_valid_duration(self):
        own    = _drone("A", [0.0, 0.0, 60.0])
        threat = _drone("B", [60.0, 30.0, 60.0], [0.0, -5.0, 0.0])
        adv = self.gen.generate(own, threat, cpa_dist_m=40.0, cpa_t_s=30.0, now=10.0)
        assert adv.duration_s > 0.0
        assert adv.timestamp_s == pytest.approx(10.0)

    def test_advisory_id_unique(self):
        own    = _drone("A", [0.0, 0.0, 60.0])
        threat = _drone("B", [60.0, 0.0, 60.0])
        ids = {
            self.gen.generate(own, threat, 30.0, 20.0, float(i)).advisory_id
            for i in range(5)
        }
        assert len(ids) == 5

    def test_lost_link_sequence_three_phases(self):
        """통신 두절 시퀀스는 3단계여야 한다."""
        drone = _drone("A", [100.0, 200.0, 60.0])
        drone.home_position = np.array([0.0, 0.0, 0.0])
        seq = self.gen.generate_lost_link_sequence(drone, loiter_s=30.0,
                                                    rtl_alt_m=80.0, now=0.0)
        assert len(seq) == 3
        types = [a.advisory_type for a in seq]
        assert "HOLD" in types
        assert "CLIMB" in types

    def test_zero_velocity_target_returns_evade_apf(self):
        """BUG-H3 회귀: velocity=0 드론에 대해 EVADE_APF를 반환해야 한다 (atan2(0,0) 오류 방지)"""
        own    = _drone("A", [0.0, 0.0, 60.0], [5.0, 0.0, 0.0])
        # 정지 드론 (velocity = [0,0,0])
        threat = _drone("B", [20.0, 0.0, 60.0], [0.0, 0.0, 0.0])
        adv = self.gen.generate(own, threat, cpa_dist_m=10.0, cpa_t_s=3.0, now=0.0)
        assert adv.advisory_type == "EVADE_APF", (
            f"정지 드론에 대해 EVADE_APF 기대, 실제: {adv.advisory_type}"
        )
