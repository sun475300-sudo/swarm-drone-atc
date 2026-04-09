# Phase 582: Drone Blockchain — PoW Consensus
"""
드론 블록체인: 비행 기록 불변 원장,
작업 증명(PoW), 블록 검증, 체인 무결성.
"""

import numpy as np
import hashlib
import time
from dataclasses import dataclass, field


@dataclass
class Block:
    index: int
    timestamp: float
    data: dict
    previous_hash: str
    nonce: int = 0
    hash: str = ""

    def compute_hash(self) -> str:
        content = f"{self.index}{self.timestamp}{self.data}{self.previous_hash}{self.nonce}"
        return hashlib.sha256(content.encode()).hexdigest()


class DroneBlockchain:
    """드론 비행 기록 블록체인."""

    def __init__(self, difficulty=2, seed=42):
        self.chain: list[Block] = []
        self.difficulty = difficulty
        self.rng = np.random.default_rng(seed)
        self.pending: list[dict] = []
        self._create_genesis()

    def _create_genesis(self):
        genesis = Block(0, time.time(), {"type": "genesis"}, "0")
        genesis.hash = genesis.compute_hash()
        self.chain.append(genesis)

    def add_transaction(self, tx: dict):
        self.pending.append(tx)

    def mine_block(self) -> Block:
        last = self.chain[-1]
        block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            data={"transactions": self.pending.copy()},
            previous_hash=last.hash
        )
        target = "0" * self.difficulty
        while not block.compute_hash().startswith(target):
            block.nonce += 1
        block.hash = block.compute_hash()
        self.chain.append(block)
        self.pending.clear()
        return block

    def is_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            prev = self.chain[i - 1]
            if current.hash != current.compute_hash():
                return False
            if current.previous_hash != prev.hash:
                return False
        return True

    def record_flight(self, drone_id: str, lat: float, lon: float, alt: float):
        self.add_transaction({
            "drone": drone_id,
            "position": [lat, lon, alt],
            "time": time.time()
        })

    def run(self, n_drones=5, n_blocks=10):
        for b in range(n_blocks):
            for d in range(n_drones):
                self.record_flight(
                    f"DRONE_{d:03d}",
                    37.5 + float(self.rng.normal(0, 0.01)),
                    127.0 + float(self.rng.normal(0, 0.01)),
                    50 + float(self.rng.uniform(0, 100))
                )
            self.mine_block()

    def summary(self):
        return {
            "chain_length": len(self.chain),
            "difficulty": self.difficulty,
            "valid": self.is_valid(),
            "total_nonces": sum(b.nonce for b in self.chain),
            "pending_tx": len(self.pending),
        }


if __name__ == "__main__":
    bc = DroneBlockchain(2, 42)
    bc.run(5, 5)
    for k, v in bc.summary().items():
        print(f"  {k}: {v}")
