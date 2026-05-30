"""P703 — Dataset validation and export tests."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent


def test_schema_is_valid_json():
    schema_path = ROOT / "benchmarks" / "_schema" / "manifest.schema.json"
    assert schema_path.exists(), "manifest.schema.json must exist"
    data = json.loads(schema_path.read_text())
    assert data.get("type") == "object"
    assert "required" in data
    assert "properties" in data


def test_validate_all_scenarios_pass():
    from scripts.validate_dataset import validate_all

    valid, total, errors = validate_all()
    assert errors == [], f"Validation errors: {errors}"
    assert total == 10, f"Expected 10 scenarios, got {total}"
    assert valid == total


def test_validate_dataset_cli_exit_zero():
    result = subprocess.run(
        [sys.executable, "scripts/validate_dataset.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "10/10" in result.stdout


def test_export_dataset(tmp_path: Path):
    from scripts.validate_dataset import export_dataset

    export_dataset(tmp_path)

    assert (tmp_path / "scenarios").is_dir()
    assert (tmp_path / "_schema" / "manifest.schema.json").exists()
    assert (tmp_path / "dataset_summary.json").exists()

    summary = json.loads((tmp_path / "dataset_summary.json").read_text())
    assert summary["n_scenarios"] == 10
    assert summary["categories"]["standard"] + summary["categories"]["stress"] == 10


def test_daily_status_script_runs(tmp_path: Path):
    out = tmp_path / "status.md"
    result = subprocess.run(
        [sys.executable, "scripts/sdacs_daily_status.py", "--output", str(out), "--no-git"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    content = out.read_text()
    assert "SDACS Daily Status" in content
    assert "ROADMAP" in content
    assert "벤치마크" in content
