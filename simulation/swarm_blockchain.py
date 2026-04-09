"""
Phase 510: Swarm Blockchain
분산 원장, 합의 알고리즘, 스마트 계약 기반 군집 관리.
"""

import numpy as np
import hashlib
import time as _time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Callable


class ConsensusType(Enum):
    PROOF_OF_STAKE = "pos"
    PBFT = "pbft"
    RAFT = "raft"
    PROOF_OF_AUTHORITY = "poa"


class TxType(Enum):
    REGISTRATION = "registration"
    MISSION_ASSIGN = "mission_assign"
    STATUS_UPDATE = "status_update"
    AIRSPACE_CLAIM = "airspace_claim"
    PENALTY = "penalty"
    REWARD = "reward"


@dataclass
class Transaction:
    tx_id: str
    tx_type: TxType
    sender: str
    receiver: str
    data: Dict
    timestamp: float
    signature: str = ""


@dataclass
class Block:
    index: int
    timestamp: float
    transactions: List[Transaction]
    prev_hash: str
    nonce: int = 0
    block_hash: str = ""

    def compute_hash(self) -> str:
        content = f"{self.index}{self.timestamp}{self.prev_hash}{self.nonce}"
        content += "".join(t.tx_id for t in self.transactions)
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class SmartContract:
    contract_id: str
    name: str
    conditions: Dict
    active: bool = True
    executions: int = 0


class SwarmLedger:
    """Distributed ledger for drone swarm operations."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.chain: List[Block] = []
        self.pending: List[Transaction] = []
        self._tx_counter = 0
        self._create_genesis()

    def _create_genesis(self):
        genesis = Block(0, 0.0, [], "0" * 64)
        genesis.block_hash = genesis.compute_hash()
        self.chain.append(genesis)

    def add_transaction(self, tx_type: TxType, sender: str,
                        receiver: str, data: Dict) -> Transaction:
        self._tx_counter += 1
        tx = Transaction(
            f"TX-{self._tx_counter:06d}", tx_type, sender, receiver,
            data, float(self._tx_counter),
            hashlib.sha256(f"{sender}{self._tx_counter}".encode()).hexdigest()[:16])
        self.pending.append(tx)
        return tx

    def mine_block(self) -> Optional[Block]:
        if not self.pending:
            return None
        block = Block(
            len(self.chain), float(len(self.chain)),
            self.pending[:50], self.chain[-1].block_hash)
        block.nonce = self.rng.integers(0, 1000000)
        block.block_hash = block.compute_hash()
        self.chain.append(block)
        self.pending = self.pending[50:]
        return block

    def verify_chain(self) -> bool:
        for i in range(1, len(self.chain)):
            if self.chain[i].prev_hash != self.chain[i - 1].block_hash:
                return False
            if self.chain[i].block_hash != self.chain[i].compute_hash():
                return False
        return True

    @property
    def height(self) -> int:
        return len(self.chain)


class PBFTConsensus:
    """Practical Byzantine Fault Tolerance for drone swarms."""

    def __init__(self, n_nodes: int = 10, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_nodes = n_nodes
        self.f = (n_nodes - 1) // 3  # max faulty
        self.rounds: List[Dict] = []

    def propose(self, block: Block) -> Dict:
        votes = []
        for i in range(self.n_nodes):
            honest = self.rng.random() > 0.1
            votes.append({"node": i, "vote": "commit" if honest else "reject",
                         "honest": honest})

        commits = sum(1 for v in votes if v["vote"] == "commit")
        threshold = 2 * self.f + 1
        accepted = commits >= threshold

        result = {
            "block_index": block.index,
            "commits": commits,
            "rejects": self.n_nodes - commits,
            "threshold": threshold,
            "accepted": accepted,
        }
        self.rounds.append(result)
        return result


class SmartContractEngine:
    """Execute smart contracts for swarm management."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.contracts: Dict[str, SmartContract] = {}
        self._counter = 0

    def deploy(self, name: str, conditions: Dict) -> SmartContract:
        self._counter += 1
        sc = SmartContract(f"SC-{self._counter:04d}", name, conditions)
        self.contracts[sc.contract_id] = sc
        return sc

    def execute(self, contract_id: str, context: Dict) -> Dict:
        sc = self.contracts.get(contract_id)
        if not sc or not sc.active:
            return {"executed": False, "reason": "contract not found or inactive"}

        results = {}
        for key, threshold in sc.conditions.items():
            val = context.get(key, 0)
            results[key] = {"value": val, "threshold": threshold,
                           "passed": val >= threshold if isinstance(threshold, (int, float)) else True}

        all_passed = all(r["passed"] for r in results.values())
        sc.executions += 1
        return {"executed": True, "contract": contract_id,
                "all_passed": all_passed, "checks": results}


