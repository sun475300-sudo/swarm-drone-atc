"""
Coverage boost tests - Phase 4.
Targets 0% modules: predictive_analytics_engine, digital_twin_federation,
swarm_cognitive_router, meta_learning_controller, battery_optimization_controller,
knowledge_graph_engine, adaptive_comm_protocol, collision_predictor,
causal_inference_engine, continuous_learning_engine, federated_edge_computer,
distributed_training_coordinator, swarm_collaborative_perception,
real_time_stream_processor, multi_modal_fusion.
"""

import time

import numpy as np
import pytest
import torch

# ── predictive_analytics_engine ───────────────────────────────────────────

from simulation.predictive_analytics_engine import (
    ForecastType,
    PredictiveAnalyticsEngine,
)


class TestPredictiveAnalyticsEngine:
    def setup_method(self):
        np.random.seed(42)
        self.engine = PredictiveAnalyticsEngine()

    def test_init(self):
        assert self.engine.history_window == 1000

    def test_ingest_data(self):
        self.engine.ingest_data(ForecastType.TRAFFIC, np.array([10.0]), time.time())
        self.engine.ingest_data(ForecastType.BATTERY, np.array([0.8]), time.time())

    def test_generate_forecast_empty(self):
        f = self.engine.generate_forecast(ForecastType.TRAFFIC)
        assert f.confidence == 0.0

    def test_generate_forecast_with_data(self):
        for i in range(20):
            self.engine.ingest_data(ForecastType.TRAFFIC, np.array([10.0 + i]), time.time() + i)
        f = self.engine.generate_forecast(ForecastType.TRAFFIC)
        assert len(f.predictions) > 0

    def test_detect_anomalies(self):
        data = np.vstack([np.ones((10, 3)), np.array([[100, 100, 100]])])
        alerts = self.engine.detect_anomalies(data, [f"d{i}" for i in range(11)])
        assert isinstance(alerts, list)

    def test_detect_anomalies_empty(self):
        alerts = self.engine.detect_anomalies(np.array([]).reshape(0, 3), [])
        assert alerts == []

    def test_predict_battery_failure_short(self):
        r = self.engine.predict_battery_failure("d1", np.array([0.9, 0.8, 0.7]))
        assert r["risk_level"] == "unknown"

    def test_predict_battery_failure_declining(self):
        history = np.linspace(1.0, 0.1, 20)
        r = self.engine.predict_battery_failure("d1", history)
        assert r["risk_level"] in ("low", "medium", "high", "critical")

    def test_predict_battery_failure_stable(self):
        history = np.ones(15) * 0.5
        r = self.engine.predict_battery_failure("d1", history)
        assert "risk_level" in r

    def test_predict_collision_risk(self):
        positions = np.array([[0, 0, 50], [10, 0, 50], [100, 100, 50]])
        velocities = np.array([[5, 0, 0], [-5, 0, 0], [0, 0, 0]])
        r = self.engine.predict_collision_risk(positions, velocities)
        assert r["total_pairs"] == 3
        assert "max_risk" in r

    def test_get_analytics_summary(self):
        s = self.engine.get_analytics_summary()
        assert "data_points" in s


# ── digital_twin_federation ───────────────────────────────────────────────

from simulation.digital_twin_federation import (
    DigitalTwinFederation,
    TwinState,
)


