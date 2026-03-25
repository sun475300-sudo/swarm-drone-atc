"""
AdvisoryGenerator 포괄적 단위 테스트
_classify 로직의 모든 분기 커버 + _wrap_angle 테스트
"""
from __future__ import annotations

import math
import numpy as np
import pytest

from src.airspace_control.avoidance.resolution_advisory import (
    AdvisoryGenerator,
    _wrap_angle,
    new_advisory_id,
)
from src.airspace_control.agents.drone_state import DroneState, FlightPhase


def _make_drone(drone_id, pos, vel, phase=FlightPhase.ENROUTE, profile="COMMERCIAL_DELIVERY"):
    return DroneState(
        drone_id=drone_id,
        position=np.array(pos, dtype=float),
        velocity=np.array(vel, dtype=float),
        flight_phase=phase,
        profile_name=profile,
    )


class TestWrapAngle:
    def test_in_range(self):
        assert _wrap_angle(0.5) == pytest.approx(0.5)

    def test_positive_wrap(self):
        assert _wrap_angle(math.pi + 1.0) == pytest.approx(-math.pi + 1.0, abs=0.01)

    def test_negative_wrap(self):
        assert _wrap_angle(-math.pi - 1.0) == pytest.approx(math.pi - 1.0, abs=0.01)

    def test_exactly_pi(self):
        result = _wrap_angle(math.pi)
        assert -math.pi <= result <= math.pi

    def test_large_positive(self):
        result = _wrap_angle(5 * math.pi)
        assert -math.pi <= result <= math.pi


class TestAdvisoryGeneratorClassify:
    def setup_method(self):
        self.gen = AdvisoryGenerator(separation_lateral_m=50.0, separation_vertical_m=15.0)

    def test_vertical_close_threat_above_descend(self):
        """위협이 위에 있고 수직 분리 부족 → DESCEND"""
        target = _make_drone("T", [0, 0, 50], [10, 0, 0])
        threat = _make_drone("H", [0, 0, 60], [10, 0, 0])  # dz = 10 < 15
        adv = self.gen.generate(target, threat, cpa_dist_m=30.0, cpa_t_s=20.0)
        assert adv.advisory_type == AdvisoryGenerator.DESCEND

    def test_vertical_close_threat_below_climb(self):
        """위협이 아래에 있고 수직 분리 부족 → CLIMB"""
        target = _make_drone("T", [0, 0, 60], [10, 0, 0])
        threat = _make_drone("H", [0, 0, 50], [10, 0, 0])  # dz = -10
        adv = self.gen.generate(target, threat, cpa_dist_m=30.0, cpa_t_s=20.0)
        assert adv.advisory_type == AdvisoryGenerator.CLIMB

    def test_urgent_cpa_evade_apf(self):
        """CPA < 10s → EVADE_APF"""
        target = _make_drone("T", [0, 0, 50], [10, 0, 0])
        threat = _make_drone("H", [100, 0, 80], [10, 0, 0])
        adv = self.gen.generate(target, threat, cpa_dist_m=30.0, cpa_t_s=5.0)
        assert adv.advisory_type == AdvisoryGenerator.EVADE_APF

    def test_failed_threat_hold(self):
        """위협 드론이 FAILED → HOLD"""
        target = _make_drone("T", [0, 0, 50], [10, 0, 0])
        threat = _make_drone("H", [100, 0, 50], [0, 0, 0], phase=FlightPhase.FAILED)
        adv = self.gen.generate(target, threat, cpa_dist_m=30.0, cpa_t_s=20.0)
        assert adv.advisory_type == AdvisoryGenerator.HOLD

    def test_horizontal_turn_right_bearing_ahead(self):
        """위협이 전방 30도 이내 → TURN_RIGHT"""
        # target은 +x 방향으로 이동, 위협도 +x 약간 앞
        target = _make_drone("T", [0, 0, 0], [10, 0, 0])
        threat = _make_drone("H", [100, 5, 30], [10, 0, 0])  # dz=30 > 15, 거의 전방
        adv = self.gen.generate(target, threat, cpa_dist_m=30.0, cpa_t_s=40.0)
        assert adv.advisory_type in (AdvisoryGenerator.TURN_RIGHT, AdvisoryGenerator.TURN_LEFT)

    def test_horizontal_turn_left(self):
        """위협이 왼쪽 → TURN_LEFT"""
        # target은 +x 방향, 위협은 -y 방향 (왼쪽)
        target = _make_drone("T", [0, 0, 0], [10, 0, 0])
        threat = _make_drone("H", [50, -100, 30], [0, 0, 0])
        adv = self.gen.generate(target, threat, cpa_dist_m=30.0, cpa_t_s=40.0)
        assert adv.advisory_type == AdvisoryGenerator.TURN_LEFT

    def test_duration_urgent(self):
        """CPA < 10s → duration = max(cpa_t * 3, 10)"""
        target = _make_drone("T", [0, 0, 50], [10, 0, 0])
        threat = _make_drone("H", [100, 0, 80], [10, 0, 0])
        adv = self.gen.generate(target, threat, cpa_dist_m=30.0, cpa_t_s=5.0)
        assert adv.duration_s == pytest.approx(max(5.0 * 3, 10.0))

    def test_duration_moderate(self):
        """10 < CPA < 30 → duration = cpa_t * 2"""
        target = _make_drone("T", [0, 0, 50], [10, 0, 0])
        threat = _make_drone("H", [0, 0, 60], [10, 0, 0])
        adv = self.gen.generate(target, threat, cpa_dist_m=30.0, cpa_t_s=20.0)
        assert adv.duration_s == pytest.approx(40.0)

    def test_duration_relaxed(self):
        """CPA >= 30 → DEFAULT_DURATION_S"""
        target = _make_drone("T", [0, 0, 50], [10, 0, 0])
        threat = _make_drone("H", [0, 0, 60], [10, 0, 0])
        adv = self.gen.generate(target, threat, cpa_dist_m=30.0, cpa_t_s=50.0)
        assert adv.duration_s == pytest.approx(AdvisoryGenerator.DEFAULT_DURATION_S)

    def test_now_s_overrides_now(self):
        """now_s 파라미터가 now보다 우선"""
        target = _make_drone("T", [0, 0, 50], [10, 0, 0])
        threat = _make_drone("H", [0, 0, 60], [10, 0, 0])
        adv = self.gen.generate(target, threat, 30.0, 50.0, now=100.0, now_s=200.0)
        assert adv.timestamp_s == 200.0

    def test_advisory_fields(self):
        """어드바이저리 필드 검증"""
        target = _make_drone("T", [0, 0, 50], [10, 0, 0])
        threat = _make_drone("H", [0, 0, 60], [10, 0, 0])
        adv = self.gen.generate(target, threat, 30.0, 20.0)
        assert adv.target_drone_id == "T"
        assert adv.conflict_pair == "H"
        assert adv.advisory_id.startswith("ADV-")
        assert adv.magnitude > 0


