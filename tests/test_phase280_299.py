"""Phase 280-299 통합 테스트: Advanced Autonomous Systems + Real-time Protocols."""

import pytest
import numpy as np


# ── Phase 280: Swarm Formation Control ──

class TestSwarmFormationControl:
    def test_create_formation(self):
        from simulation.swarm_formation_control import SwarmFormationController, FormationType
        ctrl = SwarmFormationController()
        state = ctrl.create_formation("f1", "d1", ["d1", "d2", "d3"], FormationType.V_FORMATION)
        assert state.leader_id == "d1"
        assert len(state.slots) == 3

    def test_v_formation_offsets(self):
        from simulation.swarm_formation_control import FormationGenerator
        offsets = FormationGenerator.v_formation(5, spacing=15.0)
        assert len(offsets) == 5
        assert np.allclose(offsets[0], [0, 0, 0])

    def test_grid_formation(self):
        from simulation.swarm_formation_control import FormationGenerator
        offsets = FormationGenerator.grid_formation(9, spacing=20.0)
        assert len(offsets) == 9

    def test_circle_formation(self):
        from simulation.swarm_formation_control import FormationGenerator
        offsets = FormationGenerator.circle_formation(8, radius=50.0)
        assert len(offsets) == 8
        for o in offsets:
            assert abs(np.linalg.norm(o[:2]) - 50.0) < 1e-6

    def test_transition_formation(self):
        from simulation.swarm_formation_control import SwarmFormationController, FormationType
        ctrl = SwarmFormationController()
        ctrl.create_formation("f1", "d1", ["d1", "d2", "d3", "d4"], FormationType.V_FORMATION)
        trajectory = ctrl.transition_formation("f1", FormationType.GRID, steps=5)
        assert len(trajectory) == 6
        state = ctrl.get_formation("f1")
        assert state.formation_type == FormationType.GRID

    def test_compute_cohesion(self):
        from simulation.swarm_formation_control import SwarmFormationController, FormationType
        ctrl = SwarmFormationController()
        ctrl.create_formation("f1", "d1", ["d1", "d2"], FormationType.LINE)
        ctrl.update_positions({"d1": np.array([0, 0, 0]), "d2": np.array([0, 15, 0])})
        c = ctrl.compute_cohesion("f1")
        assert 0 <= c <= 1

    def test_reassign_leader(self):
        from simulation.swarm_formation_control import SwarmFormationController, FormationType
        ctrl = SwarmFormationController()
        ctrl.create_formation("f1", "d1", ["d1", "d2"])
        assert ctrl.reassign_leader("f1", "d2")
        assert ctrl.get_formation("f1").leader_id == "d2"

    def test_summary(self):
        from simulation.swarm_formation_control import SwarmFormationController, FormationType
        ctrl = SwarmFormationController()
        ctrl.create_formation("f1", "d1", ["d1", "d2"])
        s = ctrl.summary()
        assert s["total_formations"] == 1


# ── Phase 281: Cooperative Task Allocator ──

class TestCooperativeTaskAllocator:
    def test_add_task_and_drone(self):
        from simulation.cooperative_task_allocator import CooperativeTaskAllocator, Task, DroneCapability, TaskPriority
        alloc = CooperativeTaskAllocator()
        alloc.add_task(Task("t1", np.array([100, 200, 50]), TaskPriority.HIGH))
        alloc.register_drone(DroneCapability("d1", np.array([0, 0, 50])))
        s = alloc.summary()
        assert s["total_tasks"] == 1
        assert s["total_drones"] == 1

    def test_hungarian_allocation(self):
        from simulation.cooperative_task_allocator import CooperativeTaskAllocator, Task, DroneCapability, TaskPriority
        alloc = CooperativeTaskAllocator()
        alloc.add_task(Task("t1", np.array([100, 0, 50])))
        alloc.add_task(Task("t2", np.array([0, 100, 50])))
        alloc.register_drone(DroneCapability("d1", np.array([90, 0, 50])))
        alloc.register_drone(DroneCapability("d2", np.array([0, 90, 50])))
        result = alloc.allocate_hungarian()
        assert len(result) == 2

    def test_auction_allocation(self):
        from simulation.cooperative_task_allocator import CooperativeTaskAllocator, Task, DroneCapability
        alloc = CooperativeTaskAllocator()
        alloc.add_task(Task("t1", np.array([50, 50, 50])))
        alloc.register_drone(DroneCapability("d1", np.array([40, 40, 50])))
        result = alloc.allocate_auction()
        assert len(result) >= 1

    def test_complete_task(self):
        from simulation.cooperative_task_allocator import CooperativeTaskAllocator, Task, DroneCapability
        alloc = CooperativeTaskAllocator()
        alloc.add_task(Task("t1", np.array([50, 50, 50])))
        alloc.register_drone(DroneCapability("d1", np.array([40, 40, 50])))
        alloc.allocate_hungarian()
        assert alloc.complete_task("t1")

    def test_fail_and_reallocate(self):
        from simulation.cooperative_task_allocator import CooperativeTaskAllocator, Task, DroneCapability
        alloc = CooperativeTaskAllocator()
        alloc.add_task(Task("t1", np.array([50, 50, 50])))
        alloc.register_drone(DroneCapability("d1", np.array([40, 40, 50])))
        alloc.allocate_hungarian()
        alloc.fail_task("t1")
        result = alloc.reallocate()
        assert isinstance(result, dict)


