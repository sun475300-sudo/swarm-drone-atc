"""
Acoustic Communication System
Phase 371 - Underwater/Low-noise Communication, Sonar Integration
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import random


@dataclass
class AcousticPacket:
    frequency: float
    amplitude: float
    duration: float
    data: bytes
    timestamp: float


@dataclass
class SonarReading:
    range_m: float
    angle_deg: float
    intensity_db: float
    target_type: str


class AcousticModem:
    def __init__(self, freq_range: Tuple[float, float] = (10e3, 20e3)):
        self.freq_min, self.freq_max = freq_range
        self.carrier_freq = 15e3
        self.bandwidth = 5000
        self.tx_power_w = 1.0
        self.sensitivity_db = -100

    def modulate(self, data: bytes, modulation: str = "PSK") -> AcousticPacket:
        symbol_rate = self.bandwidth / 2
        duration = len(data) * 8 / symbol_rate

        packet = AcousticPacket(
            frequency=self.carrier_freq,
            amplitude=np.sqrt(self.tx_power_w * 50),
            duration=duration,
            data=data,
            timestamp=0.0,
        )
        return packet

    def demodulate(self, packet: AcousticPacket) -> Optional[bytes]:
        if packet.amplitude < 0.01:
            return None
        return packet.data


class UnderwaterChannel:
    def __init__(self):
        self.depth_m = 50
        self.salinity_ppt = 35
        self.temperature_c = 20
        self.speed_of_sound = 1500

    def calculate_absorption(self, freq_hz: float) -> float:
        f_khz = freq_hz / 1000
        absorption = 0.036 * f_khz**2 / (1 + f_khz**2) + 0.052 * f_khz**2 / (
            10 + f_khz**2
        )
        return absorption

    def calculate_path_loss(self, distance_m: float, freq_hz: float) -> float:
        spreading_loss = 20 * np.log10(distance_m) if distance_m > 1 else 0
        absorption = self.calculate_absorption(freq_hz) * distance_m / 1000
        return spreading_loss + absorption

    def transmit(self, packet: AcousticPacket, distance_m: float) -> AcousticPacket:
        path_loss = self.calculate_path_loss(distance_m, packet.frequency)
        received_power = packet.amplitude**2 - path_loss
        packet.amplitude = np.sqrt(max(0, received_power))
        return packet


class SonarSystem:
    def __init__(self):
        self.frequency = 40e3
        self.beam_width_deg = 30
        self.max_range_m = 500
        self.pulse_duration_ms = 10

    def ping(
        self, position: Tuple[float, float, float], targets: List[Dict]
    ) -> List[SonarReading]:
        readings = []
        for target in targets:
            distance = np.sqrt(
                (position[0] - target["x"]) ** 2
                + (position[1] - target["y"]) ** 2
                + (position[2] - target["z"]) ** 2
            )
            if distance < self.max_range_m:
                angle = np.degrees(
                    np.arctan2(target["y"] - position[1], target["x"] - position[0])
                )
                intensity_db = 100 - 0.1 * distance + random.gauss(0, 2)
                readings.append(
                    SonarReading(
                        distance, angle, intensity_db, target.get("type", "unknown")
                    )
                )
        return readings


class AcousticNetwork:
    def __init__(self):
        self.nodes: Dict[str, AcousticModem] = {}
        self.channel = UnderwaterChannel()
        self.sonar = SonarSystem()

    def add_node(self, node_id: str):
        self.nodes[node_id] = AcousticModem()

    def send_message(self, src: str, dst: str, data: bytes) -> bool:
        if src not in self.nodes or dst not in self.nodes:
            return False

        distance = random.uniform(10, 200)
        packet = self.nodes[src].modulate(data)
        received = self.channel.transmit(packet, distance)
        return self.nodes[dst].demodulate(received) is not None


def simulate_acoustic():
    print("=== Acoustic Communication Simulation ===")
    net = AcousticNetwork()
    for i in range(5):
        net.add_node(f"node_{i}")

    print("\n--- Communication Test ---")
    success = 0
    for _ in range(20):
        src, dst = random.sample(list(net.nodes.keys()), 2)
        if net.send_message(src, dst, b"hello"):
            success += 1
    print(f"Success rate: {success}/20")

    print("\n--- Sonar Test ---")
    targets = [
        {"x": 50, "y": 30, "z": -20, "type": "submarine"},
        {"x": 100, "y": 50, "z": -30, "type": "wreck"},
    ]
    readings = net.sonar.ping((0, 0, 0), targets)
    for r in readings:
        print(f"Target: {r.range_m:.1f}m, {r.angle_deg:.1f}°, {r.intensity_db:.1f}dB")

    return {"success_rate": success / 20}


if __name__ == "__main__":
    simulate_acoustic()
