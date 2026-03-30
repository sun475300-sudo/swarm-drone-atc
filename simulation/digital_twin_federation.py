"""
Phase 410: Digital Twin Federation for Multi-Swarm Synchronization
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import time
import json


class SyncStatus(Enum):
    IN_SYNC = "in_sync"
    SYNCING = "syncing"
    OUT_OF_SYNC = "out_of_sync"
    DISCONNECTED = "disconnected"


@dataclass
class TwinState:
    drone_id: str
    position: np.ndarray
    velocity: np.ndarray
    battery_level: float
    mission_progress: float
    timestamp: float
    sensors: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FederationMember:
    member_id: str
    twin_states: Dict[str, TwinState]
    last_sync: float
    sync_status: SyncStatus
    priority: int


class DigitalTwinFederation:
    def __init__(
        self,
        federation_id: str,
        sync_interval: float = 1.0,
        max_latency_ms: float = 100.0,
        consensus_threshold: float = 0.8,
    ):
        self.federation_id = federation_id
        self.sync_interval = sync_interval
        self.max_latency_ms = max_latency_ms
        self.consensus_threshold = consensus_threshold

        self.members: Dict[str, FederationMember] = {}
        self.global_state: Dict[str, TwinState] = {}

        self.sync_history: List[Dict] = []

        self._start_sync_loop()

    def register_member(self, member_id: str, priority: int = 5):
        member = FederationMember(
            member_id=member_id,
            twin_states={},
            last_sync=time.time(),
            sync_status=SyncStatus.IN_SYNC,
            priority=priority,
        )
        self.members[member_id] = member

    def update_twin_state(self, member_id: str, state: TwinState):
        if member_id not in self.members:
            self.register_member(member_id)

        self.members[member_id].twin_states[state.drone_id] = state
        self.members[member_id].last_sync = time.time()
        self.members[member_id].sync_status = SyncStatus.IN_SYNC

        self.global_state[state.drone_id] = state

    def synchronize(self) -> Dict[str, Any]:
        sync_result = {
            "timestamp": time.time(),
            "members_synced": 0,
            "conflicts_resolved": 0,
            "status": "success",
        }

        drone_ids = set()
        for member in self.members.values():
            drone_ids.update(member.twin_states.keys())

        for drone_id in drone_ids:
            states = []
            for member in self.members.values():
                if drone_id in member.twin_states:
                    states.append(member.twin_states[drone_id])

            if len(states) < 2:
                continue

            consensus_state = self._resolve_consensus(states)

            if consensus_state:
                self.global_state[drone_id] = consensus_state
                sync_result["conflicts_resolved"] += 1

        sync_result["members_synced"] = len(self.members)

        self.sync_history.append(sync_result)

        return sync_result

    def _resolve_consensus(self, states: List[TwinState]) -> Optional[TwinState]:
        if not states:
            return None

        weights = []
        for state in states:
            time_diff = time.time() - state.timestamp
            weight = 1.0 / (1.0 + time_diff)
            weights.append(weight)

        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]

        positions = np.array([s.position for s in states])
        avg_position = np.average(positions, axis=0, weights=weights)

        velocities = np.array([s.velocity for s in states])
        avg_velocity = np.average(velocities, axis=0, weights=weights)

        avg_battery = sum(s.battery_level * w for s, w in zip(states, weights))
        avg_progress = sum(s.mission_progress * w for s, w in zip(states, weights))

        latest_state = max(states, key=lambda s: s.timestamp)

        return TwinState(
            drone_id=latest_state.drone_id,
            position=avg_position,
            velocity=avg_velocity,
            battery_level=avg_battery,
            mission_progress=avg_progress,
            timestamp=time.time(),
            sensors=latest_state.sensors,
        )

    def _start_sync_loop(self):
        pass

    def get_federation_status(self) -> Dict[str, Any]:
        return {
            "federation_id": self.federation_id,
            "total_members": len(self.members),
            "total_drones": len(self.global_state),
            "sync_interval": self.sync_interval,
            "members": {
                member_id: {
                    "priority": m.priority,
                    "last_sync": m.last_sync,
                    "status": m.sync_status.value,
                    "drones_count": len(m.twin_states),
                }
                for member_id, m in self.members.items()
            },
        }

    def query_twin(self, drone_id: str) -> Optional[TwinState]:
        return self.global_state.get(drone_id)

    def get_all_twins(self) -> Dict[str, TwinState]:
        return self.global_state.copy()

    def export_state(self) -> str:
        data = {
            "federation_id": self.federation_id,
            "timestamp": time.time(),
            "global_state": {
                drone_id: {
                    "position": state.position.tolist()
                    if isinstance(state.position, np.ndarray)
                    else list(state.position),
                    "velocity": state.velocity.tolist()
                    if isinstance(state.velocity, np.ndarray)
                    else list(state.velocity),
                    "battery_level": state.battery_level,
                    "mission_progress": state.mission_progress,
                    "timestamp": state.timestamp,
                }
                for drone_id, state in self.global_state.items()
            },
        }
        return json.dumps(data, indent=2)

    def detect_anomalies(self) -> List[Dict]:
        anomalies = []

        for drone_id, state in self.global_state.items():
            if state.battery_level < 0.1:
                anomalies.append(
                    {
                        "drone_id": drone_id,
                        "type": "low_battery",
                        "severity": "critical",
                        "value": state.battery_level,
                    }
                )

            speed = np.linalg.norm(state.velocity)
            if speed > 50.0:
                anomalies.append(
                    {
                        "drone_id": drone_id,
                        "type": "high_velocity",
                        "severity": "warning",
                        "value": speed,
                    }
                )

            if state.mission_progress < 0.01 and time.time() - state.timestamp > 60:
                anomalies.append(
                    {
                        "drone_id": drone_id,
                        "type": "stagnant",
                        "severity": "warning",
                    }
                )

        return anomalies
