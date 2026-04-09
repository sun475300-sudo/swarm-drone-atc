"""
Phase 28-31 테스트
==================
- Phase 28: FlightDataRecorder (FDR) — 비행 데이터 기록/리플레이/CSV
- Phase 29: MultiControllerManager — 관제 구역 분할/핸드오프
- Phase 30: SLAMonitor — SLA 위반 감지/자동 튜닝
- Phase 31: EventTimeline — 이벤트 시계열/사고 조사
"""
import tempfile
from pathlib import Path

import numpy as np
import pytest


# ─── Phase 28: FlightDataRecorder ────────────────────────────
class TestFlightDataRecorder:
    """FDR 비행 데이터 기록 테스트"""

    def _make_drone(self, drone_id="DR001", battery=80.0, phase="ENROUTE"):
        from src.airspace_control.agents.drone_state import DroneState, FlightPhase
        return DroneState(
            drone_id=drone_id,
            position=np.array([100.0, 200.0, 60.0]),
            velocity=np.array([10.0, 0.0, 0.0]),
            profile_name="COMMERCIAL_DELIVERY",
            flight_phase=FlightPhase[phase],
            battery_pct=battery,
        )

    def test_record_tick(self):
        from simulation.flight_data_recorder import FlightDataRecorder
        fdr = FlightDataRecorder()
        fdr.record_tick(1.0, [self._make_drone()])
        assert fdr.total_records() == 1
        assert fdr.tick_count() == 1

    def test_multiple_drones(self):
        from simulation.flight_data_recorder import FlightDataRecorder
        fdr = FlightDataRecorder()
        drones = [self._make_drone("DR001"), self._make_drone("DR002")]
        fdr.record_tick(1.0, drones)
        assert fdr.total_records() == 2
        assert len(fdr.drone_ids()) == 2

    def test_timeline(self):
        from simulation.flight_data_recorder import FlightDataRecorder
        fdr = FlightDataRecorder()
        d = self._make_drone()
        for t in [1.0, 2.0, 3.0]:
            fdr.record_tick(t, [d])
        timeline = fdr.get_drone_timeline("DR001")
        assert len(timeline) == 3
        assert timeline[0].t == 1.0

    def test_time_slice(self):
        from simulation.flight_data_recorder import FlightDataRecorder
        fdr = FlightDataRecorder()
        d = self._make_drone()
        for t in [1.0, 2.0, 3.0, 4.0, 5.0]:
            fdr.record_tick(t, [d])
        sliced = fdr.get_time_slice(2.0, 4.0)
        assert len(sliced) == 3
        assert all(2.0 <= r.t <= 4.0 for r in sliced)

    def test_drone_at_time(self):
        from simulation.flight_data_recorder import FlightDataRecorder
        fdr = FlightDataRecorder()
        d = self._make_drone()
        fdr.record_tick(1.0, [d])
        fdr.record_tick(5.0, [d])
        rec = fdr.get_drone_at_time("DR001", 4.5)
        assert rec is not None
        assert rec.t == 5.0  # 가장 가까운 시간

    def test_export_csv(self):
        from simulation.flight_data_recorder import FlightDataRecorder
        fdr = FlightDataRecorder()
        fdr.record_tick(1.0, [self._make_drone()])
        with tempfile.TemporaryDirectory() as td:
            path = fdr.export_csv(Path(td) / "test.csv")
            assert path.exists()
            content = path.read_text(encoding="utf-8")
            assert "DR001" in content
            assert "ENROUTE" in content

    def test_max_ticks_limit(self):
        from simulation.flight_data_recorder import FlightDataRecorder
        fdr = FlightDataRecorder(max_ticks=3)
        d = self._make_drone()
        for t in range(10):
            fdr.record_tick(float(t), [d])
        assert fdr.tick_count() == 3

    def test_summary(self):
        from simulation.flight_data_recorder import FlightDataRecorder
        fdr = FlightDataRecorder()
        fdr.record_tick(1.0, [self._make_drone()])
        s = fdr.summary()
        assert s["total_records"] == 1
        assert s["drones"] == 1

    def test_clear(self):
        from simulation.flight_data_recorder import FlightDataRecorder
        fdr = FlightDataRecorder()
        fdr.record_tick(1.0, [self._make_drone()])
        fdr.clear()
        assert fdr.total_records() == 0


