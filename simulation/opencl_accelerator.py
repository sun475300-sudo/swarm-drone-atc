"""
OpenCL accelerator pilot.
=========================
Openclaw/OpenCL-friendly helper with safe CPU fallback when OpenCL runtime is unavailable.
"""
from __future__ import annotations

from typing import Any


class OpenCLAccelerator:
    def __init__(self) -> None:
        self._available = False
        self._backend = "cpu-fallback"
        try:
            import pyopencl as cl  # type: ignore

            platforms = cl.get_platforms()
            if platforms:
                self._available = True
                self._backend = "pyopencl"
        except Exception:
            self._available = False
            self._backend = "cpu-fallback"

    @property
    def available(self) -> bool:
        return self._available

    @property
    def backend(self) -> str:
        return self._backend

    def vector_add(self, a: list[float], b: list[float]) -> list[float]:
        if len(a) != len(b):
            raise ValueError("Inputs must have the same length")
        return [float(x) + float(y) for x, y in zip(a, b)]

    def dot(self, a: list[float], b: list[float]) -> float:
        if len(a) != len(b):
            raise ValueError("Inputs must have the same length")
        return float(sum(float(x) * float(y) for x, y in zip(a, b)))

    def summary(self) -> dict[str, Any]:
        return {
            "available": self._available,
            "backend": self._backend,
        }
