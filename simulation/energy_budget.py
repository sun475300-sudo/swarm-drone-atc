"""
에너지 예산 관리
================
임무별 에너지 할당 + 소비 추적 + 예산 경고.

사용법:
    eb = EnergyBudget()
    eb.allocate("d1", total_wh=80, reserve_pct=20)
    eb.consume("d1", wh=5.0)
    ok = eb.check_budget("d1")
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class EnergyAccount:
    """에너지 계정"""
    drone_id: str
    total_wh: float
    consumed_wh: float = 0.0
    reserve_pct: float = 20.0
    mission_id: str = ""

    @property
    def remaining_wh(self) -> float:
        return max(0, self.total_wh - self.consumed_wh)

    @property
    def usage_pct(self) -> float:
        return (self.consumed_wh / max(self.total_wh, 0.01)) * 100

    @property
    def reserve_wh(self) -> float:
        return self.total_wh * self.reserve_pct / 100

    @property
    def available_wh(self) -> float:
        """예비 제외 사용 가능 에너지"""
        return max(0, self.remaining_wh - self.reserve_wh)

    @property
    def is_critical(self) -> bool:
        return self.remaining_wh <= self.reserve_wh


class EnergyBudget:
    """에너지 예산 관리."""

    def __init__(self) -> None:
        self._accounts: dict[str, EnergyAccount] = {}
        self._warnings: list[dict[str, Any]] = []

    def allocate(
        self,
        drone_id: str,
        total_wh: float = 80.0,
        reserve_pct: float = 20.0,
        mission_id: str = "",
    ) -> EnergyAccount:
        account = EnergyAccount(
            drone_id=drone_id,
            total_wh=total_wh,
            reserve_pct=reserve_pct,
            mission_id=mission_id,
        )
        self._accounts[drone_id] = account
        return account

    def consume(self, drone_id: str, wh: float) -> bool:
        account = self._accounts.get(drone_id)
        if not account:
            return False
        account.consumed_wh += wh

        if account.is_critical:
            self._warnings.append({
                "drone_id": drone_id,
                "type": "CRITICAL",
                "remaining_wh": account.remaining_wh,
                "reserve_wh": account.reserve_wh,
            })

        return True

    def check_budget(self, drone_id: str) -> bool:
        """예산 내 여부 (예비 에너지 미침범)"""
        account = self._accounts.get(drone_id)
        if not account:
            return False
        return not account.is_critical

    def can_complete_mission(
        self, drone_id: str, estimated_wh: float,
    ) -> bool:
        """임무 완료 가능 여부"""
        account = self._accounts.get(drone_id)
        if not account:
            return False
        return account.available_wh >= estimated_wh

    def get_account(self, drone_id: str) -> EnergyAccount | None:
        return self._accounts.get(drone_id)

    def fleet_efficiency(self) -> float:
        """함대 에너지 효율 (사용률)"""
        if not self._accounts:
            return 0.0
        usages = [a.usage_pct for a in self._accounts.values()]
        return sum(usages) / len(usages)

    def critical_drones(self) -> list[str]:
        return [did for did, a in self._accounts.items() if a.is_critical]

    def recharge(self, drone_id: str, wh: float) -> bool:
        account = self._accounts.get(drone_id)
        if not account:
            return False
        account.consumed_wh = max(0, account.consumed_wh - wh)
        return True

    def warnings(self) -> list[dict[str, Any]]:
        return list(self._warnings)

    def summary(self) -> dict[str, Any]:
        total_alloc = sum(a.total_wh for a in self._accounts.values())
        total_consumed = sum(a.consumed_wh for a in self._accounts.values())
        return {
            "total_drones": len(self._accounts),
            "total_allocated_wh": round(total_alloc, 1),
            "total_consumed_wh": round(total_consumed, 1),
            "fleet_efficiency": round(self.fleet_efficiency(), 1),
            "critical_count": len(self.critical_drones()),
            "warnings": len(self._warnings),
        }