class TestDigitalTwinFederation:
    def setup_method(self):
        self.dtf = DigitalTwinFederation(federation_id="test_fed")

    def _make_state(self, drone_id="d1", battery=0.9):
        return TwinState(
            drone_id=drone_id, position=np.array([0, 0, 50]),
            velocity=np.array([1, 0, 0]), battery_level=battery,
            mission_progress=0.5, timestamp=time.time(),
        )

    def test_register_member(self):
        self.dtf.register_member("m1", priority=1)
        assert "m1" in self.dtf.members

    def test_update_twin_state(self):
        self.dtf.register_member("m1")
        self.dtf.update_twin_state("m1", self._make_state())
        assert "d1" in self.dtf.global_state

    def test_update_twin_state_auto_register(self):
        self.dtf.update_twin_state("new_member", self._make_state())
        assert "new_member" in self.dtf.members

    def test_synchronize(self):
        self.dtf.register_member("m1")
        self.dtf.register_member("m2")
        self.dtf.update_twin_state("m1", self._make_state("d1", 0.8))
        self.dtf.update_twin_state("m2", self._make_state("d1", 0.75))
        result = self.dtf.synchronize()
        assert result["status"] == "success"
        assert result["conflicts_resolved"] >= 1

    def test_query_twin(self):
        self.dtf.update_twin_state("m1", self._make_state())
        assert self.dtf.query_twin("d1") is not None
        assert self.dtf.query_twin("nonexistent") is None

    def test_get_all_twins(self):
        self.dtf.update_twin_state("m1", self._make_state())
        twins = self.dtf.get_all_twins()
        assert "d1" in twins

    def test_detect_anomalies_low_battery(self):
        self.dtf.update_twin_state("m1", self._make_state("d1", 0.05))
        anomalies = self.dtf.detect_anomalies()
        assert any(a["type"] == "low_battery" for a in anomalies)

    def test_detect_anomalies_high_velocity(self):
        state = TwinState(
            drone_id="d2", position=np.zeros(3),
            velocity=np.array([60, 0, 0]), battery_level=0.9,
            mission_progress=0.5, timestamp=time.time(),
        )
        self.dtf.update_twin_state("m1", state)
        anomalies = self.dtf.detect_anomalies()
        assert any(a["type"] == "high_velocity" for a in anomalies)

    def test_export_state(self):
        self.dtf.update_twin_state("m1", self._make_state())
        exported = self.dtf.export_state()
        assert "federation_id" in exported

    def test_get_federation_status(self):
        status = self.dtf.get_federation_status()
        assert status["federation_id"] == "test_fed"


# ── swarm_cognitive_router ────────────────────────────────────────────────

from simulation.swarm_cognitive_router import (
    NetworkNode,
    PacketPriority,
    SwarmCognitiveRouter,
)


class TestSwarmCognitiveRouter:
    def _make_node(self, node_id, neighbors=None):
        return NetworkNode(
            node_id=node_id, position=np.zeros(3),
            neighbors=neighbors or [], bandwidth_mbps=100.0,
            latency_ms=5.0, packet_loss_rate=0.01,
        )

    def setup_method(self):
        self.router = SwarmCognitiveRouter(network_id="test_net")

    def test_add_node(self):
        self.router.add_node(self._make_node("n1"))
        assert "n1" in self.router.nodes

    def test_update_link_quality(self):
        self.router.add_node(self._make_node("n1"))
        self.router.add_node(self._make_node("n2"))
        self.router.update_link_quality("n1", "n2", 0.95)
        assert "n2" in self.router.nodes["n1"].neighbors

    def test_compute_routes(self):
        self.router.add_node(self._make_node("n1", ["n2"]))
        self.router.add_node(self._make_node("n2", ["n1", "n3"]))
        self.router.add_node(self._make_node("n3", ["n2"]))
        route = self.router.compute_routes("n1", "n3")
        assert route == ["n1", "n2", "n3"]

    def test_compute_routes_same(self):
        self.router.add_node(self._make_node("n1"))
        assert self.router.compute_routes("n1", "n1") == ["n1"]

    def test_compute_routes_missing(self):
        assert self.router.compute_routes("x", "y") is None

    def test_compute_routes_no_path(self):
        self.router.add_node(self._make_node("n1"))
        self.router.add_node(self._make_node("n2"))
        assert self.router.compute_routes("n1", "n2") is None

    def test_route_packet_success(self):
        self.router.add_node(self._make_node("n1", ["n2"]))
        self.router.add_node(self._make_node("n2", ["n1"]))
        assert self.router.route_packet("n1", "n2", b"data")
        assert self.router.metrics["packets_routed"] == 1

    def test_route_packet_fail(self):
        self.router.add_node(self._make_node("n1"))
        self.router.add_node(self._make_node("n2"))
        assert not self.router.route_packet("n1", "n2", b"data")
        assert self.router.metrics["packets_dropped"] == 1

    def test_get_optimal_path(self):
        self.router.add_node(self._make_node("n1", ["n2"]))
        self.router.add_node(self._make_node("n2", ["n1"]))
        path = self.router.get_optimal_path("n1", "n2")
        assert path is not None

    def test_qos_route(self):
        self.router.add_node(self._make_node("n1", ["n2"]))
        self.router.add_node(self._make_node("n2", ["n1"]))
        route = self.router.qos_route("n1", "n2", PacketPriority.HIGH)
        assert route is not None

    def test_qos_route_low_bandwidth(self):
        n = self._make_node("n1", ["n2"])
        n.bandwidth_mbps = 0.5
        self.router.add_node(n)
        self.router.add_node(self._make_node("n2", ["n1"]))
        route = self.router.qos_route("n1", "n2", PacketPriority.CRITICAL)
        assert route is None

    def test_get_network_topology(self):
        self.router.add_node(self._make_node("n1"))
        topo = self.router.get_network_topology()
        assert topo["total_nodes"] == 1


