"""Phase 304 (GENESIS): KC 전파인증 요건 체크리스트 테스트.

통신 모듈별 적합성평가 종류 분류·대역/출력 적합성 판정·검증·export 의 결정성을 검증한다.
"""

import json

import pytest

from simulation.kc_radio_certification import (
    CATEGORY_CERTIFICATION,
    CATEGORY_PROVISIONAL,
    CATEGORY_REGISTRATION,
    KIND_CELLULAR,
    KIND_GNSS_RECEIVER,
    KIND_ISM_LOWPOWER,
    KIND_NOVEL,
    KOREA_KC_BANDS,
    CommModule,
    KcBand,
    assess_module,
    build_checklist,
    classify_category,
    export_json,
    export_text,
    find_band,
)


def _rc_module(power_dbm: float = 15.0) -> CommModule:
    return CommModule(
        name="2.4GHz 무선조종",
        kind=KIND_ISM_LOWPOWER,
        freq_min_mhz=2400.0,
        freq_max_mhz=2483.5,
        tx_power_dbm=power_dbm,
    )


def _video_module() -> CommModule:
    return CommModule(
        name="5.8GHz 영상송신",
        kind=KIND_ISM_LOWPOWER,
        freq_min_mhz=5725.0,
        freq_max_mhz=5825.0,
        tx_power_dbm=20.0,
    )


def _lte_module() -> CommModule:
    return CommModule(
        name="LTE 모뎀",
        kind=KIND_CELLULAR,
        freq_min_mhz=1805.0,
        freq_max_mhz=1880.0,
        tx_power_dbm=23.0,
    )


def _gnss_module() -> CommModule:
    return CommModule(
        name="GNSS 수신기",
        kind=KIND_GNSS_RECEIVER,
        freq_min_mhz=1575.42,
        freq_max_mhz=1575.42,
        tx_power_dbm=0.0,
        is_transmitter=False,
    )


# ── 분류 로직 ─────────────────────────────────────────────


def test_cellular_classified_as_certification():
    assert classify_category(_lte_module()) == CATEGORY_CERTIFICATION


def test_ism_classified_as_registration():
    assert classify_category(_rc_module()) == CATEGORY_REGISTRATION


def test_gnss_receiver_classified_as_registration():
    assert classify_category(_gnss_module()) == CATEGORY_REGISTRATION


def test_novel_classified_as_provisional():
    novel = CommModule(
        name="신기술 송신기", kind=KIND_NOVEL,
        freq_min_mhz=6000.0, freq_max_mhz=6100.0, tx_power_dbm=10.0,
    )
    assert classify_category(novel) == CATEGORY_PROVISIONAL


def test_unknown_kind_raises():
    bad = CommModule(name="X", kind="quantum", freq_min_mhz=10.0, freq_max_mhz=20.0)
    with pytest.raises(ValueError, match="알 수 없는 모듈 종류"):
        classify_category(bad)


# ── 대역/출력 판정 ────────────────────────────────────────


def test_find_band_for_ism_24():
    band = find_band(_rc_module(), KOREA_KC_BANDS)
    assert band is not None
    assert "2.4 GHz" in band.name


def test_ism_module_within_band_and_power_is_clear():
    assessment = assess_module(_rc_module(power_dbm=15.0))

    assert assessment.in_permitted_band is True
    assert assessment.power_ok is True
    assert assessment.issues == ()


def test_ism_module_over_power_limit_flags_issue():
    # 2.4 GHz 대역 한계 20 dBm을 초과
    assessment = assess_module(_rc_module(power_dbm=25.0))

    assert assessment.in_permitted_band is True
    assert assessment.power_ok is False
    assert any("초과" in i for i in assessment.issues)


def test_ism_module_out_of_band_flags_issue():
    out = CommModule(
        name="비허용대역", kind=KIND_ISM_LOWPOWER,
        freq_min_mhz=3000.0, freq_max_mhz=3100.0, tx_power_dbm=10.0,
    )
    assessment = assess_module(out)

    assert assessment.in_permitted_band is False
    assert any("허용 소출력 대역" in i for i in assessment.issues)


def test_cellular_out_of_lowpower_band_is_not_an_issue():
    # 셀룰러는 사업자 면허 대역 사용 → 소출력 대역 미포함이 정상
    assessment = assess_module(_lte_module())

    assert assessment.category == CATEGORY_CERTIFICATION
    assert assessment.in_permitted_band is False
    assert assessment.issues == ()


