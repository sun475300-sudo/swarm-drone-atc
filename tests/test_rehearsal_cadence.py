"""ODYSSEY Phase 486 — 연 1회 건전성 리허설 케이던스 정책 테스트.

핵심 계약 검증: 케이던스 등급 경계(예고/만기/유예)·권고 우선순위(하니스 손상→
REVIEW, 미래 날짜→REVIEW, 실패 기준선→RUN_NOW)·POLICY_MATRIX ↔ assess 일치·
결정론·매니페스트 JSON 직렬화·리포 현 상태 정직성·CLI.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from simulation.rehearsal_cadence import (
    ACTION_REVIEW,
    ACTION_RUN_NOW,
    ACTION_SCHEDULE,
    ACTION_WITHIN_CADENCE,
    ANNUAL_INTERVAL_DAYS,
    DUE_SOON_LEAD_DAYS,
    OVERDUE_GRACE_DAYS,
    POLICY_MATRIX,
    REHEARSAL_HARNESS,
    RESULT_FAIL,
    RESULT_PASS,
    TIER_CURRENT,
    TIER_DUE,
    TIER_DUE_SOON,
    TIER_NEVER_RUN,
    TIER_OVERDUE,
    CadenceAssessment,
    RehearsalRecord,
    assess,
    cadence_tier,
    days_since,
    harness_intact,
    main,
    policy_manifest,
    shipped_record,
)

pytestmark = pytest.mark.unit

_TODAY = date(2026, 6, 19)


def _record_days_ago(n: int, result: str = RESULT_PASS) -> RehearsalRecord:
    """기준일(_TODAY)로부터 n일 전 PASS(기본) 기록."""
    return RehearsalRecord(_TODAY - timedelta(days=n), result)


# --- 케이던스 등급 경계 ----------------------------------------------------
class TestCadenceTier:
    def test_well_within_is_current(self):
        assert cadence_tier(0) == TIER_CURRENT
        assert cadence_tier(ANNUAL_INTERVAL_DAYS - DUE_SOON_LEAD_DAYS - 1) == TIER_CURRENT

    def test_lead_window_is_due_soon(self):
        assert cadence_tier(ANNUAL_INTERVAL_DAYS - DUE_SOON_LEAD_DAYS) == TIER_DUE_SOON
        assert cadence_tier(ANNUAL_INTERVAL_DAYS - 1) == TIER_DUE_SOON

    def test_at_interval_is_due(self):
        assert cadence_tier(ANNUAL_INTERVAL_DAYS) == TIER_DUE
        assert cadence_tier(ANNUAL_INTERVAL_DAYS + OVERDUE_GRACE_DAYS - 1) == TIER_DUE

    def test_past_grace_is_overdue(self):
        assert cadence_tier(ANNUAL_INTERVAL_DAYS + OVERDUE_GRACE_DAYS) == TIER_OVERDUE
        assert cadence_tier(10_000) == TIER_OVERDUE

    def test_negative_days_rejected(self):
        # 음수 입력은 조용히 CURRENT 로 새지 않고 명시적으로 거부된다.
        with pytest.raises(ValueError):
            cadence_tier(-1)


# --- days_since ------------------------------------------------------------
class TestDaysSince:
    def test_none_when_never_run(self):
        assert days_since(RehearsalRecord(None), _TODAY) is None

    def test_counts_elapsed_days(self):
        assert days_since(_record_days_ago(42), _TODAY) == 42

    def test_negative_when_future(self):
        future = RehearsalRecord(_TODAY + timedelta(days=5))
        assert days_since(future, _TODAY) == -5


# --- assess 우선순위 -------------------------------------------------------
class TestAssessPriority:
    def test_harness_broken_is_review_before_cadence(self):
        # 케이던스상 CURRENT 라도 하니스가 손상이면 REVIEW 가 우선한다.
        result = assess(_record_days_ago(0), _TODAY, harness_intact=False)
        assert result.action == ACTION_REVIEW
        assert result.harness_intact is False

    def test_harness_broken_and_never_run_is_review(self):
        # 최고 위험 상태(하니스 없음 + 기준선 없음) — REVIEW + NEVER_RUN 직접 검증.
        result = assess(RehearsalRecord(None), _TODAY, harness_intact=False)
        assert result.action == ACTION_REVIEW
        assert result.tier == TIER_NEVER_RUN
        assert result.days_since is None

    def test_harness_broken_and_future_date_is_review(self):
        future = RehearsalRecord(_TODAY + timedelta(days=10))
        result = assess(future, _TODAY, harness_intact=False)
        assert result.action == ACTION_REVIEW
        assert result.days_since == -10

    def test_harness_broken_beats_failing_baseline(self):
        # 결과 FAIL 이라도 하니스 손상이면 RUN_NOW 가 아니라 REVIEW 가 우선한다.
        result = assess(_record_days_ago(400, RESULT_FAIL), _TODAY, harness_intact=False)
        assert result.action == ACTION_REVIEW

    def test_never_run_is_run_now(self):
        result = assess(RehearsalRecord(None), _TODAY, harness_intact=True)
        assert result.action == ACTION_RUN_NOW
        assert result.tier == TIER_NEVER_RUN
        assert result.days_since is None

    def test_future_date_is_review(self):
        future = RehearsalRecord(_TODAY + timedelta(days=3))
        result = assess(future, _TODAY, harness_intact=True)
        assert result.action == ACTION_REVIEW
        assert result.days_since == -3

    def test_failing_baseline_is_run_now_regardless_of_recency(self):
        # 막 돌렸어도 결과가 FAIL 이면 녹색 기준선이 없으므로 RUN_NOW.
        result = assess(_record_days_ago(0, RESULT_FAIL), _TODAY, harness_intact=True)
        assert result.action == ACTION_RUN_NOW
        assert result.tier == TIER_CURRENT

    def test_recent_pass_is_within_cadence(self):
        result = assess(_record_days_ago(10), _TODAY, harness_intact=True)
        assert result.action == ACTION_WITHIN_CADENCE
        assert result.tier == TIER_CURRENT

    def test_due_soon_pass_is_schedule(self):
        result = assess(_record_days_ago(ANNUAL_INTERVAL_DAYS - 10), _TODAY, True)
        assert result.action == ACTION_SCHEDULE
        assert result.tier == TIER_DUE_SOON

    def test_overdue_pass_is_run_now(self):
        result = assess(_record_days_ago(ANNUAL_INTERVAL_DAYS + 100), _TODAY, True)
        assert result.action == ACTION_RUN_NOW
        assert result.tier == TIER_OVERDUE


# --- POLICY_MATRIX ↔ assess 일치 ------------------------------------------
class TestPolicyMatrixConsistency:
    @pytest.mark.parametrize("days,expected", sorted(POLICY_MATRIX.items()))
    def test_matrix_matches_assess(self, days, expected):
        # PASS + 하니스 온전 가정에서 assess 는 매트릭스와 정확히 일치해야 한다.
        result = assess(_record_days_ago(days), _TODAY, harness_intact=True)
        assert (result.tier, result.action) == expected

    def test_matrix_covers_all_tiers(self):
        tiers = {tier for tier, _ in POLICY_MATRIX.values()}
        assert tiers == {TIER_CURRENT, TIER_DUE_SOON, TIER_DUE, TIER_OVERDUE}


# --- 결정론 ----------------------------------------------------------------
class TestDeterminism:
    def test_same_inputs_same_output(self):
        rec = _record_days_ago(200)
        a = assess(rec, _TODAY, True)
        b = assess(rec, _TODAY, True)
        assert a == b

    def test_assessment_is_frozen(self):
        result = assess(_record_days_ago(5), _TODAY, True)
        with pytest.raises(Exception):
            result.action = "X"  # type: ignore[misc]


# --- 매니페스트 ------------------------------------------------------------
class TestManifest:
    def test_manifest_is_json_serializable(self):
        manifest = policy_manifest()
        round_trip = json.loads(json.dumps(manifest, ensure_ascii=False))
        assert round_trip == manifest

    def test_manifest_matrix_matches_policy(self):
        manifest = policy_manifest()
        entries = {e["days_since"]: (e["tier"], e["action"]) for e in manifest["matrix"]}
        assert entries == POLICY_MATRIX

    def test_manifest_lists_harness(self):
        assert tuple(policy_manifest()["harness"]) == REHEARSAL_HARNESS


# --- 리포 현 상태 정직성 ---------------------------------------------------
class TestRepoHonesty:
    def test_shipped_record_is_passing_snapshot(self):
        record = shipped_record()
        assert record.last_run is not None
        assert record.result == RESULT_PASS

    def test_repo_harness_is_intact(self):
        # 본 리포는 리허설 하니스 자산을 모두 보유한다(Phase 490 증거와 일치).
        repo_root = Path(__file__).resolve().parent.parent
        assert harness_intact(repo_root) is True

    def test_repo_status_is_actionable_verdict(self):
        repo_root = Path(__file__).resolve().parent.parent
        result = assess(shipped_record(), date(2026, 6, 19), harness_intact(repo_root))
        # 같은 날 리허설(LAST_REHEARSAL_DATE == 2026-06-19) → 경과 0 → CURRENT →
        # WITHIN_CADENCE. 스냅샷 상수 갱신 시 본 단언도 함께 갱신해야 한다.
        assert isinstance(result, CadenceAssessment)
        assert result.action == ACTION_WITHIN_CADENCE


# --- CLI -------------------------------------------------------------------
class TestCli:
    def test_policy_flag(self, capsys):
        assert main(["--policy"]) == 0
        assert "케이던스" in capsys.readouterr().out

    def test_status_flag(self, capsys):
        assert main(["--status"]) == 0
        assert "리허설" in capsys.readouterr().out

    def test_demo_flag(self, capsys):
        assert main(["--demo"]) == 0
        assert "예시" in capsys.readouterr().out

    def test_manifest_flag_emits_json(self, capsys):
        assert main(["--manifest"]) == 0
        parsed = json.loads(capsys.readouterr().out)
        assert parsed["schema"] == "sdacs-health-rehearsal-cadence-policy"

    def test_default_is_policy(self, capsys):
        assert main([]) == 0
        assert "TIER" in capsys.readouterr().out

    def test_unknown_flag_errors(self, capsys):
        assert main(["--nope"]) == 2
        assert "알 수 없는 인자" in capsys.readouterr().err
