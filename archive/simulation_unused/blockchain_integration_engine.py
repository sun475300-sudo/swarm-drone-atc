"""
Phase 411: Blockchain Integration Engine
Blockchain integration for drone swarm: smart contracts, distributed ledger, consensus.
"""

import hashlib
import json
import time
import numpy as np
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Any, Callable
from collections import defaultdict


class BlockStatus(Enum):
    """Block status."""

    PENDING = auto()
    CONFIRMED = auto()
    REJECTED = auto()
    ORPHANED = auto()


class ConsensusType(Enum):
    """Consensus mechanism types."""

    POW = auto()  # Proof of Work
    POS = auto()  # Proof of Stake
    PBFT = auto()  # Practical Byzantine Fault Tolerance
    RAFT = auto()  # Raft
    DAG = auto()  # Directed Acyclic Graph


class ContractType(Enum):
    """Smart contract types."""

    FLIGHT_LOG = auto()
    AIRSPACE_RESERVATION = auto()
    DRONE_REGISTRATION = auto()
    COLLISION_REPORT = auto()
    MISSION_ASSIGNMENT = auto()
    PAYMENT = auto()


@dataclass
class Transaction:
    """Blockchain transaction."""

    tx_id: str
    sender: str
    receiver: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    signature: str = ""
    fee: float = 0.0

    def compute_hash(self) -> str:
        content = json.dumps(
            {
                "tx_id": self.tx_id,
                "sender": self.sender,
                "receiver": self.receiver,
                "data": self.data,
                "timestamp": self.timestamp,
                "fee": self.fee,
            },
            sort_keys=True,
        )
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class Block:
    """Blockchain block."""

    index: int
    timestamp: float
    transactions: List[Transaction]
    previous_hash: str
    nonce: int = 0
    hash: str = ""
    merkle_root: str = ""
    validator: str = ""
    status: BlockStatus = BlockStatus.PENDING

    def compute_merkle_root(self) -> str:
        if not self.transactions:
            return hashlib.sha256(b"empty").hexdigest()
        hashes = [tx.compute_hash() for tx in self.transactions]
        while len(hashes) > 1:
            if len(hashes) % 2 != 0:
                hashes.append(hashes[-1])
            new_hashes = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i + 1]
                new_hashes.append(hashlib.sha256(combined.encode()).hexdigest())
            hashes = new_hashes
        return hashes[0]

    def compute_hash(self) -> str:
        content = json.dumps(
            {
                "index": self.index,
                "timestamp": self.timestamp,
                "merkle_root": self.merkle_root,
                "previous_hash": self.previous_hash,
                "nonce": self.nonce,
                "validator": self.validator,
            },
            sort_keys=True,
        )
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class SmartContract:
    """Smart contract definition."""

    contract_id: str
    contract_type: ContractType
    owner: str
    code: Dict[str, Any]
    state: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    is_active: bool = True

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        result = {"success": True, "data": {}}
        if self.contract_type == ContractType.FLIGHT_LOG:
            result["data"] = self._execute_flight_log(params)
        elif self.contract_type == ContractType.AIRSPACE_RESERVATION:
            result["data"] = self._execute_airspace_reservation(params)
        elif self.contract_type == ContractType.DRONE_REGISTRATION:
            result["data"] = self._execute_drone_registration(params)
        elif self.contract_type == ContractType.COLLISION_REPORT:
            result["data"] = self._execute_collision_report(params)
        elif self.contract_type == ContractType.MISSION_ASSIGNMENT:
            result["data"] = self._execute_mission_assignment(params)
        elif self.contract_type == ContractType.PAYMENT:
            result["data"] = self._execute_payment(params)
        return result

    def _execute_flight_log(self, params: Dict[str, Any]) -> Dict[str, Any]:
        log_entry = {
            "drone_id": params.get("drone_id", ""),
            "timestamp": params.get("timestamp", time.time()),
            "position": params.get("position", [0, 0, 0]),
            "altitude": params.get("altitude", 0),
            "speed": params.get("speed", 0),
            "battery": params.get("battery", 100),
        }
        if "flight_logs" not in self.state:
            self.state["flight_logs"] = []
        self.state["flight_logs"].append(log_entry)
        return {"logged": True, "entry": log_entry}

    def _execute_airspace_reservation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        zone_id = params.get("zone_id", "")
        drone_id = params.get("drone_id", "")
        start_time = params.get("start_time", time.time())
        end_time = params.get("end_time", time.time() + 3600)
        if "reservations" not in self.state:
            self.state["reservations"] = {}
        if zone_id not in self.state["reservations"]:
            self.state["reservations"][zone_id] = []
        reservation = {
            "drone_id": drone_id,
            "start_time": start_time,
            "end_time": end_time,
            "status": "confirmed",
        }
        self.state["reservations"][zone_id].append(reservation)
        return {"reserved": True, "zone_id": zone_id, "reservation": reservation}

    def _execute_drone_registration(self, params: Dict[str, Any]) -> Dict[str, Any]:
        drone_id = params.get("drone_id", "")
        owner = params.get("owner", "")
        specs = params.get("specs", {})
        if "drones" not in self.state:
            self.state["drones"] = {}
        self.state["drones"][drone_id] = {
            "owner": owner,
            "specs": specs,
            "registered_at": time.time(),
            "status": "active",
        }
        return {"registered": True, "drone_id": drone_id}

    def _execute_collision_report(self, params: Dict[str, Any]) -> Dict[str, Any]:
        report = {
            "report_id": params.get("report_id", ""),
            "drone1": params.get("drone1", ""),
            "drone2": params.get("drone2", ""),
            "position": params.get("position", [0, 0, 0]),
            "timestamp": params.get("timestamp", time.time()),
            "severity": params.get("severity", "low"),
        }
        if "collision_reports" not in self.state:
            self.state["collision_reports"] = []
        self.state["collision_reports"].append(report)
        return {"reported": True, "report": report}

    def _execute_mission_assignment(self, params: Dict[str, Any]) -> Dict[str, Any]:
        mission = {
            "mission_id": params.get("mission_id", ""),
            "drone_id": params.get("drone_id", ""),
            "type": params.get("type", "delivery"),
            "waypoints": params.get("waypoints", []),
            "priority": params.get("priority", 1),
            "status": "assigned",
        }
        if "missions" not in self.state:
            self.state["missions"] = []
        self.state["missions"].append(mission)
        return {"assigned": True, "mission": mission}

    def _execute_payment(self, params: Dict[str, Any]) -> Dict[str, Any]:
        sender = params.get("sender", "")
        receiver = params.get("receiver", "")
        amount = params.get("amount", 0.0)
        if "balances" not in self.state:
            self.state["balances"] = {}
        if sender not in self.state["balances"]:
            self.state["balances"][sender] = 1000.0
        if receiver not in self.state["balances"]:
            self.state["balances"][receiver] = 1000.0
        if self.state["balances"][sender] >= amount:
            self.state["balances"][sender] -= amount
            self.state["balances"][receiver] += amount
            return {"paid": True, "amount": amount}
        return {"paid": False, "reason": "insufficient balance"}


