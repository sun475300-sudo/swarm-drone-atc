"""
Phase 52-59 테스트
- 통신 품질 시뮬레이션 (CommQualitySimulator)
- 자동 보고서 생성기 (ReportGenerator)
- 동적 지오펜스 관리 (GeofenceManager)
- 군집지능 알고리즘 (SwarmIntelligence)
- 통신 중계 드론 배치 (CommRelayPlanner)
- 다중 임무 할당 (MissionPlanner)
- 공역 용량 분석 (AirspaceCapacity)
- 비상 프로토콜 관리 (EmergencyManager)
"""
import pytest
import numpy as np


# ──────────────────────────────────────────────
# Phase 52: 통신 품질 시뮬레이션
# ──────────────────────────────────────────────
class TestCommQuality:
    def _make(self):
        from simulation.comm_quality import CommQualitySimulator, CommConfig
        return CommQualitySimulator(config=CommConfig())

    def test_basic_link(self):
        sim = self._make()
        m = sim.update_link("d1", (100, 100, 50), t=1.0)
        assert m.drone_id == "d1"
        assert m.distance_m > 0
        assert 0 <= m.quality_score <= 100
        assert m.status in ("GOOD", "DEGRADED", "POOR", "LOST")

    def test_signal_degrades_with_distance(self):
        sim = self._make()
        m_near = sim.update_link("d1", (50, 0, 0), t=1.0)
        m_far = sim.update_link("d2", (4000, 0, 0), t=1.0)
        assert m_near.signal_strength_dbm > m_far.signal_strength_dbm

    def test_quality_decreases_far(self):
        sim = self._make()
        sim.update_link("d1", (100, 0, 0), t=1.0)
        sim.update_link("d2", (3000, 0, 0), t=1.0)
        q1 = sim.get_quality("d1")
        q2 = sim.get_quality("d2")
        assert q1.quality_score > q2.quality_score

    def test_out_of_range_lost(self):
        sim = self._make()
        m = sim.update_link("d1", (6000, 0, 0), t=1.0)
        assert m.status == "LOST"

    def test_drones_in_danger(self):
        sim = self._make()
        sim.update_link("d1", (100, 0, 0), t=1.0)
        sim.update_link("d2", (6000, 0, 0), t=1.0)
        danger = sim.drones_in_danger()
        assert "d2" in danger

    def test_average_quality(self):
        sim = self._make()
        sim.update_link("d1", (100, 0, 0), t=1.0)
        sim.update_link("d2", (200, 0, 0), t=1.0)
        avg = sim.average_quality()
        assert 0 < avg <= 100

    def test_link_budget(self):
        sim = self._make()
        sim.update_link("d1", (500, 0, 0), t=1.0)
        budget = sim.link_budget("d1")
        assert "tx_power_dbm" in budget
        assert "snr_db" in budget
        assert "margin_db" in budget

    def test_inter_drone_link(self):
        sim = self._make()
        sim.update_link("d1", (100, 0, 0), t=1.0)
        sim.update_link("d2", (200, 0, 0), t=1.0)
        link = sim.inter_drone_link("d1", "d2", t=1.0)
        assert link is not None
        assert link.distance_m == pytest.approx(100.0, abs=1.0)

    def test_recommend_relay(self):
        sim = self._make()
        sim.update_link("d1", (6000, 0, 0), t=1.0)
        assert sim.recommend_relay("d1") is True

    def test_summary(self):
        sim = self._make()
        sim.update_link("d1", (100, 0, 0), t=1.0)
        s = sim.summary()
        assert s["total_drones"] == 1
        assert "avg_quality" in s

    def test_clear(self):
        sim = self._make()
        sim.update_link("d1", (100, 0, 0), t=1.0)
        sim.clear()
        assert sim.get_quality("d1") is None


