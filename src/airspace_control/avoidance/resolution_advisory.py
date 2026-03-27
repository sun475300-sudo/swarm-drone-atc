"""어드바이저리 생명주기 관리 및 충돌 회피 어드바이저리 생성기"""
from __future__ import annotations
import math
import uuid
from typing import Optional

import numpy as np


def new_advisory_id() -> str:
    return f"ADV-{uuid.uuid4().hex[:8].upper()}"


class AdvisoryGenerator:
    """
    충돌 회피 어드바이저리 생성기.

    CPA 정보를 기반으로 기하학적 분류를 통해
    CLIMB / DESCEND / TURN_LEFT / TURN_RIGHT / HOLD / EVADE_APF 어드바이저리를 생성.

    Parameters
    ----------
    separation_lateral_m:  수평 최소 분리 기준 (m)
    separation_vertical_m: 수직 최소 분리 기준 (m)
    """

    CLIMB       = "CLIMB"
    DESCEND     = "DESCEND"
    TURN_LEFT   = "TURN_LEFT"
    TURN_RIGHT  = "TURN_RIGHT"
    HOLD        = "HOLD"
    EVADE_APF   = "EVADE_APF"
    RTL         = "RTL"

    # 회피 기동 어드바이저리 집합 (HOLD/RTL 제외)
    EVASION_TYPES: frozenset[str] = frozenset([CLIMB, DESCEND, TURN_LEFT, TURN_RIGHT, EVADE_APF])

    DEFAULT_CLIMB_M    = 20.0
    DEFAULT_TURN_DEG   = 30.0
    DEFAULT_DURATION_S = 30.0

    def __init__(
        self,
        separation_lateral_m: float = 50.0,
        separation_vertical_m: float = 15.0,
    ) -> None:
        self.sep_lat  = separation_lateral_m
        self.sep_vert = separation_vertical_m

    # ── 공개 API ──────────────────────────────────────────────

    def generate(
        self,
        target,
        threat,
        cpa_dist_m: float,
        cpa_t_s: float,
        now: float = 0.0,
        now_s: float | None = None,
    ):
        """
        기하학적 분류로 어드바이저리 유형 및 크기 결정.

        Parameters
        ----------
        target:     어드바이저리를 받을 드론 (낮은 우선순위)
        threat:     위협 드론 (높은 우선순위)
        cpa_dist_m: Closest Point of Approach 거리 (m)
        cpa_t_s:    CPA까지 남은 시간 (s)
        now:        현재 시각 (기본 파라미터)
        now_s:      현재 시각 (별칭, now보다 우선)
        """
        from src.airspace_control.comms.message_types import ResolutionAdvisory

        current_time = now_s if now_s is not None else now

        adv_type, magnitude = self._classify(target, threat, cpa_t_s)

        # 긴박도에 따른 유효 시간 조정
        if cpa_t_s < 10.0:
            duration = max(cpa_t_s * 3.0, 10.0)
        elif cpa_t_s < 30.0:
            duration = cpa_t_s * 2.0
        else:
            duration = self.DEFAULT_DURATION_S

        return ResolutionAdvisory(
            advisory_id=new_advisory_id(),
            target_drone_id=target.drone_id,
            advisory_type=adv_type,
            magnitude=magnitude,
            duration_s=float(duration),
            timestamp_s=current_time,
            conflict_pair=threat.drone_id,
        )

    def generate_lost_link_sequence(
        self,
        drone,
        loiter_s: float = 30.0,
        rtl_alt_m: float = 80.0,
        now: float = 0.0,
    ) -> list:
        """
        통신 두절(Lost-Link) 3단계 어드바이저리 시퀀스 생성.

        1. HOLD   — loiter_s 동안 현 위치 선회 대기
        2. CLIMB  — RTL 고도까지 상승
        3. RTL    — 귀환 비행 개시

        Returns
        -------
        list[ResolutionAdvisory]  길이 3
        """
        from src.airspace_control.comms.message_types import ResolutionAdvisory

        did = drone.drone_id

        hold = ResolutionAdvisory(
            advisory_id=new_advisory_id(),
            target_drone_id=did,
            advisory_type=self.HOLD,
            magnitude=loiter_s,
            duration_s=loiter_s,
            timestamp_s=now,
            conflict_pair=None,
        )

        climb = ResolutionAdvisory(
            advisory_id=new_advisory_id(),
            target_drone_id=did,
            advisory_type=self.CLIMB,
            magnitude=rtl_alt_m,
            duration_s=30.0,
            timestamp_s=now + loiter_s,
            conflict_pair=None,
        )

        rtl = ResolutionAdvisory(
            advisory_id=new_advisory_id(),
            target_drone_id=did,
            advisory_type=self.RTL,
            magnitude=0.0,
            duration_s=600.0,
            timestamp_s=now + loiter_s + 30.0,
            conflict_pair=None,
        )

        return [hold, climb, rtl]

    # ── 내부 분류 로직 ────────────────────────────────────────

    def _classify(self, target, threat, cpa_t_s: float) -> tuple[str, float]:
        """충돌 기하학에 따른 어드바이저리 유형 결정."""
        from src.airspace_control.agents.drone_state import FlightPhase
        from src.airspace_control.agents.drone_profiles import DRONE_PROFILES

        # 프로파일별 기동 크기 (없으면 기본값 사용)
        profile = DRONE_PROFILES.get(
            getattr(target, 'profile_name', ''), None
        )
        climb_m  = profile.avoidance_climb_m  if profile else self.DEFAULT_CLIMB_M
        turn_deg = profile.avoidance_turn_deg if profile else self.DEFAULT_TURN_DEG

        # 위협 드론이 FAILED 상태이면 HOLD
        if hasattr(threat, 'flight_phase') and threat.flight_phase == FlightPhase.FAILED:
            return self.HOLD, 0.0

        # 매우 긴박한 CPA (< 10s) → APF 위임
        if cpa_t_s < 10.0:
            return self.EVADE_APF, 0.0

        rel_pos = threat.position - target.position
        dz      = float(rel_pos[2])

        # 수직 분리: 수직 이격이 부족할 때 수직 기동 지시
        # dz = threat.z - target.z: 양수 → threat이 위(위협이 위), 음수 → threat이 아래
        # target은 threat 반대 방향으로 이동: 위협이 위 → 하강, 위협이 아래 → 상승
        if abs(dz) < self.sep_vert:
            if dz >= 0.0:
                return self.DESCEND, climb_m  # threat이 위 → target 하강
            else:
                return self.CLIMB, climb_m    # threat이 아래 → target 상승

        # 수평 기동 분류
        # 속도=0 (HOLDING 등) 이면 헤딩 미정 → EVADE_APF 위임
        spd_xy = math.hypot(float(target.velocity[0]), float(target.velocity[1]))
        if spd_xy < 0.1:
            return self.EVADE_APF, 0.0

        heading = math.atan2(target.velocity[1], target.velocity[0])
        bearing = math.atan2(rel_pos[1], rel_pos[0])
        angle_diff = _wrap_angle(bearing - heading)

        # angle_diff > 0: 위협이 우측 → 우회전
        # angle_diff <= 0: 위협이 좌측 → 좌회전
        # |angle_diff| < 30°(정면): 우회전 우선 (ICAO 관례)
        if angle_diff >= 0 or abs(angle_diff) < math.radians(30):
            return self.TURN_RIGHT, turn_deg
        return self.TURN_LEFT, turn_deg


def _wrap_angle(a: float) -> float:
    return ((a + math.pi) % (2 * math.pi)) - math.pi
