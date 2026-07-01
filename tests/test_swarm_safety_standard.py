"""ODYSSEY Phase 464 — 5계층 안전망 사례 연구 백서 골격 단위 테스트."""
from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

import pytest

from simulation.swarm_safety_standard import (
    CROSS_CUTTING_EVIDENCE,
    KINDS,
    SAFETY_LAYERS,
    STATUSES,
    SafetyEvidence,
    SafetyLayer,
    WhitepaperReport,
    case_study_matrix,
    find_layer,
    layer_status,
    markdown_table,
    missing_evidence,
    whitepaper_report,
)


# ── SafetyEvidence 검증 ──────────────────────────────────────────────────────
def test_evidence_valid_construction():
    ev = SafetyEvidence("simulation/apf_lyapunov.py", "module", "APF 수렴")
    assert ev.path == "simulation/apf_lyapunov.py"
    assert ev.is_executable is True


def test_evidence_doc_is_not_executable():
    ev = SafetyEvidence("docs/x.md", "doc", "문서")
    assert ev.is_executable is False


@pytest.mark.parametrize("kind", KINDS)
def test_evidence_all_kinds_accepted(kind):
    assert SafetyEvidence("a/b.x", kind, "role").kind == kind


def test_evidence_rejects_unknown_kind():
    with pytest.raises(ValueError, match="kind must be one of"):
        SafetyEvidence("a/b.py", "binary", "role")


def test_evidence_rejects_empty_path():
    with pytest.raises(ValueError, match="path must be non-empty"):
        SafetyEvidence("", "module", "role")


def test_evidence_rejects_padded_path():
    with pytest.raises(ValueError, match="path must be non-empty"):
        SafetyEvidence(" a/b.py ", "module", "role")


def test_evidence_rejects_absolute_path():
    with pytest.raises(ValueError, match="must be repo-relative"):
        SafetyEvidence("/etc/passwd", "doc", "role")


def test_evidence_rejects_empty_role():
    with pytest.raises(ValueError, match="role must be"):
        SafetyEvidence("a/b.py", "module", "  ")


def test_evidence_rejects_traversal_path():
    with pytest.raises(ValueError, match="must not escape"):
        SafetyEvidence("../secrets/key.pem", "doc", "role")


def test_evidence_exists_with_root(tmp_path: Path):
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "y.py").write_text("# y")
    assert SafetyEvidence("x/y.py", "module", "r").exists(tmp_path) is True
    assert SafetyEvidence("x/z.py", "module", "r").exists(tmp_path) is False


# ── SafetyLayer 검증 ─────────────────────────────────────────────────────────
def _ev(path="a/b.py", kind="module"):
    return SafetyEvidence(path, kind, "role")


def test_layer_valid_construction():
    layer = SafetyLayer("L9", "Name", "AB", 1.0, "scope", "role", (_ev(),))
    assert layer.layer_id == "L9"
    assert layer.rate_hz == 1.0


def test_layer_rejects_empty_evidence():
    with pytest.raises(ValueError, match="at least one evidence"):
        SafetyLayer("L9", "Name", "AB", 1.0, "scope", "role", ())


def test_layer_rejects_nonpositive_rate():
    with pytest.raises(ValueError, match="rate_hz must be positive"):
        SafetyLayer("L9", "Name", "AB", 0.0, "scope", "role", (_ev(),))


def test_layer_rejects_layer_id_with_space():
    with pytest.raises(ValueError, match="must not contain internal spaces"):
        SafetyLayer("L 9", "Name", "AB", 1.0, "scope", "role", (_ev(),))


@pytest.mark.parametrize("field", ["name", "abbrev", "decision_scope", "role"])
def test_layer_rejects_empty_string_fields(field):
    kwargs = dict(
        layer_id="L9", name="Name", abbrev="AB", rate_hz=1.0,
        decision_scope="scope", role="role", evidence=(_ev(),),
    )
    kwargs[field] = "  "
    with pytest.raises(ValueError, match=f"{field} must be"):
        SafetyLayer(**kwargs)


