"""
Coverage boost tests - Phase 3.
Targets: autonomous_fleet_composer, blockchain_ledger, graph_neural_network,
risk_hedge_calculator, quantum_resilience, neural_architecture_search.
"""

import time

import numpy as np
import pytest

# ── autonomous_fleet_composer ─────────────────────────────────────────────

from simulation.autonomous_fleet_composer import (
    AutonomousFleetComposer,
    Drone,
    DroneCapability,
    DroneStatus,
    FleetAssignment,
    Mission,
)


class TestDroneCapability:
    def test_values(self):
        assert DroneCapability.SURVEILLANCE.value == "surveillance"
        assert DroneCapability.RESCUE.value == "rescue"


class TestDroneStatus:
    def test_values(self):
        assert DroneStatus.AVAILABLE.value == "available"
        assert DroneStatus.EMERGENCY.value == "emergency"


class TestAutonomousFleetComposer:
    def setup_method(self):
        np.random.seed(42)
        self.fc = AutonomousFleetComposer(fleet_id="test_fleet")

    def test_init_creates_drones(self):
        assert len(self.fc.drones) == 20

    def test_register_drone(self):
        self.fc.register_drone(
            "custom_1", [DroneCapability.DELIVERY],
            max_payload_kg=10, max_range_km=20,
            battery_capacity_wh=1000, position=np.zeros(3),
        )
        assert "custom_1" in self.fc.drones

    def test_submit_mission(self):
        m = Mission(
            mission_id="m1",
            required_capabilities=[DroneCapability.SURVEILLANCE],
            required_payload_kg=5, priority=1,
            deadline=time.time() + 3600, estimated_duration=600,
        )
        assert self.fc.submit_mission(m)

    def test_compose_fleet_missing(self):
        assert self.fc.compose_fleet("nonexistent") is None

    def test_compose_fleet_success(self):
        m = Mission(
            mission_id="m1",
            required_capabilities=[DroneCapability.SURVEILLANCE],
            required_payload_kg=5, priority=1,
            deadline=time.time() + 3600, estimated_duration=600,
        )
        self.fc.submit_mission(m)
        assignment = self.fc.compose_fleet("m1")
        assert assignment is not None
        assert isinstance(assignment, FleetAssignment)

    def test_compose_fleet_no_candidates(self):
        # Make all drones unavailable
        for d in self.fc.drones.values():
            d.status = DroneStatus.MAINTENANCE
        m = Mission(
            mission_id="m1",
            required_capabilities=[DroneCapability.SURVEILLANCE],
            required_payload_kg=5, priority=1,
            deadline=time.time() + 3600, estimated_duration=600,
        )
        self.fc.submit_mission(m)
        assert self.fc.compose_fleet("m1") is None

    def test_complete_mission(self):
        m = Mission(
            mission_id="m1",
            required_capabilities=[DroneCapability.SURVEILLANCE],
            required_payload_kg=5, priority=1,
            deadline=time.time() + 3600, estimated_duration=600,
        )
        self.fc.submit_mission(m)
        self.fc.compose_fleet("m1")
        self.fc.complete_mission("m1")
        assert "m1" not in self.fc.assignments

    def test_complete_mission_missing(self):
        self.fc.complete_mission("nonexistent")  # No error

    def test_rebalance_fleet(self):
        result = self.fc.rebalance_fleet()
        assert "actions" in result
        assert "available" in result

    def test_get_fleet_status(self):
        status = self.fc.get_fleet_status()
        assert status["fleet_id"] == "test_fleet"
        assert status["total_drones"] == 20

    def test_predict_fleet_availability(self):
        pred = self.fc.predict_fleet_availability()
        assert DroneStatus.AVAILABLE.value in pred

    def test_load_balance_disabled(self):
        fc = AutonomousFleetComposer(
            fleet_id="no_lb", load_balance_enabled=False,
        )
        m = Mission(
            mission_id="m1",
            required_capabilities=[DroneCapability.SURVEILLANCE],
            required_payload_kg=5, priority=1,
            deadline=time.time() + 3600, estimated_duration=600,
        )
        fc.submit_mission(m)
        assignment = fc.compose_fleet("m1")
        assert assignment is not None


# ── blockchain_ledger ─────────────────────────────────────────────────────

from simulation.blockchain_ledger import (
    Block,
    BlockchainLedger,
    Transaction,
    TransactionType,
)