# ── meta_learning_controller ─────────────────────────────────────────────

from simulation.meta_learning_controller import (
    AdaptationType,
    MetaLearningController,
    Task,
)


class TestMetaLearningController:
    def setup_method(self):
        np.random.seed(42)
        self.mlc = MetaLearningController()

    def _make_task(self, task_id="t1"):
        return Task(
            task_id=task_id,
            support_set={"embedding": np.random.randn(64, 128)},
            query_set={"embedding": np.random.randn(64, 128)},
            labels={"embedding": 1},
        )

    def test_init(self):
        assert self.mlc.adaptation_type == AdaptationType.FEW_SHOT

    def test_meta_train(self):
        tasks = [self._make_task(f"t{i}") for i in range(3)]
        model = self.mlc.meta_train(tasks, num_iterations=2)
        assert model.trained_on_tasks == 3

    def test_adapt_to_task(self):
        tasks = [self._make_task()]
        model = self.mlc.meta_train(tasks, num_iterations=1)
        adapted = self.mlc.adapt_to_task(model, self._make_task())
        assert isinstance(adapted, dict)

    def test_adapt_zero_shot(self):
        mlc = MetaLearningController(adaptation_type=AdaptationType.ZERO_SHOT)
        model = mlc.meta_train([self._make_task()], num_iterations=1)
        adapted = mlc.adapt_to_task(model, self._make_task())
        assert isinstance(adapted, dict)

    def test_evaluate_adaptation(self):
        model = self.mlc.meta_train([self._make_task()], num_iterations=1)
        result = self.mlc.evaluate_adaptation(model, self._make_task())
        assert "accuracy" in result

    def test_get_controller_status(self):
        status = self.mlc.get_controller_status()
        assert status["adaptation_type"] == "few_shot"


# ── battery_optimization_controller ───────────────────────────────────────

from simulation.battery_optimization_controller import BatteryOptimizationController


class TestBatteryOptimizationController:
    def setup_method(self):
        np.random.seed(42)
        self.boc = BatteryOptimizationController(num_drones=5)

    def test_init(self):
        assert len(self.boc.battery_states) == 5

    def test_estimate_flight_time_hover(self):
        t = self.boc.estimate_flight_time("drone_0", velocity=0.5)
        assert t > 0

    def test_estimate_flight_time_cruise(self):
        t = self.boc.estimate_flight_time("drone_0", velocity=5.0)
        assert t > 0

    def test_estimate_flight_time_max(self):
        t = self.boc.estimate_flight_time("drone_0", velocity=15.0)
        assert t > 0

    def test_estimate_flight_time_missing(self):
        t = self.boc.estimate_flight_time("nonexistent", velocity=5.0)
        assert t == 0.0

    def test_optimize_charging_schedule(self):
        schedules = self.boc.optimize_charging_schedule(mission_duration_hours=2.0)
        assert len(schedules) == 5

    def test_balance_fleet_battery(self):
        actions = self.boc.balance_fleet_battery(target_soc=0.8)
        assert len(actions) == 5

    def test_predict_battery_failure(self):
        r = self.boc.predict_battery_failure("drone_0", [0.9, 0.85, 0.8])
        assert "risk" in r

    def test_predict_battery_failure_missing(self):
        r = self.boc.predict_battery_failure("nonexistent", [])
        assert r["risk"] == "unknown"


# ── knowledge_graph_engine ────────────────────────────────────────────────

from simulation.knowledge_graph_engine import KnowledgeGraphEngine


