"""
Phase 519: Quantum Sensing
양자 센서 시뮬레이션, 양자 관성 측정, 중력계.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple


class QuantumSensorType(Enum):
    ATOM_INTERFEROMETER = "atom_interferometer"
    NV_MAGNETOMETER = "nv_magnetometer"
    QUANTUM_GYROSCOPE = "quantum_gyroscope"
    QUANTUM_GRAVIMETER = "quantum_gravimeter"
    SQUEEZED_LIGHT = "squeezed_light"


class MeasurementBasis(Enum):
    X = "x"
    Y = "y"
    Z = "z"
    CUSTOM = "custom"


@dataclass
class QuantumState:
    amplitudes: np.ndarray  # complex
    n_qubits: int
    coherence: float = 1.0
    phase: float = 0.0


@dataclass
class SensorMeasurement:
    sensor_type: QuantumSensorType
    value: float
    uncertainty: float
    classical_equivalent: float
    quantum_advantage_db: float
    timestamp: float


class QuantumStateEvolver:
    """Evolve quantum states under Hamiltonian dynamics."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def create_state(self, n_qubits: int = 2) -> QuantumState:
        dim = 2 ** n_qubits
        amps = self.rng.standard_normal(dim) + 1j * self.rng.standard_normal(dim)
        amps /= np.linalg.norm(amps)
        return QuantumState(amps, n_qubits)

    def evolve(self, state: QuantumState, dt: float,
               hamiltonian: Optional[np.ndarray] = None) -> QuantumState:
        dim = len(state.amplitudes)
        if hamiltonian is None:
            hamiltonian = self.rng.standard_normal((dim, dim))
            hamiltonian = (hamiltonian + hamiltonian.T) / 2

        U = np.eye(dim) - 1j * hamiltonian * dt
        U_norm = U / np.linalg.norm(U, axis=1, keepdims=True)
        new_amps = U_norm @ state.amplitudes
        new_amps /= np.linalg.norm(new_amps)

        decoherence = np.exp(-dt * 0.01)
        new_coherence = state.coherence * decoherence
        new_phase = state.phase + dt * np.real(np.vdot(state.amplitudes, hamiltonian @ state.amplitudes))

        return QuantumState(new_amps, state.n_qubits, new_coherence, new_phase)

    def measure(self, state: QuantumState, basis: MeasurementBasis = MeasurementBasis.Z) -> float:
        probs = np.abs(state.amplitudes) ** 2
        outcome = self.rng.choice(len(probs), p=probs)
        return float(outcome) / (len(probs) - 1)


class AtomInterferometer:
    """Atom interferometer for precision acceleration measurement."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_atoms = 10000
        self.T_interrogation = 0.1  # seconds
        self.sensitivity = 1e-9  # m/s² per √Hz

    def measure_acceleration(self, true_accel: float) -> SensorMeasurement:
        phase = true_accel * (2 * np.pi / 9.81) * self.T_interrogation ** 2
        shot_noise = 1.0 / np.sqrt(self.n_atoms)
        measured_phase = phase + self.rng.standard_normal() * shot_noise
        measured_accel = measured_phase / (2 * np.pi / 9.81) / self.T_interrogation ** 2
        uncertainty = shot_noise / (2 * np.pi / 9.81) / self.T_interrogation ** 2
        classical_unc = uncertainty * 100
        advantage = 20 * np.log10(classical_unc / (uncertainty + 1e-20))

        return SensorMeasurement(
            QuantumSensorType.ATOM_INTERFEROMETER,
            round(measured_accel, 10), round(uncertainty, 12),
            round(true_accel + self.rng.standard_normal() * classical_unc, 6),
            round(float(advantage), 1), 0.0)


class QuantumGravimeter:
    """Quantum gravimeter for terrain mapping."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def measure_gravity(self, altitude_m: float, terrain_density: float = 2.67) -> SensorMeasurement:
        g0 = 9.80665
        g_alt = g0 * (6371000 / (6371000 + altitude_m)) ** 2
        bouguer = 2 * np.pi * 6.674e-11 * terrain_density * 1000 * altitude_m
        true_g = g_alt - bouguer
        quantum_noise = self.rng.standard_normal() * 1e-8
        classical_noise = self.rng.standard_normal() * 1e-5
        measured = true_g + quantum_noise
        advantage = 20 * np.log10(1e-5 / (1e-8 + 1e-20))

        return SensorMeasurement(
            QuantumSensorType.QUANTUM_GRAVIMETER,
            round(measured, 10), 1e-8, round(true_g + classical_noise, 6),
            round(advantage, 1), 0.0)


class QuantumSensing:
    """Integrated quantum sensing system for drone navigation."""

    def __init__(self, n_sensors: int = 5, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.evolver = QuantumStateEvolver(seed)
        self.interferometer = AtomInterferometer(seed)
        self.gravimeter = QuantumGravimeter(seed)
        self.measurements: List[SensorMeasurement] = []
        self.n_sensors = n_sensors

    def sense_acceleration(self, accel: np.ndarray) -> List[SensorMeasurement]:
        results = []
        for i, a in enumerate(accel):
            m = self.interferometer.measure_acceleration(float(a))
            m.timestamp = float(len(self.measurements) + i)
            self.measurements.append(m)
            results.append(m)
        return results

    def sense_gravity(self, altitude_m: float) -> SensorMeasurement:
        m = self.gravimeter.measure_gravity(altitude_m)
        m.timestamp = float(len(self.measurements))
        self.measurements.append(m)
        return m

    def quantum_enhanced_nav(self, true_pos: np.ndarray,
                             n_steps: int = 10) -> List[np.ndarray]:
        positions = [true_pos.copy()]
        state = self.evolver.create_state(2)
        for _ in range(n_steps):
            state = self.evolver.evolve(state, 0.1)
            accel = self.rng.standard_normal(3) * 0.1
            measurements = self.sense_acceleration(accel)
            correction = np.array([m.value for m in measurements[:3]]) if len(measurements) >= 3 else np.zeros(3)
            new_pos = positions[-1] + correction * 0.01
            positions.append(new_pos)
        return positions

    def summary(self) -> Dict:
        return {
            "sensors": self.n_sensors,
            "measurements": len(self.measurements),
            "avg_advantage_db": round(
                np.mean([m.quantum_advantage_db for m in self.measurements])
                if self.measurements else 0, 1),
        }
