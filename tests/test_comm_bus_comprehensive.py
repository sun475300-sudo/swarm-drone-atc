"""
CommunicationBus 포괄적 단위 테스트
_check_range, _get_receivers, broadcast 범위 제한, 지연 모델 커버
"""
from __future__ import annotations

import numpy as np
import pytest
import simpy

from src.airspace_control.comms.communication_bus import CommunicationBus, CommMessage


@pytest.fixture
def env():
    return simpy.Environment()


@pytest.fixture
def bus(env):
    rng = np.random.default_rng(42)
    return CommunicationBus(env, rng, comm_range_m=500.0, packet_loss_rate=0.0)


class TestCheckRange:
    def test_within_range(self, bus):
        bus.update_position("A", np.array([0.0, 0.0, 0.0]))
        bus.update_position("B", np.array([100.0, 0.0, 0.0]))
        assert bus._check_range("A", "B") == True

    def test_out_of_range(self, bus):
        bus.update_position("A", np.array([0.0, 0.0, 0.0]))
        bus.update_position("B", np.array([1000.0, 0.0, 0.0]))
        assert bus._check_range("A", "B") == False

    def test_unknown_position_allowed(self, bus):
        """위치 모르면 허용"""
        assert bus._check_range("X", "Y") == True

    def test_one_unknown(self, bus):
        bus.update_position("A", np.array([0.0, 0.0, 0.0]))
        assert bus._check_range("A", "UNKNOWN") == True

    def test_exactly_at_range(self, bus):
        bus.update_position("A", np.array([0.0, 0.0, 0.0]))
        bus.update_position("B", np.array([500.0, 0.0, 0.0]))
        assert bus._check_range("A", "B") == True


class TestGetReceivers:
    def test_p2p_in_range(self, bus):
        bus.update_position("A", np.array([0.0, 0.0, 0.0]))
        bus.update_position("B", np.array([100.0, 0.0, 0.0]))
        msg = CommMessage("A", "B", "test", 0.0)
        assert bus._get_receivers(msg) == ["B"]

    def test_p2p_out_of_range(self, bus):
        bus.update_position("A", np.array([0.0, 0.0, 0.0]))
        bus.update_position("B", np.array([1000.0, 0.0, 0.0]))
        msg = CommMessage("A", "B", "test", 0.0)
        assert bus._get_receivers(msg) == []

    def test_broadcast_range_filter(self, bus):
        bus.update_position("A", np.array([0.0, 0.0, 0.0]))
        bus.update_position("B", np.array([100.0, 0.0, 0.0]))
        bus.update_position("C", np.array([1000.0, 0.0, 0.0]))
        bus.subscribe("B", lambda m: None)
        bus.subscribe("C", lambda m: None)
        msg = CommMessage("A", "BROADCAST", "test", 0.0)
        receivers = bus._get_receivers(msg)
        assert "B" in receivers
        assert "C" not in receivers

    def test_broadcast_no_sender_position(self, bus):
        """발신자 위치 모르면 모든 구독자에게 전달"""
        bus.subscribe("X", lambda m: None)
        bus.subscribe("Y", lambda m: None)
        msg = CommMessage("UNKNOWN", "BROADCAST", "test", 0.0)
        receivers = bus._get_receivers(msg)
        assert "X" in receivers and "Y" in receivers

    def test_broadcast_excludes_sender(self, bus):
        bus.update_position("A", np.array([0.0, 0.0, 0.0]))
        bus.update_position("B", np.array([100.0, 0.0, 0.0]))
        msg = CommMessage("A", "BROADCAST", "test", 0.0)
        receivers = bus._get_receivers(msg)
        assert "A" not in receivers


class TestSendAndDeliver:
    def test_delivery_with_latency(self, env, bus):
        """메시지가 지연 후 전달"""
        received = []
        bus.subscribe("B", lambda m: received.append(m))
        bus.update_position("A", np.array([0.0, 0.0, 0.0]))
        bus.update_position("B", np.array([100.0, 0.0, 0.0]))

        msg = CommMessage("A", "B", "hello", 0.0)
        bus.send(msg)
        env.run()
        assert len(received) == 1
        assert received[0].payload == "hello"

    def test_packet_loss(self, env):
        """100% 패킷 손실"""
        rng = np.random.default_rng(42)
        lossy_bus = CommunicationBus(env, rng, packet_loss_rate=1.0)
        received = []
        lossy_bus.subscribe("B", lambda m: received.append(m))

        msg = CommMessage("A", "B", "hello", 0.0)
        lossy_bus.send(msg)
        env.run()
        assert len(received) == 0
        assert lossy_bus.stats["dropped"] == 1

    def test_stats_tracking(self, env, bus):
        bus.subscribe("B", lambda m: None)
        bus.update_position("A", np.array([0.0, 0.0, 0.0]))
        bus.update_position("B", np.array([100.0, 0.0, 0.0]))

        for i in range(5):
            bus.send(CommMessage("A", "B", f"msg{i}", float(i)))
        env.run()
        assert bus.stats["sent"] == 5
        assert bus.stats["delivered"] == 5


class TestGetNeighbors:
    def test_returns_neighbors(self, bus):
        bus.update_position("A", np.array([0.0, 0.0, 0.0]))
        bus.update_position("B", np.array([100.0, 0.0, 0.0]))
        bus.update_position("C", np.array([1000.0, 0.0, 0.0]))
        neighbors = bus.get_neighbors("A")
        assert "B" in neighbors
        assert "C" not in neighbors

    def test_excludes_self(self, bus):
        bus.update_position("A", np.array([0.0, 0.0, 0.0]))
        assert "A" not in bus.get_neighbors("A")

    def test_unknown_position_returns_empty(self, bus):
        assert bus.get_neighbors("UNKNOWN") == []

    def test_custom_range(self, bus):
        bus.update_position("A", np.array([0.0, 0.0, 0.0]))
        bus.update_position("B", np.array([300.0, 0.0, 0.0]))
        assert len(bus.get_neighbors("A", range_m=200.0)) == 0
        assert len(bus.get_neighbors("A", range_m=400.0)) == 1