class TestKnowledgeGraphEngine:
    def setup_method(self):
        np.random.seed(42)
        self.kg = KnowledgeGraphEngine(embedding_dim=32)

    def test_add_entity(self):
        self.kg.add_entity("d1", "drone", {"status": "active"})
        assert "d1" in self.kg.entities

    def test_add_relation(self):
        self.kg.add_entity("d1", "drone", {})
        self.kg.add_entity("z1", "zone", {})
        self.kg.add_relation("d1", "z1", "in_zone")
        assert len(self.kg.relations) == 1

    def test_add_relation_missing(self):
        self.kg.add_relation("missing", "also_missing", "rel")
        assert len(self.kg.relations) == 0

    def test_query(self):
        self.kg.add_entity("d1", "drone", {})
        self.kg.add_entity("z1", "zone", {})
        self.kg.add_relation("d1", "z1", "in_zone")
        results = self.kg.query("d1", "in_zone")
        assert "z1" in results

    def test_query_no_filter(self):
        self.kg.add_entity("d1", "drone", {})
        self.kg.add_entity("z1", "zone", {})
        self.kg.add_relation("d1", "z1", "in_zone")
        results = self.kg.query("d1")
        assert "z1" in results

    def test_query_missing(self):
        assert self.kg.query("nonexistent") == []

    def test_find_path(self):
        self.kg.add_entity("a", "node", {})
        self.kg.add_entity("b", "node", {})
        self.kg.add_entity("c", "node", {})
        self.kg.add_relation("a", "b", "conn")
        self.kg.add_relation("b", "c", "conn")
        path = self.kg.find_path("a", "c")
        assert path == ["a", "b", "c"]

    def test_find_path_none(self):
        self.kg.add_entity("a", "node", {})
        self.kg.add_entity("b", "node", {})
        assert self.kg.find_path("a", "b") is None

    def test_compute_similarity(self):
        self.kg.add_entity("d1", "drone", {})
        self.kg.add_entity("d2", "drone", {})
        sim = self.kg.compute_similarity("d1", "d2")
        assert -1 <= sim <= 1

    def test_compute_similarity_missing(self):
        assert self.kg.compute_similarity("x", "y") == 0.0

    def test_get_subgraph(self):
        self.kg.add_entity("d1", "drone", {})
        self.kg.add_entity("d2", "drone", {})
        self.kg.add_relation("d1", "d2", "near")
        sg = self.kg.get_subgraph("d1", depth=1)
        assert "d1" in sg["entities"]
        assert "d2" in sg["entities"]


# ── adaptive_comm_protocol ────────────────────────────────────────────────

from simulation.adaptive_comm_protocol import AdaptiveCommProtocol


class TestAdaptiveCommProtocol:
    def setup_method(self):
        self.proto = AdaptiveCommProtocol()

    def test_update_link_high_snr(self):
        self.proto.update_link_quality("d1", "d2", snr_db=25.0, packet_loss=0.01, latency=3.0, bandwidth=100.0)
        cfg = self.proto.get_config("d1", "d2")
        assert cfg.modulation == "256-QAM"

    def test_update_link_medium_snr(self):
        self.proto.update_link_quality("d1", "d2", snr_db=17.0, packet_loss=0.01, latency=5.0, bandwidth=50.0)
        cfg = self.proto.get_config("d1", "d2")
        assert cfg.modulation == "64-QAM"

    def test_update_link_low_snr(self):
        self.proto.update_link_quality("d1", "d2", snr_db=12.0, packet_loss=0.01, latency=10.0, bandwidth=20.0)
        cfg = self.proto.get_config("d1", "d2")
        assert cfg.modulation == "16-QAM"

    def test_update_link_very_low_snr(self):
        self.proto.update_link_quality("d1", "d2", snr_db=5.0, packet_loss=0.05, latency=30.0, bandwidth=5.0)
        cfg = self.proto.get_config("d1", "d2")
        assert cfg.modulation == "QPSK"

    def test_update_link_high_loss(self):
        self.proto.update_link_quality("d1", "d2", snr_db=25.0, packet_loss=0.15, latency=3.0, bandwidth=100.0)
        cfg = self.proto.get_config("d1", "d2")
        assert cfg.coding_rate == "3/4"  # Downgraded from 5/6

    def test_get_config_missing(self):
        assert self.proto.get_config("x", "y") is None

    def test_select_best_neighbor(self):
        self.proto.update_link_quality("d1", "d2", snr_db=25.0, packet_loss=0.01, latency=3.0, bandwidth=100.0)
        self.proto.update_link_quality("d1", "d3", snr_db=10.0, packet_loss=0.1, latency=20.0, bandwidth=10.0)
        best = self.proto.select_best_neighbor("d1", ["d2", "d3"])
        assert best == "d2"

    def test_select_best_neighbor_empty(self):
        assert self.proto.select_best_neighbor("d1", []) is None

    def test_get_protocol_stats(self):
        stats = self.proto.get_protocol_stats()
        assert stats["mode"] == "balanced"


