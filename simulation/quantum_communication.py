"""
Phase 503: Quantum Communication
양자 키 분배(QKD), BB84 프로토콜, 양자 텔레포테이션 시뮬레이션.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple
import hashlib


class QKDBasis(Enum):
    RECTILINEAR = "rectilinear"   # +  (0°, 90°)
    DIAGONAL = "diagonal"          # ×  (45°, 135°)


class QubitState(Enum):
    ZERO = 0       # |0⟩
    ONE = 1        # |1⟩
    PLUS = 2       # |+⟩
    MINUS = 3      # |-⟩


@dataclass
class QKDResult:
    raw_key_length: int
    sifted_key_length: int
    error_rate: float
    secure: bool
    final_key: str


@dataclass
class QuantumChannel:
    channel_id: str
    alice: str
    bob: str
    error_rate: float = 0.0
    eavesdropped: bool = False
    photons_sent: int = 0
    photons_received: int = 0


class BB84Protocol:
    """Bennett-Brassard 1984 QKD protocol simulation."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def _prepare_qubit(self, bit: int, basis: QKDBasis) -> QubitState:
        if basis == QKDBasis.RECTILINEAR:
            return QubitState.ZERO if bit == 0 else QubitState.ONE
        else:
            return QubitState.PLUS if bit == 0 else QubitState.MINUS

    def _measure_qubit(self, state: QubitState, basis: QKDBasis) -> int:
        state_basis = QKDBasis.RECTILINEAR if state in (QubitState.ZERO, QubitState.ONE) else QKDBasis.DIAGONAL
        if basis == state_basis:
            return 0 if state in (QubitState.ZERO, QubitState.PLUS) else 1
        else:
            return int(self.rng.random() > 0.5)

    def execute(self, n_bits: int = 256, eve_present: bool = False,
                channel_error: float = 0.02) -> QKDResult:
        alice_bits = self.rng.integers(0, 2, n_bits)
        alice_bases = self.rng.choice(list(QKDBasis), n_bits)
        bob_bases = self.rng.choice(list(QKDBasis), n_bits)

        qubits = [self._prepare_qubit(int(b), basis) for b, basis in zip(alice_bits, alice_bases)]

        if eve_present:
            eve_bases = self.rng.choice(list(QKDBasis), n_bits)
            for i in range(n_bits):
                _ = self._measure_qubit(qubits[i], eve_bases[i])
                qubits[i] = self._prepare_qubit(int(self.rng.random() > 0.5), eve_bases[i])

        bob_results = []
        for i in range(n_bits):
            if self.rng.random() < channel_error:
                bob_results.append(1 - self._measure_qubit(qubits[i], bob_bases[i]))
            else:
                bob_results.append(self._measure_qubit(qubits[i], bob_bases[i]))

        matching = [i for i in range(n_bits) if alice_bases[i] == bob_bases[i]]
        sifted_alice = [int(alice_bits[i]) for i in matching]
        sifted_bob = [bob_results[i] for i in matching]

        errors = sum(a != b for a, b in zip(sifted_alice, sifted_bob))
        error_rate = errors / max(len(matching), 1)
        secure = error_rate < 0.11

        key_bits = sifted_alice[:len(sifted_alice) // 2] if secure else []
        final_key = hashlib.sha256(bytes(key_bits)).hexdigest()[:32] if key_bits else ""

        return QKDResult(n_bits, len(matching), round(error_rate, 4), secure, final_key)


class QuantumTeleportation:
    """Quantum state teleportation simulation."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.fidelity_log: List[float] = []

    def teleport(self, state: Tuple[complex, complex],
                 noise: float = 0.01) -> Tuple[complex, complex]:
        alpha, beta = state
        norm = np.sqrt(abs(alpha)**2 + abs(beta)**2)
        alpha, beta = alpha / norm, beta / norm

        bell_measurement = self.rng.integers(0, 4)
        noise_alpha = alpha + self.rng.standard_normal() * noise
        noise_beta = beta + self.rng.standard_normal() * noise
        norm2 = np.sqrt(abs(noise_alpha)**2 + abs(noise_beta)**2)
        result = (noise_alpha / norm2, noise_beta / norm2)

        fidelity = abs(np.conj(alpha) * result[0] + np.conj(beta) * result[1])**2
        self.fidelity_log.append(float(fidelity))
        return result

    def avg_fidelity(self) -> float:
        return float(np.mean(self.fidelity_log)) if self.fidelity_log else 0.0


class QuantumCommunication:
    """Integrated quantum communication system for drone swarms."""

    def __init__(self, n_drones: int = 10, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.bb84 = BB84Protocol(seed)
        self.teleport = QuantumTeleportation(seed)
        self.channels: Dict[str, QuantumChannel] = {}
        self.shared_keys: Dict[str, str] = {}

    def establish_qkd(self, alice_id: str, bob_id: str,
                      n_bits: int = 256, eve: bool = False) -> QKDResult:
        result = self.bb84.execute(n_bits, eve)
        key = f"{alice_id}-{bob_id}"
        self.channels[key] = QuantumChannel(key, alice_id, bob_id,
                                            result.error_rate, eve,
                                            n_bits, int(n_bits * 0.9))
        if result.secure:
            self.shared_keys[key] = result.final_key
        return result

    def secure_send(self, sender: str, receiver: str, message: str) -> Dict:
        key = f"{sender}-{receiver}"
        alt_key = f"{receiver}-{sender}"
        shared = self.shared_keys.get(key) or self.shared_keys.get(alt_key)
        if not shared:
            qkd = self.establish_qkd(sender, receiver)
            if not qkd.secure:
                return {"sent": False, "reason": "QKD failed"}
            shared = qkd.final_key

        msg_hash = hashlib.sha256(message.encode()).hexdigest()[:16]
        return {"sent": True, "sender": sender, "receiver": receiver,
                "msg_hash": msg_hash, "key_id": key}

    def summary(self) -> Dict:
        return {
            "drones": self.n_drones,
            "channels": len(self.channels),
            "shared_keys": len(self.shared_keys),
            "avg_teleport_fidelity": round(self.teleport.avg_fidelity(), 4),
        }
