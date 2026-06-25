"""GENESIS Phase 319 — 테스트 절차서(DO-178C §6) 감사 모듈 테스트.

기존 `simulation/test_procedures.py`(커버리지 0%)에 대한 검증 추가.
실 리포 감사는 모듈 스코프 fixture 로 1회만 수행하고, 로직 검증은 tmp_path
미니 리포로 수행해 전체 리포(node_modules 등) 반복 glob 을 피한다.
"""
from __future__ import annotations

import pathlib

import pytest

from simulation.test_procedures import (
    PHASE_NAMES,
    PROC_CHECKS,
    VERIF_PHASES,
    ProcFinding,
    ProcReport,
    _detect_status,
    _glob_any,
    get_phase_report,
    list_phases,
    run_proc_audit,
)

pytestmark = pytest.mark.unit

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def live_report() -> ProcReport:
    """실 리포 감사 1회(모듈 전체 공유 — 반복 glob 방지)."""
    return run_proc_audit(_REPO_ROOT)


@pytest.fixture
def mini_repo(tmp_path) -> pathlib.Path:
    """일부 증거를 갖춘 작은 가짜 리포(빠른 glob)."""
    (tmp_path / "pyproject.toml").write_text("[tool.pytest]\n", encoding="utf-8")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_x.py").write_text("def test_x(): pass\n", encoding="utf-8")
    return tmp_path


# ── 감사 실행(공유 fixture) ──────────────────────────────────────────────────
class TestRunAudit:
    def test_returns_report(self, live_report):
        assert isinstance(live_report, ProcReport)

    def test_fifteen_findings(self, live_report):
        assert len(live_report.findings) == 15
        assert len(PROC_CHECKS) == 15

    def test_counts_sum_to_total(self, live_report):
        r = live_report
        assert r.met + r.partial + r.not_met == r.total == 15

    def test_compliance_rate_in_range(self, live_report):
        assert 0.0 <= live_report.compliance_rate <= 1.0

    def test_verdict_valid(self, live_report):
        assert live_report.verdict in ("검증 절차 충족", "부분 충족", "미충족")

    def test_finding_codes_unique(self, live_report):
        codes = [f.code for f in live_report.findings]
        assert len(codes) == len(set(codes))

    def test_deterministic(self, mini_repo):
        assert run_proc_audit(mini_repo).as_dict() == run_proc_audit(mini_repo).as_dict()

    def test_invalid_root_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="does not exist"):
            run_proc_audit(tmp_path / "nope")

    def test_live_repo_has_evidence(self, live_report):
        """실 리포는 pyproject·tests·CI 워크플로가 있어 일부는 충족돼야 한다."""
        assert live_report.met >= 1
        assert live_report.compliance_rate > 0.0


# ── 상태 판정 로직(tmp_path 통제) ────────────────────────────────────────────
class TestDetectStatus:
    def test_met_when_all_groups_match(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("x", encoding="utf-8")
        status, evidence = _detect_status(tmp_path, (("**/pyproject.toml",),))
        assert status == "MET"
        assert "pyproject.toml" in evidence

    def test_partial_when_some_groups_match(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("x", encoding="utf-8")
        status, _ = _detect_status(
            tmp_path, (("**/pyproject.toml",), ("**/conftest*",))
        )
        assert status == "PARTIAL"

    def test_not_met_when_no_match(self, tmp_path):
        status, evidence = _detect_status(tmp_path, (("**/nonexistent_xyz",),))
        assert status == "NOT_MET"
        assert evidence == ()

    def test_empty_groups_not_met(self, tmp_path):
        assert _detect_status(tmp_path, ()) == ("NOT_MET", ())


# ── _glob_any 안전성 ─────────────────────────────────────────────────────────
class TestGlobAny:
    def test_excludes_pycache(self, tmp_path):
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        (cache / "x.py").write_text("x", encoding="utf-8")
        assert _glob_any(tmp_path, ("**/*.py",)) == ()

    def test_rejects_parent_escape(self, tmp_path):
        with pytest.raises(ValueError, match="escapes root"):
            _glob_any(tmp_path, ("../**/*.py",))

    def test_sorted_unique(self, tmp_path):
        (tmp_path / "a.txt").write_text("x", encoding="utf-8")
        (tmp_path / "b.txt").write_text("x", encoding="utf-8")
        result = _glob_any(tmp_path, ("**/*.txt", "**/*.txt"))  # 중복 패턴
        assert result == tuple(sorted(result))
        assert len(result) == len(set(result))


# ── 단계별 보고(tmp_path) ────────────────────────────────────────────────────
class TestPhaseReport:
    def test_valid_phase(self, mini_repo):
        r = get_phase_report("TEST_PLANNING", mini_repo)
        assert r["phase"] == "TEST_PLANNING"
        assert r["phase_name"] == PHASE_NAMES["TEST_PLANNING"]
        assert r["total"] == 3  # TP-001~003

    def test_case_insensitive(self, mini_repo):
        assert get_phase_report("test_planning", mini_repo)["phase"] == "TEST_PLANNING"

    def test_invalid_phase_raises(self):
        with pytest.raises(ValueError, match="유효하지 않은"):
            get_phase_report("BOGUS_PHASE")

    def test_phase_check_counts_sum_to_total(self):
        """단계별 점검 항목 수 합 = 15 (정적 — 감사 불필요)."""
        per_phase = {p: sum(1 for c in PROC_CHECKS if c[1] == p) for p in VERIF_PHASES}
        assert sum(per_phase.values()) == 15
        assert per_phase["TEST_PLANNING"] == 3


# ── 단계 목록 ────────────────────────────────────────────────────────────────
class TestListPhases:
    def test_five_phases(self):
        phases = list_phases()
        assert len(phases) == 5
        assert tuple(p["code"] for p in phases) == VERIF_PHASES


# ── 직렬화 ───────────────────────────────────────────────────────────────────
class TestSerialization:
    def test_report_as_dict_keys(self, live_report):
        d = live_report.as_dict()
        assert set(d) >= {"findings", "total", "met", "partial", "not_met",
                          "compliance_rate", "verdict"}

    def test_finding_as_dict(self, live_report):
        f = live_report.findings[0]
        assert isinstance(f, ProcFinding)
        assert set(f.as_dict()) == {"code", "phase", "check_name", "status", "evidence"}
