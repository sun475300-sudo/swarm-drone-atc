"""
Phase 76-91 테스트
- 자동 스케일링 (AutoScaler)
- 경로 캐시 (PathCache)
- 공역 예약 (AirspaceReservation)
- 드론 인증 (DroneRegistry)
- 다중 목표 최적화 (MultiObjectiveOptimizer)
- 이벤트 버스 (EventBus)
- 공역 히트맵 (AirspaceHeatmap)
- 드론 그룹 (DroneGroupManager)
- 충돌 포렌식 (CollisionForensics)
- 기상 위험 구역 (WeatherHazardZone)
- 에너지 예산 (EnergyBudget)
- 네트워크 토폴로지 (NetworkTopology)
- 임무 큐 (MissionQueue)
- 비행 복도 (FlightCorridorManager)
- 센서 퓨전 (SensorFusion)
- 벤치마크 (BenchmarkSuite)
"""
import pytest
import numpy as np


# ──────────────────────────────────────────────
# Phase 76: 자동 스케일링
# ──────────────────────────────────────────────
class TestAutoScaler:
    def _make(self):
        from simulation.auto_scaler import AutoScaler
        return AutoScaler(min_drones=10, max_drones=100)

    def test_initial_count(self):
        s = self._make()
        assert s.current_count == 10

    def test_scale_up(self):
        s = self._make()
        s.update_demand(50, t=0)
        d = s.evaluate(t=100)
        from simulation.auto_scaler import ScaleAction
        assert d.action == ScaleAction.SCALE_UP

    def test_scale_down(self):
        s = self._make()
        s.set_count(50)
        s.update_demand(5, t=0)
        d = s.evaluate(t=100)
        from simulation.auto_scaler import ScaleAction
        assert d.action == ScaleAction.SCALE_DOWN

    def test_cooldown(self):
        s = self._make()
        s.update_demand(50, t=0)
        s.evaluate(t=0)
        s.update_demand(90, t=5)
        d = s.evaluate(t=5)
        from simulation.auto_scaler import ScaleAction
        assert d.action == ScaleAction.NONE

    def test_predict_demand(self):
        s = self._make()
        for i in range(10):
            s.update_demand(10 + i * 5, t=float(i))
        pred = s.predict_demand(60)
        assert pred > 50

    def test_summary(self):
        s = self._make()
        assert "current_count" in s.summary()


# ──────────────────────────────────────────────
# Phase 77: 경로 캐시
# ──────────────────────────────────────────────
class TestPathCache:
    def _make(self):
        from simulation.path_cache import PathCache
        return PathCache(max_size=5)

    def test_put_get(self):
        pc = self._make()
        path = [(0, 0, 50), (100, 100, 50)]
        pc.put("key1", path)
        assert pc.get("key1") == path

    def test_miss(self):
        pc = self._make()
        assert pc.get("nonexistent") is None

    def test_lru_eviction(self):
        pc = self._make()
        for i in range(6):
            pc.put(f"k{i}", [(i, 0, 0)])
        assert pc.get("k0") is None  # evicted
        assert pc.get("k5") is not None

    def test_hit_rate(self):
        pc = self._make()
        pc.put("k1", [(0, 0, 0)])
        pc.get("k1")
        pc.get("k2")  # miss
        assert pc.hit_rate() == 0.5

    def test_invalidate(self):
        pc = self._make()
        pc.put("k1", [(0, 0, 0)])
        assert pc.invalidate("k1") is True
        assert pc.get("k1") is None

    def test_by_positions(self):
        pc = self._make()
        path = [(0, 0, 50), (100, 100, 50)]
        pc.put_by_positions((0, 0, 50), (100, 100, 50), path)
        assert pc.get_by_positions((0, 0, 50), (100, 100, 50)) is not None

    def test_summary(self):
        pc = self._make()
        s = pc.summary()
        assert "hit_rate" in s


