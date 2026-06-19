"""Phase 403 (ODYSSEY): EASA EU 2019/947 운영 카테고리 판정 테스트.

`simulation/sora_category.py` 의 Open/Specific/Certified 결정적 판정과
SORA 2.0 산정(시뮬레이터 JS 표 정합)을 검증한다.
근거: EU 2019/947 Art. 3-4 + UAS.OPEN.020/030/040 + JARUS SORA 2.0.
"""

import math

import pytest

from simulation.sora_category import (
    A2_LOW_SPEED_DISTANCE_M,
    A2_MIN_DISTANCE_M,
    OPEN_MAX_HEIGHT_M,
    OPEN_MAX_MTOM_KG,
    SORA_IGRC,
    SORA_SAIL_TABLE,
    VALID_C_CLASSES,
    VALID_DENSITIES,
    CategoryAssessment,
    OperationProfile,
    SoraResult,
    assess_category,
    assess_sora,
    derive_c_class,
    summary,
)


# ── derive_c_class ──
@pytest.mark.parametrize(
    "mass,expected",
    [
        (0.1, "C0"),
        (0.249, "C0"),
        (0.25, "C1"),
        (0.5, "C1"),
        (0.9, "C2"),
        (3.99, "C2"),
        (4.0, "C3"),
        (24.9, "C3"),
        (25.0, None),
        (100.0, None),
    ],
)
def test_derive_c_class_mass_gates(mass, expected):
    assert derive_c_class(mass) == expected


# ── Open 카테고리 하위 분류 ──
def test_open_a1_for_c0():
    profile = OperationProfile(mtom_kg=0.2, vlos=True)
    result = assess_category(profile)
    assert result.category == "OPEN"
    assert result.subcategory == "A1"
    assert result.authorization_required is False
    assert result.c_class == "C0"
    assert result.sora is None


def test_open_a1_for_c1():
    profile = OperationProfile(mtom_kg=0.85, vlos=True)
    result = assess_category(profile)
    assert result.category == "OPEN"
    assert result.subcategory == "A1"
    assert result.c_class == "C1"


def test_open_a2_for_c2_with_sufficient_distance():
    profile = OperationProfile(
        mtom_kg=3.0, population_density="populated", horizontal_distance_to_people_m=30.0, vlos=True
    )
    result = assess_category(profile)
    assert result.category == "OPEN"
    assert result.subcategory == "A2"
    assert result.c_class == "C2"


def test_open_a2_low_speed_mode_relaxes_distance_to_5m():
    profile = OperationProfile(
        mtom_kg=3.0,
        population_density="populated",
        horizontal_distance_to_people_m=A2_LOW_SPEED_DISTANCE_M,
        low_speed_mode=True,
        vlos=True,
    )
    result = assess_category(profile)
    assert result.category == "OPEN"
    assert result.subcategory == "A2"


def test_open_a3_for_c3_in_sparse_area():
    profile = OperationProfile(mtom_kg=10.0, population_density="sparse", vlos=True)
    result = assess_category(profile)
    assert result.category == "OPEN"
    assert result.subcategory == "A3"
    assert result.c_class == "C3"


def test_open_a3_for_c2_far_from_people():
    # C2 인데 이격 정보가 없고(=A2 불가) 비관여 인원 부재 환경이면 A3 강등
    profile = OperationProfile(mtom_kg=3.0, population_density="sparse", vlos=True)
    result = assess_category(profile)
    assert result.category == "OPEN"
    assert result.subcategory == "A3"


# ── Open → Specific 강등 ──
def test_c2_close_to_people_but_insufficient_distance_falls_to_specific():
    profile = OperationProfile(
        mtom_kg=3.0, population_density="populated", horizontal_distance_to_people_m=10.0
    )
    result = assess_category(profile)
    assert result.category == "SPECIFIC"
    assert result.subcategory is None
    assert result.sora is not None


def test_bvlos_forces_specific():
    profile = OperationProfile(mtom_kg=0.2, vlos=False)
    result = assess_category(profile)
    assert result.category == "SPECIFIC"
    assert any("BVLOS" in r for r in result.reasons)


def test_height_above_120m_forces_specific():
    # vlos=True 로 BVLOS 요인을 배제해 고도 단독으로 Open 차단을 검증한다.
    profile = OperationProfile(mtom_kg=0.2, max_height_m=150.0, vlos=True)
    result = assess_category(profile)
    assert result.category == "SPECIFIC"
    assert any("120" in r for r in result.reasons)


