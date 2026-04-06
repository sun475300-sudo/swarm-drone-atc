"""
Phase 661: BurnySc2 패턴 기반 모듈 테스트
- Behavior Tree
- JPS Pathfinder
- Frame Cache
"""
from __future__ import annotations

import time

import numpy as np
import pytest


# ── Behavior Tree Tests ──────────────────────────────────────────────

class TestBehaviorTree:
    def test_node_status_enum(self):
        from simulation.behavior_tree import NodeStatus
        assert NodeStatus.SUCCESS.value == 1
        assert NodeStatus.FAILURE.value == 2
        assert NodeStatus.RUNNING.value == 3

    def test_sequence_all_success(self):
        from simulation.behavior_tree import SequenceNode, ActionNode, NodeStatus
        seq = SequenceNode(name="test", children=[
            ActionNode(name="a1", action=lambda ctx: NodeStatus.SUCCESS),
            ActionNode(name="a2", action=lambda ctx: NodeStatus.SUCCESS),
        ])
        assert seq.tick({}) == NodeStatus.SUCCESS

    def test_sequence_one_failure(self):
        from simulation.behavior_tree import SequenceNode, ActionNode, NodeStatus
        seq = SequenceNode(name="test", children=[
            ActionNode(name="a1", action=lambda ctx: NodeStatus.SUCCESS),
            ActionNode(name="a2", action=lambda ctx: NodeStatus.FAILURE),
        ])
        assert seq.tick({}) == NodeStatus.FAILURE

    def test_sequence_running(self):
        from simulation.behavior_tree import SequenceNode, ActionNode, NodeStatus
        seq = SequenceNode(name="test", children=[
            ActionNode(name="a1", action=lambda ctx: NodeStatus.RUNNING),
        ])
        assert seq.tick({}) == NodeStatus.RUNNING

    def test_selector_first_success(self):
        from simulation.behavior_tree import SelectorNode, ActionNode, NodeStatus
        sel = SelectorNode(name="test", children=[
            ActionNode(name="a1", action=lambda ctx: NodeStatus.FAILURE),
            ActionNode(name="a2", action=lambda ctx: NodeStatus.SUCCESS),
        ])
        assert sel.tick({}) == NodeStatus.SUCCESS

    def test_selector_all_failure(self):
        from simulation.behavior_tree import SelectorNode, ActionNode, NodeStatus
        sel = SelectorNode(name="test", children=[
            ActionNode(name="a1", action=lambda ctx: NodeStatus.FAILURE),
            ActionNode(name="a2", action=lambda ctx: NodeStatus.FAILURE),
        ])
        assert sel.tick({}) == NodeStatus.FAILURE

    def test_condition_node_true(self):
        from simulation.behavior_tree import ConditionNode, NodeStatus
        cond = ConditionNode(name="test", predicate=lambda ctx: ctx.get("x") > 5)
        assert cond.tick({"x": 10}) == NodeStatus.SUCCESS

    def test_condition_node_false(self):
        from simulation.behavior_tree import ConditionNode, NodeStatus
        cond = ConditionNode(name="test", predicate=lambda ctx: ctx.get("x") > 5)
        assert cond.tick({"x": 3}) == NodeStatus.FAILURE

    def test_inverter_node(self):
        from simulation.behavior_tree import InverterNode, ActionNode, NodeStatus
        inv = InverterNode(name="test", child=ActionNode(name="a", action=lambda ctx: NodeStatus.SUCCESS))
        assert inv.tick({}) == NodeStatus.FAILURE
        inv2 = InverterNode(name="test2", child=ActionNode(name="b", action=lambda ctx: NodeStatus.FAILURE))
        assert inv2.tick({}) == NodeStatus.SUCCESS

    def test_repeat_until_success(self):
        from simulation.behavior_tree import RepeatUntilSuccess, ActionNode, NodeStatus
        counter = {"n": 0}
        def counting_action(ctx):
            counter["n"] += 1
            return NodeStatus.SUCCESS if counter["n"] >= 3 else NodeStatus.FAILURE
        node = RepeatUntilSuccess(name="test", child=ActionNode(name="a", action=counting_action), max_repeats=5)
        assert node.tick({}) == NodeStatus.SUCCESS
        assert counter["n"] == 3

    def test_drone_flight_bt_emergency(self):
        from simulation.behavior_tree import build_drone_flight_bt, NodeStatus
        bt = build_drone_flight_bt()
        ctx = {"battery_pct": 3.0, "battery_critical": 5.0}
        bt.tick(ctx)
        assert ctx.get("command") == "EMERGENCY_LAND"

    def test_drone_flight_bt_comms_lost(self):
        from simulation.behavior_tree import build_drone_flight_bt
        bt = build_drone_flight_bt()
        ctx = {"battery_pct": 80.0, "comms_lost": True}
        bt.tick(ctx)
        assert ctx.get("command") == "RTL"

    def test_drone_flight_bt_conflict_advisory(self):
        from simulation.behavior_tree import build_drone_flight_bt
        bt = build_drone_flight_bt()
        ctx = {"battery_pct": 80.0, "conflict_detected": True, "advisory": "CLIMB"}
        bt.tick(ctx)
        assert ctx.get("command") == "EXECUTE_CLIMB"

    def test_drone_flight_bt_conflict_no_advisory(self):
        from simulation.behavior_tree import build_drone_flight_bt
        bt = build_drone_flight_bt()
        ctx = {"battery_pct": 80.0, "conflict_detected": True}
        bt.tick(ctx)
        assert ctx.get("command") == "EVADE_APF"

    def test_drone_flight_bt_navigate(self):
        from simulation.behavior_tree import build_drone_flight_bt
        bt = build_drone_flight_bt()
        ctx = {"battery_pct": 80.0, "distance_to_waypoint": 200.0}
        bt.tick(ctx)
        assert ctx.get("command") == "NAVIGATE"

    def test_drone_conditions(self):
        from simulation.behavior_tree import (
            is_battery_low, is_battery_warning, has_conflict,
            is_comms_lost, is_wind_strong, is_at_waypoint,
        )
        assert is_battery_low({"battery_pct": 3.0}) is True
        assert is_battery_low({"battery_pct": 50.0}) is False
        assert is_battery_warning({"battery_pct": 15.0}) is True
        assert has_conflict({"conflict_detected": True}) is True
        assert is_comms_lost({"comms_lost": True}) is True
        assert is_wind_strong({"wind_speed": 15.0}) is True
        assert is_at_waypoint({"distance_to_waypoint": 50.0, "waypoint_tol": 80.0}) is True


