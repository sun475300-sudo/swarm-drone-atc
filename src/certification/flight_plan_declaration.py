"""Phase 303 — 드론 원스톱 비행승인 신청서 자동 생성.

시뮬레이션 비행 파라미터를 항공안전법 시행규칙 별지 제122호서식
(무인비행장치 비행승인신청서) 구조로 변환한다. 드론 원스톱
민원서비스(drone.onestop.go.kr) 제출용 초안 생성을 목표로 하며,
승인·특별승인 필요 여부를 규제 임계값 기준으로 결정적으로 판정한다.

규제 근거(요약):
- 비행승인: 관제권·비행금지구역 진입, 고도 150m(AGL) 초과,
  최대이륙중량 25kg 초과 시 필요(항공안전법 §127, 시행규칙 §308).
- 특별비행승인: 야간(일몰~일출) 또는 비가시권(BVLOS) 비행 시
  별도 필요(시행규칙 §312).
"""
from __future__ import annotations

from dataclasses import dataclass, field

# 규제 임계값 (named constants — magic number 금지)
MAX_ALTITUDE_M_AGL = 150.0
MAX_WEIGHT_KG = 25.0
FORM_ID = "별지 제122호서식"


@dataclass(frozen=True)
class Applicant:
    """신청인 정보."""

    name: str
    address: str
    phone: str


@dataclass(frozen=True)
class Aircraft:
    """비행장치 정보."""

    model: str
    registration: str
    purpose: str
    max_takeoff_weight_kg: float


@dataclass(frozen=True)
class FlightPlan:
    """비행계획(일시·구역·고도)."""

    date: str
    start_time: str
    end_time: str
    area_name: str
    center_lat: float
    center_lon: float
    radius_m: float
    max_altitude_m_agl: float


@dataclass(frozen=True)
class OperationProfile:
    """운용 형태 — 승인 판정 입력."""

    in_controlled_airspace: bool
    in_prohibited_zone: bool
    is_night: bool
    is_bvlos: bool


@dataclass(frozen=True)
class FlightPlanRequest:
    """비행승인 신청 요청 (시뮬 시나리오 → 신청서 입력)."""

    applicant: Applicant
    aircraft: Aircraft
    plan: FlightPlan
    profile: OperationProfile


@dataclass(frozen=True)
class ApprovalAssessment:
    """승인 필요 판정 결과."""

    approval_required: bool
    special_approval_required: bool
    reasons: list[str] = field(default_factory=list)


def assess_approval_requirement(request: FlightPlanRequest) -> ApprovalAssessment:
    """규제 임계값 기준 승인·특별승인 필요 여부를 결정적으로 판정."""
    reasons: list[str] = []

    if request.profile.in_controlled_airspace:
        reasons.append("관제권 내 비행 — 비행승인 필요")
    if request.profile.in_prohibited_zone:
        reasons.append("비행금지구역 내 비행 — 비행승인 필요")
    if request.plan.max_altitude_m_agl > MAX_ALTITUDE_M_AGL:
        reasons.append(
            f"최고고도 {request.plan.max_altitude_m_agl:.0f}m > 150m(AGL) — 비행승인 필요"
        )
    if request.aircraft.max_takeoff_weight_kg > MAX_WEIGHT_KG:
        reasons.append(
            f"최대이륙중량 {request.aircraft.max_takeoff_weight_kg:.0f}kg > 25kg — 비행승인 필요"
        )

    special_reasons: list[str] = []
    if request.profile.is_night:
        special_reasons.append("야간(일몰~일출) 비행 — 특별비행승인 필요")
    if request.profile.is_bvlos:
        special_reasons.append("비가시권(BVLOS) 비행 — 특별비행승인 필요")

    return ApprovalAssessment(
        approval_required=bool(reasons),
        special_approval_required=bool(special_reasons),
        reasons=reasons + special_reasons,
    )


def validate_request(request: FlightPlanRequest) -> list[str]:
    """필수 필드·값 범위 검증. 위반 사유 리스트 반환(빈 리스트=정상)."""
    errors: list[str] = []

    if not request.applicant.name.strip():
        errors.append("신청인 성명이 비어 있습니다")
    if not request.applicant.phone.strip():
        errors.append("신청인 연락처가 비어 있습니다")
    if not request.aircraft.registration.strip():
        errors.append("비행장치 신고번호가 비어 있습니다")

    if request.plan.radius_m <= 0:
        errors.append("비행구역 반경은 0보다 커야 합니다")
    if request.plan.max_altitude_m_agl < 0:
        errors.append("최고고도는 음수일 수 없습니다")
    if request.aircraft.max_takeoff_weight_kg <= 0:
        errors.append("최대이륙중량은 0보다 커야 합니다")
    if request.plan.end_time <= request.plan.start_time:
        errors.append("비행 종료시간은 시작시간보다 늦어야 합니다")

    return errors


def generate_declaration(request: FlightPlanRequest) -> dict:
    """별지 제122호서식 구조의 신청서 dict 생성. 검증 실패 시 ValueError."""
    errors = validate_request(request)
    if errors:
        raise ValueError("신청서 검증 실패: " + "; ".join(errors))

    assessment = assess_approval_requirement(request)
    return {
        "form_id": FORM_ID,
        "title": "무인비행장치 비행승인신청서",
        "신청인": {
            "성명": request.applicant.name,
            "주소": request.applicant.address,
            "연락처": request.applicant.phone,
        },
        "비행장치": {
            "형식": request.aircraft.model,
            "신고번호": request.aircraft.registration,
            "용도": request.aircraft.purpose,
            "최대이륙중량(kg)": request.aircraft.max_takeoff_weight_kg,
        },
        "비행계획": {
            "일자": request.plan.date,
            "시간": f"{request.plan.start_time}~{request.plan.end_time}",
            "구역": request.plan.area_name,
            "중심좌표": [request.plan.center_lat, request.plan.center_lon],
            "반경(m)": request.plan.radius_m,
            "최고고도(m,AGL)": request.plan.max_altitude_m_agl,
        },
        "승인판정": {
            "approval_required": assessment.approval_required,
            "special_approval_required": assessment.special_approval_required,
            "reasons": assessment.reasons,
        },
    }


def render_text(form: dict) -> str:
    """신청서 dict → 사람이 읽는 평문(결정적)."""
    p = form["신청인"]
    a = form["비행장치"]
    f = form["비행계획"]
    j = form["승인판정"]
    lat, lon = f["중심좌표"]

    lines = [
        f"[{form['form_id']}] {form['title']}",
        "─" * 40,
        "■ 신청인",
        f"  성명: {p['성명']}",
        f"  주소: {p['주소']}",
        f"  연락처: {p['연락처']}",
        "■ 비행장치",
        f"  형식: {a['형식']}  신고번호: {a['신고번호']}",
        f"  용도: {a['용도']}  최대이륙중량: {a['최대이륙중량(kg)']}kg",
        "■ 비행계획",
        f"  일자: {f['일자']}  시간: {f['시간']}",
        f"  구역: {f['구역']} (중심 {lat:.4f}, {lon:.4f}, 반경 {f['반경(m)']:.0f}m)",
        f"  최고고도: {f['최고고도(m,AGL)']:.0f}m (AGL)",
        "■ 승인판정",
        f"  비행승인 필요: {'예' if j['approval_required'] else '아니오'}",
        f"  특별비행승인 필요: {'예' if j['special_approval_required'] else '아니오'}",
    ]
    if j["reasons"]:
        lines.append("  사유:")
        lines.extend(f"    - {r}" for r in j["reasons"])
    return "\n".join(lines)