def test_default_is_bvlos_matching_js_soraassess():
    # JS soraAssess 는 군집 운용을 BVLOS 로 가정 — 기본 인자 호출이 BVLOS 여야 파리티 유지.
    profile = OperationProfile(mtom_kg=0.2)
    assert profile.vlos is False
    result = assess_category(profile)
    assert result.category == "SPECIFIC"  # BVLOS → Open 불가


def test_over_assembly_sparse_keeps_arc_c_no_tmpr_reduction():
    # 군중 상공(소형)+희박 밀도: Open 차단 → Specific. TMPR 가 ARC-c 를 b 로 낮추지 않아
    # 인구밀도만 보면 ARC-b(SAIL II)일 케이스가 ARC-c(SAIL IV)로 보수 산정된다.
    profile = OperationProfile(
        mtom_kg=2.0,
        population_density="sparse",
        over_assembly=True,
        characteristic_dimension_m=1.0,
        vlos=True,
    )
    result = assess_category(profile)
    assert result.category == "SPECIFIC"
    assert result.sora is not None
    assert result.sora.arc == "ARC-c"
    assert result.sora.sail == "SAIL IV"


def test_c3_in_populated_area_forces_specific():
    # A3 는 비관여 인원 부재 환경만 허용 → populated 면 Open 불가
    profile = OperationProfile(mtom_kg=10.0, population_density="populated")
    result = assess_category(profile)
    assert result.category == "SPECIFIC"


# ── Certified 강제 트리거 ──
def test_transport_of_people_forces_certified():
    profile = OperationProfile(mtom_kg=0.2, transport_of_people=True)
    result = assess_category(profile)
    assert result.category == "CERTIFIED"
    assert result.sora is None
    assert any("인원 수송" in r for r in result.reasons)


def test_dangerous_goods_forces_certified():
    profile = OperationProfile(mtom_kg=2.0, dangerous_goods=True)
    result = assess_category(profile)
    assert result.category == "CERTIFIED"


def test_over_assembly_with_large_dimension_forces_certified():
    profile = OperationProfile(
        mtom_kg=20.0, over_assembly=True, characteristic_dimension_m=3.5
    )
    result = assess_category(profile)
    assert result.category == "CERTIFIED"
    assert any("군중 상공" in r for r in result.reasons)


def test_over_assembly_small_dimension_is_specific_not_certified():
    # 군중 상공이지만 소형 기체(<3m) → Specific (SORA), Open 불가
    profile = OperationProfile(
        mtom_kg=2.0,
        over_assembly=True,
        characteristic_dimension_m=1.0,
        population_density="populated",
    )
    result = assess_category(profile)
    assert result.category == "SPECIFIC"


def test_sora_grc_above_7_escalates_to_certified():
    # assembly + BVLOS + 완화 없음 → iGRC 8, 완화 0 → GRC 8 > 7 → Certified
    profile = OperationProfile(
        mtom_kg=20.0,
        population_density="assembly",
        vlos=False,
        geofence_active=False,
        erp_active=False,
    )
    result = assess_category(profile)
    assert result.category == "CERTIFIED"
    assert result.sora is not None
    assert result.sora.final_grc == 8
    assert result.sora.sail == "CERTIFIED"


# ── SORA 산정 (JS 표 정합) ──
def test_sora_igrc_matches_table():
    # sparse + bvlos = 3
    profile = OperationProfile(
        mtom_kg=20.0, population_density="sparse", vlos=False,
        geofence_active=False, erp_active=False,
    )
    sora = assess_sora(profile)
    assert sora.i_grc == 3
    assert sora.final_grc == 3  # 완화 없음


def test_sora_mitigations_reduce_grc():
    profile = OperationProfile(
        mtom_kg=20.0, population_density="populated", vlos=False,
        geofence_active=True, erp_active=True,
    )
    sora = assess_sora(profile)
    assert sora.i_grc == 4  # populated bvlos
    assert sora.final_grc == 2  # -M1 -M3
    assert len(sora.mitigations) == 2


def test_sora_grc_clamped_at_minimum_1():
    profile = OperationProfile(
        mtom_kg=0.5, population_density="controlled", vlos=True,
        geofence_active=True, erp_active=True,
    )
    sora = assess_sora(profile)
    assert sora.i_grc == 1
    assert sora.final_grc == 1  # max(1, 1-2)


def test_sora_arc_tactical_mitigation_reduces_c_to_b():
    # populated → ARC-c 후보, TMPR 로 ARC-b
    profile = OperationProfile(mtom_kg=20.0, population_density="populated", vlos=False)
    sora = assess_sora(profile)
    assert sora.arc == "ARC-b"