# ──────────────────────────────────────────────
# Phase 53: 자동 보고서 생성기
# ──────────────────────────────────────────────
class TestReportGenerator:
    def _make(self):
        from simulation.report_generator import ReportGenerator
        return ReportGenerator()

    def test_empty_report(self):
        gen = self._make()
        report = gen.generate()
        assert "보고서" in report
        assert "SDACS" in report

    def test_with_overview(self):
        gen = self._make()
        gen.add_section("overview", {"drones": 50, "duration": 120})
        report = gen.generate()
        assert "50" in report

    def test_with_simulation_result(self):
        gen = self._make()
        gen.add_simulation_result({
            "drone_count": 30,
            "duration": 60,
            "collisions": 2,
            "conflicts": 15,
            "resolution_rate": 0.87,
        })
        report = gen.generate()
        assert "충돌" in report

    def test_recommendations_generated(self):
        gen = self._make()
        gen.add_simulation_result({
            "collisions": 5,
            "conflicts": 10,
            "resolution_rate": 0.80,
        })
        gen.generate()
        recs = gen.get_recommendations(min_priority="HIGH")
        assert len(recs) > 0

    def test_summary(self):
        gen = self._make()
        gen.add_section("overview", {"drones": 20, "duration": 60})
        gen.generate()
        s = gen.generate_summary()
        assert s["drone_count"] == 20

    def test_no_recommendations_for_clean(self):
        gen = self._make()
        gen.add_simulation_result({
            "collisions": 0,
            "resolution_rate": 0.99,
        })
        gen.generate()
        recs = gen.get_recommendations(min_priority="CRITICAL")
        # No critical collision recommendation
        assert all(r.priority != "CRITICAL" or "충돌" not in r.title for r in recs)

    def test_clear(self):
        gen = self._make()
        gen.add_section("overview", {"drones": 10})
        gen.clear()
        s = gen.generate_summary()
        assert s["drone_count"] == 0


# ──────────────────────────────────────────────
# Phase 54: 동적 지오펜스 관리
# ──────────────────────────────────────────────
class TestGeofenceManager:
    def _make(self):
        from simulation.geofence_manager import GeofenceManager
        return GeofenceManager(buffer_m=10.0)

    def test_circle_violation(self):
        gm = self._make()
        gm.add_circle("nfz1", center=(500, 500), radius=100)
        vs = gm.check_position("d1", (510, 510, 50), t=1.0)
        assert len(vs) > 0
        assert vs[0].fence_id == "nfz1"

    def test_circle_no_violation(self):
        gm = self._make()
        gm.add_circle("nfz1", center=(500, 500), radius=100)
        vs = gm.check_position("d1", (100, 100, 50), t=1.0)
        # No violation (outside circle and outside buffer)
        assert all(v.distance_to_boundary < 0 or v.action.value == "warn" for v in vs) or len(vs) == 0

    def test_polygon_violation(self):
        gm = self._make()
        gm.add_polygon("park", vertices=[
            (0, 0), (200, 0), (200, 200), (0, 200)
        ])
        vs = gm.check_position("d1", (100, 100, 50), t=1.0)
        assert len(vs) > 0

    def test_polygon_outside(self):
        gm = self._make()
        gm.add_polygon("park", vertices=[
            (0, 0), (200, 0), (200, 200), (0, 200)
        ])
        vs = gm.check_position("d1", (500, 500, 50), t=1.0)
        deny_violations = [v for v in vs if v.action.value == "deny"]
        assert len(deny_violations) == 0

    def test_time_based_activation(self):
        gm = self._make()
        gm.add_circle("temp_nfz", center=(500, 500), radius=100,
                       active_start=10.0, active_end=60.0)
        # Before activation
        vs1 = gm.check_position("d1", (510, 510, 50), t=5.0)
        assert len(vs1) == 0
        # During activation
        vs2 = gm.check_position("d1", (510, 510, 50), t=30.0)
        assert len(vs2) > 0
        # After deactivation
        vs3 = gm.check_position("d1", (510, 510, 50), t=70.0)
        assert len(vs3) == 0

    def test_remove_fence(self):
        gm = self._make()
        gm.add_circle("nfz1", center=(500, 500), radius=100)
        assert gm.remove("nfz1")
        vs = gm.check_position("d1", (510, 510, 50), t=1.0)
        assert len(vs) == 0

    def test_deactivate_activate(self):
        gm = self._make()
        gm.add_circle("nfz1", center=(500, 500), radius=100)
        gm.deactivate("nfz1")
        vs = gm.check_position("d1", (510, 510, 50), t=1.0)
        assert len(vs) == 0
        gm.activate("nfz1")
        vs = gm.check_position("d1", (510, 510, 50), t=1.0)
        assert len(vs) > 0

    def test_altitude_filter(self):
        gm = self._make()
        gm.add_circle("nfz1", center=(500, 500), radius=100,
                       min_altitude=30, max_altitude=80)
        # Within altitude range
        vs1 = gm.check_position("d1", (510, 510, 50), t=1.0)
        assert len(vs1) > 0
        # Outside altitude range
        vs2 = gm.check_position("d1", (510, 510, 100), t=1.0)
        assert len(vs2) == 0

    def test_corridor(self):
        gm = self._make()
        gm.add_corridor("cor1", start=(0, 0), end=(1000, 0), width=50)
        vs = gm.check_position("d1", (500, 10, 50), t=1.0)
        assert len(vs) > 0  # Inside corridor

    def test_check_path(self):
        gm = self._make()
        gm.add_circle("nfz1", center=(500, 500), radius=100)
        vs = gm.check_path("d1", (0, 0, 50), (1000, 1000, 50), t=1.0)
        assert len(vs) > 0  # Path crosses NFZ

    def test_summary(self):
        gm = self._make()
        gm.add_circle("nfz1", center=(500, 500), radius=100)
        gm.check_position("d1", (510, 510, 50), t=1.0)
        s = gm.summary()
        assert s["total_fences"] == 1
        assert s["total_violations"] > 0


