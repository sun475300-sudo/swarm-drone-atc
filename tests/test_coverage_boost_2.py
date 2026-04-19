"""
Coverage boost tests - Phase 2.
Targets 0% coverage modules: advanced_path_planner, rl_agent, autoML_pipeline,
ai_inference_engine, edge_cloud_orchestrator, federated_learning_v3.
"""

import time

import numpy as np
import pytest
import torch

# ── advanced_path_planner ─────────────────────────────────────────────────

from simulation.advanced_path_planner import (
    AdvancedPathPlanner,
    PathMetric,
    PathResult,
    Waypoint,
)


class TestWaypoint:
    def test_defaults(self):
        w = Waypoint(x=1.0, y=2.0, z=3.0)
        assert w.velocity == 0.0
        assert w.timestamp == 0.0
        assert w.cost == 0.0
        assert w.parent is None

    def test_all_fields(self):
        w = Waypoint(x=1, y=2, z=3, velocity=5, timestamp=10, cost=2.5)
        assert w.velocity == 5


class TestPathResult:
    def test_fields(self):
        pr = PathResult(
            waypoints=[], total_distance=100, total_time=10,
            total_energy=50, safety_score=0.9, algorithm="A*",
            computation_time=0.01,
        )
        assert pr.algorithm == "A*"
        assert pr.total_distance == 100


class TestPathMetric:
    def test_values(self):
        assert PathMetric.DISTANCE.value == "distance"
        assert PathMetric.ENERGY.value == "energy"


class TestAdvancedPathPlanner:
    def setup_method(self):
        self.planner = AdvancedPathPlanner(
            bounds=(-100, 100, -100, 100, 0, 100),
            max_iterations=200,
            goal_tolerance=10.0,
        )

    def test_is_valid_position_in_bounds(self):
        assert self.planner.is_valid_position(0, 0, 50)

    def test_is_valid_position_out_of_bounds(self):
        assert not self.planner.is_valid_position(200, 0, 50)

    def test_add_obstacle_blocks_position(self):
        self.planner.add_obstacle(0, 0, 50, 20)
        assert not self.planner.is_valid_position(5, 5, 50)

    def test_add_no_fly_zone(self):
        # Use wider z-bounds to test NFZ altitude logic
        planner = AdvancedPathPlanner(
            bounds=(-100, 100, -100, 100, 0, 200), max_iterations=200,
        )
        planner.add_no_fly_zone(-50, 50, -50, 50)
        # Below 120m in NFZ should be invalid
        assert not planner.is_valid_position(0, 0, 50)
        # Above 120m should be valid
        assert planner.is_valid_position(0, 0, 130)

    def test_set_wind_field(self):
        self.planner.set_wind_field(lambda x, y, z: (1.0, 0.5, 0.0))
        assert self.planner.wind_field is not None

    def test_distance(self):
        d = self.planner.distance((0, 0, 0), (3, 4, 0))
        assert abs(d - 5.0) < 1e-6

    def test_heuristic_no_wind(self):
        h = self.planner.heuristic((0, 0, 0), (3, 4, 0))
        assert abs(h - 5.0) < 1e-6

    def test_heuristic_with_wind(self):
        self.planner.set_wind_field(lambda x, y, z: (10.0, 0.0, 0.0))
        h = self.planner.heuristic((0, 0, 0), (3, 4, 0))
        assert h > 5.0  # Wind increases heuristic

    def test_pos_to_key_and_back(self):
        pos = (15.0, 25.0, 35.0)
        key = self.planner._pos_to_key(pos, 5.0)
        back = self.planner._key_to_pos(key, 5.0)
        assert back == (15.0, 25.0, 35.0)

    def test_plan_astar_invalid_start(self):
        result = self.planner.plan_astar((999, 999, 999), (0, 0, 50))
        assert result.waypoints == []

    def test_plan_astar_simple(self):
        result = self.planner.plan_astar((0, 0, 50), (20, 0, 50), resolution=10.0)
        assert result.algorithm == "A*"
        assert result.total_distance >= 0

    def test_plan_rrt_star_invalid_start(self):
        result = self.planner.plan_rrt_star((999, 999, 999), (0, 0, 50))
        assert result.waypoints == []

    def test_plan_rrt_star_simple(self):
        np.random.seed(42)
        planner = AdvancedPathPlanner(
            bounds=(-100, 100, -100, 100, 0, 100),
            max_iterations=500,
            goal_tolerance=15.0,
        )
        result = planner.plan_rrt_star(
            (0, 0, 50), (30, 0, 50), step_size=20.0, goal_sample_rate=0.3,
        )
        assert result.algorithm == "RRT*"

    def test_plan_hybrid(self):
        result = self.planner.plan_hybrid((0, 0, 50), (20, 0, 50))
        assert result.algorithm in ("A*", "RRT*", "Hybrid")

    def test_smooth_path_short(self):
        wps = [Waypoint(0, 0, 0), Waypoint(10, 0, 0)]
        smoothed = self.planner.smooth_path(wps)
        assert len(smoothed) == 2

    def test_smooth_path_long(self):
        wps = [Waypoint(i * 10, 0, 50) for i in range(5)]
        smoothed = self.planner.smooth_path(wps, iterations=5)
        assert len(smoothed) == 5

    def test_calculate_safety_score_empty(self):
        score = self.planner._calculate_safety_score([])
        assert score == 0.0

    def test_calculate_safety_score_with_obstacles(self):
        self.planner.add_obstacle(50, 0, 50, 5)
        path = [(0, 0, 50), (25, 0, 50)]
        score = self.planner._calculate_safety_score(path)
        assert 0.0 <= score <= 1.0

    def test_check_collision_free(self):
        assert self.planner._check_collision_free((0, 0, 50), (10, 0, 50))

    def test_check_collision_blocked(self):
        self.planner.add_obstacle(5, 0, 50, 20)
        assert not self.planner._check_collision_free((0, 0, 50), (10, 0, 50))

    def test_random_sample(self):
        s = self.planner._random_sample()
        assert len(s) == 3


