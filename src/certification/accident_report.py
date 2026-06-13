"""GENESIS Phase 307 — 사고 보고 양식(항철위/ARAIB 표준) 자동 작성.

항공안전법 §134(사고 보고 의무) + 항공·철도 사고조사에 관한 법률에 따른
사고/준사고 보고서를 시뮬레이션 장애 주입 로그(INJ Phase 6)에서 생성한다.

항철위 = 항공·철도사고조사위원회(ARAIB). 사고 발생 시 즉시 보고 의무가 있으며,
본 모듈은 시뮬 로그 → 표준 양식 변환과 심각도(사고/준사고/경미) 분류를 제공한다.

면책: 본 모듈은 보고 양식 작성을 보조하는 개발자 도구이며, 운영자의 법적 보고
의무를 갈음하지 않는다. 실 보고는 항철위·국토교통부 절차를 따라야 한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# ── 분류 임계값 ────────────────────────────────────────────
SERIOUS_PROPERTY_DAMAGE_KRW = 10_000_000  # 1천만원 초과 → 준사고 이상


class EventType(Enum):
    """장애·사고 유형 (INJ Phase 6 주입 유형과 정렬)."""

    COLLISION = "collision"            # 충돌
    NFZ_VIOLATION = "nfz_violation"    # 비행금지구역 진입
    MOTOR_FAIL = "motor_fail"          # 모터 고장
    GPS_LOSS = "gps_loss"              # GPS 손실
    COMM_LOSS = "comm_loss"            # 통신 두절
    BATTERY_CRITICAL = "battery_critical"  # 배터리 위급


class Severity(Enum):
    """사고 조사 심각도 구분."""

    ACCIDENT = "사고"                  # 사망·중상 또는 기체 파손/실종
    SERIOUS_INCIDENT = "준사고"        # 충돌·고가 손상 등 사고 직전
    INCIDENT = "경미한 사고"           # 운항 중 경미 이상


# 준사고(SERIOUS_INCIDENT)로 곧장 격상되는 고위험 유형.
# 충돌은 기체 파손 직결, NFZ 진입은 항공안전법상 준사고 사유에 해당한다.
_HIGH_RISK_EVENTS = frozenset({EventType.COLLISION, EventType.NFZ_VIOLATION})


@dataclass(frozen=True)
class Weather:
    """기상 조건."""

    wind_mps: float
    visibility_m: float

    def __post_init__(self) -> None:
        if self.wind_mps < 0:
            raise ValueError(f"풍속은 0 이상이어야 합니다: {self.wind_mps}")
        if self.visibility_m < 0:
            raise ValueError(f"시정은 0 이상이어야 합니다: {self.visibility_m}")


@dataclass(frozen=True)
class IncidentEvent:
    """단일 사고·준사고 사건."""

    timestamp: str
    lat: float
    lon: float
    altitude_m: float
    aircraft_id: str
    model: str
    event_type: EventType
    flight_phase: str
    deaths: int
    injuries: int
    property_damage_krw: int
    weather: Weather
    narrative: str

    def __post_init__(self) -> None:
        if not -90.0 <= self.lat <= 90.0:
            raise ValueError(f"위도 범위 오류: {self.lat}")
        if not -180.0 <= self.lon <= 180.0:
            raise ValueError(f"경도 범위 오류: {self.lon}")
        if self.deaths < 0:
            raise ValueError(f"사망자 수는 0 이상이어야 합니다: {self.deaths}")
        if self.injuries < 0:
            raise ValueError(f"부상자 수는 0 이상이어야 합니다: {self.injuries}")
        if self.property_damage_krw < 0:
            raise ValueError(f"재산피해는 0 이상이어야 합니다: {self.property_damage_krw}")


@dataclass(frozen=True)
class AccidentReport:
    """완성된 사고 보고서."""

    event: IncidentEvent
    severity: Severity
    immediate_report_required: bool

    def to_dict(self) -> dict:
        """항철위 양식 필드를 한국어 라벨 dict로 반환 (JSON 직렬화 가능)."""
        e = self.event
        return {
            "구분": self.severity.value,
            "즉시보고대상": self.immediate_report_required,
            "발생개요": {
                "일시": e.timestamp,
                "장소": [e.lat, e.lon],
                "고도_m": e.altitude_m,
                "비행단계": e.flight_phase,
                "유형": e.event_type.value,
                "경위": e.narrative,
            },
            "기체정보": {
                "신고부호": e.aircraft_id,
                "형식": e.model,
            },
            "피해상황": {
                "사망": e.deaths,
                "부상": e.injuries,
                "재산피해_원": e.property_damage_krw,
            },
            "기상": {
                "풍속_mps": e.weather.wind_mps,
                "시정_m": e.weather.visibility_m,
            },
        }

    def to_text(self) -> str:
        """제출용 평문 양식."""
        e = self.event
        obligation = "즉시 보고 대상" if self.immediate_report_required else "정기 보고"
        return "\n".join([
            "═" * 52,
            "항공·철도사고조사위원회(ARAIB) 사고 보고서",
            "═" * 52,
            f"[구분] {self.severity.value} · {obligation}",
            f"[발생] {e.timestamp} @ ({e.lat}, {e.lon}) 고도 {e.altitude_m}m",
            f"       단계 {e.flight_phase} · 유형 {e.event_type.value}",
            f"[기체] {e.aircraft_id} · {e.model}",
            f"[피해] 사망 {e.deaths} · 부상 {e.injuries}"
            f" · 재산 {e.property_damage_krw:,}원",
            f"[기상] 풍속 {e.weather.wind_mps}m/s · 시정 {e.weather.visibility_m}m",
            f"[경위] {e.narrative}",
            "═" * 52,
        ])


def classify_severity(event: IncidentEvent) -> Severity:
    """사망·부상·손상 정도로 사고 심각도를 결정적으로 분류한다."""
    if event.deaths > 0 or event.injuries > 0:
        return Severity.ACCIDENT
    if (
        event.event_type in _HIGH_RISK_EVENTS
        or event.property_damage_krw > SERIOUS_PROPERTY_DAMAGE_KRW
    ):
        return Severity.SERIOUS_INCIDENT
    return Severity.INCIDENT


def build_accident_report(event: IncidentEvent) -> AccidentReport:
    """사건에서 심각도를 분류하고 보고 의무를 판정해 보고서를 생성한다."""
    severity = classify_severity(event)
    # 항공안전법 §134 ① — 사고·준사고 모두 즉시 보고 대상. 경미한 사고는 정기 보고.
    immediate = severity in (Severity.ACCIDENT, Severity.SERIOUS_INCIDENT)
    return AccidentReport(
        event=event,
        severity=severity,
        immediate_report_required=immediate,
    )


def from_sim_log(records: list[dict]) -> list[IncidentEvent]:
    """시뮬 장애 주입 로그(dict 목록)를 IncidentEvent 목록으로 변환한다.

    누락 필드는 보고서 기본값(0/무풍/미상)으로 채운다. 알 수 없는 event_type은
    조용히 넘기지 않고 ValueError를 발생시킨다(시스템 경계 입력 검증).
    """
    events: list[IncidentEvent] = []
    for rec in records:
        raw_type = rec.get("event_type", "")
        try:
            event_type = EventType(raw_type)
        except ValueError as exc:
            raise ValueError(f"알 수 없는 사고 유형: {raw_type!r}") from exc
        events.append(
            IncidentEvent(
                timestamp=rec.get("timestamp", ""),
                lat=float(rec.get("lat", 0.0)),
                lon=float(rec.get("lon", 0.0)),
                altitude_m=float(rec.get("altitude_m", 0.0)),
                aircraft_id=rec.get("aircraft_id", "UNKNOWN"),
                model=rec.get("model", "UNKNOWN"),
                event_type=event_type,
                flight_phase=rec.get("flight_phase", "UNKNOWN"),
                deaths=int(rec.get("deaths", 0)),
                injuries=int(rec.get("injuries", 0)),
                property_damage_krw=int(rec.get("property_damage_krw", 0)),
                weather=Weather(
                    wind_mps=float(rec.get("wind_mps", 0.0)),
                    visibility_m=float(rec.get("visibility_m", 9999.0)),
                ),
                narrative=rec.get("narrative", ""),
            )
        )
    return events


if __name__ == "__main__":  # pragma: no cover — 데모 출력
    sample = IncidentEvent(
        timestamp="2026-07-01T10:15:30",
        lat=37.5665, lon=126.9780, altitude_m=80.0,
        aircraft_id="SDACS-07", model="SDACS-Q4",
        event_type=EventType.COLLISION, flight_phase="ENROUTE",
        deaths=0, injuries=0, property_damage_krw=3_000_000,
        weather=Weather(wind_mps=6.0, visibility_m=8000.0),
        narrative="군집 비행 중 2기 근접 → 회피 실패 접촉.",
    )
    print(build_accident_report(sample).to_text())