def test_sora_sail_lookup_matches_js_table():
    # controlled vlos → iGRC 1, 완화 2 → grc 1, arc b → SAIL II
    profile = OperationProfile(
        mtom_kg=20.0, population_density="controlled", vlos=True,
        geofence_active=True, erp_active=True,
    )
    sora = assess_sora(profile)
    assert sora.final_grc == 1
    assert sora.arc == "ARC-b"
    assert sora.sail == "SAIL II"
    assert SORA_SAIL_TABLE[1]["b"] == "II"


def test_igrc_table_identical_to_documented_values():
    assert SORA_IGRC["controlled"] == {"vlos": 1, "bvlos": 2}
    assert SORA_IGRC["assembly"] == {"vlos": 7, "bvlos": 8}


# ── 입력 검증 ──
@pytest.mark.parametrize("bad", [0.0, -1.0, float("nan"), float("inf")])
def test_invalid_mtom_raises(bad):
    with pytest.raises(ValueError):
        OperationProfile(mtom_kg=bad)


def test_invalid_density_raises():
    with pytest.raises(ValueError):
        OperationProfile(mtom_kg=1.0, population_density="city")


def test_invalid_c_class_raises():
    with pytest.raises(ValueError):
        OperationProfile(mtom_kg=1.0, c_class="C9")


def test_negative_height_raises():
    with pytest.raises(ValueError):
        OperationProfile(mtom_kg=1.0, max_height_m=-5.0)


def test_negative_distance_raises():
    with pytest.raises(ValueError):
        OperationProfile(mtom_kg=1.0, horizontal_distance_to_people_m=-1.0)


def test_invalid_dimension_raises():
    with pytest.raises(ValueError):
        OperationProfile(mtom_kg=1.0, characteristic_dimension_m=0.0)


# ── 명시 c_class 우선 ──
def test_explicit_c_class_overrides_mass_derivation():
    # 질량은 C0 범위지만 명시 C2 → A2/A3 경로
    profile = OperationProfile(mtom_kg=0.2, c_class="C2", population_density="sparse", vlos=True)
    result = assess_category(profile)
    assert result.c_class == "C2"
    assert result.subcategory == "A3"


# ── 결정성 ──
def test_assessment_is_deterministic():
    profile = OperationProfile(mtom_kg=3.0, population_density="populated", vlos=False)
    first = assess_category(profile)
    second = assess_category(profile)
    assert first == second


def test_25kg_drone_cannot_be_open():
    profile = OperationProfile(mtom_kg=25.0, population_density="sparse")
    result = assess_category(profile)
    assert result.category != "OPEN"
    assert result.c_class is None


# ── summary ──
def test_summary_open_includes_subcategory():
    result = assess_category(OperationProfile(mtom_kg=0.2, vlos=True))
    text = summary(result)
    assert "OPEN" in text and "A1" in text and "허가 불요" in text


def test_summary_specific_includes_sail_and_auth():
    result = assess_category(OperationProfile(mtom_kg=0.2, vlos=False))
    text = summary(result)
    assert "SPECIFIC" in text and "SAIL" in text and "허가 필요" in text


def test_summary_certified():
    result = assess_category(OperationProfile(mtom_kg=0.2, transport_of_people=True))
    text = summary(result)
    assert "CERTIFIED" in text and "허가 필요" in text


# ── 불변/메타 ──
def test_frozen_dataclasses_are_immutable():
    profile = OperationProfile(mtom_kg=1.0)
    with pytest.raises(Exception):
        profile.mtom_kg = 2.0  # type: ignore[misc]
    result = assess_category(profile)
    with pytest.raises(Exception):
        result.category = "OPEN"  # type: ignore[misc]


def test_valid_constants_well_formed():
    assert VALID_DENSITIES == ("controlled", "sparse", "populated", "assembly")
    assert "C4" in VALID_C_CLASSES
    assert OPEN_MAX_MTOM_KG == 25.0
    assert OPEN_MAX_HEIGHT_M == 120.0
    assert A2_MIN_DISTANCE_M == 30.0


def test_sora_result_and_assessment_types():
    profile = OperationProfile(mtom_kg=0.2, vlos=False)
    result = assess_category(profile)
    assert isinstance(result, CategoryAssessment)
    assert isinstance(result.sora, SoraResult)
    assert math.isfinite(result.sora.final_grc)