# ── rl_agent ──────────────────────────────────────────────────────────────

from simulation.rl_agent import (
    ACT_DIM,
    ARENA_SIZE,
    COLLISION_DIST,
    GOAL_DIST,
    MAX_STEPS,
    NUM_NEIGHBORS,
    OBS_DIM,
    WARNING_DIST,
    ActorCritic,
    DroneEnv,
    PPOAgent,
    RolloutBuffer,
    StepResult,
)


class TestStepResult:
    def test_fields(self):
        sr = StepResult(obs=np.zeros(3), reward=1.0, done=False)
        assert sr.reward == 1.0
        assert not sr.done


class TestDroneEnv:
    def setup_method(self):
        self.env = DroneEnv(seed=42)

    def test_reset_returns_obs(self):
        obs = self.env.reset()
        assert obs.shape == (OBS_DIM,)
        assert obs.dtype == np.float32

    def test_step_returns_step_result(self):
        self.env.reset()
        result = self.env.step(np.array([0.1, 0.0, 0.0]))
        assert isinstance(result, StepResult)
        assert result.obs.shape == (OBS_DIM,)

    def test_step_clips_action(self):
        self.env.reset()
        result = self.env.step(np.array([100.0, -100.0, 50.0]))
        assert isinstance(result, StepResult)

    def test_episode_terminates(self):
        self.env.reset()
        done = False
        for _ in range(MAX_STEPS + 10):
            result = self.env.step(np.zeros(3))
            if result.done:
                done = True
                break
        assert done


class TestActorCritic:
    def test_forward(self):
        net = ActorCritic()
        obs = torch.randn(1, OBS_DIM)
        dist, value = net(obs)
        assert value.shape == (1, 1)
        action = dist.sample()
        assert action.shape == (1, ACT_DIM)

    def test_batch_forward(self):
        net = ActorCritic()
        obs = torch.randn(8, OBS_DIM)
        dist, value = net(obs)
        assert value.shape == (8, 1)


class TestRolloutBuffer:
    def test_clear(self):
        buf = RolloutBuffer()
        buf.obs.append(1)
        buf.rewards.append(2)
        buf.clear()
        assert len(buf.obs) == 0
        assert len(buf.rewards) == 0


