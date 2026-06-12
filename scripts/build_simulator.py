"""Build the standalone SDACS web simulator artifact.

The root ``swarm_3d_simulator.html`` is the canonical simulator source.
This script mirrors that file into the runtime copies used by GitHub Pages
and local preview flows, then creates a small static artifact under
``build/simulator`` for local preview or manual hosting.
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "swarm_3d_simulator.html"
DEFAULT_DIST = ROOT / "build" / "simulator"

SYNC_TARGETS = (
    ROOT / "visualization" / "swarm_3d_simulator.html",
    ROOT / "docs" / "swarm_3d_simulator.html",
    ROOT / "docs" / "simulator.html",
)

STATIC_FILES = (
    ROOT / "manifest.webmanifest",
    ROOT / "sdacs-sw.js",
)

VENDOR_DIRS = (
    ROOT / "vendor" / "three",
)


def copy_file(src: Path, dst: Path) -> None:
    """Copy one file while preserving metadata and creating the parent folder."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def write_index(dist: Path) -> None:
    """Create a minimal static index that forwards to the main simulator."""
    index = dist / "index.html"
    index.write_text(
        """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url=simulator.html">
  <title>SDACS Simulator</title>
</head>
<body>
  <a href="simulator.html">Open SDACS Simulator</a>
</body>
</html>
""",
        encoding="utf-8",
    )


def validate_source() -> None:
    """Fail early when the canonical simulator file is missing or incomplete."""
    if not SOURCE.exists():
        raise FileNotFoundError(f"missing canonical simulator: {SOURCE}")
    text = SOURCE.read_text(encoding="utf-8")
    required = ('<script type="importmap">', "vendor/three/three.module.js", "window._sdacs")
    missing = [token for token in required if token not in text]
    if missing:
        raise RuntimeError(f"canonical simulator failed sanity check: missing {', '.join(missing)}")


def sync_runtime_copies() -> list[Path]:
    """Mirror the canonical simulator into all runtime entry points."""
    copied: list[Path] = []
    for target in SYNC_TARGETS:
        copy_file(SOURCE, target)
        copied.append(target)
    return copied


def build_artifact(dist: Path) -> list[Path]:
    """Create a static simulator-only artifact with local vendor dependencies."""
    dist.mkdir(parents=True, exist_ok=True)

    copied: list[Path] = []
    for name in ("simulator.html", "swarm_3d_simulator.html"):
        target = dist / name
        copy_file(SOURCE, target)
        copied.append(target)

    for src in STATIC_FILES:
        if src.exists():
            target = dist / src.name
            copy_file(src, target)
            copied.append(target)

    for src in VENDOR_DIRS:
        if src.exists():
            target = dist / "vendor" / src.name
            shutil.copytree(src, target, dirs_exist_ok=True)
            copied.append(target)

    write_index(dist)
    copied.append(dist / "index.html")
    return copied


def check_outputs(dist: Path, include_artifact: bool) -> None:
    """Verify that generated files are present and synced with the canonical source."""
    validate_source()

    mismatches = [p for p in SYNC_TARGETS if not p.exists() or not filecmp.cmp(SOURCE, p, shallow=False)]
    if include_artifact:
        mismatches.extend(
            p for p in (dist / "simulator.html", dist / "swarm_3d_simulator.html")
            if not p.exists() or not filecmp.cmp(SOURCE, p, shallow=False)
        )
        required = [dist / "index.html", dist / "vendor" / "three" / "three.module.js"]
        mismatches.extend(p for p in required if not p.exists())

    if mismatches:
        details = "\n".join(f"  - {p.relative_to(ROOT)}" for p in mismatches)
        raise RuntimeError(f"simulator build outputs are stale or missing:\n{details}")


def main() -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Build/sync the SDACS web simulator.")
    parser.add_argument("--dist", type=Path, default=DEFAULT_DIST, help="artifact output directory")
    parser.add_argument("--sync-only", action="store_true", help="only sync runtime copies, skip build/simulator")
    parser.add_argument("--check", action="store_true", help="verify outputs without writing files")
    args = parser.parse_args()

    dist = args.dist if args.dist.is_absolute() else ROOT / args.dist

    if args.check:
        check_outputs(dist, include_artifact=not args.sync_only)
        print("Simulator build outputs are current.")
        return 0

    validate_source()
    copied = sync_runtime_copies()
    if not args.sync_only:
        copied.extend(build_artifact(dist))

    print("Simulator build complete:")
    for path in copied:
        print(f"  - {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