# ──────────────────────────────────────────────
# Phase 78: 공역 예약
# ──────────────────────────────────────────────
class TestAirspaceReservation:
    def _make(self):
        from simulation.airspace_reservation import AirspaceReservation
        return AirspaceReservation()

    def test_reserve(self):
        ar = self._make()
        rid = ar.reserve("d1", (1, 1), 0, 60)
        assert rid is not None

    def test_conflict_detection(self):
        ar = self._make()
        ar.reserve("d1", (1, 1), 0, 60)
        conflicts = ar.check_conflicts("d2", (1, 1), 30, 90)
        assert len(conflicts) == 1

    def test_no_conflict_different_sector(self):
        ar = self._make()
        ar.reserve("d1", (1, 1), 0, 60)
        conflicts = ar.check_conflicts("d2", (2, 2), 0, 60)
        assert len(conflicts) == 0

    def test_cancel(self):
        ar = self._make()
        rid = ar.reserve("d1", (1, 1), 0, 60)
        assert ar.cancel(rid) is True

    def test_priority_preemption(self):
        ar = self._make()
        ar.reserve("d1", (1, 1), 0, 60, priority=3)
        rid = ar.reserve("d2", (1, 1), 0, 60, priority=1)
        assert rid is not None  # higher priority preempts

    def test_cleanup_expired(self):
        ar = self._make()
        ar.reserve("d1", (1, 1), 0, 60)
        removed = ar.cleanup_expired(100)
        assert removed >= 1

    def test_summary(self):
        ar = self._make()
        ar.reserve("d1", (1, 1), 0, 60)
        s = ar.summary()
        assert s["active_reservations"] >= 1


# ──────────────────────────────────────────────
# Phase 79: 드론 인증 관리
# ──────────────────────────────────────────────
class TestDroneRegistry:
    def _make(self):
        from simulation.drone_registry import DroneRegistry
        return DroneRegistry()

    def test_register(self):
        reg = self._make()
        r = reg.register("d1", owner="pilot_A")
        assert r.drone_id == "d1"
        assert reg.is_registered("d1")

    def test_authorize_active(self):
        reg = self._make()
        reg.register("d1")
        assert reg.authorize_flight("d1") is True

    def test_authorize_unregistered(self):
        reg = self._make()
        assert reg.authorize_flight("d_unknown") is False

    def test_suspend(self):
        reg = self._make()
        reg.register("d1")
        reg.suspend("d1")
        assert reg.authorize_flight("d1") is False

    def test_blacklist(self):
        reg = self._make()
        reg.register("d1")
        reg.blacklist("d1")
        assert reg.authorize_flight("d1") is False

    def test_reinstate(self):
        reg = self._make()
        reg.register("d1")
        reg.suspend("d1")
        reg.reinstate("d1")
        assert reg.authorize_flight("d1") is True

    def test_violations_auto_suspend(self):
        reg = self._make()
        reg.register("d1")
        for _ in range(5):
            reg.add_violation("d1")
        assert reg.authorize_flight("d1") is False

    def test_summary(self):
        reg = self._make()
        reg.register("d1")
        s = reg.summary()
        assert s["total_registered"] == 1


