"""
Weather API client.
===================
Provides weather lookup with in-memory TTL cache and deterministic fallback.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import time


WeatherProvider = Callable[[str], dict[str, Any]]


@dataclass
class WeatherSample:
    city: str
    condition: str
    wind_mps: float
    visibility_km: float
    temperature_c: float
    timestamp: float


class WeatherApiClient:
    """Simple weather client with provider injection and TTL cache."""

    def __init__(self, provider: WeatherProvider | None = None, ttl_seconds: int = 300) -> None:
        self.provider = provider
        self.ttl_seconds = max(1, int(ttl_seconds))
        self._cache: dict[str, WeatherSample] = {}
        self._hits = 0
        self._misses = 0

    def _normalize_city(self, city: str) -> str:
        c = (city or "").strip().lower()
        return c or "unknown"

    def _default_provider(self, city: str) -> dict[str, Any]:
        # Deterministic fallback profile for offline simulation.
        base = {
            "condition": "clear",
            "wind_mps": 3.0,
            "visibility_km": 10.0,
            "temperature_c": 20.0,
        }
        city_key = self._normalize_city(city)
        if "incheon" in city_key or "busan" in city_key:
            base["wind_mps"] = 4.5
        if "mountain" in city_key:
            base["visibility_km"] = 8.0
        return base

    def _to_sample(self, city: str, payload: dict[str, Any], now_ts: float) -> WeatherSample:
        return WeatherSample(
            city=city,
            condition=str(payload.get("condition", "clear")).lower(),
            wind_mps=max(0.0, float(payload.get("wind_mps", 3.0))),
            visibility_km=max(0.1, float(payload.get("visibility_km", 10.0))),
            temperature_c=float(payload.get("temperature_c", 20.0)),
            timestamp=float(now_ts),
        )

    def fetch(self, city: str, now_ts: float | None = None) -> WeatherSample:
        now = time.time() if now_ts is None else float(now_ts)
        key = self._normalize_city(city)
        cached = self._cache.get(key)
        if cached and (now - cached.timestamp) <= self.ttl_seconds:
            self._hits += 1
            return cached

        self._misses += 1
        provider = self.provider or self._default_provider
        payload = provider(city)
        sample = self._to_sample(city=city, payload=payload, now_ts=now)
        self._cache[key] = sample
        return sample

    def traffic_factor(self, weather: WeatherSample) -> float:
        """Convert weather state into traffic demand multiplier."""
        factor = 1.0
        if weather.wind_mps >= 12.0:
            factor *= 0.75
        elif weather.wind_mps >= 8.0:
            factor *= 0.88

        if weather.visibility_km < 3.0:
            factor *= 0.8
        elif weather.visibility_km < 6.0:
            factor *= 0.9

        if weather.condition in {"rain", "storm", "snow"}:
            factor *= 0.85

        return max(0.4, min(1.2, round(factor, 3)))

    def cache_size(self) -> int:
        return len(self._cache)

    def summary(self) -> dict[str, Any]:
        total = self._hits + self._misses
        hit_rate = 0.0 if total == 0 else self._hits / total
        return {
            "cache_size": len(self._cache),
            "ttl_seconds": self.ttl_seconds,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 4),
        }