class TestAdvisoryGeneratorLostLink:
    def setup_method(self):
        self.gen = AdvisoryGenerator()

    def test_three_phases(self):
        drone = _make_drone("D0", [0, 0, 60], [10, 0, 0])
        seq = self.gen.generate_lost_link_sequence(drone, loiter_s=30.0, rtl_alt_m=80.0, now=100.0)
        assert len(seq) == 3
        assert seq[0].advisory_type == AdvisoryGenerator.HOLD
        assert seq[1].advisory_type == AdvisoryGenerator.CLIMB
        assert seq[2].advisory_type == AdvisoryGenerator.RTL

    def test_timestamps_sequential(self):
        drone = _make_drone("D0", [0, 0, 60], [10, 0, 0])
        seq = self.gen.generate_lost_link_sequence(drone, loiter_s=30.0, now=0.0)
        assert seq[0].timestamp_s == 0.0
        assert seq[1].timestamp_s == 30.0
        assert seq[2].timestamp_s == 60.0

    def test_climb_magnitude_is_rtl_alt(self):
        drone = _make_drone("D0", [0, 0, 60], [10, 0, 0])
        seq = self.gen.generate_lost_link_sequence(drone, rtl_alt_m=120.0)
        assert seq[1].magnitude == pytest.approx(120.0)

    def test_conflict_pair_is_none(self):
        drone = _make_drone("D0", [0, 0, 60], [10, 0, 0])
        seq = self.gen.generate_lost_link_sequence(drone)
        for adv in seq:
            assert adv.conflict_pair is None


class TestNewAdvisoryId:
    def test_format(self):
        aid = new_advisory_id()
        assert aid.startswith("ADV-")
        assert len(aid) == 12  # "ADV-" + 8 hex chars

    def test_uniqueness(self):
        ids = {new_advisory_id() for _ in range(100)}
        assert len(ids) == 100
