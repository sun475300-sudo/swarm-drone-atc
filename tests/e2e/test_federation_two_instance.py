"""Pytest gate for the Node Playwright two-instance federation E2E."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tests" / "e2e" / "federation_two_instance.mjs"


@pytest.mark.e2e
@pytest.mark.slow
def test_two_instance_live_and_ghost_rendering() -> None:
    """Run the real two-bridge, two-page Playwright federation scenario."""

    node = shutil.which("node")
    if node is None or not (ROOT / "node_modules" / "playwright").exists():
        pytest.skip("Node Playwright dependencies are not installed")

    env = os.environ.copy()
    env["SDACS_PYTHON"] = sys.executable
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [node, str(SCRIPT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
        check=False,
    )
    assert result.returncode == 0, (
        "Federation Playwright E2E failed.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    assert "PASS federation two-instance E2E" in result.stdout