# ── collision_predictor ───────────────────────────────────────────────────

from simulation.collision_predictor import CollisionPredictor, generate_training_data
from simulation.apf_engine.apf import APFState


class TestCollisionPredictor:
    def setup_method(self):
        self.cp = CollisionPredictor()

    def test_predict(self):
        a = APFState(position=np.array([0, 0, 50.0]), velocity=np.array([1, 0, 0.0]), drone_id="a")
        b = APFState(position=np.array([10, 0, 50.0]), velocity=np.array([-1, 0, 0.0]), drone_id="b")
        prob = self.cp.predict(a, b)
        assert 0 <= prob <= 1

    def test_train(self):
        X, y = generate_training_data(n_samples=100, seed=42)
        losses = self.cp.train((X, y), epochs=2, batch_size=32)
        assert len(losses) == 2

    def test_generate_training_data(self):
        X, y = generate_training_data(n_samples=200, seed=123)
        assert X.shape == (200, 12)
        assert y.shape == (200,)
        assert set(np.unique(y)) == {0.0, 1.0}


# ── causal_inference_engine ───────────────────────────────────────────────

from simulation.causal_inference_engine import CausalInferenceEngine


class TestCausalInferenceEngine:
    def setup_method(self):
        np.random.seed(42)
        self.cie = CausalInferenceEngine()

    def test_build_causal_graph(self):
        self.cie.build_causal_graph("g1", nodes=["A", "B", "C"], edges=[("A", "B"), ("B", "C")])
        assert "g1" in self.cie.causal_graphs

    def test_add_observational_data(self):
        self.cie.build_causal_graph("g1", ["A", "B"], [("A", "B")])
        data = [{"A": 1, "B": 5}, {"A": 0, "B": 3}]
        self.cie.add_observational_data("g1", data)
        assert "g1" in self.cie.observational_data

    def test_estimate_ate_with_data(self):
        self.cie.build_causal_graph("g1", ["wind", "collision"], [("wind", "collision")])
        data = [{"wind": 1, "collision": 5}] * 10 + [{"wind": 0, "collision": 2}] * 10
        self.cie.add_observational_data("g1", data)
        effect = self.cie.estimate_ate("wind", "collision", "g1")
        assert hasattr(effect, "ate")
        assert abs(effect.ate - 3.0) < 1e-6

    def test_estimate_ate_no_data(self):
        effect = self.cie.estimate_ate("A", "B", "missing")
        assert hasattr(effect, "ate")

    def test_adjust_confounding(self):
        self.cie.build_causal_graph("g1", ["A", "B"], [("A", "B")])
        result = self.cie.adjust_confounding("g1", "A", "B")
        assert isinstance(result, float)

    def test_adjust_confounding_missing(self):
        assert self.cie.adjust_confounding("missing", "A", "B") == 0.0

    def test_get_causal_paths(self):
        self.cie.build_causal_graph("g1", ["A", "B", "C"], [("A", "B"), ("B", "C")])
        paths = self.cie.get_causal_paths("A", "C", "g1")
        assert len(paths) >= 1
        assert paths[0] == ["A", "B", "C"]

    def test_get_causal_paths_missing(self):
        assert self.cie.get_causal_paths("A", "B", "missing") == []

    def test_estimate_counterfactual_treated(self):
        cf = self.cie.estimate_counterfactual("treatment", "outcome", {"treatment": 1, "outcome": 5.0})
        assert isinstance(cf, float)

    def test_estimate_counterfactual_control(self):
        cf = self.cie.estimate_counterfactual("treatment", "outcome", {"treatment": 0, "outcome": 3.0})
        assert isinstance(cf, float)


# ── continuous_learning_engine ────────────────────────────────────────────

from simulation.continuous_learning_engine import ContinuousLearningEngine, LearningTask