# ── JPS Pathfinder Tests ─────────────────────────────────────────────

class TestJPSPathfinder:
    def test_simple_2d_path(self):
        from simulation.jps_pathfinder import jps_search_2d
        grid = np.ones((10, 10), dtype=int)
        path = jps_search_2d((0, 0), (9, 9), grid, wall_value=0)
        assert path is not None
        assert path[0] == (0, 0)
        assert path[-1] == (9, 9)

    def test_2d_no_path(self):
        from simulation.jps_pathfinder import jps_search_2d
        grid = np.ones((5, 5), dtype=int)
        grid[2, :] = 0  # 벽으로 완전 차단
        path = jps_search_2d((0, 0), (4, 4), grid, wall_value=0)
        assert path is None

    def test_2d_with_obstacles(self):
        from simulation.jps_pathfinder import jps_search_2d
        grid = np.ones((10, 10), dtype=int)
        grid[3, 1:8] = 0  # 장애물
        grid[6, 3:10] = 0  # 장애물
        path = jps_search_2d((0, 0), (9, 9), grid, wall_value=0)
        assert path is not None
        assert path[0] == (0, 0)
        assert path[-1] == (9, 9)
        for p in path:
            assert grid[p] != 0

    def test_2d_start_equals_goal(self):
        from simulation.jps_pathfinder import jps_search_2d
        grid = np.ones((5, 5), dtype=int)
        path = jps_search_2d((2, 2), (2, 2), grid, wall_value=0)
        assert path is not None
        assert len(path) == 1

    def test_3d_simple_path(self):
        from simulation.jps_pathfinder import jps_search_3d
        grid = np.ones((5, 5, 5), dtype=int)
        path = jps_search_3d((0, 0, 0), (4, 4, 4), grid, wall_value=0)
        assert path is not None
        assert path[0] == (0, 0, 0)
        assert path[-1] == (4, 4, 4)

    def test_3d_no_path(self):
        from simulation.jps_pathfinder import jps_search_3d
        grid = np.ones((5, 5, 5), dtype=int)
        grid[2, :, :] = 0  # 벽
        path = jps_search_3d((0, 0, 0), (4, 4, 4), grid, wall_value=0)
        assert path is None

    def test_3d_with_obstacle(self):
        from simulation.jps_pathfinder import jps_search_3d
        grid = np.ones((8, 8, 8), dtype=int)
        grid[3, 2:6, 2:6] = 0  # 장애물 블록
        path = jps_search_3d((0, 0, 0), (7, 7, 7), grid, wall_value=0)
        assert path is not None
        for p in path:
            assert grid[p] != 0

    def test_heuristic(self):
        from simulation.jps_pathfinder import _heuristic_euclidean
        assert _heuristic_euclidean((0, 0, 0), (3, 4, 0)) == pytest.approx(5.0)
        assert _heuristic_euclidean((0, 0), (3, 4)) == pytest.approx(5.0)


