"""Phase 661-670: Advanced AI 모듈 테스트."""

import numpy as np
import pytest
import torch


# ── Transformer Trajectory ──────────────────────────────────────────────
class TestPositionalEncoding:
    def test_output_shape(self):
        from simulation.transformer_trajectory import PositionalEncoding
        pe = PositionalEncoding(d_model=64)
        x = torch.zeros(2, 10, 64)
        out = pe(x)
        assert out.shape == (2, 10, 64)

    def test_different_positions(self):
        from simulation.transformer_trajectory import PositionalEncoding
        pe = PositionalEncoding(d_model=64, dropout=0.0)
        x = torch.zeros(1, 20, 64)
        out = pe(x)
        assert not torch.allclose(out[0, 0], out[0, 1])


class TestTrajectoryTransformer:
    def test_forward_shape(self):
        from simulation.transformer_trajectory import TrajectoryTransformer
        model = TrajectoryTransformer(pred_horizon=5)
        x = torch.randn(4, 15, 6)
        out = model(x)
        assert out.shape == (4, 5, 3)

    def test_single_sequence(self):
        from simulation.transformer_trajectory import TrajectoryTransformer
        model = TrajectoryTransformer(pred_horizon=10)
        x = torch.randn(1, 8, 6)
        out = model(x)
        assert out.shape == (1, 10, 3)

    def test_deterministic_eval(self):
        from simulation.transformer_trajectory import TrajectoryTransformer
        model = TrajectoryTransformer(pred_horizon=5)
        model.eval()
        x = torch.randn(2, 10, 6)
        with torch.no_grad():
            o1 = model(x)
            o2 = model(x)
        assert torch.allclose(o1, o2)


class TestTrajectoryPredictor:
    def test_add_trajectory(self):
        from simulation.transformer_trajectory import TrajectoryPredictor
        pred = TrajectoryPredictor()
        pred.add_trajectory("d1", np.zeros((10, 3)))
        assert pred.get_trajectory_count() == 1

    def test_train_step_returns_loss(self):
        from simulation.transformer_trajectory import TrajectoryPredictor
        pred = TrajectoryPredictor(pred_horizon=5)
        states = np.random.randn(4, 10, 6).astype(np.float32)
        targets = np.random.randn(4, 5, 3).astype(np.float32)
        loss = pred.train_step(states, targets)
        assert isinstance(loss, float)
        assert loss > 0

    def test_predict_2d_input(self):
        from simulation.transformer_trajectory import TrajectoryPredictor
        pred = TrajectoryPredictor(pred_horizon=5)
        states = np.random.randn(10, 6).astype(np.float32)
        out = pred.predict(states)
        assert out.shape == (5, 3)

    def test_predict_3d_input(self):
        from simulation.transformer_trajectory import TrajectoryPredictor
        pred = TrajectoryPredictor(pred_horizon=5)
        states = np.random.randn(3, 10, 6).astype(np.float32)
        out = pred.predict(states)
        assert out.shape == (3, 5, 3)

    def test_accuracy_metrics_empty(self):
        from simulation.transformer_trajectory import TrajectoryPredictor
        pred = TrajectoryPredictor()
        metrics = pred.get_prediction_accuracy()
        assert metrics["steps"] == 0

    def test_accuracy_metrics_after_training(self):
        from simulation.transformer_trajectory import TrajectoryPredictor
        pred = TrajectoryPredictor(pred_horizon=5)
        for _ in range(3):
            s = np.random.randn(2, 10, 6).astype(np.float32)
            t = np.random.randn(2, 5, 3).astype(np.float32)
            pred.train_step(s, t)
        metrics = pred.get_prediction_accuracy()
        assert metrics["steps"] == 3
        assert metrics["mean_loss"] > 0


# ── Diffusion Path Generator ───────────────────────────────────────────
class TestNoiseScheduler:
    def test_alpha_bars_decreasing(self):
        from simulation.diffusion_path_generator import NoiseScheduler
        ns = NoiseScheduler(num_timesteps=50)
        assert all(ns.alpha_bars[i] >= ns.alpha_bars[i + 1] for i in range(49))

    def test_add_noise_shape(self):
        from simulation.diffusion_path_generator import NoiseScheduler
        ns = NoiseScheduler()
        x = torch.randn(4, 20, 3)
        t = torch.zeros(4, dtype=torch.long)
        noisy, noise = ns.add_noise(x, t)
        assert noisy.shape == x.shape
        assert noise.shape == x.shape

    def test_t0_mostly_signal(self):
        from simulation.diffusion_path_generator import NoiseScheduler
        ns = NoiseScheduler()
        x = torch.ones(1, 10, 3) * 5.0
        t = torch.zeros(1, dtype=torch.long)
        noisy, _ = ns.add_noise(x, t)
        assert torch.mean(noisy).item() > 3.0  # mostly original signal at t=0


