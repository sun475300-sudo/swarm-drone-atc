"""
Phase 431: 6G Communication Engine
6G communication for drone swarm: THz bands, IRS, holographic, AI-native.
"""

import numpy as np
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Any


class FrequencyBand(Enum):
    """6G frequency bands."""

    SUB6GHZ = auto()
    MMWAVE = auto()
    THZ = auto()
    OPTICAL = auto()
    VISIBLE_LIGHT = auto()


class ModulationType(Enum):
    """Modulation schemes."""

    QPSK = auto()
    QAM16 = auto()
    QAM64 = auto()
    QAM256 = auto()
    OFDM = auto()
    NOMA = auto()
    OTFS = auto()


class NetworkSlice(Enum):
    """Network slicing types."""

    URLLC = auto()  # Ultra-Reliable Low-Latency
    eMBB = auto()  # Enhanced Mobile Broadband
    mMTC = auto()  # Massive Machine-Type
    HCS = auto()  # Holographic Communication


@dataclass
class THzChannel:
    """Terahertz channel model."""

    frequency_hz: float = 300e9
    bandwidth_hz: float = 50e9
    path_loss_db: float = 0.0
    atmospheric_loss_db: float = 0.0
    molecular_absorption: float = 0.0
    rain_attenuation_db: float = 0.0
    scintillation_loss_db: float = 0.0

    def compute_path_loss(self, distance_m: float) -> float:
        c = 3e8
        wavelength = c / self.frequency_hz
        fspl = 20 * np.log10(4 * np.pi * distance_m / wavelength)
        self.path_loss_db = fspl
        self.atmospheric_loss_db = self.molecular_absorption * distance_m / 1000
        return self.path_loss_db + self.atmospheric_loss_db + self.rain_attenuation_db

    def compute_capacity(self, snr_db: float) -> float:
        snr_linear = 10 ** (snr_db / 10)
        capacity = self.bandwidth_hz * np.log2(1 + snr_linear)
        return capacity


@dataclass
class IRSPanel:
    """Intelligent Reflecting Surface panel."""

    panel_id: str
    position: np.ndarray
    n_elements: int = 256
    element_spacing: float = 0.005
    phase_shifts: np.ndarray = field(default_factory=lambda: np.array([]))
    is_active: bool = True

    def __post_init__(self):
        if len(self.phase_shifts) == 0:
            self.phase_shifts = np.random.uniform(0, 2 * np.pi, self.n_elements)

    def optimize_phases(
        self, tx_pos: np.ndarray, rx_pos: np.ndarray, wavelength: float = 0.001
    ) -> np.ndarray:
        n_side = int(np.sqrt(self.n_elements))
        phases = np.zeros(self.n_elements)
        for i in range(n_side):
            for j in range(n_side):
                idx = i * n_side + j
                element_pos = self.position + np.array(
                    [i * self.element_spacing, j * self.element_spacing, 0]
                )
                d_tx = np.linalg.norm(element_pos - tx_pos)
                d_rx = np.linalg.norm(element_pos - rx_pos)
                phase = -2 * np.pi * (d_tx + d_rx) / wavelength
                phases[idx] = phase % (2 * np.pi)
        self.phase_shifts = phases
        return phases

    def compute_reflection_gain(self) -> float:
        coherent_gain = np.abs(np.sum(np.exp(1j * self.phase_shifts))) ** 2
        return float(coherent_gain / self.n_elements)


@dataclass
class HolographicBeam:
    """Holographic communication beam."""

    beam_id: str
    frequency_hz: float
    bandwidth_hz: float
    beam_pattern: np.ndarray = field(default_factory=lambda: np.array([]))
    data_rate_gbps: float = 0.0
    latency_us: float = 0.0

    def compute_beam_pattern(
        self, n_antennas: int = 64, steering_angle: float = 0.0
    ) -> np.ndarray:
        angles = np.linspace(-np.pi / 2, np.pi / 2, 360)
        pattern = np.zeros(len(angles))
        for i, angle in enumerate(angles):
            phase_shift = (
                2 * np.pi * np.arange(n_antennas) * np.sin(angle - steering_angle)
            )
            pattern[i] = np.abs(np.sum(np.exp(1j * phase_shift))) ** 2
        self.beam_pattern = pattern / pattern.max()
        return self.beam_pattern

    def compute_data_rate(self, snr_db: float) -> float:
        snr_linear = 10 ** (snr_db / 10)
        self.data_rate_gbps = self.bandwidth_hz * np.log2(1 + snr_linear) / 1e9
        return self.data_rate_gbps


