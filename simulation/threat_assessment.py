"""
실시간 위협 평가 엔진
=====================
개별 위협을 레벨 분류하고
복합 위협 상황에서 우선순위 매트릭스를 적용.

위협 레벨:
  LOW (1)      — 모니터링
  MEDIUM (2)   — 주의
  HIGH (3)     — 경고, 자동 대응 시작
  CRITICAL (4) — 즉시 대응

사용법:
    engine = ThreatAssessmentEngine()
    threats = engine.assess(drone_states, wind_speed=12.0, rogue_count=2)
    matrix = engine.priority_matrix(threats)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class ThreatLevel(IntEnum):
    """위협 레벨"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Threat:
    """단일 위협"""
    threat_type: str         # COLLISION, INTRUSION, WEATHER, FAILURE, COMMS_LOSS, NFZ_VIOLATION, BATTERY
    level: ThreatLevel
    source_ids: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)
    message: str = ""

    @property
    def score(self) -> float:
        """위협 점수 (높을수록 심각)"""
        base = int(self.level) * 25
        # 관련 드론 수 보너스
        n_drones = len(self.source_ids)
        return base + min(n_drones * 5, 25)


class ThreatAssessmentEngine:
    """
    실시간 위협 평가 엔진.

    다양한 위협 요소를 분석하여 레벨 분류하고
    복합 상황에서 우선순위를 결정한다.
    """

    def __init__(self) -> None:
        self._history: list[list[Threat]] = []

    def assess(
        self,
        *,
        collision_count: int = 0,
        near_miss_count: int = 0,
        rogue_count: int = 0,
        wind_speed: float = 0.0,
        failure_count: int = 0,
        comms_loss_count: int = 0,
        low_battery_count: int = 0,
        nfz_violation_count: int = 0,
        evading_count: int = 0,
    ) -> list[Threat]:
        """
        현재 상황 기반 위협 평가.

        Returns
        -------
        위협 목록 (점수 내림차순 정렬)
        """
        threats: list[Threat] = []

        # 충돌
        if collision_count > 0:
            level = ThreatLevel.CRITICAL
            threats.append(Threat(
                threat_type="COLLISION",
                level=level,
                details={"count": collision_count},
                message=f"충돌 {collision_count}건 발생",
            ))

        # 근접 경고
        if near_miss_count > 0:
            level = ThreatLevel.HIGH if near_miss_count >= 5 else ThreatLevel.MEDIUM
            threats.append(Threat(
                threat_type="NEAR_MISS",
                level=level,
                details={"count": near_miss_count},
                message=f"근접 경고 {near_miss_count}건",
            ))

        # 침입 드론
        if rogue_count > 0:
            level = ThreatLevel.CRITICAL if rogue_count >= 3 else ThreatLevel.HIGH
            threats.append(Threat(
                threat_type="INTRUSION",
                level=level,
                details={"rogue_count": rogue_count},
                message=f"침입 드론 {rogue_count}기 감지",
            ))

        # 기상
        if wind_speed > 0:
            if wind_speed >= 20:
                level = ThreatLevel.CRITICAL
            elif wind_speed >= 15:
                level = ThreatLevel.HIGH
            elif wind_speed >= 10:
                level = ThreatLevel.MEDIUM
            else:
                level = ThreatLevel.LOW
            threats.append(Threat(
                threat_type="WEATHER",
                level=level,
                details={"wind_speed": wind_speed},
                message=f"풍속 {wind_speed:.1f} m/s",
            ))

        # 장애
        if failure_count > 0:
            level = ThreatLevel.HIGH if failure_count >= 3 else ThreatLevel.MEDIUM
            threats.append(Threat(
                threat_type="FAILURE",
                level=level,
                details={"count": failure_count},
                message=f"장애 드론 {failure_count}기",
            ))

        # 통신 두절
        if comms_loss_count > 0:
            level = ThreatLevel.HIGH if comms_loss_count >= 5 else ThreatLevel.MEDIUM
            threats.append(Threat(
                threat_type="COMMS_LOSS",
                level=level,
                details={"count": comms_loss_count},
                message=f"통신 두절 {comms_loss_count}기",
            ))

        # 배터리 부족
        if low_battery_count > 0:
            level = ThreatLevel.HIGH if low_battery_count >= 5 else ThreatLevel.MEDIUM
            threats.append(Threat(
                threat_type="BATTERY",
                level=level,
                details={"count": low_battery_count},
                message=f"배터리 부족 {low_battery_count}기",
            ))

        # NFZ 위반
        if nfz_violation_count > 0:
            level = ThreatLevel.CRITICAL
            threats.append(Threat(
                threat_type="NFZ_VIOLATION",
                level=level,
                details={"count": nfz_violation_count},
                message=f"NFZ 위반 {nfz_violation_count}건",
            ))

        # 회피 기동 중
        if evading_count > 0:
            level = ThreatLevel.MEDIUM if evading_count < 5 else ThreatLevel.HIGH
            threats.append(Threat(
                threat_type="EVADING",
                level=level,
                details={"count": evading_count},
                message=f"회피 기동 {evading_count}기",
            ))

        # 점수순 정렬
        threats.sort(key=lambda t: t.score, reverse=True)
        self._history.append(threats)
        return threats

    def priority_matrix(self, threats: list[Threat]) -> dict[str, Any]:
        """
        복합 위협 우선순위 매트릭스.

        동시 다중 위협 시 전체 위험도 + 권장 조치 반환.
        """
        if not threats:
            return {
                "overall_level": ThreatLevel.LOW,
                "total_score": 0,
                "recommended_actions": [],
                "threats_by_level": {},
            }

        # 최고 위협 레벨
        max_level = max(t.level for t in threats)
        total_score = sum(t.score for t in threats)

        # 복합 위협 에스컬레이션: 3개 이상 HIGH → CRITICAL
        high_count = sum(1 for t in threats if t.level >= ThreatLevel.HIGH)
        if high_count >= 3 and max_level < ThreatLevel.CRITICAL:
            max_level = ThreatLevel.CRITICAL

        # 위협별 분류
        by_level: dict[str, list[str]] = {}
        for t in threats:
            lv_name = t.level.name
            if lv_name not in by_level:
                by_level[lv_name] = []
            by_level[lv_name].append(t.threat_type)

        # 권장 조치
        actions = self._recommend_actions(threats, max_level)

        return {
            "overall_level": max_level,
            "total_score": total_score,
            "recommended_actions": actions,
            "threats_by_level": by_level,
            "threat_count": len(threats),
        }

    def _recommend_actions(
        self,
        threats: list[Threat],
        overall_level: ThreatLevel,
    ) -> list[str]:
        """위협에 따른 권장 조치 목록"""
        actions = []
        types = {t.threat_type for t in threats}

        if "COLLISION" in types:
            actions.append("즉시 APF 척력 증가 + 분리간격 확대")
        if "INTRUSION" in types:
            actions.append("침입 드론 추적 + IntrusionAlert 브로드캐스트")
        if "WEATHER" in types:
            actions.append("APF_PARAMS_WINDY 전환 + 속도 제한")
        if "FAILURE" in types:
            actions.append("장애 드론 RTL 명령 + 주변 드론 회피")
        if "COMMS_LOSS" in types:
            actions.append("Lost-Link 프로토콜 발동 (HOLD→CLIMB→RTL)")
        if "BATTERY" in types:
            actions.append("배터리 부족 드론 우선 착륙 유도")
        if "NFZ_VIOLATION" in types:
            actions.append("NFZ 위반 드론 즉시 리라우팅")

        if overall_level >= ThreatLevel.CRITICAL:
            actions.insert(0, "전 드론 비상 모드 전환")

        return actions

    def overall_threat_level(self) -> ThreatLevel:
        """현재 전체 위협 레벨"""
        if not self._history:
            return ThreatLevel.LOW
        latest = self._history[-1]
        if not latest:
            return ThreatLevel.LOW
        return max(t.level for t in latest)

    def history_len(self) -> int:
        return len(self._history)

    def clear(self) -> None:
        self._history.clear()
