"""Phase 409 (ODYSSEY): 다국 BVLOS 규제 비교 — 한·미·EU·일 결정적 비교 모델.

GENESIS 302(SORA `soraAssess`)·408(ICAO 공역 클래스)·`faa_laanc`·`icao_doc10019`
규제 자산이 *단일 관할권* 적합성을 다룬 반면, 본 모듈은 4개 관할권의
BVLOS(가시권 밖, Beyond Visual Line of Sight) 운영 요건을 **횡단 비교**한다.
난수·외부 호출 없이 공개 규제 프레임워크를 정적 데이터로 모델링하고,
SDACS 운영 프로파일을 각 관할권 요건에 대조해 적합성 갭을 산정한다.

모델링 근거 (2026-06 기준 공개 프레임워크 스냅샷, 교육·시뮬레이션용·법률자문 아님):
  🇰🇷 KR — 항공안전법 §129 특별비행승인(BVLOS/야간) + K-드론시스템 + 기체신고/조종자격
  🇺🇸 US — FAA Part 107 §107.31 BVLOS waiver + BEYOND 프로그램 + Part 108(NPRM) + Remote ID(Part 89)
  🇪🇺 EU — EASA Specific 카테고리 + SORA(JARUS) + 운영 승인/LUC + Remote ID(Class C)
  🇯🇵 JP — 改正航空法 Level 4 + 第一種機体認証 + 一等無人航空機操縦士 + リモートID

가정 (명시): 고도 상한은 각 관할권 *기본* 값(특별승인·SORA 등급으로 변동 가능)을
모델 기준값으로 채택한다. 수치는 결정적 비교를 위한 참조값이며 권위 있는 법령 텍스트가 아니다.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, fields

# 관할권 코드 — ISO 3166-1 alpha-2 (EU 는 지역 블록 관용 코드)
JURISDICTIONS: tuple[str, ...] = ("KR", "US", "EU", "JP")

# 피트→미터 (FAA 400ft AGL 환산용)
_FT_TO_M = 0.3048


@dataclass(frozen=True)
class BvlosRegulation:
    """단일 관할권의 BVLOS 운영 요건 모델 (frozen·결정적)."""

    code: str
    name: str
    framework: str
    approval_mechanism: str
    operator_cert: str
    aircraft_cert: str
    remote_id_required: bool
    daa_required: bool  # Detect-And-Avoid 의무
    insurance_required: bool
    max_altitude_agl_m: float
    over_people_allowed: bool  # 인구밀집/사람 위 비행 허용 (기본 카테고리 내)
    notes: str = ""


# ── 4개 관할권 요건 테이블 (모델 기준값) ───────────────────────────────────
_KR = BvlosRegulation(
    code="KR",
    name="대한민국",
    framework="항공안전법 §129 / 드론활용촉진법",
    approval_mechanism="특별비행승인 (BVLOS·야간), 국토부 Drone One-Stop",
    operator_cert="무인비행장치 조종자격 (1~4종, 자체중량별)",
    aircraft_cert="기체 신고 (자체중량 2kg 초과) + 안전성 인증 (25kg 초과)",
    remote_id_required=True,
    daa_required=True,
    insurance_required=True,  # 사업용 대인/대물 보험 의무
    max_altitude_agl_m=150.0,  # 특별승인으로 초과 가능
    over_people_allowed=False,  # 인구밀집지역은 별도 승인
    notes="K-드론시스템 UTM 연동, 특별승인 시 BVLOS/야간/고도초과 허용.",
)

_US = BvlosRegulation(
    code="US",
    name="United States",
    framework="14 CFR Part 107 §107.31 + Part 108(NPRM) + Part 89(Remote ID)",
    approval_mechanism="BVLOS waiver / BEYOND 프로그램 (Part 108 정규화 진행)",
    operator_cert="Remote Pilot Certificate (Part 107)",
    aircraft_cert="기체 등록 (Part 47/48), Part 108 시 production standard",
    remote_id_required=True,  # Part 89, ASTM F3411
    daa_required=True,
    insurance_required=False,  # 연방 의무 아님 (운영자 자율)
    max_altitude_agl_m=400.0 * _FT_TO_M,  # 400 ft AGL ≈ 121.9 m
    over_people_allowed=True,  # Operations Over People 규칙(Category 1~4) 충족 시
    notes="BVLOS 는 waiver 또는 Part 108 승인 필요, Remote ID 의무화 완료.",
)

_EU = BvlosRegulation(
    code="EU",
    name="European Union (EASA)",
    framework="EU 2019/947 Specific 카테고리 + SORA (JARUS)",
    approval_mechanism="운영 승인 (Operational Authorisation) 또는 LUC, PDRA",
    operator_cert="원격조종자 이론·실기 (STS/PDRA), LUC 보유 운영자",
    aircraft_cert="UAS Class identification (C0~C6) + 기술 표준",
    remote_id_required=True,  # Class C0+ direct/network remote ID
    daa_required=True,
    insurance_required=True,  # EC 785/2004 보험 의무
    max_altitude_agl_m=120.0,  # 기본 120 m, SORA 등급/PDRA 로 상향
    over_people_allowed=False,  # SORA iGRC 등급 따라 결정
    notes="SORA SAIL 등급 + ARC 로 BVLOS 운영 위험 등급 결정.",
)

_JP = BvlosRegulation(
    code="JP",
    name="日本",
    framework="改正航空法 (2022) Level 4 飛行 제도",
    approval_mechanism="飛行 허가·승인 (DIPS), Level 3.5/4 카테고리 비행",
    operator_cert="一等無人航空機操縦士 (Level 4) / 二等 (技能証明)",
    aircraft_cert="第一種機体認証 (Level 4) / 第二種 (기체 인증)",
    remote_id_required=True,  # 登録記号 + リモートID 발신
    daa_required=True,
    insurance_required=True,  # 飛行 허가 조건상 손해배상 보험 권고·의무화 추세
    max_altitude_agl_m=150.0,  # 地表/水面 150 m
    over_people_allowed=True,  # Level 4 = 제3자 위 유인지대 BVLOS 허용
    notes="Level 4 = 第一種機体認証 + 一等操縦士 + 運航管理 매뉴얼 필수.",
)

REGULATIONS: dict[str, BvlosRegulation] = {
    "KR": _KR,
    "US": _US,
    "EU": _EU,
    "JP": _JP,
}

# 비교 대상 필드 (matrix 컬럼 순서) — 표시명 매핑
COMPARISON_FIELDS: tuple[tuple[str, str], ...] = (
    ("framework", "규제 프레임워크"),
    ("approval_mechanism", "승인 방식"),
    ("operator_cert", "조종자 자격"),
    ("aircraft_cert", "기체 인증"),
    ("remote_id_required", "Remote ID 의무"),
    ("daa_required", "Detect-And-Avoid 의무"),
    ("insurance_required", "보험 의무"),
    ("max_altitude_agl_m", "기본 고도 상한 (m AGL)"),
    ("over_people_allowed", "사람 위 비행 (기본)"),
)


@dataclass(frozen=True)
class OperationProfile:
    """SDACS 운영 프로파일 — 각 관할권 요건에 대조할 입력."""

    altitude_agl_m: float
    has_remote_id: bool
    has_daa: bool
    has_operator_cert: bool
    has_aircraft_cert: bool
    has_insurance: bool
    over_people: bool = False


@dataclass(frozen=True)
class ConformanceResult:
    """단일 관할권 적합성 판정 결과."""

    code: str
    name: str
    conformant: bool
    gaps: tuple[str, ...] = ()


def get_regulation(code: str) -> BvlosRegulation:
    """관할권 코드로 규제 레코드를 조회한다.

    Raises:
        ValueError: 알 수 없는 관할권 코드.
    """
    key = code.upper()
    if key not in REGULATIONS:
        raise ValueError(f"알 수 없는 관할권 코드: {code!r} (지원: {', '.join(JURISDICTIONS)})")
    return REGULATIONS[key]


def compare_field(field_name: str) -> dict[str, object]:
    """단일 요건 필드를 4개 관할권에 걸쳐 비교한다.

    Raises:
        ValueError: BvlosRegulation 에 없는 필드명.
    """
    if field_name not in {f.name for f in fields(BvlosRegulation)}:
        raise ValueError(f"알 수 없는 비교 필드: {field_name!r}")
    return {code: getattr(REGULATIONS[code], field_name) for code in JURISDICTIONS}


def comparison_matrix() -> dict[str, dict[str, object]]:
    """COMPARISON_FIELDS 전체를 관할권별로 비교한 매트릭스를 반환한다.

    반환: {field_name: {jurisdiction_code: value}} (결정적·삽입순서 보존).
    """
    return {field_name: compare_field(field_name) for field_name, _label in COMPARISON_FIELDS}


def _validate_profile(profile: OperationProfile) -> None:
    if not math.isfinite(profile.altitude_agl_m):
        raise ValueError(f"고도는 유한수여야 합니다: {profile.altitude_agl_m}")
    if profile.altitude_agl_m < 0:
        raise ValueError(f"고도는 음수일 수 없습니다: {profile.altitude_agl_m}")


def assess_conformance(profile: OperationProfile, code: str) -> ConformanceResult:
    """운영 프로파일을 단일 관할권 BVLOS 요건에 대조해 적합성 갭을 산정한다."""
    _validate_profile(profile)
    reg = get_regulation(code)
    gaps: list[str] = []

    if reg.remote_id_required and not profile.has_remote_id:
        gaps.append("Remote ID 미충족")
    if reg.daa_required and not profile.has_daa:
        gaps.append("Detect-And-Avoid 미충족")
    if not profile.has_operator_cert:
        gaps.append(f"조종자 자격 미보유 ({reg.operator_cert})")
    if not profile.has_aircraft_cert:
        gaps.append(f"기체 인증 미충족 ({reg.aircraft_cert})")
    if reg.insurance_required and not profile.has_insurance:
        gaps.append("보험 미가입")
    if profile.altitude_agl_m > reg.max_altitude_agl_m:
        gaps.append(
            f"고도 초과 ({profile.altitude_agl_m:.1f}m > {reg.max_altitude_agl_m:.1f}m 기본 상한)"
        )
    if profile.over_people and not reg.over_people_allowed:
        gaps.append("사람 위 비행 — 기본 카테고리 불가 (별도 승인 필요)")

    return ConformanceResult(
        code=reg.code,
        name=reg.name,
        conformant=not gaps,
        gaps=tuple(gaps),
    )


def assess_all(profile: OperationProfile) -> dict[str, ConformanceResult]:
    """운영 프로파일을 4개 관할권 전체에 대조한다 (삽입순서 보존)."""
    return {code: assess_conformance(profile, code) for code in JURISDICTIONS}


def to_markdown_table() -> str:
    """비교 매트릭스를 마크다운 표 문자열로 출력한다 (대시보드/문서 피드)."""
    header = "| 요건 | " + " | ".join(REGULATIONS[c].name for c in JURISDICTIONS) + " |"
    divider = "|---|" + "|".join(["---"] * len(JURISDICTIONS)) + "|"
    rows = [header, divider]
    for field_name, label in COMPARISON_FIELDS:
        cells = [_format_cell(getattr(REGULATIONS[c], field_name)) for c in JURISDICTIONS]
        rows.append(f"| {label} | " + " | ".join(cells) + " |")
    return "\n".join(rows)


def _format_cell(value: object) -> str:
    """매트릭스 셀 값을 표시 문자열로 변환한다."""
    if isinstance(value, bool):
        return "✅" if value else "❌"
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def to_dict() -> dict[str, dict[str, object]]:
    """전체 규제 테이블을 직렬화 가능한 dict 로 출력한다 (JSON export 용)."""
    field_names = tuple(f.name for f in fields(BvlosRegulation))
    return {
        code: {field_name: getattr(reg, field_name) for field_name in field_names}
        for code, reg in REGULATIONS.items()
    }