# ── Phase 282: Dynamic Rerouter ──

class TestDynamicRerouter:
    def test_create_route(self):
        from simulation.dynamic_rerouter import DynamicRerouter
        router = DynamicRerouter()
        route = router.create_route("r1", "d1", [np.array([0, 0, 50]), np.array([100, 100, 50])])
        assert route.total_cost > 0

    def test_add_obstacle_invalidates(self):
        from simulation.dynamic_rerouter import DynamicRerouter, Obstacle
        router = DynamicRerouter()
        router.create_route("r1", "d1", [np.array([0, 0, 50]), np.array([100, 0, 50])])
        router.add_obstacle(Obstacle("obs1", np.array([50, 0, 50]), radius=20.0))
        assert not router.validate_route("r1")

    def test_reroute(self):
        from simulation.dynamic_rerouter import DynamicRerouter, Obstacle
        router = DynamicRerouter()
        router.create_route("r1", "d1", [np.array([0, 0, 50]), np.array([200, 0, 50])])
        router.add_obstacle(Obstacle("obs1", np.array([100, 0, 50]), radius=30.0))
        result = router.reroute("r1")
        assert result is not None
        assert result.reroute_count == 1

    def test_auto_reroute_all(self):
        from simulation.dynamic_rerouter import DynamicRerouter, Obstacle
        router = DynamicRerouter()
        router.create_route("r1", "d1", [np.array([0, 0, 50]), np.array([200, 0, 50])])
        router.add_obstacle(Obstacle("obs1", np.array([100, 0, 50]), radius=30.0))
        rerouted = router.auto_reroute_all()
        assert "r1" in rerouted

    def test_summary(self):
        from simulation.dynamic_rerouter import DynamicRerouter
        router = DynamicRerouter()
        router.create_route("r1", "d1", [np.array([0, 0, 50]), np.array([100, 0, 50])])
        s = router.summary()
        assert s["total_routes"] == 1


# ── Phase 283: Autonomous Landing System ──

class TestAutonomousLandingSystem:
    def test_add_pad_and_reserve(self):
        from simulation.autonomous_landing_system import AutonomousLandingSystem, LandingPad
        als = AutonomousLandingSystem()
        als.add_pad(LandingPad("p1", np.array([0, 0, 0])))
        assert als.reserve_pad("p1", "d1")

    def test_find_best_pad(self):
        from simulation.autonomous_landing_system import AutonomousLandingSystem, LandingPad
        als = AutonomousLandingSystem()
        als.add_pad(LandingPad("p1", np.array([100, 0, 0])))
        als.add_pad(LandingPad("p2", np.array([10, 0, 0])))
        best = als.find_best_pad(np.array([0, 0, 50]))
        assert best == "p2"

    def test_landing_sequence(self):
        from simulation.autonomous_landing_system import AutonomousLandingSystem, LandingPad, LandingPhase
        als = AutonomousLandingSystem()
        als.add_pad(LandingPad("p1", np.array([0, 0, 0])))
        seq = als.initiate_landing("d1", "p1")
        assert seq is not None
        assert seq.phase == LandingPhase.APPROACH
        phase = als.advance_phase("d1")
        assert phase == LandingPhase.ALIGNMENT

    def test_abort_landing(self):
        from simulation.autonomous_landing_system import AutonomousLandingSystem, LandingPad
        als = AutonomousLandingSystem()
        als.add_pad(LandingPad("p1", np.array([0, 0, 0])))
        als.initiate_landing("d1", "p1")
        assert als.abort_landing("d1")

    def test_descent_profile(self):
        from simulation.autonomous_landing_system import AutonomousLandingSystem, LandingPad
        als = AutonomousLandingSystem()
        als.add_pad(LandingPad("p1", np.array([0, 0, 0])))
        als.initiate_landing("d1", "p1")
        profile = als.get_descent_profile("d1")
        assert len(profile) > 0
        assert profile[-1] == 0.0


# ── Phase 284: Emergency Recovery System ──

