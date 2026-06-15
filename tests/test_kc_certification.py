"""Phase 304 (GENESIS): KC 전파인증 요건 체크리스트 테스트.

통신 모듈별 적합성평가 유형 분류·체크리스트 생성·검증·export 의 결정성을 검증한다.
"""

import json

import pytest

from simulation.kc_certification import (
    CERT_CERTIFICATION,
    CERT_REGISTRATION,
    FREE_USE_BANDS,
    REQUIRED_DOCUMENTS,
    SPECIFIED_LOW_POWER_EIRP_LIMIT_DBM,
    CommModule,
    assess_module,
    build_checklist,
    export_json,
    export_text,
)


def _rc_link(power_dbm: float = 14.0) -> CommModule:
    return CommModule(
        name="2.4GHz RC 링크",
        band_mhz=2440.0,
        tx_power_dbm=power_dbm,
        is_transmitter=True,
        kind="data",
    )


def _gnss() -> CommModule:
    return CommModule(
        name="GNSS 수신기",
        band_mhz=1575.42,
        tx_power_dbm=0.0,
        is_transmitter=False,
        kind="gnss",
    )


# ── assess_module: 분류 규칙 ─────────────────────────────────────────────


def test_free_use_transmitter_within_limit_is_registration():
    a = assess_module(_rc_link(power_dbm=14.0))
    assert a.cert_type == CERT_REGISTRATION
    assert a.in_free_use_band is True
    # 적합등록은 자기시험으로 갈음 가능 → 지정시험기관 불요
    assert a.requires_designated_lab is False


def test_free_use_transmitter_over_power_limit_escalates_to_certification():
    over = SPECIFIED_LOW_POWER_EIRP_LIMIT_DBM + 5.0
    a = assess_module(_rc_link(power_dbm=over))
    assert a.cert_type == CERT_CERTIFICATION
    assert a.in_free_use_band is True
    assert any("초과" in r for r in a.reasons)


def test_receiver_only_module_is_registration_self_test():
    a = assess_module(_gnss())
    assert a.cert_type == CERT_REGISTRATION
    assert a.requires_designated_lab is False
    assert a.in_free_use_band is False


def test_cellular_module_is_certification():
    cell = CommModule(
        name="LTE 모듈",
        band_mhz=1850.0,
        tx_power_dbm=23.0,
        is_transmitter=True,
        kind="cellular",
    )
    a = assess_module(cell)
    assert a.cert_type == CERT_CERTIFICATION
    assert a.requires_designated_lab is True
    assert any("이동통신" in r for r in a.reasons)


def test_licensed_band_transmitter_is_certification():
    # 비면허 대역 외 송신기 (예: 1.2GHz 영상송신)
    vtx = CommModule(
        name="1.2GHz 영상송신",
        band_mhz=1200.0,
        tx_power_dbm=14.0,
        is_transmitter=True,
        kind="video",
    )
    a = assess_module(vtx)
    assert a.cert_type == CERT_CERTIFICATION
    assert a.in_free_use_band is False


def test_power_exactly_at_limit_stays_registration():
    a = assess_module(_rc_link(power_dbm=SPECIFIED_LOW_POWER_EIRP_LIMIT_DBM))
    assert a.cert_type == CERT_REGISTRATION


@pytest.mark.parametrize("band", FREE_USE_BANDS)
def test_each_free_use_band_low_power_is_registration(band):
    mid = (band.low_mhz + band.high_mhz) / 2
    a = assess_module(
        CommModule(name=f"{band.name} TX", band_mhz=mid, tx_power_dbm=10.0)
    )
    assert a.cert_type == CERT_REGISTRATION
    assert a.in_free_use_band is True


def test_assess_is_deterministic():
    m = _rc_link()
    assert assess_module(m) == assess_module(m)


# ── build_checklist: 집계 ────────────────────────────────────────────────


