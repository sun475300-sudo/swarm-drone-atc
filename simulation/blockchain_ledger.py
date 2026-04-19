"""
Phase 404: Blockchain Ledger for Drone Mission Audit Trail
"""

import hashlib
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np


class TransactionType(Enum):
    MISSION_START = "mission_start"
    MISSION_COMPLETE = "mission_complete"
    COLLISION_EVENT = "collision_event"
    BATTERY_SWAP = "battery_swap"
    POSITION_UPDATE = "position_update"
    EMERGENCY = "emergency"
    AIRSPACE_VIOLATION = "airspace_violation"


@dataclass
class Transaction:
    tx_id: str
    timestamp: float
    drone_id: str
    tx_type: TransactionType
    data: Dict[str, Any]
    signature: str = ""
    previous_hash: str = ""


@dataclass
class Block:
    index: int
    timestamp: float
    transactions: List[Transaction]
    hash: str
    previous_hash: str
    nonce: int = 0
    validator: str = ""


class BlockchainLedger:
    def __init__(self, difficulty: int = 4):
        self.difficulty = difficulty
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []
        self.validators: set = set()
        self.drone_registry: Dict[str, Dict] = {}

        self.create_genesis_block()

    def create_genesis_block(self):
        genesis_block = Block(
            index=0,
            timestamp=time.time(),
            transactions=[],
            hash=self.calculate_hash(0, time.time(), [], "0"),
            previous_hash="0",
            nonce=0,
            validator="system",
        )
        self.chain.append(genesis_block)

    def calculate_hash(
        self,
        index: int,
        timestamp: float,
        transactions: List[Transaction],
        previous_hash: str,
        nonce: int = 0,
    ) -> str:
        data = f"{index}{timestamp}{[self._tx_to_dict(t) for t in transactions]}{previous_hash}{nonce}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _tx_to_dict(self, tx: Transaction) -> Dict:
        return {
            "tx_id": tx.tx_id,
            "timestamp": tx.timestamp,
            "drone_id": tx.drone_id,
            "tx_type": tx.tx_type.value,
            "data": tx.data,
        }

    def add_validator(self, validator_id: str):
        self.validators.add(validator_id)

    def register_drone(self, drone_id: str, metadata: Dict[str, Any]):
        self.drone_registry[drone_id] = {
            "registered_at": time.time(),
            "metadata": metadata,
            "mission_count": 0,
        }

    def create_transaction(
        self,
        drone_id: str,
        tx_type: TransactionType,
        data: Dict[str, Any],
    ) -> Transaction:
        if drone_id not in self.drone_registry:
            self.register_drone(drone_id, {})

        tx = Transaction(
            tx_id=self._generate_tx_id(drone_id, tx_type),
            timestamp=time.time(),
            drone_id=drone_id,
            tx_type=tx_type,
            data=data,
        )

        last_block = self.chain[-1]
        tx.previous_hash = last_block.hash

        return tx

    def _generate_tx_id(self, drone_id: str, tx_type: TransactionType) -> str:
        unique_data = (
            f"{drone_id}{tx_type.value}{time.time()}{np.random.randint(0, 10000)}"
        )
        return hashlib.sha256(unique_data.encode()).hexdigest()

    def add_transaction(self, transaction: Transaction):
        self.pending_transactions.append(transaction)

    def mine_block(self, validator: str = "validator_1") -> Block:
        if not self.pending_transactions:
            raise ValueError("No pending transactions to mine")

        last_block = self.chain[-1]

        block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            transactions=self.pending_transactions.copy(),
            hash="",
            previous_hash=last_block.hash,
            nonce=0,
            validator=validator,
        )

        block.hash = self._proof_of_work(block)

        self.chain.append(block)

        if validator in self.drone_registry:
            self.drone_registry[validator]["mission_count"] = (
                self.drone_registry[validator].get("mission_count", 0) + 1
            )

        self.pending_transactions = []

        return block

    def _proof_of_work(self, block: Block) -> str:
        target = "0" * self.difficulty

        while True:
            hash_result = self.calculate_hash(
                block.index,
                block.timestamp,
                block.transactions,
                block.previous_hash,
                block.nonce,
            )

            if hash_result[: self.difficulty] == target:
                return hash_result

            block.nonce += 1

            if block.nonce > 100000:
                raise RuntimeError("Mining failed - too many iterations")

    def verify_chain(self) -> bool:
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            if current_block.previous_hash != previous_block.hash:
                return False

            expected_hash = self.calculate_hash(
                current_block.index,
                current_block.timestamp,
                current_block.transactions,
                current_block.previous_hash,
                current_block.nonce,
            )

            if current_block.hash != expected_hash:
                return False

        return True

    def get_drone_history(self, drone_id: str) -> List[Dict]:
        history = []

        for block in self.chain:
            for tx in block.transactions:
                if tx.drone_id == drone_id:
                    history.append(
                        {
                            "block_index": block.index,
                            "timestamp": tx.timestamp,
                            "tx_type": tx.tx_type.value,
                            "data": tx.data,
                        }
                    )

        return sorted(history, key=lambda x: x["timestamp"], reverse=True)

    def get_chain_stats(self) -> Dict[str, Any]:
        tx_counts = {}
        for block in self.chain:
            for tx in block.transactions:
                tx_type = tx.tx_type.value
                tx_counts[tx_type] = tx_counts.get(tx_type, 0) + 1

        return {
            "total_blocks": len(self.chain),
            "total_transactions": sum(len(b.transactions) for b in self.chain),
            "transaction_counts": tx_counts,
            "validators": list(self.validators),
            "registered_drones": len(self.drone_registry),
        }

    def export_chain(self) -> str:
        chain_data = []
        for block in self.chain:
            chain_data.append(
                {
                    "index": block.index,
                    "timestamp": block.timestamp,
                    "transactions": [self._tx_to_dict(tx) for tx in block.transactions],
                    "hash": block.hash,
                    "previous_hash": block.previous_hash,
                    "nonce": block.nonce,
                    "validator": block.validator,
                }
            )
        return json.dumps(chain_data, indent=2)
