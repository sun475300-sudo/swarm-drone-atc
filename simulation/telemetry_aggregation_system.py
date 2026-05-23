"""
Phase 458: Telemetry Aggregation System
"""

import time
from dataclasses import dataclass

import numpy as np


@dataclass
class TelemetryPacket:
    drone_id: str
    data: dict
    timestamp: float


class TelemetryAggregationSystem:
    def __init__(self, aggregation_window_sec: float = 60):
        self.window = aggregation_window_sec
        self.telemetry_buffer: dict[str, list[TelemetryPacket]] = {}
        self.aggregated: dict[str, dict] = {}

    def ingest(self, packet: TelemetryPacket):
        if packet.drone_id not in self.telemetry_buffer:
            self.telemetry_buffer[packet.drone_id] = []
        self.telemetry_buffer[packet.drone_id].append(packet)

    def aggregate(self, drone_id: str) -> dict:
        if drone_id not in self.telemetry_buffer:
            return {}

        packets = self.telemetry_buffer[drone_id]
        now = time.time()

        recent = [p for p in packets if now - p.timestamp <= self.window]

        if not recent:
            return {}

        battery_values = [p.data.get("battery", 50) for p in recent]

        self.aggregated[drone_id] = {
            "avg_battery": np.mean(battery_values),
            "packet_count": len(recent),
            "timestamp": now,
        }

        return self.aggregated[drone_id]
