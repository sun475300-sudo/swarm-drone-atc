# Reproducibility scripts

These scripts are the runtime arm of [`docs/REPRODUCIBILITY.md`](../../docs/REPRODUCIBILITY.md).
Spec-level guarantees and design rationale live there. **This README only documents what each script does.**

| Script | Purpose |
|--------|---------|
| `run_one.sh <scenario_id> <method> <seed>` | Run one simulation, write `results/<timestamp>/<scenario>__<method>__<seed>.json`. |
| `run_all.sh` | Sweep all (scenario × method × seed) combinations from `config/seeds.yaml` and `benchmarks/scenarios/*/`. |
| `aggregate.py <results_dir>` | Walk per-run JSONs in `results_dir` and produce `summary.parquet`. |
| `set_seed.py <seed> [-- cmd...]` | CLI shim around `src.utils.rng.set_global_seed`. Optionally exec a child command. |
| `make_lock.sh [--hashes]` | Regenerate `requirements.lock.txt` from `requirements.txt`. |

## One-command full reproduction

```bash
docker run --rm -v "$(pwd)/results:/app/results" sdacs-repro:0.1.0 \
    bash scripts/reproduce/run_all.sh
```

## Single-scenario debugging loop

```bash
docker run --rm -v "$(pwd)/results:/app/results" sdacs-repro:0.1.0 \
    bash scripts/reproduce/run_one.sh 02_dense_intersection sdacs_hybrid 42
```

## Re-aggregate after a failed run

```bash
python scripts/reproduce/aggregate.py results/2026-04-26T10-15-00/ \
    --output summary.parquet
```

## Lock file workflow

After editing `requirements.txt`:

```bash
bash scripts/reproduce/make_lock.sh           # plain
bash scripts/reproduce/make_lock.sh --hashes  # paper-grade
git add requirements.txt requirements.lock.txt
git commit -m "deps: bump <pkg> to <version>"
```

## See also

- `docs/REPRODUCIBILITY.md` — guarantees, reference hardware, debugging
- `Dockerfile.reproducible` — image definition
- `docker-compose.reproducible.yml` — convenience compose file
- `src/utils/rng.py` — the only allowed RNG entry point