@dataclass
class NetworkSliceConfig:
    """Network slice configuration."""

    slice_type: NetworkSlice
    priority: int = 0
    max_latency_ms: float = 1.0
    min_reliability: float = 0.99999
    bandwidth_allocation: float = 0.0
    qos_class: int = 0


@dataclass
class CommunicationLink:
    """Communication link between nodes."""

    link_id: str
    source: str
    target: str
    frequency_band: FrequencyBand
    modulation: ModulationType
    snr_db: float = 20.0
    data_rate_mbps: float = 0.0
    latency_ms: float = 0.0
    reliability: float = 0.99
    is_active: bool = True


class SixGCommunicationEngine:
    """6G communication engine for drone swarm."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.channels: Dict[str, THzChannel] = {}
        self.irs_panels: Dict[str, IRSPanel] = {}
        self.holographic_beams: Dict[str, HolographicBeam] = {}
        self.links: Dict[str, CommunicationLink] = {}
        self.slices: Dict[str, NetworkSliceConfig] = {}
        self.drone_positions: Dict[str, np.ndarray] = {}

    def add_thz_channel(
        self, channel_id: str, frequency_hz: float = 300e9, bandwidth_hz: float = 50e9
    ) -> THzChannel:
        channel = THzChannel(frequency_hz=frequency_hz, bandwidth_hz=bandwidth_hz)
        self.channels[channel_id] = channel
        return channel

    def add_irs_panel(
        self, panel_id: str, position: np.ndarray, n_elements: int = 256
    ) -> IRSPanel:
        panel = IRSPanel(panel_id, position, n_elements)
        self.irs_panels[panel_id] = panel
        return panel

    def create_holographic_beam(
        self, beam_id: str, frequency_hz: float = 100e9, bandwidth_hz: float = 10e9
    ) -> HolographicBeam:
        beam = HolographicBeam(beam_id, frequency_hz, bandwidth_hz)
        beam.compute_beam_pattern()
        self.holographic_beams[beam_id] = beam
        return beam

    def create_link(
        self, source: str, target: str, band: FrequencyBand = FrequencyBand.THZ
    ) -> CommunicationLink:
        link_id = f"link_{source}_{target}"
        modulation = (
            ModulationType.QAM256 if band == FrequencyBand.THZ else ModulationType.QAM64
        )
        link = CommunicationLink(link_id, source, target, band, modulation)
        self.links[link_id] = link
        return link

    def configure_slice(
        self, slice_type: NetworkSlice, config: Dict[str, Any]
    ) -> NetworkSliceConfig:
        slice_config = NetworkSliceConfig(
            slice_type=slice_type,
            priority=config.get("priority", 0),
            max_latency_ms=config.get("max_latency_ms", 1.0),
            min_reliability=config.get("min_reliability", 0.99999),
            bandwidth_allocation=config.get("bandwidth", 1000.0),
        )
        self.slices[slice_type.name] = slice_config
        return slice_config

    def register_drone(self, drone_id: str, position: np.ndarray) -> None:
        self.drone_positions[drone_id] = position.copy()

    def update_drone_position(self, drone_id: str, position: np.ndarray) -> None:
        self.drone_positions[drone_id] = position.copy()

    def compute_link_quality(self, source: str, target: str) -> Dict[str, float]:
        if source not in self.drone_positions or target not in self.drone_positions:
            return {"snr_db": 0, "data_rate_mbps": 0, "latency_ms": 999}
        distance = np.linalg.norm(
            self.drone_positions[source] - self.drone_positions[target]
        )
        channel = list(self.channels.values())[0] if self.channels else THzChannel()
        path_loss = channel.compute_path_loss(distance)
        tx_power_dbm = 30
        noise_power_dbm = -90
        snr_db = tx_power_dbm - path_loss - noise_power_dbm
        if snr_db < 0:
            snr_db = 0
        capacity = channel.compute_capacity(snr_db)
        latency = distance / 3e8 * 1000 + self.rng.uniform(0.01, 0.1)
        return {
            "snr_db": snr_db,
            "data_rate_mbps": capacity / 1e6,
            "latency_ms": latency,
            "distance_m": distance,
        }

    def optimize_irs_for_link(self, source: str, target: str) -> float:
        if not self.irs_panels:
            return 0.0
        if source not in self.drone_positions or target not in self.drone_positions:
            return 0.0
        total_gain = 0.0
        for panel in self.irs_panels.values():
            if panel.is_active:
                panel.optimize_phases(
                    self.drone_positions[source], self.drone_positions[target]
                )
                total_gain += panel.compute_reflection_gain()
        return total_gain

    def handover_decision(
        self, drone_id: str, candidate_bands: List[FrequencyBand]
    ) -> FrequencyBand:
        best_band = FrequencyBand.SUB6GHZ
        best_rate = 0.0
        for band in candidate_bands:
            channel = self.add_thz_channel(
                f"temp_{band.name}",
                frequency_hz=300e9 if band == FrequencyBand.THZ else 28e9,
            )
            rate = channel.compute_capacity(20)
            if rate > best_rate:
                best_rate = rate
                best_band = band
        return best_band

    def get_network_stats(self) -> Dict[str, Any]:
        active_links = sum(1 for l in self.links.values() if l.is_active)
        avg_snr = np.mean([l.snr_db for l in self.links.values()]) if self.links else 0
        return {
            "channels": len(self.channels),
            "irs_panels": len(self.irs_panels),
            "holographic_beams": len(self.holographic_beams),
            "active_links": active_links,
            "slices": len(self.slices),
            "drones": len(self.drone_positions),
            "avg_snr_db": avg_snr,
        }


class DroneSwarm6GNetwork:
    """6G network manager for drone swarm."""

    def __init__(self, n_drones: int, seed: int = 42):
        self.n_drones = n_drones
        self.rng = np.random.default_rng(seed)
        self.engine = SixGCommunicationEngine(seed)
        self._init_network()

    def _init_network(self) -> None:
        self.engine.add_thz_channel("main_thz", 300e9, 50e9)
        self.engine.add_thz_channel("backup_mmwave", 28e9, 1e9)
        for i in range(self.n_drones):
            pos = np.array([i * 100.0, self.rng.uniform(-50, 50), 50.0])
            self.engine.register_drone(f"drone_{i}", pos)
        for i in range(self.n_drones - 1):
            self.engine.create_link(f"drone_{i}", f"drone_{i + 1}", FrequencyBand.THZ)
        irs_pos = np.array([self.n_drones * 50, 0, 100])
        self.engine.add_irs_panel("irs_0", irs_pos, n_elements=256)
        self.engine.configure_slice(
            NetworkSlice.URLLC,
            {
                "priority": 1,
                "max_latency_ms": 0.5,
                "min_reliability": 0.99999,
                "bandwidth": 100,
            },
        )
        self.engine.configure_slice(
            NetworkSlice.eMBB,
            {
                "priority": 2,
                "max_latency_ms": 10,
                "min_reliability": 0.99,
                "bandwidth": 5000,
            },
        )

    def update_swarm_positions(self, positions: Dict[str, np.ndarray]) -> None:
        for drone_id, pos in positions.items():
            self.engine.update_drone_position(drone_id, pos)

    def get_link_quality_matrix(self) -> Dict[str, Dict[str, float]]:
        matrix = {}
        for i in range(self.n_drones):
            for j in range(i + 1, self.n_drones):
                key = f"drone_{i}_drone_{j}"
                matrix[key] = self.engine.compute_link_quality(
                    f"drone_{i}", f"drone_{j}"
                )
        return matrix

    def optimize_network(self) -> Dict[str, float]:
        gains = {}
        for i in range(self.n_drones):
            for j in range(i + 1, self.n_drones):
                gain = self.engine.optimize_irs_for_link(f"drone_{i}", f"drone_{j}")
                gains[f"drone_{i}_drone_{j}"] = gain
        return gains

    def get_network_report(self) -> Dict[str, Any]:
        return {
            "stats": self.engine.get_network_stats(),
            "link_quality": self.get_link_quality_matrix(),
            "irs_optimization": self.optimize_network(),
        }


if __name__ == "__main__":
    network = DroneSwarm6GNetwork(n_drones=5, seed=42)
    report = network.get_network_report()
    print(f"Network stats: {report['stats']}")
    print(f"Link quality samples: {list(report['link_quality'].items())[:2]}")