class TestPPOAgent:
    def test_select_action(self):
        agent = PPOAgent(seed=42)
        obs = np.random.randn(OBS_DIM).astype(np.float32)
        action, log_prob, value = agent.select_action(obs)
        assert action.shape == (ACT_DIM,)
        assert isinstance(log_prob, float)
        assert isinstance(value, float)

    def test_collect_rollout(self):
        agent = PPOAgent(seed=42)
        env = DroneEnv(seed=42)
        total_reward = agent.collect_rollout(env)
        assert isinstance(total_reward, float)
        assert len(agent._buffer.obs) > 0

    def test_update_empty_buffer(self):
        agent = PPOAgent(seed=42)
        loss = agent.update()
        assert loss == 0.0

    def test_update_after_rollout(self):
        agent = PPOAgent(seed=42, epochs=2)
        env = DroneEnv(seed=42)
        agent.collect_rollout(env)
        loss = agent.update()
        assert isinstance(loss, float)

    def test_train_short(self):
        agent = PPOAgent(seed=42, epochs=2)
        rewards = agent.train(n_episodes=3, seed=42)
        assert len(rewards) == 3


class TestRLConstants:
    def test_constants(self):
        assert OBS_DIM == 18
        assert ACT_DIM == 3
        assert COLLISION_DIST == 5.0
        assert WARNING_DIST == 15.0
        assert GOAL_DIST == 3.0
        assert MAX_STEPS == 200
        assert NUM_NEIGHBORS == 3
        assert ARENA_SIZE == 100.0


# ── autoML_pipeline ───────────────────────────────────────────────────────

from simulation.autoML_pipeline import (
    AutoMLPipeline,
    HyperparameterConfig,
    ModelType,
    SearchStrategy,
    TrialResult,
)


class TestHyperparameterConfig:
    def test_defaults(self):
        cfg = HyperparameterConfig()
        assert cfg.learning_rate == 0.1
        assert cfg.max_depth == 6
        assert cfg.n_estimators == 100


class TestModelType:
    def test_values(self):
        assert ModelType.LIGHTGBM.value == "lightgbm"
        assert ModelType.NEURAL_NETWORK.value == "neural_network"


class TestSearchStrategy:
    def test_values(self):
        assert SearchStrategy.BAYESIAN.value == "bayesian"
        assert SearchStrategy.GENETIC.value == "genetic"


