"""
멀티 테넌트 관제
===============
운영자별 격리 + 공유 공역 조율.

사용법:
    mt = MultiTenant()
    mt.add_tenant("op1", name="쿠팡", max_drones=100)
    mt.assign_drone("d1", "op1")
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Tenant:
    tenant_id: str
    name: str
    max_drones: int = 100
    drones: list[str] = field(default_factory=list)
    priority: int = 5
    airspace_quota_pct: float = 0.0


class MultiTenant:
    def __init__(self) -> None:
        self._tenants: dict[str, Tenant] = {}
        self._drone_tenant: dict[str, str] = {}

    def add_tenant(self, tenant_id: str, name: str = "", max_drones: int = 100, priority: int = 5) -> None:
        self._tenants[tenant_id] = Tenant(tenant_id=tenant_id, name=name, max_drones=max_drones, priority=priority)

    def assign_drone(self, drone_id: str, tenant_id: str) -> bool:
        t = self._tenants.get(tenant_id)
        if not t or len(t.drones) >= t.max_drones:
            return False
        t.drones.append(drone_id)
        self._drone_tenant[drone_id] = tenant_id
        return True

    def get_tenant(self, drone_id: str) -> str | None:
        return self._drone_tenant.get(drone_id)

    def tenant_drones(self, tenant_id: str) -> list[str]:
        t = self._tenants.get(tenant_id)
        return list(t.drones) if t else []

    def allocate_quota(self) -> None:
        total = sum(len(t.drones) for t in self._tenants.values())
        for t in self._tenants.values():
            t.airspace_quota_pct = round(len(t.drones) / max(total, 1) * 100, 1)

    def summary(self) -> dict[str, Any]:
        self.allocate_quota()
        return {
            "tenants": len(self._tenants),
            "total_drones": len(self._drone_tenant),
            "quotas": {t.name or t.tenant_id: t.airspace_quota_pct for t in self._tenants.values()},
        }
