# Phase 562: Quantum Error Correction — Surface Code Simulation
"""
양자 오류 정정: 표면 코드 시뮬레이션, 신드롬 측정, 디코딩.
비트 플립/위상 플립 오류 모델.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum


class ErrorType(Enum):
    NONE = "none"
    BIT_FLIP = "X"
    PHASE_FLIP = "Z"
    BOTH = "Y"


@dataclass
class Qubit:
    index: int
    state: complex = 1.0 + 0j
    error: ErrorType = ErrorType.NONE


@dataclass
class Syndrome:
    stabilizer_id: int
    value: int  # 0 or 1
    qubits: list = field(default_factory=list)


@dataclass
class CorrectionResult:
    errors_injected: int
    errors_detected: int
    errors_corrected: int
    logical_error: bool


class SurfaceCode:
    """표면 코드: d×d 격자."""

    def __init__(self, distance=3, seed=42):
        self.d = distance
        self.rng = np.random.default_rng(seed)
        n_data = distance * distance
        self.data_qubits = [Qubit(i) for i in range(n_data)]
        self.x_stabilizers: list[list[int]] = []
        self.z_stabilizers: list[list[int]] = []
        self._build_stabilizers()

    def _build_stabilizers(self):
        d = self.d
        # X stabilizers (face)
        for r in range(d - 1):
            for c in range(d - 1):
                qubits = [r * d + c, r * d + c + 1, (r + 1) * d + c, (r + 1) * d + c + 1]
                self.x_stabilizers.append(qubits)
        # Z stabilizers (vertex) — simplified
        for r in range(1, d):
            for c in range(1, d):
                qubits = [(r - 1) * d + c - 1, (r - 1) * d + c, r * d + c - 1, r * d + c]
                self.z_stabilizers.append(qubits)

    def inject_errors(self, error_rate=0.1) -> int:
        count = 0
        for q in self.data_qubits:
            if self.rng.random() < error_rate:
                r = self.rng.random()
                if r < 0.5:
                    q.error = ErrorType.BIT_FLIP
                elif r < 0.8:
                    q.error = ErrorType.PHASE_FLIP
                else:
                    q.error = ErrorType.BOTH
                count += 1
        return count

    def measure_syndrome(self) -> list[Syndrome]:
        syndromes = []
        for i, stab in enumerate(self.x_stabilizers):
            parity = 0
            for qi in stab:
                if qi < len(self.data_qubits):
                    if self.data_qubits[qi].error in (ErrorType.BIT_FLIP, ErrorType.BOTH):
                        parity ^= 1
            syndromes.append(Syndrome(i, parity, stab))
        for i, stab in enumerate(self.z_stabilizers):
            parity = 0
            for qi in stab:
                if qi < len(self.data_qubits):
                    if self.data_qubits[qi].error in (ErrorType.PHASE_FLIP, ErrorType.BOTH):
                        parity ^= 1
            syndromes.append(Syndrome(len(self.x_stabilizers) + i, parity, stab))
        return syndromes

    def decode_and_correct(self, syndromes: list[Syndrome]) -> int:
        """간이 MWPM 디코딩: 신드롬 매칭으로 오류 위치 추정."""
        corrected = 0
        for syn in syndromes:
            if syn.value == 1:
                # 첫 번째 큐빗 수정 (greedy)
                for qi in syn.qubits:
                    if qi < len(self.data_qubits) and self.data_qubits[qi].error != ErrorType.NONE:
                        self.data_qubits[qi].error = ErrorType.NONE
                        corrected += 1
                        break
        return corrected

    def reset(self):
        for q in self.data_qubits:
            q.error = ErrorType.NONE


class QuantumErrorCorrection:
    """양자 오류 정정 시뮬레이션."""

    def __init__(self, distance=3, seed=42):
        self.code = SurfaceCode(distance, seed)
        self.rng = np.random.default_rng(seed)
        self.results: list[CorrectionResult] = []

    def run_cycle(self, error_rate=0.1) -> CorrectionResult:
        self.code.reset()
        injected = self.code.inject_errors(error_rate)
        syndromes = self.code.measure_syndrome()
        detected = sum(1 for s in syndromes if s.value == 1)
        corrected = self.code.decode_and_correct(syndromes)
        remaining = sum(1 for q in self.code.data_qubits if q.error != ErrorType.NONE)
        result = CorrectionResult(injected, detected, corrected, remaining > 0)
        self.results.append(result)
        return result

    def run(self, cycles=50, error_rate=0.1):
        for _ in range(cycles):
            self.run_cycle(error_rate)

    def summary(self):
        n = len(self.results)
        logical_errors = sum(1 for r in self.results if r.logical_error)
        return {
            "distance": self.code.d,
            "data_qubits": len(self.code.data_qubits),
            "cycles": n,
            "total_injected": sum(r.errors_injected for r in self.results),
            "total_corrected": sum(r.errors_corrected for r in self.results),
            "logical_error_rate": round(logical_errors / max(n, 1), 4),
        }


if __name__ == "__main__":
    qec = QuantumErrorCorrection(3, 42)
    qec.run(50, 0.1)
    for k, v in qec.summary().items():
        print(f"  {k}: {v}")