def test_checklist_overall_is_strictest_type():
    registration_only = [_rc_link(), _gnss()]  # 둘 다 적합등록
    cl = build_checklist("SDACS-Drone", registration_only)
    assert cl["overall_cert_type"] == CERT_REGISTRATION

    with_cellular = [
        _rc_link(),
        _gnss(),
        CommModule(name="LTE", band_mhz=1850.0, tx_power_dbm=23.0, kind="cellular"),
    ]
    cl2 = build_checklist("SDACS-Drone", with_cellular)
    assert cl2["overall_cert_type"] == CERT_CERTIFICATION


def test_checklist_documents_match_overall_type():
    cl = build_checklist("SDACS-Drone", [_rc_link()])
    assert cl["required_documents"] == list(REQUIRED_DOCUMENTS[CERT_REGISTRATION])


def test_checklist_lists_every_module():
    modules = [_rc_link(), _gnss()]
    cl = build_checklist("SDACS-Drone", modules)
    assert len(cl["modules"]) == 2
    names = {m["name"] for m in cl["modules"]}
    assert names == {"2.4GHz RC 링크", "GNSS 수신기"}


def test_checklist_requires_designated_lab_if_any_module_does():
    # 적합등록만(자기시험 가능) → 지정시험기관 불요
    cl_reg = build_checklist("SDACS-Drone", [_rc_link(), _gnss()])
    assert cl_reg["requires_designated_lab"] is False

    # 적합인증 모듈(셀룰러) 포함 → 지정시험기관 필요
    cell = CommModule(name="LTE", band_mhz=1850.0, tx_power_dbm=23.0, kind="cellular")
    cl_cert = build_checklist("SDACS-Drone", [_rc_link(), cell])
    assert cl_cert["requires_designated_lab"] is True


def test_designated_lab_matches_certification_type():
    # 일관성: 지정시험기관 필요 ⇔ 적합인증
    for module in (
        _rc_link(),
        _gnss(),
        CommModule(name="LTE", band_mhz=1850.0, tx_power_dbm=23.0, kind="cellular"),
        CommModule(name="1.2GHz VTX", band_mhz=1200.0, tx_power_dbm=14.0, kind="video"),
    ):
        a = assess_module(module)
        assert a.requires_designated_lab == (a.cert_type == CERT_CERTIFICATION)


# ── 입력 검증 ────────────────────────────────────────────────────────────


def test_empty_product_name_raises():
    with pytest.raises(ValueError, match="제품명"):
        build_checklist("", [_rc_link()])


def test_empty_modules_raises():
    with pytest.raises(ValueError, match="모듈"):
        build_checklist("SDACS-Drone", [])


def test_transmitter_zero_power_raises():
    bad = CommModule(name="bad TX", band_mhz=2440.0, tx_power_dbm=0.0)
    with pytest.raises(ValueError, match="공중선전력"):
        build_checklist("SDACS-Drone", [bad])


def test_negative_band_raises():
    bad = CommModule(name="bad", band_mhz=-1.0, tx_power_dbm=10.0)
    with pytest.raises(ValueError, match="주파수"):
        build_checklist("SDACS-Drone", [bad])


# ── export ───────────────────────────────────────────────────────────────


def test_export_json_roundtrip_and_sorted():
    cl = build_checklist("SDACS-Drone", [_rc_link(), _gnss()])
    s = export_json(cl)
    assert json.loads(s) == cl
    # sort_keys=True → 결정적 직렬화
    assert export_json(cl) == s


def test_export_text_contains_key_fields():
    cl = build_checklist("SDACS-Drone", [_rc_link(), _gnss()])
    txt = export_text(cl)
    assert "KC 전파인증" in txt
    assert "SDACS-Drone" in txt
    assert "2.4GHz RC 링크" in txt
    assert "GNSS 수신기" in txt
    assert "제출 서류" in txt


def test_export_text_is_deterministic():
    cl = build_checklist("SDACS-Drone", [_rc_link()])
    assert export_text(cl) == export_text(cl)