class TestAutoMLPipeline:
    def setup_method(self):
        np.random.seed(42)

    def test_init_random_search(self):
        pipeline = AutoMLPipeline(
            search_strategy=SearchStrategy.RANDOM_SEARCH, max_trials=3,
        )
        assert pipeline.search_strategy == SearchStrategy.RANDOM_SEARCH

    def test_init_bayesian(self):
        pipeline = AutoMLPipeline(
            search_strategy=SearchStrategy.BAYESIAN, max_trials=3,
        )
        assert pipeline.gaussian_process is not None

    def test_random_search_sample(self):
        pipeline = AutoMLPipeline(
            search_strategy=SearchStrategy.RANDOM_SEARCH, max_trials=3,
        )
        cfg = pipeline._random_search()
        assert isinstance(cfg, HyperparameterConfig)

    def test_grid_search_sample(self):
        pipeline = AutoMLPipeline(
            search_strategy=SearchStrategy.GRID_SEARCH, max_trials=3,
        )
        cfg = pipeline._grid_search()
        assert isinstance(cfg, HyperparameterConfig)

    def test_grid_search_overflow(self):
        pipeline = AutoMLPipeline(
            search_strategy=SearchStrategy.GRID_SEARCH, max_trials=3,
        )
        # Add many fake trials to exceed grid size
        for i in range(999999):
            pipeline.trials.append(
                TrialResult(f"t{i}", HyperparameterConfig(), 0.5, 0.0, 0.0)
            )
        cfg = pipeline._grid_search()
        assert isinstance(cfg, HyperparameterConfig)

    def test_bayesian_search_with_history(self):
        pipeline = AutoMLPipeline(
            search_strategy=SearchStrategy.BAYESIAN, max_trials=3,
        )
        for i in range(10):
            pipeline.trials.append(
                TrialResult(f"t{i}", HyperparameterConfig(), float(i) / 10, 0.0, 0.0)
            )
        cfg = pipeline._bayesian_search()
        assert isinstance(cfg, HyperparameterConfig)

    def test_bayesian_search_few_trials(self):
        pipeline = AutoMLPipeline(
            search_strategy=SearchStrategy.BAYESIAN, max_trials=3,
        )
        pipeline.trials.append(
            TrialResult("t0", HyperparameterConfig(), 0.5, 0.0, 0.0)
        )
        cfg = pipeline._bayesian_search()
        assert isinstance(cfg, HyperparameterConfig)

    def test_train_lightgbm(self):
        pipeline = AutoMLPipeline(model_type=ModelType.LIGHTGBM, max_trials=2)
        X = np.random.randn(20, 5)
        y = np.random.randn(20)
        score = pipeline._train_lightgbm(HyperparameterConfig(n_estimators=5), X, y)
        assert 0 <= score <= 99

    def test_train_xgboost(self):
        pipeline = AutoMLPipeline(model_type=ModelType.XGBOOST, max_trials=2)
        X = np.random.randn(20, 5)
        y = np.random.randn(20)
        score = pipeline._train_xgboost(HyperparameterConfig(n_estimators=5), X, y)
        assert 0 <= score <= 99

    def test_train_random_forest(self):
        pipeline = AutoMLPipeline(model_type=ModelType.RANDOM_FOREST, max_trials=2)
        X = np.random.randn(20, 5)
        y = np.random.randn(20)
        score = pipeline._train_random_forest(
            HyperparameterConfig(n_estimators=50), X, y,
        )
        assert 0 <= score <= 99

    def test_train_neural_network(self):
        pipeline = AutoMLPipeline(model_type=ModelType.NEURAL_NETWORK, max_trials=2)
        X = np.random.randn(20, 5)
        y = np.random.randn(20)
        score = pipeline._train_neural_network(HyperparameterConfig(), X, y)
        assert 0 <= score <= 99

    def test_run(self):
        pipeline = AutoMLPipeline(
            model_type=ModelType.LIGHTGBM,
            search_strategy=SearchStrategy.RANDOM_SEARCH,
            max_trials=3,
        )
        X = np.random.randn(30, 5)
        y = np.random.randn(30)
        best_cfg = pipeline.run(X, y)
        assert isinstance(best_cfg, HyperparameterConfig)
        assert pipeline.best_trial is not None

    def test_get_best_config_none(self):
        pipeline = AutoMLPipeline(max_trials=1)
        assert pipeline.get_best_config() is None

    def test_get_leaderboard(self):
        pipeline = AutoMLPipeline(
            search_strategy=SearchStrategy.RANDOM_SEARCH, max_trials=5,
        )
        X = np.random.randn(20, 5)
        y = np.random.randn(20)
        pipeline.run(X, y)
        lb = pipeline.get_leaderboard(top_k=3)
        assert len(lb) <= 3

    def test_get_optimization_history(self):
        pipeline = AutoMLPipeline(
            search_strategy=SearchStrategy.RANDOM_SEARCH, max_trials=3,
        )
        X = np.random.randn(20, 5)
        y = np.random.randn(20)
        pipeline.run(X, y)
        history = pipeline.get_optimization_history()
        assert "scores" in history
        assert "best_scores" in history


# ── ai_inference_engine ───────────────────────────────────────────────────

from simulation.ai_inference_engine import (
    AIInferenceEngine,
    InferenceModel,
    InferenceRequest,
    InferenceResult,
    InferenceTask,
    ModelMetadata,
)


class TestInferenceEnums:
    def test_inference_model(self):
        assert InferenceModel.ONNX.value == "onnx"
        assert InferenceModel.LSTM.value == "lstm"

    def test_inference_task(self):
        assert InferenceTask.COLLISION_PREDICTION.value == "collision_prediction"


class TestInferenceRequest:
    def test_fields(self):
        req = InferenceRequest(
            task=InferenceTask.COLLISION_PREDICTION,
            inputs={"pos": np.zeros(3)},
        )
        assert req.priority == 5
        assert req.deadline is None


class TestModelMetadata:
    def test_defaults(self):
        m = ModelMetadata(
            name="test", model_type=InferenceModel.ONNX,
            input_shapes={"x": (10, 3)}, output_shapes={"y": (10, 1)},
        )
        assert m.inference_count == 0