# ──────────────────────────────────────────────
# Phase 55: 군집지능 알고리즘
# ──────────────────────────────────────────────
class TestSwarmIntelligence:
    def _make(self, n=10):
        from simulation.swarm_intelligence import SwarmIntelligence
        return SwarmIntelligence(n_agents=n, rng_seed=42)

    def test_boids_basic(self):
        swarm = self._make(5)
        positions = np.array([
            [0, 0, 0], [10, 0, 0], [0, 10, 0], [10, 10, 0], [5, 5, 0]
        ], dtype=float)
        swarm.update_positions(positions)
        vels = swarm.compute_boids()
        assert vels.shape == (5, 3)

    def test_boids_separation(self):
        swarm = self._make(2)
        # Two very close drones
        positions = np.array([[0, 0, 0], [1, 0, 0]], dtype=float)
        swarm.update_positions(positions)
        vels = swarm.compute_boids()
        # First drone should move away (negative x)
        assert vels[0, 0] < 0 or vels[1, 0] > 0

    def test_pso_converge(self):
        swarm = self._make(10)
        # Random initial positions
        positions = np.random.default_rng(42).uniform(-100, 100, (10, 3))
        swarm.update_positions(positions)
        swarm.set_target((0, 0, 0))
        # Run several steps
        for _ in range(50):
            swarm.step(dt=0.1, mode="pso")
        state = swarm.get_state()
        # Should converge toward target
        assert np.linalg.norm(state.center_of_mass) < 100

    def test_step_boids(self):
        swarm = self._make(5)
        positions = np.random.default_rng(42).uniform(0, 100, (5, 3))
        swarm.update_positions(positions)
        new_pos = swarm.step(dt=0.1)
        assert new_pos.shape == (5, 3)

    def test_get_state(self):
        swarm = self._make(5)
        positions = np.array([
            [0, 0, 0], [10, 0, 0], [0, 10, 0], [10, 10, 0], [5, 5, 0]
        ], dtype=float)
        swarm.update_positions(positions)
        state = swarm.get_state()
        assert state.spread >= 0
        assert state.min_separation > 0
        assert 0 <= state.cohesion_index <= 1

    def test_multi_target_pso(self):
        swarm = self._make(10)
        positions = np.random.default_rng(42).uniform(-100, 100, (10, 3))
        swarm.update_positions(positions)
        swarm.set_targets([(50, 50, 0), (-50, -50, 0)])
        swarm.compute_pso()
        # Should not error

    def test_summary(self):
        swarm = self._make(5)
        positions = np.random.default_rng(42).uniform(0, 50, (5, 3))
        swarm.update_positions(positions)
        s = swarm.summary()
        assert s["n_agents"] == 5
        assert "cohesion_index" in s


