#!/usr/bin/env bash
# Run a single reproducible benchmark cell.
#
# Usage:
#   scripts/reproduce/run_one.sh <scenario_id> <method> <seed>
# Example:
#   scripts/reproduce/run_one.sh light_traffic_10 hybrid 42

set -euo pipefail

SCENARIO="${1:-light_traffic_10}"
METHOD="${2:-hybrid}"
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
print(f\"[done] ${SCENARIO} ${METHOD} seed=${SEED} nmr={r.get('near_miss_rate','?')} ms={r.get('makespan_s','?')}\")
"
