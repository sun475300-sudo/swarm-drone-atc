"""ODYSSEY Phase 484 — Electron LTS 추적 정책 테스트.

핵심 계약 검증: major 파싱·지원 등급 분류·등급별 권고·정책 매트릭스와
assess() 의 일치·결정론·리포 핀 실측 판정·매니페스트 JSON 직렬화·CLI.
"""
from __future__ import annotations

import json

import pytest

from simulation.electron_lts_policy import (
    ACTION_PLAN_UPGRADE,
    ACTION_REVIEW,
    ACTION_UPGRADE_NOW,
    ACTION_WITHIN_SLA,
    OBSERVED_LATEST_STABLE_MAJOR,
    POLICY_MATRIX,
    SUPPORT_WINDOW_MAJORS,
    TIER_AHEAD,
    TIER_CURRENT,
    TIER_ENDING,
    TIER_EOL,
    TIER_SUPPORTED,
    ElectronRuntime,
    LtsAssessment,
    assess,
    main,
    parse_major,
    policy_manifest,
    read_pinned_major,
    shipped_runtime,
    support_tier,
)

pytestmark = pytest.mark.unit


# --- parse_major -----------------------------------------------------------
@pytest.mark.parametrize(
    "version,expected",
    [
        ("39.8.5", 39),
        ("^39.8.5", 39),
        ("~42", 42),
        (">=40.0.0", 40),
        ("v41", 41),
        ("  ^32.3.3  ", 32),
        ("42", 42),
    ],
)
def test_parse_major_accepts_valid_specs(version, expected):
    assert parse_major(version) == expected


@pytest.mark.parametrize("version", ["latest", "*", "", "x.y.z", "next", "<40", "<=39.0.0"])
def test_parse_major_rejects_unparseable(version):
    # `<` 상한 스펙은 핀 major 과대 추정 방지를 위해 거부 → REVIEW.
    assert parse_major(version) is None


# --- support_tier ----------------------------------------------------------
def test_support_window_is_three():
    # 정책 기준선: Electron 은 최신 3개 stable major 만 지원.
    assert SUPPORT_WINDOW_MAJORS == 3


@pytest.mark.parametrize(
    "pinned,latest,tier",
    [
        (42, 42, TIER_CURRENT),    # lag 0
        (41, 42, TIER_SUPPORTED),  # lag 1
        (40, 42, TIER_ENDING),     # lag 2 (창의 마지막 칸)
        (39, 42, TIER_EOL),        # lag 3 (창 밖)
        (35, 42, TIER_EOL),        # lag 7
        (43, 42, TIER_AHEAD),      # lag -1
    ],
)
def test_support_tier_classification(pinned, latest, tier):
    assert support_tier(pinned, latest) == tier


def test_ending_is_exactly_last_in_window():
    # window-1 만 ENDING, window 부터 EOL — 경계가 정확.
    latest = 50
    assert support_tier(latest - (SUPPORT_WINDOW_MAJORS - 1), latest) == TIER_ENDING
    assert support_tier(latest - SUPPORT_WINDOW_MAJORS, latest) == TIER_EOL


# --- assess ----------------------------------------------------------------
def test_assess_current_within_sla():
    result = assess(ElectronRuntime(42, 42))
    assert result.action == ACTION_WITHIN_SLA
    assert result.tier == TIER_CURRENT
    assert result.lag == 0


def test_assess_supported_within_sla():
    result = assess(ElectronRuntime(41, 42))
    assert result.action == ACTION_WITHIN_SLA
    assert result.tier == TIER_SUPPORTED


def test_assess_ending_plans_upgrade():
    result = assess(ElectronRuntime(40, 42))
    assert result.action == ACTION_PLAN_UPGRADE
    assert result.tier == TIER_ENDING


def test_assess_eol_upgrade_now():
    result = assess(ElectronRuntime(39, 42))
    assert result.action == ACTION_UPGRADE_NOW
    assert result.tier == TIER_EOL
    assert result.lag == 3


def test_assess_32_to_39_drift_teaching_example_is_eol():
    # 현 32→39 표류 교훈: lag 7 은 창(3) 의 두 배 이상 → EOL.
    result = assess(ElectronRuntime(32, 39))
    assert result.tier == TIER_EOL
    assert result.action == ACTION_UPGRADE_NOW
    assert result.lag == 7


@pytest.mark.parametrize("lag", [3, 4, 7, 10, 100])
def test_assess_large_lags_all_eol(lag):
    latest = 200
    result = assess(ElectronRuntime(latest - lag, latest))
    assert result.tier == TIER_EOL
    assert result.action == ACTION_UPGRADE_NOW


def test_assess_ahead_review():
    result = assess(ElectronRuntime(43, 42))
    assert result.action == ACTION_REVIEW
    assert result.tier == TIER_AHEAD
    assert result.lag == -1


def test_assess_is_deterministic():
    runtime = ElectronRuntime(39, 42)
    assert assess(runtime) == assess(runtime)


def test_assessment_summary_is_human_readable():
    summary = assess(ElectronRuntime(39, 42)).summary()
    assert ACTION_UPGRADE_NOW in summary
    assert "lag=3" in summary


def test_reasons_nonempty_for_every_tier():
    for pinned in (42, 41, 40, 39, 43):
        result = assess(ElectronRuntime(pinned, 42))
        assert result.reasons
        assert all(r.strip() for r in result.reasons)


