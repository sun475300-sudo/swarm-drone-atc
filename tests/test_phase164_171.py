"""Phase 164-171 tests: infra modules (message queue, circuit breaker)."""

import time


class TestMessageQueue:
    def setup_method(self):
        from simulation.message_queue import MessageQueue

        self.q = MessageQueue(max_size=4, max_retries=2)

    def test_publish_consume(self):
        ok = self.q.publish("telemetry", {"id": 1}, priority=3)
        assert ok
        msg = self.q.consume()
        assert msg is not None
        assert msg.topic == "telemetry"

    def test_priority_order(self):
        self.q.publish("normal", {"v": 1}, priority=5)
        self.q.publish("urgent", {"v": 2}, priority=1)
        first = self.q.consume()
        assert first is not None
        assert first.topic == "urgent"

    def test_backpressure_drop(self):
        for i in range(4):
            assert self.q.publish("t", {"i": i}, priority=5)
        assert not self.q.publish("overflow", {"i": 99}, priority=5)
        assert self.q.summary()["dropped"] == 1

    def test_nack_requeue_then_dlq(self):
        self.q.publish("task", {"k": "v"}, priority=2)
        msg = self.q.consume()
        assert msg is not None

        self.q.nack(msg)
        again = self.q.consume()
        assert again is not None
        self.q.nack(again)
        again2 = self.q.consume()
        assert again2 is not None
        self.q.nack(again2)

        assert len(self.q.dead_letters()) == 1

    def test_summary(self):
        s = self.q.summary()
        assert "max_size" in s


class TestCircuitBreaker:
    def setup_method(self):
        from simulation.circuit_breaker import CircuitBreaker

        self.cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.2, half_open_max_calls=1)

    def test_closed_initial(self):
        st = self.cb.state()
        assert st.state == "CLOSED"

    def test_open_after_failures(self):
        def fail() -> None:
            raise ValueError("boom")

        for _ in range(2):
            try:
                self.cb.execute(fail)
            except ValueError:
                pass
        assert self.cb.state().state == "OPEN"

    def test_block_when_open(self):
        self.cb.record_failure()
        self.cb.record_failure()
        try:
            self.cb.execute(lambda: 1)
            assert False
        except RuntimeError:
            assert True

    def test_half_open_recovery(self):
        self.cb.record_failure()
        self.cb.record_failure()
        time.sleep(0.25)
        out = self.cb.execute(lambda: 7)
        assert out == 7
        assert self.cb.state().state == "CLOSED"

    def test_summary(self):
        s = self.cb.summary()
        assert "failure_threshold" in s
