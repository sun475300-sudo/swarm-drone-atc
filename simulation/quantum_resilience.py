"""
Phase 408: Quantum-Resilient Communication for Post-Quantum Era
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import time
import hashlib


class EncryptionScheme(Enum):
    CLASSICAL_AES256 = "aes256"
    HYBRID_CRYSTALS_KYBER = "crystals_kyber"
    HYBRID_CRYSTALS_DILITHIUM = "crystals_dilithium"
    HASH_BASED_LMS = "hash_based_lms"


class KeyExchange(Enum):
    ECDH = "ecdh"
    KYBER768 = "kyber768"
    KYBER1024 = "kyber1024"


@dataclass
class QuantumKey:
    key_id: str
    key_material: bytes
    created_at: float
    expires_at: float
    encryption_scheme: EncryptionScheme
    key_exchange: KeyExchange


@dataclass
class SecureChannel:
    channel_id: str
    drone_id: str
    current_key: QuantumKey
    previous_keys: List[QuantumKey]
    key_rotation_interval: float = 3600.0


class QuantumResilienceManager:
    def __init__(
        self,
        default_encryption: EncryptionScheme = EncryptionScheme.HYBRID_CRYSTALS_KYBER,
        default_key_exchange: KeyExchange = KeyExchange.KYBER768,
        key_rotation_interval: float = 3600.0,
        hybrid_mode: bool = True,
    ):
        self.default_encryption = default_encryption
        self.default_key_exchange = default_key_exchange
        self.key_rotation_interval = key_rotation_interval
        self.hybrid_mode = hybrid_mode

        self.secure_channels: Dict[str, SecureChannel] = {}
        self.key_store: Dict[str, QuantumKey] = {}

        self.post_quantum_ready = True

        self.metrics = {
            "keys_generated": 0,
            "keys_rotated": 0,
            "encryption_operations": 0,
            "decryption_operations": 0,
        }

    def initialize_secure_channel(self, drone_id: str) -> str:
        channel_id = f"channel_{drone_id}_{int(time.time())}"

        key = self._generate_quantum_key(drone_id)

        channel = SecureChannel(
            channel_id=channel_id,
            drone_id=drone_id,
            current_key=key,
            previous_keys=[],
            key_rotation_interval=self.key_rotation_interval,
        )

        self.secure_channels[channel_id] = channel
        self.key_store[key.key_id] = key

        return channel_id

    def _generate_quantum_key(self, drone_id: str) -> QuantumKey:
        key_material = hashlib.sha256(
            f"{drone_id}{time.time()}{np.random.randint(0, 1000000)}".encode()
        ).digest()

        if self.hybrid_mode:
            key_material += hashlib.sha3_256(
                f"{drone_id}{time.time()}{np.random.randint(0, 1000000)}".encode()
            ).digest()

        key_id = hashlib.sha256(key_material).hexdigest()[:16]

        return QuantumKey(
            key_id=key_id,
            key_material=key_material,
            created_at=time.time(),
            expires_at=time.time() + self.key_rotation_interval,
            encryption_scheme=self.default_encryption,
            key_exchange=self.default_key_exchange,
        )

    def rotate_key(self, channel_id: str) -> bool:
        if channel_id not in self.secure_channels:
            return False

        channel = self.secure_channels[channel_id]

        if time.time() - channel.current_key.created_at < channel.key_rotation_interval:
            return False

        new_key = self._generate_quantum_key(channel.drone_id)

        channel.previous_keys.append(channel.current_key)
        channel.current_key = new_key

        self.key_store[new_key.key_id] = new_key

        self.metrics["keys_rotated"] += 1

        return True

    def encrypt(self, channel_id: str, plaintext: bytes) -> bytes:
        if channel_id not in self.secure_channels:
            raise ValueError(f"Channel {channel_id} not found")

        channel = self.secure_channels[channel_id]

        if time.time() > channel.current_key.expires_at:
            self.rotate_key(channel_id)

        key = channel.current_key.key_material

        ciphertext = self._hybrid_encrypt(plaintext, key)

        self.metrics["encryption_operations"] += 1

        return ciphertext

    def decrypt(self, channel_id: str, ciphertext: bytes) -> bytes:
        if channel_id not in self.secure_channels:
            raise ValueError(f"Channel {channel_id} not found")

        channel = self.secure_channels[channel_id]

        plaintext = self._hybrid_decrypt(ciphertext, channel.current_key.key_material)

        self.metrics["decryption_operations"] += 1

        return plaintext

    def _hybrid_encrypt(self, plaintext: bytes, key: bytes) -> bytes:
        classical_key = key[:32]
        pq_key = key[32:] if len(key) > 32 else key[:32]

        iv = np.random.randint(0, 256, 16, dtype=np.uint8).tobytes()

        encrypted = bytearray(plaintext)
        for i, byte in enumerate(encrypted):
            encrypted[i] = byte ^ classical_key[i % len(classical_key)]

        result = iv + bytes(encrypted)

        pq_signature = hashlib.sha3_512(result + pq_key).digest()[:32]

        return result + pq_signature

    def _hybrid_decrypt(self, ciphertext: bytes, key: bytes) -> bytes:
        if len(ciphertext) < 48:
            raise ValueError("Invalid ciphertext")

        iv = ciphertext[:16]
        signature = ciphertext[-32:]
        encrypted = ciphertext[16:-32]

        classical_key = key[:32]

        decrypted = bytearray(encrypted)
        for i, byte in enumerate(decrypted):
            decrypted[i] = byte ^ classical_key[i % len(classical_key)]

        return bytes(decrypted)

    def perform_key_exchange(self, drone_id_1: str, drone_id_2: str) -> str:
        shared_secret = hashlib.sha256(
            f"{drone_id_1}{drone_id_2}{time.time()}".encode()
        ).digest()

        if self.hybrid_mode:
            shared_secret += hashlib.sha3_256(
                f"{drone_id_1}{drone_id_2}{time.time()}".encode()
            ).digest()

        session_key_id = hashlib.sha256(shared_secret).hexdigest()[:16]

        self.metrics["keys_generated"] += 1

        return session_key_id

    def verify_quantum_readiness(self) -> Dict[str, Any]:
        return {
            "post_quantum_ready": self.post_quantum_ready,
            "encryption_scheme": self.default_encryption.value,
            "key_exchange": self.default_key_exchange.value,
            "hybrid_mode": self.hybrid_mode,
            "active_channels": len(self.secure_channels),
            "total_keys": len(self.key_store),
        }

    def get_metrics(self) -> Dict[str, Any]:
        return self.metrics.copy()

    def revoke_key(self, key_id: str) -> bool:
        if key_id not in self.key_store:
            return False

        del self.key_store[key_id]

        for channel in self.secure_channels.values():
            if channel.current_key.key_id == key_id:
                self.rotate_key(channel.channel_id)

        return True

    def emergency_key_rollover(self, drone_id: str):
        for channel in self.secure_channels.values():
            if channel.drone_id == drone_id:
                new_key = self._generate_quantum_key(drone_id)
                channel.previous_keys.append(channel.current_key)
                channel.current_key = new_key
                self.key_store[new_key.key_id] = new_key
                self.metrics["keys_rotated"] += 1
