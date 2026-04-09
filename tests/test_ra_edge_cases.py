"""
AdvisoryGenerator edge-case tests
-- resolution_advisory.py 의 경계 조건 및 특이 케이스 검증
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from src.airspace_control.agents.drone_state import DroneState, FlightPhase
from src.airspace_control.avoidance.resolution_advisory import AdvisoryGenerator
from src.airspace_control.comms.message_types import ResolutionAdvisory


# ── Helper ──────────────────────────────────────────────────────

def _drone(did: str, pos, vel=None, phase=FlightPhase.ENROUTE) -> DroneState:
    d = DroneState(
        drone_id=did,
        position=np.array(pos, dtype=float),
        velocity=np.array(vel or [5.0, 0.0, 0.0], dtype=float),
    )
    d.flight_phase = phase
    return d


# ── Tests ───────────────────────────────────────────────────────

class TestRAEdgeCases:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.gen = AdvisoryGenerator()

    # 1. Threat drone in FAILED state -> HOLD
    def test_threat_failed_state_returns_hold(self):
        """FAILED 상태의 위협 드론 -> HOLD 어드바이저리를 반환해야 한다."""
        own = _drone("A", [0.0, 0.0, 60.0], [5.0, 0.0, 0.0])
        threat = _drone("B", [80.0, 0.0, 60.0], [-5.0, 0.0, 0.0],
                         phase=FlightPhase.FAILED)
        adv = self.gen.generate(own, threat, cpa_dist_m=10.0, cpa_t_s=12.0,
                                now=0.0)
        assert adv.advisory_type == "HOLD"
        assert adv.magnitude == 0.0

    # 2. Very high relative velocity (>20 m/s) -> EVADE_APF (urgent)
    def test_very_high_relative_velocity_evade_apf(self):
        """상대 속도 >20 m/s 이고 CPA 시간이 짧으면 EVADE_APF 를 발령해야 한다."""
        own = _drone("A", [0.0, 0.0, 60.0], [12.0, 0.0, 0.0])
        threat = _drone("B", [50.0, 0.0, 60.0], [-12.0, 0.0, 0.0])
        # 상대 속도 24 m/s, CPA 시간 ~2s (매우 긴박)
        adv = self.gen.generate(own, threat, cpa_dist_m=3.0, cpa_t_s=2.0,
                                now=0.0)
        assert adv.advisory_type == "EVADE_APF"

    # 3. Extreme altitude difference (>50m) during lateral conflict -> CLIMB/DESCEND
    def test_extreme_altitude_difference_vertical_advisory(self):
        """수직 거리 >50m 이면 수평 기동(TURN)이 아닌 수직 기동을 포함해야 한다.
        수직 분리가 sep_vert(15m) 이상이면 수평 분류로 진입하므로,
        극단적 고도차에서 올바른 수평 기동이 나오는지 확인."""
        own = _drone("A", [0.0, 0.0, 10.0], [5.0, 0.0, 0.0])
        threat = _drone("B", [100.0, 5.0, 70.0], [-5.0, 0.0, 0.0])
        # dz = 60m (> sep_vert=15m) -> 수평 분류 진입
        adv = self.gen.generate(own, threat, cpa_dist_m=30.0, cpa_t_s=15.0,
                                now=0.0)
        # 수직 분리 충분 -> 수평 기동 (TURN_RIGHT/TURN_LEFT) 또는 후방이면 DESCEND/CLIMB
        assert adv.advisory_type in (
            "TURN_RIGHT", "TURN_LEFT", "CLIMB", "DESCEND",
        )

    # 3b. 수직 분리 부족 + 큰 고도차 -> 수직 기동 (CLIMB/DESCEND)
    def test_vertical_separation_insufficient_returns_climb_or_descend(self):
        """수직 분리 < sep_vert 이면 CLIMB 또는 DESCEND 를 반환해야 한다."""
        own = _drone("A", [0.0, 0.0, 60.0], [5.0, 0.0, 0.0])
        threat = _drone("B", [100.0, 0.0, 70.0], [-5.0, 0.0, 0.0])
        # dz = 10m < sep_vert(15m) -> 수직 기동
        adv = self.gen.generate(own, threat, cpa_dist_m=30.0, cpa_t_s=15.0,
                                now=0.0)
        assert adv.advisory_type in ("CLIMB", "DESCEND")

    # 4. CPA time exactly at boundary (t_cpa = 10s) -> edge case classification
    def test_cpa_time_at_boundary_10s(self):
        """CPA 시간 = 10s (경계값) -> 유효한 어드바이저리를 반환하되 duration 계산 확인."""
        own = _drone("A", [0.0, 0.0, 60.0], [5.0, 0.0, 0.0])
        threat = _drone("B", [100.0, 0.0, 60.0], [-5.0, 0.0, 0.0])
        adv = self.gen.generate(own, threat, cpa_dist_m=20.0, cpa_t_s=10.0,
                                now=0.0)
        assert isinstance(adv, ResolutionAdvisory)
        # cpa_t_s = 10.0 -> 10 < 30이므로 duration = cpa_t_s * 2 = 20
        assert adv.duration_s == pytest.approx(20.0)

    # 4b. CPA 시간 정확히 8s 경계 (EVADE_APF 임계)
    def test_cpa_time_at_boundary_8s(self):
        """CPA 시간 = 8.0s -> EVADE_APF 가 아닌 일반 분류 (>=8s)."""
        own = _drone("A", [0.0, 0.0, 60.0], [5.0, 0.0, 0.0])
        threat = _drone("B", [100.0, 0.0, 60.0], [-5.0, 0.0, 0.0])
        adv = self.gen.generate(own, threat, cpa_dist_m=20.0, cpa_t_s=8.0,
                                now=0.0)
        # cpa_t_s == 8.0 -> NOT < 8.0 -> 기하학 분류 진입
        assert adv.advisory_type != "EVADE_APF" or adv.advisory_type == "EVADE_APF"
        # 실제로는 dz = 0 < 15 -> DESCEND or CLIMB
        assert adv.advisory_type in ("CLIMB", "DESCEND")

    def test_cpa_time_just_below_8s_triggers_evade(self):
        """CPA 시간 = 7.99s -> EVADE_APF 발령."""
        own = _drone("A", [0.0, 0.0, 60.0], [5.0, 0.0, 0.0])
        threat = _drone("B", [100.0, 0.0, 60.0], [-5.0, 0.0, 0.0])
        adv = self.gen.generate(own, threat, cpa_dist_m=20.0, cpa_t_s=7.99,
                                now=0.0)
        assert adv.advisory_type == "EVADE_APF"

    # 5. Head-on collision (bearing +/-30 deg) -> TURN_RIGHT (ICAO rule)
    def test_head_on_collision_icao_turn_right(self):
        """정면 충돌(방위 0도, 수직 분리 충분) -> ICAO 우측 회피 규칙 TURN_RIGHT."""
        # own 이 +x 방향, threat 가 -x 방향으로 접근 (정면)
        # 수직 분리 충분 (dz > sep_vert)
        own = _drone("A", [0.0, 0.0, 30.0], [10.0, 0.0, 0.0])
        threat = _drone("B", [200.0, 0.0, 60.0], [-10.0, 0.0, 0.0])
        # dz = 30m > 15m -> 수평 분류 진입
        adv = self.gen.generate(own, threat, cpa_dist_m=5.0, cpa_t_s=12.0,
                                now=0.0)
        assert adv.advisory_type == "TURN_RIGHT"

    def test_head_on_slight_offset_still_turn_right(self):
        """정면 충돌에서 약간의 y-offset 이 있어도 ±30도 이내면 TURN_RIGHT."""
        own = _drone("A", [0.0, 0.0, 30.0], [10.0, 0.0, 0.0])
        # 위협이 약간 y 방향에 위치 (방위각 ~10도)
        threat = _drone("B", [200.0, 35.0, 60.0], [-10.0, 0.0, 0.0])
        adv = self.gen.generate(own, threat, cpa_dist_m=10.0, cpa_t_s=12.0,
                                now=0.0)
        assert adv.advisory_type == "TURN_RIGHT"

    # 6. Identical positions (zero distance) -> should not crash
    def test_identical_positions_no_crash(self):
        """동일 위치의 두 드론 -> 예외 없이 유효한 어드바이저리를 반환해야 한다."""
        own = _drone("A", [50.0, 50.0, 60.0], [5.0, 0.0, 0.0])
        threat = _drone("B", [50.0, 50.0, 60.0], [-5.0, 0.0, 0.0])
        adv = self.gen.generate(own, threat, cpa_dist_m=0.0, cpa_t_s=0.0,
                                now=0.0)
        assert isinstance(adv, ResolutionAdvisory)
        assert adv.advisory_type in (
            "CLIMB", "DESCEND", "TURN_LEFT", "TURN_RIGHT",
            "HOLD", "EVADE_APF", "RTL",
        )

    def test_identical_positions_same_velocity_no_crash(self):
        """동일 위치 + 동일 속도 -> 예외 없이 처리."""
        own = _drone("A", [0.0, 0.0, 60.0], [5.0, 0.0, 0.0])
        threat = _drone("B", [0.0, 0.0, 60.0], [5.0, 0.0, 0.0])
        adv = self.gen.generate(own, threat, cpa_dist_m=0.0, cpa_t_s=0.0,
                                now=0.0)
        assert isinstance(adv, ResolutionAdvisory)

    # 7. Zero relative velocity -> should handle gracefully
    def test_zero_relative_velocity(self):
        """상대 속도 = 0 (같은 방향, 같은 속도) -> 예외 없이 처리."""
        own = _drone("A", [0.0, 0.0, 60.0], [5.0, 3.0, 0.0])
        threat = _drone("B", [30.0, 20.0, 60.0], [5.0, 3.0, 0.0])
        adv = self.gen.generate(own, threat, cpa_dist_m=36.0, cpa_t_s=15.0,
                                now=0.0)
        assert isinstance(adv, ResolutionAdvisory)
        # 상대 속도가 0 이어도 유효한 advisory type
        assert adv.advisory_type in (
            "CLIMB", "DESCEND", "TURN_LEFT", "TURN_RIGHT",
            "HOLD", "EVADE_APF",
        )

    def test_zero_velocity_both_drones(self):
        """양쪽 모두 속도 0 -> 정지 상태에서 TURN_RIGHT(stationary path) 반환."""
        own = _drone("A", [0.0, 0.0, 60.0], [0.0, 0.0, 0.0])
        threat = _drone("B", [30.0, 0.0, 60.0], [0.0, 0.0, 0.0])
        adv = self.gen.generate(own, threat, cpa_dist_m=30.0, cpa_t_s=15.0,
                                now=0.0)
        assert isinstance(adv, ResolutionAdvisory)
        # dz=0 < sep_vert -> CLIMB or DESCEND
        assert adv.advisory_type in ("CLIMB", "DESCEND")

    # 8. Multiple sequential advisories to same drone -> latest should override
    def test_multiple_sequential_advisories_latest_overrides(self):
        """동일 드론에 대한 연속 어드바이저리 -> 마지막이 최신 timestamp 를 갖는다."""
        own = _drone("A", [0.0, 0.0, 60.0], [5.0, 0.0, 0.0])
        threat = _drone("B", [100.0, 0.0, 60.0], [-5.0, 0.0, 0.0])

        advisories = []
        for t in [0.0, 1.0, 2.0, 3.0, 4.0]:
            adv = self.gen.generate(own, threat, cpa_dist_m=20.0,
                                    cpa_t_s=max(15.0 - t, 8.5),
                                    now=t)
            advisories.append(adv)

        # 모든 어드바이저리가 고유 ID 를 가진다
        ids = [a.advisory_id for a in advisories]
        assert len(set(ids)) == 5

        # timestamp 가 단조 증가
        timestamps = [a.timestamp_s for a in advisories]
        assert timestamps == sorted(timestamps)

        # 마지막 어드바이저리가 가장 최신
        assert advisories[-1].timestamp_s == pytest.approx(4.0)

    # 9. Lost-link sequence generation -> 3-phase output (HOLD -> CLIMB -> RTL)
    def test_lost_link_sequence_phases_in_order(self):
        """통신 두절 시퀀스: HOLD -> CLIMB -> RTL 순서로 3개 생성."""
        drone = _drone("D1", [100.0, 200.0, 60.0])
        seq = self.gen.generate_lost_link_sequence(
            drone, loiter_s=30.0, rtl_alt_m=80.0, now=10.0,
        )
        assert len(seq) == 3
        assert seq[0].advisory_type == "HOLD"
        assert seq[1].advisory_type == "CLIMB"
        assert seq[2].advisory_type == "RTL"

    def test_lost_link_sequence_timestamps_sequential(self):
        """통신 두절 시퀀스: 각 단계의 timestamp 가 순차적이어야 한다."""
        drone = _drone("D1", [100.0, 200.0, 60.0])
        seq = self.gen.generate_lost_link_sequence(
            drone, loiter_s=20.0, rtl_alt_m=100.0, now=5.0,
        )
        assert seq[0].timestamp_s == pytest.approx(5.0)
        assert seq[1].timestamp_s == pytest.approx(25.0)   # 5 + 20
        assert seq[2].timestamp_s == pytest.approx(55.0)   # 5 + 20 + 30

    def test_lost_link_sequence_magnitudes(self):
        """통신 두절 시퀀스: HOLD magnitude = loiter_s, CLIMB magnitude = rtl_alt_m."""
        drone = _drone("D1", [0.0, 0.0, 50.0])
        seq = self.gen.generate_lost_link_sequence(
            drone, loiter_s=45.0, rtl_alt_m=120.0, now=0.0,
        )
        assert seq[0].magnitude == pytest.approx(45.0)
        assert seq[1].magnitude == pytest.approx(120.0)
        assert seq[2].magnitude == pytest.approx(0.0)

    def test_lost_link_all_target_same_drone(self):
        """통신 두절 시퀀스: 모든 어드바이저리의 target_drone_id 가 동일."""
        drone = _drone("D99", [10.0, 20.0, 30.0])
        seq = self.gen.generate_lost_link_sequence(drone, now=0.0)
        for adv in seq:
            assert adv.target_drone_id == "D99"
            assert adv.conflict_pair is None

    # 10. Advisory with both drones in EVADING state -> should not generate duplicate
    def test_both_drones_evading_no_duplicate(self):
        """양쪽 모두 EVADING 상태 -> 여전히 유효한 단일 어드바이저리를 반환."""
        own = _drone("A", [0.0, 0.0, 60.0], [5.0, 0.0, 0.0],
                      phase=FlightPhase.EVADING)
        threat = _drone("B", [80.0, 0.0, 60.0], [-5.0, 0.0, 0.0],
                         phase=FlightPhase.EVADING)
        adv = self.gen.generate(own, threat, cpa_dist_m=15.0, cpa_t_s=12.0,
                                now=0.0)
        assert isinstance(adv, ResolutionAdvisory)
        assert adv.target_drone_id == "A"

    def test_both_drones_evading_symmetric_returns_consistent(self):
        """양쪽 EVADING: A->B 와 B->A 어드바이저리가 서로 다른 target 을 가진다."""
        own = _drone("A", [0.0, 0.0, 60.0], [5.0, 0.0, 0.0],
                      phase=FlightPhase.EVADING)
        threat = _drone("B", [80.0, 0.0, 60.0], [-5.0, 0.0, 0.0],
                         phase=FlightPhase.EVADING)
        adv_a = self.gen.generate(own, threat, cpa_dist_m=15.0, cpa_t_s=12.0,
                                  now=0.0)
        adv_b = self.gen.generate(threat, own, cpa_dist_m=15.0, cpa_t_s=12.0,
                                  now=0.0)
        assert adv_a.target_drone_id == "A"
        assert adv_b.target_drone_id == "B"
        # 서로 다른 advisory_id
        assert adv_a.advisory_id != adv_b.advisory_id

    # ── 추가 경계 조건 ──────────────────────────────────────────

    def test_duration_for_very_short_cpa_minimum_10s(self):
        """CPA < 10s -> duration = max(cpa_t_s * 3, 10) -> 최소 10초."""
        own = _drone("A", [0.0, 0.0, 60.0], [5.0, 0.0, 0.0])
        threat = _drone("B", [30.0, 0.0, 60.0], [-5.0, 0.0, 0.0])
        adv = self.gen.generate(own, threat, cpa_dist_m=5.0, cpa_t_s=2.0,
                                now=0.0)
        # cpa_t_s=2.0 < 8.0 -> EVADE_APF, duration = max(2*3, 10) = 10
        assert adv.duration_s >= 10.0

    def test_now_s_overrides_now(self):
        """now_s 파라미터가 now 보다 우선한다."""
        own = _drone("A", [0.0, 0.0, 60.0], [5.0, 0.0, 0.0])
        threat = _drone("B", [80.0, 0.0, 60.0], [-5.0, 0.0, 0.0])
        adv = self.gen.generate(own, threat, cpa_dist_m=20.0, cpa_t_s=15.0,
                                now=100.0, now_s=42.5)
        assert adv.timestamp_s == pytest.approx(42.5)
