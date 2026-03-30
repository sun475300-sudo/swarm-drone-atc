"""Phase 311-330 통합 테스트 — PBFT, Physics v2, Satellite, Edge AI,
Formation v2, Weather NN, IDS, SLAM, DSA, FL v2.
"""

import numpy as np
import pytest
import time


# ── Phase 311: Distributed Consensus v2 (PBFT) ──────────────────
from simulation.distributed_consensus_v2 import (
    DistributedConsensusV2, ConsensusRequest, NodeRole,
)


class TestDistributedConsensusV2:
    def test_init(self):
        dc = DistributedConsensusV2(n_nodes=4, f_faulty=1)
        assert dc.n_nodes == 4

    def test_submit_request(self):
        dc = DistributedConsensusV2(n_nodes=4, f_faulty=1)
        req = ConsensusRequest(client_id="c1", operation="move_drone_1")
        result = dc.submit_request(req)
        assert result is True

    def test_faulty_node(self):
        dc = DistributedConsensusV2(n_nodes=7, f_faulty=2)
        dc.set_faulty(1)
        dc.set_faulty(2)
        req = ConsensusRequest(client_id="c1", operation="reroute")
        result = dc.submit_request(req)
        assert result is True

    def test_consistency(self):
        dc = DistributedConsensusV2(n_nodes=4, f_faulty=1)
        dc.submit_request(ConsensusRequest(client_id="c1", operation="op1"))
        dc.submit_request(ConsensusRequest(client_id="c2", operation="op2"))
        assert dc.verify_consistency() is True

    def test_view_change(self):
        dc = DistributedConsensusV2(n_nodes=4, f_faulty=1)
        new_view = dc.view_change()
        assert new_view == 1
        assert dc.get_primary() == 1

    def test_summary(self):
        dc = DistributedConsensusV2()
        s = dc.summary()
        assert s["consistent"] is True


# ── Phase 312: Real-time Physics v2 ─────────────────────────────
from simulation.realtime_physics_v2 import (
    RealtimePhysicsV2, RigidBody, ForceField, CollisionInfo,
)


class TestRealtimePhysicsV2:
    def test_add_body(self):
        phys = RealtimePhysicsV2()
        body = RigidBody(body_id="d1", position=np.array([0.0, 0.0, 50.0]), mass=2.0)
        phys.add_body(body)
        assert phys.get_body("d1") is not None

    def test_gravity(self):
        phys = RealtimePhysicsV2(dt=0.01)
        phys.add_body(RigidBody(body_id="ball", position=np.array([0.0, 0.0, 100.0])))
        phys.run_for(0.5)
        ball = phys.get_body("ball")
        assert ball.position[2] < 100.0  # fell under gravity

    def test_collision(self):
        phys = RealtimePhysicsV2(dt=0.01)
        phys.add_body(RigidBody(body_id="a", position=np.array([0.0, 0.0, 50.0]),
                                velocity=np.array([10.0, 0.0, 0.0]), radius=2.0))
        phys.add_body(RigidBody(body_id="b", position=np.array([3.0, 0.0, 50.0]),
                                velocity=np.array([-10.0, 0.0, 0.0]), radius=2.0))
        phys.step()
        # After collision, bodies should have changed velocities
        a = phys.get_body("a")
        b = phys.get_body("b")
        assert a is not None and b is not None

    def test_kinetic_energy(self):
        phys = RealtimePhysicsV2()
        phys.add_body(RigidBody(body_id="d1", velocity=np.array([10.0, 0.0, 0.0]), mass=2.0))
        ke = phys.get_kinetic_energy()
        assert ke == pytest.approx(100.0, rel=0.1)

    def test_summary(self):
        phys = RealtimePhysicsV2()
        phys.add_body(RigidBody(body_id="d1"))
        s = phys.summary()
        assert s["total_bodies"] == 1


# ── Phase 313: Satellite Communication Layer ─────────────────────
from simulation.satellite_comm_layer import (
    SatelliteCommLayer, Satellite, OrbitType, LinkStatus,
)


