"""어드바이저리 생명주기 관리"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import uuid

import numpy as np

from src.airspace_control.agents.drone_state import DroneState, FlightPhase
from src.airspace_control.comms.message_types import ResolutionAdvisory


def new_advisory_id() -> str:
    return f"ADV-{uuid.uuid4().hex[:8].upper()}"


class AdvisoryGenerator:
    """충돌 회피 어드바이저리를 생성한다.

    Parameters
    ----------
    separation_lateral_m : float
        최소 수평 이격 거리 (m).
    separation_vertical_m : float
        최소 수직 이격 거리 (m).
    """

    def __init__(
        self,
        separation_lateral_m: float = 50.0,
        separation_vertical_m: float = 15.0,
    ) -> None:
        self.separation_lateral_m = separation_lateral_m
        self.separation_vertical_m = separation_vertical_m

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------

    def generate(
        self,
        own: DroneState,
        threat: DroneState,
        cpa_dist_m: float,
        cpa_t_s: float,
        now: float,
    ) -> ResolutionAdvisory:
        """단일 충돌 쌍에 대한 어드바이저리를 생성한다.

        * threat 가 FAILED 상태이면 → HOLD
        * cpa_t_s < 10 s 이면 → EVADE_APF (긴급 APF 회피)
        * 그 외 → 수직 분리(CLIMB / DESCEND) 또는 수평 회전(TURN_LEFT / TURN_RIGHT)
        """
        # 1. 상대가 고장 상태이면 제자리 대기
        if threat.flight_phase == FlightPhase.FAILED:
            return self._build(
                target_id=own.drone_id,
                advisory_type="HOLD",
                magnitude=0.0,
                duration_s=max(cpa_t_s, 10.0),
                now=now,
                conflict_pair=threat.drone_id,
            )

        # 2. 긴급 근접 — APF 기반 회피
        if cpa_t_s < 10.0:
            return self._build(
                target_id=own.drone_id,
                advisory_type="EVADE_APF",
                magnitude=cpa_dist_m,
                duration_s=max(cpa_t_s * 2.0, 5.0),
                now=now,
                conflict_pair=threat.drone_id,
            )

        # 3. 일반 분리 — 수직 또는 수평 기동 선택
        dz = own.position[2] - threat.position[2]
        if abs(dz) < self.separation_vertical_m:
            # 수직 분리가 부족 → 상승 또는 하강
            advisory_type = "CLIMB" if dz >= 0 else "DESCEND"
            magnitude = self.separation_vertical_m - abs(dz)
        else:
            # 수평 회전
            rel = threat.position[:2] - own.position[:2]
            cross = own.velocity[0] * rel[1] - own.velocity[1] * rel[0]
            advisory_type = "TURN_RIGHT" if cross >= 0 else "TURN_LEFT"
            magnitude = self.separation_lateral_m - cpa_dist_m

        return self._build(
            target_id=own.drone_id,
            advisory_type=advisory_type,
            magnitude=max(magnitude, 1.0),
            duration_s=max(cpa_t_s, 5.0),
            now=now,
            conflict_pair=threat.drone_id,
        )

    def generate_lost_link_sequence(
        self,
        drone: DroneState,
        loiter_s: float,
        rtl_alt_m: float,
        now: float,
    ) -> list[ResolutionAdvisory]:
        """통신 두절 시 3단계 시퀀스를 생성한다.

        1. HOLD  — loiter_s 동안 현 위치 대기
        2. CLIMB — rtl_alt_m 까지 상승 (복귀 고도 확보)
        3. RTL   — 홈 위치로 복귀
        """
        seq: list[ResolutionAdvisory] = []

        # Phase 1: 제자리 대기
        seq.append(self._build(
            target_id=drone.drone_id,
            advisory_type="HOLD",
            magnitude=0.0,
            duration_s=loiter_s,
            now=now,
        ))

        # Phase 2: 복귀 고도로 상승
        climb_needed = max(rtl_alt_m - drone.position[2], 0.0)
        climb_duration = max(climb_needed / 3.0, 5.0)  # ~3 m/s 상승률 가정
        seq.append(self._build(
            target_id=drone.drone_id,
            advisory_type="CLIMB",
            magnitude=climb_needed,
            duration_s=climb_duration,
            now=now + loiter_s,
        ))

        # Phase 3: 홈 복귀
        home = getattr(drone, "home_position", drone.position)
        dist_home = float(np.linalg.norm(drone.position - home))
        rtl_duration = max(dist_home / 5.0, 10.0)  # ~5 m/s 순항 가정
        seq.append(self._build(
            target_id=drone.drone_id,
            advisory_type="RTL",
            magnitude=dist_home,
            duration_s=rtl_duration,
            now=now + loiter_s + climb_duration,
        ))

        return seq

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------

    @staticmethod
    def _build(
        target_id: str,
        advisory_type: str,
        magnitude: float,
        duration_s: float,
        now: float,
        conflict_pair: str | None = None,
    ) -> ResolutionAdvisory:
        return ResolutionAdvisory(
            advisory_id=new_advisory_id(),
            target_drone_id=target_id,
            advisory_type=advisory_type,
            magnitude=magnitude,
            duration_s=duration_s,
            timestamp_s=now,
            conflict_pair=conflict_pair,
        )
