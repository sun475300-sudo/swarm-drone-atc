"""
Phase 339: Drone Swarm Encryption
군집 전용 암호화 시스템.
그룹 키 교환 (Diffie-Hellman) + 양자내성 격자 암호 시뮬레이션.
"""

import hashlib
import secrets
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple


class CipherSuite(Enum):
    AES_256_GCM = "aes-256-gcm"
    CHACHA20_POLY1305 = "chacha20-poly1305"
    LATTICE_KYBER = "lattice-kyber"
    HYBRID_PQ = "hybrid-pq"


class KeyExchangeMethod(Enum):
    DH = "diffie-hellman"
    ECDH = "ecdh"
    KYBER_KEM = "kyber-kem"
    GROUP_DH = "group-dh"


@dataclass
class KeyPair:
    public_key: bytes
    private_key: bytes
    algorithm: str


@dataclass
class GroupKey:
    key_id: str
    key_data: bytes
    epoch: int
    member_ids: List[str]
    created_at: float
    expires_at: float


@dataclass
class EncryptedMessage:
    msg_id: str
    sender_id: str
    recipient_ids: List[str]
    ciphertext: bytes
    nonce: bytes
    tag: bytes
    cipher_suite: CipherSuite
    key_id: str


@dataclass
class SecurityEvent:
    event_type: str  # key_rotation, intrusion, revocation
    drone_id: str
    description: str
    timestamp: float


class LatticeKEM:
    """Simplified lattice-based KEM (Kyber-like) simulation."""

    def __init__(self, n: int = 256, q: int = 3329, seed: int = 42):
        self.n = n
        self.q = q
        self.rng = np.random.default_rng(seed)

    def keygen(self) -> Tuple[np.ndarray, np.ndarray]:
        s = self.rng.integers(-2, 3, size=self.n)
        a = self.rng.integers(0, self.q, size=self.n)
        e = self.rng.integers(-1, 2, size=self.n)
        b = (a * s + e) % self.q
        return b, s  # public, private

    def encapsulate(self, public_key: np.ndarray) -> Tuple[np.ndarray, bytes]:
        r = self.rng.integers(-1, 2, size=self.n)
        a = self.rng.integers(0, self.q, size=self.n)
        e1 = self.rng.integers(-1, 2, size=self.n)
        u = (a * r + e1) % self.q
        e2 = self.rng.integers(-1, 2, size=self.n)
        v = (public_key * r + e2) % self.q
        shared = hashlib.sha256(v.tobytes()).digest()
        return u, shared

    def decapsulate(self, ciphertext: np.ndarray,
                    private_key: np.ndarray) -> bytes:
        v_approx = (ciphertext * private_key) % self.q
        return hashlib.sha256(v_approx.tobytes()).digest()


