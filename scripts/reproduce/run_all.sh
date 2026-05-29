#!/usr/bin/env bash
# Run the full benchmark sweep — 7 scenarios × 2 methods × 30 seeds = 420 runs.
#
# Stores per-run JSONs under results/<scenario>/<method>/seed<N>.json
# Then aggregates into results/summary.parquet for the paper's Table 6.
#
# Scenario IDs match benchmarks/scenarios/ directory names.

set -euo pipefail

SCENARIOS=(
  01_corridor_crossing
  02_dense_intersection
  03_emergency_landing
  04_no_fly_zone
  05_weather_diversion
  06_priority_aircraft
  07_communication_loss
)
METHODS=(sdacs_hybrid orca)
SEEDS=(0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29)

TOTAL=$(( ${#SCENARIOS[@]} * ${#METHODS[@]} * ${#SEEDS[@]} ))
DONE=0
START=$(date +%s)

for scenario in "${SCENARIOS[@]}"; do
  for method in "${METHODS[@]}"; do
    for seed in "${SEEDS[@]}"; do
      DONE=$(( DONE + 1 ))
      printf "[%d/%d] %s / %s / seed=%s\n" "$DONE" "$TOTAL" "$scenario" "$method" "$seed"
      bash scripts/reproduce/run_one.sh "$scenario" "$method" "$seed" || {
        echo "[fail] $scenario/$method/seed=$seed" >&2
      }
    done
  done
done

END=$(date +%s)
echo "[done] $TOTAL runs in $((END - START))s"

echo "[aggregate] -> results/summary.parquet"
python scripts/reproduce/aggregate.py --root results --out results/summary.parquet