# ── Frame Cache Tests ────────────────────────────────────────────────

class TestTickCache:
    def test_same_tick_cached(self):
        from simulation.frame_cache import TickCache
        cache = TickCache()
        calls = {"n": 0}
        def compute():
            calls["n"] += 1
            return 42
        v1 = cache.get_or_compute("key", tick=1, compute_fn=compute)
        v2 = cache.get_or_compute("key", tick=1, compute_fn=compute)
        assert v1 == 42
        assert v2 == 42
        assert calls["n"] == 1  # 한 번만 계산

    def test_different_tick_invalidates(self):
        from simulation.frame_cache import TickCache
        cache = TickCache()
        calls = {"n": 0}
        def compute():
            calls["n"] += 1
            return calls["n"]
        v1 = cache.get_or_compute("key", tick=1, compute_fn=compute)
        v2 = cache.get_or_compute("key", tick=2, compute_fn=compute)
        assert v1 == 1
        assert v2 == 2

    def test_invalidate(self):
        from simulation.frame_cache import TickCache
        cache = TickCache()
        cache.get_or_compute("key", tick=1, compute_fn=lambda: 10)
        cache.invalidate()
        assert len(cache) == 0


class TestExpiringCache:
    def test_set_get(self):
        from simulation.frame_cache import ExpiringCache
        cache = ExpiringCache(ttl_seconds=10.0)
        cache.set("a", 42)
        assert cache.get("a") == 42
        assert "a" in cache

    def test_expired_item(self):
        from simulation.frame_cache import ExpiringCache
        cache = ExpiringCache(ttl_seconds=0.01)
        cache.set("a", 42)
        time.sleep(0.02)
        assert cache.get("a") is None
        assert "a" not in cache

    def test_len_excludes_expired(self):
        from simulation.frame_cache import ExpiringCache
        cache = ExpiringCache(ttl_seconds=0.01)
        cache.set("a", 1)
        cache.set("b", 2)
        time.sleep(0.02)
        assert len(cache) == 0

    def test_clear(self):
        from simulation.frame_cache import ExpiringCache
        cache = ExpiringCache(ttl_seconds=10.0)
        cache.set("a", 1)
        cache.clear()
        assert len(cache) == 0


class TestCachePerTickDecorator:
    def test_caches_within_tick(self):
        from simulation.frame_cache import cache_per_tick
        class MyObj:
            _sim_tick = 1
            call_count = 0
            @cache_per_tick()
            def compute(self):
                self.call_count += 1
                return self.call_count
        obj = MyObj()
        assert obj.compute() == 1
        assert obj.compute() == 1  # 캐시됨
        assert obj.call_count == 1

    def test_invalidates_on_new_tick(self):
        from simulation.frame_cache import cache_per_tick
        class MyObj:
            _sim_tick = 1
            call_count = 0
            @cache_per_tick()
            def compute(self):
                self.call_count += 1
                return self.call_count
        obj = MyObj()
        assert obj.compute() == 1
        obj._sim_tick = 2
        assert obj.compute() == 2