# ── 상태 판정 (디스크 실재 기반, tmp_path 격리) ───────────────────────────────
def test_status_substantiated_when_all_present_with_executable(tmp_path: Path):
    (tmp_path / "d").mkdir()
    (tmp_path / "d" / "m.py").write_text("x")
    (tmp_path / "d" / "doc.md").write_text("x")
    layer = SafetyLayer(
        "L9", "N", "AB", 1.0, "scope", "role",
        (_ev("d/m.py", "module"), _ev("d/doc.md", "doc")),
    )
    assert layer.status(tmp_path) == "SUBSTANTIATED"


def test_status_partial_when_some_missing(tmp_path: Path):
    (tmp_path / "d").mkdir()
    (tmp_path / "d" / "m.py").write_text("x")
    layer = SafetyLayer(
        "L9", "N", "AB", 1.0, "scope", "role",
        (_ev("d/m.py", "module"), _ev("d/missing.md", "doc")),
    )
    assert layer.status(tmp_path) == "PARTIAL"


def test_status_partial_when_all_present_but_doc_only(tmp_path: Path):
    (tmp_path / "d").mkdir()
    (tmp_path / "d" / "a.md").write_text("x")
    (tmp_path / "d" / "b.md").write_text("x")
    layer = SafetyLayer(
        "L9", "N", "AB", 1.0, "scope", "role",
        (_ev("d/a.md", "doc"), _ev("d/b.md", "doc")),
    )
    # 모두 실재하나 실행/형식 근거가 없음 → PARTIAL (거짓 완전입증 차단).
    assert layer.status(tmp_path) == "PARTIAL"


def test_status_unsubstantiated_when_none_present(tmp_path: Path):
    layer = SafetyLayer(
        "L9", "N", "AB", 1.0, "scope", "role",
        (_ev("nope/x.py", "module"),),
    )
    assert layer.status(tmp_path) == "UNSUBSTANTIATED"


def test_existing_and_missing_partition(tmp_path: Path):
    (tmp_path / "d").mkdir()
    (tmp_path / "d" / "m.py").write_text("x")
    layer = SafetyLayer(
        "L9", "N", "AB", 1.0, "scope", "role",
        (_ev("d/m.py", "module"), _ev("d/gone.md", "doc")),
    )
    assert len(layer.existing_evidence(tmp_path)) == 1
    assert len(layer.missing_evidence(tmp_path)) == 1
    assert (len(layer.existing_evidence(tmp_path))
            + len(layer.missing_evidence(tmp_path))) == len(layer.evidence)


# ── 정본 레지스트리 무결성 (디스크 실재 강제) ─────────────────────────────────
def test_registry_has_five_layers():
    assert len(SAFETY_LAYERS) == 5
    assert [layer.layer_id for layer in SAFETY_LAYERS] == ["L1", "L2", "L3", "L4", "L5"]


def test_registry_layer_ids_unique():
    ids = [layer.layer_id for layer in SAFETY_LAYERS]
    assert len(ids) == len(set(ids))


def test_all_layer_evidence_exists_on_disk():
    """정직성 결속: 인용한 모든 계층 근거가 리포에 실재해야 한다."""
    for layer in SAFETY_LAYERS:
        for ev in layer.evidence:
            assert ev.exists(), f"{layer.layer_id} cites missing evidence {ev.path}"


def test_all_cross_cutting_evidence_exists_on_disk():
    for ev in CROSS_CUTTING_EVIDENCE:
        assert ev.exists(), f"cross-cutting cites missing evidence {ev.path}"


def test_every_layer_substantiated_on_real_repo():
    for layer in SAFETY_LAYERS:
        assert layer.status() == "SUBSTANTIATED"


def test_every_layer_has_executable_evidence():
    for layer in SAFETY_LAYERS:
        assert any(ev.is_executable for ev in layer.evidence)


# ── 조회 API ─────────────────────────────────────────────────────────────────
def test_find_layer_returns_match():
    assert find_layer("L1").abbrev == "APF"


def test_find_layer_unknown_raises():
    with pytest.raises(KeyError, match="unknown safety layer"):
        find_layer("L99")


def test_layer_status_helper():
    assert layer_status("L1") == "SUBSTANTIATED"


def test_layer_status_helper_propagates_root(tmp_path: Path):
    assert layer_status("L1", tmp_path) == "UNSUBSTANTIATED"