class SwarmBlockchain:
    """Blockchain-based swarm drone management system."""

    def __init__(self, n_drones: int = 20, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.ledger = SwarmLedger(seed)
        self.consensus = PBFTConsensus(min(n_drones, 10), seed)
        self.contracts = SmartContractEngine(seed)
        self.drone_stakes: Dict[str, float] = {}

        for i in range(n_drones):
            did = f"drone_{i}"
            self.drone_stakes[did] = self.rng.uniform(10, 100)
            self.ledger.add_transaction(
                TxType.REGISTRATION, "system", did,
                {"stake": self.drone_stakes[did]})

        self.ledger.mine_block()

        self.contracts.deploy("airspace_clearance",
                             {"battery": 20, "altitude": 10, "separation": 30})
        self.contracts.deploy("mission_complete",
                             {"distance_to_target": 5, "time_remaining": 0})

    def assign_mission(self, drone_id: str, mission: Dict) -> Dict:
        tx = self.ledger.add_transaction(
            TxType.MISSION_ASSIGN, "controller", drone_id, mission)
        block = self.ledger.mine_block()
        if block:
            result = self.consensus.propose(block)
            return {"tx": tx.tx_id, "accepted": result["accepted"],
                    "block": block.index}
        return {"tx": tx.tx_id, "accepted": False, "block": -1}

    def update_status(self, drone_id: str, status: Dict) -> str:
        tx = self.ledger.add_transaction(
            TxType.STATUS_UPDATE, drone_id, "ledger", status)
        return tx.tx_id

    def check_clearance(self, drone_id: str, context: Dict) -> Dict:
        sc_ids = [k for k, v in self.contracts.contracts.items()
                  if v.name == "airspace_clearance"]
        if sc_ids:
            return self.contracts.execute(sc_ids[0], context)
        return {"executed": False, "reason": "no clearance contract"}

    def apply_penalty(self, drone_id: str, reason: str, amount: float) -> str:
        self.drone_stakes[drone_id] = max(0, self.drone_stakes.get(drone_id, 0) - amount)
        tx = self.ledger.add_transaction(
            TxType.PENALTY, "system", drone_id,
            {"reason": reason, "amount": amount})
        return tx.tx_id

    def run_epoch(self) -> Dict:
        for i in range(min(self.n_drones, 10)):
            did = f"drone_{i}"
            self.update_status(did, {
                "battery": float(self.rng.uniform(20, 95)),
                "altitude": float(self.rng.uniform(30, 150)),
                "speed": float(self.rng.uniform(0, 15)),
            })
        block = self.ledger.mine_block()
        result = self.consensus.propose(block) if block else {"accepted": False}
        return {
            "block_height": self.ledger.height,
            "pending_tx": len(self.ledger.pending),
            "consensus": result.get("accepted", False),
        }

    def summary(self) -> Dict:
        return {
            "drones": self.n_drones,
            "chain_height": self.ledger.height,
            "total_tx": self.ledger._tx_counter,
            "chain_valid": self.ledger.verify_chain(),
            "contracts": len(self.contracts.contracts),
            "consensus_rounds": len(self.consensus.rounds),
            "total_stake": round(sum(self.drone_stakes.values()), 1),
        }
