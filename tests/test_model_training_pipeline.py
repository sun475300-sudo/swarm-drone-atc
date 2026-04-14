"""Tests for Model Training Pipeline (Phase 220).

Tests for model training, data generation, and model evaluation.
"""

import json
import shutil
import tempfile
from pathlib import Path

import numpy as np
import pytest

from simulation.model_training_pipeline import (
    DataGenerator,
    ModelTrainer,
    ModelTrainingPipeline,
    TrainingConfig,
    TrainingResult,
)


class TestDataGenerator:
    """Test data generation."""

    def test_generate_collision_data_shape(self):
        """Test collision data generation shape."""
        generator = DataGenerator(seed=42)
        features, labels = generator.generate_collision_data(n_samples=1000)

        assert features.shape[0] == 1000
        assert features.shape[1] == 5
        assert labels.shape == (1000,)
        assert set(np.unique(labels)).issubset({0, 1})

    def test_generate_collision_data_balance(self):
        """Test collision data has proper balance."""
        generator = DataGenerator(seed=42)
        features, labels = generator.generate_collision_data(
            n_samples=1000, collision_rate=0.1
        )

        collision_count = np.sum(labels == 1)
        assert 50 <= collision_count <= 150

    def test_generate_route_data_shape(self):
        """Test route data generation shape."""
        generator = DataGenerator(seed=42)
        features, waypoints = generator.generate_route_data(n_samples=500)

        assert features.shape[0] == 500
        assert features.shape[1] == 8
        assert waypoints.shape[0] == 500
        assert waypoints.shape[1] == 18

    def test_generate_demand_data_shape(self):
        """Test demand data generation shape."""
        generator = DataGenerator(seed=42)
        features, demands = generator.generate_demand_data(n_samples=2000, n_days=30)

        assert features.shape[0] == 2000
        assert features.shape[1] == 4
        assert demands.shape == (2000,)

    def test_generate_demand_data_ranges(self):
        """Test demand values are in reasonable range."""
        generator = DataGenerator(seed=42)
        _, demands = generator.generate_demand_data(n_samples=1000)

        assert np.all(demands >= 0)
        assert np.all(demands <= 300)

    def test_safe_scenarios_far_distance(self):
        """Test safe scenarios have larger distances."""
        generator = DataGenerator(seed=42)
        features, labels = generator.generate_collision_data(n_samples=1000)

        safe_features = features[labels == 0]
        collision_features = features[labels == 1]

        assert np.mean(safe_features[:, 0]) > np.mean(collision_features[:, 0])

    def test_collision_scenarios_close_time(self):
        """Test collision scenarios have shorter time to CPA."""
        generator = DataGenerator(seed=42)
        features, labels = generator.generate_collision_data(n_samples=1000)

        safe_features = features[labels == 0]
        collision_features = features[labels == 1]

        assert np.mean(safe_features[:, 1]) > np.mean(collision_features[:, 1])

    def test_reproducibility_with_seed(self):
        """Test data generation is reproducible with same seed."""
        gen1 = DataGenerator(seed=12345)
        gen2 = DataGenerator(seed=12345)

        features1, labels1 = gen1.generate_collision_data(n_samples=100)
        features2, labels2 = gen2.generate_collision_data(n_samples=100)

        assert np.allclose(features1, features2)
        assert np.array_equal(labels1, labels2)


