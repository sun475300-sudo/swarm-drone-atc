"""
충돌 회피 어드바이저리 생성기
CLIMB / DESCEND / TURN_LEFT / TURN_RIGHT / HOLD / EVADE_APF 명령 결정 로직
"""
from __future__ import annotations
import uuid
import math
import numpy as np
from typing import TYPE_CHECKING

from src.airspace_control.comms.message_types import ResolutionAdvisory
from src.airspace_control.agents.drone_state import DroneState, FlightPhase
from src.airspace_control.utils.geo_math import bearing, closest_approach

if TYPE_CHECKING:
    pass


def new_advisory_id() -> str:
    return f"ADV-{uuid.uuid4().hex[:8].upper()}"


class AdvisoryGenerator:
    """
    두 드론 간 CPA(Closest Point of Approach) 예측 결과를 바탕으로
    충돌 회피 어드바이저리를 생성한다.

    우선순위 결정 규칙:
      1. 즉각적(cpa_t < 10s) → EVADE_APF
      2. FAILED/LANDING 드론 상대편 → HOLD
      3. 수직 분리가 경제적이면 → CLIMB/DESCEND (낮은 우선순위 드론이 CLIMB)
      4. 수평 교차/정면 → TURN_LEFT/TURN_RIGHT
      5. 동일 방향 추월 → HOLD (빠른 드론)
    """

    def __init__(
        self,
        separation_lateral_m: float = 50.0,
        separation_vertical_m: float = 15.0,
        climb_rate_ms: float = 3.0,
        turn_rate_deg_s: float = 15.0,
    ) -> None:
        self.lat_sep = separation_lateral_m
        self.vert_sep = separation_vertical_m
        self.climb_rate = climb_rate_ms
        self.turn_rate = turn_rate_deg_s

    # ── 공개 메서드 ──────────────────────────────────────────

    def generate(
        self,
        own: DroneState,
        threat: DroneState,
        cpa_dist_m: float,
        cpa_t_s: float,
        now: float = 0.0,
    ) -> ResolutionAdvisory:
        """
        주 어드바이저리 생성.

        Args:
            own:       어드바이저리를 받을 드론
            threat:    충돌 위협 드론
            cpa_dist_m: 예상 최근접 거리 (m)
            cpa_t_s:   최근접 도달 시간 (s)
            now:       현재 시뮬레이션 시각 (s)

        Returns:
            ResolutionAdvisory
        """
        adv_id = new_advisory_id()

        # 1. 즉각 회피
        if cpa_t_s < 10.0 or cpa_dist_m < 10.0:
            return self._make(adv_id, own.drone_id, threat.drone_id,
                              "EVADE_APF", 0.0,
                              max(15.0, cpa_t_s * 1.5), now)

        # 2. 상대가 FAILED/LANDING이면 내가 HOLD
        if threat.flight_phase in (FlightPhase.FAILED, FlightPhase.LANDING):
            return self._make(adv_id, own.drone_id, threat.drone_id,
                              "HOLD", cpa_t_s + 5.0,
                              min(cpa_t_s * 1.2 + 5.0, 120.0), now)

        # 3. 고도 분리로 해결 가능한지 검사
        dz = abs(float(own.position[2]) - float(threat.position[2]))
        needed_dz = self.vert_sep * 1.5
        if dz < needed_dz:
            mag = float(needed_dz - dz + 5.0)
            adv_type = self._vertical_choice(own, threat)
            dur = max(mag / self.climb_rate + 5.0, 15.0)
            return self._make(adv_id, own.drone_id, threat.drone_id,
                              adv_type, mag, min(dur, 120.0), now)

        # 4. 수평 기하로 결정
        geom = self._geometry(own, threat)
        if geom == "HEAD_ON":
            adv_type = "TURN_RIGHT"
            mag = min(cpa_t_s * self.turn_rate, 45.0)
        elif geom == "CROSSING":
            # 상대가 오른쪽에서 오면 내가 오른쪽으로 양보
            rel_bear = bearing(own.position, threat.position)
            own_hdg  = float(own.heading)
            angle    = (rel_bear - own_hdg) % 360.0
            adv_type = "TURN_LEFT" if angle < 180.0 else "TURN_RIGHT"
            mag = min(cpa_t_s * self.turn_rate, 45.0)
        else:  # OVERTAKE
            adv_type = "HOLD"
            mag = cpa_t_s + 5.0

        dur = float(np.clip(cpa_t_s * 1.2, 15.0, 120.0))
        return self._make(adv_id, own.drone_id, threat.drone_id,
                          adv_type, mag, dur, now)

    def generate_lost_link_sequence(
        self,
        drone: DroneState,
        loiter_s: float = 30.0,
        rtl_alt_m: float = 80.0,
        now: float = 0.0,
    ) -> list[ResolutionAdvisory]:
        """
        통신 두절(Lost-link) 프로토콜 3단계 어드바이저리 시퀀스.

        Phase 1: HOLD (loiter_s초 공중 대기)
        Phase 2: CLIMB → RTL 고도
        Phase 3: DESCEND → 착륙
        """
        cur_alt = float(drone.position[2]) if drone.position is not None else 60.0
        climb_mag = max(0.0, rtl_alt_m - cur_alt)
        climb_dur = climb_mag / max(self.climb_rate, 0.1) + 5.0

        return [
            self._make(new_advisory_id(), drone.drone_id, None,
                       "HOLD", loiter_s, loiter_s, now),
            self._make(new_advisory_id(), drone.drone_id, None,
                       "CLIMB", climb_mag, climb_dur, now + loiter_s),
            self._make(new_advisory_id(), drone.drone_id, None,
                       "DESCEND", rtl_alt_m, rtl_alt_m / max(self.climb_rate, 0.1) + 5.0,
                       now + loiter_s + climb_dur),
        ]

    # ── 내부 헬퍼 ────────────────────────────────────────────

    def _vertical_choice(self, own: DroneState, threat: DroneState) -> str:
        """어느 드론이 상승해야 하는지: 낮은 우선순위(큰 숫자)가 CLIMB"""
        from src.airspace_control.agents.drone_profiles import DRONE_PROFILES
        own_pri    = DRONE_PROFILES.get(own.profile_name,
                                         DRONE_PROFILES["COMMERCIAL_DELIVERY"]).priority
        threat_pri = DRONE_PROFILES.get(threat.profile_name,
                                         DRONE_PROFILES["COMMERCIAL_DELIVERY"]).priority
        # own 우선순위가 낮으면(숫자 크면) → own이 올라간다
        return "CLIMB" if own_pri >= threat_pri else "DESCEND"

    def _geometry(self, own: DroneState, threat: DroneState) -> str:
        """HEAD_ON / CROSSING / OVERTAKE 분류"""
        own_vel    = own.velocity[:2]
        threat_vel = threat.velocity[:2]
        own_spd    = float(np.linalg.norm(own_vel))
        threat_spd = float(np.linalg.norm(threat_vel))

        if own_spd < 0.5 or threat_spd < 0.5:
            return "CROSSING"

        own_hdg    = math.atan2(float(own_vel[1]),    float(own_vel[0]))
        threat_hdg = math.atan2(float(threat_vel[1]), float(threat_vel[0]))
        delta_hdg  = abs(math.degrees(own_hdg - threat_hdg)) % 360.0
        if delta_hdg > 180.0:
            delta_hdg = 360.0 - delta_hdg

        if delta_hdg > 150.0:
            return "HEAD_ON"
        if delta_hdg < 30.0:
            return "OVERTAKE"
        return "CROSSING"

    @staticmethod
    def _make(
        adv_id: str,
        target_id: str,
        conflict_pair_id: str | None,
        adv_type: str,
        magnitude: float,
        duration_s: float,
        timestamp_s: float,
    ) -> ResolutionAdvisory:
        return ResolutionAdvisory(
            advisory_id=adv_id,
            target_drone_id=target_id,
            advisory_type=adv_type,
            magnitude=magnitude,
            duration_s=duration_s,
            timestamp_s=timestamp_s,
            conflict_pair=conflict_pair_id,
        )
