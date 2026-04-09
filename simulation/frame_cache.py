"""
Phase 661: Frame-based Cache Decorators

BurnySc2/python-sc2의 property_cache_once_per_frame 패턴을 참고하여
시뮬레이션 틱 기반 캐싱 데코레이터를 구현.

Reference: https://github.com/BurnySc2/python-sc2 (MIT License)

시뮬레이션에서 동일 틱 내 반복 계산을 피하기 위한 캐시.
틱이 변경되면 자동으로 캐시가 무효화됩니다.
"""
from __future__ import annotations

import time
from functools import wraps
from typing import Any, Callable, TypeVar

T = TypeVar("T")


class TickCache(dict):
    """틱 기반 캐시 딕셔너리.

    동일한 시뮬레이션 틱 내에서는 캐시된 값을 반환하고,
    틱이 변경되면 캐시를 자동 무효화합니다.
    """

    def __init__(self):
        super().__init__()
        self._current_tick: int = -1

    def get_or_compute(self, key: str, tick: int, compute_fn: Callable[[], T]) -> T:
        """캐시에서 값을 가져오거나, 없으면 계산하여 저장."""
        if tick != self._current_tick:
            self.clear()
            self._current_tick = tick

        if key not in self:
            self[key] = compute_fn()
        return self[key]

    def invalidate(self):
        """캐시 수동 무효화."""
        self.clear()
        self._current_tick = -1


class ExpiringCache:
    """TTL(Time-To-Live) 기반 만료 캐시.

    지정된 시간(초) 후에 항목이 자동으로 만료됩니다.
    드론 텔레메트리 등 시간 제한 데이터에 적합.
    """

    def __init__(self, ttl_seconds: float = 5.0):
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str, default: Any = None) -> Any:
        """값을 가져옴. 만료된 항목은 자동 삭제."""
        if key in self._store:
            ts, val = self._store[key]
            if time.monotonic() - ts <= self._ttl:
                return val
            del self._store[key]
        return default

    def set(self, key: str, value: Any) -> None:
        """값을 저장."""
        self._store[key] = (time.monotonic(), value)

    def __contains__(self, key: str) -> bool:
        if key in self._store:
            ts, _ = self._store[key]
            if time.monotonic() - ts <= self._ttl:
                return True
            del self._store[key]
        return False

    def __len__(self) -> int:
        self._cleanup()
        return len(self._store)

    def _cleanup(self) -> None:
        """만료된 항목 일괄 제거."""
        now = time.monotonic()
        expired = [k for k, (ts, _) in self._store.items() if now - ts > self._ttl]
        for k in expired:
            del self._store[k]

    def clear(self) -> None:
        self._store.clear()

    @property
    def ttl(self) -> float:
        return self._ttl

    @ttl.setter
    def ttl(self, value: float) -> None:
        self._ttl = value


def cache_per_tick(tick_attr: str = "_sim_tick"):
    """시뮬레이션 틱 기반 메서드 캐시 데코레이터.

    동일 틱 내 동일 인자로 호출 시 캐시된 결과를 반환합니다.
    틱이 변경되면 캐시가 자동 리셋됩니다.

    사용법:
        class MyController:
            _sim_tick = 0

            @cache_per_tick()
            def expensive_computation(self):
                ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        cache_key = f"__cache_{func.__qualname__}"
        tick_key = f"__tick_{func.__qualname__}"

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            current_tick = getattr(self, tick_attr, -1)
            cached_tick = getattr(self, tick_key, -2)

            if current_tick == cached_tick and hasattr(self, cache_key):
                return getattr(self, cache_key)

            result = func(self, *args, **kwargs)
            setattr(self, cache_key, result)
            setattr(self, tick_key, current_tick)
            return result

        return wrapper
    return decorator
