"""
고객 서비스 지표
===============
배송 시간/정확도/만족도 KPI.

사용법:
    cm = CustomerMetrics()
    cm.record_delivery("c1", promised_min=30, actual_min=25)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class DeliveryRecord:
    """``DeliveryRecord`` 데이터를 표현한다."""
    customer_id: str
    promised_min: float
    actual_min: float
    on_time: bool = True
    damage: bool = False
    rating: int = 5


class CustomerMetrics:
    """``CustomerMetrics`` 데이터를 표현한다."""
    def __init__(self) -> None:
        """인스턴스를 초기화한다."""
        self._records: list[DeliveryRecord] = []

    def record_delivery(self, customer_id: str, promised_min: float = 30, actual_min: float = 25, damage: bool = False, rating: int = 5) -> None:
        """`delivery` 정보를 기록한다."""
        self._records.append(DeliveryRecord(
            customer_id=customer_id, promised_min=promised_min,
            actual_min=actual_min, on_time=actual_min <= promised_min,
            damage=damage, rating=rating,
        ))

    def on_time_rate(self) -> float:
        """``on_time_rate`` 동작을 수행한다."""
        if not self._records:
            return 100
        return round(sum(1 for r in self._records if r.on_time) / len(self._records) * 100, 1)

    def avg_delivery_time(self) -> float:
        """``avg_delivery_time`` 동작을 수행한다."""
        if not self._records:
            return 0
        return round(float(np.mean([r.actual_min for r in self._records])), 1)

    def customer_satisfaction(self) -> float:
        """``customer_satisfaction`` 동작을 수행한다."""
        if not self._records:
            return 5.0
        return round(float(np.mean([r.rating for r in self._records])), 2)

    def damage_rate(self) -> float:
        """``damage_rate`` 동작을 수행한다."""
        if not self._records:
            return 0
        return round(sum(1 for r in self._records if r.damage) / len(self._records) * 100, 1)

    def summary(self) -> dict[str, Any]:
        """현재 상태 요약을 반환한다."""
        return {
            "deliveries": len(self._records),
            "on_time_rate": self.on_time_rate(),
            "avg_time_min": self.avg_delivery_time(),
            "satisfaction": self.customer_satisfaction(),
            "damage_rate": self.damage_rate(),
        }