class BlockchainEngine:
    """Blockchain engine for drone swarm management."""

    def __init__(
        self,
        consensus: ConsensusType = ConsensusType.PBFT,
        difficulty: int = 2,
        seed: int = 42,
    ):
        self.consensus = consensus
        self.difficulty = difficulty
        self.rng = np.random.default_rng(seed)
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []
        self.contracts: Dict[str, SmartContract] = {}
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self._create_genesis_block()

    def _create_genesis_block(self) -> None:
        genesis = Block(
            index=0,
            timestamp=time.time(),
            transactions=[],
            previous_hash="0" * 64,
            validator="genesis",
        )
        genesis.merkle_root = genesis.compute_merkle_root()
        genesis.hash = genesis.compute_hash()
        genesis.status = BlockStatus.CONFIRMED
        self.chain.append(genesis)

    def register_node(self, node_id: str, stake: float = 0.0) -> None:
        self.nodes[node_id] = {
            "stake": stake,
            "reputation": 1.0,
            "blocks_validated": 0,
            "registered_at": time.time(),
        }

    def add_transaction(self, tx: Transaction) -> str:
        self.pending_transactions.append(tx)
        return tx.tx_id

    def create_contract(
        self, contract_type: ContractType, owner: str, code: Dict[str, Any]
    ) -> SmartContract:
        contract_id = hashlib.sha256(
            f"{contract_type.name}{owner}{time.time()}".encode()
        ).hexdigest()[:16]
        contract = SmartContract(contract_id, contract_type, owner, code)
        self.contracts[contract_id] = contract
        return contract

    def execute_contract(
        self, contract_id: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        if contract_id not in self.contracts:
            return {"success": False, "error": "Contract not found"}
        contract = self.contracts[contract_id]
        result = contract.execute(params)
        tx = Transaction(
            tx_id=hashlib.sha256(
                f"contract_{contract_id}_{time.time()}".encode()
            ).hexdigest()[:16],
            sender=params.get("sender", "system"),
            receiver=contract_id,
            data={"type": "contract_execution", "result": result},
        )
        self.add_transaction(tx)
        return result

    def mine_block(self, validator: Optional[str] = None) -> Optional[Block]:
        if not self.pending_transactions:
            return None
        if validator is None:
            validator = self._select_validator()
        new_block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            transactions=self.pending_transactions[:10],
            previous_hash=self.chain[-1].hash,
            validator=validator,
        )
        new_block.merkle_root = new_block.compute_merkle_root()
        if self.consensus == ConsensusType.POW:
            new_block = self._proof_of_work(new_block)
        elif self.consensus == ConsensusType.PBFT:
            new_block = self._pbft_consensus(new_block)
        new_block.hash = new_block.compute_hash()
        new_block.status = BlockStatus.CONFIRMED
        self.chain.append(new_block)
        self.pending_transactions = self.pending_transactions[10:]
        if validator in self.nodes:
            self.nodes[validator]["blocks_validated"] += 1
        return new_block

    def _select_validator(self) -> str:
        if not self.nodes:
            return "default_validator"
        if self.consensus == ConsensusType.POS:
            total_stake = sum(n["stake"] for n in self.nodes.values())
            if total_stake == 0:
                return list(self.nodes.keys())[0]
            r = self.rng.random() * total_stake
            cumulative = 0
            for node_id, info in self.nodes.items():
                cumulative += info["stake"]
                if r <= cumulative:
                    return node_id
        return list(self.nodes.keys())[0]

    def _proof_of_work(self, block: Block) -> Block:
        target = "0" * self.difficulty
        while not block.compute_hash().startswith(target):
            block.nonce += 1
        return block

    def _pbft_consensus(self, block: Block) -> Block:
        n_nodes = len(self.nodes)
        if n_nodes < 4:
            return block
        votes = 0
        for node_id in self.nodes:
            if self.rng.random() < self.nodes[node_id]["reputation"]:
                votes += 1
        if votes >= (2 * n_nodes) // 3 + 1:
            return block
        block.status = BlockStatus.REJECTED
        return block

    def validate_chain(self) -> bool:
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]
            if current.previous_hash != previous.hash:
                return False
            if current.compute_hash() != current.hash:
                return False
        return True

    def get_chain_state(self) -> Dict[str, Any]:
        return {
            "length": len(self.chain),
            "pending_transactions": len(self.pending_transactions),
            "contracts": len(self.contracts),
            "nodes": len(self.nodes),
            "is_valid": self.validate_chain(),
        }

    def get_drone_flights(self, drone_id: str) -> List[Dict[str, Any]]:
        flights = []
        for contract in self.contracts.values():
            if contract.contract_type == ContractType.FLIGHT_LOG:
                for log in contract.state.get("flight_logs", []):
                    if log.get("drone_id") == drone_id:
                        flights.append(log)
        return flights

    def get_airspace_reservations(self, zone_id: str) -> List[Dict[str, Any]]:
        for contract in self.contracts.values():
            if contract.contract_type == ContractType.AIRSPACE_RESERVATION:
                return contract.state.get("reservations", {}).get(zone_id, [])
        return []