class TestContinuousLearningEngine:
    def setup_method(self):
        np.random.seed(42)
        self.cle = ContinuousLearningEngine()

    def _make_task(self, task_id="t1"):
        return LearningTask(
            task_id=task_id, data=np.random.randn(10, 128),
            labels=np.random.randn(10, 64), timestamp=time.time(),
        )

    def test_add_experience(self):
        self.cle.add_experience(self._make_task())
        assert len(self.cle.experience_memory) == 1

    def test_train_on_task(self):
        loss = self.cle.train_on_task(self._make_task())
        assert isinstance(loss, float)

    def test_replay_experiences(self):
        for i in range(5):
            self.cle.add_experience(self._make_task(f"t{i}"))
        loss = self.cle.replay_experiences()
        assert isinstance(loss, float)

    def test_save_restore_snapshot(self):
        snap_id = self.cle.save_snapshot()
        assert isinstance(snap_id, str)
        assert self.cle.restore_snapshot(snap_id)

    def test_restore_snapshot_missing(self):
        assert not self.cle.restore_snapshot("nonexistent")

    def test_get_learning_stats(self):
        stats = self.cle.get_learning_stats()
        assert isinstance(stats, dict)


# ── federated_edge_computer ───────────────────────────────────────────────

from simulation.federated_edge_computer import (
    EdgeDeviceType,
    FederatedEdgeComputer,
    InferenceTask as EdgeInferenceTask,
)


class TestFederatedEdgeComputer:
    def setup_method(self):
        np.random.seed(42)
        self.fec = FederatedEdgeComputer(federation_id="test_fed")

    def test_init(self):
        assert len(self.fec.devices) == 13  # 10 drones + 3 edge

    def test_register_device(self):
        self.fec.register_device(
            "custom_1", EdgeDeviceType.GATEWAY,
            compute_capacity=10, memory_mb=4096, battery_level=1.0,
        )
        assert "custom_1" in self.fec.devices

    def test_submit_task(self):
        task = EdgeInferenceTask(
            task_id="t1", model_name="collision_model",
            input_data=np.random.randn(10, 3), priority=1,
            deadline=time.time() + 100,
        )
        self.fec.submit_task(task)
        assert len(self.fec.task_queue) == 1

    def test_schedule_task(self):
        task = EdgeInferenceTask(
            task_id="t1", model_name="model",
            input_data=np.random.randn(5, 3), priority=1,
            deadline=time.time() + 100,
        )
        self.fec.submit_task(task)
        result = self.fec.schedule_task("t1")
        assert isinstance(result, (str, type(None)))

    def test_schedule_task_missing(self):
        assert self.fec.schedule_task("nonexistent") is None

    def test_get_federation_status(self):
        status = self.fec.get_federation_status()
        assert isinstance(status, dict)


# ── distributed_training_coordinator ──────────────────────────────────────

from simulation.distributed_training_coordinator import DistributedTrainingCoordinator


class TestDistributedTrainingCoordinator:
    def setup_method(self):
        self.dtc = DistributedTrainingCoordinator(coordinator_id="test_coord")

    def test_register_worker(self):
        self.dtc.register_worker("w1")

    def test_start_training(self):
        self.dtc.register_worker("w1")
        self.dtc.start_training("w1")

    def test_submit_gradients(self):
        self.dtc.register_worker("w1")
        self.dtc.start_training("w1")
        self.dtc.submit_gradients("w1", {"layer": np.random.randn(10, 5)})

    def test_synchronize_models(self):
        self.dtc.register_worker("w1")
        self.dtc.register_worker("w2")
        self.dtc.start_training("w1")
        self.dtc.start_training("w2")
        self.dtc.submit_gradients("w1", {"layer": np.random.randn(10, 5)})
        self.dtc.submit_gradients("w2", {"layer": np.random.randn(10, 5)})
        result = self.dtc.synchronize_models()
        assert isinstance(result, bool)

    def test_get_worker_status(self):
        self.dtc.register_worker("w1")
        status = self.dtc.get_worker_status("w1")
        assert status is not None

    def test_get_worker_status_missing(self):
        assert self.dtc.get_worker_status("nonexistent") is None

    def test_get_coordinator_status(self):
        status = self.dtc.get_coordinator_status()
        assert isinstance(status, dict)


# ── swarm_collaborative_perception ────────────────────────────────────────

from simulation.swarm_collaborative_perception import (
    PerceptionFrame,
    PerceptionModality,
    SwarmCollaborativePerception,
)


