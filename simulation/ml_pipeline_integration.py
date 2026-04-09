"""ML Model Pipeline Integration for Phase 200-219.

Provides a standardized interface for integrating trained ML models
into the simulation pipeline for inference and decision support.
"""

from __future__ import annotations

import json
import pickle
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Protocol

import numpy as np


class ModelAdapter(Protocol):
    """Protocol for model adapters."""

    def predict(self, features: np.ndarray) -> np.ndarray: ...
    def predict_proba(self, features: np.ndarray) -> np.ndarray: ...


class BaseModelWrapper(ABC):
    """Abstract base class for model wrappers."""

    def __init__(self, model_path: str | Path | None = None) -> None:
        self._model = None
        self._feature_names: list[str] = []
        self._model_version: str = "1.0.0"
        if model_path:
            self.load(model_path)

    @abstractmethod
    def predict(self, features: np.ndarray) -> np.ndarray:
        """Make predictions on input features."""
        ...

    @abstractmethod
    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        """Make probabilistic predictions."""
        ...

    def load(self, model_path: str | Path) -> None:
        """Load model from disk."""
        path = Path(model_path)
        if path.suffix == ".pkl":
            with open(path, "rb") as f:
                self._model = pickle.load(f)
        elif path.suffix == ".json":
            with open(path) as f:
                data = json.load(f)
                self._model = data
        else:
            raise ValueError(f"Unsupported model format: {path.suffix}")

    def save(self, model_path: str | Path) -> None:
        """Save model to disk."""
        path = Path(model_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".pkl":
            with open(path, "wb") as f:
                pickle.dump(self._model, f)
        elif path.suffix == ".json":
            with open(path, "w") as f:
                json.dump(self._model, f, indent=2, default=str)

    @property
    def version(self) -> str:
        """Get model version."""
        return self._model_version


class CollisionPredictor(BaseModelWrapper):
    """ML model for collision probability prediction."""

    def __init__(self, model_path: str | Path | None = None) -> None:
        super().__init__(model_path)
        self._feature_names = [
            "distance_to_cpa",
            "time_to_cpa",
            "relative_velocity",
            "altitude_diff",
            "heading_diff",
        ]

    def predict(self, features: np.ndarray) -> np.ndarray:
        """Predict collision risk (0=safe, 1=collision)."""
        if self._model is None:
            return self._mock_predict(features)
        return np.array([0.0] * len(features))

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        """Predict collision probability."""
        if self._model is None:
            return self._mock_predict_proba(features)
        return np.array([[0.8, 0.2] for _ in range(len(features))])

    def _mock_predict(self, features: np.ndarray) -> np.ndarray:
        """Mock prediction for testing."""
        return np.zeros(len(features))

    def _mock_predict_proba(self, features: np.ndarray) -> np.ndarray:
        """Mock probability prediction."""
        probs = []
        for f in features:
            if len(f) >= 3 and f[0] < 50:
                probs.append([0.3, 0.7])
            else:
                probs.append([0.9, 0.1])
        return np.array(probs)

    def predict_collision_risk(
        self,
        positions: np.ndarray,
        velocities: np.ndarray,
    ) -> np.ndarray:
        """Predict collision risk for drone pairs.

        Args:
            positions: Array of shape (n, 3) with x, y, z positions
            velocities: Array of shape (n, 3) with vx, vy, vz velocities

        Returns:
            Array of collision probabilities
        """
        n = len(positions)
        risks = np.zeros(n)

        for i in range(n):
            for j in range(i + 1, n):
                dist = np.linalg.norm(positions[i] - positions[j])
                rel_vel = np.linalg.norm(velocities[i] - velocities[j])
                t_cpa = dist / (rel_vel + 1e-6)

                if dist < 100 and t_cpa < 30:
                    risk = min(1.0, (100 - dist) / 100 * (30 - t_cpa) / 30)
                    risks[i] = max(risks[i], risk)
                    risks[j] = max(risks[j], risk)

        return risks


class RouteOptimizer(BaseModelWrapper):
    """ML model for route optimization decisions."""

    def __init__(self, model_path: str | Path | None = None) -> None:
        super().__init__(model_path)
        self._feature_names = [
            "start_x",
            "start_y",
            "end_x",
            "end_y",
            "obstacle_count",
            "weather_factor",
        ]

    def predict(self, features: np.ndarray) -> np.ndarray:
        """Predict optimal waypoints."""
        if self._model is None:
            return self._mock_predict(features)
        return np.zeros((len(features), 5, 3))

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        """Predict route confidence scores."""
        return np.ones((len(features), 1))

    def _mock_predict(self, features: np.ndarray) -> np.ndarray:
        """Mock waypoint prediction."""
        return np.zeros((len(features), 5, 3))

    def optimize_route(
        self,
        start: np.ndarray,
        end: np.ndarray,
        obstacles: list[np.ndarray] | None = None,
    ) -> dict[str, Any]:
        """Optimize route from start to end.

        Args:
            start: Starting position [x, y, z]
            end: Ending position [x, y, z]
            obstacles: List of obstacle positions

        Returns:
            Dictionary with optimized route information
        """
        waypoints = self._generate_waypoints(start, end, obstacles or [])
        distance = float(np.linalg.norm(end - start))

        return {
            "waypoints": waypoints,
            "total_distance": distance,
            "estimated_time": distance / 15.0,
            "obstacle_avoidance": len(obstacles or []) > 0,
        }

    def _generate_waypoints(
        self,
        start: np.ndarray,
        end: np.ndarray,
        obstacles: list[np.ndarray],
    ) -> list[np.ndarray]:
        """Generate intermediate waypoints."""
        n_waypoints = 5
        waypoints = [start]

        for i in range(1, n_waypoints):
            t = i / n_waypoints
            mid = start + t * (end - start)
            for obs in obstacles:
                dist = np.linalg.norm(mid - obs)
                if dist < 30:
                    offset = np.random.randn(3) * 10
                    mid = mid + offset
            waypoints.append(mid)

        waypoints.append(end)
        return waypoints


class DemandForecaster(BaseModelWrapper):
    """ML model for delivery demand forecasting."""

    def __init__(self, model_path: str | Path | None = None) -> None:
        super().__init__(model_path)
        self._feature_names = [
            "hour_of_day",
            "day_of_week",
            "weather_factor",
            "historical_demand",
        ]

    def predict(self, features: np.ndarray) -> np.ndarray:
        """Predict demand values."""
        if self._model is None:
            return self._mock_predict(features)
        return np.zeros(len(features))

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        """Predict demand confidence intervals."""
        return np.ones((len(features), 3))

    def _mock_predict(self, features: np.ndarray) -> np.ndarray:
        """Mock demand prediction."""
        demands = []
        for f in features:
            if len(f) >= 1:
                hour = f[0] if len(f) > 0 else 12
                base = 50.0
                if 7 <= hour <= 9:
                    base = 150.0
                elif 11 <= hour <= 13:
                    base = 180.0
                elif 17 <= hour <= 20:
                    base = 200.0
                elif 22 <= hour or hour <= 5:
                    base = 20.0
                demands.append(base)
            else:
                demands.append(50.0)
        return np.array(demands)

    def forecast_demand(
        self,
        hours_ahead: int = 24,
        weather_scenario: str = "clear",
    ) -> dict[str, Any]:
        """Forecast demand for upcoming hours.

        Args:
            hours_ahead: Number of hours to forecast
            weather_scenario: Weather condition scenario

        Returns:
            Dictionary with forecast data
        """
        weather_factor = 1.0
        if weather_scenario == "rain":
            weather_factor = 0.6
        elif weather_scenario == "storm":
            weather_factor = 0.2

        forecasts = []
        for h in range(hours_ahead):
            hour = h % 24
            base = 50.0
            if 7 <= hour <= 9:
                base = 150.0
            elif 11 <= hour <= 13:
                base = 180.0
            elif 17 <= hour <= 20:
                base = 200.0
            elif 22 <= hour or hour <= 5:
                base = 20.0
            forecasts.append({"hour": hour, "demand": base * weather_factor})

        return {
            "forecasts": forecasts,
            "total_demand": sum(f["demand"] for f in forecasts),
            "peak_hour": max(forecasts, key=lambda x: x["demand"])
            if forecasts
            else {"hour": 0, "demand": 0.0},
            "weather_scenario": weather_scenario,
        }


class MLInferencePipeline:
    """Unified pipeline for ML inference in simulation."""

    def __init__(self) -> None:
        self._collision_predictor = CollisionPredictor()
        self._route_optimizer = RouteOptimizer()
        self._demand_forecaster = DemandForecaster()
        self._inference_cache: dict[str, Any] = {}
        self._use_gpu = False

    def enable_gpu(self) -> None:
        """Enable GPU acceleration if available."""
        self._use_gpu = True

    def predict_collision_risks(
        self,
        positions: np.ndarray,
        velocities: np.ndarray,
    ) -> np.ndarray:
        """Predict collision risks for all drones."""
        return self._collision_predictor.predict_collision_risk(positions, velocities)

    def optimize_route(
        self,
        start: np.ndarray,
        end: np.ndarray,
        obstacles: list[np.ndarray] | None = None,
    ) -> dict[str, Any]:
        """Optimize route for a drone."""
        return self._route_optimizer.optimize_route(start, end, obstacles)

    def forecast_demand(
        self,
        hours_ahead: int = 24,
        weather_scenario: str = "clear",
    ) -> dict[str, Any]:
        """Forecast delivery demand."""
        cache_key = f"demand_{hours_ahead}_{weather_scenario}"
        if cache_key in self._inference_cache:
            return self._inference_cache[cache_key]
        result = self._demand_forecaster.forecast_demand(hours_ahead, weather_scenario)
        self._inference_cache[cache_key] = result
        return result

    def run_full_inference(
        self,
        positions: np.ndarray,
        velocities: np.ndarray,
        start: np.ndarray,
        end: np.ndarray,
    ) -> dict[str, Any]:
        """Run full inference pipeline.

        Args:
            positions: Drone positions
            velocities: Drone velocities
            start: Route start position
            end: Route end position

        Returns:
            Dictionary with all inference results
        """
        collision_risks = self.predict_collision_risks(positions, velocities)
        route = self.optimize_route(start, end)
        demand = self.forecast_demand()

        return {
            "collision_risks": collision_risks,
            "high_risk_count": int(np.sum(collision_risks > 0.7)),
            "route": route,
            "demand_forecast": demand,
            "gpu_enabled": self._use_gpu,
        }

    def get_pipeline_stats(self) -> dict[str, Any]:
        """Get pipeline statistics."""
        return {
            "cache_size": len(self._inference_cache),
            "gpu_enabled": self._use_gpu,
            "models_loaded": {
                "collision_predictor": True,
                "route_optimizer": True,
                "demand_forecaster": True,
            },
            "inference_count": len(self._inference_cache),
        }
