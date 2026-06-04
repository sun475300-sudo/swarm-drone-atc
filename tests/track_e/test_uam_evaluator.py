"""P742 K-UAM 자동 평가기 검증."""
from __future__ import annotations

import csv
import tempfile
from pathlib import Path

from scripts.uam_evaluator import (
    KUAMCriteria,
    evaluate,
    format_report,
    load_kpi_csv,
)


def _write_csv(rows: list[dict]) -> str:
    tmp = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="")
    writer = csv.DictWriter(tmp, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    tmp.close()
    return tmp.name


def test_passing_scenario() -> None:
    """모든 기준 충족 → 전부 PASS."""
    path = _write_csv([
        {"seed": "1", "NMR": "0.03", "MSD": "67", "AU": "0.71", "RTF": "142", "Completion": "1.0"},
        {"seed": "2", "NMR": "0.04", "MSD": "65", "AU": "0.70", "RTF": "140", "Completion": "1.0"},
    ])
    kpi = load_kpi_csv(path)
    results = evaluate(kpi)
    assert all(r.passed for r in results)
    Path(path).unlink()


def test_failing_nmr() -> None:
    """NMR 초과 → NMR FAIL."""
    path = _write_csv([
        {"seed": "1", "NMR": "0.12", "MSD": "67", "AU": "0.71", "RTF": "142", "Completion": "1.0"},
    ])
    kpi = load_kpi_csv(path)
    results = evaluate(kpi)
    nmr = next(r for r in results if r.metric == "NMR")
    assert not nmr.passed
    Path(path).unlink()


def test_failing_rtf_below_realtime() -> None:
    """RTF < 1.0 → FAIL (실시간 미달)."""
    path = _write_csv([
        {"seed": "1", "NMR": "0.03", "MSD": "67", "AU": "0.71", "RTF": "0.8", "Completion": "1.0"},
    ])
    kpi = load_kpi_csv(path)
    results = evaluate(kpi)
    rtf = next(r for r in results if r.metric == "RTF")
    assert not rtf.passed
    Path(path).unlink()


def test_mean_across_seeds() -> None:
    """다중 seed 평균 계산."""
    path = _write_csv([
        {"seed": "1", "NMR": "0.04", "MSD": "60", "AU": "0.70", "RTF": "100", "Completion": "1.0"},
        {"seed": "2", "NMR": "0.06", "MSD": "50", "AU": "0.60", "RTF": "120", "Completion": "0.9"},
    ])
    kpi = load_kpi_csv(path)
    results = evaluate(kpi)
    nmr = next(r for r in results if r.metric == "NMR")
    assert abs(nmr.value - 0.05) < 1e-9
    Path(path).unlink()


def test_custom_criteria() -> None:
    """엄격한 기준 적용."""
    path = _write_csv([
        {"seed": "1", "NMR": "0.04", "MSD": "55", "AU": "0.65", "RTF": "50", "Completion": "0.96"},
    ])
    kpi = load_kpi_csv(path)
    strict = KUAMCriteria(nmr_max=0.03)
    results = evaluate(kpi, strict)
    nmr = next(r for r in results if r.metric == "NMR")
    assert not nmr.passed  # 0.04 > 0.03
    Path(path).unlink()


def test_format_report_contains_status() -> None:
    """보고서에 STATUS 라인 포함."""
    path = _write_csv([
        {"seed": "1", "NMR": "0.03", "MSD": "67", "AU": "0.71", "RTF": "142", "Completion": "1.0"},
    ])
    kpi = load_kpi_csv(path)
    report = format_report(evaluate(kpi))
    assert "STATUS" in report
    assert "PASS" in report
    Path(path).unlink()
