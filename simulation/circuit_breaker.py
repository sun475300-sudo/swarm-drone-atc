"""
Circuit breaker infrastructure.
===============================
Failure-rate based breaker with CLOSED, OPEN, HALF_OPEN state transitions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import time


@dataclass
class CircuitState:
    state: str
    failures: int
    successes: int
    opened_at: float | None


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 5.0,
        half_open_max_calls: int = 2,
    ) -> None:
        self.failure_threshold = max(1, int(failure_threshold))
        self.recovery_timeout = max(0.1, float(recovery_timeout))
        self.half_open_max_calls = max(1, int(half_open_max_calls))

        self._state = "CLOSED"
        self._failures = 0
        self._successes = 0
        self._opened_at: float | None = None
        self._half_open_calls = 0
        self._blocked = 0

    def _now(self) -> float:
        return time.monotonic()

    def _to_half_open_if_ready(self) -> None:
        if self._state != "OPEN":
            return
        if self._opened_at is None:
            return
        if (self._now() - self._opened_at) >= self.recovery_timeout:
            self._state = "HALF_OPEN"
            self._half_open_calls = 0

    def allow_request(self) -> bool:
        self._to_half_open_if_ready()
        if self._state == "OPEN":
            self._blocked += 1
            return False
        if self._state == "HALF_OPEN" and self._half_open_calls >= self.half_open_max_calls:
            self._blocked += 1
            return False
        if self._state == "HALF_OPEN":
            self._half_open_calls += 1
        return True

    def record_success(self) -> None:
        self._successes += 1
        if self._state == "HALF_OPEN":
            if self._half_open_calls >= self.half_open_max_calls:
                self._state = "CLOSED"
                self._failures = 0
                self._half_open_calls = 0

    def record_failure(self) -> None:
        self._failures += 1
        if self._state == "HALF_OPEN":
            self._state = "OPEN"
            self._opened_at = self._now()
            self._half_open_calls = 0
            return
        if self._failures >= self.failure_threshold:
            self._state = "OPEN"
            self._opened_at = self._now()

    def execute(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        if not self.allow_request():
            raise RuntimeError("Circuit breaker is OPEN")
        try:
            result = fn(*args, **kwargs)
        except Exception:
            self.record_failure()
            raise
        self.record_success()
        return result

    def state(self) -> CircuitState:
        self._to_half_open_if_ready()
        return CircuitState(
            state=self._state,
            failures=self._failures,
            successes=self._successes,
            opened_at=self._opened_at,
        )

    def summary(self) -> dict[str, Any]:
        st = self.state()
        return {
            "state": st.state,
            "failures": st.failures,
            "successes": st.successes,
            "blocked": self._blocked,
            "failure_threshold": self.failure_threshold,
        }
