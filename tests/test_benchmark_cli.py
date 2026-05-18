from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


_ROOT = Path(__file__).resolve().parent.parent
_MAIN = _ROOT / "main.py"


def test_benchmark_cli_writes_metrics_json(tmp_path: Path) -> None:
    output_path = tmp_path / "benchmark.json"
    result = subprocess.run(
        [
            sys.executable,
            str(_MAIN),
            "benchmark",
            "--scenario",
            "01_corridor_crossing",
            "--method",
            "orca",
            "--seed",
            "0",
            "--output",
            str(output_path),
            "--quiet",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["scenario_id"] == "01_corridor_crossing"
    assert payload["method"] == "orca"
    assert payload["seed"] == 0
    for key in (
        "near_miss_rate",
        "min_separation_m",
        "path_efficiency",
        "makespan_s",
        "flowtime_s",
        "airspace_utilization",
        "rid_compliance_rate",
        "rtf",
    ):
        assert key in payload