def test_novel_out_of_band_is_not_an_issue():
    # 잠정인증은 기존 표준이 없으므로 소출력 대역 미포함이 정상(지적 없음)
    novel = CommModule(
        name="신기술송신기", kind=KIND_NOVEL,
        freq_min_mhz=6000.0, freq_max_mhz=6100.0, tx_power_dbm=10.0,
    )
    assessment = assess_module(novel)

    assert assessment.category == CATEGORY_PROVISIONAL
    assert assessment.in_permitted_band is False
    assert assessment.issues == ()


def test_receiver_skips_band_and_power_checks():
    assessment = assess_module(_gnss_module())

    assert assessment.in_permitted_band is True
    assert assessment.power_ok is True
    assert assessment.matched_band == "(수신전용)"
    assert assessment.issues == ()


def test_power_exactly_at_limit_is_ok():
    # 2.4 GHz 한계 20 dBm 정확히 = 초과(>)가 아니므로 적합
    assessment = assess_module(_rc_module(power_dbm=20.0))
    assert assessment.power_ok is True


def test_custom_bands_override():
    bands = (KcBand("협대역", 100.0, 200.0, 5.0),)
    module = CommModule(
        name="협대역송신", kind=KIND_ISM_LOWPOWER,
        freq_min_mhz=120.0, freq_max_mhz=150.0, tx_power_dbm=3.0,
    )
    assessment = assess_module(module, bands=bands)

    assert assessment.matched_band == "협대역"
    assert assessment.power_ok is True


# ── 문서 요건 ─────────────────────────────────────────────


def test_certification_requires_designated_lab_report():
    assessment = assess_module(_lte_module())
    assert "지정시험기관 시험성적서(필수)" in assessment.required_documents


def test_provisional_requires_reason_and_draft_standard():
    novel = CommModule(
        name="신기술", kind=KIND_NOVEL,
        freq_min_mhz=6000.0, freq_max_mhz=6100.0, tx_power_dbm=10.0,
    )
    docs = assess_module(novel).required_documents
    assert "잠정인증 신청 사유서" in docs
    assert "기술기준(안)" in docs


# ── 체크리스트 생성 / 검증 ────────────────────────────────


def test_build_checklist_structure_and_determinism():
    modules = [_rc_module(), _video_module(), _lte_module(), _gnss_module()]

    first = build_checklist(modules)
    second = build_checklist(modules)

    assert first == second  # 결정성
    assert first["form_type"] == "kc_radio_certification_checklist"
    assert first["module_count"] == 4
    assert first["all_clear"] is True


def test_build_checklist_all_clear_false_when_issue_present():
    modules = [_rc_module(power_dbm=30.0)]  # 출력 초과

    checklist = build_checklist(modules)

    assert checklist["all_clear"] is False
    assert checklist["items"][0]["power_ok"] is False


def test_empty_module_list_raises():
    with pytest.raises(ValueError, match="비어 있음"):
        build_checklist([])


def test_invalid_module_freq_raises():
    bad = CommModule(
        name="잘못된주파수", kind=KIND_ISM_LOWPOWER,
        freq_min_mhz=2000.0, freq_max_mhz=1000.0,
    )
    with pytest.raises(ValueError, match="최대 주파수"):
        build_checklist([bad])


def test_zero_bandwidth_transmitter_raises():
    bad = CommModule(
        name="영대역송신", kind=KIND_ISM_LOWPOWER,
        freq_min_mhz=2450.0, freq_max_mhz=2450.0, tx_power_dbm=10.0,
    )
    with pytest.raises(ValueError, match="영대역"):
        build_checklist([bad])


def test_invalid_kind_in_build_raises():
    bad = CommModule(name="X", kind="bogus", freq_min_mhz=10.0, freq_max_mhz=20.0)
    with pytest.raises(ValueError, match="유효하지 않음"):
        build_checklist([bad])


# ── export ────────────────────────────────────────────────


def test_export_json_roundtrip():
    checklist = build_checklist([_rc_module(), _gnss_module()])

    text = export_json(checklist)
    parsed = json.loads(text)

    assert parsed == checklist


def test_export_text_contains_key_fields():
    checklist = build_checklist([_lte_module(), _rc_module(power_dbm=30.0)])

    text = export_text(checklist)

    assert "KC 전파인증" in text
    assert "LTE 모뎀" in text
    assert "적합인증" in text
    assert "지적사항" in text  # 출력 초과 모듈 포함
