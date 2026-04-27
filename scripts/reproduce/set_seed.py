#!/usr/bin/env python3
"""CLI shim for :func:`src.utils.rng.set_global_seed`.

Lets bash scripts seed the process before invoking the simulator,
without each script importing the SDACS package directly::

    python scripts/reproduce/set_seed.py 42 -- python main.py simulate ...
"""
from __future__ import annotations

import os
import sys


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print("usage: set_seed.py <seed> [-- <command...>]", file=sys.stderr)
        return 2
    try:
        seed = int(args[0])
    except ValueError:
        print(f"error: seed must be an integer, got {args[0]!r}",
              file=sys.stderr)
        return 2

    # Seed THIS process (also sets env vars for child processes)
    sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )))
    from src.utils.rng import set_global_seed  # noqa: E402
    set_global_seed(seed)

    if len(args) >= 2 and args[1] == "--":
        cmd = args[2:]
        if not cmd:
            return 0
        os.execvp(cmd[0], cmd)
        # unreachable
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