# ──────────────────────────────────────────────
# Phase 80: 다중 목표 최적화
# ──────────────────────────────────────────────
class TestMultiObjectiveOptimizer:
    def _make(self):
        from simulation.multi_objective import MultiObjectiveOptimizer
        return MultiObjectiveOptimizer()

    def test_add_and_pareto(self):
        moo = self._make()
        moo.add_solution("A", energy=10, time=100)
        moo.add_solution("B", energy=20, time=50)
        moo.add_solution("C", energy=30, time=120)  # dominated by B
        front = moo.pareto_front()
        ids = [s.solution_id for s in front]
        assert "A" in ids
        assert "B" in ids
        assert "C" not in ids

    def test_best_compromise(self):
        moo = self._make()
        moo.add_solution("A", energy=10, time=100)
        moo.add_solution("B", energy=50, time=20)
        best = moo.best_compromise(weights={"energy": 1, "time": 1})
        assert best is not None

    def test_dominates(self):
        moo = self._make()
        a = moo.add_solution("A", energy=10, time=50)
        b = moo.add_solution("B", energy=20, time=100)
        assert moo.dominates(a, b)
        assert not moo.dominates(b, a)

    def test_normalize(self):
        moo = self._make()
        moo.add_solution("A", energy=10, time=100)
        moo.add_solution("B", energy=50, time=20)
        norm = moo.normalize()
        assert len(norm) == 2

    def test_summary(self):
        moo = self._make()
        moo.add_solution("A", energy=10)
        s = moo.summary()
        assert s["total_solutions"] == 1


# ──────────────────────────────────────────────
# Phase 81: 이벤트 버스
# ──────────────────────────────────────────────
class TestEventBus:
    def _make(self):
        from simulation.event_bus import EventBus
        return EventBus()

    def test_publish_subscribe(self):
        bus = self._make()
        received = []
        bus.subscribe("TEST", lambda e: received.append(e))
        bus.publish("TEST", {"val": 1})
        assert len(received) == 1

    def test_subscribe_all(self):
        bus = self._make()
        received = []
        bus.subscribe_all(lambda e: received.append(e))
        bus.publish("A", {})
        bus.publish("B", {})
        assert len(received) == 2

    def test_query_by_type(self):
        bus = self._make()
        bus.publish("A", {}, t=1.0)
        bus.publish("B", {}, t=2.0)
        result = bus.query(event_type="A")
        assert len(result) == 1

    def test_query_by_time(self):
        bus = self._make()
        bus.publish("A", {}, t=1.0)
        bus.publish("A", {}, t=10.0)
        result = bus.query(t_start=5.0)
        assert len(result) == 1

    def test_unsubscribe(self):
        bus = self._make()
        handler = lambda e: None
        bus.subscribe("X", handler)
        assert bus.unsubscribe("X", handler) is True

    def test_summary(self):
        bus = self._make()
        bus.publish("A", {})
        s = bus.summary()
        assert s["published"] == 1


# ──────────────────────────────────────────────
# Phase 82: 공역 히트맵
# ──────────────────────────────────────────────
class TestAirspaceHeatmap:
    def _make(self):
        from simulation.airspace_heatmap import AirspaceHeatmap
        return AirspaceHeatmap(bounds=(0, 0, 1000, 1000), resolution=100)

    def test_record_and_heatmap(self):
        hm = self._make()
        hm.record({"d1": (150, 150, 50)}, t=1.0)
        assert hm.current_heatmap().sum() == 1

    def test_peak_density(self):
        hm = self._make()
        hm.record({f"d{i}": (150, 150, 50) for i in range(5)}, t=1.0)
        assert hm.peak_density() == 5

    def test_hotspot_detection(self):
        hm = self._make()
        hm.record({f"d{i}": (150, 150, 50) for i in range(5)}, t=1.0)
        hot = hm.hotspots(threshold=3)
        assert len(hot) >= 1

    def test_average_heatmap(self):
        hm = self._make()
        hm.record({"d1": (150, 150, 50)}, t=1.0)
        hm.record({"d1": (150, 150, 50), "d2": (150, 150, 50)}, t=2.0)
        avg = hm.average_heatmap()
        assert avg.max() > 0

    def test_predict_density(self):
        hm = self._make()
        for t in range(5):
            hm.record({f"d{i}": (150, 150, 50) for i in range(t + 1)}, t=float(t))
        pred = hm.predict_density(1, 1, steps_ahead=3)
        assert pred >= 0

    def test_summary(self):
        hm = self._make()
        s = hm.summary()
        assert "grid_size" in s