class TestTrainingConfig:
    """Test training configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TrainingConfig()

        assert config.model_type == "classifier"
        assert config.test_split == 0.2
        assert config.validation_split == 0.1
        assert config.random_seed == 42
        assert config.epochs == 100
        assert config.batch_size == 32

    def test_custom_config(self):
        """Test custom configuration."""
        config = TrainingConfig(
            model_type="regressor",
            test_split=0.3,
            epochs=50,
            learning_rate=0.01,
        )

        assert config.model_type == "regressor"
        assert config.test_split == 0.3
        assert config.epochs == 50
        assert config.learning_rate == 0.01


class TestModelTrainer:
    """Test model training."""

    def setup_method(self):
        """Setup test fixtures."""
        self.config = TrainingConfig(epochs=20, random_seed=42)
        self.trainer = ModelTrainer(self.config)
        self.generator = DataGenerator(seed=42)

    def test_train_collision_model(self):
        """Test collision model training."""
        features, labels = self.generator.generate_collision_data(n_samples=2000)
        result = self.trainer.train_collision_model(features, labels)

        assert isinstance(result, TrainingResult)
        assert result.model_type == "collision_predictor"
        assert 0 <= result.train_accuracy <= 1
        assert 0 <= result.test_accuracy <= 1
        assert result.training_time >= 0

    def test_train_collision_model_convergence(self):
        """Test collision model converges."""
        features, labels = self.generator.generate_collision_data(n_samples=2000)
        result = self.trainer.train_collision_model(features, labels)

        assert result.test_accuracy > 0.7

    def test_train_route_model(self):
        """Test route model training."""
        features, waypoints = self.generator.generate_route_data(n_samples=500)
        result = self.trainer.train_route_model(features, waypoints)

        assert isinstance(result, TrainingResult)
        assert result.model_type == "route_optimizer"
        assert result.test_loss >= 0

    def test_train_demand_model(self):
        """Test demand model training."""
        features, demands = self.generator.generate_demand_data(n_samples=2000)
        result = self.trainer.train_demand_model(features, demands)

        assert isinstance(result, TrainingResult)
        assert result.model_type == "demand_forecaster"
        assert "mae" in result.metrics

    def test_train_with_different_seeds(self):
        """Test training with different seeds produces different results."""
        features, labels = self.generator.generate_collision_data(n_samples=500)

        trainer1 = ModelTrainer(TrainingConfig(random_seed=1))
        trainer2 = ModelTrainer(TrainingConfig(random_seed=2))

        result1 = trainer1.train_collision_model(features, labels)
        result2 = trainer2.train_collision_model(features, labels)

        assert result1.training_time != result2.training_time

    def test_feature_importance(self):
        """Test feature importance extraction."""
        features, labels = self.generator.generate_collision_data(n_samples=500)
        result = self.trainer.train_collision_model(features, labels)

        assert result.feature_importance is not None
        assert len(result.feature_importance) == 5

    def test_confusion_matrix(self):
        """Test confusion matrix computation."""
        features, labels = self.generator.generate_collision_data(n_samples=1000)
        result = self.trainer.train_collision_model(features, labels)

        assert result.confusion_matrix is not None
        assert result.confusion_matrix.shape == (2, 2)


class TestTrainingResult:
    """Test training result."""

    def test_default_result(self):
        """Test default training result."""
        result = TrainingResult(
            model_type="test",
            training_time=10.0,
            train_accuracy=0.9,
            test_accuracy=0.85,
            train_loss=0.1,
            test_loss=0.15,
        )

        assert result.model_type == "test"
        assert result.timestamp is not None

    def test_result_with_metrics(self):
        """Test result with additional metrics."""
        result = TrainingResult(
            model_type="test",
            training_time=10.0,
            train_accuracy=0.9,
            test_accuracy=0.85,
            train_loss=0.1,
            test_loss=0.15,
            metrics={"mae": 0.05, "rmse": 0.08},
        )

        assert result.metrics["mae"] == 0.05
        assert result.metrics["rmse"] == 0.08


class TestModelTrainingPipeline:
    """Test end-to-end training pipeline."""

    def setup_method(self):
        """Setup test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.pipeline = ModelTrainingPipeline(output_dir=self.temp_dir)

    def teardown_method(self):
        """Cleanup test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_pipeline_initialization(self):
        """Test pipeline initialization."""
        assert self.pipeline._output_dir.exists()
        assert len(self.pipeline._trained_models) == 0

    def test_train_all_models(self):
        """Test training all models."""
        results = self.pipeline.train_all_models(
            n_collision_samples=500,
            n_route_samples=300,
            n_demand_samples=500,
        )

        assert len(results) == 3
        assert "collision" in results
        assert "route" in results
        assert "demand" in results

    def test_save_and_load_model(self):
        """Test model persistence."""
        self.pipeline.train_all_models(
            n_collision_samples=200,
            n_route_samples=100,
            n_demand_samples=200,
        )

        loaded = self.pipeline.load_model("collision_model")
        assert loaded is not None
        assert loaded.model_type == "collision_predictor"

    def test_pipeline_summary(self):
        """Test pipeline summary."""
        self.pipeline.train_all_models(
            n_collision_samples=200,
            n_route_samples=100,
            n_demand_samples=200,
        )

        summary = self.pipeline.get_pipeline_summary()
        assert "trained_models" in summary
        assert len(summary["trained_models"]) == 3

    def test_model_files_created(self):
        """Test model files are created."""
        self.pipeline.train_all_models(
            n_collision_samples=200,
            n_route_samples=100,
            n_demand_samples=200,
        )

        output_dir = Path(self.temp_dir)
        assert (output_dir / "collision_model.pkl").exists()
        assert (output_dir / "route_model.pkl").exists()
        assert (output_dir / "demand_model.pkl").exists()

    def test_result_json_files_created(self):
        """Test result JSON files are created."""
        self.pipeline.train_all_models(
            n_collision_samples=200,
            n_route_samples=100,
            n_demand_samples=200,
        )

        output_dir = Path(self.temp_dir)
        assert (output_dir / "collision_model_result.json").exists()

        with open(output_dir / "collision_model_result.json") as f:
            result = json.load(f)
            assert "test_accuracy" in result
            assert "timestamp" in result


class TestIntegration:
    """Integration tests."""

    def test_full_training_workflow(self):
        """Test complete training workflow."""
        temp_dir = tempfile.mkdtemp()

        try:
            pipeline = ModelTrainingPipeline(output_dir=temp_dir)

            results = pipeline.train_all_models(
                n_collision_samples=1000,
                n_route_samples=500,
                n_demand_samples=1000,
            )

            for name, result in results.items():
                assert result.test_accuracy > 0
                assert result.training_time >= 0
                assert result.timestamp is not None

            summary = pipeline.get_pipeline_summary()
            assert len(summary["trained_models"]) == 3

            for model_name in ["collision", "route", "demand"]:
                loaded = pipeline.load_model(f"{model_name}_model")
                assert loaded is not None
                assert (
                    loaded.model_type == f"{model_name}_forecaster"
                    or loaded.model_type == f"{model_name}_predictor"
                    or loaded.model_type == f"{model_name}_optimizer"
                )

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_multiple_training_runs(self):
        """Test multiple training runs produce consistent results."""
        temp_dir = tempfile.mkdtemp()

        try:
            results1 = ModelTrainingPipeline(output_dir=temp_dir).train_all_models(
                n_collision_samples=300,
                n_route_samples=200,
                n_demand_samples=300,
            )

            shutil.rmtree(temp_dir, ignore_errors=True)
            temp_dir = tempfile.mkdtemp()

            results2 = ModelTrainingPipeline(output_dir=temp_dir).train_all_models(
                n_collision_samples=300,
                n_route_samples=200,
                n_demand_samples=300,
            )

            assert len(results1) == len(results2)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