def test_missing_evidence_empty_on_real_repo():
    assert missing_evidence() == ()


# ── 백서 리포트 ──────────────────────────────────────────────────────────────
def test_report_fully_substantiated_on_real_repo():
    rep = whitepaper_report()
    assert rep.total_layers == 5
    assert rep.substantiated == 5
    assert rep.partial == 0
    assert rep.unsubstantiated == 0
    assert rep.coverage_pct == 100.0
    assert rep.evidence_pct == 100.0
    assert rep.is_fully_substantiated is True


def test_report_by_layer_is_readonly_mapping():
    rep = whitepaper_report()
    assert isinstance(rep.by_layer, MappingProxyType)
    with pytest.raises(TypeError):
        rep.by_layer["L1"] = "x"  # type: ignore[index]


def test_report_counts_consistent():
    rep = whitepaper_report()
    assert rep.substantiated + rep.partial + rep.unsubstantiated == rep.total_layers
    assert rep.existing_evidence <= rep.total_evidence


def test_report_rejects_inconsistent_counts():
    with pytest.raises(ValueError, match="!= total_layers"):
        WhitepaperReport(
            total_layers=5, substantiated=1, partial=1, unsubstantiated=1,
            total_evidence=10, existing_evidence=10,
            cross_cutting_total=5, cross_cutting_existing=5,
            by_layer=MappingProxyType({}),
        )


def test_report_rejects_invalid_by_layer_status():
    with pytest.raises(ValueError, match="invalid status"):
        WhitepaperReport(
            total_layers=1, substantiated=1, partial=0, unsubstantiated=0,
            total_evidence=1, existing_evidence=1,
            cross_cutting_total=0, cross_cutting_existing=0,
            by_layer=MappingProxyType({"L1": "BOGUS"}),
        )


def test_report_rejects_existing_exceeding_total():
    with pytest.raises(ValueError, match="existing_evidence must not exceed"):
        WhitepaperReport(
            total_layers=1, substantiated=1, partial=0, unsubstantiated=0,
            total_evidence=2, existing_evidence=3,
            cross_cutting_total=0, cross_cutting_existing=0,
            by_layer=MappingProxyType({"L1": "SUBSTANTIATED"}),
        )


def test_report_partial_when_evidence_removed(tmp_path: Path):
    """근거가 하나도 없는 격리 루트에서는 전 계층 UNSUBSTANTIATED."""
    rep = whitepaper_report(tmp_path)
    assert rep.unsubstantiated == 5
    assert rep.coverage_pct == 0.0
    assert rep.is_fully_substantiated is False


# ── 매트릭스·markdown ────────────────────────────────────────────────────────
def test_case_study_matrix_shape():
    rows = case_study_matrix()
    assert len(rows) == 5
    assert rows[0]["layer_id"] == "L1"
    assert rows[0]["status"] == "SUBSTANTIATED"
    assert set(rows[0]) == {
        "layer_id", "abbrev", "name", "rate_hz", "decision_scope",
        "status", "evidence_present", "evidence_total",
    }


def test_markdown_table_has_header_and_rows():
    md = markdown_table()
    assert "| 계층 |" in md
    assert md.count("\n") >= 6  # 헤더 2줄 + 5계층
    assert "L1" in md and "L5" in md


def test_statuses_constant_complete():
    assert set(STATUSES) == {"SUBSTANTIATED", "PARTIAL", "UNSUBSTANTIATED"}


# ── CLI ──────────────────────────────────────────────────────────────────────
def test_main_report_default(capsys):
    from simulation.swarm_safety_standard import _main
    assert _main([]) == 0
    assert "5계층 안전망" in capsys.readouterr().out


def test_main_layers(capsys):
    from simulation.swarm_safety_standard import _main
    assert _main(["--layers"]) == 0
    out = capsys.readouterr().out
    assert "L1" in out and "APF" in out


def test_main_markdown(capsys):
    from simulation.swarm_safety_standard import _main
    assert _main(["--markdown"]) == 0
    assert "| 계층 |" in capsys.readouterr().out


def test_main_gaps_no_missing(capsys):
    from simulation.swarm_safety_standard import _main
    assert _main(["--gaps"]) == 0
    assert "누락 근거 없음" in capsys.readouterr().out