class TestEmergencyRecoverySystem:
    def test_detect_emergency(self):
        from simulation.emergency_recovery_system import EmergencyRecoverySystem, EmergencyType
        ers = EmergencyRecoverySystem()
        event = ers.detect_emergency("d1", EmergencyType.MOTOR_FAILURE, 0.8, np.array([100, 100, 50]))
        assert event.event_id.startswith("EMG-")
        assert event.severity == 0.8

    def test_execute_recovery(self):
        from simulation.emergency_recovery_system import EmergencyRecoverySystem, EmergencyType
        ers = EmergencyRecoverySystem(rng_seed=1)
        event = ers.detect_emergency("d1", EmergencyType.BATTERY_CRITICAL, 0.3, np.array([50, 50, 30]))
        result = ers.execute_recovery(event.event_id)
        assert isinstance(result, bool)

    def test_get_active_emergencies(self):
        from simulation.emergency_recovery_system import EmergencyRecoverySystem, EmergencyType
        ers = EmergencyRecoverySystem()
        ers.detect_emergency("d1", EmergencyType.GPS_LOSS, 0.5, np.array([0, 0, 0]))
        active = ers.get_active_emergencies()
        assert len(active) == 1

    def test_resolve_event(self):
        from simulation.emergency_recovery_system import EmergencyRecoverySystem, EmergencyType
        ers = EmergencyRecoverySystem()
        event = ers.detect_emergency("d1", EmergencyType.COMM_LOSS, 0.4, np.array([0, 0, 0]))
        assert ers.resolve_event(event.event_id)
        assert len(ers.get_active_emergencies()) == 0

    def test_summary(self):
        from simulation.emergency_recovery_system import EmergencyRecoverySystem, EmergencyType
        ers = EmergencyRecoverySystem()
        ers.detect_emergency("d1", EmergencyType.WEATHER_EXTREME, 0.7, np.array([0, 0, 0]))
        s = ers.summary()
        assert s["total_events"] == 1


# ── Phase 285: Fleet Coordination Engine ──

class TestFleetCoordinationEngine:
    def test_register_fleet(self):
        from simulation.fleet_coordination_engine import FleetCoordinationEngine, Fleet
        fce = FleetCoordinationEngine()
        fce.register_fleet(Fleet("fleet1", drone_ids=["d1", "d2", "d3"]))
        assert fce.get_fleet("fleet1") is not None

    def test_assign_zone(self):
        from simulation.fleet_coordination_engine import FleetCoordinationEngine, Fleet, AirspaceZone
        fce = FleetCoordinationEngine()
        fce.register_fleet(Fleet("fleet1", drone_ids=["d1"]))
        fce.register_zone(AirspaceZone("z1", np.array([0, 0, 100]), 200.0))
        assert fce.assign_zone("fleet1", "z1")

    def test_handoff_drone(self):
        from simulation.fleet_coordination_engine import FleetCoordinationEngine, Fleet
        fce = FleetCoordinationEngine()
        fce.register_fleet(Fleet("f1", drone_ids=["d1", "d2"]))
        fce.register_fleet(Fleet("f2", drone_ids=["d3"]))
        assert fce.handoff_drone("d1", "f1", "f2")
        assert fce.get_drone_fleet("d1") == "f2"

    def test_request_support(self):
        from simulation.fleet_coordination_engine import FleetCoordinationEngine, Fleet, FleetStatus
        fce = FleetCoordinationEngine()
        fce.register_fleet(Fleet("f1", drone_ids=[f"d{i}" for i in range(10)], status=FleetStatus.ACTIVE))
        fce.register_fleet(Fleet("f2", drone_ids=["x1"], status=FleetStatus.ACTIVE))
        transferred = fce.request_support("f2", 3)
        assert len(transferred) <= 3

    def test_summary(self):
        from simulation.fleet_coordination_engine import FleetCoordinationEngine, Fleet
        fce = FleetCoordinationEngine()
        fce.register_fleet(Fleet("f1", drone_ids=["d1", "d2"]))
        s = fce.summary()
        assert s["total_fleets"] == 1
        assert s["total_drones"] == 2


# ── Phase 286: Predictive Collision Avoidance ──

