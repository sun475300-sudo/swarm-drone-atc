"""GENESIS Phase 303 — 비행계획 신고 양식 자동 생성 (Drone One-Stop export).

근거: 항공안전법 §127(비행승인)·§129·§131, 같은 법 시행규칙 §306(비행계획 제출),
드론 원스톱 민원서비스(drone.onestop.go.kr) 신청 항목.

면책: 본 모듈은 시뮬레이션 파라미터를 드론 원스톱 신청 양식 구조로 변환하는
**개발자 보조 도구**이며, 운영자의 법적 신고 의무를 갈음하지 않는다.
실 신청 시 최신 양식·국토교통부 고시를 확인해야 한다.

설계: 입력은 frozen dataclass로 받고, 양식은 결정적(deterministic)으로 생성한다.
어떤 승인이 필요한지는 순수 함수로 판정한다(테스트 가능).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

# 법정 상한 — Class G(비통제) 경계. 초과 시 통제공역 진입 → 비행승인 필요.
# 근거: AIRSPACE_CLASS_MAPPING.md (150m AGL = Class G 상한, L5 법정 상한).
MAX_UNCONTROLLED_ALTITUDE_M_AGL = 150.0


class FilingForm(Enum):
    """드론 원스톱 신청 양식 종류."""

    FLIGHT_APPROVAL = "비행승인신청서"          # §127 ① 관제권/제한구역/150m 초과
    SPECIAL_APPROVAL = "특별비행승인신청서"      # §129 ② 야간·비가시(BVLOS)
    AERIAL_PHOTOGRAPHY = "항공촬영허가신청서"    # 국방부 항공촬영 허가


@dataclass(frozen=True)
class Operator:
    """신청인 정보."""

    name: str               # 성명 또는 기관명
    contact: str            # 연락처
    address: str            # 주소


@dataclass(frozen=True)
class Aircraft:
    """기체 정보."""

    model: str                      # 기종
    registration: str               # 신고번호 (12kg 초과 신고 대상)
    empty_weight_kg: float          # 자체중량
    max_takeoff_weight_kg: float    # 최대이륙중량


@dataclass(frozen=True)
class FlightPlan:
    """비행 계획."""

    purpose: str                    # 비행 목적
    area_name: str                  # 비행 구역명
    start_ts: float                 # 시작 시각 (epoch seconds)
    end_ts: float                   # 종료 시각 (epoch seconds)
    max_altitude_m_agl: float       # 최대 고도 (m, AGL)
    controlled_airspace: bool = False   # 관제권 진입 여부
    restricted_area: bool = False       # 비행제한·금지구역 여부
    night: bool = False                 # 야간(일몰~일출) 비행
    bvlos: bool = False                 # 비가시권 비행
    aerial_photography: bool = False    # 항공촬영 동반


def requires_flight_approval(plan: FlightPlan) -> bool:
    """비행승인(§127 ①) 필요 여부.

    관제권·비행제한구역 진입 또는 150m AGL 초과 시 승인 대상.
    """
    return (
        plan.controlled_airspace
        or plan.restricted_area
        or plan.max_altitude_m_agl > MAX_UNCONTROLLED_ALTITUDE_M_AGL
    )


def requires_special_approval(plan: FlightPlan) -> bool:
    """특별비행승인(§129 ②) 필요 여부 — 야간 또는 비가시권."""
    return plan.night or plan.bvlos


def required_forms(plan: FlightPlan) -> list[FilingForm]:
    """비행 계획에 필요한 신청 양식 목록 (결정적 순서)."""
    forms: list[FilingForm] = []
    if requires_flight_approval(plan):
        forms.append(FilingForm.FLIGHT_APPROVAL)
    if requires_special_approval(plan):
        forms.append(FilingForm.SPECIAL_APPROVAL)
    if plan.aerial_photography:
        forms.append(FilingForm.AERIAL_PHOTOGRAPHY)
    return forms


@dataclass(frozen=True)
class FlightPlanFiling:
    """드론 원스톱 신청 양식 (export 대상)."""

    operator: Operator
    aircraft: Aircraft
    plan: FlightPlan
    # 직접 생성 금지 — build_filing()이 required_forms()로 채워준다.
    forms: tuple[FilingForm, ...]

    def to_dict(self) -> dict:
        """원스톱 신청 항목 구조의 dict 반환 (시각은 사람이 읽을 수 있는 ISO-8601 UTC)."""
        return {
            "신청양식": [f.value for f in self.forms],
            "신청인": {
                "성명": self.operator.name,
                "연락처": self.operator.contact,
                "주소": self.operator.address,
            },
            "기체": {
                "기종": self.aircraft.model,
                "신고번호": self.aircraft.registration,
                "자체중량_kg": self.aircraft.empty_weight_kg,
                "최대이륙중량_kg": self.aircraft.max_takeoff_weight_kg,
            },
            "비행계획": {
                "목적": self.plan.purpose,
                "구역": self.plan.area_name,
                "시작시각": _iso(self.plan.start_ts),
                "종료시각": _iso(self.plan.end_ts),
                "최대고도_m_AGL": self.plan.max_altitude_m_agl,
                "관제권": self.plan.controlled_airspace,
                "비행제한구역": self.plan.restricted_area,
                "야간": self.plan.night,
                "비가시권_BVLOS": self.plan.bvlos,
                "항공촬영": self.plan.aerial_photography,
            },
        }


def _iso(ts: float) -> str:
    """epoch 초 → ISO-8601 UTC 문자열 (신청서에 그대로 기재 가능)."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _validate(operator: Operator, aircraft: Aircraft, plan: FlightPlan) -> None:
    """입력 검증 — 빈 필수 항목·비정상 수치는 즉시 실패."""
    if not operator.name.strip():
        raise ValueError("신청인 성명(operator.name)은 필수입니다.")
    if not operator.contact.strip():
        raise ValueError("신청인 연락처(operator.contact)는 필수입니다.")
    if not operator.address.strip():
        raise ValueError("신청인 주소(operator.address)는 필수입니다.")
    if not aircraft.model.strip():
        raise ValueError("기체 기종(aircraft.model)은 필수입니다.")
    if not aircraft.registration.strip():
        raise ValueError("기체 신고번호(aircraft.registration)는 필수입니다.")
    if aircraft.empty_weight_kg <= 0:
        raise ValueError("자체중량(empty_weight_kg)은 0보다 커야 합니다.")
    if aircraft.max_takeoff_weight_kg < aircraft.empty_weight_kg:
        raise ValueError("최대이륙중량은 자체중량 이상이어야 합니다.")
    if plan.max_altitude_m_agl < 0:
        raise ValueError("최대고도(max_altitude_m_agl)는 음수일 수 없습니다.")
    if plan.end_ts <= plan.start_ts:
        raise ValueError("종료시각은 시작시각보다 뒤여야 합니다.")


def build_filing(
    operator: Operator,
    aircraft: Aircraft,
    plan: FlightPlan,
) -> FlightPlanFiling:
    """검증 후 필요한 양식을 채워 신청 양식 객체를 생성한다."""
    _validate(operator, aircraft, plan)
    return FlightPlanFiling(
        operator=operator,
        aircraft=aircraft,
        plan=plan,
        forms=tuple(required_forms(plan)),
    )