class TestTransactionType:
    def test_values(self):
        assert TransactionType.MISSION_START.value == "mission_start"
        assert TransactionType.EMERGENCY.value == "emergency"


class TestBlockchainLedger:
    def setup_method(self):
        self.ledger = BlockchainLedger(difficulty=1)  # Low difficulty for speed

    def test_genesis_block(self):
        assert len(self.ledger.chain) == 1
        assert self.ledger.chain[0].index == 0

    def test_add_validator(self):
        self.ledger.add_validator("v1")
        assert "v1" in self.ledger.validators

    def test_register_drone(self):
        self.ledger.register_drone("d1", {"type": "surveillance"})
        assert "d1" in self.ledger.drone_registry

    def test_create_transaction(self):
        tx = self.ledger.create_transaction(
            "d1", TransactionType.MISSION_START, {"waypoints": [1, 2, 3]},
        )
        assert isinstance(tx, Transaction)
        assert tx.drone_id == "d1"

    def test_create_transaction_auto_register(self):
        tx = self.ledger.create_transaction(
            "new_drone", TransactionType.POSITION_UPDATE, {"pos": [0, 0, 0]},
        )
        assert "new_drone" in self.ledger.drone_registry

    def test_add_and_mine_block(self):
        tx = self.ledger.create_transaction(
            "d1", TransactionType.MISSION_START, {"data": "test"},
        )
        self.ledger.add_transaction(tx)
        block = self.ledger.mine_block()
        assert isinstance(block, Block)
        assert len(self.ledger.chain) == 2

    def test_mine_no_pending(self):
        with pytest.raises(ValueError, match="No pending"):
            self.ledger.mine_block()

    def test_verify_chain(self):
        tx = self.ledger.create_transaction(
            "d1", TransactionType.COLLISION_EVENT, {"severity": "high"},
        )
        self.ledger.add_transaction(tx)
        self.ledger.mine_block()
        assert self.ledger.verify_chain()

    def test_verify_chain_tampered(self):
        tx = self.ledger.create_transaction(
            "d1", TransactionType.BATTERY_SWAP, {},
        )
        self.ledger.add_transaction(tx)
        self.ledger.mine_block()
        self.ledger.chain[1].hash = "tampered"
        assert not self.ledger.verify_chain()

    def test_get_drone_history(self):
        tx = self.ledger.create_transaction(
            "d1", TransactionType.MISSION_START, {"data": 1},
        )
        self.ledger.add_transaction(tx)
        self.ledger.mine_block()
        history = self.ledger.get_drone_history("d1")
        assert len(history) >= 1

    def test_get_chain_stats(self):
        stats = self.ledger.get_chain_stats()
        assert stats["total_blocks"] == 1

    def test_export_chain(self):
        export = self.ledger.export_chain()
        assert isinstance(export, str)
        assert "index" in export

    def test_calculate_hash(self):
        h = self.ledger.calculate_hash(0, 0.0, [], "0")
        assert isinstance(h, str)
        assert len(h) == 64


# ── graph_neural_network ─────────────────────────────────────────────────

from simulation.graph_neural_network import GraphEdge, GraphNode, GraphNeuralNetwork


class TestGraphNode:
    def test_fields(self):
        n = GraphNode(
            node_id="n1", position=np.zeros(3), velocity=np.ones(3),
        )
        assert n.node_id == "n1"


