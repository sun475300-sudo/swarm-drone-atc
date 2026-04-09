"""
Phase 483: Quantum-Secured Communication
Quantum key distribution and encryption for drone swarm.
"""

import numpy as np
import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Any


class QKDProtocol(Enum):
    """Quantum Key Distribution protocols."""

    BB84 = auto()
    E91 = auto()
    SARG04 = auto()


@dataclass
class QuantumKey:
    """Quantum encryption key."""

    key_id: str
    key_bits: np.ndarray
    length: int
    creation_time: float
    expiry_time: float
    is_consumed: bool = False


@dataclass
class EncryptedMessage:
    """Encrypted message."""

    message_id: str
    sender: str
    receiver: str
    ciphertext: bytes
    key_id: str
    timestamp: float = field(default_factory=time.time)


class QuantumSecuredComm:
    """Quantum-secured communication system."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.keys: Dict[str, QuantumKey] = {}
        self.message_log: List[EncryptedMessage] = []
        self.key_counter = 0

    def bb84_distribute(
        self, sender: str, receiver: str, key_length: int = 256
    ) -> QuantumKey:
        alice_bits = self.rng.integers(0, 2, key_length)
        alice_bases = self.rng.integers(0, 2, key_length)
        bob_bases = self.rng.integers(0, 2, key_length)
        matching = alice_bases == bob_bases
        sifted_key = alice_bits[matching]
        if len(sifted_key) > 128:
            final_key = sifted_key[:128]
        else:
            final_key = np.pad(sifted_key, (0, 128 - len(sifted_key)))
        key = QuantumKey(
            key_id=f"qkey_{self.key_counter}",
            key_bits=final_key,
            length=128,
            creation_time=time.time(),
            expiry_time=time.time() + 3600,
        )
        self.keys[key.key_id] = key
        self.key_counter += 1
        return key

    def encrypt(self, message: bytes, key_id: str) -> Optional[bytes]:
        if key_id not in self.keys:
            return None
        key = self.keys[key_id]
        if key.is_consumed or time.time() > key.expiry_time:
            return None
        key_bytes = (
            np.packbits(key.key_bits[: len(message) * 8])
            if len(message) * 8 <= len(key.key_bits)
            else np.packbits(key.key_bits)
        )
        encrypted = bytes([m ^ k for m, k in zip(message, key_bytes[: len(message)])])
        key.is_consumed = True
        return encrypted

    def decrypt(self, ciphertext: bytes, key_id: str) -> Optional[bytes]:
        return self.encrypt(ciphertext, key_id)

    def send_encrypted(
        self, sender: str, receiver: str, message: bytes
    ) -> Optional[EncryptedMessage]:
        key = self.bb84_distribute(sender, receiver)
        ciphertext = self.encrypt(message, key.key_id)
        if ciphertext is None:
            return None
        msg = EncryptedMessage(
            f"msg_{len(self.message_log)}", sender, receiver, ciphertext, key.key_id
        )
        self.message_log.append(msg)
        return msg

    def get_security_stats(self) -> Dict[str, Any]:
        active_keys = sum(1 for k in self.keys.values() if not k.is_consumed)
        return {
            "total_keys": len(self.keys),
            "active_keys": active_keys,
            "messages_sent": len(self.message_log),
            "key_utilization": 1 - active_keys / max(1, len(self.keys)),
        }


if __name__ == "__main__":
    qsc = QuantumSecuredComm(seed=42)
    msg = qsc.send_encrypted("drone_0", "drone_1", b"Hello Swarm!")
    if msg:
        decrypted = qsc.decrypt(msg.ciphertext, msg.key_id)
        print(f"Decrypted: {decrypted}")
    print(f"Stats: {qsc.get_security_stats()}")
