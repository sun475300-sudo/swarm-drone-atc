"""Phase 303 (GENESIS): 비행계획 신고 양식 자동 생성 — Drone One-Stop 신청서 export.

한국 「항공안전법」 제127조(초경량비행장치 비행승인) 및 드론 원스톱 민원서비스
(drone.onestop.go.kr)의 비행승인·비행계획 신고 양식을 시뮬레이션 파라미터로부터
결정적으로 생성한다. 외부 API 호출 없이 입력 검증 + 승인 필요 여부 판정 +
JSON/텍스트 양식 export 만 수행한다 (production 등급의 결정적 구현).

판정 근거:
  - 관제권: 공항 표점 반경 9.3 km 이내 → 비행승인 필요
  - 고도: 지표/수면 150 m 초과 → 비행승인 필요
  - 비행금지구역(P-73 등) 내부 → 비행승인 필요
  - 비가시권(BVLOS) 또는 야간 비행 → 특별비행승인 필요
  - 사업용 전 기체 신고 / 비사업용 자체중량 12 kg 초과 → 기체 신고 대상
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# 비행승인 판정 임계값 (항공안전법 시행규칙 기준)
CONTROL_ZONE_RADIUS_M = 9_300.0  # 관제권: 공항 표점 반경 9.3 km
MAX_ALTITUDE_AGL_M = 150.0  # 지표/수면으로부터 150 m
# 기체 신고 기준 중량 (자체중량 기준; 사업용은 전 기체 신고)
WEIGHT_REPORT_THRESHOLD_KG = 12.0


@dataclass(frozen=True)
class FlightPlanApplicant:
    """비행계획 신청인(조종자/사업자) 정보."""

    name: str
    phone: str
    address: str
    is_business: bool = False  # 초경량비행장치사용사업 등록 여부
    business_reg_no: str = ""  # 사업자등록번호 (사업자에 한함)


@dataclass(frozen=True)
class FlightPlanAircraft:
    """비행에 사용하는 기체 정보."""

    model: str
    registration_no: str  # 신고번호 (미신고 시 빈 문자열)
    empty_weight_kg: float
    mtow_kg: float
    purpose: str = "교육/연구"  # 비행 목적


@dataclass(frozen=True)
class ControlZone:
    """관제권/비행금지구역 정의 (공항 표점 또는 금지구역 중심)."""

    name: str
    center_lat: float
    center_lon: float
    radius_m: float = CONTROL_ZONE_RADIUS_M
    is_prohibited: bool = False  # True면 비행금지구역(P-구역)


@dataclass(frozen=True)
class FlightPlan:
    """비행 정보 (구역·일시·고도·방식)."""

    area_name: str
    center_lat: float
    center_lon: float
    radius_m: float
    max_altitude_agl_m: float
    start: datetime
    end: datetime
    is_bvlos: bool = False  # 비가시권 비행
    is_night: bool = False  # 야간(일몰 후~일출 전) 비행


@dataclass(frozen=True)
class FilingDecision:
    """비행승인 필요 여부 판정 결과."""

    needs_approval: bool
    needs_special_approval: bool
    needs_aircraft_report: bool
    reasons: tuple[str, ...] = ()


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 위경도 좌표 사이의 대원거리(m)를 반환한다."""
    radius_earth_m = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return radius_earth_m * 2 * math.asin(math.sqrt(a))


def assess_filing(
    plan: FlightPlan,
    aircraft: FlightPlanAircraft,
    applicant: FlightPlanApplicant,
    control_zones: list[ControlZone] | None = None,
) -> FilingDecision:
    """비행계획에 대한 비행승인·특별승인·기체신고 필요 여부를 판정한다.

    관제권/금지구역과의 거리, 고도, 비행 방식, 기체 중량을 종합해 결정적으로 판정한다.
    """
    reasons: list[str] = []
    needs_approval = False
    needs_special_approval = False

    for zone in control_zones or []:
        distance = _haversine_m(
            plan.center_lat, plan.center_lon, zone.center_lat, zone.center_lon
        )
        # 비행 반경이 구역 경계와 겹치면 진입으로 간주
        if distance - plan.radius_m <= zone.radius_m:
            needs_approval = True
            label = "비행금지구역" if zone.is_prohibited else "관제권"
            reasons.append(f"{label} '{zone.name}' 진입 (거리 {distance:.0f} m)")

    if plan.max_altitude_agl_m > MAX_ALTITUDE_AGL_M:
        needs_approval = True
        reasons.append(
            f"비행고도 {plan.max_altitude_agl_m:.0f} m가 150 m를 초과"
        )

    if plan.is_bvlos:
        needs_special_approval = True
        reasons.append("비가시권(BVLOS) 비행 — 특별비행승인 대상")
    if plan.is_night:
        needs_special_approval = True
        reasons.append("야간 비행 — 특별비행승인 대상")

    # 사업용은 전 기체 신고, 비사업은 자체중량 12 kg 초과 시 신고 대상
    needs_aircraft_report = (
        applicant.is_business
        or aircraft.empty_weight_kg > WEIGHT_REPORT_THRESHOLD_KG
    )
    if needs_aircraft_report and not aircraft.registration_no:
        reasons.append("기체 신고번호 미등록 — 기체 신고 선행 필요")

    return FilingDecision(
        needs_approval=needs_approval,
        needs_special_approval=needs_special_approval,
        needs_aircraft_report=needs_aircraft_report,
        reasons=tuple(reasons),
    )


