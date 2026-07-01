"""Phase 403 (ODYSSEY): EASA EU 2019/947 운영 카테고리(Open/Specific/Certified) 결정적 판정.

GENESIS Phase 302 의 `soraAssess`(JS, JARUS SORA 2.0 표 기반 SAIL 산정)는 *Specific*
카테고리의 SAIL 등급만 답한다. 본 모듈은 그 위에 EU 2019/947 의 **세 운영 카테고리**
(Open / Specific / Certified)와 Open 하위 분류(A1·A2·A3)를 결정적으로 판정하는 Python
계층을 얹는다 — "이 운용은 어느 규제 체계로 비행 가능한가" 에 답한다.

판정 순서 (EU 2019/947 Art. 3-4 + UAS.OPEN.020/030/040 + JARUS SORA 2.0):
  1) Certified 강제 트리거 — 인원 수송, 위험물(고위험), 군집 대형 기체의 군중 상공 비행
  2) Open 적격 — MTOM<25kg·VLOS·고도≤120m·군중 상공 아님·위험물 없음 + 유효한 A1/A2/A3
  3) 그 외 — Specific (SORA 산정). SORA GRC>7 (Specific 범위 초과) → Certified 격상

SORA 표(`SORA_IGRC`·`SORA_SAIL_TABLE`)는 `swarm_3d_simulator.html` 의 동명 표와 **동일**하게
복제했다(수치 불일치 금지 규약) — *동일 입력은 동일 SORA 결과* 를 낸다. JS `soraAssess` 는
군집 운용을 BVLOS 로 가정(`bvlos !== false`)하므로 본 모듈의 `vlos` 도 **기본 False(BVLOS)** 로
맞춰, 기본 인자 호출에서도 JS 와 동일한 iGRC 를 보장하고 위험을 과소평가하지 않는다. VLOS 단일
운용을 모델링하려면 `vlos=True` 를 명시한다. 외부 호출·난수 없음.

가정 (명시):
  - C-class 는 EU 위임규정 2019/945 의 *질량* 게이트만으로 C0-C3 를 파생한다(속도·운동에너지·
    클래스 마킹 전자요건은 본 결정적 모델 범위 밖 — `c_class` 명시 시 그 값을 우선한다).
    **C5/C6/C7 클래스는 범위 밖**(EU 2019/947 Art. 4(1)(b) — Certified 자동 격상 대상이나 미구현).
  - "위험물(dangerous_goods)"은 사고 시 고위험으로 분류해 Certified 로 본다(EU Art. 4(1)(c)).
    저위험 위험물 운송의 Specific 분기는 본 모델에서 다루지 않는다.
  - 군중 상공 비행(over_assembly)은 기체 특성 치수 ≥3 m 이면 Certified, 그 미만이면 Specific.
    JS `soraAssess` 는 over_assembly 입력이 없으나, 본 모듈은 SORA 2.0 정합을 위해 군중 상공이면
    인구밀도와 무관히 ARC-c(전술 완화 전)로 끌어올린다(JS 표 자체와는 모순 없음 — 입력 모델 확장).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# ── SORA 2.0 표 (swarm_3d_simulator.html SORA_IGRC·SORA_SAIL_TABLE 와 동일) ──
# 내재적 지상 위험 등급(iGRC): 인구밀도 × (VLOS/BVLOS)
SORA_IGRC: dict[str, dict[str, int]] = {
    "controlled": {"vlos": 1, "bvlos": 2},
    "sparse": {"vlos": 2, "bvlos": 3},
    "populated": {"vlos": 3, "bvlos": 4},
    "assembly": {"vlos": 7, "bvlos": 8},
}

# 최종 GRC → ARC 별 SAIL 등급 (로마 숫자). swarm_3d_simulator.html SORA_SAIL_TABLE 와 동일.
# 주의: 현 전술 완화(TMPR) 로직은 ARC 를 항상 'b' 로 귀결시키므로 'a'(통제공역)·'d'(최고
# 지상위험) 열은 현재 미사용이다. JS 표와의 동일성 유지 + 향후 ARC-a/d 경로 확장 여지를 위해
# 열을 보존한다(제거하면 우발적 ARC-a/d 조회 시 KeyError 로 즉시 드러남 vs 표 불일치 trade-off).
SORA_SAIL_TABLE: dict[int, dict[str, str]] = {
    1: {"a": "I", "b": "II", "c": "IV", "d": "VI"},
    2: {"a": "I", "b": "II", "c": "IV", "d": "VI"},
    3: {"a": "II", "b": "II", "c": "IV", "d": "VI"},
    4: {"a": "III", "b": "III", "c": "IV", "d": "VI"},
    5: {"a": "IV", "b": "IV", "c": "IV", "d": "VI"},
    6: {"a": "V", "b": "V", "c": "V", "d": "VI"},
    7: {"a": "VI", "b": "VI", "c": "VI", "d": "VI"},
}

VALID_DENSITIES = tuple(SORA_IGRC.keys())  # 인구밀도 4종

# EU 위임규정 2019/945 C-class 질량 상한 (kg, 미만)
C_CLASS_MASS_LIMITS: tuple[tuple[str, float], ...] = (
    ("C0", 0.25),
    ("C1", 0.9),
    ("C2", 4.0),
    ("C3", 25.0),
)
VALID_C_CLASSES = ("C0", "C1", "C2", "C3", "C4")

# Open 카테고리 경계 상수 (EU 2019/947)
OPEN_MAX_MTOM_KG = 25.0  # Open/Specific 공통 — 25kg 이상은 Open 불가
OPEN_MAX_HEIGHT_M = 120.0  # Open 고도 상한 (m AGL)
A2_MIN_DISTANCE_M = 30.0  # A2 비저속 모드 수평 이격 (UAS.OPEN.030)
A2_LOW_SPEED_DISTANCE_M = 5.0  # A2 저속 모드(<3 m/s) 이격
CERTIFIED_DIMENSION_M = 3.0  # 군중 상공 Certified 임계 특성 치수


@dataclass(frozen=True)
class OperationProfile:
    """드론 운용 프로파일 — 카테고리 판정 입력."""

    mtom_kg: float  # 최대 이륙 질량 (kg)
    population_density: str = "sparse"  # controlled | sparse | populated | assembly
    vlos: bool = False  # 가시권 내(VLOS) 여부 — 기본 BVLOS (군집 운용·JS soraAssess 정합)
    max_height_m: float = 120.0  # 최대 비행 고도 (m AGL)
    over_assembly: bool = False  # 군중 상공 비행 여부
    dangerous_goods: bool = False  # 위험물 운송 (고위험) 여부
    transport_of_people: bool = False  # 인원 수송 여부
    horizontal_distance_to_people_m: float | None = None  # 비관여 인원 수평 이격 (m)
    characteristic_dimension_m: float = 1.0  # 기체 특성 치수 (m)
    low_speed_mode: bool = False  # A2 저속 모드(<3 m/s) 여부
    c_class: str | None = None  # 명시 C-class (없으면 질량으로 파생)
    geofence_active: bool = True  # M1 전략적 완화 (NFZ 지오펜스)
    erp_active: bool = True  # M3 비상대응절차(ERP) 완화

    def __post_init__(self) -> None:
        if not math.isfinite(self.mtom_kg) or self.mtom_kg <= 0:
            raise ValueError(f"mtom_kg must be positive finite, got {self.mtom_kg!r}")
        if self.population_density not in VALID_DENSITIES:
            raise ValueError(
                f"population_density must be one of {VALID_DENSITIES}, got {self.population_density!r}"
            )
        if not math.isfinite(self.max_height_m) or self.max_height_m < 0:
            raise ValueError(f"max_height_m must be >= 0 finite, got {self.max_height_m!r}")
        if not math.isfinite(self.characteristic_dimension_m) or self.characteristic_dimension_m <= 0:
            raise ValueError(
                f"characteristic_dimension_m must be positive finite, got {self.characteristic_dimension_m!r}"
            )
        if self.c_class is not None and self.c_class not in VALID_C_CLASSES:
            raise ValueError(
                f"c_class must be one of {VALID_C_CLASSES} or None, got {self.c_class!r} "
                "(C5/C6/C7 are out of scope; they require Certified category — EU 2019/947 Art. 4(1)(b))"
            )
        if self.horizontal_distance_to_people_m is not None and (
            not math.isfinite(self.horizontal_distance_to_people_m)
            or self.horizontal_distance_to_people_m < 0
        ):
            raise ValueError(
                "horizontal_distance_to_people_m must be >= 0 finite or None, "
                f"got {self.horizontal_distance_to_people_m!r}"
            )


@dataclass(frozen=True)
class SoraResult:
    """SORA 2.0 산정 결과 (Specific 카테고리용)."""

    i_grc: int  # 내재적 지상 위험 등급
    final_grc: int  # 완화 적용 후 최종 GRC
    arc: str  # 'ARC-a' | 'ARC-b' | 'ARC-c' | 'ARC-d'
    sail: str  # 'SAIL I'..'SAIL VI' 또는 'CERTIFIED'
    mitigations: tuple[str, ...]  # 적용된 지상 완화 목록
    tactical_mitigation: str  # 전술 완화(TMPR) 서술


@dataclass(frozen=True)
class CategoryAssessment:
    """EU 2019/947 운영 카테고리 판정 결과."""

    category: str  # 'OPEN' | 'SPECIFIC' | 'CERTIFIED'
    subcategory: str | None  # Open: 'A1'|'A2'|'A3', 그 외 None
    authorization_required: bool  # 운영 허가/선언 필요 여부
    c_class: str | None  # 파생/명시 C-class (≥25kg 등 미분류 시 None)
    sora: SoraResult | None  # Specific 일 때 SORA 결과, 그 외 None
    reasons: tuple[str, ...] = ()  # 판정 근거 (한국어) — tuple 은 불변이라 frozen 에 안전


def derive_c_class(mtom_kg: float) -> str | None:
    """질량(kg)으로 EU C-class(C0-C4)를 파생한다. 25kg 이상은 None."""
    for label, limit in C_CLASS_MASS_LIMITS:
        if mtom_kg < limit:
            return label
    return None  # ≥ 25 kg — Open 불가, C4 도 ≤25kg 이므로 미분류


def assess_sora(profile: OperationProfile) -> SoraResult:
    """SORA 2.0 으로 iGRC·완화·ARC·SAIL 을 결정적으로 산정한다.

    `swarm_3d_simulator.html` 의 `soraAssess` 와 동일한 표·완화 규칙을 사용한다.
    """
    density = profile.population_density
    mode = "vlos" if profile.vlos else "bvlos"
    i_grc = SORA_IGRC[density][mode]

    mitigations: list[str] = []
    grc = i_grc
    if profile.geofence_active:
        grc -= 1
        mitigations.append("M1 strategic geofence (NFZ 활성)")
    if profile.erp_active:
        grc -= 1
        mitigations.append("M3 ERP (failsafe + 착륙 시퀀스 관리)")
    grc = max(1, grc)

    # ARC: 인구밀집 환경 또는 군중 상공이면 ARC-c, 그 외 ARC-b. 전술 완화(TMPR)로 c→b 1단계 경감.
    # over_assembly 를 ARC 에 반영하는 것은 SORA 2.0 정합을 위한 입력 모델 확장(JS soraAssess 는
    # 장면 상태에서 밀도만 파생하므로 본 추가는 JS 표와 모순이 아니다). 단, 군중 상공은 전술
    # 완화(CPA·APF·ATC)만으로 지상위험을 충분히 낮출 수 없어 TMPR c→b 경감을 적용하지 않는다.
    arc_letter = "c" if density in ("populated", "assembly") or profile.over_assembly else "b"
    tactical = "CPA lookahead + APF + ATC (5계층 안전망)"
    if arc_letter == "c" and not profile.over_assembly:
        arc_letter = "b"  # TMPR 적용 (군중 상공 제외)

    # arc_letter(맨 글자)는 표 조회용, SoraResult.arc 는 'ARC-' 접두 표시용 — 혼용 금지.
    sail = "CERTIFIED" if grc > 7 else "SAIL " + SORA_SAIL_TABLE[grc][arc_letter]

    return SoraResult(
        i_grc=i_grc,
        final_grc=grc,
        arc="ARC-" + arc_letter,
        sail=sail,
        mitigations=tuple(mitigations),
        tactical_mitigation=tactical,
    )


def _certified_trigger(profile: OperationProfile, c_class: str | None) -> str | None:
    """Certified 카테고리 강제 트리거를 검사한다(해당 없으면 None)."""
    if profile.transport_of_people:
        return "인원 수송 운용 — Certified 카테고리 강제 (EU 2019/947 Art. 4(1)(a))"
    if profile.dangerous_goods:
        return "고위험 위험물 운송 — Certified 카테고리 강제 (EU 2019/947 Art. 4(1)(c))"
    if profile.over_assembly and profile.characteristic_dimension_m >= CERTIFIED_DIMENSION_M:
        return (
            f"군중 상공 + 특성 치수 {profile.characteristic_dimension_m:.1f} m "
            f"≥ {CERTIFIED_DIMENSION_M:.0f} m — Certified 카테고리 강제"
        )
    return None


def _open_subcategory(profile: OperationProfile, c_class: str | None) -> tuple[str | None, str]:
    """Open 하위 분류(A1/A2/A3)를 판정한다. 부적격이면 (None, 사유)."""
    if c_class is None:
        return None, "C-class 미분류(≥25kg) — Open 불가"
    # A1: C0/C1 — 비관여 인원 상공 비행 허용(군중 제외). UAS.OPEN.020
    if c_class in ("C0", "C1"):
        return "A1", f"{c_class} 경량 기체 — A1 (비관여 인원 근접 허용, 군중 제외)"
    # A2: C2 — 수평 이격 ≥30 m(저속 모드 ≥5 m). UAS.OPEN.030
    if c_class == "C2":
        required = A2_LOW_SPEED_DISTANCE_M if profile.low_speed_mode else A2_MIN_DISTANCE_M
        dist = profile.horizontal_distance_to_people_m
        if dist is not None and dist >= required:
            return "A2", f"C2 + 수평 이격 {dist:.0f} m ≥ {required:.0f} m — A2 (인원 근접)"
        # A2 이격 미충족 시 A3 로 강등 시도(비관여 인원 부재 환경)
    # A3: C2/C3/C4 — 비관여 인원 부재(controlled/sparse) 환경. UAS.OPEN.040
    if c_class in ("C2", "C3", "C4") and profile.population_density in ("controlled", "sparse"):
        return "A3", f"{c_class} + 비관여 인원 부재 환경 — A3 (인원·시가지 원거리)"
    return None, f"{c_class} 운용 조건이 A1/A2/A3 어디에도 부합하지 않음 — Specific 필요"


def assess_category(profile: OperationProfile) -> CategoryAssessment:
    """운용 프로파일로부터 EU 2019/947 운영 카테고리를 결정적으로 판정한다."""
    c_class = profile.c_class if profile.c_class is not None else derive_c_class(profile.mtom_kg)

    # 1) Certified 강제 트리거
    trigger = _certified_trigger(profile, c_class)
    if trigger is not None:
        return CategoryAssessment(
            category="CERTIFIED",
            subcategory=None,
            authorization_required=True,
            c_class=c_class,
            sora=None,
            reasons=(trigger,),
        )

    # 2) Open 적격 — 하드 제약 전부 충족 + 유효 하위분류
    reasons: list[str] = []
    open_blocked = _open_hard_constraints(profile)
    if not open_blocked:
        subcat, reason = _open_subcategory(profile, c_class)
        if subcat is not None:
            return CategoryAssessment(
                category="OPEN",
                subcategory=subcat,
                authorization_required=False,
                c_class=c_class,
                sora=None,
                reasons=(reason,),
            )
        reasons.append(reason)
    else:
        reasons.extend(open_blocked)

    # 3) Specific (SORA). GRC>7 → Certified 격상.
    sora = assess_sora(profile)
    if sora.sail == "CERTIFIED":
        reasons.append(f"SORA 최종 GRC {sora.final_grc} > 7 — Specific 범위 초과, Certified 격상")
        return CategoryAssessment(
            category="CERTIFIED",
            subcategory=None,
            authorization_required=True,
            c_class=c_class,
            sora=sora,
            reasons=tuple(reasons),
        )
    reasons.append(f"Open 부적격 — Specific 운영 허가 필요 ({sora.sail})")
    return CategoryAssessment(
        category="SPECIFIC",
        subcategory=None,
        authorization_required=True,
        c_class=c_class,
        sora=sora,
        reasons=tuple(reasons),
    )


def _open_hard_constraints(profile: OperationProfile) -> list[str]:
    """Open 카테고리의 하드 제약 위반 목록을 반환한다(빈 목록 = 적격)."""
    blocked: list[str] = []
    if profile.mtom_kg >= OPEN_MAX_MTOM_KG:
        blocked.append(f"MTOM {profile.mtom_kg:.1f} kg ≥ {OPEN_MAX_MTOM_KG:.0f} kg — Open 불가")
    if not profile.vlos:
        blocked.append("BVLOS 운용 — Open 불가 (Open 은 VLOS 한정)")
    if profile.max_height_m > OPEN_MAX_HEIGHT_M:
        blocked.append(
            f"고도 {profile.max_height_m:.0f} m > {OPEN_MAX_HEIGHT_M:.0f} m — Open 불가"
        )
    if profile.over_assembly:
        blocked.append("군중 상공 비행 — Open 불가")
    # dangerous_goods 는 _certified_trigger 가 먼저 CERTIFIED 로 단락하므로 본 분기는 현재
    # 도달하지 않는다. Open 적격 판정의 독립 안전망(방어적 중복)으로 의도적으로 남겨둔다.
    if profile.dangerous_goods:
        blocked.append("위험물 운송 — Open 불가")
    return blocked


def summary(assessment: CategoryAssessment) -> str:
    """판정 결과의 사람이 읽는 한 줄 요약."""
    label = assessment.category
    if assessment.subcategory:
        label += f" ({assessment.subcategory})"
    if assessment.sora is not None:
        label += f" · {assessment.sora.sail}"
    auth = "허가 필요" if assessment.authorization_required else "허가 불요"
    return f"{label} — {auth}"