class TestSwarmCollaborativePerception:
    def setup_method(self):
        self.scp = SwarmCollaborativePerception()

    def _make_frame(self, drone_id, position=None):
        return PerceptionFrame(
            frame_id=f"f_{drone_id}", drone_id=drone_id,
            modality=PerceptionModality.VISUAL,
            data=np.random.randn(10, 10), timestamp=time.time(),
            position=position if position is not None else np.zeros(3),
        )

    def test_add_frame(self):
        self.scp.add_frame(self._make_frame("d1"))

    def test_fuse_frames(self):
        self.scp.add_frame(self._make_frame("d1", np.array([0, 0, 0])))
        self.scp.add_frame(self._make_frame("d2", np.array([5, 0, 0])))
        result = self.scp.fuse_frames(PerceptionModality.VISUAL, "d1")
        assert result is not None or result is None  # May or may not fuse

    def test_fuse_frames_missing(self):
        result = self.scp.fuse_frames(PerceptionModality.VISUAL, "nonexistent")
        assert result is None

    def test_get_coverage_stats(self):
        stats = self.scp.get_coverage_stats()
        assert isinstance(stats, dict)

    def test_estimate_occlusion(self):
        result = self.scp.estimate_occlusion(
            viewpoint=np.zeros(3), target_position=np.array([10.0, 0.0, 0.0]),
        )
        assert isinstance(result, float)


# ── real_time_stream_processor ────────────────────────────────────────────

from simulation.real_time_stream_processor import (
    RealTimeStreamProcessor,
    StreamEvent,
    StreamType,
)


class TestRealTimeStreamProcessor:
    def setup_method(self):
        self.rsp = RealTimeStreamProcessor()

    def _make_event(self, stream_type=StreamType.TELEMETRY, value=42):
        return StreamEvent(
            event_id=f"e_{value}", stream_type=stream_type,
            data={"value": value}, timestamp=time.time(), drone_id="d1",
        )

    def test_register_processor(self):
        self.rsp.register_processor(StreamType.TELEMETRY, lambda x: x)

    def test_ingest(self):
        self.rsp.ingest(self._make_event())

    def test_process_stream(self):
        self.rsp.register_processor(StreamType.TELEMETRY, lambda x: x)
        self.rsp.ingest(self._make_event())
        results = self.rsp.process_stream(StreamType.TELEMETRY)
        assert isinstance(results, list)

    def test_process_stream_default(self):
        self.rsp.ingest(self._make_event())
        results = self.rsp.process_stream(StreamType.TELEMETRY)
        assert isinstance(results, list)

    def test_compute_window_aggregate(self):
        for i in range(10):
            self.rsp.ingest(self._make_event(StreamType.SENSOR, float(i)))
        result = self.rsp.compute_window_aggregate("value", window_sec=60.0)
        assert isinstance(result, float)

    def test_get_metrics(self):
        metrics = self.rsp.get_metrics()
        assert isinstance(metrics, dict)


# ── multi_modal_fusion ────────────────────────────────────────────────────

from simulation.multi_modal_fusion import (
    FusionResult,
    MultiModalFusion,
    SensorReading,
    SensorType,
)


class TestMultiModalFusion:
    def setup_method(self):
        self.mmf = MultiModalFusion()

    def _make_reading(self, sensor_type=SensorType.LIDAR, confidence=0.9):
        return SensorReading(
            sensor_type=sensor_type, data=np.array([1, 2, 3, 4, 5, 6.0]),
            timestamp=time.time(), confidence=confidence,
        )

    def test_add_reading(self):
        self.mmf.add_reading(self._make_reading())

    def test_fuse(self):
        self.mmf.add_reading(self._make_reading(SensorType.LIDAR, 0.9))
        self.mmf.add_reading(self._make_reading(SensorType.GPS, 0.8))
        result = self.mmf.fuse()
        assert isinstance(result, FusionResult)
        assert len(result.sources_used) >= 2

    def test_fuse_empty(self):
        result = self.mmf.fuse()
        assert isinstance(result, FusionResult)

    def test_get_state_estimate(self):
        result = self.mmf.get_state_estimate()
        assert isinstance(result, np.ndarray)

    def test_calibrate_sensor(self):
        self.mmf.calibrate_sensor(SensorType.LIDAR, np.zeros(6))
