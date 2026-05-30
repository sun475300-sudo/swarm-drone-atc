"""P706 — Baseline comparison experiment tests."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent


def test_compare_baselines_script_exists():
    assert (ROOT / "scripts" / "compare_baselines.py").exists()


def test_all_scenario_ids_returns_ten():
    import sys
    sys.path.insert(0, str(ROOT))
    from scripts.compare_baselines import _all_scenario_ids

    ids = _all_scenario_ids()
    assert len(ids) == 10, f"Expected 10 scenarios, got {len(ids)}: {ids}"


def test_load_manifest_returns_dict():
    import sys
    sys.path.insert(0, str(ROOT))
    from scripts.compare_baselines import _load_manifest

    scenario_dir = ROOT / "benchmarks" / "scenarios" / "01_corridor_crossing"
    manifest = _load_manifest(scenario_dir)
    assert isinstance(manifest, dict)
    assert "id" in manifest


def test_run_one_returns_metric_dict():
    import sys
    sys.path.insert(0, str(ROOT))
    from scripts.compare_baselines import _run_one

    metrics = _run_one("01_corridor_crossing", "orca", seed=0, hard_wall_s=5.0)
    assert isinstance(metrics, dict)
    assert "_scenario" in metrics
    assert "_method" in metrics
    assert "_seed" in metrics
    assert "NMR" in metrics
    assert "MSD" in metrics
    assert "PE" in metrics


def test_run_sweep_two_methods_one_seed():
    import sys
    sys.path.insert(0, str(ROOT))
    from scripts.compare_baselines import run_sweep

    rows = run_sweep(
        scenarios=["01_corridor_crossing"],
        methods=["orca", "cbs"],
        seeds=[0],
        hard_wall_s=5.0,
        verbose=False,
    )
    assert len(rows) == 2
    methods = {r["_method"] for r in rows}
    assert methods == {"orca", "cbs"}


def test_build_summary_table():
    import sys
    sys.path.insert(0, str(ROOT))
    from scripts.compare_baselines import build_summary_table

    rows = [
        {"_scenario": "sc1", "_method": "orca", "_seed": 0, "NMR": 0.1, "MSD": 5.0, "PE": 0.9,
         "MS": 60.0, "FT": 120.0, "AU": 0.5, "RID_CR": 1.0, "GFV": 0, "RTF": 10.0},
        {"_scenario": "sc1", "_method": "orca", "_seed": 1, "NMR": 0.2, "MSD": 4.0, "PE": 0.8,
         "MS": 65.0, "FT": 130.0, "AU": 0.55, "RID_CR": 0.95, "GFV": 1, "RTF": 9.0},
    ]
    summary = build_summary_table(rows)
    assert len(summary) == 1
    entry = summary[0]
    assert entry["scenario"] == "sc1"
    assert entry["method"] == "orca"
    assert entry["n_seeds"] == 2
    assert abs(entry["NMR_mean"] - 0.15) < 1e-9


def test_write_csv(tmp_path: Path):
    import sys
    sys.path.insert(0, str(ROOT))
    from scripts.compare_baselines import write_csv

    summary = [
        {"scenario": "s1", "method": "orca", "n_seeds": 1, "NMR_mean": 0.1},
    ]
    out = tmp_path / "out.csv"
    write_csv(summary, out)
    assert out.exists()
    rows = list(csv.DictReader(out.read_text().splitlines()))
    assert len(rows) == 1
    assert rows[0]["scenario"] == "s1"


def test_main_quick_mode(tmp_path: Path):
    import sys
    sys.path.insert(0, str(ROOT))
    from scripts.compare_baselines import main

    out = tmp_path / "comparison.csv"
    rc = main([
        "--quick",
        "--methods", "orca",
        "--scenarios", "01_corridor_crossing",
        "--out", str(out),
    ])
    assert rc == 0
    assert out.exists()
    text = out.read_text()
    assert "orca" in text
