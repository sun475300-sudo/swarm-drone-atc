"""
Phase 461: Video Streaming System for Real-Time Surveillance
"""

from dataclasses import dataclass


@dataclass
class VideoFrame:
    """``VideoFrame`` 관련 기능을 제공한다."""
    frame_id: str
    drone_id: str
    timestamp: float
    resolution: tuple
    data: bytes


class VideoStreamingSystem:
    """``VideoStreamingSystem`` 역할을 담당한다."""
    def __init__(self, max_bitrate_mbps: int = 10):
        """인스턴스를 초기화한다."""
        self.max_bitrate = max_bitrate_mbps
        self.active_streams: dict[str, list[VideoFrame]] = {}
        self.stream_quality: dict[str, int] = {}

    def start_stream(self, drone_id: str, resolution: tuple = (1920, 1080)):
        """`stream` 실행 상태를 제어한다."""
        self.active_streams[drone_id] = []
        self.stream_quality[drone_id] = 80

    def send_frame(self, drone_id: str, frame: VideoFrame):
        """``send_frame`` 동작을 수행한다."""
        if drone_id in self.active_streams:
            self.active_streams[drone_id].append(frame)

    def adjust_quality(self, drone_id: str, bandwidth_percent: float):
        """``adjust_quality`` 동작을 수행한다."""
        if drone_id in self.stream_quality:
            self.stream_quality[drone_id] = int(bandwidth_percent * 100)

    def get_stream_stats(self, drone_id: str) -> dict:
        """`stream stats` 정보를 조회한다."""
        return {
            "active": drone_id in self.active_streams,
            "quality": self.stream_quality.get(drone_id, 0),
            "frames_sent": len(self.active_streams.get(drone_id, [])),
        }
