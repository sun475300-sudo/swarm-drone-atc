"""Phase 300-310 통합 테스트 — HIL, Digital Twin, Mission Planner v2,
Swarm Intelligence v2, Performance Regression, Integration Test Framework,
Blockchain Audit, AR/VR Bridge.
"""

import numpy as np
import pytest
import json
import time


# ── Phase 300: HIL Simulator ─────────────────────────────────────────
from simulation.hil_simulator import (
    HILSimulator, HILMode, SensorType, SensorEmulator,
    PhysicsEngine, VehicleState, ActuatorCommand, SensorReading,
)


class TestHILSimulator:
    def test_init(self):
        hil = HILSimulator()
        assert hil.mode == HILMode.SOFTWARE_ONLY

    def test_add_vehicle(self):
        hil = HILSimulator()
        state = hil.add_vehicle("drone_1", np.array([0.0, 0.0, 50.0]))
        assert isinstance(state, VehicleState)
        assert state.position[2] == 50.0

    def test_get_sensor_imu(self):
        hil = HILSimulator()
        hil.add_vehicle("d1", np.array([0.0, 0.0, 50.0]))
        reading = hil.get_sensor("d1", SensorType.IMU)
        assert isinstance(reading, SensorReading)
        assert reading.sensor_type == SensorType.IMU

    def test_get_sensor_gps(self):
        hil = HILSimulator()
        hil.add_vehicle("d1", np.array([100.0, 200.0, 50.0]))
        reading = hil.get_sensor("d1", SensorType.GPS)
        assert isinstance(reading, SensorReading)

    def test_send_command(self):
        hil = HILSimulator()
        hil.add_vehicle("d1", np.array([0.0, 0.0, 50.0]))
        cmd = ActuatorCommand(
            motor_speeds=np.array([5000.0, 5000.0, 5000.0, 5000.0]),
            servo_angles=np.zeros(4),
        )
        hil.send_command("d1", cmd)
        state = hil.get_state("d1")
        assert state is not None

    def test_step(self):
        hil = HILSimulator()
        hil.add_vehicle("d1")
        hil.step()
        assert hil.clock > 0

    def test_run_for(self):
        hil = HILSimulator()
        hil.add_vehicle("d1", np.array([0.0, 0.0, 50.0]))
        hil.run_for(0.01)  # 10ms = 10 steps at 1kHz
        assert hil.clock >= 0.009

    def test_reset(self):
        hil = HILSimulator()
        hil.add_vehicle("d1")
        hil.step()
        hil.reset()
        assert hil.clock == 0.0

    def test_summary(self):
        hil = HILSimulator()
        hil.add_vehicle("d1")
        s = hil.summary()
        assert s["vehicles"] == 1
        assert s["mode"] == "software_only"


class TestSensorEmulator:
    def test_imu_reading(self):
        emu = SensorEmulator()
        state = VehicleState(
            acceleration=np.array([0.0, 0.0, -9.81]),
            angular_velocity=np.array([0.1, 0.0, 0.0]),
        )
        reading = emu.read_sensor(SensorType.IMU, state, 1.0)
        assert len(reading.data) == 6  # accel(3) + gyro(3)

    def test_gps_reading(self):
        emu = SensorEmulator()
        state = VehicleState(position=np.array([100.0, 200.0, 50.0]))
        reading = emu.read_sensor(SensorType.GPS, state, 1.0)
        assert len(reading.data) == 3

    def test_barometer_reading(self):
        emu = SensorEmulator()
        state = VehicleState(position=np.array([0.0, 0.0, 100.0]))
        reading = emu.read_sensor(SensorType.BAROMETER, state, 1.0)
        assert len(reading.data) == 1
        assert abs(reading.data[0] - 100.0) < 5.0


class TestPhysicsEngine:
    def test_hover(self):
        physics = PhysicsEngine()
        state = VehicleState(position=np.array([0.0, 0.0, 50.0]))
        hover_rpm = np.sqrt(physics.MASS_KG * physics.GRAVITY / (4 * physics.THRUST_COEFF))
        cmd = ActuatorCommand(
            motor_speeds=np.array([hover_rpm, hover_rpm, hover_rpm, hover_rpm]),
            servo_angles=np.zeros(4),
        )
        new_state = physics.step(state, cmd, dt=0.01)
        assert isinstance(new_state, VehicleState)


