"""TRANSCENDENCE Phase 246 — 부하 하니스 계획·집계 결정성 회귀."""

from __future__ import annotations

import pytest

from simulation.ws_load_harness import LoadReport, build_plan, summarize


class TestBuildPlan:
    def test_default_100_clients(self) -> None:
        plan = build_plan("ws://127.0.0.1:8765")
        assert len(plan.clients) == 100
        assert plan.total_messages == 100 * 10

    def test_deterministic_same_args_same_plan(self) -> None:
        p1 = build_plan("ws://x", 50, 5, 2.0)
        p2 = build_plan("ws://x", 50, 5, 2.0)
        assert p1 == p2  # frozen dataclass 동등성 — 무작위성 0

    def test_ramp_up_uniform_offsets(self) -> None:
        plan = build_plan("ws://x", n_clients=4, ramp_up_s=4.0)
        offsets = [c.start_offset_s for c in plan.clients]
        assert offsets == [0.0, 1.0, 2.0, 3.0]

    def test_client_ids_zero_padded_sorted(self) -> None:
        plan = build_plan("ws://x", n_clients=3)
        assert [c.client_id for c in plan.clients] == ["load-0000", "load-0001", "load-0002"]

    def test_invalid_args_rejected(self) -> None:
        with pytest.raises(ValueError):
            build_plan("ws://x", n_clients=0)
        with pytest.raises(ValueError):
            build_plan("ws://x", messages_per_client=-1)
        with pytest.raises(ValueError):
            build_plan("ws://x", ramp_up_s=-0.1)


class TestSummarize:
    def test_pass_requires_all_connected(self) -> None:
        plan = build_plan("ws://x", n_clients=2, messages_per_client=1)
        ok = LoadReport(connected=2, connect_failures=0, messages_sent=2)
        bad = LoadReport(connected=1, connect_failures=1, messages_sent=1)
        assert summarize(plan, ok)["pass"] is True
        assert summarize(plan, bad)["pass"] is False

    def test_latency_percentiles(self) -> None:
        plan = build_plan("ws://x", n_clients=1, messages_per_client=1)
        rep = LoadReport(connected=1, latencies_ms=[10.0, 20.0, 30.0, 40.0, 100.0])
        lat = summarize(plan, rep)["latency"]
        assert lat["count"] == 5
        assert lat["p50_ms"] == 30.0
        assert lat["max_ms"] == 100.0

    def test_empty_latency(self) -> None:
        plan = build_plan("ws://x", n_clients=1)
        assert summarize(plan, LoadReport(connected=1))["latency"] == {"count": 0}