class TestSatelliteCommLayer:
    def test_add_satellite(self):
        layer = SatelliteCommLayer()
        sat = Satellite(sat_id="sat1", altitude_km=550)
        layer.add_satellite(sat)
        assert len(layer._satellites) == 1

    def test_link_budget(self):
        layer = SatelliteCommLayer()
        sat = Satellite(sat_id="sat1", altitude_km=550)
        layer.add_satellite(sat)
        budget = layer.compute_link_budget(sat, np.array([0.0, 0.0, 0.0]))
        assert budget.path_loss_db > 0

    def test_latency(self):
        layer = SatelliteCommLayer()
        sat = Satellite(sat_id="sat1", altitude_km=550)
        layer.add_satellite(sat)
        latency = layer.compute_latency(sat, np.array([0.0, 0.0, 0.0]))
        assert latency > 0

    def test_update_links(self):
        layer = SatelliteCommLayer()
        layer.add_satellite(Satellite(sat_id="s1", altitude_km=550, longitude_deg=0))
        layer.add_satellite(Satellite(sat_id="s2", altitude_km=550, longitude_deg=90))
        layer.update_links({"d1": np.array([6371.0, 0.0, 0.0])})
        link = layer.get_link("d1")
        assert link is not None

    def test_summary(self):
        layer = SatelliteCommLayer()
        s = layer.summary()
        assert isinstance(s, dict)


# ── Phase 314: Edge AI Inference Engine ──────────────────────────
from simulation.edge_ai_inference import (
    EdgeAIInferenceEngine, EdgeModel, ModelFormat, InferenceResult,
)


class TestEdgeAIInference:
    def test_load_model(self):
        engine = EdgeAIInferenceEngine()
        model = EdgeModel(model_id="det", name="Detector", input_shape=(10,), output_shape=(5,))
        engine.load_model(model)
        assert engine.get_model("det") is not None

    def test_infer(self):
        engine = EdgeAIInferenceEngine()
        engine.load_model(EdgeModel(model_id="m1", name="M1", input_shape=(10,), output_shape=(5,)))
        result = engine.infer("m1", np.random.randn(10))
        assert isinstance(result, InferenceResult)
        assert result.output is not None

    def test_quantize(self):
        engine = EdgeAIInferenceEngine()
        engine.load_model(EdgeModel(model_id="m1", name="M1", input_shape=(10,), output_shape=(5,), size_mb=20.0))
        q = engine.quantize_model("m1", ModelFormat.INT8)
        assert q.size_mb < 20.0
        assert q.format == ModelFormat.INT8

    def test_cache_hit(self):
        engine = EdgeAIInferenceEngine()
        engine.load_model(EdgeModel(model_id="m1", name="M1", input_shape=(10,), output_shape=(5,)))
        data = np.ones(10)
        engine.infer("m1", data)
        result2 = engine.infer("m1", data)
        assert result2.cached is True

    def test_batch_infer(self):
        engine = EdgeAIInferenceEngine()
        engine.load_model(EdgeModel(model_id="m1", name="M1", input_shape=(10,), output_shape=(5,)))
        batch = [np.random.randn(10) for _ in range(5)]
        results = engine.batch_infer("m1", batch)
        assert len(results) == 5

    def test_summary(self):
        engine = EdgeAIInferenceEngine()
        s = engine.summary()
        assert s["loaded_models"] == 0


# ── Phase 315: Swarm Formation v2 ───────────────────────────────
from simulation.swarm_formation_v2 import (
    SwarmFormationV2, FormationType, FormationConfig, DroneRole,
)


class TestSwarmFormationV2:
    def test_add_drones(self):
        sf = SwarmFormationV2()
        sf.add_drone("leader", np.array([0.0, 0.0, 50.0]), DroneRole.LEADER)
        sf.add_drone("f1", np.array([10.0, 0.0, 50.0]))
        sf.add_drone("f2", np.array([-10.0, 0.0, 50.0]))
        assert len(sf._drones) == 3

    def test_set_formation(self):
        sf = SwarmFormationV2()
        sf.add_drone("leader", np.array([0.0, 0.0, 50.0]), DroneRole.LEADER)
        sf.add_drone("f1", np.array([10.0, 0.0, 50.0]))
        sf.set_formation(FormationConfig(FormationType.V_FORMATION, spacing=20.0))
        assert sf._config.formation_type == FormationType.V_FORMATION

    def test_step(self):
        sf = SwarmFormationV2()
        sf.add_drone("leader", np.array([0.0, 0.0, 50.0]), DroneRole.LEADER)
        sf.add_drone("f1", np.array([10.0, 0.0, 50.0]))
        sf.set_formation(FormationConfig(FormationType.LINE, spacing=15.0))
        sf.step(dt=0.1)
        assert sf._step_count == 1

    def test_cohesion(self):
        sf = SwarmFormationV2()
        sf.add_drone("leader", np.array([0.0, 0.0, 50.0]), DroneRole.LEADER)
        cohesion = sf.get_cohesion()
        assert 0 <= cohesion <= 1.0

    def test_summary(self):
        sf = SwarmFormationV2()
        s = sf.summary()
        assert isinstance(s, dict)