# ─── Phase 29: MultiControllerManager ───────────────────────
class TestMultiController:
    """다중 컨트롤러 관제 구역 테스트"""

    def test_sector_creation(self):
        from simulation.multi_controller import MultiControllerManager
        mcm = MultiControllerManager(bounds=5000.0, n_sectors=4)
        assert len(mcm.sectors) == 4

    def test_assign_sector(self):
        from simulation.multi_controller import MultiControllerManager
        mcm = MultiControllerManager(bounds=5000.0, n_sectors=4)
        pos = np.array([2000.0, 2000.0, 60.0])
        sid = mcm.assign_sector(pos)
        assert sid is not None

    def test_register_drone(self):
        from simulation.multi_controller import MultiControllerManager
        mcm = MultiControllerManager(bounds=5000.0, n_sectors=4)
        pos = np.array([1000.0, 1000.0, 60.0])
        sid = mcm.register_drone("DR001", pos)
        assert sid is not None
        assert "DR001" in mcm.sectors[sid].drones

    def test_handoff_on_move(self):
        from simulation.multi_controller import MultiControllerManager
        mcm = MultiControllerManager(bounds=5000.0, n_sectors=4)
        # 왼쪽 아래에서 오른쪽 위로 이동
        mcm.register_drone("DR001", np.array([-4000.0, -4000.0, 60.0]))
        old_sid = mcm.get_drone_sector("DR001")
        mcm.update_drone_position("DR001", np.array([4000.0, 4000.0, 60.0]))
        new_sid = mcm.get_drone_sector("DR001")
        assert old_sid != new_sid
        assert mcm.total_handoffs >= 1

    def test_sector_stats(self):
        from simulation.multi_controller import MultiControllerManager
        mcm = MultiControllerManager(bounds=5000.0, n_sectors=4)
        mcm.register_drone("DR001", np.array([1000.0, 1000.0, 60.0]))
        stats = mcm.sector_stats()
        assert len(stats) == 4
        total_drones = sum(s["drones"] for s in stats.values())
        assert total_drones == 1

    def test_global_stats(self):
        from simulation.multi_controller import MultiControllerManager
        mcm = MultiControllerManager(bounds=5000.0, n_sectors=4)
        mcm.register_drone("DR001", np.array([1000.0, 1000.0, 60.0]))
        gs = mcm.global_stats()
        assert gs["total_sectors"] == 4
        assert gs["total_drones"] == 1

    def test_near_boundary(self):
        from simulation.multi_controller import MultiControllerManager
        mcm = MultiControllerManager(bounds=5000.0, n_sectors=4)
        # 정확히 구역 경계 근처
        near = mcm.is_near_boundary(np.array([0.0, 50.0, 60.0]), margin=100.0)
        # 0.0은 구역 경계 (2개 구역 사이)
        assert isinstance(near, bool)

    def test_sector_area(self):
        from simulation.multi_controller import MultiControllerManager
        mcm = MultiControllerManager(bounds=5000.0, n_sectors=4)
        for s in mcm.sectors.values():
            assert s.area_km2() > 0

    def test_nine_sectors(self):
        from simulation.multi_controller import MultiControllerManager
        mcm = MultiControllerManager(bounds=5000.0, n_sectors=9)
        assert len(mcm.sectors) == 9


# ─── Phase 30: SLAMonitor ───────────────────────────────────
class TestSLAMonitor:
    """SLA 위반 감지 / 자동 튜닝 테스트"""

    def test_no_violations(self):
        from simulation.sla_monitor import SLAMonitor
        mon = SLAMonitor()
        violations = mon.check(
            collision_count=0,
            conflict_resolution_rate_pct=99.9,
            route_efficiency_mean=1.05,
        )
        assert len(violations) == 0

    def test_collision_violation(self):
        from simulation.sla_monitor import SLAMonitor
        mon = SLAMonitor()
        violations = mon.check(collision_count=5)
        assert len(violations) >= 1
        assert any(v.metric == "collision_count" for v in violations)

    def test_resolution_rate_violation(self):
        from simulation.sla_monitor import SLAMonitor
        mon = SLAMonitor()
        violations = mon.check(conflict_resolution_rate_pct=90.0)
        assert len(violations) >= 1

    def test_severity_levels(self):
        from simulation.sla_monitor import SLAMonitor
        mon = SLAMonitor()
        violations = mon.check(collision_count=1, route_efficiency_mean=2.0)
        severities = {v.severity for v in violations}
        assert "CRITICAL" in severities

    def test_auto_tune_collision(self):
        from simulation.sla_monitor import SLAMonitor
        mon = SLAMonitor()
        violations = mon.check(collision_count=3)
        adjustments = mon.auto_tune(violations)
        assert "apf_k_rep_increase" in adjustments

    def test_auto_tune_latency(self):
        from simulation.sla_monitor import SLAMonitor
        mon = SLAMonitor()
        violations = mon.check(advisory_latency_p99=15.0)
        adjustments = mon.auto_tune(violations)
        assert "scan_radius_reduction" in adjustments

    def test_violation_count(self):
        from simulation.sla_monitor import SLAMonitor
        mon = SLAMonitor()
        mon.check(collision_count=1)
        mon.check(collision_count=2)
        assert mon.violation_count() >= 2

    def test_violation_count_by_severity(self):
        from simulation.sla_monitor import SLAMonitor
        mon = SLAMonitor()
        mon.check(collision_count=1)  # CRITICAL
        count = mon.violation_count(severity="CRITICAL")
        assert count >= 1

    def test_reset(self):
        from simulation.sla_monitor import SLAMonitor
        mon = SLAMonitor()
        mon.check(collision_count=1)
        mon.reset()
        assert mon.violation_count() == 0

    def test_tune_history(self):
        from simulation.sla_monitor import SLAMonitor
        mon = SLAMonitor()
        v = mon.check(collision_count=5)
        mon.auto_tune(v)
        assert len(mon.tune_history()) == 1


