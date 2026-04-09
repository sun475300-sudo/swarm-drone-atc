"""
Phase 428: Real-Time Stream Processor for Telemetry Data
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import deque


class StreamType(Enum):
    TELEMETRY = "telemetry"
    SENSOR = "sensor"
    EVENT = "event"
    COMMAND = "command"


@dataclass
class StreamEvent:
    event_id: str
    stream_type: StreamType
    data: Dict[str, Any]
    timestamp: float
    drone_id: str


@dataclass
class ProcessingResult:
    event_id: str
    processed: bool
    output: Any
    latency_ms: float


class RealTimeStreamProcessor:
    def __init__(self, buffer_size: int = 1000, num_workers: int = 4):
        self.buffer_size = buffer_size
        self.num_workers = num_workers

        self.buffers: Dict[StreamType, deque] = {
            st: deque(maxlen=buffer_size) for st in StreamType
        }

        self.processors: Dict[StreamType, Callable] = {}
        self.windowed_aggregates: Dict[str, float] = {}

        self.metrics = {
            "events_processed": 0,
            "events_dropped": 0,
            "avg_latency_ms": 0.0,
        }

    def register_processor(self, stream_type: StreamType, processor: Callable):
        self.processors[stream_type] = processor

    def ingest(self, event: StreamEvent):
        self.buffers[event.stream_type].append(event)

    def process_stream(self, stream_type: StreamType) -> List[ProcessingResult]:
        results = []

        buffer = self.buffers[stream_type]

        while buffer:
            event = buffer.popleft()

            start_time = time.time()

            if stream_type in self.processors:
                output = self.processors[stream_type](event.data)
            else:
                output = self._default_process(event.data)

            latency = (time.time() - start_time) * 1000

            result = ProcessingResult(
                event_id=event.event_id,
                processed=True,
                output=output,
                latency_ms=latency,
            )

            results.append(result)

            self.metrics["events_processed"] += 1
            self.metrics["avg_latency_ms"] = (
                self.metrics["avg_latency_ms"] * 0.99 + latency * 0.01
            )

        return results

    def _default_process(self, data: Dict) -> Dict:
        return {"status": "processed", "data": data}

    def compute_window_aggregate(self, key: str, window_sec: float = 60.0) -> float:
        now = time.time()

        total = 0.0
        count = 0

        for buffer in self.buffers.values():
            for event in buffer:
                if now - event.timestamp <= window_sec:
                    total += event.data.get(key, 0)
                    count += 1

        return total / count if count > 0 else 0.0

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "events_processed": self.metrics["events_processed"],
            "events_dropped": self.metrics["events_dropped"],
            "avg_latency_ms": self.metrics["avg_latency_ms"],
            "buffer_sizes": {st.value: len(buf) for st, buf in self.buffers.items()},
        }
