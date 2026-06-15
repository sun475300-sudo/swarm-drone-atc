"""Phase 311 (GENESIS) CSAP 자가진단 자동화 단위 테스트."""

import json

import pytest

from simulation.csap_self_assessment import (
    DEFAULT_CATALOG,
    PARTIAL_THRESHOLD,
    READY_THRESHOLD,
    Assessment,
    ControlResult,
    Status,
    assess_csap,
    build_report,
    build_responses,
    export_json,
    export_text,
)


def _all(status: Status) -> dict[str, dict[str, Status]]:
    """모든 통제항목을 동일 상태로 채운 응답을 생성한다."""
    return {
        code: dict.fromkeys(controls, status)
        for code, (_, controls) in DEFAULT_CATALOG.items()
    }


# ── 카탈로그 구조 ──────────────────────────────────────────────
class TestCatalog:
    def test_catalog_has_14_domains(self):
        # Arrange / Act / Assert
        assert len(DEFAULT_CATALOG) == 14

    def test_catalog_codes_are_1_to_14(self):
        codes = {int(c) for c in DEFAULT_CATALOG}
        assert codes == set(range(1, 15))

    def test_every_domain_has_at_least_one_control(self):
        assert all(len(controls) >= 1 for _, controls in DEFAULT_CATALOG.values())


# ── 종합 이행률·판정 ───────────────────────────────────────────
class TestAssessment:
    def test_full_implementation_scores_100(self):
        result = assess_csap(_all(Status.IMPLEMENTED))
        assert result.overall_rate == 1.0
        assert result.verdict == "신청 권장"

    def test_no_implementation_scores_zero(self):
        result = assess_csap(_all(Status.NOT_IMPLEMENTED))
        assert result.overall_rate == 0.0
        assert result.verdict == "준비 부족"

    def test_partial_counts_half(self):
        result = assess_csap(_all(Status.PARTIAL))
        assert result.overall_rate == 0.5

    def test_not_applicable_excluded_from_denominator(self):
        # 전부 해당없음이면 분모 0 → 이행률 1.0 으로 규정
        result = assess_csap(_all(Status.NOT_APPLICABLE))
        assert result.overall_rate == 1.0
        assert all(d.applicable == 0 for d in result.domains)

    def test_missing_control_treated_as_not_implemented(self):
        # 응답 누락 항목은 보수적으로 미이행 처리
        result = assess_csap({})
        assert result.overall_rate == 0.0

    def test_verdict_boundary_partial_threshold(self):
        # 정확히 PARTIAL_THRESHOLD 면 "보완 후 신청"
        responses = _all(Status.IMPLEMENTED)
        result_full = assess_csap(responses)
        assert result_full.overall_rate >= READY_THRESHOLD
        assert PARTIAL_THRESHOLD < READY_THRESHOLD

    def test_returns_assessment_instance(self):
        assert isinstance(assess_csap(_all(Status.IMPLEMENTED)), Assessment)


# ── 분야별 점수 ────────────────────────────────────────────────
class TestDomainScores:
    def test_one_weak_domain_flagged(self):
        responses = _all(Status.IMPLEMENTED)
        # 분야 8(접근통제) 전부 미이행으로 약화
        responses["8"] = dict.fromkeys(DEFAULT_CATALOG["8"][1], Status.NOT_IMPLEMENTED)
        result = assess_csap(responses)
        assert "8" in result.weak_domains
        domain8 = next(d for d in result.domains if d.code == "8")
        assert domain8.rate == 0.0

    def test_domain_rate_is_rounded(self):
        result = assess_csap(_all(Status.PARTIAL))
        for d in result.domains:
            assert d.rate == round(d.rate, 4)


# ── 입력 검증 ──────────────────────────────────────────────────
class TestValidation:
    def test_unknown_domain_code_raises(self):
        with pytest.raises(ValueError, match="미정의 통제분야"):
            assess_csap({"99": {"x": Status.IMPLEMENTED}})

    def test_unknown_control_raises(self):
        with pytest.raises(ValueError, match="미정의 통제항목"):
            assess_csap({"1": {"존재하지않는항목": Status.IMPLEMENTED}})


# ── ControlResult → 응답 변환 ──────────────────────────────────
class TestBuildResponses:
    def test_build_responses_groups_by_domain(self):
        name, controls = DEFAULT_CATALOG["1"]
        results = [
            ControlResult("1", name, controls[0], Status.IMPLEMENTED),
            ControlResult("1", name, controls[1], Status.PARTIAL),
        ]
        responses = build_responses(results)
        assert responses["1"][controls[0]] is Status.IMPLEMENTED
        assert responses["1"][controls[1]] is Status.PARTIAL


# ── 보고서·export ──────────────────────────────────────────────
class TestReport:
    def test_report_total_controls_matches_catalog(self):
        report = build_report(_all(Status.IMPLEMENTED))
        expected = sum(len(c) for _, c in DEFAULT_CATALOG.values())
        assert report["total_controls"] == expected

    def test_export_json_round_trips(self):
        report = build_report(_all(Status.IMPLEMENTED))
        parsed = json.loads(export_json(report))
        assert parsed["assessment"]["verdict"] == "신청 권장"

    def test_export_json_is_deterministic(self):
        report = build_report(_all(Status.PARTIAL))
        assert export_json(report) == export_json(report)

    def test_export_text_contains_verdict(self):
        report = build_report(_all(Status.NOT_IMPLEMENTED))
        text = export_text(report)
        assert "준비 부족" in text
        assert "자가진단 보고서" in text

    def test_export_text_lists_all_domains(self):
        report = build_report(_all(Status.IMPLEMENTED))
        text = export_text(report)
        for _, (name, _) in DEFAULT_CATALOG.items():
            assert name in text