# ─── Phase 31: EventTimeline ────────────────────────────────
class TestEventTimeline:
    """이벤트 타임라인 / 사고 조사 테스트"""

    def test_add_event(self):
        from simulation.event_timeline import EventTimeline
        tl = EventTimeline()
        tl.add("COLLISION", t=10.0, drone_ids=["DR001", "DR002"])
        assert tl.total_events() == 1

    def test_query_by_type(self):
        from simulation.event_timeline import EventTimeline
        tl = EventTimeline()
        tl.add("COLLISION", t=10.0, drone_ids=["DR001"])
        tl.add("ADVISORY", t=11.0, drone_ids=["DR002"])
        results = tl.query(event_type="COLLISION")
        assert len(results) == 1

    def test_query_by_time_range(self):
        from simulation.event_timeline import EventTimeline
        tl = EventTimeline()
        for t in [5, 10, 15, 20, 25]:
            tl.add("ADVISORY", t=float(t), drone_ids=["DR001"])
        results = tl.query(t_start=10.0, t_end=20.0)
        assert len(results) == 3

    def test_query_by_drone(self):
        from simulation.event_timeline import EventTimeline
        tl = EventTimeline()
        tl.add("COLLISION", t=10.0, drone_ids=["DR001", "DR002"])
        tl.add("ADVISORY", t=11.0, drone_ids=["DR003"])
        results = tl.query(drone_id="DR001")
        assert len(results) == 1

    def test_drone_history(self):
        from simulation.event_timeline import EventTimeline
        tl = EventTimeline()
        tl.add("COLLISION", t=10.0, drone_ids=["DR001"])
        tl.add("ADVISORY", t=15.0, drone_ids=["DR001"])
        history = tl.drone_history("DR001")
        assert len(history) == 2

    def test_event_types(self):
        from simulation.event_timeline import EventTimeline
        tl = EventTimeline()
        tl.add("COLLISION", t=10.0)
        tl.add("ADVISORY", t=11.0)
        tl.add("FAILURE", t=12.0)
        types = tl.event_types()
        assert set(types) == {"ADVISORY", "COLLISION", "FAILURE"}

    def test_count_by_type(self):
        from simulation.event_timeline import EventTimeline
        tl = EventTimeline()
        tl.add("COLLISION", t=10.0)
        tl.add("COLLISION", t=11.0)
        tl.add("ADVISORY", t=12.0)
        counts = tl.count_by_type()
        assert counts["COLLISION"] == 2
        assert counts["ADVISORY"] == 1

    def test_critical_events(self):
        from simulation.event_timeline import EventTimeline
        tl = EventTimeline()
        tl.add("COLLISION", t=10.0, severity="CRITICAL")
        tl.add("ADVISORY", t=11.0, severity="INFO")
        crits = tl.critical_events()
        assert len(crits) == 1

    def test_time_range(self):
        from simulation.event_timeline import EventTimeline
        tl = EventTimeline()
        tl.add("A", t=5.0)
        tl.add("B", t=25.0)
        r = tl.time_range()
        assert r == (5.0, 25.0)

    def test_summary(self):
        from simulation.event_timeline import EventTimeline
        tl = EventTimeline()
        tl.add("COLLISION", t=10.0, drone_ids=["DR001"], severity="CRITICAL")
        s = tl.summary()
        assert s["total_events"] == 1
        assert s["critical_count"] == 1

    def test_clear(self):
        from simulation.event_timeline import EventTimeline
        tl = EventTimeline()
        tl.add("COLLISION", t=10.0)
        tl.clear()
        assert tl.total_events() == 0

    def test_combined_query(self):
        from simulation.event_timeline import EventTimeline
        tl = EventTimeline()
        tl.add("COLLISION", t=10.0, drone_ids=["DR001"], severity="CRITICAL")
        tl.add("COLLISION", t=20.0, drone_ids=["DR002"], severity="CRITICAL")
        tl.add("ADVISORY", t=15.0, drone_ids=["DR001"], severity="INFO")
        results = tl.query(event_type="COLLISION", drone_id="DR001")
        assert len(results) == 1
        assert results[0].t == 10.0
