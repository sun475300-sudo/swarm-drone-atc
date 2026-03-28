"""
실시간 가격 엔진
===============
수요/기상/거리 기반 동적 가격 산정.

사용법:
    pe = PricingEngine(base_price=5000)
    price = pe.calculate(distance_km=5, demand_level=0.8, wind_speed=12)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass
class PriceQuote:
    base: float
    distance_surcharge: float
    demand_surcharge: float
    weather_surcharge: float
    total: float
    currency: str = "KRW"


class PricingEngine:
    def __init__(self, base_price: float = 5000, per_km: float = 1000, demand_multiplier: float = 0.5, weather_multiplier: float = 0.3) -> None:
        self.base_price = base_price
        self.per_km = per_km
        self.demand_multiplier = demand_multiplier
        self.weather_multiplier = weather_multiplier
        self._quotes: list[PriceQuote] = []

    def calculate(self, distance_km: float = 1.0, demand_level: float = 0.5, wind_speed: float = 5.0, priority: int = 5) -> PriceQuote:
        dist_surcharge = distance_km * self.per_km
        demand_surcharge = self.base_price * demand_level * self.demand_multiplier
        weather_surcharge = self.base_price * max(0, (wind_speed - 10) / 15) * self.weather_multiplier
        priority_mult = 1 + (priority - 5) * 0.1

        total = (self.base_price + dist_surcharge + demand_surcharge + weather_surcharge) * priority_mult
        quote = PriceQuote(
            base=self.base_price, distance_surcharge=round(dist_surcharge),
            demand_surcharge=round(demand_surcharge),
            weather_surcharge=round(weather_surcharge),
            total=round(total),
        )
        self._quotes.append(quote)
        return quote

    def average_price(self) -> float:
        if not self._quotes:
            return 0
        return round(sum(q.total for q in self._quotes) / len(self._quotes))

    def summary(self) -> dict[str, Any]:
        return {
            "quotes_generated": len(self._quotes),
            "avg_price": self.average_price(),
            "base_price": self.base_price,
        }
