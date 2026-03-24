"""어드바이저리 생명주기 관리"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import uuid

import numpy as np


def new_advisory_id() -> str:
    return f"ADV-{uuid.uuid4().hex[:8].upper()}"


class AdvisoryGenerator:
    """충돌 예측 결과를 받아 ResolutionAdvisory 를 생성한다.

    Parameters
    ----------
    separation_lateral_m:  횡방향 최소 이격 거리 (m)
    separation_vertical_m: 수직 최소 이격 거리 (m)
    urgent_cpa_threshold_s: 이 시간(초) 미만이면 EVADE_APF 발령
    """

    def __init__(
        self,
        separation_lateral_m: float = 50.0,
        separation_vertical_m: float = 15.0,
        urgent_cpa_threshold_s: float = 10.0,
    ) -> None:
        self.separation_lateral_m  = separation_lateral_m
        self.separation_vertical_m = separation_vertical_m
        self.urgent_cpa_threshold_s = urgent_cpa_threshold_s

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------

    def generate(
        self,
        own,
        threat,
        cpa_dist_m: float,
        cpa_t_s: float,
        now: float,
    ):
        """단일 충돌 위협에 대한 ResolutionAdvisory 를 생성한다.

        Parameters
        ----------
        own:       자기 드론 DroneState
        threat:    위협 드론 DroneState
        cpa_dist_m: 최근접점 거리 (m)
        cpa_t_s:   최근접점까지 남은 시간 (s)
        now:       현재 시뮬레이션 시각 (s)
        """
        from src.airspace_control.agents.drone_state import FlightPhase
        from src.airspace_control.comms.message_types import ResolutionAdvisory

        # 위협 드론이 FAILED 상태 → HOLD 로 대기
        if threat.flight_phase == FlightPhase.FAILED:
            return ResolutionAdvisory(
                advisory_id=new_advisory_id(),
                target_drone_id=own.drone_id,
                advisory_type="HOLD",
                magnitude=0.0,
                duration_s=30.0,
                timestamp_s=now,
                conflict_pair=threat.drone_id,
            )

        # 긴급 (CPA 시간 짧음) → APF 회피 기동
        if cpa_t_s < self.urgent_cpa_threshold_s:
            return ResolutionAdvisory(
                advisory_id=new_advisory_id(),
                target_drone_id=own.drone_id,
                advisory_type="EVADE_APF",
                magnitude=cpa_dist_m,
                duration_s=max(cpa_t_s * 2.0, 5.0),
                timestamp_s=now,
                conflict_pair=threat.drone_id,
            )

        # 일반 분리 기동 — 고도 차이를 기준으로 CLIMB / DESCEND 선택
        # 동고도인 경우 드론 ID 사전순으로 타이브레이킹 (쌍방 충돌 방지)
        own_z    = float(own.position[2])
        threat_z = float(threat.position[2])
        if own_z < threat_z or (own_z == threat_z and own.drone_id < threat.drone_id):
            advisory_type = "DESCEND"
            magnitude     = self.separation_vertical_m
        else:
            advisory_type = "CLIMB"
            magnitude     = self.separation_vertical_m

        return ResolutionAdvisory(
            advisory_id=new_advisory_id(),
            target_drone_id=own.drone_id,
            advisory_type=advisory_type,
            magnitude=magnitude,
            duration_s=max(cpa_t_s, 10.0),
            timestamp_s=now,
            conflict_pair=threat.drone_id,
        )

    def generate_lost_link_sequence(
        self,
        drone,
        loiter_s: float = 30.0,
        rtl_alt_m: float = 80.0,
        now: float = 0.0,
    ) -> list:
        """통신 두절(Lost-link) 표준 3단계 어드바이저리 시퀀스를 생성한다.

        단계:
          1. HOLD   — 현재 위치에서 제자리 체공 (loiter_s)
          2. CLIMB  — RTL 고도까지 상승
          3. RTL    — 이륙지점으로 복귀

        Returns
        -------
        list[ResolutionAdvisory]  길이 3
        """
        from src.airspace_control.comms.message_types import ResolutionAdvisory

        current_alt = float(drone.position[2])
        climb_needed = max(rtl_alt_m - current_alt, 0.0)

        seq = [
            # 1단계: 체공
            ResolutionAdvisory(
                advisory_id=new_advisory_id(),
                target_drone_id=drone.drone_id,
                advisory_type="HOLD",
                magnitude=0.0,
                duration_s=loiter_s,
                timestamp_s=now,
            ),
            # 2단계: RTL 고도까지 상승
            ResolutionAdvisory(
                advisory_id=new_advisory_id(),
                target_drone_id=drone.drone_id,
                advisory_type="CLIMB",
                magnitude=climb_needed,
                duration_s=climb_needed / 3.5 if climb_needed > 0 else 5.0,
                timestamp_s=now + loiter_s,
            ),
            # 3단계: 이륙지점 복귀
            ResolutionAdvisory(
                advisory_id=new_advisory_id(),
                target_drone_id=drone.drone_id,
                advisory_type="RTL",
                magnitude=0.0,
                duration_s=300.0,
                timestamp_s=now + loiter_s + 10.0,
            ),
        ]
        return seq