class TestGraphNeuralNetwork:
    def setup_method(self):
        self.gnn = GraphNeuralNetwork(node_feature_dim=6, hidden_dim=16)

    def test_add_node(self):
        self.gnn.add_node("d1", np.array([1, 2, 3]), np.array([0, 0, 0]))
        assert "d1" in self.gnn.node_embeddings

    def test_add_node_padding(self):
        self.gnn.add_node("d1", np.array([1]), np.array([2]))
        assert self.gnn.node_embeddings["d1"].shape == (6,)

    def test_add_edge(self):
        self.gnn.add_node("d1", np.zeros(3), np.zeros(3))
        self.gnn.add_node("d2", np.ones(3), np.zeros(3))
        self.gnn.add_edge("d1", "d2")
        assert ("d1", "d2") in self.gnn.edge_features

    def test_add_edge_missing_node(self):
        self.gnn.add_edge("missing1", "missing2")
        assert len(self.gnn.edge_features) == 0

    def test_build_graph_from_drones(self):
        drones = [
            {"id": "d1", "position": [0, 0, 0], "velocity": [1, 0, 0]},
            {"id": "d2", "position": [10, 0, 0], "velocity": [0, 1, 0]},
            {"id": "d3", "position": [500, 500, 500], "velocity": [0, 0, 0]},
        ]
        self.gnn.build_graph_from_drones(drones, communication_range=50)
        assert "d1" in self.gnn.node_embeddings
        assert ("d1", "d2") in self.gnn.edge_features
        assert ("d1", "d3") not in self.gnn.edge_features

    def test_message_passing(self):
        drones = [
            {"id": "d1", "position": [0, 0, 0], "velocity": [1, 0, 0]},
            {"id": "d2", "position": [10, 0, 0], "velocity": [0, 1, 0]},
        ]
        self.gnn.build_graph_from_drones(drones, communication_range=50)
        states = self.gnn.message_passing()
        assert "d1" in states
        assert states["d1"].shape == (16,)

    def test_predict_collision_risk(self):
        drones = [
            {"id": "d1", "position": [0, 0, 0], "velocity": [5, 0, 0]},
            {"id": "d2", "position": [10, 0, 0], "velocity": [-5, 0, 0]},
        ]
        risks = self.gnn.predict_collision_risk(drones)
        assert ("d1", "d2") in risks
        assert 0 <= risks[("d1", "d2")] <= 1

    def test_predict_trajectory(self):
        self.gnn.add_node("d1", np.zeros(3), np.ones(3))
        traj = self.gnn.predict_trajectory("d1", future_steps=5)
        assert len(traj) == 5

    def test_get_swarm_embedding(self):
        drones = [
            {"id": "d1", "position": [0, 0, 0], "velocity": [0, 0, 0]},
            {"id": "d2", "position": [10, 0, 0], "velocity": [0, 0, 0]},
        ]
        self.gnn.build_graph_from_drones(drones)
        emb = self.gnn.get_swarm_embedding()
        assert emb.shape == (16,)

    def test_get_swarm_embedding_empty(self):
        emb = self.gnn.get_swarm_embedding()
        assert emb.shape == (16,)
        assert np.allclose(emb, 0)


# ── risk_hedge_calculator ─────────────────────────────────────────────────

from simulation.risk_hedge_calculator import (
    HedgeAction,
    HedgeStrategy,
    PortfolioMetrics,
    RiskCategory,
    RiskFactor,
    RiskHedgeCalculator,
)


class TestRiskCategory:
    def test_values(self):
        assert RiskCategory.COLLISION.value == "collision"
        assert RiskCategory.SECURITY.value == "security"


class TestHedgeStrategy:
    def test_values(self):
        assert HedgeStrategy.DIVERSIFICATION.value == "diversification"


class TestRiskHedgeCalculator:
    def setup_method(self):
        np.random.seed(42)
        self.calc = RiskHedgeCalculator()

    def test_add_risk_factor(self):
        self.calc.add_risk_factor(RiskCategory.COLLISION, 0.1, 0.8)
        assert len(self.calc.risk_factors[RiskCategory.COLLISION]) == 1

    def test_portfolio_risk_empty(self):
        metrics = self.calc.calculate_portfolio_risk(np.array([]))
        assert metrics.total_risk == 0

    def test_portfolio_risk(self):
        self.calc.add_risk_factor(RiskCategory.COLLISION, 0.1, 0.8)
        self.calc.mission_returns = [0.1, 0.15, 0.05]
        self.calc.mission_variance = 0.01
        metrics = self.calc.calculate_portfolio_risk(np.array([0.5, 0.3, 0.2]))
        assert isinstance(metrics, PortfolioMetrics)
        assert metrics.total_risk > 0

    def test_portfolio_risk_no_returns(self):
        metrics = self.calc.calculate_portfolio_risk(np.array([0.5, 0.5]))
        assert isinstance(metrics, PortfolioMetrics)

    def test_optimize_hedge(self):
        actions = self.calc.optimize_hedge(1000)
        assert len(actions) == 4
        total_cost = sum(a.cost for a in actions)
        assert total_cost <= 1000 + 1e-6

    def test_calculate_var_empty(self):
        assert self.calc.calculate_var() == 0.0

    def test_calculate_var(self):
        self.calc.mission_returns = list(np.random.randn(100))
        var = self.calc.calculate_var(0.95)
        assert var >= 0

    def test_calculate_cvar_empty(self):
        assert self.calc.calculate_cvar() == 0.0

    def test_calculate_cvar(self):
        self.calc.mission_returns = list(np.random.randn(100))
        cvar = self.calc.calculate_cvar(0.95)
        assert cvar >= 0

    def test_simulate_monte_carlo(self):
        self.calc.add_risk_factor(RiskCategory.WEATHER, 0.2, 0.5)
        result = self.calc.simulate_monte_carlo(num_simulations=100)
        assert "mean_return" in result
        assert "probability_loss" in result

    def test_get_risk_report(self):
        self.calc.add_risk_factor(RiskCategory.BATTERY, 0.15, 0.6)
        report = self.calc.get_risk_report()
        assert report["total_risk_factors"] == 1
        assert "battery" in report["category_risks"]


