"""Module: tests/test_simulate_cli.py.

나이틀리 벤치마크 CI(ci.yml)가 호출하는
``main.py simulate --output <path>`` 계약을 회귀 테스트로 고정한다.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_MAIN = _ROOT / "main.py"


def test_simulate_cli_writes_result_json(tmp_path: Path) -> None:
    output_path = tmp_path / "bench.json"
    result = subprocess.run(
        [
            sys.executable,
            str(_MAIN),
            "simulate",
            "--duration",
            "5",
            "--drones",
            "5",
            "--seed",
            "0",
            "--output",
            str(output_path),
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
    assert payload["seed"] == 0
    assert payload["n_drones"] == 5
    for key in (
        "collision_count",
        "near_miss_count",
        "conflict_resolution_rate_pct",
        "route_efficiency_mean",
        "total_distance_km",
        "duration_s",
    ):
        assert key in payload
