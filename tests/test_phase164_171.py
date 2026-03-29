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


class TestRateLimiter:
    def setup_method(self):
        from simulation.rate_limiter import RateLimiter

        self.r = RateLimiter(rate_per_sec=5.0, burst=3)

    def test_allow_within_burst(self):
        assert self.r.allow("api")
        assert self.r.allow("api")
        assert self.r.allow("api")

    def test_block_after_burst(self):
        self.r.allow("api")
        self.r.allow("api")
        self.r.allow("api")
        assert not self.r.allow("api")

    def test_key_isolation(self):
        assert self.r.allow("a")
        assert self.r.allow("b")

    def test_summary(self):
        s = self.r.summary()
        assert "rate_per_sec" in s


class TestHealthChecker:
    def setup_method(self):
        from simulation.health_checker import HealthChecker

        self.h = HealthChecker(stale_after_sec=0.2)

    def test_heartbeat_and_status(self):
        self.h.heartbeat("planner")
        st = self.h.status("planner")
        assert st["status"] in ("HEALTHY", "DEGRADED")

    def test_report_metrics(self):
        self.h.report("planner", latency_ms=10.0, success=True)
        self.h.report("planner", latency_ms=20.0, success=False)
        st = self.h.status("planner")
        assert st["avg_latency_ms"] > 0

    def test_stale_detection(self):
        import time

        self.h.heartbeat("planner")
        time.sleep(0.25)
        st = self.h.status("planner")
        assert st["status"] == "STALE"

    def test_overall(self):
        self.h.heartbeat("planner")
        ov = self.h.overall()
        assert ov["modules"] >= 1


class TestConfigHotReload:
    def test_load_and_reload_and_rollback(self, tmp_path):
        from simulation.config_hot_reload import ConfigHotReload

        config_file = tmp_path / "sim.yaml"
        config_file.write_text("a: 1\nb: test\n", encoding="utf-8")

        h = ConfigHotReload(str(config_file))
        current = h.load()
        assert current["a"] == 1

        config_file.write_text("a: 2\nb: changed\n", encoding="utf-8")
        changed = h.reload_if_changed()
        assert changed
        assert h.current()["a"] == 2

        rolled = h.rollback()
        assert rolled
        assert h.current()["a"] == 1

    def test_reload_if_not_changed(self, tmp_path):
        from simulation.config_hot_reload import ConfigHotReload

        config_file = tmp_path / "sim.yaml"
        config_file.write_text("x: 10\n", encoding="utf-8")
        h = ConfigHotReload(str(config_file))
        h.load()
        assert not h.reload_if_changed()

    def test_summary(self, tmp_path):
        from simulation.config_hot_reload import ConfigHotReload

        config_file = tmp_path / "sim.yaml"
        config_file.write_text("k: v\n", encoding="utf-8")
        h = ConfigHotReload(str(config_file))
        h.load()
        s = h.summary()
        assert s["version"] >= 1


class TestDistributedLock:
    def setup_method(self):
        from simulation.distributed_lock import DistributedLock

        self.l = DistributedLock(default_ttl_sec=0.2)

    def test_acquire_release(self):
        assert self.l.acquire("key1", "worker-a")
        assert self.l.owner_of("key1") == "worker-a"
        assert self.l.release("key1", "worker-a")
        assert self.l.owner_of("key1") is None

    def test_reject_other_owner(self):
        assert self.l.acquire("key1", "worker-a")
        assert not self.l.acquire("key1", "worker-b")

    def test_renew(self):
        assert self.l.acquire("key1", "worker-a", ttl_sec=0.1)
        assert self.l.renew("key1", "worker-a", ttl_sec=0.5)

    def test_expire(self):
        import time

        assert self.l.acquire("key1", "worker-a", ttl_sec=0.1)
        time.sleep(0.15)
        assert self.l.owner_of("key1") is None

    def test_summary(self):
        self.l.acquire("key1", "worker-a")
        s = self.l.summary()
        assert "active_locks" in s
