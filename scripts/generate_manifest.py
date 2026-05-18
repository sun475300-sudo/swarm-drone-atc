"""
test_manifest.json + environment_snapshot.txt 자동 생성.

실행: python scripts/generate_manifest.py
출력: reports/test_manifest.json, reports/environment_snapshot.txt
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
REPORTS = ROOT / "reports"


def _run(cmd: list[str], **kw) -> str:
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL, **kw).decode().strip()
    except Exception:
        return "N/A"


def _pip_freeze() -> list[str]:
    try:
        out = subprocess.check_output([sys.executable, "-m", "pip", "freeze"],
                                      stderr=subprocess.DEVNULL).decode()
        return [ln.strip() for ln in out.splitlines() if ln.strip()]
    except Exception:
        return []


def generate() -> None:
    REPORTS.mkdir(exist_ok=True)

    git_sha   = _run(["git", "rev-parse", "HEAD"], cwd=ROOT)
    git_branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT)
    git_tag   = _run(["git", "describe", "--tags", "--always"], cwd=ROOT)

    packages = _pip_freeze()

    manifest = {
        "generated_at": datetime.now().isoformat(),
        "project": "SDACS (Swarm Drone Airspace Control System)",
        "version": git_tag,
        "git": {
            "sha": git_sha,
            "branch": git_branch,
            "tag": git_tag,
        },
        "python": {
            "version": sys.version,
            "executable": sys.executable,
            "platform": sys.platform,
        },
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "environment": {
            "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED", "not set"),
            "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS", "not set"),
            "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS", "not set"),
            "SDACS_ENABLE_TORCH": os.environ.get("SDACS_ENABLE_TORCH", "0"),
        },
        "packages": packages,
        "test_command": "pytest tests/ --tb=short -q --cov=src --cov=simulation --cov-report=xml --cov-report=html --junitxml=reports/test_results.xml",
        "rng_seed": 42,
        "notes": "재현성 보장: PYTHONHASHSEED=0, OMP_NUM_THREADS=1 권장",
    }

    manifest_path = REPORTS / "test_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"manifest → {manifest_path}")

    # 사람이 읽을 수 있는 환경 스냅샷
    snapshot_path = REPORTS / "environment_snapshot.txt"
    with open(snapshot_path, "w", encoding="utf-8") as f:
        f.write(f"SDACS 시험 환경 명세서\n")
        f.write(f"생성일시: {manifest['generated_at']}\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"[프로젝트]\n")
        f.write(f"  이름   : {manifest['project']}\n")
        f.write(f"  버전   : {manifest['version']}\n")
        f.write(f"  Git SHA: {git_sha}\n")
        f.write(f"  브랜치 : {git_branch}\n\n")
        f.write(f"[Python 환경]\n")
        f.write(f"  버전   : {sys.version}\n")
        f.write(f"  플랫폼 : {sys.platform}\n\n")
        f.write(f"[운영체제]\n")
        f.write(f"  시스템 : {platform.system()} {platform.release()}\n")
        f.write(f"  머신   : {platform.machine()}\n")
        f.write(f"  프로세서: {platform.processor()}\n\n")
        f.write(f"[환경변수]\n")
        for k, v in manifest["environment"].items():
            f.write(f"  {k}: {v}\n")
        f.write(f"\n[설치 패키지 ({len(packages)}개)]\n")
        for pkg in packages:
            f.write(f"  {pkg}\n")
    print(f"snapshot → {snapshot_path}")


if __name__ == "__main__":
    generate()