class GroupKeyManager:
    """Manages group keys for swarm communication."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.group_keys: Dict[str, GroupKey] = {}
        self.epoch = 0
        self._key_counter = 0

    def generate_group_key(self, member_ids: List[str],
                           ttl_seconds: float = 3600.0) -> GroupKey:
        self._key_counter += 1
        self.epoch += 1
        key_data = secrets.token_bytes(32)
        import time
        now = time.time()
        gk = GroupKey(
            key_id=f"GK-{self._key_counter:06d}",
            key_data=key_data,
            epoch=self.epoch,
            member_ids=list(member_ids),
            created_at=now,
            expires_at=now + ttl_seconds
        )
        self.group_keys[gk.key_id] = gk
        return gk

    def rotate_key(self, old_key_id: str,
                   exclude_members: Optional[List[str]] = None) -> Optional[GroupKey]:
        old = self.group_keys.get(old_key_id)
        if not old:
            return None
        members = [m for m in old.member_ids
                   if not exclude_members or m not in exclude_members]
        return self.generate_group_key(members)

    def revoke_member(self, key_id: str, member_id: str) -> Optional[GroupKey]:
        return self.rotate_key(key_id, exclude_members=[member_id])


class DroneSwarmEncryption:
    """Complete encryption system for drone swarm communication."""

    def __init__(self, cipher_suite: CipherSuite = CipherSuite.HYBRID_PQ,
                 seed: int = 42):
        self.cipher_suite = cipher_suite
        self.rng = np.random.default_rng(seed)
        self.lattice_kem = LatticeKEM(seed=seed)
        self.key_manager = GroupKeyManager(seed=seed)
        self.drone_keys: Dict[str, KeyPair] = {}
        self.active_group_key: Optional[GroupKey] = None
        self.security_events: List[SecurityEvent] = []
        self._msg_counter = 0

    def register_drone(self, drone_id: str) -> KeyPair:
        pub, priv = self.lattice_kem.keygen()
        kp = KeyPair(
            public_key=pub.tobytes(),
            private_key=priv.tobytes(),
            algorithm="kyber-sim"
        )
        self.drone_keys[drone_id] = kp
        return kp

    def establish_group(self, member_ids: List[str]) -> GroupKey:
        gk = self.key_manager.generate_group_key(member_ids)
        self.active_group_key = gk
        self._log_event("group_established", "system",
                        f"Group key {gk.key_id} for {len(member_ids)} members")
        return gk

    def encrypt_message(self, sender_id: str, plaintext: bytes,
                        recipients: Optional[List[str]] = None) -> EncryptedMessage:
        self._msg_counter += 1

        if not self.active_group_key:
            raise RuntimeError("No active group key")

        key = self.active_group_key.key_data
        nonce = secrets.token_bytes(12)

        # Simplified XOR encryption (production would use AES-GCM)
        key_stream = hashlib.sha256(key + nonce).digest()
        extended_key = key_stream * (len(plaintext) // len(key_stream) + 1)
        ciphertext = bytes(p ^ k for p, k in zip(plaintext, extended_key[:len(plaintext)]))
        tag = hashlib.sha256(key + ciphertext + nonce).digest()[:16]

        return EncryptedMessage(
            msg_id=f"MSG-{self._msg_counter:08d}",
            sender_id=sender_id,
            recipient_ids=recipients or self.active_group_key.member_ids,
            ciphertext=ciphertext,
            nonce=nonce,
            tag=tag,
            cipher_suite=self.cipher_suite,
            key_id=self.active_group_key.key_id
        )

    def decrypt_message(self, msg: EncryptedMessage,
                        drone_id: str) -> Optional[bytes]:
        if drone_id not in msg.recipient_ids:
            return None

        gk = self.key_manager.group_keys.get(msg.key_id)
        if not gk:
            return None

        key = gk.key_data
        nonce = msg.nonce

        expected_tag = hashlib.sha256(key + msg.ciphertext + nonce).digest()[:16]
        if expected_tag != msg.tag:
            self._log_event("integrity_fail", drone_id,
                            f"Message {msg.msg_id} tag mismatch")
            return None

        key_stream = hashlib.sha256(key + nonce).digest()
        extended_key = key_stream * (len(msg.ciphertext) // len(key_stream) + 1)
        plaintext = bytes(c ^ k for c, k in zip(msg.ciphertext, extended_key[:len(msg.ciphertext)]))
        return plaintext

    def rotate_group_key(self) -> Optional[GroupKey]:
        if not self.active_group_key:
            return None
        new_key = self.key_manager.rotate_key(self.active_group_key.key_id)
        if new_key:
            self.active_group_key = new_key
            self._log_event("key_rotation", "system",
                            f"Rotated to {new_key.key_id} (epoch {new_key.epoch})")
        return new_key

    def revoke_drone(self, drone_id: str) -> Optional[GroupKey]:
        if not self.active_group_key:
            return None
        self._log_event("revocation", drone_id, f"Drone {drone_id} revoked")
        new_key = self.key_manager.revoke_member(
            self.active_group_key.key_id, drone_id)
        if new_key:
            self.active_group_key = new_key
        if drone_id in self.drone_keys:
            del self.drone_keys[drone_id]
        return new_key

    def _log_event(self, event_type: str, drone_id: str, desc: str) -> None:
        import time
        self.security_events.append(SecurityEvent(
            event_type=event_type, drone_id=drone_id,
            description=desc, timestamp=time.time()
        ))

    def summary(self) -> Dict:
        return {
            "cipher_suite": self.cipher_suite.value,
            "registered_drones": len(self.drone_keys),
            "group_keys": len(self.key_manager.group_keys),
            "current_epoch": self.key_manager.epoch,
            "messages_encrypted": self._msg_counter,
            "security_events": len(self.security_events),
        }


if __name__ == "__main__":
    enc = DroneSwarmEncryption(CipherSuite.HYBRID_PQ)
    drones = [f"drone_{i}" for i in range(5)]
    for d in drones:
        enc.register_drone(d)

    enc.establish_group(drones)

    msg = enc.encrypt_message("drone_0", b"Formation alpha, heading 090")
    decrypted = enc.decrypt_message(msg, "drone_1")
    print(f"Decrypted: {decrypted}")

    enc.rotate_group_key()
    enc.revoke_drone("drone_4")
    print(f"Summary: {enc.summary()}")
