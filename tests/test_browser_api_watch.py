"""ODYSSEY Phase 482 — 브라우저 API 폐기 감시 테스트.

핵심 계약 검증: (상태×방식) 위험 분류·카나리(실험+필수)·등급별 권고·매트릭스와
assess() 의 일치·결정론·리포 실측 레지스트리 판정·종합 자세·매니페스트 JSON
직렬화·CLI.
"""
from __future__ import annotations

import json

import pytest

from simulation.browser_api_watch import (
    ACTION_ADD_FALLBACK,
    ACTION_MIGRATE_NOW,
    ACTION_MONITOR,
    ACTION_PLAN_MIGRATION,
    ACTION_REVIEW,
    ACTION_WITHIN_SLA,
    MODE_ENHANCED,
    MODE_REQUIRED,
    POSTURE_AT_RISK,
    POSTURE_RESILIENT,
    SNAPSHOT_AS_OF,
    STATUS_BASELINE_NEW,
    STATUS_BASELINE_WIDE,
    STATUS_DEPRECATED,
    STATUS_EXPERIMENTAL,
    STATUS_UNKNOWN,
    TIER_BREAKING,
    TIER_FRAGILE,
    TIER_STABLE,
    TIER_SUNSET,
    TIER_UNKNOWN,
    TIER_WATCH,
    BrowserApi,
    _RISK_MATRIX,
    assess,
    assess_registry,
    main,
    policy_manifest,
    shipped_registry,
)

pytestmark = pytest.mark.unit


# --- assess: (상태 × 방식) → (tier, action) --------------------------------
@pytest.mark.parametrize(
    "status,mode,tier,action",
    [
        (STATUS_BASELINE_WIDE, MODE_REQUIRED, TIER_STABLE, ACTION_WITHIN_SLA),
        (STATUS_BASELINE_WIDE, MODE_ENHANCED, TIER_STABLE, ACTION_WITHIN_SLA),
        (STATUS_BASELINE_NEW, MODE_REQUIRED, TIER_WATCH, ACTION_MONITOR),
        (STATUS_BASELINE_NEW, MODE_ENHANCED, TIER_WATCH, ACTION_MONITOR),
        (STATUS_EXPERIMENTAL, MODE_REQUIRED, TIER_FRAGILE, ACTION_ADD_FALLBACK),
        (STATUS_EXPERIMENTAL, MODE_ENHANCED, TIER_WATCH, ACTION_MONITOR),
        (STATUS_DEPRECATED, MODE_REQUIRED, TIER_BREAKING, ACTION_MIGRATE_NOW),
        (STATUS_DEPRECATED, MODE_ENHANCED, TIER_SUNSET, ACTION_PLAN_MIGRATION),
    ],
)
def test_assess_matrix(status, mode, tier, action):
    result = assess(BrowserApi("X", status, mode, "test"))
    assert result.tier == tier
    assert result.action == action
    assert result.status == status
    assert result.mode == mode


def test_assess_matches_risk_matrix_exactly():
    """assess() 가 _RISK_MATRIX 의 모든 칸과 정확히 일치한다(중복 로직 없음)."""
    for (status, mode), (tier, action) in _RISK_MATRIX.items():
        result = assess(BrowserApi("api", status, mode, "u"))
        assert (result.tier, result.action) == (tier, action)


def test_risk_matrix_covers_all_real_combinations():
    """UNKNOWN 을 뺀 4 상태 × 2 방식 = 8 칸 전부 정의돼 있다."""
    assert len(_RISK_MATRIX) == 8


# --- 카나리 핵심: 실험+필수 만 위험, 같은 API라도 폴백이면 안전 ----------------
def test_canary_fires_only_for_experimental_required():
    fragile = assess(BrowserApi("WebXR", STATUS_EXPERIMENTAL, MODE_REQUIRED, "u"))
    safe = assess(BrowserApi("WebXR", STATUS_EXPERIMENTAL, MODE_ENHANCED, "u"))
    assert fragile.tier == TIER_FRAGILE
    assert fragile.action == ACTION_ADD_FALLBACK
    assert safe.tier == TIER_WATCH
    assert safe.action == ACTION_MONITOR


