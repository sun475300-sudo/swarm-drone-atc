"""Phase 156-163 tests: advanced AI routing and prediction modules (8 modules, 32 tests)."""

import numpy as np


class TestGeneticPathPlanner:
    def setup_method(self):
        from simulation.genetic_path_planner import GeneticPathPlanner

        self.g = GeneticPathPlanner(pop_size=20, n_waypoints=4, seed=42)

    def test_optimize_returns_path(self):
        result = self.g.optimize(start=(0, 0, 50), goal=(500, 500, 50), generations=10)
        assert "path" in result
        assert len(result["path"]) >= 2

    def test_environment_reflects_summary(self):
        self.g.set_environment(obstacles=[(100, 100, 50)], nfz=[(200, 200, 50, 80)])
        summary = self.g.summary()
        assert summary["obstacles"] == 1
        assert summary["nfz_zones"] == 1

    def test_fitness_positive(self):
        result = self.g.optimize(start=(0, 0, 50), goal=(300, 200, 50), generations=8)
        assert result["fitness"] > 0

    def test_summary(self):
        self.g.optimize(start=(0, 0, 50), goal=(200, 200, 50), generations=5)
        summary = self.g.summary()
        assert summary["plans_generated"] >= 1


class TestDeepRLController:
    def setup_method(self):
        from simulation.deep_rl_controller import DeepRLController

        self.r = DeepRLController(state_dim=8, n_actions=5, seed=42)

    def test_select_action_range(self):
        action = self.r.select_action([0.0] * 8)
        assert 0 <= action < 5

    def test_store_transition(self):
        self.r.store_transition([0.0] * 8, 1, 0.5, [0.1] * 8, done=False)
        summary = self.r.summary()
        assert summary["buffer_size"] == 1

    def test_train_step_runs(self):
        for i in range(40):
            s = [float(i % 5)] * 8
            ns = [float((i + 1) % 5)] * 8
            self.r.store_transition(s, i % 5, 0.1, ns, done=(i % 9 == 0))
        loss = self.r.train_step(batch_size=16)
        assert loss >= 0

    def test_summary(self):
        summary = self.r.summary()
        assert "epsilon" in summary


class TestGNNTraffic:
    def setup_method(self):
        from simulation.gnn_traffic import GNNTraffic

        self.g = GNNTraffic(seed=42)

    def test_update_graph(self):
        self.g.update_graph({"d1": (0, 0, 0), "d2": (10, 10, 0), "d3": (500, 500, 0)})
        summary = self.g.summary()
        assert summary["nodes"] == 3

    def test_predict_density(self):
        self.g.update_graph({"d1": (0, 0, 0), "d2": (20, 20, 0)})
        pred = self.g.predict_density(horizon=20)
        assert 0 <= pred["risk"] <= 1

    def test_hotspots(self):
        self.g.update_graph({"d1": (0, 0, 0), "d2": (10, 5, 0), "d3": (20, 10, 0)})
        hotspots = self.g.hotspots(top_k=2)
        assert isinstance(hotspots, list)

    def test_summary(self):
        summary = self.g.summary()
        assert "threshold" in summary


class TestBayesianTuner:
    def setup_method(self):
        from simulation.bayesian_tuner import BayesianTuner

        self.tuner = BayesianTuner(
            bounds={"lr": (0.0001, 0.1), "gamma": (0.8, 0.99)},
            seed=42,
        )

    def test_suggest(self):
        candidates = self.tuner.suggest(3)
        assert len(candidates) == 3
        assert "lr" in candidates[0]

    def test_report_and_best(self):
        self.tuner.report({"lr": 0.01, "gamma": 0.95}, 0.8)
        self.tuner.report({"lr": 0.02, "gamma": 0.9}, 0.7)
        best = self.tuner.best()
        assert best["score"] >= 0.8

    def test_optimize(self):
        def objective(p: dict[str, float]) -> float:
            return 1.0 - abs(p["lr"] - 0.02) - abs(p["gamma"] - 0.93)

        result = self.tuner.optimize(objective, n_iter=8)
        assert "params" in result
        assert "score" in result

    def test_summary(self):
        summary = self.tuner.summary()
        assert summary["parameters"] == 2


