"""Verify canonical SHA256 hashes for reproducibility CI.

Reads config/canonical_hashes.yaml, re-runs each cell, and compares the
resulting JSON's SHA256 to the pinned value.

Exit codes:
    0 - all pinned cells matched, pending cells were skipped
    1 - at least one pinned cell mismatched
    2 - manifest is malformed or a cell failed to execute

Usage:
    python scripts/reproduce/verify_canonical_hashes.py
    python scripts/reproduce/verify_canonical_hashes.py --capture  # rewrite pending entries with freshly captured hashes
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "config" / "canonical_hashes.yaml"
MAIN_PY = REPO_ROOT / "main.py"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _run_cell(scenario: str, method: str, seed: int) -> Path:
    out_path = REPO_ROOT / "results" / scenario / method / f"seed{seed}.json"
    subprocess.run(
        [
            sys.executable,
            str(MAIN_PY),
            "benchmark",
            "--scenario",
            scenario,
            "--method",
            method,
            "--seed",
            str(seed),
            "--output",
            str(out_path),
            "--hard-wall-s",
            "120",
            "--quiet",
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    if not out_path.exists():
        raise FileNotFoundError(f"expected output not produced: {out_path}")
    return out_path


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _verify(manifest: dict) -> int:
    cells = manifest.get("cells") or []
    if not cells:
        print("[verify] no cells in manifest", file=sys.stderr)
        return 2

    failures: list[str] = []
    skipped: list[str] = []
    matched: list[str] = []

    for cell in cells:
        tag = f"{cell['scenario']}/{cell['method']}/seed{cell['seed']}"
        if cell.get("status") != "pinned":
            skipped.append(tag)
            continue

        expected = cell.get("sha256")
        if not expected:
            failures.append(f"{tag}: status=pinned but sha256 missing")
            continue

        out_path = _run_cell(cell["scenario"], cell["method"], cell["seed"])
        actual = _sha256(out_path)
        if actual == expected:
            matched.append(tag)
        else:
            failures.append(f"{tag}: expected={expected} actual={actual}")

    print(f"[verify] matched={len(matched)} skipped={len(skipped)} failed={len(failures)}")
    for s in skipped:
        print(f"[verify]  skipped (pending): {s}")
    for f in failures:
        print(f"[verify]  FAIL: {f}", file=sys.stderr)

    return 1 if failures else 0


def _capture(manifest: dict, manifest_path: Path) -> int:
    cells = manifest.get("cells") or []
    today = date.today().isoformat()
    commit = _git_head()
    updated = 0

    for cell in cells:
        if cell.get("status") == "pinned":
            continue
        out_path = _run_cell(cell["scenario"], cell["method"], cell["seed"])
        cell["sha256"] = _sha256(out_path)
        cell["status"] = "pinned"
        cell["captured_on"] = today
        cell["captured_commit"] = commit
        updated += 1
        print(f"[capture] pinned {cell['scenario']}/{cell['method']}/seed{cell['seed']} -> {cell['sha256']}")

    if updated:
        manifest_path.write_text(
            yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        print(f"[capture] wrote {updated} new pin(s) to {manifest_path}")
    else:
        print("[capture] no pending cells to capture")
    return 0


def _load_manifest(manifest_path: Path) -> dict | None:
    try:
        return yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        print(f"[verify] invalid YAML: {exc}", file=sys.stderr)
        return None


def main() -> int:
    """``main`` 동작을 수행한다."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--capture",
        action="store_true",
        help="Rewrite pending cells with freshly captured hashes",
    )
    args = parser.parse_args()

    if not MANIFEST_PATH.exists():
        print(f"[verify] manifest not found: {MANIFEST_PATH}", file=sys.stderr)
        return 2

    manifest = _load_manifest(MANIFEST_PATH)
    if manifest is None:
        return 2

    if args.capture:
        return _capture(manifest, MANIFEST_PATH)
    return _verify(manifest)


if __name__ == "__main__":
    sys.exit(main())
