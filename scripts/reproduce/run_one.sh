#!/usr/bin/env bash
# Run a single reproducible benchmark cell.
#
# Usage:
#   scripts/reproduce/run_one.sh <scenario_id> <method> <seed>
# Example:
#   scripts/reproduce/run_one.sh 01_corridor_crossing sdacs_hybrid 42

set -euo pipefail

SCENARIO="${1:-01_corridor_crossing}"
METHOD="${2:-sdacs_hybrid}"
SEED="${3:-0}"

OUT_DIR="results/${SCENARIO}/${METHOD}"
mkdir -p "${OUT_DIR}"

OUT_FILE="${OUT_DIR}/seed${SEED}.json"

echo "[reproduce] scenario=${SCENARIO} method=${METHOD} seed=${SEED}"
echo "[reproduce] output -> ${OUT_FILE}"

# Hand off to the real runner. main.py must accept these flags (add if missing).
python main.py benchmark \
    --scenario "${SCENARIO}" \
    --method "${METHOD}" \
    --seed "${SEED}" \
    --output "${OUT_FILE}" \
    --quiet

# Print a single-line summary for grepping.
python -c "
import json, sys
with open('${OUT_FILE}') as f:
    r = json.load(f)
print(f\"[done] ${SCENARIO} ${METHOD} seed=${SEED} NMR={r.get('NMR','?')} MS_s={r.get('MS_s','?')} RID_CR={r.get('RID_CR','?')}\")
"
