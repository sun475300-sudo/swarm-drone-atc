"""
Rate limiter infrastructure.
============================
Token-bucket limiter with per-key quotas and burst control.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import time


@dataclass
class Bucket:
    tokens: float
    last_refill: float


class RateLimiter:
    def __init__(self, rate_per_sec: float = 10.0, burst: int = 20) -> None:
        self.rate_per_sec = max(0.1, float(rate_per_sec))
        self.burst = max(1, int(burst))
        self._buckets: dict[str, Bucket] = {}
        self._allowed = 0
        self._blocked = 0

    def _now(self) -> float:
        return time.monotonic()

    def _bucket(self, key: str) -> Bucket:
        now = self._now()
        if key not in self._buckets:
            self._buckets[key] = Bucket(tokens=float(self.burst), last_refill=now)
            return self._buckets[key]
        b = self._buckets[key]
        elapsed = max(0.0, now - b.last_refill)
        b.tokens = min(float(self.burst), b.tokens + elapsed * self.rate_per_sec)
        b.last_refill = now
        return b

    def allow(self, key: str = "global", cost: float = 1.0) -> bool:
        cost = max(0.0, float(cost))
        b = self._bucket(key)
        if b.tokens >= cost:
            b.tokens -= cost
            self._allowed += 1
            return True
        self._blocked += 1
        return False

    def remaining(self, key: str = "global") -> float:
        return self._bucket(key).tokens

    def summary(self) -> dict[str, Any]:
        return {
            "keys": len(self._buckets),
            "allowed": self._allowed,
            "blocked": self._blocked,
            "rate_per_sec": self.rate_per_sec,
            "burst": self.burst,
        }