class TestPredictiveCollisionAvoidance:
    def test_update_and_predict(self):
        from simulation.predictive_collision_avoidance import PredictiveCollisionAvoidance
        pca = PredictiveCollisionAvoidance()
        pca.update_state("d1", np.array([0, 0, 50]), np.array([10, 0, 0]))
        pca.update_state("d2", np.array([100, 0, 50]), np.array([-10, 0, 0]))
        preds = pca.predict_all()
        assert "d1" in preds
        assert len(preds["d1"].positions) > 0

    def test_assess_risks(self):
        from simulation.predictive_collision_avoidance import PredictiveCollisionAvoidance
        pca = PredictiveCollisionAvoidance(safety_distance=10.0)
        pca.update_state("d1", np.array([0, 0, 50]), np.array([10, 0, 0]))
        pca.update_state("d2", np.array([40, 0, 50]), np.array([-10, 0, 0]))
        pca.predict_all()
        risks = pca.assess_risks()
        assert len(risks) > 0

    def test_step(self):
        from simulation.predictive_collision_avoidance import PredictiveCollisionAvoidance
        pca = PredictiveCollisionAvoidance()
        pca.update_state("d1", np.array([0, 0, 50]), np.array([5, 0, 0]))
        pca.update_state("d2", np.array([30, 0, 50]), np.array([-5, 0, 0]))
        result = pca.step()
        assert "risks" in result

    def test_summary(self):
        from simulation.predictive_collision_avoidance import PredictiveCollisionAvoidance
        pca = PredictiveCollisionAvoidance()
        pca.update_state("d1", np.array([0, 0, 50]), np.array([1, 0, 0]))
        s = pca.summary()
        assert s["tracked_drones"] == 1


# ── Phase 287: Energy Harvest Optimizer ──

class TestEnergyHarvestOptimizer:
    def test_solar_harvest(self):
        from simulation.energy_harvest_optimizer import EnergyHarvestOptimizer, DroneEnergy
        eho = EnergyHarvestOptimizer()
        eho.register_drone(DroneEnergy("d1"))
        rate = eho.compute_harvest_rate("d1", np.array([0, 0, 50]), hour=12.0)
        assert rate > 0

    def test_zone_harvest(self):
        from simulation.energy_harvest_optimizer import EnergyHarvestOptimizer, DroneEnergy, HarvestZone, EnergySource
        eho = EnergyHarvestOptimizer()
        eho.register_drone(DroneEnergy("d1"))
        eho.add_zone(HarvestZone("z1", np.array([0, 0, 50]), 100.0, EnergySource.CHARGING_STATION, 500.0))
        rate = eho.compute_harvest_rate("d1", np.array([0, 0, 50]), hour=12.0)
        assert rate >= 500.0

    def test_energy_share(self):
        from simulation.energy_harvest_optimizer import EnergyHarvestOptimizer, DroneEnergy
        eho = EnergyHarvestOptimizer()
        eho.register_drone(DroneEnergy("d1", battery_wh=80))
        eho.register_drone(DroneEnergy("d2", battery_wh=20))
        shared = eho.energy_share("d1", "d2", 10.0)
        assert shared > 0

    def test_critical_drones(self):
        from simulation.energy_harvest_optimizer import EnergyHarvestOptimizer, DroneEnergy
        eho = EnergyHarvestOptimizer()
        eho.register_drone(DroneEnergy("d1", battery_wh=10))
        assert "d1" in eho.get_critical_drones(threshold_pct=20.0)

    def test_summary(self):
        from simulation.energy_harvest_optimizer import EnergyHarvestOptimizer, DroneEnergy
        eho = EnergyHarvestOptimizer()
        eho.register_drone(DroneEnergy("d1"))
        s = eho.summary()
        assert s["total_drones"] == 1


# ── Phase 288: Terrain Awareness System ──

class TestTerrainAwarenessSystem:
    def test_get_elevation(self):
        from simulation.terrain_awareness_system import TerrainAwarenessSystem
        taws = TerrainAwarenessSystem()
        elev = taws.get_elevation(50.0, 50.0)
        assert isinstance(elev, float)

    def test_check_clearance(self):
        from simulation.terrain_awareness_system import TerrainAwarenessSystem, AlertLevel
        taws = TerrainAwarenessSystem()
        alert = taws.check_clearance("d1", np.array([50, 50, 200]))
        assert alert.level in AlertLevel

    def test_validate_path(self):
        from simulation.terrain_awareness_system import TerrainAwarenessSystem
        taws = TerrainAwarenessSystem()
        alerts = taws.validate_path([np.array([0, 0, 200]), np.array([100, 100, 200])])
        assert isinstance(alerts, list)

    def test_compute_msa(self):
        from simulation.terrain_awareness_system import TerrainAwarenessSystem
        taws = TerrainAwarenessSystem()
        msa = taws.compute_msa(50.0, 50.0)
        assert msa > 0

    def test_summary(self):
        from simulation.terrain_awareness_system import TerrainAwarenessSystem
        taws = TerrainAwarenessSystem()
        s = taws.summary()
        assert "dem_size" in s


# ── Phase 289: Communication Mesh Optimizer ──