class TestDenoisingNetwork:
    def test_forward_shape(self):
        from simulation.diffusion_path_generator import DenoisingNetwork
        net = DenoisingNetwork(path_length=20)
        x = torch.randn(4, 20, 3)
        t = torch.randint(0, 100, (4,))
        out = net(x, t)
        assert out.shape == (4, 20, 3)


class TestDiffusionPathGenerator:
    def test_train_step(self):
        from simulation.diffusion_path_generator import DiffusionPathGenerator
        gen = DiffusionPathGenerator(path_length=10, num_timesteps=10)
        paths = np.random.randn(4, 10, 3).astype(np.float32)
        loss = gen.train_step(paths)
        assert isinstance(loss, float)
        assert loss > 0

    def test_sample_shape(self):
        from simulation.diffusion_path_generator import DiffusionPathGenerator
        gen = DiffusionPathGenerator(path_length=10, num_timesteps=5)
        samples = gen.sample(num_paths=2)
        assert samples.shape == (2, 10, 3)

    def test_generate_endpoints(self):
        from simulation.diffusion_path_generator import DiffusionPathGenerator
        gen = DiffusionPathGenerator(path_length=10, num_timesteps=5)
        start = np.array([0.0, 0.0, 0.0])
        end = np.array([100.0, 100.0, 50.0])
        path = gen.generate(start, end, num_steps=10)
        assert path.shape == (10, 3)
        np.testing.assert_array_almost_equal(path[0], start)
        np.testing.assert_array_almost_equal(path[-1], end)

    def test_stats(self):
        from simulation.diffusion_path_generator import DiffusionPathGenerator
        gen = DiffusionPathGenerator(path_length=10, num_timesteps=5)
        paths = np.random.randn(2, 10, 3).astype(np.float32)
        gen.train_step(paths)
        stats = gen.get_stats()
        assert stats["train_steps"] == 1
        assert stats["mean_loss"] > 0


# ── GNN Communication (기존 모듈 통합 테스트) ──────────────────────────
class TestGNNCommunication:
    def test_build_adjacency(self):
        from simulation.gnn_communication import build_adjacency
        pos = np.array([[0, 0, 0], [100, 0, 0], [1000, 0, 0]], dtype=np.float32)
        adj = build_adjacency(pos, comm_range=500)
        assert adj[0, 1] == 1.0
        assert adj[0, 2] == 0.0
        assert adj[0, 0] == 0.0

    def test_drone_graph_forward(self):
        from simulation.gnn_communication import DroneGraphNetwork
        net = DroneGraphNetwork()
        feat = torch.randn(5, 6).to(net.device)
        adj = torch.ones(5, 5).to(net.device)
        adj.fill_diagonal_(0)
        emb = net(feat, adj)
        assert emb.shape == (5, 32)

    def test_predict_risk(self):
        from simulation.gnn_communication import DroneGraphNetwork
        net = DroneGraphNetwork()
        feat = torch.randn(5, 6).to(net.device)
        adj = torch.ones(5, 5).to(net.device)
        adj.fill_diagonal_(0)
        emb = net(feat, adj)
        risk = net.predict_risk(emb)
        assert risk.shape == (5,)
        assert (risk >= 0).all() and (risk <= 1).all()

    def test_compute_risk_numpy(self):
        from simulation.gnn_communication import DroneGraphNetwork
        net = DroneGraphNetwork()
        pos = np.random.randn(5, 3).astype(np.float32)
        vel = np.random.randn(5, 3).astype(np.float32)
        risk = net.compute_risk(pos, vel, comm_range=10000)
        assert risk.shape == (5,)


# ── Federated Learning v3 (기존 모듈 통합 테스트) ─────────────────────
class TestFederatedLearningV3:
    def test_register_client(self):
        from simulation.federated_learning_v3 import FederatedLearningV3
        fl = FederatedLearningV3(model_shape={"w": (4, 4)})
        fl.register_client("d1")
        assert "d1" in fl.client_models

    def test_submit_and_aggregate(self):
        from simulation.federated_learning_v3 import FederatedLearningV3
        fl = FederatedLearningV3(model_shape={"w": (4,)}, min_clients_per_round=2)
        for did in ["d1", "d2", "d3"]:
            update = fl.simulate_local_training(did)
            fl.submit_update(update)
        result = fl.aggregate()
        assert result is not None
        assert result.round_number == 0

    def test_should_aggregate_false(self):
        from simulation.federated_learning_v3 import FederatedLearningV3
        fl = FederatedLearningV3(model_shape={"w": (4,)}, min_clients_per_round=5)
        fl.simulate_local_training("d1")
        assert not fl.should_aggregate()

    def test_stats(self):
        from simulation.federated_learning_v3 import FederatedLearningV3
        fl = FederatedLearningV3(model_shape={"w": (4,)})
        stats = fl.get_stats()
        assert stats["current_round"] == 0
        assert stats["differential_privacy_enabled"] is True