# ── quantum_resilience ────────────────────────────────────────────────────

from simulation.quantum_resilience import (
    EncryptionScheme,
    KeyExchange,
    QuantumKey,
    QuantumResilienceManager,
    SecureChannel,
)


class TestEncryptionScheme:
    def test_values(self):
        assert EncryptionScheme.CLASSICAL_AES256.value == "aes256"
        assert EncryptionScheme.HYBRID_CRYSTALS_KYBER.value == "crystals_kyber"


class TestQuantumResilienceManager:
    def setup_method(self):
        self.qrm = QuantumResilienceManager()

    def test_init(self):
        assert self.qrm.post_quantum_ready
        assert self.qrm.hybrid_mode

    def test_init_channel(self):
        ch_id = self.qrm.initialize_secure_channel("drone_1")
        assert ch_id in self.qrm.secure_channels

    def test_encrypt_decrypt(self):
        ch_id = self.qrm.initialize_secure_channel("drone_1")
        plaintext = b"Hello, quantum world!"
        ciphertext = self.qrm.encrypt(ch_id, plaintext)
        decrypted = self.qrm.decrypt(ch_id, ciphertext)
        assert decrypted == plaintext

    def test_encrypt_missing_channel(self):
        with pytest.raises(ValueError):
            self.qrm.encrypt("nonexistent", b"data")

    def test_decrypt_missing_channel(self):
        with pytest.raises(ValueError):
            self.qrm.decrypt("nonexistent", b"data")

    def test_decrypt_short_ciphertext(self):
        ch_id = self.qrm.initialize_secure_channel("d1")
        with pytest.raises(ValueError, match="Invalid ciphertext"):
            self.qrm.decrypt(ch_id, b"short")

    def test_rotate_key_not_expired(self):
        ch_id = self.qrm.initialize_secure_channel("d1")
        assert not self.qrm.rotate_key(ch_id)

    def test_rotate_key_missing_channel(self):
        assert not self.qrm.rotate_key("nonexistent")

    def test_key_exchange(self):
        session_key = self.qrm.perform_key_exchange("d1", "d2")
        assert isinstance(session_key, str)
        assert self.qrm.metrics["keys_generated"] == 1

    def test_verify_quantum_readiness(self):
        readiness = self.qrm.verify_quantum_readiness()
        assert readiness["post_quantum_ready"]
        assert readiness["hybrid_mode"]

    def test_get_metrics(self):
        self.qrm.initialize_secure_channel("d1")
        metrics = self.qrm.get_metrics()
        assert isinstance(metrics, dict)

    def test_revoke_key(self):
        ch_id = self.qrm.initialize_secure_channel("d1")
        key_id = self.qrm.secure_channels[ch_id].current_key.key_id
        assert self.qrm.revoke_key(key_id)

    def test_revoke_key_missing(self):
        assert not self.qrm.revoke_key("nonexistent")

    def test_emergency_key_rollover(self):
        ch_id = self.qrm.initialize_secure_channel("d1")
        old_key = self.qrm.secure_channels[ch_id].current_key.key_id
        self.qrm.emergency_key_rollover("d1")
        new_key = self.qrm.secure_channels[ch_id].current_key.key_id
        assert old_key != new_key

    def test_no_hybrid_mode(self):
        qrm = QuantumResilienceManager(hybrid_mode=False)
        ch_id = qrm.initialize_secure_channel("d1")
        plaintext = b"test data"
        ciphertext = qrm.encrypt(ch_id, plaintext)
        decrypted = qrm.decrypt(ch_id, ciphertext)
        assert decrypted == plaintext


