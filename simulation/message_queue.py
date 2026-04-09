"""
Message queue infrastructure.
=============================
Priority queue with bounded capacity, backpressure, retry, and dead-letter queue.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import heapq


@dataclass(order=True)
class QueueMessage:
    priority: int
    seq: int
    topic: str = field(compare=False)
    payload: dict[str, Any] = field(compare=False)
    retries: int = field(default=0, compare=False)


class MessageQueue:
    def __init__(self, max_size: int = 1000, max_retries: int = 3) -> None:
        self.max_size = max(1, max_size)
        self.max_retries = max(0, max_retries)
        self._seq = 0
        self._queue: list[QueueMessage] = []
        self._dlq: list[QueueMessage] = []
        self._published = 0
        self._consumed = 0
        self._requeued = 0
        self._dropped = 0

    def publish(self, topic: str, payload: dict[str, Any], priority: int = 5) -> bool:
        if len(self._queue) >= self.max_size:
            self._dropped += 1
            return False
        msg = QueueMessage(priority=int(priority), seq=self._seq, topic=topic, payload=dict(payload))
        self._seq += 1
        heapq.heappush(self._queue, msg)
        self._published += 1
        return True

    def consume(self) -> QueueMessage | None:
        if not self._queue:
            return None
        msg = heapq.heappop(self._queue)
        self._consumed += 1
        return msg

    def ack(self, _msg: QueueMessage) -> None:
        return None

    def nack(self, msg: QueueMessage) -> None:
        msg.retries += 1
        if msg.retries > self.max_retries:
            self._dlq.append(msg)
            return
        heapq.heappush(self._queue, msg)
        self._requeued += 1

    def dead_letters(self) -> list[QueueMessage]:
        return list(self._dlq)

    def size(self) -> int:
        return len(self._queue)

    def summary(self) -> dict[str, Any]:
        return {
            "size": self.size(),
            "published": self._published,
            "consumed": self._consumed,
            "requeued": self._requeued,
            "dead_letters": len(self._dlq),
            "dropped": self._dropped,
            "max_size": self.max_size,
        }