# ──────────────────────────────────────────────
# Phase 83: 드론 그룹
# ──────────────────────────────────────────────
class TestDroneGroupManager:
    def _make(self):
        from simulation.drone_group import DroneGroupManager
        return DroneGroupManager()

    def test_create_group(self):
        gm = self._make()
        g = gm.create_group("alpha", ["d1", "d2", "d3"])
        assert g.group_id == "alpha"
        assert len(g.members) == 3

    def test_dissolve_group(self):
        gm = self._make()
        gm.create_group("alpha", ["d1", "d2"])
        assert gm.dissolve_group("alpha") is True
        assert len(gm.active_groups()) == 0

    def test_add_remove_member(self):
        gm = self._make()
        gm.create_group("alpha", ["d1"])
        gm.add_member("alpha", "d2")
        assert gm.group_size("alpha") == 2
        gm.remove_member("alpha", "d2")
        assert gm.group_size("alpha") == 1

    def test_set_command(self):
        gm = self._make()
        gm.create_group("alpha", ["d1"])
        assert gm.set_group_command("alpha", "RTL") is True
        assert gm.get_group("alpha").command == "RTL"

    def test_drone_to_group(self):
        gm = self._make()
        gm.create_group("alpha", ["d1", "d2"])
        assert gm.get_drone_group("d1") == "alpha"

    def test_merge_groups(self):
        gm = self._make()
        gm.create_group("a", ["d1", "d2"])
        gm.create_group("b", ["d3", "d4"])
        merged = gm.merge_groups("a", "b", "merged")
        assert merged is not None
        assert len(merged.members) == 4

    def test_summary(self):
        gm = self._make()
        gm.create_group("alpha", ["d1", "d2"])
        s = gm.summary()
        assert s["active_groups"] == 1
        assert s["total_members"] == 2


# ──────────────────────────────────────────────
# Phase 84: 충돌 포렌식
# ──────────────────────────────────────────────
class TestCollisionForensics:
    def _make(self):
        from simulation.collision_forensics import CollisionForensics
        return CollisionForensics()

    def test_record_and_analyze(self):
        cf = self._make()
        for i in range(10):
            cf.record_event("d1", (500 + i*5, 500, 50), (5, 0, 0), t=float(i))
            cf.record_event("d2", (600 - i*5, 500, 50), (-5, 0, 0), t=float(i))
        report = cf.analyze_collision("d1", "d2", collision_time=9.0)
        assert report.closing_speed > 0
        assert report.severity in ("MINOR", "MODERATE", "SEVERE")

    def test_severity_high_speed(self):
        cf = self._make()
        cf.record_event("d1", (500, 500, 50), (15, 0, 0), t=0.0)
        cf.record_event("d2", (510, 500, 50), (-15, 0, 0), t=0.0)
        report = cf.analyze_collision("d1", "d2", collision_time=0.0)
        assert report.severity == "SEVERE"

    def test_failure_cause(self):
        cf = self._make()
        cf.record_event("d1", (500, 500, 50), (5, 0, 0), t=0.0, event_type="FAILURE")
        cf.record_event("d2", (510, 500, 50), (0, 0, 0), t=0.0)
        report = cf.analyze_collision("d1", "d2", collision_time=0.0)
        assert "고장" in report.root_cause or "장애" in report.contributing_factors[0]

    def test_summary(self):
        cf = self._make()
        s = cf.summary()
        assert "total_collisions_analyzed" in s