def _validate(
    plan: FlightPlan,
    aircraft: FlightPlanAircraft,
    applicant: FlightPlanApplicant,
) -> list[str]:
    """필수 입력값을 검증하고 누락/오류 목록을 반환한다."""
    errors: list[str] = []
    if not applicant.name:
        errors.append("신청인 성명이 비어 있음")
    if not applicant.phone:
        errors.append("신청인 연락처가 비어 있음")
    if applicant.is_business and not applicant.business_reg_no:
        errors.append("사업자는 사업자등록번호가 필요함")
    if not aircraft.model:
        errors.append("기체 모델명이 비어 있음")
    if aircraft.empty_weight_kg <= 0 or aircraft.mtow_kg <= 0:
        errors.append("기체 중량은 0보다 커야 함")
    if aircraft.mtow_kg < aircraft.empty_weight_kg:
        errors.append("최대이륙중량이 자체중량보다 작을 수 없음")
    if plan.radius_m <= 0:
        errors.append("비행 반경은 0보다 커야 함")
    if plan.max_altitude_agl_m <= 0:
        errors.append("비행 고도는 0보다 커야 함")
    if plan.end <= plan.start:
        errors.append("비행 종료 일시가 시작 일시보다 빠르거나 같음")
    return errors


def build_filing(
    plan: FlightPlan,
    aircraft: FlightPlanAircraft,
    applicant: FlightPlanApplicant,
    control_zones: list[ControlZone] | None = None,
) -> dict[str, Any]:
    """Drone One-Stop 비행승인 신청서 데이터를 결정적으로 구성한다.

    검증 오류가 있으면 ``ValueError`` 를 발생시킨다(시스템 경계 입력 검증).
    """
    errors = _validate(plan, aircraft, applicant)
    if errors:
        raise ValueError("비행계획 신고 양식 검증 실패: " + "; ".join(errors))

    decision = assess_filing(plan, aircraft, applicant, control_zones)
    duration_h = (plan.end - plan.start).total_seconds() / 3600.0

    return {
        "form_type": "drone_onestop_flight_approval",
        "applicant": {
            "name": applicant.name,
            "phone": applicant.phone,
            "address": applicant.address,
            "category": "사업자" if applicant.is_business else "개인",
            "business_reg_no": applicant.business_reg_no,
        },
        "aircraft": {
            "model": aircraft.model,
            "registration_no": aircraft.registration_no or "(미신고)",
            "empty_weight_kg": round(aircraft.empty_weight_kg, 2),
            "mtow_kg": round(aircraft.mtow_kg, 2),
            "purpose": aircraft.purpose,
        },
        "flight": {
            "area_name": plan.area_name,
            "center": [round(plan.center_lat, 6), round(plan.center_lon, 6)],
            "radius_m": round(plan.radius_m, 1),
            "max_altitude_agl_m": round(plan.max_altitude_agl_m, 1),
            "start": plan.start.isoformat(),
            "end": plan.end.isoformat(),
            "duration_h": round(duration_h, 2),
            "mode": "비가시권" if plan.is_bvlos else "가시권",
            "time_of_day": "야간" if plan.is_night else "주간",
        },
        "decision": {
            "needs_approval": decision.needs_approval,
            "needs_special_approval": decision.needs_special_approval,
            "needs_aircraft_report": decision.needs_aircraft_report,
            "reasons": list(decision.reasons),
        },
    }


def export_json(filing: dict[str, Any]) -> str:
    """신청서 데이터를 UTF-8 JSON 문자열로 직렬화한다."""
    return json.dumps(filing, ensure_ascii=False, indent=2, sort_keys=True)


def export_text(filing: dict[str, Any]) -> str:
    """신청서 데이터를 사람이 읽는 한국어 양식 텍스트로 변환한다."""
    a = filing["applicant"]
    ac = filing["aircraft"]
    fl = filing["flight"]
    d = filing["decision"]
    approval = "필요" if d["needs_approval"] else "불요"
    special = "필요" if d["needs_special_approval"] else "불요"
    lines = [
        "═══ 드론 원스톱 비행승인 신청서 ═══",
        "",
        "[신청인]",
        f"  성명/업체: {a['name']} ({a['category']})",
        f"  연락처:    {a['phone']}",
        f"  주소:      {a['address']}",
    ]
    if a["business_reg_no"]:
        lines.append(f"  사업자번호: {a['business_reg_no']}")
    lines += [
        "",
        "[기체]",
        f"  모델:      {ac['model']}",
        f"  신고번호:  {ac['registration_no']}",
        f"  중량:      자체 {ac['empty_weight_kg']} kg / 최대이륙 {ac['mtow_kg']} kg",
        f"  목적:      {ac['purpose']}",
        "",
        "[비행]",
        f"  구역:      {fl['area_name']} "
        f"(중심 {fl['center'][0]}, {fl['center'][1]} / 반경 {fl['radius_m']} m)",
        f"  고도:      지표 {fl['max_altitude_agl_m']} m AGL",
        f"  일시:      {fl['start']} ~ {fl['end']} ({fl['duration_h']} h)",
        f"  방식:      {fl['mode']} / {fl['time_of_day']}",
        "",
        "[판정]",
        f"  비행승인:     {approval}",
        f"  특별비행승인: {special}",
        f"  기체신고:     {'필요' if d['needs_aircraft_report'] else '불요'}",
    ]
    if d["reasons"]:
        lines.append("  사유:")
        lines += [f"   - {r}" for r in d["reasons"]]
    return "\n".join(lines)
