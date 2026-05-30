"""P700 — HITL FMEA report generator tests."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def test_fmea_script_exists():
    assert (ROOT / "scripts" / "generate_fmea.py").exists()


def test_build_fmea_report_returns_string():
    import sys
    sys.path.insert(0, str(ROOT))
    from scripts.generate_fmea import build_fmea_report

    report = build_fmea_report()
    assert isinstance(report, str)
    assert len(report) > 100


def test_fmea_report_contains_required_sections():
    import sys
    sys.path.insert(0, str(ROOT))
    from scripts.generate_fmea import build_fmea_report

    report = build_fmea_report()
    assert "FMEA" in report
    assert "RPN" in report
    assert "HITL" in report
    assert "경감" in report


def test_fmea_items_have_valid_rpn():
    import sys
    sys.path.insert(0, str(ROOT))
    from scripts.generate_fmea import FMEA_ITEMS

    for item in FMEA_ITEMS:
        fid, comp, mode, effect, s, o, d, rpn, mitigation = item
        assert rpn == s * o * d, f"{fid}: RPN mismatch: {s}×{o}×{d}≠{rpn}"
        assert 1 <= s <= 10, f"{fid}: Severity out of range: {s}"
        assert 1 <= o <= 10, f"{fid}: Occurrence out of range: {o}"
        assert 1 <= d <= 10, f"{fid}: Detection out of range: {d}"


def test_fmea_covers_hw_sw_cm_reg_categories():
    import sys
    sys.path.insert(0, str(ROOT))
    from scripts.generate_fmea import FMEA_ITEMS

    prefixes = {item[0].split("-")[0] for item in FMEA_ITEMS}
    assert "HW" in prefixes
    assert "SW" in prefixes
    assert "CM" in prefixes
    assert "REG" in prefixes


def test_generate_fmea_main_writes_file(tmp_path: Path):
    import sys
    sys.path.insert(0, str(ROOT))
    from scripts.generate_fmea import main

    out = tmp_path / "fmea.md"
    rc = main(["--output", str(out)])
    assert rc == 0
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "SDACS HITL" in content


def test_generate_fmea_cli_exit_zero(tmp_path: Path):
    out = tmp_path / "fmea_cli.md"
    result = subprocess.run(
        [sys.executable, "scripts/generate_fmea.py", "--output", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert out.exists()