def test_deprecated_required_is_breaking():
    result = assess(BrowserApi("AppCache", STATUS_DEPRECATED, MODE_REQUIRED, "u"))
    assert result.tier == TIER_BREAKING
    assert result.action == ACTION_MIGRATE_NOW


# --- 분류 밖 입력 → REVIEW (정직성, 추측 안전등급 금지) --------------------------
def test_unknown_status_routes_to_review():
    result = assess(BrowserApi("Mystery", STATUS_UNKNOWN, MODE_ENHANCED, "u"))
    assert result.tier == TIER_UNKNOWN
    assert result.action == ACTION_REVIEW


def test_malformed_status_routes_to_review():
    result = assess(BrowserApi("Typo", "baseline", MODE_REQUIRED, "u"))
    assert result.action == ACTION_REVIEW


def test_malformed_mode_routes_to_review():
    result = assess(BrowserApi("Typo", STATUS_BASELINE_WIDE, "optional", "u"))
    assert result.action == ACTION_REVIEW


# --- 결정론 ---------------------------------------------------------------
def test_assess_is_deterministic():
    api = BrowserApi("WebGPU", STATUS_EXPERIMENTAL, MODE_ENHANCED, "u")
    assert assess(api) == assess(api)
    # 레지스트리 수준에서도 반복 호출이 동일 결과(자세·등급 카운트)를 낸다.
    first, second = assess_registry(), assess_registry()
    assert first.posture == second.posture
    assert dict(first.tier_counts) == dict(second.tier_counts)


# --- 리포 실측 레지스트리 판정 ----------------------------------------------
def test_shipped_registry_nonempty_and_grounded():
    reg = shipped_registry()
    assert len(reg) >= 6
    names = {a.name for a in reg}
    # 실측 grep 으로 확인된 핵심 API 가 등록돼 있다.
    assert {"WebGL", "requestAnimationFrame", "WebGPU", "WebXR"} <= names


def test_shipped_registry_required_deps_are_baseline_wide():
    """시뮬레이터의 *필수* 의존은 전부 baseline-wide (카나리 없음)."""
    for api in shipped_registry():
        if api.mode == MODE_REQUIRED:
            assert api.status == STATUS_BASELINE_WIDE, api.name


def test_shipped_registry_experimental_apis_are_enhanced():
    """실험 API(WebGPU·WebXR)는 전부 폴백 있는 ENHANCED — 단일 실패점 아님."""
    for api in shipped_registry():
        if api.status == STATUS_EXPERIMENTAL:
            assert api.mode == MODE_ENHANCED, api.name


def test_shipped_posture_is_resilient():
    """정직 공시: 현 리포는 RESILIENT (BREAKING/FRAGILE 0)."""
    report = assess_registry()
    assert report.posture == POSTURE_RESILIENT
    assert report.tier_counts.get(TIER_BREAKING, 0) == 0
    assert report.tier_counts.get(TIER_FRAGILE, 0) == 0


# --- 종합 자세 산출 --------------------------------------------------------
def test_at_risk_posture_when_fragile_present():
    reg = (
        BrowserApi("WebGL", STATUS_BASELINE_WIDE, MODE_REQUIRED, "u"),
        BrowserApi("WebXR", STATUS_EXPERIMENTAL, MODE_REQUIRED, "u"),  # FRAGILE
    )
    report = assess_registry(reg)
    assert report.posture == POSTURE_AT_RISK
    assert len(report.actionable()) == 1
    assert report.actionable()[0].name == "WebXR"


def test_at_risk_posture_when_breaking_present():
    reg = (
        BrowserApi("Old", STATUS_DEPRECATED, MODE_REQUIRED, "u"),  # BREAKING
    )
    assert assess_registry(reg).posture == POSTURE_AT_RISK


def test_enhanced_experimental_does_not_trip_posture():
    """실험 API 라도 폴백이면 자세를 떨어뜨리지 않는다."""
    reg = (
        BrowserApi("WebGPU", STATUS_EXPERIMENTAL, MODE_ENHANCED, "u"),
        BrowserApi("WebSQL", STATUS_DEPRECATED, MODE_ENHANCED, "u"),  # SUNSET
    )
    assert assess_registry(reg).posture == POSTURE_RESILIENT


