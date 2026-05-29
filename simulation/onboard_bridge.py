"""P692: SimPy 환경용 온보드 컴패니언 컴퓨터 브릿지.

src/hardware/onboard_bridge.py의 실기 하드웨어 구현과 달리,
이 모듈은 SimPy 이산 이벤트 시뮬레이션 내에서 동작.
MAVLink UART↔UDP 메시지 라우팅을 SimPy 프로세스로 모델링.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generator

try:
    import simpy  # type: ignore[import]
except ImportError:
    simpy = None  # type: ignore[assignment]


class LinkType(Enum):
    UART = "UART"       # SITL ↔ Jetson 직렬 링크
    UDP = "UDP"         # 지상국 ↔ Jetson UDP
    TCP = "TCP"         # 데이터 수집 서버


@dataclass
class MAVLinkMsg:
    """경량 MAVLink 메시지 표현 (시뮬레이션용)."""
    msg_id: int
    seq: int
    system_id: int
    component_id: int
    payload: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"MAVLinkMsg(id={self.msg_id}, sys={self.system_id}, seq={self.seq})"


@dataclass
class BridgeStats:
    uart_rx: int = 0
    uart_tx: int = 0
    udp_rx: int = 0
    udp_tx: int = 0
    dropped: int = 0


class OnboardBridgeSim:
    """SimPy 내 Jetson Orin Nano 온보드 브릿지 시뮬레이션.

    UART(비행 컨트롤러) ↔ UDP(지상국) 양방향 라우팅.
    실기 하드웨어 없이 메시지 흐름·지연·손실을 모델링.
    """

    def __init__(self, env: Any, drone_id: str, uart_latency_ms: float = 2.0,
                 udp_latency_ms: float = 5.0, packet_loss_rate: float = 0.0) -> None:
        if simpy is None:
            raise RuntimeError("simpy가 설치되어 있지 않습니다. pip install simpy")
        self.env = env
        self.drone_id = drone_id
        self.uart_latency = uart_latency_ms / 1000.0
        self.udp_latency = udp_latency_ms / 1000.0
        self.packet_loss_rate = packet_loss_rate

        self._uart_queue: Any = simpy.Store(env)
        self._udp_queue: Any = simpy.Store(env)
        self._stats = BridgeStats()
        self._output_callbacks: list[Any] = []

    @property
    def stats(self) -> BridgeStats:
        return self._stats

    def send_uart(self, msg: MAVLinkMsg) -> None:
        """UART 채널(비행 컨트롤러 방향)로 메시지 전송."""
        self._uart_queue.put(msg)
        self._stats.uart_tx += 1

    def send_udp(self, msg: MAVLinkMsg) -> None:
        """UDP 채널(지상국 방향)로 메시지 전송."""
        self._udp_queue.put(msg)
        self._stats.udp_tx += 1

    def register_output_callback(self, fn: Any) -> None:
        """라우팅된 메시지 수신 콜백."""
        self._output_callbacks.append(fn)

    def uart_router(self) -> Generator:
        """SimPy 프로세스: UART 수신 메시지를 UDP로 라우팅."""
        while True:
            msg = yield self._uart_queue.get()
            self._stats.uart_rx += 1
            yield self.env.timeout(self.uart_latency)
            for cb in self._output_callbacks:
                cb("uart→udp", msg)
            self._stats.udp_tx += 1

    def udp_router(self) -> Generator:
        """SimPy 프로세스: UDP 수신 메시지를 UART로 라우팅."""
        while True:
            msg = yield self._udp_queue.get()
            self._stats.udp_rx += 1
            yield self.env.timeout(self.udp_latency)
            for cb in self._output_callbacks:
                cb("udp→uart", msg)
            self._stats.uart_tx += 1

    def start(self) -> None:
        """SimPy 라우터 프로세스 시작."""
        self.env.process(self.uart_router())
        self.env.process(self.udp_router())