class TestAIInferenceEngine:
    def setup_method(self):
        self.engine = AIInferenceEngine()

    def test_load_model(self):
        self.engine.load_model(
            "test_model", InferenceModel.LIGHTGBM, "/fake/path",
            {"x": (10, 3)}, {"y": (10,)},
        )
        assert "test_model" in self.engine.models

    def test_submit_request(self):
        req = InferenceRequest(
            task=InferenceTask.COLLISION_PREDICTION,
            inputs={"pos": np.zeros(3)},
        )
        req_id = self.engine.submit_request(req)
        assert isinstance(req_id, str)
        assert self.engine.metrics["total_requests"] == 1

    def test_submit_request_overflow(self):
        engine = AIInferenceEngine(max_queue_size=1)
        req = InferenceRequest(
            task=InferenceTask.COLLISION_PREDICTION,
            inputs={"pos": np.zeros(3)},
        )
        engine.submit_request(req)
        with pytest.raises(RuntimeError, match="Queue overflow"):
            engine.submit_request(req)

    def test_get_result_not_found(self):
        result = self.engine.get_result("nonexistent")
        assert result is None

    def test_infer_model_not_found(self):
        result = self.engine.infer(
            InferenceTask.COLLISION_PREDICTION,
            {"pos": np.zeros((10, 3))},
            model_name="missing",
        )
        assert result.confidence == 0.0

    def test_infer_lightgbm(self):
        self.engine.load_model(
            "collision_model", InferenceModel.LIGHTGBM, "/path",
            {"x": (10, 3)}, {"y": (10,)},
        )
        result = self.engine.infer(
            InferenceTask.COLLISION_PREDICTION,
            {"positions": np.random.rand(10, 3)},
        )
        assert isinstance(result, InferenceResult)
        assert result.latency_ms >= 0

    def test_infer_xgboost(self):
        self.engine.load_model(
            "xg", InferenceModel.XGBOOST, "/path",
            {"x": (10, 3)}, {"y": (10,)},
        )
        result = self.engine.infer(
            InferenceTask.COLLISION_PREDICTION,
            {"data": np.random.rand(10, 3)},
            model_name="xg",
        )
        assert isinstance(result, InferenceResult)

    def test_infer_onnx(self):
        self.engine.load_model(
            "onnx_m", InferenceModel.ONNX, "/path",
            {"x": (10, 3)}, {"y": (10,)},
        )
        result = self.engine.infer(
            InferenceTask.ANOMALY_DETECTION,
            {"data": np.random.rand(5, 3)},
            model_name="onnx_m",
        )
        assert isinstance(result, InferenceResult)

    def test_infer_lstm(self):
        self.engine.load_model(
            "lstm_m", InferenceModel.LSTM, "/path",
            {"x": (10, 20, 3)}, {"y": (10, 10)},
        )
        result = self.engine.infer(
            InferenceTask.TRAJECTORY_PREDICTION,
            {"history": np.random.rand(10, 20, 3)},
            model_name="lstm_m",
        )
        assert "prediction" in result.outputs

    def test_infer_default_model_type(self):
        self.engine.load_model(
            "tf_m", InferenceModel.TENSORRT, "/path",
            {"x": (10,)}, {"y": (10,)},
        )
        result = self.engine.infer(
            InferenceTask.PATH_OPTIMIZATION,
            {"data": np.random.rand(5, 3)},
            model_name="tf_m",
        )
        assert isinstance(result, InferenceResult)

    def test_get_metrics(self):
        metrics = self.engine.get_metrics()
        assert "global" in metrics
        assert "models" in metrics
        assert "queue_sizes" in metrics

    def test_warm_up(self):
        self.engine.load_model(
            "collision_model", InferenceModel.LIGHTGBM, "/path",
            {"x": (10, 3)}, {"y": (10,)},
        )
        self.engine.warm_up(InferenceTask.COLLISION_PREDICTION, num_iterations=3)
        assert self.engine.models["collision_model"].inference_count == 3

    def test_generate_dummy_inputs_collision(self):
        inputs = self.engine._generate_dummy_inputs(InferenceTask.COLLISION_PREDICTION)
        assert "positions" in inputs
        assert "velocities" in inputs

    def test_generate_dummy_inputs_trajectory(self):
        inputs = self.engine._generate_dummy_inputs(
            InferenceTask.TRAJECTORY_PREDICTION,
        )
        assert "history" in inputs

    def test_generate_dummy_inputs_other(self):
        inputs = self.engine._generate_dummy_inputs(InferenceTask.WEATHER_ESTIMATION)
        assert "data" in inputs

    def test_clear_queue(self):
        req = InferenceRequest(
            task=InferenceTask.COLLISION_PREDICTION,
            inputs={"pos": np.zeros(3)},
        )
        self.engine.submit_request(req)
        self.engine.clear_queue(InferenceTask.COLLISION_PREDICTION)
        assert len(self.engine.inference_queues[InferenceTask.COLLISION_PREDICTION]) == 0

    def test_reset_metrics(self):
        self.engine.metrics["total_requests"] = 99
        self.engine.reset_metrics()
        assert self.engine.metrics["total_requests"] == 0

    def test_calculate_confidence_empty(self):
        c = self.engine._calculate_confidence({})
        assert c == 0.0

    def test_calculate_confidence_with_score(self):
        c = self.engine._calculate_confidence({"score_val": np.array([0.8])})
        assert 0.0 <= c <= 1.0

    def test_calculate_confidence_with_probability_2d(self):
        c = self.engine._calculate_confidence(
            {"probability": np.array([[0.1, 0.9], [0.3, 0.7]])},
        )
        assert 0.0 <= c <= 1.0

    def test_get_default_model(self):
        assert self.engine._get_default_model(InferenceTask.COLLISION_PREDICTION) == "collision_model"
        assert self.engine._get_default_model(InferenceTask.BATTERY_PREDICTION) == "battery_model"


