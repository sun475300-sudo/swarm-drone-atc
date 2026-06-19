"""ODYSSEY Phase 481 — 의존성 자동 갱신 회귀 게이트 정책 테스트.

핵심 계약 검증: SemVer 파싱·점프 분류·결정 우선순위(게이트 우선)·정책
매트릭스와 evaluate() 의 일치·결정론·매니페스트 JSON 직렬화.
"""
from __future__ import annotations

import json

import pytest

from simulation.dependency_gate import (
    BUMP_DOWNGRADE,
    BUMP_MAJOR,
    BUMP_MINOR,
    BUMP_NONE,
    BUMP_PATCH,
    BUMP_UNKNOWN,
    CLASS_CI,
    CLASS_DEV,
    CLASS_RUNTIME,
    DECISION_AUTO_MERGE,
    DECISION_BLOCK,
    DECISION_REVIEW_REQUIRED,
    POLICY_MATRIX,
    DependencyUpdate,
    GateDecision,
    RegressionGate,
    SemVer,
    classify_bump,
    evaluate,
    policy_manifest,
)

pytestmark = pytest.mark.unit


def _green() -> RegressionGate:
    return RegressionGate(tests_passed=True, coverage_ok=True)


def _update(
    bump_from: str = "1.0.0",
    bump_to: str = "1.0.1",
    dep_class: str = CLASS_RUNTIME,
    gate: RegressionGate | None = None,
) -> DependencyUpdate:
    return DependencyUpdate(
        name="pkg",
        ecosystem="pip",
        from_version=bump_from,
        to_version=bump_to,
        dep_class=dep_class,
        gate=gate if gate is not None else _green(),
    )


class TestSemVerParse:
    def test_parses_full_triple(self):
        assert SemVer.parse("1.2.3").as_tuple() == (1, 2, 3)

    def test_pads_missing_components(self):
        assert SemVer.parse("4").as_tuple() == (4, 0, 0)
        assert SemVer.parse("4.2").as_tuple() == (4, 2, 0)

    def test_strips_leading_v(self):
        assert SemVer.parse("v2.1.0").as_tuple() == (2, 1, 0)

    def test_drops_prerelease_and_build_tail(self):
        assert SemVer.parse("1.2.3-rc1").as_tuple() == (1, 2, 3)
        assert SemVer.parse("1.2.3+build5").as_tuple() == (1, 2, 3)

    def test_non_numeric_returns_none(self):
        assert SemVer.parse("abc") is None
        assert SemVer.parse("1.x.0") is None

    def test_empty_returns_none(self):
        assert SemVer.parse("") is None

    def test_too_many_components_returns_none(self):
        assert SemVer.parse("1.2.3.4") is None

    def test_incomplete_version_with_hyphen_returns_none(self):
        # "1-2-3" 는 불완전 버전의 하이픈 → prerelease 가 아님 → None.
        assert SemVer.parse("1-2-3") is None
        assert SemVer.parse("1.2-rc1") is None

    def test_leading_zero_returns_none(self):
        assert SemVer.parse("01.0.0") is None
        assert SemVer.parse("1.02.0") is None
        assert SemVer.parse("1.0.07") is None

    def test_zero_components_are_valid(self):
        assert SemVer.parse("0.0.0").as_tuple() == (0, 0, 0)
        assert SemVer.parse("1.0.0").as_tuple() == (1, 0, 0)


class TestClassifyBump:
    def test_patch(self):
        assert classify_bump("1.0.0", "1.0.1") == BUMP_PATCH

    def test_minor(self):
        assert classify_bump("1.0.5", "1.1.0") == BUMP_MINOR

    def test_major(self):
        assert classify_bump("1.9.9", "2.0.0") == BUMP_MAJOR

    def test_major_from_bare_versions(self):
        assert classify_bump("4", "5") == BUMP_MAJOR

    def test_none_when_equal(self):
        assert classify_bump("1.2.3", "1.2.3") == BUMP_NONE

    def test_downgrade(self):
        assert classify_bump("2.0.0", "1.9.9") == BUMP_DOWNGRADE

    def test_unknown_when_unparsable(self):
        assert classify_bump("1.0.0", "latest") == BUMP_UNKNOWN
        assert classify_bump("main", "1.0.0") == BUMP_UNKNOWN