# ──────────────────────────────────────────────
# Phase 56: 통신 중계 드론 배치
# ──────────────────────────────────────────────
class TestCommRelay:
    def _make(self):
        from simulation.comm_relay import CommRelayPlanner
        return CommRelayPlanner(
            base_station=(0, 0, 0),
            comm_range=500,
            relay_range=300,
        )

    def test_all_connected(self):
        planner = self._make()
        planner.update_drones({
            "d1": (100, 0, 0),
            "d2": (200, 0, 0),
        })
        assert planner.get_coverage() == 1.0

    def test_disconnected_far(self):
        planner = self._make()
        planner.update_drones({
            "d1": (100, 0, 0),
            "d2": (2000, 0, 0),  # Out of range
        })
        assert planner.get_coverage() < 1.0
        assert "d2" in planner.get_disconnected()

    def test_relay_plan(self):
        planner = self._make()
        planner.update_drones({
            "d1": (100, 0, 0),
            "d2": (800, 0, 0),  # Out of range
        })
        plan = planner.compute_relay_plan(max_relays=3)
        assert plan.coverage_after >= plan.coverage_before

    def test_find_path(self):
        planner = self._make()
        planner.update_drones({
            "d1": (200, 0, 0),
        })
        path = planner.find_path("d1")
        assert len(path) >= 2  # d1 -> BASE
        assert path[-1] == "BASE"

    def test_hop_count(self):
        planner = self._make()
        planner.update_drones({"d1": (100, 0, 0)})
        hops = planner.hop_count("d1")
        assert hops == 1  # Direct to base

    def test_remove_relays(self):
        planner = self._make()
        planner.update_drones({"d1": (800, 0, 0)})
        planner.compute_relay_plan()
        planner.remove_relays()
        assert planner.summary()["relay_count"] == 0

    def test_summary(self):
        planner = self._make()
        planner.update_drones({"d1": (100, 0, 0)})
        s = planner.summary()
        assert s["total_drones"] == 1
        assert "coverage" in s