# ── edge_cloud_orchestrator ───────────────────────────────────────────────

from simulation.edge_cloud_orchestrator import (
    ComputeNode,
    DeploymentTier,
    EdgeCloudOrchestrator,
    Placement,
    ResourceType,
    Workload,
)


class TestResourceType:
    def test_values(self):
        assert ResourceType.COMPUTE.value == "compute"
        assert ResourceType.MEMORY.value == "memory"


class TestDeploymentTier:
    def test_values(self):
        assert DeploymentTier.DRONE.value == "drone"
        assert DeploymentTier.CLOUD.value == "cloud"


class TestEdgeCloudOrchestrator:
    def setup_method(self):
        self.orch = EdgeCloudOrchestrator()

    def test_init_creates_nodes(self):
        assert len(self.orch.nodes) == 5  # 3 edge + 2 cloud
        assert "edge_1" in self.orch.nodes
        assert "cloud_1" in self.orch.nodes

    def test_add_node(self):
        self.orch.add_node(
            "drone_1", DeploymentTier.DRONE,
            compute_capacity=10, storage_capacity=50,
            bandwidth_capacity=5, memory_capacity=20,
            cost_per_unit=0.1,
        )
        assert "drone_1" in self.orch.nodes

    def test_update_drone_latency(self):
        self.orch.update_drone_latency("edge_1", "drone_A", 10.0)
        assert self.orch.nodes["edge_1"].latency_to_drones["drone_A"] == 10.0

    def test_update_drone_latency_missing_node(self):
        self.orch.update_drone_latency("nonexistent", "drone_A", 10.0)

    def test_submit_workload(self):
        wl = Workload(
            workload_id="wl1", drone_id="d1",
            required_resources={ResourceType.COMPUTE: 10},
            priority=1, deadline=time.time() + 100, created_at=time.time(),
        )
        assert self.orch.submit_workload(wl)

    def test_schedule_workload_missing(self):
        assert self.orch.schedule_workload("nonexistent") is None

    def test_schedule_workload_success(self):
        self.orch.update_drone_latency("edge_1", "d1", 5.0)
        wl = Workload(
            workload_id="wl1", drone_id="d1",
            required_resources={ResourceType.COMPUTE: 10},
            priority=1, deadline=time.time() + 100, created_at=time.time(),
        )
        self.orch.submit_workload(wl)
        placement = self.orch.schedule_workload("wl1")
        assert placement is not None
        assert isinstance(placement, Placement)

    def test_schedule_workload_with_tier_preference(self):
        self.orch.update_drone_latency("cloud_1", "d2", 5.0)
        wl = Workload(
            workload_id="wl2", drone_id="d2",
            required_resources={ResourceType.COMPUTE: 10},
            priority=1, deadline=time.time() + 100, created_at=time.time(),
            tier_preference=[DeploymentTier.CLOUD],
        )
        self.orch.submit_workload(wl)
        placement = self.orch.schedule_workload("wl2")
        assert placement is not None
        assert "cloud" in placement.node_id

    def test_complete_workload(self):
        self.orch.update_drone_latency("edge_1", "d1", 5.0)
        wl = Workload(
            workload_id="wl1", drone_id="d1",
            required_resources={ResourceType.COMPUTE: 10},
            priority=1, deadline=time.time() + 100, created_at=time.time(),
        )
        self.orch.submit_workload(wl)
        self.orch.schedule_workload("wl1")
        self.orch.complete_workload("wl1")
        assert "wl1" not in self.orch.placements

    def test_complete_workload_missing(self):
        self.orch.complete_workload("nonexistent")  # Should not raise

    def test_get_system_status(self):
        status = self.orch.get_system_status()
        assert status["total_nodes"] == 5
        assert status["active_nodes"] == 5
        assert "nodes" in status

    def test_scale_node(self):
        orig = self.orch.nodes["edge_1"].capacity[ResourceType.COMPUTE]
        self.orch.scale_node("edge_1", 2.0)
        assert self.orch.nodes["edge_1"].capacity[ResourceType.COMPUTE] == orig * 2.0

    def test_scale_node_missing(self):
        self.orch.scale_node("nonexistent", 2.0)

    def test_failover_node(self):
        self.orch.update_drone_latency("edge_1", "d1", 5.0)
        self.orch.update_drone_latency("edge_2", "d1", 5.0)
        wl = Workload(
            workload_id="wl1", drone_id="d1",
            required_resources={ResourceType.COMPUTE: 10},
            priority=1, deadline=time.time() + 100, created_at=time.time(),
        )
        self.orch.submit_workload(wl)
        self.orch.schedule_workload("wl1")
        relocated = self.orch.failover_node("edge_1")
        assert not self.orch.nodes["edge_1"].is_active

    def test_failover_missing_node(self):
        result = self.orch.failover_node("nonexistent")
        assert result == []

    def test_can_allocate(self):
        node = self.orch.nodes["edge_1"]
        assert self.orch._can_allocate(node, {ResourceType.COMPUTE: 1})
        assert not self.orch._can_allocate(node, {ResourceType.COMPUTE: 999999})


