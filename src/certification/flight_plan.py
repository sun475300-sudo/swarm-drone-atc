"""
비행계획 신고 양식 자동 생성 (GENESIS Phase 303).

드론 원스톱 민원서비스(drone.onestop.go.kr)의 비행승인·특별비행승인
신청서 양식을 시뮬레이션·운영 메타데이터로부터 결정적으로 생성한다.

법적 근거:
  - 항공안전법 제127조(초경량비행장치 비행승인)
  - 항공안전법 시행규칙 제308조(특별비행승인 — 야간/비가시권)
  - 항공안전법 시행규칙 제309조(비행승인 대상)

설계 원칙: 외부 의존성 없음(순수 dataclass + 표준 라이브러리). 모든 출력은
입력에 대해 결정적이며 단위 테스트로 검증한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

# ── 규제 임계값 (항공안전법 시행규칙) ──────────────────────────────────
# 최대이륙중량 25kg 초과 무인비행장치는 비행 시 비행승인 대상.
MAX_TAKEOFF_WEIGHT_APPROVAL_KG = 25.0
# 지표면 기준 150m 이상 고도 비행은 비행승인 대상.
ALTITUDE_APPROVAL_M = 150.0


@dataclass(frozen=True)
class Operator:
    """신청인(운영자) 정보."""

    name: str
    organization: str
    phone: str
    address: str


@dataclass(frozen=True)
class Aircraft:
    """비행장치(드론) 제원."""

    model: str
    category: str  # 멀티콥터 / 고정익 / 헬리콥터 등
    purpose: str  # 비행 목적(촬영·측량·방제·배송 등)
    weight_kg: float  # 자체중량
    max_takeoff_weight_kg: float  # 최대이륙중량
    registration_no: str  # 신고번호


@dataclass(frozen=True)
class Pilot:
    """조종자 정보."""

    name: str
    license_no: str
    phone: str


@dataclass(frozen=True)
class FlightPlan:
    """비행계획 — 일시·구역·고도·목적."""

    purpose: str
    area_name: str
    center_lat: float
    center_lon: float
    radius_m: float
    altitude_max_m: float
    start_date: date
    end_date: date
    is_night: bool = False  # 야간(일몰 후~일출 전) 비행
    is_bvlos: bool = False  # 비가시권(BVLOS) 비행
    in_controlled_airspace: bool = False  # 관제권/비행금지·제한구역 포함


@dataclass(frozen=True)
class Insurance:
    """보험 가입 정보."""

    insured: bool
    provider: str = ""
    policy_no: str = ""


@dataclass(frozen=True)
class ApplicationInput:
    """신청서 생성 입력 묶음."""

    operator: Operator
    aircraft: Aircraft
    pilot: Pilot
    flight_plan: FlightPlan
    insurance: Insurance = field(default_factory=lambda: Insurance(insured=False))


def required_approvals(plan: FlightPlan, aircraft: Aircraft) -> list[str]:
    """이 비행에 필요한 승인 유형 목록을 반환한다.

    - 비행승인: 최대이륙중량 25kg 초과 · 고도 150m 이상 · 관제권/금지구역.
    - 특별비행승인: 야간 또는 비가시권 비행.
    """
    approvals: list[str] = []

    needs_flight_approval = (
        aircraft.max_takeoff_weight_kg > MAX_TAKEOFF_WEIGHT_APPROVAL_KG
        or plan.altitude_max_m >= ALTITUDE_APPROVAL_M
        or plan.in_controlled_airspace
    )
    if needs_flight_approval:
        approvals.append("비행승인")

    if plan.is_night or plan.is_bvlos:
        approvals.append("특별비행승인")

    return approvals


def validate(data: ApplicationInput) -> list[str]:
    """신청 입력의 형식·범위 오류를 모두 수집해 반환한다(빈 리스트=유효).

    시스템 경계에서 입력을 검증한다(fail-fast 대신 전체 수집 — 사용자가 한 번에
    모든 누락 필드를 확인할 수 있도록).
    """
    errors: list[str] = []

    # 필수 텍스트 필드 누락 검사
    text_fields = {
        "신청인 성명": data.operator.name,
        "신청인 연락처": data.operator.phone,
        "신청인 주소": data.operator.address,
        "비행장치 모델": data.aircraft.model,
        "비행장치 신고번호": data.aircraft.registration_no,
        "조종자 성명": data.pilot.name,
        "조종자 자격번호": data.pilot.license_no,
        "비행 구역명": data.flight_plan.area_name,
        "비행 목적": data.flight_plan.purpose,
    }
    for label, value in text_fields.items():
        if not value or not value.strip():
            errors.append(f"필수 항목 누락: {label}")

    # 중량 검증
    if data.aircraft.weight_kg <= 0:
        errors.append("자체중량은 0보다 커야 합니다")
    if data.aircraft.max_takeoff_weight_kg < data.aircraft.weight_kg:
        errors.append("최대이륙중량은 자체중량 이상이어야 합니다")

    # 좌표 범위 검증
    if not -90.0 <= data.flight_plan.center_lat <= 90.0:
        errors.append("위도는 -90~90 범위여야 합니다")
    if not -180.0 <= data.flight_plan.center_lon <= 180.0:
        errors.append("경도는 -180~180 범위여야 합니다")

    # 구역·고도 검증
    if data.flight_plan.radius_m <= 0:
        errors.append("비행 반경은 0보다 커야 합니다")
    if data.flight_plan.altitude_max_m <= 0:
        errors.append("최대 비행고도는 0보다 커야 합니다")

    # 일정 검증
    if data.flight_plan.end_date < data.flight_plan.start_date:
        errors.append("비행 종료일은 시작일 이후여야 합니다")

    # 보험 일관성 검증
    if data.insurance.insured and not data.insurance.provider.strip():
        errors.append("보험 가입 시 보험사명은 필수입니다")

    return errors


def build_application(data: ApplicationInput) -> dict:
    """검증을 통과한 입력으로 구조화된 신청서(dict)를 생성한다.

    Raises:
        ValueError: 입력이 유효하지 않은 경우(검증 오류 목록 포함).
    """
    errors = validate(data)
    if errors:
        raise ValueError("신청서 입력 검증 실패: " + "; ".join(errors))

    approvals = required_approvals(data.flight_plan, data.aircraft)

    return {
        "양식": "드론 원스톱 비행승인 신청서",
        "법적근거": ["항공안전법 제127조", "항공안전법 시행규칙 제308조·제309조"],
        "필요승인": approvals,
        "신청인": {
            "성명": data.operator.name,
            "소속": data.operator.organization,
            "연락처": data.operator.phone,
            "주소": data.operator.address,
        },
        "비행장치": {
            "모델": data.aircraft.model,
            "종류": data.aircraft.category,
            "용도": data.aircraft.purpose,
            "자체중량_kg": data.aircraft.weight_kg,
            "최대이륙중량_kg": data.aircraft.max_takeoff_weight_kg,
            "신고번호": data.aircraft.registration_no,
        },
        "조종자": {
            "성명": data.pilot.name,
            "자격번호": data.pilot.license_no,
            "연락처": data.pilot.phone,
        },
        "비행계획": {
            "목적": data.flight_plan.purpose,
            "구역명": data.flight_plan.area_name,
            "중심좌표": [data.flight_plan.center_lat, data.flight_plan.center_lon],
            "반경_m": data.flight_plan.radius_m,
            "최대고도_m": data.flight_plan.altitude_max_m,
            "시작일": data.flight_plan.start_date.isoformat(),
            "종료일": data.flight_plan.end_date.isoformat(),
            "야간비행": data.flight_plan.is_night,
            "비가시권비행": data.flight_plan.is_bvlos,
            "관제권포함": data.flight_plan.in_controlled_airspace,
        },
        "보험": {
            "가입여부": data.insurance.insured,
            "보험사": data.insurance.provider,
            "증권번호": data.insurance.policy_no,
        },
    }


def render_markdown(application: dict) -> str:
    """구조화된 신청서를 사람이 읽을 수 있는 Markdown 양식으로 변환한다."""
    fp = application["비행계획"]
    ac = application["비행장치"]
    op = application["신청인"]
    pi = application["조종자"]
    ins = application["보험"]
    approvals = "·".join(application["필요승인"]) if application["필요승인"] else "해당 없음(승인 면제 대상)"

    lat, lon = fp["중심좌표"]
    yesno = lambda v: "예" if v else "아니오"

    return "\n".join(
        [
            f"# {application['양식']}",
            "",
            f"- **법적 근거**: {', '.join(application['법적근거'])}",
            f"- **필요 승인**: {approvals}",
            "",
            "## 1. 신청인",
            f"- 성명: {op['성명']}",
            f"- 소속: {op['소속']}",
            f"- 연락처: {op['연락처']}",
            f"- 주소: {op['주소']}",
            "",
            "## 2. 비행장치",
            f"- 모델: {ac['모델']} ({ac['종류']})",
            f"- 용도: {ac['용도']}",
            f"- 자체중량 / 최대이륙중량: {ac['자체중량_kg']}kg / {ac['최대이륙중량_kg']}kg",
            f"- 신고번호: {ac['신고번호']}",
            "",
            "## 3. 조종자",
            f"- 성명: {pi['성명']}",
            f"- 자격번호: {pi['자격번호']}",
            f"- 연락처: {pi['연락처']}",
            "",
            "## 4. 비행계획",
            f"- 목적: {fp['목적']}",
            f"- 구역: {fp['구역명']} (중심 {lat}, {lon} / 반경 {fp['반경_m']}m)",
            f"- 최대고도: {fp['최대고도_m']}m",
            f"- 기간: {fp['시작일']} ~ {fp['종료일']}",
            f"- 야간비행: {yesno(fp['야간비행'])} / 비가시권: {yesno(fp['비가시권비행'])} / 관제권포함: {yesno(fp['관제권포함'])}",
            "",
            "## 5. 보험",
            f"- 가입여부: {yesno(ins['가입여부'])}",
            f"- 보험사 / 증권번호: {ins['보험사'] or '-'} / {ins['증권번호'] or '-'}",
            "",
        ]
    )
