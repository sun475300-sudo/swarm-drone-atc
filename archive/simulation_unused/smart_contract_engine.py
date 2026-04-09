"""
Phase 412: Smart Contract Engine
Advanced smart contract execution for drone swarm operations.
"""

import hashlib
import json
import time
import numpy as np
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Any, Callable


class ContractState(Enum):
    """Smart contract lifecycle states."""

    CREATED = auto()
    DEPLOYED = auto()
    ACTIVE = auto()
    PAUSED = auto()
    COMPLETED = auto()
    TERMINATED = auto()


class EventType(Enum):
    """Contract event types."""

    FLIGHT_START = auto()
    FLIGHT_END = auto()
    COLLISION_DETECTED = auto()
    AIRSPACE_ENTER = auto()
    AIRSPACE_EXIT = auto()
    BATTERY_LOW = auto()
    EMERGENCY_LANDING = auto()
    MISSION_COMPLETE = auto()


@dataclass
class ContractEvent:
    """Smart contract event."""

    event_type: EventType
    timestamp: float
    drone_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    block_index: int = 0


@dataclass
class ContractCondition:
    """Contract execution condition."""

    field_name: str
    operator: str
    value: Any
    action: str = "trigger"


@dataclass
class ContractRule:
    """Contract rule definition."""

    rule_id: str
    conditions: List[ContractCondition]
    actions: List[Dict[str, Any]]
    priority: int = 0
    is_active: bool = True


@dataclass
class ContractExecution:
    """Contract execution record."""

    execution_id: str
    contract_id: str
    timestamp: float
    input_params: Dict[str, Any]
    output_result: Dict[str, Any]
    gas_used: float = 0.0
    success: bool = True