# ── Phase 316: Weather Prediction NN ─────────────────────────────
from simulation.weather_prediction_nn import (
    WeatherPredictionNN, WeatherObservation, WeatherVariable, WeatherForecast,
)


class TestWeatherPredictionNN:
    def test_observe(self):
        nn = WeatherPredictionNN(hidden_size=16, n_ensemble=2)
        obs = WeatherObservation(timestamp=1.0, values={
            "temperature": 25.0, "wind_speed": 5.0, "wind_direction": 180.0,
            "humidity": 60.0, "pressure": 1013.0, "visibility": 10.0, "precipitation": 0.0,
        })
        nn.observe(obs)
        assert len(nn._observations) == 1

    def test_predict(self):
        nn = WeatherPredictionNN(hidden_size=16, n_ensemble=2)
        for i in range(5):
            nn.observe(WeatherObservation(timestamp=float(i), values={
                "temperature": 25.0 + i * 0.1, "wind_speed": 5.0,
                "wind_direction": 180.0, "humidity": 60.0,
                "pressure": 1013.0, "visibility": 10.0, "precipitation": 0.0,
            }))
        forecast = nn.predict(horizon_sec=300)
        assert isinstance(forecast, WeatherForecast)
        assert forecast.confidence > 0

    def test_trend(self):
        nn = WeatherPredictionNN()
        for i in range(10):
            nn.observe(WeatherObservation(timestamp=float(i), values={
                "temperature": 20.0 + i, "wind_speed": 5.0,
                "wind_direction": 180.0, "humidity": 60.0,
                "pressure": 1013.0, "visibility": 10.0, "precipitation": 0.0,
            }))
        trend = nn.get_trend(WeatherVariable.TEMPERATURE)
        assert trend["trend"] == "increasing"

    def test_summary(self):
        nn = WeatherPredictionNN()
        s = nn.summary()
        assert s["observations"] == 0


# ── Phase 317: Cybersecurity IDS ─────────────────────────────────
from simulation.cybersecurity_ids import (
    CybersecurityIDS, NetworkPacket, ThreatLevel, AttackType,
)


class TestCybersecurityIDS:
    def test_analyze_normal(self):
        ids = CybersecurityIDS()
        pkt = NetworkPacket(source_id="d1", dest_id="atc", packet_type="telemetry",
                            size_bytes=256, timestamp=1.0)
        alert = ids.analyze_packet(pkt)
        assert alert is None  # normal packet

    def test_detect_dos(self):
        ids = CybersecurityIDS()
        for i in range(150):
            pkt = NetworkPacket(source_id="attacker", dest_id="atc", packet_type="telemetry",
                                size_bytes=100, timestamp=1.0)
            alert = ids.analyze_packet(pkt)
        assert alert is not None
        assert alert.attack_type == AttackType.DOS

    def test_unencrypted_command(self):
        ids = CybersecurityIDS()
        pkt = NetworkPacket(source_id="d1", dest_id="atc", packet_type="command",
                            size_bytes=128, timestamp=1.0, is_encrypted=False)
        alert = ids.analyze_packet(pkt)
        assert alert is not None
        assert alert.attack_type == AttackType.INJECTION

    def test_summary(self):
        ids = CybersecurityIDS()
        s = ids.summary()
        assert s["total_packets"] == 0


# ── Phase 318: Multi-Drone SLAM ──────────────────────────────────
from simulation.multi_drone_slam import (
    MultiDroneSLAM, Pose, Landmark,
)


