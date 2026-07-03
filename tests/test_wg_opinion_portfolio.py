"""ODYSSEY Phase 473 — 국제 워킹그룹 의견서 포트폴리오 추적기 테스트.

핵심 계약 검증: 판정 위임(Phase 472 ``assess`` 재사용·복제 0)·밴드 집계
정확성(ready/needs_work/not_ready 분류·진행도·완료 판정)·발목 요건 롤업(빈도
내림차순·동률 id 오름차순·빈도 0 제외·READY 후보 제외)·결정론·매니페스트 JSON
직렬화·CLI·현 포트폴리오 정직성(3건 목표 미달).
"""
from __future__ import annotations

import json

import pytest

from simulation.intl_wg_opinion_gate import (
    CRITERIA,
    STATUS_MET,
    STATUS_PARTIAL,
    STATUS_UNMET,
    OpinionLetter,
    assess,
)
from simulation.wg_opinion_portfolio import (
    BAND_TARGET,
    PortfolioEntry,
    PortfolioReport,
    assess_portfolio,
    blocking_criteria,
    main,
    portfolio,
    portfolio_manifest,
)

pytestmark = pytest.mark.unit

_CRITERION_IDS = tuple(c.criterion_id for c in CRITERIA)


def _entry(target: str, **overrides: str) -> PortfolioEntry:
    """기본 전부 MET 의견서에 일부 기준만 덮어쓴 후보 엔트리 생성."""
    statuses = dict.fromkeys(_CRITERION_IDS, STATUS_MET)
    statuses.update(overrides)
    letter = OpinionLetter(target=target, statuses=statuses)
    return PortfolioEntry(letter=letter, assessment=assess(letter))


# --- 포트폴리오 구성 -------------------------------------------------------
def test_portfolio_has_band_target_entries():
    # 밴드 471-480 이 명시한 3건 목표를 그대로 등록.
    assert len(portfolio()) == BAND_TARGET == 3


def test_portfolio_targets_unique():
    labels = [e.label for e in portfolio()]
    assert len(labels) == len(set(labels))


def test_portfolio_reuses_phase472_shipped_letter():
    # 첫 건은 Phase 472 shipped_letter 를 복제 없이 재사용(DRY).
    from simulation.intl_wg_opinion_gate import shipped_letter

    jarus = shipped_letter()
    assert any(e.label == jarus.target for e in portfolio())


def test_entry_assessment_delegates_to_gate():
    # 엔트리 판정은 Phase 472 assess 결과와 정확히 일치(복제 아님).
    for e in portfolio():
        assert e.assessment == assess(e.letter)


# --- 밴드 집계 -------------------------------------------------------------
def test_assess_portfolio_classifies_by_verdict():
    entries = (
        _entry("ready-1"),                               # 전부 MET → READY
        _entry("work-1", **{"WG-02": STATUS_PARTIAL}),   # CRITICAL PARTIAL → WORK
        _entry("stop-1", **{"WG-01": STATUS_UNMET}),     # CRITICAL UNMET → STOP
    )
    report = assess_portfolio(entries)
    assert report.ready == ("ready-1",)
    assert report.needs_work == ("work-1",)
    assert report.not_ready == ("stop-1",)
    assert report.total == 3


def test_progress_is_ready_over_target():
    entries = (_entry("r1"), _entry("r2"), _entry("stop", **{"WG-01": STATUS_UNMET}))
    report = assess_portfolio(entries, target=3)
    assert report.ready_count == 2
    assert report.progress == pytest.approx(2 / 3, abs=1e-4)
    assert not report.is_band_complete


def test_band_complete_when_target_met():
    entries = (_entry("r1"), _entry("r2"), _entry("r3"))
    report = assess_portfolio(entries, target=3)
    assert report.is_band_complete
    assert report.progress == 1.0


def test_progress_caps_at_one_when_over_target():
    # 목표 초과 제출 가능해도 진행도는 1.0 을 넘지 않는다.
    entries = (_entry("r1"), _entry("r2"))
    report = assess_portfolio(entries, target=1)
    assert report.ready_count == 2
    assert report.progress == 1.0
    assert report.is_band_complete


def test_progress_zero_target_safe():
    report = PortfolioReport(target=0, ready=(), needs_work=(), not_ready=())
    assert report.progress == 0.0


def test_zero_target_is_not_band_complete():
    # progress 0.0 과 정합 — target<=0 은 완료로 보지 않는다(모순 차단).
    report = PortfolioReport(target=0, ready=(), needs_work=(), not_ready=())
    assert not report.is_band_complete