class DroneBlockchainManager:
    """Blockchain manager for drone operations."""

    def __init__(self, seed: int = 42):
        self.engine = BlockchainEngine(consensus=ConsensusType.PBFT, seed=seed)
        self.flight_log_contract = None
        self.airspace_contract = None
        self._init_contracts()

    def _init_contracts(self) -> None:
        self.flight_log_contract = self.engine.create_contract(
            ContractType.FLIGHT_LOG, "system", {"version": "1.0"}
        )
        self.airspace_contract = self.engine.create_contract(
            ContractType.AIRSPACE_RESERVATION, "system", {"version": "1.0"}
        )

    def register_drone(
        self, drone_id: str, owner: str, specs: Dict[str, Any]
    ) -> Dict[str, Any]:
        contract = self.engine.create_contract(
            ContractType.DRONE_REGISTRATION, owner, {"drone_id": drone_id}
        )
        return self.engine.execute_contract(
            contract.contract_id, {"drone_id": drone_id, "owner": owner, "specs": specs}
        )

    def log_flight(
        self,
        drone_id: str,
        position: List[float],
        altitude: float,
        speed: float,
        battery: float,
    ) -> Dict[str, Any]:
        if self.flight_log_contract is None:
            return {"success": False}
        return self.engine.execute_contract(
            self.flight_log_contract.contract_id,
            {
                "drone_id": drone_id,
                "position": position,
                "altitude": altitude,
                "speed": speed,
                "battery": battery,
            },
        )

    def reserve_airspace(
        self, zone_id: str, drone_id: str, duration_hours: float = 1.0
    ) -> Dict[str, Any]:
        if self.airspace_contract is None:
            return {"success": False}
        return self.engine.execute_contract(
            self.airspace_contract.contract_id,
            {
                "zone_id": zone_id,
                "drone_id": drone_id,
                "start_time": time.time(),
                "end_time": time.time() + duration_hours * 3600,
            },
        )

    def report_collision(
        self, drone1: str, drone2: str, position: List[float], severity: str
    ) -> Dict[str, Any]:
        contract = self.engine.create_contract(
            ContractType.COLLISION_REPORT, "system", {}
        )
        return self.engine.execute_contract(
            contract.contract_id,
            {
                "drone1": drone1,
                "drone2": drone2,
                "position": position,
                "severity": severity,
            },
        )

    def get_flight_history(self, drone_id: str) -> List[Dict[str, Any]]:
        return self.engine.get_drone_flights(drone_id)

    def get_chain_status(self) -> Dict[str, Any]:
        return self.engine.get_chain_state()


if __name__ == "__main__":
    manager = DroneBlockchainManager(seed=42)
    manager.engine.register_node("drone1", stake=100)
    manager.engine.register_node("drone2", stake=200)
    manager.register_drone("D001", "owner1", {"type": "delivery", "max_speed": 20})
    manager.log_flight("D001", [100, 200, 50], 50, 15, 85)
    manager.reserve_airspace("ZONE_A", "D001", 2.0)
    block = manager.engine.mine_block()
    print(f"Chain status: {manager.get_chain_status()}")
    print(f"Flight history: {manager.get_flight_history('D001')}")
