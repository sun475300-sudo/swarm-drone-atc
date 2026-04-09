"""
Distributed lock infrastructure.
================================
In-memory lease lock abstraction with ownership and expiration checks.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import time


@dataclass
class Lease:
    key: str
    owner: str
    expires_at: float


class DistributedLock:
    def __init__(self, default_ttl_sec: float = 5.0) -> None:
        self.default_ttl_sec = max(0.1, float(default_ttl_sec))
        self._locks: dict[str, Lease] = {}
        self._acquired = 0
        self._rejected = 0

    def _now(self) -> float:
        return time.monotonic()

    def _cleanup(self) -> None:
        now = self._now()
        expired = [k for k, v in self._locks.items() if v.expires_at <= now]
        for key in expired:
            del self._locks[key]

    def acquire(self, key: str, owner: str, ttl_sec: float | None = None) -> bool:
        self._cleanup()
        ttl = self.default_ttl_sec if ttl_sec is None else max(0.1, float(ttl_sec))
        lock = self._locks.get(key)
        if lock is not None and lock.owner != owner:
            self._rejected += 1
            return False
        self._locks[key] = Lease(key=key, owner=owner, expires_at=self._now() + ttl)
        self._acquired += 1
        return True

    def release(self, key: str, owner: str) -> bool:
        self._cleanup()
        lock = self._locks.get(key)
        if lock is None or lock.owner != owner:
            return False
        del self._locks[key]
        return True

    def renew(self, key: str, owner: str, ttl_sec: float | None = None) -> bool:
        self._cleanup()
        lock = self._locks.get(key)
        if lock is None or lock.owner != owner:
            return False
        ttl = self.default_ttl_sec if ttl_sec is None else max(0.1, float(ttl_sec))
        lock.expires_at = self._now() + ttl
        return True

    def owner_of(self, key: str) -> str | None:
        self._cleanup()
        lock = self._locks.get(key)
        return None if lock is None else lock.owner

    def summary(self) -> dict[str, Any]:
        self._cleanup()
        return {
            "active_locks": len(self._locks),
            "acquired": self._acquired,
            "rejected": self._rejected,
            "default_ttl_sec": self.default_ttl_sec,
        }