class TestGateBlocks:
    def test_conflicts_block_even_when_tests_pass(self):
        gate = RegressionGate(tests_passed=True, coverage_ok=True, has_conflicts=True)
        decision = evaluate(_update(gate=gate))
        assert decision.decision == DECISION_BLOCK

    def test_failed_tests_block(self):
        gate = RegressionGate(tests_passed=False, coverage_ok=True)
        decision = evaluate(_update(gate=gate))
        assert decision.decision == DECISION_BLOCK

    def test_downgrade_blocks(self):
        decision = evaluate(_update("2.0.0", "1.0.0"))
        assert decision.decision == DECISION_BLOCK
        assert decision.bump == BUMP_DOWNGRADE

    def test_gate_block_precedes_downgrade(self):
        # 충돌이 다운그레이드보다 먼저 평가되지만 둘 다 BLOCK 이다.
        gate = RegressionGate(tests_passed=True, coverage_ok=True, has_conflicts=True)
        decision = evaluate(_update("2.0.0", "1.0.0", gate=gate))
        assert decision.decision == DECISION_BLOCK
        assert "충돌" in decision.reasons[0]

    def test_unknown_dep_class_blocks(self):
        decision = evaluate(_update(dep_class="mystery"))
        assert decision.decision == DECISION_BLOCK

    def test_failed_tests_supersede_downgrade(self):
        # 게이트 우선: 테스트 실패가 다운그레이드보다 먼저 매칭되어 BLOCK.
        gate = RegressionGate(tests_passed=False, coverage_ok=True)
        decision = evaluate(_update("2.0.0", "1.0.0", gate=gate))
        assert decision.decision == DECISION_BLOCK
        assert decision.bump == BUMP_DOWNGRADE
        assert "테스트" in decision.reasons[0]

    def test_no_change_with_failed_gate_blocks(self):
        # NONE bump 이라도 테스트 실패면 rule 3 이 rule 6 보다 먼저 → BLOCK.
        gate = RegressionGate(tests_passed=False, coverage_ok=True)
        decision = evaluate(_update("1.2.3", "1.2.3", gate=gate))
        assert decision.decision == DECISION_BLOCK
        assert decision.bump == BUMP_NONE


class TestReviewRequired:
    def test_unknown_version_requires_review(self):
        decision = evaluate(_update("1.0.0", "latest"))
        assert decision.decision == DECISION_REVIEW_REQUIRED
        assert decision.bump == BUMP_UNKNOWN

    def test_no_change_requires_review(self):
        decision = evaluate(_update("1.2.3", "1.2.3"))
        assert decision.decision == DECISION_REVIEW_REQUIRED
        assert decision.bump == BUMP_NONE

    def test_coverage_miss_demotes_auto_merge(self):
        gate = RegressionGate(tests_passed=True, coverage_ok=False)
        # patch/runtime 는 GREEN 이면 AUTO_MERGE 지만 커버리지 미달이면 리뷰.
        decision = evaluate(_update("1.0.0", "1.0.1", gate=gate))
        assert decision.decision == DECISION_REVIEW_REQUIRED
        assert "커버리지" in decision.reasons[0]

    def test_minor_runtime_coverage_miss_blames_coverage(self):
        # MINOR/runtime 은 리뷰 후보지만, 커버리지(rule 7)가 bump 사유(rule 8)
        # 보다 먼저 매칭되어 reason 은 커버리지여야 한다.
        gate = RegressionGate(tests_passed=True, coverage_ok=False)
        decision = evaluate(_update("1.0.0", "1.1.0", CLASS_RUNTIME, gate=gate))
        assert decision.decision == DECISION_REVIEW_REQUIRED
        assert "커버리지" in decision.reasons[0]

    def test_major_always_requires_review(self):
        for dep_class in (CLASS_RUNTIME, CLASS_DEV, CLASS_CI):
            decision = evaluate(_update("1.0.0", "2.0.0", dep_class))
            assert decision.decision == DECISION_REVIEW_REQUIRED

    def test_runtime_minor_requires_review(self):
        decision = evaluate(_update("1.0.0", "1.1.0", CLASS_RUNTIME))
        assert decision.decision == DECISION_REVIEW_REQUIRED