class TestEnsemblePredictor:
    def setup_method(self):
        from simulation.ensemble_predictor import EnsemblePredictor

        self.e = EnsemblePredictor()

    def test_register_and_predict(self):
        self.e.register_model("m1", lambda x: float(sum(x)) * 0.1, weight=1.0)
        self.e.register_model("m2", lambda x: float(max(x)) * 0.2, weight=1.0)
        pred = self.e.predict([1.0, 2.0, 3.0])
        assert "prediction" in pred
        assert "components" in pred

    def test_calibrate(self):
        self.e.register_model("m1", lambda x: x[0], weight=1.0)
        self.e.register_model("m2", lambda x: x[0] * 0.5, weight=1.0)
        w = self.e.calibrate([([2.0], 2.0), ([4.0], 4.0)])
        assert len(w) == 2

    def test_top_model(self):
        self.e.register_model("m1", lambda x: x[0], weight=3.0)
        self.e.register_model("m2", lambda x: x[0], weight=1.0)
        assert self.e.top_model() == "m1"

    def test_summary(self):
        summary = self.e.summary()
        assert "models" in summary


class TestAnomalyAutoencoder:
    def setup_method(self):
        from simulation.anomaly_autoencoder import AnomalyAutoencoder

        self.a = AnomalyAutoencoder(input_dim=4, latent_dim=2, seed=42)

    def test_fit(self):
        normal = np.random.default_rng(42).normal(0, 1, (60, 4)).tolist()
        result = self.a.fit(normal, epochs=20)
        assert result["epochs"] == 20

    def test_reconstruction_error(self):
        normal = np.random.default_rng(0).normal(0, 1, (40, 4)).tolist()
        self.a.fit(normal, epochs=10)
        err = self.a.reconstruction_error(normal[:5])
        assert len(err) == 5

    def test_detect(self):
        rng = np.random.default_rng(1)
        normal = rng.normal(0, 1, (80, 4)).tolist()
        self.a.fit(normal, epochs=25)
        out = self.a.detect([8.0, 8.0, 8.0, 8.0])
        assert "is_anomaly" in out

    def test_summary(self):
        summary = self.a.summary()
        assert summary["input_dim"] == 4


class TestTimeSeriesForecaster:
    def setup_method(self):
        from simulation.time_series_forecaster import TimeSeriesForecaster

        self.f = TimeSeriesForecaster(alpha=0.3)

    def test_fit(self):
        result = self.f.fit([10, 12, 13, 15, 18, 20])
        assert result["n_points"] == 6

    def test_forecast(self):
        self.f.fit([100, 102, 101, 105, 110])
        preds = self.f.forecast(steps=4)
        assert len(preds) == 4

    def test_update(self):
        self.f.fit([1, 2, 3, 4])
        self.f.update(5)
        summary = self.f.summary()
        assert summary["points"] == 5

    def test_summary(self):
        summary = self.f.summary()
        assert "alpha" in summary


class TestMARLCoordinator:
    def setup_method(self):
        from simulation.marl_coordinator import MARLCoordinator

        self.m = MARLCoordinator(n_actions=4, seed=42)

    def test_register_agent(self):
        self.m.register_agent("a1")
        summary = self.m.summary()
        assert summary["agents"] == 1

    def test_select_actions(self):
        self.m.register_agent("a1")
        self.m.register_agent("a2")
        actions = self.m.select_actions({"a1": 0, "a2": 1})
        assert set(actions.keys()) == {"a1", "a2"}

    def test_train_step(self):
        self.m.register_agent("a1")
        for i in range(20):
            done = i % 7 == 0
            self.m.store_step({"a1": (i % 3, i % 4, 1.0, (i + 1) % 3, done)}, shared_reward=0.1)
        loss = self.m.train_step(batch_size=12)
        assert loss >= 0

    def test_policy_snapshot(self):
        self.m.register_agent("a1")
        self.m.store_step({"a1": (0, 1, 1.0, 1, False)})
        self.m.train_step(batch_size=1)
        snap = self.m.policy_snapshot()
        assert "a1" in snap
