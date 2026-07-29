"""
Canary deployer infrastructure.
===============================
Progressive rollout with automated rollback on SLO breach.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CanaryStep:
    """``CanaryStep`` 관련 기능을 제공한다."""
    step_index: int
    traffic_percent: int
    error_rate: float
    latency_ms: float
    passed: bool
    reason: str


class CanaryDeployer:
    """``CanaryDeployer`` 관련 기능을 제공한다."""
    def __init__(
        self,
        stages: list[int] | None = None,
        max_error_rate: float = 0.02,
        max_latency_ms: float = 250.0,
    ) -> None:
        """인스턴스를 초기화한다."""
        raw_stages = stages or [5, 10, 25, 50, 100]
        self.stages = sorted({max(1, min(100, int(v))) for v in raw_stages})
        if 100 not in self.stages:
            self.stages.append(100)

        self.max_error_rate = max(0.0, float(max_error_rate))
        self.max_latency_ms = max(1.0, float(max_latency_ms))

        self._version: str | None = None
        self._status = "IDLE"
        self._stage_idx = -1
        self._history: list[CanaryStep] = []
        self._rollback_reason = ""

    def start(self, version: str) -> None:
        """`대상` 실행 상태를 제어한다."""
        self._version = version
        self._status = "ROLLING_OUT"
        self._stage_idx = 0
        self._history.clear()
        self._rollback_reason = ""

    def current_traffic(self) -> int:
        """``current_traffic`` 동작을 수행한다."""
        if self._stage_idx < 0:
            return 0
        return self.stages[self._stage_idx]

    def evaluate_step(self, error_rate: float, latency_ms: float) -> CanaryStep:
        """`step` 결과를 계산하거나 판정한다."""
        if self._status != "ROLLING_OUT":
            raise RuntimeError("Canary is not in rolling state")

        err = max(0.0, float(error_rate))
        lat = max(0.0, float(latency_ms))
        passed = err <= self.max_error_rate and lat <= self.max_latency_ms

        if passed:
            reason = "PASS"
        elif err > self.max_error_rate and lat > self.max_latency_ms:
            reason = "ERROR_AND_LATENCY_BREACH"
        elif err > self.max_error_rate:
            reason = "ERROR_RATE_BREACH"
        else:
            reason = "LATENCY_BREACH"

        step = CanaryStep(
            step_index=self._stage_idx,
            traffic_percent=self.current_traffic(),
            error_rate=err,
            latency_ms=lat,
            passed=passed,
            reason=reason,
        )
        self._history.append(step)

        if not passed:
            self.rollback(reason=reason)
            return step

        if self.current_traffic() == 100:
            self._status = "COMPLETE"
            return step

        self._stage_idx += 1
        return step

    def rollback(self, reason: str = "MANUAL") -> None:
        """``rollback`` 동작을 수행한다."""
        self._status = "ROLLED_BACK"
        self._stage_idx = -1
        self._rollback_reason = reason

    def status(self) -> dict[str, Any]:
        """``status`` 동작을 수행한다."""
        return {
            "version": self._version,
            "status": self._status,
            "traffic_percent": self.current_traffic(),
            "current_stage": self._stage_idx,
            "rollback_reason": self._rollback_reason,
            "history": len(self._history),
        }

    def summary(self) -> dict[str, Any]:
        """현재 상태 요약을 반환한다."""
        s = self.status()
        s["stages"] = list(self.stages)
        return s
