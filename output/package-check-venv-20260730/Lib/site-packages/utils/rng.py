"""Centralized RNG for SDACS — Phase 704.

Every random source in the codebase MUST go through this module so that
``--seed N`` produces bit-identical traces across runs (within the
guarantees documented in ``docs/REPRODUCIBILITY.md``).

Usage::

    from src.utils.rng import set_global_seed, get_rng

    set_global_seed(42)               # do once at process start
    rng = get_rng()                   # numpy.random.Generator
    arr = rng.uniform(0, 1, size=8)

    # If you need a sub-seeded child stream (e.g. per-agent):
    child_rng = get_rng().spawn(1)[0]

What this module guarantees:

* Stable single-process determinism for ``random``, ``numpy``, and
  optionally ``torch`` if installed.
* Sets ``PYTHONHASHSEED``, ``OMP_NUM_THREADS``, ``MKL_NUM_THREADS``,
  ``OPENBLAS_NUM_THREADS`` for the *current* process. (For sub-processes,
  these need to be set in the environment before launch — that's why
  the Dockerfile sets them too.)
* Surfaces a single ``numpy.random.Generator`` so all random draws come
  from one stream — no hidden ``numpy.random.seed`` global state.

What it does NOT guarantee:

* Multi-process / multi-thread determinism (BLAS reductions reorder).
* GPU determinism on non-NVIDIA hardware.
* Bit-equality across NumPy major version bumps.
"""
from __future__ import annotations

import os
import random
from typing import Optional

import numpy as np


_GLOBAL_RNG: Optional[np.random.Generator] = None
_GLOBAL_SEED: Optional[int] = None


def set_global_seed(seed: int = 42) -> None:
    """Seed every randomness source for the current process.

    Idempotent: calling twice with the same seed is a no-op.

    Args:
        seed: Non-negative integer; default 42 to match the spec.
    """
    if seed < 0:
        raise ValueError(f"seed must be >= 0, got {seed}")

    global _GLOBAL_RNG, _GLOBAL_SEED
    _GLOBAL_SEED = int(seed)

    # Standard library random
    random.seed(seed)

    # NumPy: prefer the new Generator API and route everything through it.
    _GLOBAL_RNG = np.random.default_rng(seed)
    # Keep the legacy global state in sync for any third-party that ignores
    # our API. This is the only place we touch the legacy seed.
    np.random.seed(seed)

    # Torch is optional — silently skipped if not installed.
    try:
        import torch  # type: ignore[import-not-found]

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        # cuDNN determinism (slower but reproducible)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except ImportError:
        pass

    # Hash randomization off
    os.environ["PYTHONHASHSEED"] = str(seed)
    # Thread caps so BLAS reductions are deterministic
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS",
                "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ.setdefault(var, "1")


def get_rng() -> np.random.Generator:
    """Return the process-wide :class:`numpy.random.Generator`.

    Raises:
        RuntimeError: if :func:`set_global_seed` was never called.
    """
    if _GLOBAL_RNG is None:
        raise RuntimeError(
            "RNG used before set_global_seed() was called. "
            "Call set_global_seed(seed) at the start of main()."
        )
    return _GLOBAL_RNG


def get_current_seed() -> int:
    """Return the seed passed to the most recent :func:`set_global_seed` call."""
    if _GLOBAL_SEED is None:
        raise RuntimeError(
            "set_global_seed() was never called in this process."
        )
    return _GLOBAL_SEED


def reset_for_test() -> None:
    """Re-init module state. **Test-only** — never call from production code."""
    global _GLOBAL_RNG, _GLOBAL_SEED
    _GLOBAL_RNG = None
    _GLOBAL_SEED = None