# ──────────────────────────────────────────────
# Phase 85: 기상 위험 구역
# ──────────────────────────────────────────────
class TestWeatherHazardZone:
    def _make(self):
        from simulation.weather_hazard_zone import WeatherHazardZone
        return WeatherHazardZone()

    def test_add_zone(self):
        whz = self._make()
        z = whz.add_zone("WZ1", (500, 500), 200)
        assert z.zone_id == "WZ1"

    def test_is_safe(self):
        whz = self._make()
        whz.add_zone("WZ1", (500, 500), 200)
        assert whz.is_safe((100, 100, 50)) is True
        assert whz.is_safe((500, 500, 50)) is False

    def test_check_path(self):
        whz = self._make()
        whz.add_zone("WZ1", (500, 500), 200)
        hazards = whz.check_path((0, 500, 50), (1000, 500, 50))
        assert len(hazards) >= 1

    def test_suggest_avoidance(self):
        whz = self._make()
        whz.add_zone("WZ1", (500, 500), 200)
        avoid = whz.suggest_avoidance((400, 500, 50), (600, 500, 50))
        assert avoid is not None

    def test_zone_movement(self):
        whz = self._make()
        whz.add_zone("WZ1", (500, 500), 100, movement=(10, 0))
        whz.update_positions(dt=10.0)
        zones = whz.active_zones()
        assert zones[0].center[0] > 500

    def test_alert_drones(self):
        whz = self._make()
        whz.add_zone("WZ1", (500, 500), 200)
        alerts = whz.alert_drones({"d1": (500, 500, 50)})
        assert len(alerts) >= 1

    def test_summary(self):
        whz = self._make()
        whz.add_zone("WZ1", (500, 500), 200)
        s = whz.summary()
        assert s["active_zones"] == 1


# ──────────────────────────────────────────────
# Phase 86: 에너지 예산
# ──────────────────────────────────────────────
class TestEnergyBudget:
    def _make(self):
        from simulation.energy_budget import EnergyBudget
        return EnergyBudget()

    def test_allocate(self):
        eb = self._make()
        a = eb.allocate("d1", total_wh=80)
        assert a.total_wh == 80

    def test_consume(self):
        eb = self._make()
        eb.allocate("d1", total_wh=80)
        eb.consume("d1", 30)
        a = eb.get_account("d1")
        assert a.consumed_wh == 30
        assert a.remaining_wh == 50

    def test_critical_detection(self):
        eb = self._make()
        eb.allocate("d1", total_wh=80, reserve_pct=20)
        eb.consume("d1", 70)  # 10 Wh remaining, reserve = 16 Wh
        assert eb.check_budget("d1") is False
        assert "d1" in eb.critical_drones()

    def test_can_complete_mission(self):
        eb = self._make()
        eb.allocate("d1", total_wh=80, reserve_pct=20)
        assert eb.can_complete_mission("d1", estimated_wh=50) is True
        assert eb.can_complete_mission("d1", estimated_wh=70) is False

    def test_recharge(self):
        eb = self._make()
        eb.allocate("d1", total_wh=80)
        eb.consume("d1", 30)
        eb.recharge("d1", 20)
        assert eb.get_account("d1").consumed_wh == 10

    def test_summary(self):
        eb = self._make()
        eb.allocate("d1", total_wh=80)
        s = eb.summary()
        assert s["total_drones"] == 1


# ──────────────────────────────────────────────
# Phase 87: 네트워크 토폴로지
# ──────────────────────────────────────────────
class TestNetworkTopology:
    def _make(self):
        from simulation.network_topology import NetworkTopology
        return NetworkTopology(comm_range=200)

    def test_update_links(self):
        nt = self._make()
        nt.update_links({"d1": (0, 0, 50), "d2": (100, 0, 50), "d3": (500, 500, 50)})
        assert nt.degree("d1") == 1  # d1 connected to d2 only
        assert nt.degree("d3") == 0

    def test_connected(self):
        nt = self._make()
        nt.update_links({"d1": (0, 0, 50), "d2": (100, 0, 50)})
        assert nt.is_connected() is True

    def test_disconnected(self):
        nt = self._make()
        nt.update_links({"d1": (0, 0, 50), "d2": (500, 500, 50)})
        assert nt.is_connected() is False

    def test_components(self):
        nt = self._make()
        nt.update_links({"d1": (0, 0, 50), "d2": (100, 0, 50), "d3": (500, 500, 50)})
        assert len(nt.connected_components()) == 2

    def test_most_central(self):
        nt = self._make()
        nt.update_links({
            "d1": (0, 0, 50), "d2": (100, 0, 50),
            "d3": (50, 50, 50), "d4": (200, 200, 50),
        })
        central = nt.most_central(top_n=1)
        assert len(central) == 1

    def test_density(self):
        nt = self._make()
        nt.update_links({"d1": (0, 0, 50), "d2": (50, 0, 50), "d3": (100, 0, 50)})
        assert nt.density() > 0

    def test_summary(self):
        nt = self._make()
        nt.update_links({"d1": (0, 0, 50), "d2": (100, 0, 50)})
        s = nt.summary()
        assert s["nodes"] == 2


