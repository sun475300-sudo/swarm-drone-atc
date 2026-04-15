"""
분산 드론 통신 버스 시뮬레이터
MAVLink/DDS 통신의 지연, 패킷 손실, 재순서화를 시뮬레이션

분산 시스템 특성:
  - 드론 간 P2P 통신 (컨트롤러 우회 가능)
  - 통신 범위 기반 자동 이웃 탐색
  - 실시간 공역 상황 브로드캐스트
"""
from __future__ import annotations
import simpy
import numpy as np
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class CommMessage:
    """통신 메시지 래퍼"""
    sender_id: str
    receiver_id: str           # "BROADCAST" = 전체
    payload: object
    sent_time: float
    channel: str = "telemetry"


class CommunicationBus:
    """
    분산 드론 통신 버스

    기능:
      - send(msg): 메시지 발송 (지연/손실 적용)
      - subscribe(drone_id, callback): 수신 콜백 등록
      - get_neighbors(pos, range): 통신 범위 내 드론 조회
    """

    def __init__(
        self,
        env: simpy.Environment,
        rng: np.random.Generator,
        latency_ms_mean: float = 20.0,    # 평균 지연 (ms)
        latency_ms_std: float = 5.0,      # 지연 표준편차
        packet_loss_rate: float = 0.0,    # 패킷 손실률 [0, 1]
        comm_range_m: float = 2000.0,     # 통신 범위 (m)
    ):
        self.env = env
        self.rng = rng
        self.latency_ms_mean = latency_ms_mean
        self.latency_ms_std = latency_ms_std
        self.packet_loss_rate = packet_loss_rate
        self.comm_range_m = comm_range_m

        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._positions: dict[str, np.ndarray] = {}  # 최신 드론 위치
        self._message_log: deque = deque(maxlen=10000)
        self.stats = {"sent": 0, "delivered": 0, "dropped": 0}

    def update_position(self, drone_id: str, position: np.ndarray):
        """드론 위치 업데이트 (통신 범위 계산용)"""
        self._positions[drone_id] = position

    def subscribe(self, drone_id: str, callback: Callable):
        """메시지 수신 콜백 등록"""
        self._subscribers[drone_id].append(callback)

    def send(self, msg: CommMessage):
        """메시지 발송 (비동기, SimPy 프로세스로 지연 처리)"""
        self.stats["sent"] += 1

        # 패킷 손실
        if self.rng.random() < self.packet_loss_rate:
            self.stats["dropped"] += 1
            return

        self.env.process(self._deliver(msg))

    def _deliver(self, msg: CommMessage):
        """지연 후 메시지 전달 (SimPy 제너레이터)"""
        delay_s = max(0, self.rng.normal(
            self.latency_ms_mean, self.latency_ms_std
        )) / 1000.0
        yield self.env.timeout(delay_s)

        receivers = self._get_receivers(msg)
        for receiver_id in receivers:
            if receiver_id in self._subscribers:
                for callback in self._subscribers[receiver_id]:
                    callback(msg)
                self.stats["delivered"] += 1

        self._message_log.append(msg)

    def _get_receivers(self, msg: CommMessage) -> list[str]:
        """수신자 목록 결정 (BROADCAST = 범위 내 모든 드론)"""
        if msg.receiver_id != "BROADCAST":
            # 점대점: 통신 범위 확인
            if self._check_range(msg.sender_id, msg.receiver_id):
                return [msg.receiver_id]
            return []

        # 브로드캐스트: 통신 범위 내 모든 드론
        sender_pos = self._positions.get(msg.sender_id)
        if sender_pos is None:
            return list(self._subscribers.keys())

        receivers = []
        for did, pos in self._positions.items():
            if did == msg.sender_id:
                continue
            dist = np.linalg.norm(sender_pos - pos)
            if dist <= self.comm_range_m:
                receivers.append(did)
        return receivers

    def _check_range(self, id_a: str, id_b: str) -> bool:
        """두 드론이 통신 범위 내에 있는지 확인"""
        pos_a = self._positions.get(id_a)
        pos_b = self._positions.get(id_b)
        if pos_a is None or pos_b is None:
            return True  # 위치 모르면 허용
        dist = np.linalg.norm(pos_a - pos_b)
        return bool(dist <= self.comm_range_m)

    def get_neighbors(
        self, drone_id: str, range_m: Optional[float] = None
    ) -> list[str]:
        """통신 범위 내 이웃 드론 ID 목록"""
        r = range_m or self.comm_range_m
        pos = self._positions.get(drone_id)
        if pos is None:
            return []
        neighbors = []
        for did, p in self._positions.items():
            if did == drone_id:
                continue
            if np.linalg.norm(pos - p) <= r:
                neighbors.append(did)
        return neighbors