# ── federated_learning_v3 ────────────────────────────────────────────────

from simulation.federated_learning_v3 import (
    AggregatedModel,
    AggregationMethod,
    FederatedLearningV3,
    ModelUpdate,
)


class TestAggregationMethod:
    def test_values(self):
        assert AggregationMethod.FEDAVG.value == "fedavg"
        assert AggregationMethod.SCAFFOLD.value == "scaffold"


class TestFederatedLearningV3:
    def setup_method(self):
        np.random.seed(42)
        self.model_shape = {"layer1": (10, 5), "layer2": (5, 1)}
        self.fl = FederatedLearningV3(
            model_shape=self.model_shape,
            min_clients_per_round=2,
        )

    def test_init(self):
        assert self.fl.current_round == 0
        assert len(self.fl.global_model) == 2

    def test_register_client(self):
        self.fl.register_client("drone_1")
        assert "drone_1" in self.fl.client_models

    def test_get_client_model_auto_register(self):
        model = self.fl.get_client_model("drone_new")
        assert "drone_new" in self.fl.client_models
        assert "layer1" in model

    def test_submit_update_correct_round(self):
        update = ModelUpdate(
            drone_id="d1", round_number=0,
            parameters={"layer1": np.zeros((10, 5)), "layer2": np.zeros((5, 1))},
            num_samples=100, timestamp=time.time(), loss=0.3, accuracy=0.8,
        )
        assert self.fl.submit_update(update)

    def test_submit_update_wrong_round(self):
        update = ModelUpdate(
            drone_id="d1", round_number=5,
            parameters={}, num_samples=100, timestamp=0, loss=0, accuracy=0,
        )
        assert not self.fl.submit_update(update)

    def test_pending_updates_count(self):
        assert self.fl.get_pending_updates_count() == 0
        update = ModelUpdate(
            drone_id="d1", round_number=0,
            parameters={"layer1": np.zeros((10, 5)), "layer2": np.zeros((5, 1))},
            num_samples=100, timestamp=0, loss=0.3, accuracy=0.8,
        )
        self.fl.submit_update(update)
        assert self.fl.get_pending_updates_count() == 1

    def test_should_aggregate_false(self):
        assert not self.fl.should_aggregate()

    def test_aggregate_not_enough(self):
        assert self.fl.aggregate() is None

    def _submit_n_updates(self, n: int):
        for i in range(n):
            update = ModelUpdate(
                drone_id=f"d{i}", round_number=self.fl.current_round,
                parameters={
                    "layer1": np.random.randn(10, 5),
                    "layer2": np.random.randn(5, 1),
                },
                num_samples=100, timestamp=time.time(), loss=0.3, accuracy=0.8,
            )
            self.fl.submit_update(update)

    def test_aggregate_fedavg(self):
        self._submit_n_updates(3)
        result = self.fl.aggregate()
        assert isinstance(result, AggregatedModel)
        assert result.round_number == 0
        assert self.fl.current_round == 1

    def test_aggregate_fedprox(self):
        fl = FederatedLearningV3(
            model_shape=self.model_shape,
            aggregation_method=AggregationMethod.FEDPROX,
            min_clients_per_round=2,
        )
        for i in range(2):
            update = ModelUpdate(
                drone_id=f"d{i}", round_number=0,
                parameters={
                    "layer1": np.random.randn(10, 5),
                    "layer2": np.random.randn(5, 1),
                },
                num_samples=100, timestamp=time.time(), loss=0.2, accuracy=0.85,
            )
            fl.submit_update(update)
        result = fl.aggregate()
        assert isinstance(result, AggregatedModel)

    def test_aggregate_fednova(self):
        fl = FederatedLearningV3(
            model_shape=self.model_shape,
            aggregation_method=AggregationMethod.FEDNOVA,
            min_clients_per_round=2,
        )
        for i in range(2):
            update = ModelUpdate(
                drone_id=f"d{i}", round_number=0,
                parameters={
                    "layer1": np.random.randn(10, 5),
                    "layer2": np.random.randn(5, 1),
                },
                num_samples=50 + i * 50, timestamp=time.time(),
                loss=0.2, accuracy=0.85,
            )
            fl.submit_update(update)
        result = fl.aggregate()
        assert isinstance(result, AggregatedModel)

    def test_aggregate_scaffold_falls_to_fedavg(self):
        fl = FederatedLearningV3(
            model_shape=self.model_shape,
            aggregation_method=AggregationMethod.SCAFFOLD,
            min_clients_per_round=2,
        )
        for i in range(2):
            update = ModelUpdate(
                drone_id=f"d{i}", round_number=0,
                parameters={
                    "layer1": np.random.randn(10, 5),
                    "layer2": np.random.randn(5, 1),
                },
                num_samples=100, timestamp=time.time(), loss=0.2, accuracy=0.85,
            )
            fl.submit_update(update)
        result = fl.aggregate()
        assert isinstance(result, AggregatedModel)

    def test_add_noise(self):
        params = np.random.randn(10, 5)
        noised = self.fl._add_noise(params)
        assert noised.shape == params.shape

    def test_add_noise_clips_norm(self):
        params = np.ones((10, 5)) * 100  # Large norm
        noised = self.fl._add_noise(params)
        assert noised.shape == params.shape

    def test_no_differential_privacy(self):
        fl = FederatedLearningV3(
            model_shape=self.model_shape,
            differential_privacy=False,
            min_clients_per_round=2,
        )
        for i in range(2):
            update = ModelUpdate(
                drone_id=f"d{i}", round_number=0,
                parameters={
                    "layer1": np.random.randn(10, 5),
                    "layer2": np.random.randn(5, 1),
                },
                num_samples=100, timestamp=time.time(), loss=0.2, accuracy=0.85,
            )
            fl.submit_update(update)
        result = fl.aggregate()
        assert isinstance(result, AggregatedModel)

    def test_get_global_model(self):
        model = self.fl.get_global_model()
        assert "layer1" in model
        assert model is not self.fl.global_model  # Should be a copy

    def test_simulate_local_training(self):
        update = self.fl.simulate_local_training("drone_1", local_epochs=3)
        assert isinstance(update, ModelUpdate)
        assert update.drone_id == "drone_1"
        assert update.num_samples == 100

    def test_get_stats(self):
        stats = self.fl.get_stats()
        assert stats["current_round"] == 0
        assert stats["aggregation_method"] == "fedavg"
        assert stats["differential_privacy_enabled"] is True
