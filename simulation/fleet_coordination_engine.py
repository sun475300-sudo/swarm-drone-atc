"""Phase 285: Fleet Coordination Engine — 함대 조율 엔진.

다중 군집 간 조율, 공역 분할, 우선순위 기반 충돌 해결,
실시간 함대 상태 모니터링 및 자원 공유를 구현합니다.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


class FleetStatus(Enum):
    ACTIVE = "active"
    STANDBY = "standby"
    DEPLOYING = "deploying"
    RETURNING = "returning"
    MAINTENANCE = "maintenance"


class CoordinationMode(Enum):
    CENTRALIZED = "centralized"
    DISTRIBUTED = "distributed"
    HIERARCHICAL = "hierarchical"


@dataclass
class Fleet:
    fleet_id: str
    drone_ids: List[str] = field(default_factory=list)
    status: FleetStatus = FleetStatus.STANDBY
    assigned_zone: Optional[str] = None
    priority: int = 5
    leader_id: Optional[str] = None
    max_size: int = 50


@dataclass
class AirspaceZone:
    zone_id: str
    center: np.ndarray
    radius: float
    altitude_range: Tuple[float, float] = (0.0, 200.0)
    assigned_fleet: Optional[str] = None
    capacity: int = 50


@dataclass
class CoordinationMessage:
    sender_fleet: str
    receiver_fleet: str
    msg_type: str  # "handoff", "resource_request", "conflict_notify", "status_update"
    payload: dict = field(default_factory=dict)
    timestamp: float = 0.0


class FleetCoordinationEngine:
    """함대 조율 엔진.

    - 다중 군집 관리 및 공역 할당
    - 군집 간 드론 핸드오프
    - 우선순위 기반 공역 충돌 해결
    - 자원 공유 프로토콜
    """

    def __init__(self, mode: CoordinationMode = CoordinationMode.HIERARCHICAL, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self.mode = mode
        self._fleets: Dict[str, Fleet] = {}
        self._zones: Dict[str, AirspaceZone] = {}
        self._messages: List[CoordinationMessage] = []
        self._handoff_history: List[dict] = []
        self._drone_fleet_map: Dict[str, str] = {}  # drone_id -> fleet_id

    def register_fleet(self, fleet: Fleet):
        self._fleets[fleet.fleet_id] = fleet
        for did in fleet.drone_ids:
            self._drone_fleet_map[did] = fleet.fleet_id

    def register_zone(self, zone: AirspaceZone):
        self._zones[zone.zone_id] = zone

    def assign_zone(self, fleet_id: str, zone_id: str) -> bool:
        fleet = self._fleets.get(fleet_id)
        zone = self._zones.get(zone_id)
        if not fleet or not zone:
            return False
        if zone.assigned_fleet and zone.assigned_fleet != fleet_id:
            # Conflict resolution by priority
            other = self._fleets.get(zone.assigned_fleet)
            if other and other.priority >= fleet.priority:
                return False
        zone.assigned_fleet = fleet_id
        fleet.assigned_zone = zone_id
        fleet.status = FleetStatus.ACTIVE
        return True

    def handoff_drone(self, drone_id: str, from_fleet: str, to_fleet: str) -> bool:
        src = self._fleets.get(from_fleet)
        dst = self._fleets.get(to_fleet)
        if not src or not dst:
            return False
        if drone_id not in src.drone_ids:
            return False
        if len(dst.drone_ids) >= dst.max_size:
            return False
        src.drone_ids.remove(drone_id)
        dst.drone_ids.append(drone_id)
        self._drone_fleet_map[drone_id] = to_fleet
        self._handoff_history.append({"drone": drone_id, "from": from_fleet, "to": to_fleet})
        self._messages.append(CoordinationMessage(
            sender_fleet=from_fleet, receiver_fleet=to_fleet,
            msg_type="handoff", payload={"drone_id": drone_id},
        ))
        return True

    def request_support(self, requester_fleet: str, n_drones: int) -> List[str]:
        requester = self._fleets.get(requester_fleet)
        if not requester:
            return []
        transferred = []
        for fid, fleet in self._fleets.items():
            if fid == requester_fleet:
                continue
            if fleet.status != FleetStatus.ACTIVE:
                continue
            available = len(fleet.drone_ids) - 5  # keep minimum 5
            if available <= 0:
                continue
            to_transfer = min(available, n_drones - len(transferred))
            for _ in range(to_transfer):
                did = fleet.drone_ids[-1]
                if self.handoff_drone(did, fid, requester_fleet):
                    transferred.append(did)
            if len(transferred) >= n_drones:
                break
        return transferred

    def resolve_zone_conflicts(self) -> List[dict]:
        """공역 할당 충돌 해결."""
        conflicts = []
        zone_claims: Dict[str, List[str]] = {}
        for fid, fleet in self._fleets.items():
            if fleet.assigned_zone:
                zone_claims.setdefault(fleet.assigned_zone, []).append(fid)
        for zid, fleets in zone_claims.items():
            if len(fleets) > 1:
                # Highest priority wins
                fleets.sort(key=lambda f: self._fleets[f].priority, reverse=True)
                winner = fleets[0]
                for loser in fleets[1:]:
                    self._fleets[loser].assigned_zone = None
                    self._fleets[loser].status = FleetStatus.STANDBY
                    conflicts.append({"zone": zid, "winner": winner, "displaced": loser})
        return conflicts

    def get_fleet(self, fleet_id: str) -> Optional[Fleet]:
        return self._fleets.get(fleet_id)

    def get_drone_fleet(self, drone_id: str) -> Optional[str]:
        return self._drone_fleet_map.get(drone_id)

    def get_fleet_positions(self, fleet_id: str, positions: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        fleet = self._fleets.get(fleet_id)
        if not fleet:
            return {}
        return {did: positions[did] for did in fleet.drone_ids if did in positions}

    def summary(self) -> dict:
        active = sum(1 for f in self._fleets.values() if f.status == FleetStatus.ACTIVE)
        total_drones = sum(len(f.drone_ids) for f in self._fleets.values())
        return {
            "total_fleets": len(self._fleets),
            "active_fleets": active,
            "total_drones": total_drones,
            "total_zones": len(self._zones),
            "handoffs": len(self._handoff_history),
            "messages": len(self._messages),
        }