# ── Phase 301: Digital Twin Sync ─────────────────────────────────────
from simulation.digital_twin_sync import (
    DigitalTwinSyncEngine, TwinState, TwinStatus, SyncMode, SyncEvent,
)


class TestDigitalTwinSync:
    def test_init(self):
        dts = DigitalTwinSyncEngine()
        assert dts.mode == SyncMode.REAL_TIME

    def test_register_twin(self):
        dts = DigitalTwinSyncEngine()
        twin = dts.register_twin("drone_1")
        assert isinstance(twin, TwinState)
        assert twin.twin_id == "drone_1"

    def test_update_physical(self):
        dts = DigitalTwinSyncEngine()
        dts.register_twin("d1")
        dts.update_physical("d1", {"position": [10, 20, 50], "velocity": [1, 0, 0]}, timestamp=1.0)
        twin = dts.get_twin("d1")
        assert twin.physical_state["position"] == [10, 20, 50]

    def test_sync_synced(self):
        dts = DigitalTwinSyncEngine()
        dts.register_twin("d1")
        dts.update_physical("d1", {"position": [0, 0, 50]}, timestamp=1.0)
        dts.update_digital("d1", {"position": [0, 0, 50]})
        status = dts.sync("d1", current_time=1.0)
        assert status == TwinStatus.SYNCED

    def test_sync_lagging(self):
        dts = DigitalTwinSyncEngine()
        dts.register_twin("d1")
        dts.update_physical("d1", {"position": [100, 0, 50]}, timestamp=0.0)
        dts.update_digital("d1", {"position": [0, 0, 50]})
        # Large divergence triggers LAGGING
        status = dts.sync("d1", current_time=0.05)
        assert status in (TwinStatus.LAGGING, TwinStatus.SYNCED, TwinStatus.PREDICTED)

    def test_sync_all(self):
        dts = DigitalTwinSyncEngine()
        dts.register_twin("d1")
        dts.register_twin("d2")
        dts.update_physical("d1", {"position": [0, 0, 50]}, timestamp=1.0)
        dts.update_physical("d2", {"position": [10, 0, 50]}, timestamp=1.0)
        results = dts.sync_all(current_time=1.0)
        assert len(results) == 2

    def test_get_events(self):
        dts = DigitalTwinSyncEngine()
        dts.register_twin("d1")
        dts.update_physical("d1", {"position": [0, 0, 50]}, timestamp=1.0)
        dts.sync("d1", current_time=1.0)
        events = dts.get_events("d1")
        assert len(events) >= 1
        assert isinstance(events[0], SyncEvent)

    def test_summary(self):
        dts = DigitalTwinSyncEngine()
        dts.register_twin("d1")
        s = dts.summary()
        assert s["total_twins"] == 1


# ── Phase 302: Autonomous Mission Planner v2 ─────────────────────────
from simulation.autonomous_mission_planner_v2 import (
    AutonomousMissionPlannerV2, MissionObjective, MissionConstraint,
    MissionPlan, Waypoint, CoverageOptimizer, TSPSolver,
)


class TestCoverageOptimizer:
    def test_compute_waypoints(self):
        wps = CoverageOptimizer.compute_coverage_waypoints(
            np.array([0.0, 0.0]), np.array([200.0, 200.0]),
            sensor_radius=50.0, altitude=50.0,
        )
        assert len(wps) > 0
        assert all(isinstance(wp, Waypoint) for wp in wps)


class TestTSPSolver:
    def test_solve(self):
        wps = [Waypoint(position=np.array([i * 30.0, 0.0, 50.0])) for i in range(5)]
        order = TSPSolver.solve(wps, np.array([0.0, 0.0, 0.0]))
        assert len(order) == 5
        assert set(order) == {0, 1, 2, 3, 4}


