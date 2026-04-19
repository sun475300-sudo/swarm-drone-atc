"""
Phase 407: AutoML Pipeline for Hyperparameter Optimization
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import defaultdict


class ModelType(Enum):
    LIGHTGBM = "lightgbm"
    XGBOOST = "xgboost"
    RANDOM_FOREST = "random_forest"
    NEURAL_NETWORK = "neural_network"


class SearchStrategy(Enum):
    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    BAYESIAN = "bayesian"
    GENETIC = "genetic"


@dataclass
class HyperparameterConfig:
    learning_rate: float = 0.1
    max_depth: int = 6
    n_estimators: int = 100
    min_child_weight: int = 1
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    reg_alpha: float = 0.0
    reg_lambda: float = 1.0


@dataclass
class TrialResult:
    trial_id: str
    config: HyperparameterConfig
    score: float
    training_time: float
    timestamp: float


class AutoMLPipeline:
    def __init__(
        self,
        model_type: ModelType = ModelType.LIGHTGBM,
        search_strategy: SearchStrategy = SearchStrategy.BAYESIAN,
        max_trials: int = 50,
        timeout_per_trial: float = 60.0,
        n_jobs: int = 4,
    ):
        self.model_type = model_type
        self.search_strategy = search_strategy
        self.max_trials = max_trials
        self.timeout_per_trial = timeout_per_trial
        self.n_jobs = n_jobs

        self.trials: List[TrialResult] = []
        self.best_trial: Optional[TrialResult] = None
        self.search_space = self._define_search_space()

        self.history_scores: List[float] = []

        self._initialize_search()

    def _define_search_space(self) -> Dict[str, List[Any]]:
        return {
            "learning_rate": [0.01, 0.05, 0.1, 0.2],
            "max_depth": [3, 4, 5, 6, 8, 10],
            "n_estimators": [50, 100, 200, 300],
            "min_child_weight": [1, 3, 5, 7],
            "subsample": [0.6, 0.7, 0.8, 0.9, 1.0],
            "colsample_bytree": [0.6, 0.7, 0.8, 0.9, 1.0],
            "reg_alpha": [0.0, 0.1, 0.5, 1.0],
            "reg_lambda": [0.1, 0.5, 1.0, 2.0],
        }

    def _initialize_search(self):
        if self.search_strategy == SearchStrategy.BAYESIAN:
            self.gaussian_process = self._init_gaussian_process()

    def _init_gaussian_process(self):
        return {
            "mean": 0.5,
            "std": 0.3,
            "observations": [],
        }

    def _sample_config(self) -> HyperparameterConfig:
        if self.search_strategy == SearchStrategy.RANDOM_SEARCH:
            return self._random_search()
        elif self.search_strategy == SearchStrategy.GRID_SEARCH:
            return self._grid_search()
        elif self.search_strategy == SearchStrategy.BAYESIAN:
            return self._bayesian_search()
        else:
            return self._random_search()

    def _random_search(self) -> HyperparameterConfig:
        config = HyperparameterConfig()

        config.learning_rate = np.random.choice(self.search_space["learning_rate"])
        config.max_depth = np.random.choice(self.search_space["max_depth"])
        config.n_estimators = np.random.choice(self.search_space["n_estimators"])
        config.min_child_weight = np.random.choice(
            self.search_space["min_child_weight"]
        )
        config.subsample = np.random.choice(self.search_space["subsample"])
        config.colsample_bytree = np.random.choice(
            self.search_space["colsample_bytree"]
        )
        config.reg_alpha = np.random.choice(self.search_space["reg_alpha"])
        config.reg_lambda = np.random.choice(self.search_space["reg_lambda"])

        return config

    def _grid_search(self) -> HyperparameterConfig:
        trial_idx = len(self.trials)

        grid_sizes = [len(v) for v in self.search_space.values()]
        total_configs = np.prod(grid_sizes)

        if trial_idx >= total_configs:
            return self._random_search()

        config = HyperparameterConfig()

        keys = list(self.search_space.keys())
        for i, key in enumerate(keys):
            dim_size = grid_sizes[i]
            idx = int((trial_idx // np.prod(grid_sizes[i + 1 :])) % dim_size)
            value = self.search_space[key][idx]
            setattr(config, key, value)

        return config

    def _bayesian_search(self) -> HyperparameterConfig:
        if len(self.trials) < 5:
            return self._random_search()

        scores = np.array([t.score for t in self.trials[-10:]])
        best_idx = np.argmax(scores)
        best_config = self.trials[-10:][best_idx].config

        config = HyperparameterConfig()

        noise = np.random.randn() * 0.1
        config.learning_rate = max(
            0.001, min(0.5, best_config.learning_rate + noise * 0.05)
        )

        noise = np.random.randint(-2, 3)
        config.max_depth = max(1, min(15, best_config.max_depth + noise))

        noise = np.random.randint(-50, 51)
        config.n_estimators = max(10, min(500, best_config.n_estimators + noise))

        noise = np.random.randn() * 0.1
        config.subsample = max(0.5, min(1.0, best_config.subsample + noise))
        config.colsample_bytree = max(
            0.5, min(1.0, best_config.colsample_bytree + noise)
        )

        config.min_child_weight = best_config.min_child_weight
        config.reg_alpha = best_config.reg_alpha
        config.reg_lambda = best_config.reg_lambda

        return config

    def _train_and_evaluate(
        self, config: HyperparameterConfig, X: np.ndarray, y: np.ndarray
    ) -> float:
        start_time = time.time()

        if self.model_type == ModelType.LIGHTGBM:
            score = self._train_lightgbm(config, X, y)
        elif self.model_type == ModelType.XGBOOST:
            score = self._train_xgboost(config, X, y)
        elif self.model_type == ModelType.RANDOM_FOREST:
            score = self._train_random_forest(config, X, y)
        else:
            score = self._train_neural_network(config, X, y)

        training_time = time.time() - start_time

        return score

    def _train_lightgbm(
        self, config: HyperparameterConfig, X: np.ndarray, y: np.ndarray
    ) -> float:
        n_samples = X.shape[0]

        if len(y.shape) == 1:
            y_pred = np.zeros(n_samples)
            for i in range(config.n_estimators):
                residual = y - y_pred
                y_pred += config.learning_rate * residual * np.random.randn(n_samples)

        train_score = 1.0 / (1.0 + np.mean(np.abs(y - y_pred)))

        return min(train_score * 100, 99.0)

    def _train_xgboost(
        self, config: HyperparameterConfig, X: np.ndarray, y: np.ndarray
    ) -> float:
        return self._train_lightgbm(config, X, y)

    def _train_random_forest(
        self, config: HyperparameterConfig, X: np.ndarray, y: np.ndarray
    ) -> float:
        n_samples = X.shape[0]

        predictions = np.zeros(n_samples)
        for _ in range(config.n_estimators // 10):
            indices = np.random.choice(n_samples, n_samples, replace=True)
            predictions += y[indices]
        predictions /= config.n_estimators // 10

        train_score = 1.0 / (1.0 + np.mean(np.abs(y - predictions)))

        return min(train_score * 100, 99.0)

    def _train_neural_network(
        self, config: HyperparameterConfig, X: np.ndarray, y: np.ndarray
    ) -> float:
        n_samples = X.shape[0]

        np.random.seed(int(time.time() * 1000) % 10000)

        hidden = min(config.max_depth * 16, 256)

        W1 = np.random.randn(X.shape[1], hidden) * 0.1
        b1 = np.zeros(hidden)
        W2 = np.random.randn(hidden, hidden) * 0.1
        b2 = np.zeros(hidden)
        W3 = np.random.randn(hidden, 1) * 0.1

        h1 = np.tanh(X @ W1 + b1)
        h2 = np.tanh(h1 @ W2 + b2)
        y_pred = h2 @ W3

        if len(y.shape) == 1:
            y = y.reshape(-1, 1)

        train_score = 1.0 / (1.0 + np.mean(np.abs(y - y_pred)))

        return min(train_score * 100, 99.0)

    def run(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
    ) -> HyperparameterConfig:
        X = X_train
        y = y_train

        for trial_idx in range(self.max_trials):
            config = self._sample_config()

            score = self._train_and_evaluate(config, X, y)

            trial_id = f"trial_{trial_idx}_{int(time.time())}"
            result = TrialResult(
                trial_id=trial_id,
                config=config,
                score=score,
                training_time=0.0,
                timestamp=time.time(),
            )

            self.trials.append(result)
            self.history_scores.append(score)

            if self.best_trial is None or score > self.best_trial.score:
                self.best_trial = result

            if (trial_idx + 1) % 10 == 0:
                print(
                    f"Trial {trial_idx + 1}/{self.max_trials} - Best Score: {self.best_trial.score:.4f}"
                )

        return self.best_trial.config

    def get_best_config(self) -> Optional[HyperparameterConfig]:
        return self.best_trial.config if self.best_trial else None

    def get_leaderboard(self, top_k: int = 10) -> List[TrialResult]:
        sorted_trials = sorted(self.trials, key=lambda t: t.score, reverse=True)
        return sorted_trials[:top_k]

    def get_optimization_history(self) -> Dict[str, List[float]]:
        return {
            "scores": self.history_scores,
            "best_scores": np.maximum.accumulate(self.history_scores).tolist(),
        }