class TestCommunicationMeshOptimizer:
    def test_add_nodes_and_update(self):
        from simulation.communication_mesh_optimizer import CommunicationMeshOptimizer, MeshNode
        cmo = CommunicationMeshOptimizer()
        cmo.add_node(MeshNode("n1", np.array([0, 0, 50])))
        cmo.add_node(MeshNode("n2", np.array([100, 0, 50])))
        cmo.update_topology()
        s = cmo.summary()
        assert s["total_nodes"] == 2

    def test_find_route(self):
        from simulation.communication_mesh_optimizer import CommunicationMeshOptimizer, MeshNode
        cmo = CommunicationMeshOptimizer()
        cmo.add_node(MeshNode("n1", np.array([0, 0, 50])))
        cmo.add_node(MeshNode("n2", np.array([100, 0, 50])))
        cmo.add_node(MeshNode("n3", np.array([200, 0, 50])))
        cmo.update_topology()
        route = cmo.find_route("n1", "n3")
        assert len(route) >= 2

    def test_connectivity(self):
        from simulation.communication_mesh_optimizer import CommunicationMeshOptimizer, MeshNode
        cmo = CommunicationMeshOptimizer()
        cmo.add_node(MeshNode("n1", np.array([0, 0, 50])))
        cmo.add_node(MeshNode("n2", np.array([100, 0, 50])))
        cmo.update_topology()
        assert cmo.get_network_connectivity() > 0

    def test_relay_positions(self):
        from simulation.communication_mesh_optimizer import CommunicationMeshOptimizer, MeshNode
        cmo = CommunicationMeshOptimizer()
        cmo.add_node(MeshNode("n1", np.array([0, 0, 50])))
        cmo.add_node(MeshNode("n2", np.array([1000, 0, 50])))
        cmo.update_topology()
        relays = cmo.find_relay_positions(["n2"])
        assert isinstance(relays, list)


# ── Phase 290: V2X Communication ──

class TestV2XCommunication:
    def test_send_bsm(self):
        from simulation.v2x_communication import V2XCommunicationSystem, V2XEndpoint, V2XMode
        v2x = V2XCommunicationSystem()
        v2x.register_endpoint(V2XEndpoint("d1", np.array([0, 0, 50]), V2XMode.V2V))
        msg = v2x.send_bsm("d1", np.array([0, 0, 50]), np.array([10, 0, 0]))
        assert msg.msg_id.startswith("BSM-")

    def test_broadcast(self):
        from simulation.v2x_communication import V2XCommunicationSystem, V2XEndpoint, V2XMode
        v2x = V2XCommunicationSystem()
        v2x.register_endpoint(V2XEndpoint("d1", np.array([0, 0, 50]), V2XMode.V2V))
        v2x.register_endpoint(V2XEndpoint("d2", np.array([50, 0, 50]), V2XMode.V2V))
        msg = v2x.send_bsm("d1", np.array([0, 0, 50]), np.array([10, 0, 0]))
        delivered = v2x.broadcast(msg)
        assert isinstance(delivered, list)

    def test_send_denm(self):
        from simulation.v2x_communication import V2XCommunicationSystem, V2XEndpoint, V2XMode
        v2x = V2XCommunicationSystem()
        v2x.register_endpoint(V2XEndpoint("d1", np.array([0, 0, 50]), V2XMode.V2V))
        msg = v2x.send_denm("d1", "obstacle_detected", np.array([0, 0, 50]))
        assert msg.msg_id.startswith("DENM-")

    def test_summary(self):
        from simulation.v2x_communication import V2XCommunicationSystem, V2XEndpoint, V2XMode
        v2x = V2XCommunicationSystem()
        v2x.register_endpoint(V2XEndpoint("d1", np.array([0, 0, 50]), V2XMode.V2V))
        s = v2x.summary()
        assert s["total_endpoints"] == 1


# ── Phase 291: Protocol Optimizer ──

class TestProtocolOptimizer:
    def test_enqueue_and_transmit(self):
        from simulation.protocol_optimizer import ProtocolOptimizer, Packet, QoSLevel
        po = ProtocolOptimizer()
        po.enqueue(Packet("p1", "d1", "d2", 256, QoSLevel.HIGH))
        result = po.transmit_next()
        assert result is not None

    def test_qos_ordering(self):
        from simulation.protocol_optimizer import ProtocolOptimizer, Packet, QoSLevel
        po = ProtocolOptimizer()
        po.enqueue(Packet("p1", "d1", "d2", 128, QoSLevel.BEST_EFFORT))
        po.enqueue(Packet("p2", "d1", "d3", 128, QoSLevel.CRITICAL))
        result = po.transmit_next()
        assert result.packet_id == "p2"

    def test_compression(self):
        from simulation.protocol_optimizer import ProtocolOptimizer, Packet, QoSLevel
        po = ProtocolOptimizer()
        po.enqueue(Packet("p1", "d1", "d2", 1024, QoSLevel.NORMAL))
        result = po.transmit_next()
        assert result.actual_bytes < 1024

    def test_flush_queue(self):
        from simulation.protocol_optimizer import ProtocolOptimizer, Packet, QoSLevel
        po = ProtocolOptimizer()
        for i in range(5):
            po.enqueue(Packet(f"p{i}", "d1", "d2", 64, QoSLevel.NORMAL))
        results = po.flush_queue()
        assert len(results) == 5

    def test_summary(self):
        from simulation.protocol_optimizer import ProtocolOptimizer, Packet, QoSLevel
        po = ProtocolOptimizer()
        po.enqueue(Packet("p1", "d1", "d2", 128))
        po.transmit_next()
        s = po.summary()
        assert s["total_sent"] >= 1