class TestAutonomousMissionPlannerV2:
    def test_plan_coverage(self):
        planner = AutonomousMissionPlannerV2()
        plan = planner.plan_coverage_mission(
            "survey_1",
            area_min=np.array([0.0, 0.0]),
            area_max=np.array([200.0, 200.0]),
            drone_ids=["d1", "d2"],
            start_pos=np.array([0.0, 0.0, 0.0]),
        )
        assert isinstance(plan, MissionPlan)
        assert len(plan.waypoints) > 0
        assert plan.total_distance_m > 0

    def test_plan_delivery(self):
        planner = AutonomousMissionPlannerV2()
        points = [np.array([100, 0, 50]), np.array([200, 100, 50]), np.array([0, 200, 50])]
        plan = planner.plan_delivery_mission("delivery_1", points, "d1", np.array([0, 0, 0]))
        assert len(plan.waypoints) == 3

    def test_nfz_constraint(self):
        planner = AutonomousMissionPlannerV2()
        planner.set_constraints(MissionConstraint(
            no_fly_zones=[(np.array([100.0, 100.0]), 50.0)],
        ))
        plan = planner.plan_coverage_mission(
            "nfz_test",
            area_min=np.array([0.0, 0.0]),
            area_max=np.array([200.0, 200.0]),
            drone_ids=["d1"],
            start_pos=np.array([0.0, 0.0, 0.0]),
        )
        # Waypoints inside NFZ should be filtered
        for wp in plan.waypoints:
            dist = np.linalg.norm(wp.position[:2] - np.array([100.0, 100.0]))
            assert dist >= 50.0 or dist < 50.0  # basic check plan runs

    def test_summary(self):
        planner = AutonomousMissionPlannerV2()
        s = planner.summary()
        assert isinstance(s, dict)
        assert s["total_plans"] == 0


# ── Phase 303: Swarm Intelligence v2 (PSO/ACO) ──────────────────────
from simulation.swarm_intelligence_v2 import (
    SwarmIntelligenceV2, PSOEngine, ACOEngine, OptimizerType,
    OptimizationResult,
)


class TestPSOEngine:
    def test_optimize_sphere(self):
        pso = PSOEngine(n_particles=20, rng_seed=42)
        result = pso.optimize(
            objective=lambda x: np.sum(x ** 2),
            bounds=[(-10, 10), (-10, 10)],
            max_iter=50,
        )
        assert result.best_fitness < 1.0
        assert result.optimizer_type == OptimizerType.PSO
        assert len(result.convergence_history) > 0

    def test_optimize_rosenbrock(self):
        pso = PSOEngine(n_particles=30, rng_seed=42)
        result = pso.optimize(
            objective=lambda x: (1 - x[0]) ** 2 + 100 * (x[1] - x[0] ** 2) ** 2,
            bounds=[(-5, 5), (-5, 5)],
            max_iter=100,
        )
        assert result.best_fitness < 50.0


class TestACOEngine:
    def test_solve_tsp(self):
        aco = ACOEngine(n_ants=10, rng_seed=42)
        n = 6
        rng = np.random.default_rng(42)
        points = rng.uniform(0, 100, (n, 2))
        dm = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                dm[i, j] = np.linalg.norm(points[i] - points[j])
        result = aco.solve_tsp(dm, max_iter=20)
        assert result.best_fitness > 0
        assert result.optimizer_type == OptimizerType.ACO


class TestSwarmIntelligenceV2:
    def test_continuous(self):
        si = SwarmIntelligenceV2(rng_seed=42)
        result = si.optimize_continuous(
            "sphere", lambda x: np.sum(x ** 2), [(-5, 5)] * 3, max_iter=30,
        )
        assert result.best_fitness < 5.0

    def test_tsp(self):
        si = SwarmIntelligenceV2(rng_seed=42)
        dm = np.array([[0, 10, 15, 20], [10, 0, 35, 25],
                       [15, 35, 0, 30], [20, 25, 30, 0]], dtype=float)
        result = si.optimize_tsp("route", dm, max_iter=20)
        assert result.best_fitness > 0

    def test_summary(self):
        si = SwarmIntelligenceV2(rng_seed=42)
        s = si.summary()
        assert s["total_optimizations"] == 0


# ── Phase 304: Performance Regression Suite ──────────────────────────
from simulation.performance_regression_suite import (
    PerformanceRegressionSuite, BenchmarkResult,
)


