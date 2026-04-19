"""새 모듈 테스트: digital_twin, heatmap_generator, trajectory_recorder, structured_logger, multi_gpu."""

import json
import logging
from unittest import mock

import numpy as np
import pytest

from simulation.digital_twin import DigitalTwin, TelemetrySnapshot
import simulation.heatmap_generator as _heatmap_mod
from simulation.heatmap_generator import generate_risk_heatmap
from simulation.trajectory_recorder import TrajectoryRecorder
from simulation.structured_logger import get_logger
from simulation.apf_engine.multi_gpu import get_gpu_count, multi_gpu_batch_compute


# ── DigitalTwin ──────────────────────────────────────────────


class TestDigitalTwin:
    def test_update_and_get_state(self) -> None:
        # Arrange
        twin = DigitalTwin()
        # Act
        twin.update_from_telemetry("d1", [1, 2, 3], [0, 0, 0])
        state = twin.get_state("d1")
        # Assert
        assert state is not None
        assert state.drone_id == "d1"
        np.testing.assert_array_equal(state.position, [1, 2, 3])

    def test_get_state_missing_returns_none(self) -> None:
        twin = DigitalTwin()
        assert twin.get_state("nonexistent") is None

    def test_get_prediction_linear(self) -> None:
        # Arrange
        twin = DigitalTwin()
        twin.update_from_telemetry("d1", [0, 0, 0], [1, 0, 0])
        # Act
        pred = twin.get_prediction("d1", lookahead_s=10.0)
        # Assert
        assert pred["predicted_position"] == [10.0, 0.0, 0.0]
        assert pred["speed_ms"] == pytest.approx(1.0)

    def test_get_prediction_missing_drone(self) -> None:
        twin = DigitalTwin()
        result = twin.get_prediction("missing")
        assert "error" in result

    def test_get_divergence(self) -> None:
        # Arrange
        twin = DigitalTwin()
        twin.update_from_telemetry("d1", [3, 0, 0], [0, 0, 0])
        # Act
        div = twin.get_divergence("d1", np.array([0, 0, 0]))
        # Assert
        assert div == pytest.approx(3.0)

    def test_get_divergence_missing_returns_inf(self) -> None:
        twin = DigitalTwin()
        assert twin.get_divergence("x", np.array([0, 0, 0])) == float("inf")


# ── Heatmap ──────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _force_numpy_heatmap(monkeypatch):
    """Force numpy fallback to avoid CUDA histogramdd issues."""
    monkeypatch.setattr(_heatmap_mod, "_HAS_TORCH", False)


class TestHeatmap:
    def test_empty_input(self) -> None:
        result = generate_risk_heatmap([], grid_size=10)
        assert result["max_density"] == 0.0
        assert result["grid"].shape == (10, 10)

    def test_single_drone(self) -> None:
        states = [{"position": [0, 0, 0]}]
        result = generate_risk_heatmap(states, grid_size=10)
        assert result["max_density"] >= 1.0
        assert result["grid"].sum() == 1.0

    def test_multiple_drones_same_cell(self) -> None:
        states = [{"position": [0, 0, 0]}] * 5
        result = generate_risk_heatmap(states, grid_size=10)
        assert result["max_density"] == pytest.approx(5.0)

    def test_bounds_in_result(self) -> None:
        result = generate_risk_heatmap([], bounds=(-100, 100))
        assert result["bounds"]["min"] == -100.0
        assert result["bounds"]["max"] == 100.0


# ── TrajectoryRecorder ───────────────────────────────────────


class TestTrajectoryRecorder:
    def test_record_and_get(self) -> None:
        rec = TrajectoryRecorder()
        rec.record(0.0, "d1", [1, 2, 3])
        rec.record(0.1, "d1", [4, 5, 6])
        traj = rec.get_trajectory("d1")
        assert len(traj) == 2
        assert traj[0] == (0.0, (1.0, 2.0, 3.0))

    def test_get_trajectory_missing(self) -> None:
        rec = TrajectoryRecorder()
        assert rec.get_trajectory("nope") == []

    def test_drone_ids(self) -> None:
        rec = TrajectoryRecorder()
        rec.record(0, "a", [0, 0, 0])
        rec.record(0, "b", [0, 0, 0])
        assert set(rec.drone_ids) == {"a", "b"}

    def test_export_json(self, tmp_path) -> None:
        # Arrange
        rec = TrajectoryRecorder()
        rec.record(1.0, "d1", [10, 20, 30])
        filepath = str(tmp_path / "traj.json")
        # Act
        rec.export_json(filepath)
        # Assert
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        assert "d1" in data
        assert data["d1"][0]["t"] == 1.0
        assert data["d1"][0]["position"] == [10.0, 20.0, 30.0]

    def test_max_snapshots(self) -> None:
        rec = TrajectoryRecorder(max_snapshots=3)
        for i in range(5):
            rec.record(float(i), "d1", [i, 0, 0])
        assert len(rec.get_trajectory("d1")) == 3


# ── StructuredLogger ─────────────────────────────────────────


class TestStructuredLogger:
    def test_returns_logger(self) -> None:
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

    def test_json_format(self, capfd) -> None:
        logger = get_logger("json_test_fmt", level=logging.WARNING)
        logger.warning("hello")
        captured = capfd.readouterr()
        parsed = json.loads(captured.err)
        assert parsed["level"] == "WARNING"
        assert parsed["message"] == "hello"
        assert "timestamp" in parsed

    def test_idempotent_handlers(self) -> None:
        logger1 = get_logger("idem_test")
        logger2 = get_logger("idem_test")
        assert logger1 is logger2
        assert len(logger1.handlers) == 1


# ── MultiGPU ─────────────────────────────────────────────────


class TestMultiGPU:
    def test_gpu_count_non_negative(self) -> None:
        assert get_gpu_count() >= 0

    def test_empty_input_returns_empty(self) -> None:
        result = multi_gpu_batch_compute([], {})
        assert result == {}

    def test_basic_computation(self) -> None:
        torch = pytest.importorskip("torch")
        from simulation.apf_engine.apf import APFState
        states = [
            APFState(position=np.array([0, 0, 0], dtype=float),
                     velocity=np.array([0, 0, 0], dtype=float),
                     drone_id="d1"),
            APFState(position=np.array([5000, 5000, 0], dtype=float),
                     velocity=np.array([0, 0, 0], dtype=float),
                     drone_id="d2"),
        ]
        goals = {
            "d1": np.array([10, 0, 0], dtype=float),
            "d2": np.array([5000, 5000, 0], dtype=float),
        }
        # Force CPU to avoid CUDA compatibility issues
        with mock.patch.object(torch.cuda, "is_available", return_value=False):
            result = multi_gpu_batch_compute(states, goals)
        assert "d1" in result
        assert result["d1"].shape == (3,)
        # force should point toward goal (positive x)
        assert result["d1"][0] > 0
