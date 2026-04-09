"""
SLA 계약 엔진
=============
서비스 등급별 보장 + 위약금 계산 + 보고서.

사용법:
    sla = SLAContract()
    sla.add_contract("c1", tier="GOLD", max_latency_s=2.0, uptime_pct=99.9)
    sla.record_performance("c1", latency_s=1.5, available=True)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import numpy as np


@dataclass
class Contract:
    contract_id: str
    tier: str
    max_latency_s: float
    uptime_pct: float
    penalty_per_violation: float = 1000.0
    records: list[dict] = field(default_factory=list)


class SLAContract:
    def __init__(self) -> None:
        self._contracts: dict[str, Contract] = {}

    def add_contract(self, contract_id: str, tier: str = "SILVER", max_latency_s: float = 5.0, uptime_pct: float = 99.0, penalty: float = 1000) -> None:
        self._contracts[contract_id] = Contract(contract_id=contract_id, tier=tier, max_latency_s=max_latency_s, uptime_pct=uptime_pct, penalty_per_violation=penalty)

    def record_performance(self, contract_id: str, latency_s: float = 0, available: bool = True) -> None:
        c = self._contracts.get(contract_id)
        if c:
            c.records.append({"latency": latency_s, "available": available})

    def compliance(self, contract_id: str) -> dict[str, Any]:
        c = self._contracts.get(contract_id)
        if not c or not c.records:
            return {"compliant": True, "uptime": 100, "avg_latency": 0}
        uptime = sum(1 for r in c.records if r["available"]) / len(c.records) * 100
        avg_lat = float(np.mean([r["latency"] for r in c.records]))
        violations = sum(1 for r in c.records if r["latency"] > c.max_latency_s or not r["available"])
        return {
            "compliant": uptime >= c.uptime_pct and avg_lat <= c.max_latency_s,
            "uptime": round(uptime, 2),
            "avg_latency": round(avg_lat, 3),
            "violations": violations,
            "penalty": violations * c.penalty_per_violation,
        }

    def summary(self) -> dict[str, Any]:
        return {
            "contracts": len(self._contracts),
            "compliant": sum(1 for cid in self._contracts if self.compliance(cid).get("compliant", True)),
        }