# --- POLICY_MATRIX 일치 강제 -----------------------------------------------
def test_policy_matrix_matches_assess():
    """매트릭스의 모든 (lag → tier·action) 칸이 assess() 결과와 정확 일치."""
    latest = 50
    for lag, (tier, action) in POLICY_MATRIX.items():
        runtime = ElectronRuntime(latest - lag, latest)
        result = assess(runtime)
        assert result.tier == tier, f"lag={lag}"
        assert result.action == action, f"lag={lag}"


def test_policy_matrix_covers_window_boundary():
    # 매트릭스는 창 안(0·1)·경계(2)·밖(3·4)·앞섬(-1) 을 모두 대표한다.
    assert set(POLICY_MATRIX) == {-1, 0, 1, 2, 3, 4}


# --- shipped_runtime / read_pinned_major -----------------------------------
def test_read_pinned_major_from_repo():
    # 리포 package.json 의 electron 핀이 실제로 읽힌다(현 ^39.8.5).
    major = read_pinned_major(_repo_root())
    assert major == 39


def test_shipped_runtime_reflects_repo_pin():
    runtime = shipped_runtime()
    assert runtime is not None
    assert runtime.pinned_major == 39
    assert runtime.latest_stable_major == OBSERVED_LATEST_STABLE_MAJOR


def test_shipped_runtime_honest_eol_disclosure():
    # 정직 공시: 현 핀 39 는 최신 42 대비 EOL → UPGRADE_NOW.
    runtime = shipped_runtime()
    assert runtime is not None, "package.json electron 핀을 읽지 못함"
    result = assess(runtime)
    assert result.tier == TIER_EOL
    assert result.action == ACTION_UPGRADE_NOW


def test_read_pinned_major_missing_file(tmp_path):
    assert read_pinned_major(tmp_path) is None


def test_read_pinned_major_handles_malformed_json(tmp_path):
    (tmp_path / "package.json").write_text("{not json", encoding="utf-8")
    assert read_pinned_major(tmp_path) is None


def test_read_pinned_major_missing_electron_field(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"devDependencies": {"vite": "^5.0.0"}}), encoding="utf-8"
    )
    assert read_pinned_major(tmp_path) is None


def test_read_pinned_major_falls_back_to_runtime_dep(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"electron": "^30.0.0"}}), encoding="utf-8"
    )
    assert read_pinned_major(tmp_path) == 30


def test_read_pinned_major_prefers_devdependencies(tmp_path):
    # 둘 다 있으면 devDependencies 가 이긴다(우선순위 계약).
    (tmp_path / "package.json").write_text(
        json.dumps({
            "devDependencies": {"electron": "^39.0.0"},
            "dependencies": {"electron": "^30.0.0"},
        }),
        encoding="utf-8",
    )
    assert read_pinned_major(tmp_path) == 39


def test_shipped_runtime_none_when_pin_unreadable(tmp_path):
    assert shipped_runtime(tmp_path) is None


# --- 매니페스트 ------------------------------------------------------------
def test_manifest_is_json_serializable_and_complete():
    manifest = policy_manifest()
    dumped = json.loads(json.dumps(manifest, ensure_ascii=False))
    assert dumped["schema"] == "sdacs-electron-lts-policy"
    assert dumped["support_window_majors"] == SUPPORT_WINDOW_MAJORS
    assert dumped["observed_latest_stable_major"] == OBSERVED_LATEST_STABLE_MAJOR
    assert len(dumped["matrix"]) == len(POLICY_MATRIX)


def test_manifest_actions_cover_all_decisions():
    actions = set(policy_manifest()["actions"])
    assert actions == {
        ACTION_WITHIN_SLA, ACTION_PLAN_UPGRADE, ACTION_UPGRADE_NOW, ACTION_REVIEW,
    }


# --- CLI -------------------------------------------------------------------
def test_cli_policy(capsys):
    assert main(["--policy"]) == 0
    assert "Electron LTS" in capsys.readouterr().out


def test_cli_status_reports_repo_pin(capsys):
    assert main(["--status"]) == 0
    out = capsys.readouterr().out
    assert "Electron 39" in out
    assert ACTION_UPGRADE_NOW in out


def test_cli_demo(capsys):
    assert main(["--demo"]) == 0
    out = capsys.readouterr().out
    assert "electron" in out


def test_cli_manifest_emits_json(capsys):
    assert main(["--manifest"]) == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed["schema"] == "sdacs-electron-lts-policy"


def test_cli_default_is_policy(capsys):
    assert main([]) == 0
    assert "정책" in capsys.readouterr().out


def test_cli_rejects_unknown_flag(capsys):
    assert main(["--bogus"]) == 2
    assert "알 수 없는 인자" in capsys.readouterr().err


# --- 헬퍼 ------------------------------------------------------------------
def _repo_root():
    from pathlib import Path

    return Path(__file__).resolve().parent.parent


def test_lts_assessment_is_frozen():
    result = LtsAssessment(ACTION_WITHIN_SLA, TIER_CURRENT, 0, ("ok",))
    with pytest.raises((AttributeError, TypeError)):
        result.action = ACTION_UPGRADE_NOW  # type: ignore[misc]