# ──────────────────────────────────────────────
# Phase 88: 임무 큐
# ──────────────────────────────────────────────
class TestMissionQueue:
    def _make(self):
        from simulation.mission_queue import MissionQueue
        return MissionQueue()

    def test_enqueue_dequeue(self):
        mq = self._make()
        mq.enqueue("m1", priority=2)
        mq.enqueue("m2", priority=1)
        m = mq.dequeue()
        assert m.mission_id == "m2"  # higher priority (lower number)

    def test_assign(self):
        mq = self._make()
        mq.enqueue("m1")
        mq.assign("m1", "d1")
        m = mq._all_missions["m1"]
        assert m.drone_id == "d1"

    def test_complete(self):
        mq = self._make()
        mq.enqueue("m1")
        mq.complete("m1")
        assert mq.pending_count() == 0

    def test_expire_overdue(self):
        mq = self._make()
        mq.enqueue("m1", deadline=50.0, enqueue_time=0.0)
        expired = mq.expire_overdue(100.0)
        assert "m1" in expired

    def test_reassign(self):
        mq = self._make()
        mq.enqueue("m1")
        m = mq.dequeue()
        mq.reassign("m1", "d2")
        assert mq._all_missions["m1"].drone_id == "d2"

    def test_summary(self):
        mq = self._make()
        mq.enqueue("m1")
        s = mq.summary()
        assert s["total_missions"] == 1


# ──────────────────────────────────────────────
# Phase 89: 비행 복도
# ──────────────────────────────────────────────
class TestFlightCorridor:
    def _make(self):
        from simulation.flight_corridor import FlightCorridorManager
        return FlightCorridorManager()

    def test_add_corridor(self):
        fc = self._make()
        c = fc.add_corridor("C1", (0, 0), (1000, 0), width=100)
        assert c.corridor_id == "C1"

    def test_entry_exit(self):
        fc = self._make()
        fc.add_corridor("C1", (0, 0), (1000, 0))
        assert fc.request_entry("d1", "C1") is True
        assert fc.exit_corridor("d1", "C1") is True

    def test_max_capacity(self):
        fc = self._make()
        fc.add_corridor("C1", (0, 0), (1000, 0), max_drones=2)
        fc.request_entry("d1", "C1")
        fc.request_entry("d2", "C1")
        assert fc.request_entry("d3", "C1") is False

    def test_is_in_corridor(self):
        fc = self._make()
        fc.add_corridor("C1", (0, 0), (1000, 0), width=100)
        assert fc.is_in_corridor((500, 0, 50), "C1") is True
        assert fc.is_in_corridor((500, 200, 50), "C1") is False

    def test_find_corridor(self):
        fc = self._make()
        fc.add_corridor("C1", (0, 0), (1000, 0), width=100)
        assert fc.find_corridor((500, 0, 50)) == "C1"
        assert fc.find_corridor((500, 500, 50)) is None

    def test_direction_enforcement(self):
        fc = self._make()
        fc.add_corridor("C1", (0, 0), (1000, 0), direction="FORWARD")
        assert fc.request_entry("d1", "C1", direction="FORWARD") is True
        assert fc.request_entry("d2", "C1", direction="REVERSE") is False

    def test_summary(self):
        fc = self._make()
        fc.add_corridor("C1", (0, 0), (1000, 0))
        s = fc.summary()
        assert s["active_corridors"] == 1