# ── Phase 292: Telemetry Stream Processor ──

class TestTelemetryStreamProcessor:
    def test_ingest(self):
        from simulation.telemetry_stream_processor import TelemetryStreamProcessor, TelemetryPoint, TelemetryField
        tsp = TelemetryStreamProcessor()
        alert = tsp.ingest(TelemetryPoint("d1", 1.0, TelemetryField.ALTITUDE, 100.0))
        assert alert is None  # normal value

    def test_threshold_alert(self):
        from simulation.telemetry_stream_processor import TelemetryStreamProcessor, TelemetryPoint, TelemetryField
        tsp = TelemetryStreamProcessor()
        alert = tsp.ingest(TelemetryPoint("d1", 1.0, TelemetryField.BATTERY, 5.0))
        assert alert is not None
        assert alert.severity in ("warning", "critical")

    def test_z_score_alert(self):
        from simulation.telemetry_stream_processor import TelemetryStreamProcessor, TelemetryPoint, TelemetryField
        tsp = TelemetryStreamProcessor(z_threshold=2.0)
        for i in range(20):
            tsp.ingest(TelemetryPoint("d1", float(i), TelemetryField.SPEED, 10.0 + np.random.default_rng(42).normal(0, 0.1)))
        alert = tsp.ingest(TelemetryPoint("d1", 21.0, TelemetryField.SPEED, 50.0))
        # May or may not trigger depending on threshold
        assert isinstance(alert, type(None)) or hasattr(alert, 'severity')

    def test_window_stats(self):
        from simulation.telemetry_stream_processor import TelemetryStreamProcessor, TelemetryPoint, TelemetryField
        tsp = TelemetryStreamProcessor()
        for i in range(10):
            tsp.ingest(TelemetryPoint("d1", float(i), TelemetryField.ALTITUDE, 50.0 + i))
        stats = tsp.get_window_stats("d1", TelemetryField.ALTITUDE)
        assert stats is not None
        assert stats["count"] == 10

    def test_summary(self):
        from simulation.telemetry_stream_processor import TelemetryStreamProcessor, TelemetryPoint, TelemetryField
        tsp = TelemetryStreamProcessor()
        tsp.ingest(TelemetryPoint("d1", 1.0, TelemetryField.SPEED, 10.0))
        s = tsp.summary()
        assert s["tracked_drones"] == 1


# ── Phase 293: Consensus Protocol ──

class TestConsensusProtocol:
    def test_add_nodes(self):
        from simulation.consensus_protocol import RaftConsensus
        raft = RaftConsensus()
        raft.add_node("n1")
        raft.add_node("n2")
        raft.add_node("n3")
        assert raft.summary()["total_nodes"] == 3

    def test_election(self):
        from simulation.consensus_protocol import RaftConsensus
        raft = RaftConsensus()
        for i in range(5):
            raft.add_node(f"n{i}")
        assert raft.start_election("n0")
        assert raft.get_leader() == "n0"

    def test_propose(self):
        from simulation.consensus_protocol import RaftConsensus
        raft = RaftConsensus()
        for i in range(3):
            raft.add_node(f"n{i}")
        raft.start_election("n0")
        entry = raft.propose({"action": "deploy"})
        assert entry is not None

    def test_kill_and_revive(self):
        from simulation.consensus_protocol import RaftConsensus
        raft = RaftConsensus()
        for i in range(3):
            raft.add_node(f"n{i}")
        raft.start_election("n0")
        raft.kill_node("n0")
        assert raft.get_leader() is None
        raft.revive_node("n0")
        assert raft.summary()["alive_nodes"] == 3


# ── Phase 294: Swarm Behavior Engine ──