def test_negative_target_rejected():
    with pytest.raises(ValueError):
        assess_portfolio((), target=-1)


# --- 발목 요건 롤업 --------------------------------------------------------
def test_blocking_criteria_counts_non_met_among_unready():
    entries = (
        _entry("a", **{"WG-02": STATUS_PARTIAL}),               # WG-02 미완
        _entry("b", **{"WG-02": STATUS_UNMET, "WG-06": STATUS_UNMET}),  # WG-02·WG-06
    )
    rolled = dict(blocking_criteria(entries))
    assert rolled["WG-02"] == 2
    assert rolled["WG-06"] == 1


def test_blocking_criteria_excludes_ready_letters():
    # 제출 가능(전부 MET) 후보는 롤업에서 제외.
    entries = (_entry("ready"), _entry("blocked", **{"WG-02": STATUS_UNMET}))
    rolled = dict(blocking_criteria(entries))
    assert rolled.get("WG-02") == 1
    assert len(rolled) == 1


def test_blocking_criteria_sorted_by_frequency_then_id():
    entries = (
        _entry("a", **{"WG-02": STATUS_UNMET, "WG-06": STATUS_UNMET}),
        _entry("b", **{"WG-02": STATUS_UNMET, "WG-01": STATUS_UNMET}),
    )
    rolled = blocking_criteria(entries)
    # WG-02=2(최다 먼저), 그다음 빈도 1 동률은 id 오름차순(WG-01 < WG-06).
    assert rolled[0] == ("WG-02", 2)
    assert rolled[1] == ("WG-01", 1)
    assert rolled[2] == ("WG-06", 1)


def test_blocking_criteria_empty_when_all_ready():
    entries = (_entry("r1"), _entry("r2"))
    assert blocking_criteria(entries) == ()


def test_blocking_criteria_excludes_zero_frequency():
    entries = (_entry("a", **{"WG-02": STATUS_UNMET}),)
    rolled = blocking_criteria(entries)
    ids = [cid for cid, _ in rolled]
    assert ids == ["WG-02"]  # 미완 0 인 기준은 잡음으로 제외


# --- 결정론 ----------------------------------------------------------------
def test_deterministic():
    assert assess_portfolio() == assess_portfolio()
    assert blocking_criteria() == blocking_criteria()
    assert portfolio_manifest() == portfolio_manifest()


# --- 현 포트폴리오 정직성 --------------------------------------------------
def test_shipped_portfolio_is_honest_about_shortfall():
    # 현 3건은 아직 아무도 제출 가능하지 않음(격상 없는 정직 공시).
    report = assess_portfolio()
    assert report.total == 3
    assert report.ready_count == 0
    assert not report.is_band_complete


def test_shipped_blocker_is_submission_channel():
    # EUROCAE(Phase 474)·ISO(잔여 완결) redline(WG-02) 완성 뒤로, 포트폴리오의
    # 최대 발목은 제출 채널·기한(WG-06)으로 정직하게 이동했다 — WG-06 은 3건
    # 전부에서 미완(외부 회람·검토 기한 의존)이라 빈도 최다. WG-02 는 JARUS
    # 1건만 막는다(redline 산문 수준 PARTIAL).
    rolled = dict(blocking_criteria())
    assert rolled["WG-06"] == 3
    assert max(rolled.values()) == rolled["WG-06"]
    assert rolled["WG-02"] == 1


# --- 매니페스트 ------------------------------------------------------------
def test_manifest_json_serialisable():
    blob = json.dumps(portfolio_manifest(), ensure_ascii=False)
    restored = json.loads(blob)
    assert restored["schema"] == "sdacs-wg-opinion-portfolio"
    assert restored["band"] == "471-480"
    assert restored["target"] == 3
    assert len(restored["entries"]) == 3


def test_manifest_progress_matches_report():
    manifest = portfolio_manifest()
    report = assess_portfolio()
    assert manifest["progress"] == report.progress
    assert manifest["ready_count"] == report.ready_count
    assert manifest["is_band_complete"] == report.is_band_complete


# --- CLI -------------------------------------------------------------------
@pytest.mark.parametrize("flag", ["--portfolio", "--report", "--blockers", "--manifest"])
def test_cli_known_flags_succeed(flag, capsys):
    assert main([flag]) == 0
    assert capsys.readouterr().out.strip()


def test_cli_default_is_portfolio(capsys):
    assert main([]) == 0
    assert "포트폴리오" in capsys.readouterr().out


def test_cli_rejects_unknown_flag(capsys):
    assert main(["--bogus"]) == 2
    assert "알 수 없는 인자" in capsys.readouterr().err