# ──────────────────────────────────────────────
# Phase 90: 센서 퓨전
# ──────────────────────────────────────────────
class TestSensorFusion:
    def _make(self):
        from simulation.sensor_fusion import SensorFusion
        return SensorFusion()

    def test_single_sensor(self):
        sf = self._make()
        sf.add_measurement("d1", "GPS", (500, 500, 50), accuracy=2.0)
        fused = sf.fuse("d1")
        assert fused is not None
        assert fused.sources == 1

    def test_multi_sensor_fusion(self):
        sf = self._make()
        sf.add_measurement("d1", "GPS", (500, 500, 50), accuracy=2.0)
        sf.add_measurement("d1", "RADAR", (502, 498, 50), accuracy=5.0)
        fused = sf.fuse("d1")
        assert fused.sources == 2
        # GPS 더 정확 → 융합 위치는 GPS에 가까워야
        assert abs(fused.position[0] - 500) < abs(fused.position[0] - 502) + 1

    def test_fuse_all(self):
        sf = self._make()
        sf.add_measurement("d1", "GPS", (500, 500, 50), accuracy=2.0)
        sf.add_measurement("d2", "GPS", (600, 600, 50), accuracy=2.0)
        result = sf.fuse_all()
        assert len(result) == 2

    def test_degraded_sensors(self):
        sf = self._make()
        sf.add_measurement("d1", "GPS", (500, 500, 50), accuracy=2.0, confidence=0.3)
        degraded = sf.degraded_sensors(threshold=0.5)
        assert ("d1", "GPS") in degraded

    def test_sensor_health(self):
        sf = self._make()
        sf.add_measurement("d1", "GPS", (500, 500, 50), confidence=0.9)
        health = sf.sensor_health("d1")
        assert health["GPS"] == 0.9

    def test_summary(self):
        sf = self._make()
        sf.add_measurement("d1", "GPS", (500, 500, 50))
        s = sf.summary()
        assert s["tracked_drones"] == 1


# ──────────────────────────────────────────────
# Phase 91: 벤치마크
# ──────────────────────────────────────────────
class TestBenchmarkSuite:
    def _make(self):
        from simulation.benchmark_suite import BenchmarkSuite
        return BenchmarkSuite()

    def test_run_benchmark(self):
        bs = self._make()
        result = bs.run_benchmark("test_op", lambda: sum(range(100)), iterations=10, warmup=2)
        assert result.mean_ms > 0
        assert result.iterations == 10

    def test_set_baseline_and_compare(self):
        bs = self._make()
        r1 = bs.run_benchmark("op", lambda: sum(range(100)), iterations=10, warmup=1)
        bs.set_baseline("op")
        r2 = bs.run_benchmark("op", lambda: sum(range(100)), iterations=10, warmup=1)
        comp = bs.compare_with_baseline("op")
        assert comp is not None
        assert "speedup" in comp

    def test_detect_regressions(self):
        bs = self._make()
        bs.run_benchmark("fast", lambda: None, iterations=10, warmup=1)
        bs.set_baseline("fast")
        regs = bs.detect_regressions()
        assert isinstance(regs, list)

    def test_report(self):
        bs = self._make()
        bs.run_benchmark("op", lambda: sum(range(50)), iterations=5, warmup=1)
        report = bs.report()
        assert "벤치마크" in report

    def test_summary(self):
        bs = self._make()
        bs.run_benchmark("op", lambda: None, iterations=5, warmup=1)
        s = bs.summary()
        assert s["total_benchmarks"] == 1
