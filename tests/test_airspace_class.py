"""Phase 408 (ODYSSEY): ICAO 공역 클래스 A-G 자동 매핑 테스트.

`simulation/airspace_class.py` 의 결정적 산정(고도·NFZ·특별승인)을 검증한다.
근거: docs/certification/AIRSPACE_CLASS_MAPPING.md §3 매핑 매트릭스 + §6 결정 규칙.
"""

import math

import pytest

from simulation.airspace_class import (
    ALTITUDE_LAYERS,
    CLASS_REQUIREMENTS,
    LEGAL_CEILING_AGL_M,
    SIM_CEILING_AGL_M,
    AirspaceClassification,
    NoFlyZone,
    classify_airspace,
    sdacs_layer_index,
)

# 좌표 헬퍼 — 김포공항 표점 근방(임의)을 NFZ 중심으로 사용
GIMPO = (126.801, 37.558)  # (lon, lat)


def _airport_nfz() -> NoFlyZone:
    return NoFlyZone(name="김포 관제권", center_lon=GIMPO[0], center_lat=GIMPO[1], radius_m=9_300.0)


def _military_nfz() -> NoFlyZone:
    return NoFlyZone(
        name="P-73A", center_lon=126.99, center_lat=37.50, radius_m=2_000.0, kind="military"
    )


# --- 고도 기반 판정 (NFZ 없음) ---


def test_ground_level_is_class_g():
    result = classify_airspace(0.0)
    assert result.icao_class == "G"
    assert result.controlled is False
    assert result.approval_required is False


def test_legal_ceiling_boundary_is_class_g():
    # 정확히 150 m 는 Class G (≤ 법정 상한)
    result = classify_airspace(LEGAL_CEILING_AGL_M)
    assert result.icao_class == "G"


def test_just_above_legal_ceiling_is_class_e():
    result = classify_airspace(LEGAL_CEILING_AGL_M + 0.1)
    assert result.icao_class == "E"
    assert result.controlled is True
    assert result.approval_required is True


def test_sim_ceiling_boundary_is_class_e():
    # 정확히 240 m 는 여전히 Class E (≤ 운용 상한)
    result = classify_airspace(SIM_CEILING_AGL_M)
    assert result.icao_class == "E"


def test_above_sim_ceiling_is_class_b():
    result = classify_airspace(SIM_CEILING_AGL_M + 1.0)
    assert result.icao_class == "B"
    assert result.controlled is True
    assert result.approval_required is True


# --- NFZ 기반 판정 ---


def test_inside_airport_nfz_without_approval_is_class_b():
    # NFZ 중심에서 고도는 낮아도 공항 관제권이면 B
    result = classify_airspace(30.0, lon=GIMPO[0], lat=GIMPO[1], nfz_zones=(_airport_nfz(),))
    assert result.icao_class == "B"
    assert result.approval_required is True


def test_inside_airport_nfz_with_approval_is_class_d():
    result = classify_airspace(
        30.0, lon=GIMPO[0], lat=GIMPO[1], nfz_zones=(_airport_nfz(),), has_special_approval=True
    )
    assert result.icao_class == "D"
    assert result.controlled is True


def test_inside_military_nfz_is_class_r_regardless_of_approval():
    z = (_military_nfz(),)
    result = classify_airspace(
        30.0, lon=126.99, lat=37.50, nfz_zones=z, has_special_approval=True
    )
    assert result.icao_class == "R"


def test_military_takes_precedence_over_airport():
    # 같은 좌표에 군·공항 NFZ 가 겹치면 군(R)이 우선
    overlap_lon, overlap_lat = 126.99, 37.50
    zones = (
        NoFlyZone("공항", overlap_lon, overlap_lat, 5_000.0, kind="airport"),
        NoFlyZone("군작전", overlap_lon, overlap_lat, 5_000.0, kind="military"),
    )
    result = classify_airspace(30.0, lon=overlap_lon, lat=overlap_lat, nfz_zones=zones)
    assert result.icao_class == "R"


def test_outside_all_nfz_falls_back_to_altitude():
    # NFZ 에서 멀리 떨어진 지점은 고도 규칙(G) 적용
    result = classify_airspace(60.0, lon=128.0, lat=36.0, nfz_zones=(_airport_nfz(),))
    assert result.icao_class == "G"


# --- 레이어 인덱스 ---


@pytest.mark.parametrize(
    "altitude,expected",
    [(0, 0), (29.9, 0), (30, 1), (150, 5), (151, 5), (240, 8)],
)
def test_layer_index(altitude, expected):
    assert sdacs_layer_index(altitude) == expected


def test_layer_index_above_ceiling_is_none():
    assert sdacs_layer_index(SIM_CEILING_AGL_M + 1) is None


# --- 입력 검증 ---


def test_negative_altitude_raises():
    with pytest.raises(ValueError):
        classify_airspace(-1.0)


def test_nan_altitude_raises():
    with pytest.raises(ValueError):
        classify_airspace(math.nan)


def test_lon_without_lat_raises():
    with pytest.raises(ValueError):
        classify_airspace(30.0, lon=126.0)


def test_invalid_nfz_kind_raises():
    with pytest.raises(ValueError):
        NoFlyZone("x", 126.0, 37.0, 100.0, kind="ocean")


def test_nonpositive_nfz_radius_raises():
    with pytest.raises(ValueError):
        NoFlyZone("x", 126.0, 37.0, 0.0)


# --- 결정성 / 요건 ---


def test_classification_is_deterministic():
    a = classify_airspace(170.0)
    b = classify_airspace(170.0)
    assert a == b
    assert isinstance(a, AirspaceClassification)


def test_class_d_requirements_superset_of_g():
    g = set(CLASS_REQUIREMENTS["G"])
    d = set(CLASS_REQUIREMENTS["D"])
    assert g.issubset(d)


def test_class_g_layers_cover_legal_range():
    # 0~150 m 의 모든 표준 레이어는 Class G
    for layer in ALTITUDE_LAYERS:
        if layer <= LEGAL_CEILING_AGL_M:
            assert classify_airspace(float(layer)).icao_class == "G"
