"""CommunicationBus 테스트"""
import numpy as np
import simpy
import pytest
from src.airspace_control.comms.communication_bus import CommunicationBus, CommMessage


@pytest.fixture
def bus():
    env = simpy.Environment()
    rng = np.random.default_rng(42)
    return CommunicationBus(env=env, rng=rng)


class TestCommunicationBus:
    def test_subscribe_and_deliver(self, bus):
        """send()는 SimPy process로 전달 — env.run() 필요"""
        received = []
        bus.subscribe("DR001", lambda msg: received.append(msg))
        # sender 위치 등록 필요 없음 (위치 모르면 허용)
        msg = CommMessage(sender_id="CTRL", receiver_id="DR001",
                          payload="hello", sent_time=0.0)
        bus.send(msg)
        bus.env.run(until=1.0)  # 전달 대기
        assert len(received) == 1
        assert received[0].payload == "hello"

    def test_packet_loss(self):
        env = simpy.Environment()
        rng = np.random.default_rng(42)
        bus = CommunicationBus(env=env, rng=rng, packet_loss_rate=1.0)
        received = []
        bus.subscribe("DR001", lambda msg: received.append(msg))
        msg = CommMessage(sender_id="CTRL", receiver_id="DR001",
                          payload="test", sent_time=0.0)
        bus.send(msg)
        bus.env.run(until=1.0)
        assert len(received) == 0
        assert bus.stats["dropped"] >= 1

    def test_update_position(self, bus):
        pos = np.array([100.0, 200.0, 50.0])
        bus.update_position("DR001", pos)
        assert "DR001" in bus._positions

    def test_get_neighbors(self, bus):
        bus.update_position("DR001", np.array([0.0, 0.0, 60.0]))
        bus.update_position("DR002", np.array([100.0, 0.0, 60.0]))
        bus.update_position("DR003", np.array([5000.0, 0.0, 60.0]))
        # get_neighbors takes drone_id, not position
        neighbors = bus.get_neighbors("DR001", range_m=500.0)
        assert "DR002" in neighbors
        assert "DR003" not in neighbors

    def test_stats_tracking(self, bus):
        bus.subscribe("DR001", lambda msg: None)
        msg = CommMessage(sender_id="CTRL", receiver_id="DR001",
                          payload="test", sent_time=0.0)
        bus.send(msg)
        bus.env.run(until=1.0)
        assert bus.stats["sent"] >= 1
        assert bus.stats["delivered"] >= 1

    def test_broadcast(self, bus):
        received_a = []
        received_b = []
        bus.subscribe("DR001", lambda msg: received_a.append(msg))
        bus.subscribe("DR002", lambda msg: received_b.append(msg))
        bus.update_position("CTRL", np.array([0, 0, 60]))
        bus.update_position("DR001", np.array([100, 0, 60]))
        bus.update_position("DR002", np.array([200, 0, 60]))
        msg = CommMessage(sender_id="CTRL", receiver_id="BROADCAST",
                          payload="alert", sent_time=0.0)
        bus.send(msg)
        bus.env.run(until=1.0)
        assert len(received_a) == 1
        assert len(received_b) == 1
