"""Phase 673: MQTT/DDS 실시간 통신 시뮬레이션 브릿지."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import numpy as np


class QoSLevel(Enum):
    AT_MOST_ONCE = 0
    AT_LEAST_ONCE = 1
    EXACTLY_ONCE = 2


class Reliability(Enum):
    BEST_EFFORT = "best_effort"
    RELIABLE = "reliable"


class Durability(Enum):
    VOLATILE = "volatile"
    TRANSIENT_LOCAL = "transient_local"
    TRANSIENT = "transient"
    PERSISTENT = "persistent"


@dataclass
class MQTTConfig:
    broker_host: str = "localhost"
    broker_port: int = 1883
    keepalive: int = 60
    qos: QoSLevel = QoSLevel.AT_LEAST_ONCE
    use_tls: bool = False
    client_id: str = "sdacs_client"


@dataclass
class DDSConfig:
    domain_id: int = 0
    partition: str = "sdacs"
    reliability: Reliability = Reliability.RELIABLE
    durability: Durability = Durability.VOLATILE


class MQTTClient:
    """Simulated MQTT client."""

    def __init__(self, seed: int = 42) -> None:
        self.rng = np.random.default_rng(seed)
        self.connected = False
        self.config: Optional[MQTTConfig] = None
        self.subscriptions: Dict[str, Callable] = {}
        self._message_buffer: List[Dict[str, Any]] = []
        self.stats = {
            "msgs_sent": 0, "msgs_received": 0,
            "latency_sum_ms": 0.0, "connect_time": 0.0,
        }

    def connect(self, config: Optional[MQTTConfig] = None) -> bool:
        self.config = config or MQTTConfig()
        self.connected = True
        self.stats["connect_time"] = time.time()
        return True

    def publish(self, topic: str, payload: Any, qos: int = 1) -> bool:
        if not self.connected:
            return False
        latency = self.rng.uniform(1.0, 15.0)
        self.stats["msgs_sent"] += 1
        self.stats["latency_sum_ms"] += latency

        msg = {"topic": topic, "payload": payload, "qos": qos, "ts": time.time()}
        self._message_buffer.append(msg)

        if topic in self.subscriptions:
            self.subscriptions[topic](msg)
            self.stats["msgs_received"] += 1
        return True

    def subscribe(self, topic: str, callback: Callable) -> bool:
        if not self.connected:
            return False
        self.subscriptions[topic] = callback
        return True

    def disconnect(self) -> None:
        self.connected = False
        self.subscriptions.clear()

    def get_stats(self) -> Dict[str, Any]:
        sent = max(self.stats["msgs_sent"], 1)
        return {
            "connected": self.connected,
            "msgs_sent": self.stats["msgs_sent"],
            "msgs_received": self.stats["msgs_received"],
            "avg_latency_ms": self.stats["latency_sum_ms"] / sent,
            "subscriptions": len(self.subscriptions),
        }


class DDSParticipant:
    """Simulated DDS Domain Participant."""

    def __init__(self, config: Optional[DDSConfig] = None, seed: int = 42) -> None:
        self.rng = np.random.default_rng(seed)
        self.config = config or DDSConfig()
        self._next_id = 0
        self.writers: Dict[int, Dict[str, Any]] = {}
        self.readers: Dict[int, Dict[str, Any]] = {}
        self.stats = {
            "samples_written": 0, "samples_read": 0, "latency_sum_ms": 0.0,
        }

    def _gen_id(self) -> int:
        self._next_id += 1
        return self._next_id

    def create_writer(self, topic: str, data_type: str = "DroneState") -> int:
        wid = self._gen_id()
        self.writers[wid] = {"topic": topic, "data_type": data_type, "samples": []}
        return wid

    def create_reader(self, topic: str, callback: Callable) -> int:
        rid = self._gen_id()
        self.readers[rid] = {"topic": topic, "callback": callback}
        return rid

    def write(self, writer_id: int, data: Any) -> bool:
        if writer_id not in self.writers:
            return False
        w = self.writers[writer_id]
        w["samples"].append(data)
        self.stats["samples_written"] += 1
        latency = self.rng.uniform(0.5, 5.0)
        self.stats["latency_sum_ms"] += latency

        for r in self.readers.values():
            if r["topic"] == w["topic"]:
                r["callback"](data)
                self.stats["samples_read"] += 1
        return True

    def get_stats(self) -> Dict[str, Any]:
        written = max(self.stats["samples_written"], 1)
        return {
            "domain_id": self.config.domain_id,
            "writers": len(self.writers),
            "readers": len(self.readers),
            "samples_written": self.stats["samples_written"],
            "samples_read": self.stats["samples_read"],
            "avg_latency_ms": self.stats["latency_sum_ms"] / written,
        }


class MQTTDDSBridge:
    """Hybrid MQTT + DDS communication bridge."""

    def __init__(self, seed: int = 42) -> None:
        self.mqtt = MQTTClient(seed=seed)
        self.dds = DDSParticipant(seed=seed)
        self.topic_mapping: Dict[str, str] = {}

    def setup(
        self, mqtt_config: Optional[MQTTConfig] = None, dds_config: Optional[DDSConfig] = None
    ) -> bool:
        mqtt_ok = self.mqtt.connect(mqtt_config)
        if dds_config:
            self.dds = DDSParticipant(config=dds_config)
        return mqtt_ok

    def map_topic(self, mqtt_topic: str, dds_topic: str) -> None:
        self.topic_mapping[mqtt_topic] = dds_topic

    def publish_hybrid(self, topic: str, data: Any) -> Dict[str, bool]:
        mqtt_ok = self.mqtt.publish(topic, data)
        dds_topic = self.topic_mapping.get(topic, topic)
        wid = self.dds.create_writer(dds_topic)
        dds_ok = self.dds.write(wid, data)
        return {"mqtt": mqtt_ok, "dds": dds_ok}

    def get_combined_stats(self) -> Dict[str, Any]:
        return {
            "mqtt": self.mqtt.get_stats(),
            "dds": self.dds.get_stats(),
            "topic_mappings": len(self.topic_mapping),
        }