# ──────────────────────────────────────────────
# Phase 57: 다중 임무 할당
# ──────────────────────────────────────────────
class TestMissionPlanner:
    def _make(self):
        from simulation.mission_planner import MissionPlanner, Mission, DroneAsset
        return MissionPlanner(), Mission, DroneAsset

    def test_basic_assignment(self):
        planner, Mission, DroneAsset = self._make()
        planner.add_drone(DroneAsset("d1", position=(0, 0, 50), battery_pct=90))
        planner.add_mission(Mission("m1", target=(500, 0, 50)))
        assigns = planner.assign()
        assert len(assigns) == 1
        assert assigns[0].drone_id == "d1"
        assert assigns[0].mission_id == "m1"

    def test_multiple_assignments(self):
        planner, Mission, DroneAsset = self._make()
        planner.add_drone(DroneAsset("d1", position=(0, 0, 50), battery_pct=90))
        planner.add_drone(DroneAsset("d2", position=(100, 0, 50), battery_pct=90))
        planner.add_mission(Mission("m1", target=(500, 0, 50)))
        planner.add_mission(Mission("m2", target=(600, 0, 50)))
        assigns = planner.assign()
        assert len(assigns) == 2

    def test_priority_assignment(self):
        planner, Mission, DroneAsset = self._make()
        planner.add_drone(DroneAsset("d1", position=(0, 0, 50), battery_pct=90))
        planner.add_mission(Mission("m_low", target=(500, 0, 50), priority=1))
        planner.add_mission(Mission("m_high", target=(500, 100, 50), priority=5))
        assigns = planner.assign()
        # Only one drone, should get high priority mission
        assert len(assigns) == 1
        assert assigns[0].mission_id == "m_high"

    def test_battery_constraint(self):
        planner, Mission, DroneAsset = self._make()
        planner.add_drone(DroneAsset("d1", position=(0, 0, 50), battery_pct=10))
        planner.add_mission(Mission("m1", target=(5000, 0, 50), required_battery_pct=20))
        assigns = planner.assign()
        # Too far + low battery
        assert len(assigns) == 0

    def test_complete_mission(self):
        planner, Mission, DroneAsset = self._make()
        planner.add_mission(Mission("m1", target=(500, 0, 50)))
        planner.complete_mission("m1")
        assert planner.unassigned_missions() == []

    def test_utilization(self):
        planner, Mission, DroneAsset = self._make()
        planner.add_drone(DroneAsset("d1", position=(0, 0, 50)))
        planner.add_drone(DroneAsset("d2", position=(100, 0, 50)))
        planner.add_mission(Mission("m1", target=(500, 0, 50)))
        planner.assign()
        util = planner.drone_utilization()
        assert 0 < util <= 1.0

    def test_summary(self):
        planner, Mission, DroneAsset = self._make()
        planner.add_drone(DroneAsset("d1", position=(0, 0, 50)))
        planner.add_mission(Mission("m1", target=(500, 0, 50)))
        planner.assign()
        s = planner.summary()
        assert s["total_missions"] == 1
        assert s["assignments"] == 1

    def test_clear(self):
        planner, Mission, DroneAsset = self._make()
        planner.add_drone(DroneAsset("d1", position=(0, 0, 50)))
        planner.add_mission(Mission("m1", target=(500, 0, 50)))
        planner.clear()
        assert planner.summary()["total_missions"] == 0


# ──────────────────────────────────────────────
# Phase 58: 공역 용량 분석
# ──────────────────────────────────────────────
class TestAirspaceCapacity:
    def _make(self):
        from simulation.airspace_capacity import AirspaceCapacity
        return AirspaceCapacity(
            bounds=(0, 0, 900, 900),
            sectors=(3, 3),
            base_capacity_per_sector=5,
        )

    def test_basic_saturation(self):
        cap = self._make()
        # Put 3 drones in one sector
        positions = {
            "d1": (50, 50, 50),
            "d2": (60, 60, 50),
            "d3": (70, 70, 50),
        }
        cap.update_positions(positions)
        sat = cap.overall_saturation()
        assert 0 < sat < 1

    def test_overloaded_sector(self):
        cap = self._make()
        # Put many drones in one sector (capacity=5)
        positions = {f"d{i}": (50, 50, 50) for i in range(10)}
        cap.update_positions(positions)
        report = cap.analyze()
        assert len(report.overloaded_sectors) > 0

    def test_auto_restrict(self):
        cap = self._make()
        positions = {f"d{i}": (50, 50, 50) for i in range(10)}
        cap.update_positions(positions)
        restricted = cap.auto_restrict()
        assert len(restricted) > 0

    def test_can_enter(self):
        cap = self._make()
        positions = {f"d{i}": (50, 50, 50) for i in range(10)}
        cap.update_positions(positions)
        cap.auto_restrict()
        # The overloaded sector should be restricted
        assert not cap.can_enter("S00")

    def test_least_busy_sector(self):
        cap = self._make()
        positions = {f"d{i}": (50, 50, 50) for i in range(5)}
        cap.update_positions(positions)
        least = cap.get_least_busy_sector()
        assert least is not None
        assert least != "S00"  # S00 is the busiest

    def test_set_capacity(self):
        cap = self._make()
        cap.set_capacity("S00", 20)
        positions = {f"d{i}": (50, 50, 50) for i in range(10)}
        cap.update_positions(positions)
        info = cap.get_sector_for_position(50, 50)
        assert info.capacity == 20

    def test_analyze_recommendation(self):
        cap = self._make()
        cap.update_positions({"d1": (50, 50, 50)})
        report = cap.analyze()
        assert report.recommendation != ""

    def test_summary(self):
        cap = self._make()
        cap.update_positions({"d1": (50, 50, 50)})
        s = cap.summary()
        assert s["total_drones"] == 1
        assert "sectors" in s

    def test_prediction(self):
        cap = self._make()
        # Add several updates to build history
        for i in range(5):
            n = i + 1
            positions = {f"d{j}": (50, 50, 50) for j in range(n)}
            cap.update_positions(positions)
        report = cap.analyze()
        # Prediction should be >= 0
        assert report.predicted_saturation_30s >= 0