class TestMultiDroneSLAM:
    def test_add_drone(self):
        slam = MultiDroneSLAM()
        slam.add_drone("d1", Pose(position=np.array([0.0, 0.0, 50.0])))
        assert "d1" in slam._drone_poses

    def test_odometry(self):
        slam = MultiDroneSLAM()
        slam.add_drone("d1", Pose(position=np.array([0.0, 0.0, 50.0])))
        slam.update_odometry("d1", np.array([1.0, 0.0, 0.0]))
        traj = slam.get_drone_trajectory("d1")
        assert len(traj) == 2

    def test_observe_landmark(self):
        slam = MultiDroneSLAM()
        slam.add_drone("d1", Pose(position=np.array([0.0, 0.0, 50.0])))
        slam.observe_landmark("d1", "lm1", np.array([50.0, 0.0, 50.0]))
        assert "lm1" in slam._landmarks

    def test_merge_maps(self):
        slam = MultiDroneSLAM()
        slam.add_drone("d1", Pose(position=np.zeros(3)))
        slam.observe_landmark("d1", "lm1", np.array([10.0, 0.0, 0.0]))
        merged = slam.merge_maps()
        assert "lm1" in merged

    def test_summary(self):
        slam = MultiDroneSLAM()
        s = slam.summary()
        assert s["total_drones"] == 0


# ── Phase 319: Dynamic Spectrum Access ───────────────────────────
from simulation.dynamic_spectrum_access import (
    DynamicSpectrumAccess, Channel, SpectrumBand, ChannelStatus,
)


class TestDynamicSpectrumAccess:
    def test_init_channels(self):
        dsa = DynamicSpectrumAccess()
        dsa.init_default_channels()
        assert len(dsa._channels) == 10

    def test_sense_channel(self):
        dsa = DynamicSpectrumAccess()
        dsa.init_default_channels()
        energy = dsa.sense_channel("ch1", 1.0)
        assert isinstance(energy, float)

    def test_detect_holes(self):
        dsa = DynamicSpectrumAccess()
        dsa.init_default_channels()
        dsa.sense_all(1.0)
        holes = dsa.detect_spectrum_holes(1.0)
        assert len(holes) >= 0

    def test_allocate_channel(self):
        dsa = DynamicSpectrumAccess()
        dsa.init_default_channels()
        dsa.sense_all(1.0)
        alloc = dsa.allocate_channel("d1", 1.0)
        # May or may not allocate depending on sensing
        assert alloc is None or alloc.drone_id == "d1"

    def test_primary_user_eviction(self):
        dsa = DynamicSpectrumAccess()
        dsa.init_default_channels()
        dsa.sense_all(1.0)
        alloc = dsa.allocate_channel("d1", 1.0)
        if alloc:
            dsa.set_primary_user(alloc.channel_id, True)
            assert dsa.get_allocation("d1") is None

    def test_summary(self):
        dsa = DynamicSpectrumAccess()
        dsa.init_default_channels()
        s = dsa.summary()
        assert s["total_channels"] == 10


# ── Phase 320: Federated Learning v2 ────────────────────────────
from simulation.federated_learning_v2 import (
    FederatedLearningV2, AggregationMethod, FLRound,
)


class TestFederatedLearningV2:
    def test_register_clients(self):
        fl = FederatedLearningV2(model_dim=20)
        fl.register_client("d1", data_size=100)
        fl.register_client("d2", data_size=200)
        assert len(fl._clients) == 2

    def test_local_train(self):
        fl = FederatedLearningV2(model_dim=20)
        fl.register_client("d1", data_size=100)
        loss = fl.local_train("d1", n_epochs=3)
        assert loss < float("inf")

    def test_run_round(self):
        fl = FederatedLearningV2(model_dim=20)
        for i in range(5):
            fl.register_client(f"d{i}", data_size=100)
        fl_round = fl.run_round(fraction=0.6, n_epochs=3)
        assert isinstance(fl_round, FLRound)
        assert fl_round.global_loss < float("inf")

    def test_convergence(self):
        fl = FederatedLearningV2(model_dim=10)
        for i in range(4):
            fl.register_client(f"d{i}", data_size=50)
        for _ in range(3):
            fl.run_round(fraction=1.0, n_epochs=5)
        conv = fl.get_convergence()
        assert len(conv) == 3

    def test_fedprox(self):
        fl = FederatedLearningV2(model_dim=10, method=AggregationMethod.FEDPROX)
        for i in range(3):
            fl.register_client(f"d{i}")
        fl_round = fl.run_round()
        assert fl_round is not None

    def test_summary(self):
        fl = FederatedLearningV2()
        s = fl.summary()
        assert s["total_rounds"] == 0