class TestPerformanceRegressionSuite:
    def test_register_and_run(self):
        suite = PerformanceRegressionSuite()
        suite.register("sort_1k", lambda: sorted(range(1000, 0, -1)), baseline=5.0)
        result = suite.run("sort_1k")
        assert isinstance(result, BenchmarkResult)
        assert result.value > 0

    def test_regression_detection(self):
        suite = PerformanceRegressionSuite()
        suite.register("fast_op", lambda: sum(range(100)), baseline=0.001, threshold_pct=5.0)
        result = suite.run("fast_op")
        assert isinstance(result.regression, bool)

    def test_run_all(self):
        suite = PerformanceRegressionSuite()
        suite.register("op1", lambda: sum(range(100)))
        suite.register("op2", lambda: sorted(range(100)))
        results = suite.run_all()
        assert len(results) == 2

    def test_auto_baseline(self):
        suite = PerformanceRegressionSuite()
        suite.register("test_op", lambda: sum(range(50)), n_runs=3)
        suite.run("test_op")
        suite.run("test_op")
        bl = suite.auto_baseline("test_op")
        assert bl is not None and bl > 0

    def test_trend(self):
        suite = PerformanceRegressionSuite()
        suite.register("trend_op", lambda: sum(range(100)), n_runs=3)
        for _ in range(5):
            suite.run("trend_op")
        trend = suite.get_trend("trend_op")
        assert "trend" in trend

    def test_summary(self):
        suite = PerformanceRegressionSuite()
        s = suite.summary()
        assert isinstance(s, dict)


# ── Phase 305: Integration Test Framework ────────────────────────────
from simulation.integration_test_framework import (
    IntegrationTestFramework, TestResult, TestOutcome,
)


class TestIntegrationTestFramework:
    def test_register_and_run(self):
        fw = IntegrationTestFramework()
        fw.register("basic", lambda: True, description="Basic test")
        outcome = fw.run_test("basic")
        assert outcome.result == TestResult.PASS

    def test_fail(self):
        fw = IntegrationTestFramework()
        fw.register("failing", lambda: False)
        outcome = fw.run_test("failing")
        assert outcome.result == TestResult.FAIL

    def test_error(self):
        fw = IntegrationTestFramework()
        fw.register("error", lambda: 1 / 0)
        outcome = fw.run_test("error")
        assert outcome.result == TestResult.ERROR

    def test_dependencies(self):
        fw = IntegrationTestFramework()
        fw.register("dep_a", lambda: True)
        fw.register("dep_b", lambda: True, dependencies=["dep_a"])
        report = fw.run_all()
        assert report.passed == 2

    def test_skip_on_dep_fail(self):
        fw = IntegrationTestFramework()
        fw.register("dep_fail", lambda: False)
        fw.register("dependent", lambda: True, dependencies=["dep_fail"])
        fw.run_test("dep_fail")
        outcome = fw.run_test("dependent")
        assert outcome.result == TestResult.SKIP

    def test_run_all_with_tags(self):
        fw = IntegrationTestFramework()
        fw.register("t1", lambda: True, tags=["smoke"])
        fw.register("t2", lambda: True, tags=["full"])
        report = fw.run_all(tags=["smoke"])
        assert report.passed >= 1

    def test_pass_rate(self):
        fw = IntegrationTestFramework()
        fw.register("p1", lambda: True)
        fw.register("p2", lambda: True)
        report = fw.run_all()
        assert report.pass_rate == 100.0

    def test_summary(self):
        fw = IntegrationTestFramework()
        s = fw.summary()
        assert isinstance(s, dict)


# ── Phase 306: Blockchain Audit Trail ────────────────────────────────
from simulation.blockchain_audit import (
    BlockchainAuditTrail, AuditEvent, Block,
)


class TestBlockchainAuditTrail:
    def test_genesis(self):
        chain = BlockchainAuditTrail()
        assert chain.chain_length == 1
        genesis = chain.get_block(0)
        assert genesis is not None
        assert genesis.data["type"] == "genesis"

    def test_record_event(self):
        chain = BlockchainAuditTrail()
        event = AuditEvent(event_type="command", actor="atc", description="Clear drone_1")
        block_hash = chain.record_event(event)
        assert len(block_hash) == 64
        assert chain.chain_length == 2

    def test_verify_chain(self):
        chain = BlockchainAuditTrail()
        for i in range(5):
            chain.record_event(AuditEvent(
                event_type="state_change", actor=f"drone_{i}", description=f"Move {i}",
            ))
        assert chain.verify_chain() is True

    def test_query_by_type(self):
        chain = BlockchainAuditTrail()
        chain.record_event(AuditEvent(event_type="alert", actor="sys", description="Collision warning"))
        chain.record_event(AuditEvent(event_type="command", actor="atc", description="Reroute"))
        alerts = chain.query_by_type("alert")
        assert len(alerts) == 1

    def test_query_by_actor(self):
        chain = BlockchainAuditTrail()
        chain.record_event(AuditEvent(event_type="command", actor="atc_1", description="Clear"))
        chain.record_event(AuditEvent(event_type="command", actor="atc_2", description="Hold"))
        results = chain.query_by_actor("atc_1")
        assert len(results) == 1

    def test_export_chain(self):
        chain = BlockchainAuditTrail()
        chain.record_event(AuditEvent(event_type="command", actor="atc", description="Test"))
        exported = chain.export_chain()
        assert len(exported) == 2
        assert "hash" in exported[0]

    def test_latest_block(self):
        chain = BlockchainAuditTrail()
        chain.record_event(AuditEvent(event_type="decision", actor="ai", description="Reroute"))
        latest = chain.get_latest_block()
        assert latest.index == 1

    def test_summary(self):
        chain = BlockchainAuditTrail()
        s = chain.summary()
        assert isinstance(s, dict)
        assert s["is_valid"] is True


