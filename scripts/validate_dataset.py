"""P703 — SDACS Benchmark Dataset Validator & Exporter.

Usage:
    python scripts/validate_dataset.py [--export <out_dir>] [--strict]

Validates all scenario manifests in benchmarks/scenarios/ against the JSON
schema in benchmarks/_schema/manifest.schema.json, then optionally packages
the dataset into a Zenodo-compatible directory structure.

Exit codes:
    0  — all manifests valid (and export completed if requested)
    1  — one or more validation errors
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
SCENARIOS_DIR = ROOT / "benchmarks" / "scenarios"
SCHEMA_FILE = ROOT / "benchmarks" / "_schema" / "manifest.schema.json"
DATASET_CARD = ROOT / "benchmarks" / "DATASET_CARD.md"
CITATION_BIB = ROOT / "benchmarks" / "CITATION.bib"


def _load_schema() -> dict:
    with SCHEMA_FILE.open() as f:
        return json.load(f)


def _load_manifest(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


def _validate_manifest(manifest: dict, schema: dict, scenario_id: str) -> list[str]:
    """Lightweight structural validation without jsonschema dependency."""
    errors: list[str] = []

    required = schema.get("required", [])
    for field in required:
        if field not in manifest:
            errors.append(f"{scenario_id}: missing required field '{field}'")

    # id must match directory name
    if manifest.get("id") != scenario_id:
        errors.append(
            f"{scenario_id}: manifest id '{manifest.get('id')}' "
            f"does not match directory name '{scenario_id}'"
        )

    # category enum
    category = manifest.get("category", "")
    if category not in ("standard", "stress"):
        errors.append(f"{scenario_id}: invalid category '{category}'")

    # difficulty enum
    difficulty = manifest.get("difficulty", "")
    if difficulty not in ("easy", "medium", "hard", "extreme"):
        errors.append(f"{scenario_id}: invalid difficulty '{difficulty}'")

    # positive duration
    dur = manifest.get("duration_seconds", 0)
    if not isinstance(dur, (int, float)) or dur <= 0:
        errors.append(f"{scenario_id}: duration_seconds must be > 0")

    # agent count
    agents = manifest.get("agents", {})
    count = agents.get("count", 0)
    if not isinstance(count, int) or count < 1:
        errors.append(f"{scenario_id}: agents.count must be >= 1")

    # success criteria
    sc = manifest.get("success_criteria", {})
    for key in ("NMR_max", "MSD_min_m", "RID_CR_min"):
        if key not in sc:
            errors.append(f"{scenario_id}: success_criteria.{key} missing")

    return errors


def validate_all() -> tuple[int, int, list[str]]:
    """Return (valid_count, total_count, errors)."""
    schema = _load_schema()
    scenarios = sorted(SCENARIOS_DIR.iterdir())
    all_errors: list[str] = []
    valid = 0

    for scenario_dir in scenarios:
        if not scenario_dir.is_dir():
            continue
        manifest_path = scenario_dir / "manifest.yaml"
        if not manifest_path.exists():
            all_errors.append(f"{scenario_dir.name}: manifest.yaml not found")
            continue
        manifest = _load_manifest(manifest_path)
        errs = _validate_manifest(manifest, schema, scenario_dir.name)
        if errs:
            all_errors.extend(errs)
        else:
            valid += 1

    total = sum(1 for d in scenarios if d.is_dir())
    return valid, total, all_errors


def export_dataset(out_dir: Path) -> None:
    """Package benchmark scenarios into a Zenodo-compatible directory."""
    out_dir.mkdir(parents=True, exist_ok=True)

    # copy scenarios
    scenarios_out = out_dir / "scenarios"
    if scenarios_out.exists():
        shutil.rmtree(scenarios_out)
    shutil.copytree(SCENARIOS_DIR, scenarios_out)

    # copy schema
    schema_out = out_dir / "_schema"
    schema_out.mkdir(exist_ok=True)
    shutil.copy(SCHEMA_FILE, schema_out / SCHEMA_FILE.name)

    # copy metadata
    for src in (DATASET_CARD, CITATION_BIB):
        if src.exists():
            shutil.copy(src, out_dir / src.name)

    # generate summary JSON
    manifests = []
    for sc_dir in sorted(scenarios_out.iterdir()):
        mp = sc_dir / "manifest.yaml"
        if mp.exists():
            manifests.append(_load_manifest(mp))

    summary = {
        "dataset": "SDACS-Benchmark-v1",
        "n_scenarios": len(manifests),
        "categories": {
            "standard": sum(1 for m in manifests if m.get("category") == "standard"),
            "stress": sum(1 for m in manifests if m.get("category") == "stress"),
        },
        "scenarios": [
            {
                "id": m.get("id"),
                "name": m.get("name"),
                "category": m.get("category"),
                "difficulty": m.get("difficulty"),
                "agents": m.get("agents", {}).get("count"),
                "duration_s": m.get("duration_seconds"),
            }
            for m in manifests
        ],
    }
    with (out_dir / "dataset_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)

    print(f"Dataset exported to: {out_dir}")
    print(f"  Scenarios: {len(manifests)}")
    print(f"  Files: {sum(1 for _ in out_dir.rglob('*') if _.is_file())}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and export SDACS benchmark dataset")
    parser.add_argument("--export", metavar="DIR", help="Export dataset to directory")
    parser.add_argument("--strict", action="store_true", help="Exit 1 on any warning")
    args = parser.parse_args()

    print("Validating benchmark scenarios...")
    valid, total, errors = validate_all()

    if errors:
        for e in errors:
            print(f"  ERROR: {e}", file=sys.stderr)
        print(f"\nResult: {valid}/{total} valid", file=sys.stderr)
        return 1

    print(f"  OK: {valid}/{total} scenario manifests valid")

    if args.export:
        export_dataset(Path(args.export))

    return 0


if __name__ == "__main__":
    sys.exit(main())
