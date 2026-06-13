"""GENESIS Phase 303 — 비행계획 신고/승인 신청서 자동 생성.

항공안전법 §127(비행승인) + 시행규칙 §306(비행계획 제출)에 따른
Drone One-Stop(드론 원스톱 민원서비스) 신청서 양식을 결정적으로 생성한다.

설계 원칙(`src/uast/intruder_response.py`와 동일): frozen dataclass + Enum.
입력은 생성자에서 검증하고(fail fast), 출력은 `to_dict()`/`to_text()`로 제공한다.

면책: 본 모듈은 양식 필드를 정리한 개발자 참고 도구이며, 운영자의 법적 신고 의무를
갈음하지 않는다. 실 신청은 Drone One-Stop(drone.onestop.go.kr)을 통해야 한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# ── 규제 임계값 (시행규칙·고시 기준) ──────────────────────────
MAX_VISUAL_ALTITUDE_M = 150.0       # 150m 초과 시 비행승인 필수
SAFETY_CERT_WEIGHT_KG = 25.0        # 자체중량 25kg 초과 시 안전성 인증 필요
MIN_LICENSE_GRADE = 1               # 1종(최상위) ~ 4종(최하위)
MAX_LICENSE_GRADE = 4


class FlightMethod(Enum):
    """비행 방식 — 가시권/비가시권 × 주간/야간."""

    VISUAL_DAY = "주간 가시권(VLOS)"
    VISUAL_NIGHT = "야간 가시권"
    BVLOS_DAY = "주간 비가시권(BVLOS)"
    BVLOS_NIGHT = "야간 비가시권"

    @property
    def is_night(self) -> bool:
        return self in (FlightMethod.VISUAL_NIGHT, FlightMethod.BVLOS_NIGHT)

    @property
    def is_bvlos(self) -> bool:
        return self in (FlightMethod.BVLOS_DAY, FlightMethod.BVLOS_NIGHT)


class ApprovalRequirement(Enum):
    """비행계획에서 추가로 충족해야 하는 승인·인증 요건."""

    ALTITUDE_OVER_150M = "고도 150m 초과 비행승인"
    SPECIAL_FLIGHT_APPROVAL = "야간·비가시 특별비행승인"
    SAFETY_CERTIFICATION = "자체중량 25kg 초과 안전성 인증"


@dataclass(frozen=True)
class Applicant:
    """신청인 정보."""

    name: str
    organization: str
    address: str
    phone: str


@dataclass(frozen=True)
class Aircraft:
    """비행장치 정보."""

    registration_number: str  # 신고번호
    model: str                # 형식
    weight_kg: float          # 자체중량
    purpose: str              # 용도

    def __post_init__(self) -> None:
        if self.weight_kg < 0:
            raise ValueError(f"자체중량은 0 이상이어야 합니다: {self.weight_kg}")


@dataclass(frozen=True)
class FlightPlan:
    """비행 계획 — 일시·구역·고도·방식."""

    start: str          # ISO8601 비행 시작
    end: str            # ISO8601 비행 종료
    center_lat: float   # 비행구역 중심 위도
    center_lon: float   # 비행구역 중심 경도
    radius_m: float     # 비행구역 반경
    altitude_max_m: float
    method: FlightMethod
    purpose: str

    def __post_init__(self) -> None:
        if not -90.0 <= self.center_lat <= 90.0:
            raise ValueError(f"위도 범위 오류: {self.center_lat}")
        if not -180.0 <= self.center_lon <= 180.0:
            raise ValueError(f"경도 범위 오류: {self.center_lon}")
        if self.radius_m <= 0:
            raise ValueError(f"비행구역 반경은 양수여야 합니다: {self.radius_m}")
        if self.altitude_max_m < 0:
            raise ValueError(f"최대고도는 0 이상이어야 합니다: {self.altitude_max_m}")
        # ISO8601 동일 포맷 문자열의 사전식 비교로 명백한 시각 역전을 차단한다.
        if self.start and self.end and self.end <= self.start:
            raise ValueError(
                f"종료 시각이 시작 시각보다 앞섭니다: {self.end} <= {self.start}"
            )


@dataclass(frozen=True)
class Pilot:
    """조종자 정보."""

    name: str
    license_grade: int       # 1~4종
    experience_hours: float

    def __post_init__(self) -> None:
        if not MIN_LICENSE_GRADE <= self.license_grade <= MAX_LICENSE_GRADE:
            raise ValueError(
                f"조종자 자격은 {MIN_LICENSE_GRADE}~{MAX_LICENSE_GRADE}종이어야 합니다: "
                f"{self.license_grade}"
            )
        if self.experience_hours < 0:
            raise ValueError(f"비행경력은 0 이상이어야 합니다: {self.experience_hours}")


@dataclass(frozen=True)
class FlightPlanSubmission:
    """완성된 비행계획 승인 신청서."""

    applicant: Applicant
    aircraft: Aircraft
    plan: FlightPlan
    pilot: Pilot
    requirements: tuple[ApprovalRequirement, ...]

    def to_dict(self) -> dict:
        """양식 필드를 한국어 라벨 dict로 반환 (JSON 직렬화 가능)."""
        return {
            "신청인": {
                "성명": self.applicant.name,
                "기관": self.applicant.organization,
                "주소": self.applicant.address,
                "연락처": self.applicant.phone,
            },
            "비행장치": {
                "신고번호": self.aircraft.registration_number,
                "형식": self.aircraft.model,
                "자체중량_kg": self.aircraft.weight_kg,
                "용도": self.aircraft.purpose,
            },
            "비행계획": {
                "시작": self.plan.start,
                "종료": self.plan.end,
                "중심좌표": [self.plan.center_lat, self.plan.center_lon],
                "반경_m": self.plan.radius_m,
                "최대고도_m": self.plan.altitude_max_m,
                "비행방식": self.plan.method.value,
                "목적": self.plan.purpose,
            },
            "조종자": {
                "성명": self.pilot.name,
                "자격": f"{self.pilot.license_grade}종",
                "비행경력_h": self.pilot.experience_hours,
            },
            "승인요건": [r.value for r in self.requirements],
        }

    def to_text(self) -> str:
        """제출용 평문 양식."""
        lines = [
            "═" * 52,
            "비행계획 승인 신청서 (Drone One-Stop · 시행규칙 §306)",
            "═" * 52,
            f"[신청인] {self.applicant.name} / {self.applicant.organization}",
            f"         {self.applicant.address} · {self.applicant.phone}",
            f"[비행장치] 신고번호 {self.aircraft.registration_number}"
            f" · {self.aircraft.model} · {self.aircraft.weight_kg}kg"
            f" · {self.aircraft.purpose}",
            f"[비행] {self.plan.start} ~ {self.plan.end}",
            f"       중심({self.plan.center_lat}, {self.plan.center_lon})"
            f" 반경 {self.plan.radius_m}m · 최대고도 {self.plan.altitude_max_m}m",
            f"       방식 {self.plan.method.value} · 목적 {self.plan.purpose}",
            f"[조종자] {self.pilot.name}"
            f" · {self.pilot.license_grade}종 · {self.pilot.experience_hours}h",
            "─" * 52,
            "[추가 승인·인증 요건]",
        ]
        if self.requirements:
            lines += [f"  • {r.value}" for r in self.requirements]
        else:
            lines.append("  • 없음 (경량·주간·가시권·150m 이하)")
        lines.append("═" * 52)
        return "\n".join(lines)


def _derive_requirements(
    aircraft: Aircraft, plan: FlightPlan
) -> tuple[ApprovalRequirement, ...]:
    """비행장치·비행계획에서 추가 승인 요건을 결정적으로 도출."""
    reqs: list[ApprovalRequirement] = []
    if plan.altitude_max_m > MAX_VISUAL_ALTITUDE_M:
        reqs.append(ApprovalRequirement.ALTITUDE_OVER_150M)
    if plan.method.is_night or plan.method.is_bvlos:
        reqs.append(ApprovalRequirement.SPECIAL_FLIGHT_APPROVAL)
    if aircraft.weight_kg > SAFETY_CERT_WEIGHT_KG:
        reqs.append(ApprovalRequirement.SAFETY_CERTIFICATION)
    return tuple(reqs)


def build_flight_plan_submission(
    applicant: Applicant,
    aircraft: Aircraft,
    plan: FlightPlan,
    pilot: Pilot,
) -> FlightPlanSubmission:
    """검증된 입력으로 비행계획 승인 신청서를 생성한다."""
    requirements = _derive_requirements(aircraft, plan)
    return FlightPlanSubmission(
        applicant=applicant,
        aircraft=aircraft,
        plan=plan,
        pilot=pilot,
        requirements=requirements,
    )


if __name__ == "__main__":  # pragma: no cover — 데모 출력
    demo = build_flight_plan_submission(
        Applicant("홍길동", "SDACS 드론팀", "서울 강남구 테헤란로 1", "010-1234-5678"),
        Aircraft("K-2026-0001", "SDACS-Q4", 4.2, "연구·실증"),
        FlightPlan(
            "2026-07-01T09:00", "2026-07-01T11:00",
            37.5665, 126.9780, 300.0, 120.0,
            FlightMethod.VISUAL_DAY, "군집 비행 실증",
        ),
        Pilot("홍길동", 2, 150.0),
    )
    print(demo.to_text())