# ──────────────────────────────────────────────
# Phase 59: 비상 프로토콜 관리
# ──────────────────────────────────────────────
class TestEmergencyProtocol:
    def _make(self):
        from simulation.emergency_protocol import EmergencyManager, EmergencyType
        return EmergencyManager(), EmergencyType

    def test_declare_emergency(self):
        mgr, ET = self._make()
        em = mgr.declare_emergency("d1", ET.ENGINE_FAILURE, t=10.0)
        assert em.drone_id == "d1"
        assert em.emergency_type == ET.ENGINE_FAILURE
        assert len(em.actions) > 0

    def test_respond(self):
        mgr, ET = self._make()
        em = mgr.declare_emergency("d1", ET.COMM_LOSS, t=5.0)
        executed = mgr.respond(em.emergency_id)
        assert len(executed) > 0
        assert all(a.executed for a in executed)

    def test_resolve(self):
        mgr, ET = self._make()
        em = mgr.declare_emergency("d1", ET.BATTERY_CRITICAL, t=10.0)
        assert mgr.resolve(em.emergency_id, t=20.0)
        assert len(mgr.get_active()) == 0

    def test_escalate(self):
        mgr, ET = self._make()
        em = mgr.declare_emergency("d1", ET.GPS_FAILURE, t=5.0, severity=2)
        mgr.escalate(em.emergency_id)
        updated = mgr._emergencies[em.emergency_id]
        assert updated.severity == 3
        assert updated.state.name == "ESCALATED"

    def test_get_by_drone(self):
        mgr, ET = self._make()
        mgr.declare_emergency("d1", ET.COMM_LOSS, t=1.0)
        mgr.declare_emergency("d2", ET.ENGINE_FAILURE, t=2.0)
        d1_ems = mgr.get_by_drone("d1")
        assert len(d1_ems) == 1

    def test_is_affected(self):
        mgr, ET = self._make()
        mgr.declare_emergency("d1", ET.INTRUDER, t=1.0, affected_drones=["d1", "d2"])
        assert mgr.is_affected("d2")

    def test_response_time(self):
        mgr, ET = self._make()
        em = mgr.declare_emergency("d1", ET.MIDAIR_COLLISION, t=10.0)
        mgr.resolve(em.emergency_id, t=25.0)
        assert mgr.response_time(em.emergency_id) == 15.0

    def test_all_emergency_types(self):
        mgr, ET = self._make()
        for etype in ET:
            em = mgr.declare_emergency("d_test", etype, t=0.0)
            assert len(em.actions) > 0

    def test_get_response_actions(self):
        mgr, ET = self._make()
        mgr.declare_emergency("d1", ET.ENGINE_FAILURE, t=1.0)
        actions = mgr.get_response("d1")
        assert len(actions) > 0
        # Should be sorted by priority
        priorities = [a.priority for a in actions]
        assert priorities == sorted(priorities)

    def test_summary(self):
        mgr, ET = self._make()
        mgr.declare_emergency("d1", ET.COMM_LOSS, t=1.0)
        mgr.declare_emergency("d2", ET.ENGINE_FAILURE, t=2.0)
        s = mgr.summary()
        assert s["total_emergencies"] == 2
        assert s["active"] == 2

    def test_clear(self):
        mgr, ET = self._make()
        mgr.declare_emergency("d1", ET.COMM_LOSS, t=1.0)
        mgr.clear()
        assert mgr.active_count == 0
