"""Model Training Pipeline for Phase 220-239.

Provides training infrastructure for ML models using simulation-generated data.
Supports training, evaluation, hyperparameter tuning, and model persistence.
"""

from __future__ import annotations

import json
import pickle
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import numpy as np


@dataclass
class TrainingConfig:
    """Configuration for model training."""

    model_type: str = "classifier"
    test_split: float = 0.2
    validation_split: float = 0.1
    random_seed: int = 42
    epochs: int = 100
    batch_size: int = 32
    learning_rate: float = 0.001
    early_stopping_patience: int = 10
    use_cross_validation: bool = True
    n_folds: int = 5
    verbose: bool = True


@dataclass
class TrainingResult:
    """Results from model training."""

    model_type: str
    training_time: float
    train_accuracy: float
    test_accuracy: float
    train_loss: float
    test_loss: float
    confusion_matrix: np.ndarray | None = None
    feature_importance: dict[str, float] | None = None
    hyperparameters: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
    training_history: list[dict[str, float]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class DataGenerator:
    """Generate training data from simulation scenarios."""

    def __init__(self, seed: int = 42) -> None:
        self._rng = np.random.default_rng(seed)
        self._data_cache: list[dict[str, np.ndarray]] = []

    def generate_collision_data(
        self,
        n_samples: int = 10000,
        collision_rate: float = 0.05,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Generate collision prediction training data.

        Args:
            n_samples: Number of samples to generate
            collision_rate: Proportion of collision samples

        Returns:
            Tuple of (features, labels)
        """
        n_collision = int(n_samples * collision_rate)
        n_safe = n_samples - n_collision

        safe_features = self._generate_safe_scenarios(n_safe)
        collision_features = self._generate_collision_scenarios(n_collision)

        features = np.vstack([safe_features, collision_features])
        labels = np.array([0] * n_safe + [1] * n_collision)

        indices = self._rng.permutation(len(labels))
        return features[indices], labels[indices]

    def _generate_safe_scenarios(self, n: int) -> np.ndarray:
        """Generate safe (non-collision) scenarios."""
        features = []
        for _ in range(n):
            dist = self._rng.uniform(100, 500)
            t_cpa = self._rng.uniform(30, 120)
            rel_vel = self._rng.uniform(0, 10)
            alt_diff = self._rng.uniform(0, 100)
            heading_diff = self._rng.uniform(0, 180)
            features.append([dist, t_cpa, rel_vel, alt_diff, heading_diff])
        return np.array(features)

    def _generate_collision_scenarios(self, n: int) -> np.ndarray:
        """Generate collision scenarios."""
        features = []
        for _ in range(n):
            dist = self._rng.uniform(10, 80)
            t_cpa = self._rng.uniform(5, 25)
            rel_vel = self._rng.uniform(5, 25)
            alt_diff = self._rng.uniform(0, 30)
            heading_diff = self._rng.uniform(0, 45)
            features.append([dist, t_cpa, rel_vel, alt_diff, heading_diff])
        return np.array(features)

    def generate_route_data(
        self,
        n_samples: int = 5000,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Generate route optimization training data.

        Args:
            n_samples: Number of samples to generate

        Returns:
            Tuple of (features, waypoints)
        """
        features = []
        waypoints = []

        for _ in range(n_samples):
            start = self._rng.uniform(-500, 500, 3)
            end = self._rng.uniform(-500, 500, 3)
            n_obstacles = self._rng.integers(0, 10)
            obstacles = [self._rng.uniform(-300, 300, 3) for _ in range(n_obstacles)]
            weather = self._rng.uniform(0.5, 1.0)

            feat = np.concatenate([start, end, [n_obstacles, weather]])
            features.append(feat)

            route = self._generate_reference_route(start, end, obstacles)
            waypoints.append(route)

        return np.array(features), np.array(waypoints)

    def _generate_reference_route(
        self,
        start: np.ndarray,
        end: np.ndarray,
        obstacles: list[np.ndarray],
    ) -> np.ndarray:
        """Generate reference route (optimal waypoints)."""
        n_waypoints = 5
        waypoints = [start]
        direction = end - start

        for i in range(1, n_waypoints):
            t = i / n_waypoints
            waypoint = start + t * direction

            for obs in obstacles:
                if np.linalg.norm(waypoint - obs) < 50:
                    avoid_dir = waypoint - obs
                    waypoint = waypoint + 20 * avoid_dir / (
                        np.linalg.norm(avoid_dir) + 1e-6
                    )

            waypoints.append(waypoint)

        waypoints.append(end)
        return np.array(waypoints).flatten()

    def generate_demand_data(
        self,
        n_samples: int = 10000,
        n_days: int = 365,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Generate demand forecasting training data.

        Args:
            n_samples: Number of samples to generate
            n_days: Number of days of historical data

        Returns:
            Tuple of (features, demands)
        """
        features = []
        demands = []

        for day in range(n_days):
            for hour in range(24):
                dow = day % 7
                base_demand = self._get_base_demand(hour, dow)
                weather_factor = self._rng.uniform(0.3, 1.0)
                historical = base_demand * weather_factor + self._rng.normal(0, 10)

                features.append([hour, dow, weather_factor, historical])
                demands.append(base_demand * weather_factor)

        indices = self._rng.choice(len(features), n_samples, replace=True)
        return np.array([features[i] for i in indices]), np.array(
            [demands[i] for i in indices]
        )

    def _get_base_demand(self, hour: int, dow: int) -> float:
        """Get base demand for hour and day of week."""
        hourly = [
            20,
            15,
            10,
            10,
            15,
            30,
            80,
            150,
            180,
            120,
            100,
            150,
            180,
            140,
            100,
            90,
            120,
            200,
            220,
            180,
            120,
            80,
            50,
            30,
        ]
        weekend_factor = 0.8 if dow >= 5 else 1.0
        return hourly[hour] * weekend_factor


class ModelTrainer:
    """Train ML models on simulation data."""

    def __init__(self, config: TrainingConfig | None = None) -> None:
        self._config = config or TrainingConfig()
        self._rng = np.random.default_rng(self._config.random_seed)
        self._models: dict[str, Any] = {}

    def train_collision_model(
        self,
        features: np.ndarray,
        labels: np.ndarray,
    ) -> TrainingResult:
        """Train collision prediction model.

        Args:
            features: Input features
            labels: Collision labels (0=safe, 1=collision)

        Returns:
            Training result with metrics
        """
        start_time = datetime.now()

        X_train, X_test, y_train, y_test = self._split_data(
            features, labels, self._config.test_split
        )

        weights = self._compute_class_weights(y_train)
        model = self._initialize_model("collision")
        model.fit(X_train, y_train, sample_weight=weights)

        train_acc = model.score(X_train, y_train)
        test_acc = model.score(X_test, y_test)

        train_loss = self._compute_loss(model, X_train, y_train)
        test_loss = self._compute_loss(model, X_test, y_test)

        training_time = (datetime.now() - start_time).total_seconds()

        return TrainingResult(
            model_type="collision_predictor",
            training_time=training_time,
            train_accuracy=train_acc,
            test_accuracy=test_acc,
            train_loss=train_loss,
            test_loss=test_loss,
            confusion_matrix=self._compute_confusion_matrix(model, X_test, y_test),
            feature_importance=self._get_feature_importance(
                model,
                [
                    "distance_to_cpa",
                    "time_to_cpa",
                    "relative_velocity",
                    "altitude_diff",
                    "heading_diff",
                ],
            ),
            hyperparameters=self._get_model_params(model),
        )

    def train_route_model(
        self,
        features: np.ndarray,
        waypoints: np.ndarray,
    ) -> TrainingResult:
        """Train route optimization model.

        Args:
            features: Input features
            waypoints: Target waypoints

        Returns:
            Training result with metrics
        """
        start_time = datetime.now()

        X_train, X_test, y_train, y_test = self._split_data(
            features, waypoints, self._config.test_split
        )

        model = self._initialize_model("route")
        model.fit(X_train, y_train)

        train_mse = float(np.mean((model.predict(X_train) - y_train) ** 2))
        test_mse = float(np.mean((model.predict(X_test) - y_test) ** 2))

        training_time = (datetime.now() - start_time).total_seconds()

        return TrainingResult(
            model_type="route_optimizer",
            training_time=training_time,
            train_accuracy=1.0 / (1.0 + train_mse),
            test_accuracy=1.0 / (1.0 + test_mse),
            train_loss=train_mse,
            test_loss=test_mse,
            hyperparameters=self._get_model_params(model),
            metrics={"mse": test_mse, "rmse": float(np.sqrt(test_mse))},
        )

    def train_demand_model(
        self,
        features: np.ndarray,
        demands: np.ndarray,
    ) -> TrainingResult:
        """Train demand forecasting model.

        Args:
            features: Input features
            demands: Target demand values

        Returns:
            Training result with metrics
        """
        start_time = datetime.now()

        X_train, X_test, y_train, y_test = self._split_data(
            features, demands, self._config.test_split
        )

        model = self._initialize_model("demand")
        model.fit(X_train, y_train)

        train_mse = float(np.mean((model.predict(X_train) - y_train) ** 2))
        test_mse = float(np.mean((model.predict(X_test) - y_test) ** 2))

        train_mae = float(np.mean(np.abs(model.predict(X_train) - y_train)))
        test_mae = float(np.mean(np.abs(model.predict(X_test) - y_test)))

        training_time = (datetime.now() - start_time).total_seconds()

        return TrainingResult(
            model_type="demand_forecaster",
            training_time=training_time,
            train_accuracy=1.0 / (1.0 + train_mse),
            test_accuracy=1.0 / (1.0 + test_mse),
            train_loss=train_mse,
            test_loss=test_mse,
            hyperparameters=self._get_model_params(model),
            metrics={
                "mse": test_mse,
                "rmse": float(np.sqrt(test_mse)),
                "mae": test_mae,
            },
        )

    def _split_data(
        self,
        X: np.ndarray,
        y: np.ndarray,
        test_ratio: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Split data into train/test sets."""
        n = len(X)
        indices = self._rng.permutation(n)
        test_size = int(n * test_ratio)

        test_idx = indices[:test_size]
        train_idx = indices[test_size:]

        return X[train_idx], X[test_idx], y[train_idx], y[test_idx]

    def _compute_class_weights(self, labels: np.ndarray) -> np.ndarray:
        """Compute class weights for imbalanced data."""
        n_samples = len(labels)
        n_positive = np.sum(labels)
        n_negative = n_samples - n_positive

        weight_0 = n_samples / (2 * n_negative) if n_negative > 0 else 1.0
        weight_1 = n_samples / (2 * n_positive) if n_positive > 0 else 1.0

        return np.array([weight_0 if l == 0 else weight_1 for l in labels])

    def _initialize_model(self, model_type: str) -> Any:
        """Initialize model based on type."""
        if model_type == "collision":
            return _CollisionModel(self._config)
        elif model_type == "route":
            return _RouteModel(self._config)
        elif model_type == "demand":
            return _DemandModel(self._config)
        else:
            raise ValueError(f"Unknown model type: {model_type}")

    def _compute_loss(self, model: Any, X: np.ndarray, y: np.ndarray) -> float:
        """Compute loss for model."""
        predictions = model.predict(X)
        if len(y.shape) > 1:
            return float(np.mean((predictions - y) ** 2))
        else:
            return float(np.mean((predictions - y) ** 2))

    def _compute_confusion_matrix(
        self, model: Any, X: np.ndarray, y: np.ndarray
    ) -> np.ndarray:
        """Compute confusion matrix."""
        predictions = model.predict(X)
        tn = np.sum((predictions == 0) & (y == 0))
        fp = np.sum((predictions == 1) & (y == 0))
        fn = np.sum((predictions == 0) & (y == 1))
        tp = np.sum((predictions == 1) & (y == 1))
        return np.array([[tn, fp], [fn, tp]])

    def _get_feature_importance(
        self, model: Any, feature_names: list[str]
    ) -> dict[str, float]:
        """Get feature importance scores."""
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
            return dict(zip(feature_names, importances.tolist()))
        return {name: 1.0 / len(feature_names) for name in feature_names}

    def _get_model_params(self, model: Any) -> dict[str, Any]:
        """Get model parameters."""
        if hasattr(model, "get_params"):
            return model.get_params()
        return {}


class _CollisionModel:
    """Internal collision prediction model (simplified)."""

    def __init__(self, config: TrainingConfig) -> None:
        self._config = config
        self._rng = np.random.default_rng(config.random_seed)
        self._weights = None
        self._threshold = 0.5

    def fit(
        self, X: np.ndarray, y: np.ndarray, sample_weight: np.ndarray | None = None
    ) -> None:
        """Fit the model."""
        n_features = X.shape[1]
        self._weights = self._rng.normal(0, 0.1, n_features + 1)

        for epoch in range(self._config.epochs):
            logits = X @ self._weights[:-1] + self._weights[-1]
            probs = 1 / (1 + np.exp(-logits))

            if sample_weight is not None:
                error = sample_weight * (probs - y)
            else:
                error = probs - y

            gradient = X.T @ error / len(y)
            bias_grad = np.mean(error)

            lr = self._config.learning_rate
            self._weights[:-1] -= lr * gradient
            self._weights[-1] -= lr * bias_grad

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict class labels."""
        logits = X @ self._weights[:-1] + self._weights[-1]
        probs = 1 / (1 + np.exp(-logits))
        return (probs >= self._threshold).astype(int)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict probabilities."""
        logits = X @ self._weights[:-1] + self._weights[-1]
        probs = 1 / (1 + np.exp(-logits))
        return np.column_stack([1 - probs, probs])

    def score(self, X: np.ndarray, y: np.ndarray) -> float:
        """Compute accuracy."""
        predictions = self.predict(X)
        return float(np.mean(predictions == y))

    def get_params(self) -> dict[str, Any]:
        """Get model parameters."""
        return {
            "threshold": self._threshold,
            "learning_rate": self._config.learning_rate,
            "epochs": self._config.epochs,
        }


class _RouteModel:
    """Internal route optimization model (simplified linear)."""

    def __init__(self, config: TrainingConfig) -> None:
        self._config = config
        self._weights = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Fit the model."""
        n_features = X.shape[1]
        n_targets = y.shape[1] if len(y.shape) > 1 else 1

        self._weights = np.linalg.lstsq(X, y, rcond=None)[0]
        if len(self._weights.shape) == 1:
            self._weights = self._weights.reshape(-1, 1)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict waypoints."""
        return X @ self._weights

    def score(self, X: np.ndarray, y: np.ndarray) -> float:
        """Compute R2 score."""
        predictions = self.predict(X)
        ss_res = np.sum((y - predictions) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        return float(1 - ss_res / (ss_tot + 1e-10))

    def get_params(self) -> dict[str, Any]:
        """Get model parameters."""
        return {"model_type": "linear_regression"}


class _DemandModel:
    """Internal demand forecasting model (simplified)."""

    def __init__(self, config: TrainingConfig) -> None:
        self._config = config
        self._weights = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Fit the model."""
        self._weights = np.linalg.lstsq(X, y, rcond=None)[0]

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict demand."""
        return X @ self._weights

    def score(self, X: np.ndarray, y: np.ndarray) -> float:
        """Compute R2 score."""
        predictions = self.predict(X)
        ss_res = np.sum((y - predictions) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        return float(1 - ss_res / (ss_tot + 1e-10))

    def get_params(self) -> dict[str, Any]:
        """Get model parameters."""
        return {"model_type": "demand_forecaster"}


class ModelTrainingPipeline:
    """End-to-end model training pipeline."""

    def __init__(self, output_dir: str | Path = "models") -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._data_generator = DataGenerator()
        self._trainer = ModelTrainer()
        self._trained_models: dict[str, TrainingResult] = {}

    def train_all_models(
        self,
        n_collision_samples: int = 10000,
        n_route_samples: int = 5000,
        n_demand_samples: int = 10000,
    ) -> dict[str, TrainingResult]:
        """Train all models.

        Args:
            n_collision_samples: Number of collision samples
            n_route_samples: Number of route samples
            n_demand_samples: Number of demand samples

        Returns:
            Dictionary of training results
        """
        print("Generating training data...")
        collision_features, collision_labels = (
            self._data_generator.generate_collision_data(n_collision_samples)
        )
        route_features, waypoints = self._data_generator.generate_route_data(
            n_route_samples
        )
        demand_features, demands = self._data_generator.generate_demand_data(
            n_demand_samples
        )

        print("Training collision prediction model...")
        collision_result = self._trainer.train_collision_model(
            collision_features, collision_labels
        )
        self._trained_models["collision"] = collision_result
        self._save_model(collision_result, "collision_model")

        print("Training route optimization model...")
        route_result = self._trainer.train_route_model(route_features, waypoints)
        self._trained_models["route"] = route_result
        self._save_model(route_result, "route_model")

        print("Training demand forecasting model...")
        demand_result = self._trainer.train_demand_model(demand_features, demands)
        self._trained_models["demand"] = demand_result
        self._save_model(demand_result, "demand_model")

        return self._trained_models

    def _save_model(self, result: TrainingResult, name: str) -> None:
        """Save trained model and results."""
        model_path = self._output_dir / f"{name}.pkl"
        result_path = self._output_dir / f"{name}_result.json"

        with open(model_path, "wb") as f:
            pickle.dump(result, f)

        result_dict = {
            "model_type": result.model_type,
            "training_time": result.training_time,
            "train_accuracy": result.train_accuracy,
            "test_accuracy": result.test_accuracy,
            "train_loss": result.train_loss,
            "test_loss": result.test_loss,
            "metrics": result.metrics,
            "feature_importance": result.feature_importance,
            "timestamp": result.timestamp,
        }
        with open(result_path, "w") as f:
            json.dump(result_dict, f, indent=2)

    def load_model(self, name: str) -> TrainingResult | None:
        """Load trained model."""
        model_path = self._output_dir / f"{name}.pkl"
        if not model_path.exists():
            return None

        with open(model_path, "rb") as f:
            return pickle.load(f)

    def get_pipeline_summary(self) -> dict[str, Any]:
        """Get training pipeline summary."""
        return {
            "output_directory": str(self._output_dir),
            "trained_models": list(self._trained_models.keys()),
            "results": {
                name: {
                    "test_accuracy": result.test_accuracy,
                    "test_loss": result.test_loss,
                    "training_time": result.training_time,
                }
                for name, result in self._trained_models.items()
            },
        }


def train_models_cli() -> None:
    """Command-line interface for model training."""
    import argparse

    parser = argparse.ArgumentParser(description="Train ML models for SDACS")
    parser.add_argument(
        "--collision-samples",
        type=int,
        default=10000,
        help="Number of collision samples",
    )
    parser.add_argument(
        "--route-samples", type=int, default=5000, help="Number of route samples"
    )
    parser.add_argument(
        "--demand-samples", type=int, default=10000, help="Number of demand samples"
    )
    parser.add_argument(
        "--output-dir", type=str, default="models", help="Output directory"
    )
    parser.add_argument("--epochs", type=int, default=100, help="Training epochs")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")

    args = parser.parse_args()

    config = TrainingConfig(
        epochs=args.epochs,
        batch_size=args.batch_size,
    )

    pipeline = ModelTrainingPipeline(output_dir=args.output_dir)
    results = pipeline.train_all_models(
        n_collision_samples=args.collision_samples,
        n_route_samples=args.route_samples,
        n_demand_samples=args.demand_samples,
    )

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    for name, result in results.items():
        print(f"\n{name.upper()}:")
        print(f"  Test Accuracy: {result.test_accuracy:.4f}")
        print(f"  Test Loss: {result.test_loss:.4f}")
        print(f"  Training Time: {result.training_time:.2f}s")
    print(f"\nModels saved to: {args.output_dir}/")


if __name__ == "__main__":
    train_models_cli()
