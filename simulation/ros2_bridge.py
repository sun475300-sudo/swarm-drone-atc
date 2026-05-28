"""Phase 672: ROS2 메시지 브릿지 시뮬레이션."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class ROSMessage:
    topic: str
    msg_type: str
    data: dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    frame_id: str = "world"


@dataclass
class TFTransform:
    parent_frame: str
    child_frame: str
    translation: np.ndarray  # (3,)
    rotation: np.ndarray  # (4,) quaternion xyzw
    timestamp: float = field(default_factory=time.time)


# Standard drone topics
DRONE_TOPICS = {
    "/drone/pose": "geometry_msgs/PoseStamped",
    "/drone/velocity": "geometry_msgs/TwistStamped",
    "/drone/battery": "sensor_msgs/BatteryState",
    "/swarm/status": "std_msgs/String",
    "/drone/imu": "sensor_msgs/Imu",
    "/drone/gps": "sensor_msgs/NavSatFix",
}


class ROS2Bridge:
    """Simulated ROS2 topic/service bridge for testing."""

    def __init__(self, node_name: str = "sdacs_bridge", seed: int = 42) -> None:
        self.node_name = node_name
        self.rng = np.random.default_rng(seed)
        self._next_id = 0

        self.publishers: dict[int, dict[str, str]] = {}
        self.subscribers: dict[int, dict[str, Any]] = {}
        self.services: dict[str, Callable] = {}
        self.tf_buffer: dict[str, TFTransform] = {}

        self._message_queue: list[ROSMessage] = []
        self.stats = {
            "msgs_published": 0, "msgs_received": 0,
            "services_called": 0, "spin_cycles": 0,
        }

    def _gen_id(self) -> int:
        self._next_id += 1
        return self._next_id

    def create_publisher(self, topic: str, msg_type: str = "std_msgs/String") -> int:
        pub_id = self._gen_id()
        self.publishers[pub_id] = {"topic": topic, "msg_type": msg_type}
        return pub_id

    def create_subscriber(self, topic: str, callback: Callable) -> int:
        sub_id = self._gen_id()
        self.subscribers[sub_id] = {"topic": topic, "callback": callback}
        return sub_id

    def publish(self, publisher_id: int, data: dict[str, Any]) -> bool:
        if publisher_id not in self.publishers:
            return False
        pub = self.publishers[publisher_id]
        msg = ROSMessage(
            topic=pub["topic"], msg_type=pub["msg_type"],
            data=data, timestamp=time.time(),
        )
        self._message_queue.append(msg)
        self.stats["msgs_published"] += 1
        return True

    def create_service(self, name: str, callback: Callable) -> str:
        self.services[name] = callback
        return name

    def call_service(self, name: str, request: dict[str, Any]) -> dict[str, Any] | None:
        if name not in self.services:
            return None
        self.stats["services_called"] += 1
        return self.services[name](request)

    def spin_once(self) -> int:
        """Process one cycle of callbacks. Returns messages delivered."""
        delivered = 0
        pending = list(self._message_queue)
        self._message_queue.clear()

        for msg in pending:
            for sub in self.subscribers.values():
                if sub["topic"] == msg.topic:
                    sub["callback"](msg)
                    delivered += 1
                    self.stats["msgs_received"] += 1

        self.stats["spin_cycles"] += 1
        return delivered

    def set_transform(self, transform: TFTransform) -> None:
        key = f"{transform.parent_frame}->{transform.child_frame}"
        self.tf_buffer[key] = transform

    def lookup_transform(
        self, parent: str, child: str
    ) -> TFTransform | None:
        key = f"{parent}->{child}"
        return self.tf_buffer.get(key)

    def get_topic_list(self) -> list[str]:
        topics = set()
        for pub in self.publishers.values():
            topics.add(pub["topic"])
        for sub in self.subscribers.values():
            topics.add(sub["topic"])
        return sorted(topics)

    def get_node_stats(self) -> dict[str, Any]:
        return {
            "node_name": self.node_name,
            "publishers": len(self.publishers),
            "subscribers": len(self.subscribers),
            "services": len(self.services),
            "tf_frames": len(self.tf_buffer),
            **self.stats,
        }