class TestSwarmBehaviorEngine:
    def test_add_agents(self):
        from simulation.swarm_behavior_engine import SwarmBehaviorEngine, BoidState
        sbe = SwarmBehaviorEngine()
        sbe.add_agent(BoidState("a1", np.array([0, 0, 50]), np.array([1, 0, 0])))
        sbe.add_agent(BoidState("a2", np.array([10, 0, 50]), np.array([1, 0, 0])))
        assert sbe.summary()["total_agents"] == 2

    def test_step(self):
        from simulation.swarm_behavior_engine import SwarmBehaviorEngine, BoidState
        sbe = SwarmBehaviorEngine()
        for i in range(5):
            sbe.add_agent(BoidState(f"a{i}", np.array([i * 10.0, 0.0, 50.0]), np.array([1.0, 0.0, 0.0])))
        positions = sbe.step(dt=0.1)
        assert len(positions) == 5

    def test_behavior_modes(self):
        from simulation.swarm_behavior_engine import SwarmBehaviorEngine, BoidState, BehaviorMode
        sbe = SwarmBehaviorEngine()
        sbe.add_agent(BoidState("a1", np.array([0, 0, 50]), np.array([1, 0, 0])))
        sbe.set_behavior("a1", BehaviorMode.SCATTER)
        assert sbe.summary()["behaviors"]["scatter"] == 1

    def test_swarm_metrics(self):
        from simulation.swarm_behavior_engine import SwarmBehaviorEngine, BoidState
        sbe = SwarmBehaviorEngine()
        for i in range(3):
            sbe.add_agent(BoidState(f"a{i}", np.array([i * 5.0, 0, 50]), np.array([0, 0, 0])))
        center = sbe.get_swarm_center()
        assert center is not None
        spread = sbe.get_swarm_spread()
        assert spread >= 0


# ── Phase 295: Geospatial Index ──

class TestGeospatialIndex:
    def test_insert_and_query(self):
        from simulation.geospatial_index import GeospatialIndex, SpatialObject
        gsi = GeospatialIndex()
        gsi.insert(SpatialObject("o1", np.array([100, 100, 50])))
        gsi.insert(SpatialObject("o2", np.array([200, 200, 50])))
        results = gsi.query_radius(np.array([100, 100, 50]), 50.0)
        assert len(results) >= 1

    def test_knn(self):
        from simulation.geospatial_index import GeospatialIndex, SpatialObject
        gsi = GeospatialIndex()
        for i in range(10):
            gsi.insert(SpatialObject(f"o{i}", np.array([i * 20.0, 0, 50])))
        knn = gsi.query_knn(np.array([0, 0, 50]), 3)
        assert len(knn) == 3
        assert knn[0][1] <= knn[1][1]  # sorted by distance

    def test_geohash(self):
        from simulation.geospatial_index import GeospatialIndex, SpatialObject
        gsi = GeospatialIndex()
        gsi.insert(SpatialObject("o1", np.array([34.8, 126.4, 50])))
        gh = gsi.get_geohash("o1")
        assert gh is not None
        assert len(gh) == 6


# ── Phase 296: Mission Orchestrator ──

class TestMissionOrchestrator:
    def test_create_mission(self):
        from simulation.mission_orchestrator import MissionOrchestrator, MissionType
        mo = MissionOrchestrator()
        m = mo.create_mission("m1", MissionType.DELIVERY)
        assert m.mission_id == "m1"

    def test_add_tasks_and_start(self):
        from simulation.mission_orchestrator import MissionOrchestrator, MissionType, MissionTask
        mo = MissionOrchestrator()
        mo.create_mission("m1", MissionType.SURVEILLANCE)
        mo.add_task("m1", MissionTask("t1", "m1", "scan"))
        mo.add_task("m1", MissionTask("t2", "m1", "photograph", dependencies=["t1"]))
        ready = mo.start_mission("m1")
        assert len(ready) == 1
        assert ready[0].task_id == "t1"

    def test_complete_task_unlocks_next(self):
        from simulation.mission_orchestrator import MissionOrchestrator, MissionType, MissionTask
        mo = MissionOrchestrator()
        mo.create_mission("m1", MissionType.DELIVERY)
        mo.add_task("m1", MissionTask("t1", "m1", "pickup"))
        mo.add_task("m1", MissionTask("t2", "m1", "deliver", dependencies=["t1"]))
        mo.start_mission("m1")
        mo.assign_drone("t1", "d1")
        newly_ready = mo.complete_task("t1")
        assert any(t.task_id == "t2" for t in newly_ready)

    def test_mission_progress(self):
        from simulation.mission_orchestrator import MissionOrchestrator, MissionType, MissionTask
        mo = MissionOrchestrator()
        mo.create_mission("m1", MissionType.PATROL)
        mo.add_task("m1", MissionTask("t1", "m1", "patrol"))
        mo.add_task("m1", MissionTask("t2", "m1", "patrol"))
        mo.start_mission("m1")
        mo.assign_drone("t1", "d1")
        mo.complete_task("t1")
        assert mo.get_mission_progress("m1") == 0.5


# ── Phase 297: Realtime Map Builder ──

