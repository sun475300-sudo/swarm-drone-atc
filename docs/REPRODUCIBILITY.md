# Reproducibility Guide

**Phase:** P704
**Audience:** paper reviewers and anyone who wants to verify our numbers.

---

## TL;DR (one-liner)

```bash
git clone https://github.com/jangsunwoo/swarm-drone-atc.git && \
cd swarm-drone-atc && \
docker build -t sdacs-repro:0.1.0 -f Dockerfile.reproducible . && \
docker run --rm -v "$(pwd)/results:/app/results" sdacs-repro:0.1.0 \
    bash scripts/reproduce/run_all.sh
```

Expected wall time on reference hardware (16 cores / 32 GB): **~25 minutes**.
Output: `results/summary.parquet` plus 420 per-run JSONs.

---

## What "reproducible" means here

Two stronger-than-usual guarantees:

1. **Bit-level determinism for each run.** The same seed produces identical JSON to the last decimal, because:
   - `PYTHONHASHSEED=0`
   - `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1` (no parallel float reductions)
   - All RNGs routed through a single `numpy.random.default_rng(seed)` instance (see `src/utils/rng.py` — **TODO** if not yet centralized)
   - No wall-clock time used as a randomness source (search `time.time()` usages)
2. **Build reproducibility.** Pinned base image digest + `requirements.lock.txt` + `setuptools`/`pip` pinned.

---

## Reference hardware

| Component | Spec |
|-----------|------|
| CPU | 16 physical cores, x86_64, AVX2 |
| RAM | 32 GB |
| Storage | 50 GB free |
| Docker | 24.0+ |
| OS | Ubuntu 22.04 host (any host works as long as Docker runs) |

If you run on 8-core / 16 GB, set `--parallel 4` (halve the concurrent runs).

---

## Files involved

| File | Role |
|------|------|
| `Dockerfile.reproducible` | Pinned image. Sets `PYTHONHASHSEED=0`, thread limits, non-root user. |
| `requirements.txt` | Loose top-level deps. |
| `requirements.lock.txt` | (**TODO**) Fully pinned transitive deps via `pip-compile`. |
| `scripts/reproduce/run_one.sh` | Single cell: one (scenario, method, seed) |
| `scripts/reproduce/run_all.sh` | Full sweep: 7 × 2 × 30 = 420 runs |
| `scripts/reproduce/aggregate.py` | Rolls per-run JSONs up into a parquet table |
| `config/seeds.yaml` | (**TODO**) The 30 seeds of record (0..29 by default) |

---

## Generating `requirements.lock.txt`

```bash
pip install pip-tools==7.4.1
pip-compile --generate-hashes --resolver=backtracking \
    --output-file requirements.lock.txt \
    requirements.txt
```

Commit `requirements.lock.txt` alongside any `requirements.txt` bump.

---

## Verifying a single run matches the paper

After running `run_one.sh`, compare to the expected hash:

```bash
sha256sum results/light_traffic_10/hybrid/seed42.json
# expected (example): TODO — fill in after first canonical run
```

Any deviation means non-determinism leaked in. Known causes to check:
- `random.random()` called without `random.seed()` — use `default_rng(seed).random()` instead.
- `dict` iteration order used in a metric (Python 3.7+ preserves insertion order, but set/frozenset do not).
- `numpy.random` global state (use a `Generator`, not the legacy API).
- Threaded BLAS reductions — handled by env vars but verify `np.show_config()` inside the container.

---

## What's still TODO for full reproducibility

- [ ] `src/utils/rng.py` — single RNG factory used by every module
- [ ] `config/seeds.yaml` — committed canonical seeds
- [ ] `main.py benchmark` subcommand — adapter between `run_one.sh` and existing simulator code
- [ ] `requirements.lock.txt` — generated via pip-compile
- [ ] Expected SHA256 table for reference runs (commit after first canonical pass)
- [ ] CI job that re-runs 3 canonical cells on every PR and fails if hashes change
- [ ] Archive the Docker image on Zenodo with a DOI for the paper camera-ready

---

## Non-Docker path

For local development without Docker:

```bash
python3.10 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export PYTHONHASHSEED=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
bash scripts/reproduce/run_one.sh light_traffic_10 hybrid 42
```

Results are NOT guaranteed to match Docker-produced results exactly — different BLAS versions can differ in the last 1-2 bits. Use Docker for any number that goes into the paper.
