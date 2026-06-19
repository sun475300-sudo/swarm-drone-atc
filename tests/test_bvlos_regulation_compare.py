"""Phase 409 (ODYSSEY): 다국 BVLOS 규제 비교 테스트.

`simulation/bvlos_regulation_compare.py` 의 결정적 비교·적합성 갭 산정을 검증한다.
근거: docs/certification/BVLOS_REGULATION_COMPARISON.md.
"""

from dataclasses import FrozenInstanceError

import pytest

from simulation.bvlos_regulation_compare import (
    COMPARISON_FIELDS,
    JURISDICTIONS,
    REGULATIONS,
    BvlosRegulation,
    ConformanceResult,
    OperationProfile,
    assess_all,
    assess_conformance,
    compare_field,
    comparison_matrix,
    get_regulation,
    to_dict,
    to_markdown_table,
)


def _full_profile(**overrides: object) -> OperationProfile:
    """모든 요건을 충족하는 기준 프로파일 (개별 필드만 override)."""
    base = dict(
        altitude_agl_m=100.0,
        has_remote_id=True,
        has_daa=True,
        has_operator_cert=True,
        has_aircraft_cert=True,
        has_insurance=True,
        over_people=False,
    )
    return OperationProfile(**{**base, **overrides})


# --- 테이블 무결성 ---


def test_four_jurisdictions_registered():
    assert JURISDICTIONS == ("KR", "US", "EU", "JP")
    assert set(REGULATIONS) == set(JURISDICTIONS)


def test_each_record_is_frozen_regulation():
    for code in JURISDICTIONS:
        reg = REGULATIONS[code]
        assert isinstance(reg, BvlosRegulation)
        assert reg.code == code
        with pytest.raises(FrozenInstanceError):
            reg.code = "XX"  # frozen → 변경 불가


def test_altitudes_are_positive():
    for code in JURISDICTIONS:
        assert REGULATIONS[code].max_altitude_agl_m > 0


def test_us_altitude_is_400ft_in_meters():
    # 400 ft AGL ≈ 121.92 m
    assert REGULATIONS["US"].max_altitude_agl_m == pytest.approx(121.92, abs=0.01)


# --- 조회 ---


def test_get_regulation_case_insensitive():
    assert get_regulation("kr") is REGULATIONS["KR"]
    assert get_regulation("Us") is REGULATIONS["US"]


def test_get_regulation_unknown_raises():
    with pytest.raises(ValueError):
        get_regulation("ZZ")


# --- 필드 비교 ---


def test_compare_field_covers_all_jurisdictions():
    result = compare_field("remote_id_required")
    assert set(result) == set(JURISDICTIONS)
    assert all(v is True for v in result.values())  # 4개국 모두 Remote ID 의무


def test_compare_field_unknown_raises():
    with pytest.raises(ValueError):
        compare_field("nonexistent_field")


def test_comparison_matrix_keys_match_comparison_fields():
    matrix = comparison_matrix()
    expected = [name for name, _label in COMPARISON_FIELDS]
    assert list(matrix) == expected
    for field_map in matrix.values():
        assert list(field_map) == list(JURISDICTIONS)  # 삽입순서 보존


def test_comparison_matrix_is_deterministic():
    assert comparison_matrix() == comparison_matrix()


# --- 적합성 갭 산정 ---


def test_full_profile_conformant_everywhere():
    results = assess_all(_full_profile())
    assert set(results) == set(JURISDICTIONS)
    for res in results.values():
        assert res.conformant is True
        assert res.gaps == ()


def test_missing_remote_id_flagged():
    res = assess_conformance(_full_profile(has_remote_id=False), "KR")
    assert res.conformant is False
    assert any("Remote ID" in g for g in res.gaps)


def test_missing_insurance_flagged_where_required_only():
    profile = _full_profile(has_insurance=False)
    # US 는 연방 보험 의무 아님 → 갭 없음
    assert assess_conformance(profile, "US").conformant is True
    # KR/EU/JP 는 보험 의무 → 갭 발생
    for code in ("KR", "EU", "JP"):
        res = assess_conformance(profile, code)
        assert res.conformant is False
        assert any("보험" in g for g in res.gaps)


def test_altitude_exceedance_flagged():
    # EU 기본 상한 120 m 초과
    res = assess_conformance(_full_profile(altitude_agl_m=130.0), "EU")
    assert res.conformant is False
    assert any("고도 초과" in g for g in res.gaps)


def test_over_people_allowed_differs_by_jurisdiction():
    profile = _full_profile(over_people=True)
    # US·JP 는 기본 카테고리 내 사람 위 비행 허용
    assert assess_conformance(profile, "US").conformant is True
    assert assess_conformance(profile, "JP").conformant is True
    # KR·EU 는 별도 승인 필요 → 갭
    assert assess_conformance(profile, "KR").conformant is False
    assert assess_conformance(profile, "EU").conformant is False


def test_negative_altitude_raises():
    with pytest.raises(ValueError):
        assess_conformance(_full_profile(altitude_agl_m=-1.0), "KR")


def test_non_finite_altitude_raises():
    with pytest.raises(ValueError):
        assess_conformance(_full_profile(altitude_agl_m=float("nan")), "KR")


def test_conformance_result_is_frozen():
    res = assess_conformance(_full_profile(), "KR")
    assert isinstance(res, ConformanceResult)
    with pytest.raises(FrozenInstanceError):
        res.conformant = False


# --- export ---


def test_markdown_table_has_all_rows_and_columns():
    table = to_markdown_table()
    lines = table.splitlines()
    # 헤더 + 구분선 + COMPARISON_FIELDS 행 수
    assert len(lines) == 2 + len(COMPARISON_FIELDS)
    # 헤더에 4개국 표시명 포함
    for code in JURISDICTIONS:
        assert REGULATIONS[code].name in lines[0]
    # bool 필드는 ✅/❌ 로 렌더
    assert "✅" in table


def test_to_dict_round_trips_all_fields():
    data = to_dict()
    assert set(data) == set(JURISDICTIONS)
    for code in JURISDICTIONS:
        assert set(data[code]) == set(BvlosRegulation.__dataclass_fields__)
        assert data[code]["code"] == code