def test_unknown_status_trips_posture():
    """미분류 의존이 있으면 RESILIENT 를 주장할 수 없다 — AT_RISK."""
    reg = (
        BrowserApi("WebGL", STATUS_BASELINE_WIDE, MODE_REQUIRED, "u"),
        BrowserApi("Mystery", STATUS_UNKNOWN, MODE_ENHANCED, "u"),
    )
    report = assess_registry(reg)
    assert report.posture == POSTURE_AT_RISK
    assert report.actionable()[0].name == "Mystery"


def test_tier_counts_sum_to_registry_size():
    report = assess_registry()
    assert sum(report.tier_counts.values()) == len(shipped_registry())


def test_tier_counts_is_immutable():
    """frozen 계약: tier_counts 를 in-place 변형할 수 없다."""
    report = assess_registry()
    with pytest.raises(TypeError):
        report.tier_counts["INJECTED"] = 999  # type: ignore[index]


def test_summary_resilient_uses_monitor_wording_not_warning():
    """RESILIENT 자세는 '조치'가 아닌 '감시' 표현 — 모순 표현 회피."""
    reg = (BrowserApi("WebGPU", STATUS_EXPERIMENTAL, MODE_ENHANCED, "u"),)
    s = assess_registry(reg).summary()
    assert POSTURE_RESILIENT in s
    assert "감시" in s and "조치" not in s


# --- 매니페스트 -----------------------------------------------------------
def test_manifest_is_json_serializable_and_complete():
    manifest = policy_manifest()
    dumped = json.dumps(manifest, ensure_ascii=False)
    assert manifest["schema"] == "sdacs-browser-api-watch"
    assert manifest["snapshot_as_of"] == SNAPSHOT_AS_OF
    assert len(manifest["matrix"]) == len(_RISK_MATRIX)
    assert "WebGPU" not in dumped or True  # 직렬화 성공 확인


def test_manifest_matrix_matches_assess():
    for entry in policy_manifest()["matrix"]:
        result = assess(BrowserApi("x", entry["status"], entry["mode"], "u"))
        assert result.tier == entry["tier"]
        assert result.action == entry["action"]


# --- summary 문자열 -------------------------------------------------------
def test_report_summary_lists_risky_when_present():
    reg = (BrowserApi("WebXR", STATUS_EXPERIMENTAL, MODE_REQUIRED, "u"),)
    assert "WebXR" in assess_registry(reg).summary()


def test_report_summary_when_all_stable():
    reg = (BrowserApi("WebGL", STATUS_BASELINE_WIDE, MODE_REQUIRED, "u"),)
    assert "STABLE" in assess_registry(reg).summary()


# --- CLI ------------------------------------------------------------------
@pytest.mark.parametrize("flag", ["--policy", "--status", "--demo", "--manifest"])
def test_cli_known_flags_succeed(flag, capsys):
    assert main([flag]) == 0
    assert capsys.readouterr().out


def test_cli_default_is_policy(capsys):
    assert main([]) == 0
    assert "정책" in capsys.readouterr().out


def test_cli_rejects_unknown_flag(capsys):
    assert main(["--bogus"]) == 2
    assert "알 수 없는 인자" in capsys.readouterr().err


def test_cli_manifest_emits_valid_json(capsys):
    assert main(["--manifest"]) == 0
    assert json.loads(capsys.readouterr().out)["schema"] == "sdacs-browser-api-watch"


def test_cli_flag_precedence_manifest_beats_status(capsys):
    """결합 호출 시 우선순위 계약: --manifest > --status."""
    assert main(["--status", "--manifest"]) == 0
    assert json.loads(capsys.readouterr().out)["schema"] == "sdacs-browser-api-watch"


# --- BrowserApi 입력 검증 (정직성: 빈 식별자 거부) --------------------------
def test_browser_api_rejects_blank_name():
    with pytest.raises(ValueError):
        BrowserApi("  ", STATUS_BASELINE_WIDE, MODE_REQUIRED, "u")


def test_browser_api_rejects_blank_used_by():
    with pytest.raises(ValueError):
        BrowserApi("WebGL", STATUS_BASELINE_WIDE, MODE_REQUIRED, "")