# ── neural_architecture_search ────────────────────────────────────────────

from simulation.neural_architecture_search import (
    Architecture,
    NeuralArchitectureSearch,
    NeuralBlock,
    OperationType,
    SearchStrategy as NASSearchStrategy,
)


class TestOperationType:
    def test_values(self):
        assert OperationType.CONV2D.value == "conv2d"
        assert OperationType.DROPOUT.value == "dropout"


class TestNeuralArchitectureSearch:
    def setup_method(self):
        np.random.seed(42)

    def test_init(self):
        nas = NeuralArchitectureSearch(
            search_space={}, population_size=5, generations=2,
        )
        assert len(nas.population) == 5

    def test_search_evolution(self):
        nas = NeuralArchitectureSearch(
            search_space={},
            strategy=NASSearchStrategy.EVOLUTION,
            population_size=6, generations=3,
        )
        best = nas.search()
        assert isinstance(best, Architecture)
        assert best.accuracy > 0

    def test_search_random(self):
        nas = NeuralArchitectureSearch(
            search_space={},
            strategy=NASSearchStrategy.RANDOM,
            population_size=4, generations=2,
        )
        best = nas.search()
        assert isinstance(best, Architecture)

    def test_sample_parameters_conv2d(self):
        nas = NeuralArchitectureSearch(search_space={}, population_size=2, generations=1)
        params = nas._sample_parameters(OperationType.CONV2D)
        assert "filters" in params
        assert "kernel_size" in params

    def test_sample_parameters_dense(self):
        nas = NeuralArchitectureSearch(search_space={}, population_size=2, generations=1)
        params = nas._sample_parameters(OperationType.DENSE)
        assert "units" in params

    def test_sample_parameters_attention(self):
        nas = NeuralArchitectureSearch(search_space={}, population_size=2, generations=1)
        params = nas._sample_parameters(OperationType.ATTENTION)
        assert "heads" in params

    def test_sample_parameters_other(self):
        nas = NeuralArchitectureSearch(search_space={}, population_size=2, generations=1)
        params = nas._sample_parameters(OperationType.POOLING)
        assert "pool_size" in params

    def test_compute_output_shape_conv2d(self):
        nas = NeuralArchitectureSearch(search_space={}, population_size=2, generations=1)
        shape = nas._compute_output_shape(
            (224, 224, 3), OperationType.CONV2D,
            {"strides": 2, "kernel_size": 3, "filters": 64},
        )
        assert shape == (112, 112, 64)

    def test_compute_output_shape_dense(self):
        nas = NeuralArchitectureSearch(search_space={}, population_size=2, generations=1)
        shape = nas._compute_output_shape(
            (256,), OperationType.DENSE, {"units": 128},
        )
        assert shape == (128,)

    def test_compute_output_shape_pooling(self):
        nas = NeuralArchitectureSearch(search_space={}, population_size=2, generations=1)
        shape = nas._compute_output_shape(
            (64, 64, 32), OperationType.POOLING, {"pool_size": 2},
        )
        assert shape == (32, 32, 32)

    def test_estimate_params(self):
        nas = NeuralArchitectureSearch(search_space={}, population_size=2, generations=1)
        block = NeuralBlock(
            "b1", OperationType.CONV2D,
            {"filters": 64, "kernel_size": 3},
            (224, 224, 3), (224, 224, 64),
        )
        params = nas._estimate_params(block)
        assert params == 64 * 9 * 3

    def test_get_best_architecture_none(self):
        nas = NeuralArchitectureSearch(search_space={}, population_size=2, generations=1)
        assert nas.get_best_architecture() is None

    def test_get_search_history(self):
        nas = NeuralArchitectureSearch(
            search_space={}, population_size=4, generations=2,
        )
        nas.search()
        history = nas.get_search_history()
        assert len(history) == 2

    def test_mutate(self):
        nas = NeuralArchitectureSearch(search_space={}, population_size=2, generations=1)
        arch = nas.population[0]
        mutated = nas._mutate(arch)
        assert isinstance(mutated, Architecture)

    def test_custom_fitness(self):
        def custom_fn(arch):
            return 0.42

        nas = NeuralArchitectureSearch(
            search_space={}, population_size=4, generations=2,
            fitness_fn=custom_fn,
        )
        best = nas.search()
        assert abs(best.accuracy - 0.42) < 1e-6
