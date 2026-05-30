"""P717 — Load test script validation."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent


def test_load_test_script_exists():
    assert (ROOT / "scripts" / "load_test.py").exists()


def test_run_load_test_returns_dict():
    import sys
    sys.path.insert(0, str(ROOT))
    from scripts.load_test import run_load_test

    result = run_load_test(n_drones=5, duration_s=2.0, dt=0.1, seed=42)
    assert isinstance(result, dict)
    assert result["n_drones"] == 5
    assert "rtf" in result
    assert "fps" in result
    assert "tick_p50_ms" in result
    assert "tick_p95_ms" in result
    assert "tick_p99_ms" in result


def test_run_load_test_rtf_positive():
    import sys
    sys.path.insert(0, str(ROOT))
    from scripts.load_test import run_load_test

    result = run_load_test(n_drones=10, duration_s=1.0, dt=0.1, seed=0)
    assert result["rtf"] > 0


def test_load_test_main_quick(tmp_path: Path):
    import sys
    sys.path.insert(0, str(ROOT))
    from scripts.load_test import main

    out = tmp_path / "load.json"
    rc = main(["--quick", "--out", str(out)])
    assert rc == 0
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["n_drones"] == 20
    assert data["fps_ok"] is True