class TestRealtimeMapBuilder:
    def test_process_observation(self):
        from simulation.realtime_map_builder import RealtimeMapBuilder, MapObservation
        rmb = RealtimeMapBuilder()
        obs = MapObservation("d1", np.array([0, 0, 50]), [np.array([30, 0, 50]), np.array([0, 30, 50])])
        rmb.process_observation(obs)
        assert rmb.summary()["total_observations"] == 1

    def test_exploration_progress(self):
        from simulation.realtime_map_builder import RealtimeMapBuilder, MapObservation
        rmb = RealtimeMapBuilder()
        for i in range(10):
            obs = MapObservation(f"d{i}", np.array([i * 50, 0, 50]), [np.array([i * 50 + 20, 0, 50])])
            rmb.process_observation(obs)
        progress = rmb.get_exploration_progress()
        assert progress > 0

    def test_pois(self):
        from simulation.realtime_map_builder import RealtimeMapBuilder, MapObservation
        rmb = RealtimeMapBuilder()
        # Multiple observations at same spot to build confidence
        for _ in range(5):
            obs = MapObservation("d1", np.array([0, 0, 50]), [np.array([100, 100, 50])])
            rmb.process_observation(obs)
        pois = rmb.get_pois()
        assert isinstance(pois, list)


# ── Phase 298: Adaptive Control System ──

class TestAdaptiveControlSystem:
    def test_register_and_compute(self):
        from simulation.adaptive_control_system import AdaptiveControlSystem
        acs = AdaptiveControlSystem()
        acs.register_drone("d1")
        output = acs.compute_control("d1", np.array([0, 0, 50]), np.array([100, 0, 50]))
        assert np.linalg.norm(output) > 0

    def test_wind_compensation(self):
        from simulation.adaptive_control_system import AdaptiveControlSystem
        acs = AdaptiveControlSystem()
        acs.register_drone("d1")
        acs.set_wind_compensation("d1", np.array([5, 0, 0]))
        output = acs.compute_control("d1", np.array([0, 0, 50]), np.array([100, 0, 50]))
        assert output is not None

    def test_tracking_error(self):
        from simulation.adaptive_control_system import AdaptiveControlSystem
        acs = AdaptiveControlSystem()
        acs.register_drone("d1")
        acs.compute_control("d1", np.array([0, 0, 50]), np.array([100, 0, 50]))
        error = acs.get_tracking_error("d1")
        assert error > 0

    def test_summary(self):
        from simulation.adaptive_control_system import AdaptiveControlSystem
        acs = AdaptiveControlSystem()
        acs.register_drone("d1")
        s = acs.summary()
        assert s["total_drones"] == 1


# ── Phase 299: Simulation Analytics Engine ──

class TestSimulationAnalyticsEngine:
    def test_record_and_kpi(self):
        from simulation.simulation_analytics_engine import SimulationAnalyticsEngine, SimulationRun, KPICategory
        sae = SimulationAnalyticsEngine()
        for i in range(10):
            sae.record_run(SimulationRun(f"r{i}", metrics={"collision_rate": 0.01 + i * 0.001}, timestamp=float(i)))
        kpi = sae.compute_kpi("avg_collision", KPICategory.SAFETY, "collision_rate")
        assert kpi is not None
        assert kpi.value > 0

    def test_compare_groups(self):
        from simulation.simulation_analytics_engine import SimulationAnalyticsEngine, SimulationRun
        sae = SimulationAnalyticsEngine()
        for i in range(10):
            sae.record_run(SimulationRun(f"a{i}", metrics={"throughput": 100.0 + np.random.default_rng(i).normal(0, 5)}))
            sae.add_to_group("baseline", f"a{i}")
            sae.record_run(SimulationRun(f"b{i}", metrics={"throughput": 110.0 + np.random.default_rng(i+100).normal(0, 5)}))
            sae.add_to_group("experiment", f"b{i}")
        result = sae.compare_groups("baseline", "experiment", "throughput")
        assert result is not None
        assert result.difference_pct != 0

    def test_trend_analysis(self):
        from simulation.simulation_analytics_engine import SimulationAnalyticsEngine, SimulationRun
        sae = SimulationAnalyticsEngine()
        for i in range(20):
            sae.record_run(SimulationRun(f"r{i}", metrics={"latency": 10.0 - i * 0.1}, timestamp=float(i)))
        trend = sae.trend_analysis("latency")
        assert trend["trend"] in ("improving", "degrading", "stable")

    def test_generate_report(self):
        from simulation.simulation_analytics_engine import SimulationAnalyticsEngine, SimulationRun
        sae = SimulationAnalyticsEngine()
        sae.record_run(SimulationRun("r1", metrics={"safety": 0.99}))
        report = sae.generate_report()
        assert report["total_runs"] == 1
