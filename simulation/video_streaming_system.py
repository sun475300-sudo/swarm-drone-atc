"""
Phase 461: Video Streaming System for Real-Time Surveillance
"""

import numpy as np
from typing import Dict, List
from dataclasses import dataclass
import time


@dataclass
class VideoFrame:
    frame_id: str
    drone_id: str
    timestamp: float
    resolution: tuple
    data: bytes


class VideoStreamingSystem:
    def __init__(self, max_bitrate_mbps: int = 10):
        self.max_bitrate = max_bitrate_mbps
        self.active_streams: Dict[str, List[VideoFrame]] = {}
        self.stream_quality: Dict[str, int] = {}

    def start_stream(self, drone_id: str, resolution: tuple = (1920, 1080)):
        self.active_streams[drone_id] = []
        self.stream_quality[drone_id] = 80

    def send_frame(self, drone_id: str, frame: VideoFrame):
        if drone_id in self.active_streams:
            self.active_streams[drone_id].append(frame)

    def adjust_quality(self, drone_id: str, bandwidth_percent: float):
        if drone_id in self.stream_quality:
            self.stream_quality[drone_id] = int(bandwidth_percent * 100)

    def get_stream_stats(self, drone_id: str) -> Dict:
        return {
            "active": drone_id in self.active_streams,
            "quality": self.stream_quality.get(drone_id, 0),
            "frames_sent": len(self.active_streams.get(drone_id, [])),
        }