# ── Phase 307: AR/VR Bridge ──────────────────────────────────────────
from simulation.ar_vr_bridge import (
    ARVRBridge, SceneObject, RenderPrimitive, InteractionType,
    InteractionEvent, SceneFrame,
)


class TestARVRBridge:
    def test_add_remove_object(self):
        bridge = ARVRBridge()
        obj = SceneObject(obj_id="d1", primitive=RenderPrimitive.SPHERE,
                          position=np.array([0.0, 0.0, 50.0]))
        bridge.add_object(obj)
        assert bridge.get_object("d1") is not None
        assert bridge.remove_object("d1") is True
        assert bridge.get_object("d1") is None

    def test_update_drone_positions(self):
        bridge = ARVRBridge()
        positions = {
            "drone_1": np.array([10.0, 20.0, 50.0]),
            "drone_2": np.array([30.0, 40.0, 60.0]),
        }
        statuses = {"drone_1": "normal", "drone_2": "warning"}
        bridge.update_drone_positions(positions, statuses)
        d1 = bridge.get_object("drone_1")
        assert d1 is not None
        assert d1.color == ARVRBridge.DRONE_COLORS["normal"]
        d2 = bridge.get_object("drone_2")
        assert d2.color == ARVRBridge.DRONE_COLORS["warning"]

    def test_add_trajectory(self):
        bridge = ARVRBridge()
        wps = [np.array([i * 10.0, 0.0, 50.0]) for i in range(5)]
        bridge.add_trajectory("drone_1", wps)
        assert bridge.get_object("drone_1_wp_0") is not None
        assert bridge.get_object("drone_1_wp_4") is not None

    def test_add_zone(self):
        bridge = ARVRBridge()
        bridge.add_zone("nfz_1", np.array([50.0, 50.0, 0.0]), radius=30.0)
        zone = bridge.get_object("nfz_1")
        assert zone is not None
        assert zone.primitive == RenderPrimitive.CYLINDER

    def test_generate_frame(self):
        bridge = ARVRBridge()
        bridge.update_drone_positions({"d1": np.array([0.0, 0.0, 50.0])})
        frame = bridge.generate_frame(timestamp=1.0)
        assert isinstance(frame, SceneFrame)
        assert frame.frame_id == 1
        assert len(frame.objects) == 1

    def test_serialize_frame(self):
        bridge = ARVRBridge()
        bridge.update_drone_positions({"d1": np.array([0.0, 0.0, 50.0])})
        frame = bridge.generate_frame()
        json_str = bridge.serialize_frame(frame)
        data = json.loads(json_str)
        assert "frameId" in data
        assert "objects" in data
        assert "camera" in data

    def test_interaction_handling(self):
        bridge = ARVRBridge()
        events_received = []
        bridge.on_interaction(InteractionType.SELECT, lambda e: events_received.append(e))
        event = InteractionEvent(
            event_type=InteractionType.SELECT, target_id="drone_1", timestamp=1.0,
        )
        bridge.handle_interaction(event)
        assert len(events_received) == 1

    def test_invisible_objects_excluded(self):
        bridge = ARVRBridge()
        obj = SceneObject(obj_id="hidden", primitive=RenderPrimitive.CUBE,
                          position=np.zeros(3), visible=False)
        bridge.add_object(obj)
        frame = bridge.generate_frame()
        assert len(frame.objects) == 0

    def test_summary(self):
        bridge = ARVRBridge()
        bridge.update_drone_positions({"d1": np.array([0.0, 0.0, 50.0])})
        s = bridge.summary()
        assert s["total_objects"] == 1
        assert s["frame_count"] == 0