class SmartContractVM:
    """Smart contract virtual machine."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.contracts: Dict[str, Dict[str, Any]] = {}
        self.execution_history: List[ContractExecution] = []
        self.event_listeners: Dict[EventType, List[Callable]] = defaultdict(list)
        self.gas_limit = 1000000

    def deploy_contract(
        self, contract_id: str, code: Dict[str, Any], owner: str
    ) -> bool:
        self.contracts[contract_id] = {
            "code": code,
            "owner": owner,
            "state": ContractState.DEPLOYED,
            "storage": {},
            "created_at": time.time(),
            "executions": 0,
        }
        return True

    def execute_contract(
        self, contract_id: str, function: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        if contract_id not in self.contracts:
            return {"success": False, "error": "Contract not found"}
        contract = self.contracts[contract_id]
        if contract["state"] not in [ContractState.DEPLOYED, ContractState.ACTIVE]:
            return {"success": False, "error": "Contract not active"}
        gas_used = self.rng.uniform(100, 10000)
        result = self._execute_function(contract, function, params)
        execution = ContractExecution(
            execution_id=hashlib.sha256(
                f"{contract_id}{function}{time.time()}".encode()
            ).hexdigest()[:16],
            contract_id=contract_id,
            timestamp=time.time(),
            input_params=params,
            output_result=result,
            gas_used=gas_used,
            success=result.get("success", True),
        )
        self.execution_history.append(execution)
        contract["executions"] += 1
        return result

    def _execute_function(
        self, contract: Dict[str, Any], function: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        code = contract["code"]
        storage = contract["storage"]
        if function == "verify_flight":
            return self._verify_flight(code, storage, params)
        elif function == "check_airspace":
            return self._check_airspace(code, storage, params)
        elif function == "validate_mission":
            return self._validate_mission(code, storage, params)
        elif function == "process_payment":
            return self._process_payment(code, storage, params)
        elif function == "register_drone":
            return self._register_drone(code, storage, params)
        return {"success": False, "error": f"Unknown function: {function}"}

    def _verify_flight(self, code: Dict, storage: Dict, params: Dict) -> Dict[str, Any]:
        drone_id = params.get("drone_id", "")
        position = params.get("position", [0, 0, 0])
        altitude = params.get("altitude", 0)
        if altitude < 0 or altitude > 500:
            return {"success": False, "reason": "Altitude out of bounds"}
        if "flights" not in storage:
            storage["flights"] = []
        storage["flights"].append(
            {
                "drone_id": drone_id,
                "position": position,
                "altitude": altitude,
                "timestamp": time.time(),
            }
        )
        return {"success": True, "verified": True}

    def _check_airspace(
        self, code: Dict, storage: Dict, params: Dict
    ) -> Dict[str, Any]:
        position = params.get("position", [0, 0, 0])
        no_fly_zones = code.get("no_fly_zones", [])
        for zone in no_fly_zones:
            center = zone.get("center", [0, 0, 0])
            radius = zone.get("radius", 100)
            dist = np.linalg.norm(np.array(position) - np.array(center))
            if dist < radius:
                return {
                    "success": False,
                    "reason": "In no-fly zone",
                    "zone": zone.get("name", "unknown"),
                }
        return {"success": True, "clear": True}

    def _validate_mission(
        self, code: Dict, storage: Dict, params: Dict
    ) -> Dict[str, Any]:
        mission_type = params.get("type", "")
        waypoints = params.get("waypoints", [])
        if not waypoints:
            return {"success": False, "reason": "No waypoints"}
        if len(waypoints) > code.get("max_waypoints", 100):
            return {"success": False, "reason": "Too many waypoints"}
        return {"success": True, "validated": True, "waypoints": len(waypoints)}

    def _process_payment(
        self, code: Dict, storage: Dict, params: Dict
    ) -> Dict[str, Any]:
        sender = params.get("sender", "")
        receiver = params.get("receiver", "")
        amount = params.get("amount", 0.0)
        if "balances" not in storage:
            storage["balances"] = {}
        if sender not in storage["balances"]:
            storage["balances"][sender] = code.get("initial_balance", 1000)
        if storage["balances"][sender] < amount:
            return {"success": False, "reason": "Insufficient balance"}
        storage["balances"][sender] -= amount
        storage["balances"][receiver] = storage["balances"].get(receiver, 0) + amount
        return {"success": True, "paid": amount}

    def _register_drone(
        self, code: Dict, storage: Dict, params: Dict
    ) -> Dict[str, Any]:
        drone_id = params.get("drone_id", "")
        owner = params.get("owner", "")
        if "drones" not in storage:
            storage["drones"] = {}
        if drone_id in storage["drones"]:
            return {"success": False, "reason": "Drone already registered"}
        storage["drones"][drone_id] = {
            "owner": owner,
            "registered_at": time.time(),
            "status": "active",
        }
        return {"success": True, "registered": drone_id}

    def register_event_listener(
        self, event_type: EventType, callback: Callable
    ) -> None:
        self.event_listeners[event_type].append(callback)

    def emit_event(self, event: ContractEvent) -> None:
        for callback in self.event_listeners.get(event.event_type, []):
            callback(event)

    def get_contract_state(self, contract_id: str) -> Dict[str, Any]:
        if contract_id not in self.contracts:
            return {}
        contract = self.contracts[contract_id]
        return {
            "state": contract["state"].name,
            "executions": contract["executions"],
            "storage_keys": list(contract["storage"].keys()),
        }


class DroneSmartContractManager:
    """Manager for drone-specific smart contracts."""

    def __init__(self, seed: int = 42):
        self.vm = SmartContractVM(seed)
        self.active_contracts: Dict[str, str] = {}

    def create_flight_verification_contract(
        self, owner: str, max_altitude: float = 500
    ) -> str:
        contract_id = hashlib.sha256(
            f"flight_verify_{owner}_{time.time()}".encode()
        ).hexdigest()[:16]
        code = {
            "type": "flight_verification",
            "max_altitude": max_altitude,
            "owner": owner,
        }
        self.vm.deploy_contract(contract_id, code, owner)
        self.active_contracts["flight_verification"] = contract_id
        return contract_id

    def create_airspace_contract(self, owner: str, no_fly_zones: List[Dict]) -> str:
        contract_id = hashlib.sha256(
            f"airspace_{owner}_{time.time()}".encode()
        ).hexdigest()[:16]
        code = {
            "type": "airspace_management",
            "no_fly_zones": no_fly_zones,
            "owner": owner,
        }
        self.vm.deploy_contract(contract_id, code, owner)
        self.active_contracts["airspace"] = contract_id
        return contract_id

    def create_mission_contract(self, owner: str, max_waypoints: int = 100) -> str:
        contract_id = hashlib.sha256(
            f"mission_{owner}_{time.time()}".encode()
        ).hexdigest()[:16]
        code = {
            "type": "mission_management",
            "max_waypoints": max_waypoints,
            "owner": owner,
        }
        self.vm.deploy_contract(contract_id, code, owner)
        self.active_contracts["mission"] = contract_id
        return contract_id

    def verify_flight(
        self, drone_id: str, position: List[float], altitude: float
    ) -> Dict[str, Any]:
        contract_id = self.active_contracts.get("flight_verification")
        if not contract_id:
            return {"success": False, "error": "No flight contract"}
        return self.vm.execute_contract(
            contract_id,
            "verify_flight",
            {"drone_id": drone_id, "position": position, "altitude": altitude},
        )

    def check_airspace(self, position: List[float]) -> Dict[str, Any]:
        contract_id = self.active_contracts.get("airspace")
        if not contract_id:
            return {"success": False, "error": "No airspace contract"}
        return self.vm.execute_contract(
            contract_id, "check_airspace", {"position": position}
        )

    def validate_mission(
        self, mission_type: str, waypoints: List[List[float]]
    ) -> Dict[str, Any]:
        contract_id = self.active_contracts.get("mission")
        if not contract_id:
            return {"success": False, "error": "No mission contract"}
        return self.vm.execute_contract(
            contract_id,
            "validate_mission",
            {"type": mission_type, "waypoints": waypoints},
        )

    def get_execution_history(self) -> List[ContractExecution]:
        return self.vm.execution_history


if __name__ == "__main__":
    manager = DroneSmartContractManager(seed=42)
    manager.create_flight_verification_contract("admin", max_altitude=500)
    manager.create_airspace_contract(
        "admin", [{"name": "Airport", "center": [0, 0, 0], "radius": 5000}]
    )
    result = manager.verify_flight("D001", [100, 200, 50], 50)
    print(f"Flight verification: {result}")
    result = manager.check_airspace([100, 200, 50])
    print(f"Airspace check: {result}")
