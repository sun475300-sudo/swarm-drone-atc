#!/usr/bin/env bash
# Regenerate requirements.lock.txt from requirements.txt using pip-compile.
# Run this after editing requirements.txt and commit BOTH files together.
#
# Usage:
#     bash scripts/reproduce/make_lock.sh
#     # or with hashes (slow but maximally reproducible):
#     bash scripts/reproduce/make_lock.sh --hashes

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if ! command -v pip-compile >/dev/null 2>&1; then
  echo "[make_lock] installing pip-tools..."
  pip install --quiet "pip-tools==7.4.1"
fi

ARGS=( --resolver=backtracking
       --no-header
       --output-file=requirements.lock.txt )

if [[ "${1:-}" == "--hashes" ]]; then
  ARGS+=( --generate-hashes )
fi

echo "[make_lock] compiling requirements.txt -> requirements.lock.txt"
pip-compile "${ARGS[@]}" requirements.txt

echo "[make_lock] done."
echo "[make_lock] git diff requirements.lock.txt to inspect the change."
