"""
OpenCL accelerator pilot.
=========================
Openclaw/OpenCL-friendly helper with safe CPU fallback when OpenCL runtime is unavailable.
"""
from __future__ import annotations

from typing import Any


class OpenCLAccelerator:
    """``OpenCLAccelerator`` 관련 기능을 제공한다."""
    def __init__(self) -> None:
        """인스턴스를 초기화한다."""
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
        """``available`` 동작을 수행한다."""
        return self._available

    @property
    def backend(self) -> str:
        """``backend`` 동작을 수행한다."""
        return self._backend

    def vector_add(self, a: list[float], b: list[float]) -> list[float]:
        """``vector_add`` 동작을 수행한다."""
        if len(a) != len(b):
            raise ValueError("Inputs must have the same length")
        return [float(x) + float(y) for x, y in zip(a, b, strict=False)]

    def dot(self, a: list[float], b: list[float]) -> float:
        """``dot`` 동작을 수행한다."""
        if len(a) != len(b):
            raise ValueError("Inputs must have the same length")
        return float(sum(float(x) * float(y) for x, y in zip(a, b, strict=False)))

    def summary(self) -> dict[str, Any]:
        """현재 상태 요약을 반환한다."""
        return {
            "available": self._available,
            "backend": self._backend,
        }