class TestAutoMerge:
    def test_patch_runtime_auto_merges(self):
        decision = evaluate(_update("1.0.0", "1.0.1", CLASS_RUNTIME))
        assert decision.decision == DECISION_AUTO_MERGE

    def test_patch_dev_auto_merges(self):
        decision = evaluate(_update("1.0.0", "1.0.1", CLASS_DEV))
        assert decision.decision == DECISION_AUTO_MERGE

    def test_minor_dev_auto_merges(self):
        decision = evaluate(_update("1.0.0", "1.1.0", CLASS_DEV))
        assert decision.decision == DECISION_AUTO_MERGE

    def test_minor_ci_auto_merges(self):
        decision = evaluate(_update("1.0.0", "1.1.0", CLASS_CI))
        assert decision.decision == DECISION_AUTO_MERGE

    def test_patch_ci_auto_merges(self):
        decision = evaluate(_update("4.1.0", "4.1.1", CLASS_CI))
        assert decision.decision == DECISION_AUTO_MERGE


class TestPolicyMatrixConsistency:
    """POLICY_MATRIX(문서용 투영)가 evaluate()(권위)와 정확히 일치함을 강제.

    이로써 매트릭스가 evaluate 의 *중복 로직*이 아니라 검증된 투영임을 보장
    한다 — 둘이 어긋나면 테스트가 깨진다.
    """

    def test_matrix_covers_exactly_green_eligible_keys(self):
        # 매트릭스는 게이트 GREEN 에서 의미 있는 (PATCH/MINOR/MAJOR)×(3 분류)
        # 9칸만 담아야 한다 — NONE/DOWNGRADE/UNKNOWN 행이 새는 것을 차단.
        assert set(POLICY_MATRIX.keys()) == {
            (bump, dep_class)
            for bump in (BUMP_PATCH, BUMP_MINOR, BUMP_MAJOR)
            for dep_class in (CLASS_RUNTIME, CLASS_DEV, CLASS_CI)
        }

    def test_matrix_matches_evaluate_when_green(self):
        for (bump, dep_class), expected in POLICY_MATRIX.items():
            versions = {
                BUMP_PATCH: ("1.0.0", "1.0.1"),
                BUMP_MINOR: ("1.0.0", "1.1.0"),
                BUMP_MAJOR: ("1.0.0", "2.0.0"),
            }[bump]
            decision = evaluate(_update(versions[0], versions[1], dep_class))
            assert decision.decision == expected, (bump, dep_class)


class TestDeterminism:
    def test_same_input_same_output(self):
        update = _update("1.0.0", "1.0.1", CLASS_RUNTIME)
        assert evaluate(update) == evaluate(update)

    def test_decision_is_immutable(self):
        decision = evaluate(_update())
        with pytest.raises(Exception):
            decision.decision = DECISION_BLOCK  # type: ignore[misc]


class TestManifest:
    def test_manifest_is_json_serializable(self):
        text = json.dumps(policy_manifest(), ensure_ascii=False)
        assert "sdacs-dependency-gate" in text

    def test_manifest_matrix_matches_policy_matrix(self):
        manifest = policy_manifest()
        pairs = {
            (row["bump"], row["dep_class"]): row["decision_when_green"]
            for row in manifest["matrix"]
        }
        assert pairs == POLICY_MATRIX

    def test_summary_includes_decision_and_bump(self):
        decision = GateDecision(DECISION_AUTO_MERGE, BUMP_PATCH, ("ok",))
        summary = decision.summary()
        assert DECISION_AUTO_MERGE in summary and BUMP_PATCH in summary


class TestCli:
    def test_known_flags_exit_zero(self):
        from simulation.dependency_gate import main
        assert main(["--policy"]) == 0
        assert main(["--demo"]) == 0
        assert main(["--manifest"]) == 0

    def test_unknown_flag_exits_nonzero(self):
        from simulation.dependency_gate import main
        assert main(["--manifets"]) == 2
