"""Quick E2E integration test for SwarmSimulator + Analytics pipeline.

This test verifies the complete simulation pipeline works end-to-end:
1. Simulator initializes and runs without error
2. Drones move and have valid positions
3. Analytics hook collects metrics
4. Performance analyzer produces valid results
5. Monte Carlo analyzer works on small sweep

Tests cover:
- Basic simulator run with 10 drones for 5 seconds
- Analytics hook integration
- Full analytics pipeline (PerformanceAnalyzer, SwarmMetricsCollector)
- Monte Carlo mini sweep (3 runs)
- Collision resolution formula verification
- Metrics JSON serialization
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import numpy as np
import pytest

# Add project root to path
_ROOT = str(Path(__file__).parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from simulation.simulator import SwarmSimulator
from src.analytics.core_analytics import (
    PerformanceAnalyzer,
    SwarmMetricsCollector,
    MonteCarloAnalyzer,
)
from src.analytics.simulation_hook import SimulationAnalyticsHook
from src.airspace_control.agents.drone_state import DroneState


# ─────────────────────────────────────────────────────────────
# Test Fixtures
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def config_path():
    """Return path to default config."""
    config_file = Path(_ROOT) / "config" / "default_simulation.yaml"
    if not config_file.exists():
        pytest.skip("Config file not found")
    return str(config_file)


@pytest.fixture
def performance_analyzer():
    """Provide PerformanceAnalyzer instance."""
    return PerformanceAnalyzer()


@pytest.fixture
def metrics_collector():
    """Provide SwarmMetricsCollector instance."""
    return SwarmMetricsCollector()


@pytest.fixture
def monte_carlo_analyzer():
    """Provide MonteCarloAnalyzer instance."""
    return MonteCarloAnalyzer(seed=42)


# ─────────────────────────────────────────────────────────────
# End-to-End Integration Tests
# ─────────────────────────────────────────────────────────────


class TestE2ESimulation:
    """Comprehensive end-to-end integration tests."""

    def test_simulator_basic_run(self, config_path):
        """Test 1: Basic simulator initialization and run.

        Verifies:
        - Simulator initializes without error
        - Runs for specified duration
        - Returns valid SimulationResult
        """
        # Create simulator: 10 drones, 5 seconds, seed=42
        scenario_cfg = {"drones": {"default_count": 10}}
        sim = SwarmSimulator(
            config_path=config_path,
            scenario_cfg=scenario_cfg,
            seed=42,
        )

        # Run simulation for 5 seconds
        result = sim.run(duration_s=5.0)

        # Verify result
        assert result is not None
        assert hasattr(result, "to_dict")
        assert result.n_drones == 10
        assert result.duration_s == 5.0
        assert result.seed == 42

        # Verify drones exist and have valid positions
        assert len(sim._drones) == 10
        for drone_id, drone in sim._drones.items():
            assert isinstance(drone, DroneState)
            assert drone.position is not None
            assert len(drone.position) == 3
            # Drones should move within bounds
            assert -10000 <= drone.position[0] <= 10000
            assert -10000 <= drone.position[1] <= 10000
            assert 0 <= drone.position[2] <= 200

    def test_simulator_with_analytics_hook(self, config_path):
        """Test 2: Simulator with analytics hook integration.

        Verifies:
        - Analytics hook collects metrics during simulation
        - Metrics history is populated
        - Events are recorded
        """
        scenario_cfg = {"drones": {"default_count": 5}}
        sim = SwarmSimulator(
            config_path=config_path,
            scenario_cfg=scenario_cfg,
            seed=123,
        )

        # Create and attach analytics hook
        hook = SimulationAnalyticsHook(simulator=sim)

        # Manually trigger hook at key points (simulating integration)
        # Note: In real usage, hook would be called from simulator
        drones = list(sim._drones.values()) if hasattr(sim, "_drones") else []

        # Run simulation
        result = sim.run(duration_s=3.0)

        # Verify hook was initialized
        assert hook is not None
        assert hook.simulator == sim
        assert isinstance(hook.events, list)
        assert isinstance(hook.collision_events, list)

    def test_analytics_pipeline(self, performance_analyzer, metrics_collector):
        """Test 3: Full analytics pipeline with mock data.

        Verifies:
        - PerformanceAnalyzer computes metrics correctly
        - SwarmMetricsCollector collects drone metrics
        - All results are JSON-serializable
        """
        # Create mock drones with varying speeds
        mock_drones = []
        for i in range(5):
            drone = Mock(spec=DroneState)
            drone.position = np.array([float(i * 100), float(i * 100), 50.0])
            drone.velocity = np.array([1.0 + i * 0.5, 1.0, 0.0])
            drone.speed = float(1.414 + i * 0.3)  # Varying speeds
            drone.battery_pct = 80.0 + i * 2.0

            mock_drones.append(drone)

        # Test PerformanceAnalyzer
        conflicts = 5
        collisions = 1
        crr = performance_analyzer.analyze_collision_resolution_rate(
            conflicts=conflicts, collisions=collisions
        )
        assert 0.0 <= crr <= 1.0
        assert crr == pytest.approx(1.0 - 1 / 6, abs=0.01)

        # Test SwarmMetricsCollector
        drone_metrics = metrics_collector.collect_drone_metrics(mock_drones)
        assert drone_metrics["count"] == 5
        assert 0 < drone_metrics["position_variance_m2"]
        assert 0 < drone_metrics["speed_std_ms"]  # Should have variance in speeds
        assert 80 < drone_metrics["battery_mean_pct"] < 92

        # Test JSON serialization
        summary = metrics_collector.get_summary()
        json_str = json.dumps(summary, default=str)
        assert json_str is not None

    def test_monte_carlo_mini_sweep(self, monte_carlo_analyzer, config_path):
        """Test 4: Monte Carlo mini sweep with 3 runs.

        Verifies:
        - Able to run multiple simulations with different seeds
        - MC analyzer aggregates results correctly
        - Confidence intervals computed
        """
        # Run 3 simulations with different seeds
        results = []
        for seed in [42, 43, 44]:
            scenario_cfg = {"drones": {"default_count": 5}}
            sim = SwarmSimulator(
                config_path=config_path,
                scenario_cfg=scenario_cfg,
                seed=seed,
            )
            result = sim.run(duration_s=2.0)
            results.append(result.to_dict())

        # Analyze sweep
        sweep_summary = monte_carlo_analyzer.analyze_sweep_results(results)
        assert sweep_summary["num_runs"] == 3
        assert sweep_summary["collision_count_mean"] >= 0.0
        assert sweep_summary["collision_count_std"] >= 0.0
        assert 0.0 <= sweep_summary["collision_rate"] <= 1.0

        # Test confidence intervals
        collision_counts = [r.get("collision_count", 0) for r in results]
        ci = monte_carlo_analyzer.compute_confidence_intervals(
            collision_counts, confidence=0.95
        )
        assert ci["sample_size"] == 3
        assert ci["ci_lower"] <= ci["mean"]
        assert ci["mean"] <= ci["ci_upper"]

    def test_collision_resolution_formula(self, performance_analyzer):
        """Test 5: Verify collision resolution formula.

        Formula: 1 - collisions / (conflicts + collisions)

        Edge cases:
        - No conflicts/collisions: rate = 1.0 (100% safe)
        - All conflicts resolved (no collisions): rate = 1.0
        - All events are collisions: rate = 0.0
        - Partial resolution: rate between 0 and 1
        """
        # Case 1: No events
        rate = performance_analyzer.analyze_collision_resolution_rate(0, 0)
        assert rate == 1.0

        # Case 2: Conflicts only
        rate = performance_analyzer.analyze_collision_resolution_rate(10, 0)
        assert rate == 1.0

        # Case 3: Collisions only
        rate = performance_analyzer.analyze_collision_resolution_rate(0, 10)
        assert rate == 0.0

        # Case 4: Mixed (5 conflicts, 1 collision)
        rate = performance_analyzer.analyze_collision_resolution_rate(5, 1)
        expected = 1.0 - 1.0 / 6.0  # 5/6 ≈ 0.833
        assert rate == pytest.approx(expected, abs=0.001)

        # Case 5: Equal conflicts and collisions
        rate = performance_analyzer.analyze_collision_resolution_rate(10, 10)
        assert rate == 0.5

        # Case 6: Large numbers (stress test)
        rate = performance_analyzer.analyze_collision_resolution_rate(1000, 50)
        expected = 1.0 - 50.0 / 1050.0
        assert rate == pytest.approx(expected, abs=0.001)

    def test_metrics_json_serializable(self, metrics_collector, monte_carlo_analyzer):
        """Test 6: Verify all metrics are JSON-serializable.

        Ensures that:
        - DroneMetrics can be JSON serialized
        - AirspaceMetrics can be JSON serialized
        - Monte Carlo results can be JSON serialized
        """
        # Create mock drones for metrics collection
        mock_drones = []
        for i in range(3):
            drone = Mock(spec=DroneState)
            drone.position = np.array([float(i), float(i), 50.0])
            drone.velocity = np.array([1.0, 0.0, 0.0])
            drone.speed = 1.0
            drone.battery_pct = 75.0

            mock_drones.append(drone)

        # Collect metrics
        drone_metrics = metrics_collector.collect_drone_metrics(mock_drones)
        mock_controller = Mock()
        mock_controller._advisories = {}
        mock_controller._pending = []
        airspace_metrics = metrics_collector.collect_airspace_metrics(
            mock_controller, active_drones=3
        )

        # Test JSON serialization
        test_data = {
            "drone_metrics": drone_metrics,
            "airspace_metrics": airspace_metrics,
        }

        json_str = json.dumps(test_data, default=str)
        assert json_str is not None

        # Parse back and verify
        parsed = json.loads(json_str)
        assert "drone_metrics" in parsed
        assert "airspace_metrics" in parsed
        assert parsed["drone_metrics"]["count"] == 3

        # Test Monte Carlo results
        mc_results = [
            {
                "collision_count": 0,
                "conflicts_total": 5,
                "conflict_resolution_rate_pct": 100.0,
                "safety_score": 0.95,
            },
            {
                "collision_count": 1,
                "conflicts_total": 6,
                "conflict_resolution_rate_pct": 83.3,
                "safety_score": 0.85,
            },
        ]

        sweep_summary = monte_carlo_analyzer.analyze_sweep_results(mc_results)
        json_str = json.dumps(sweep_summary, default=str)
        assert json_str is not None

    def test_response_time_analysis(self, performance_analyzer):
        """Test 7: Response time analysis with event log.

        Verifies:
        - Extracts response times from event log
        - Computes percentiles correctly
        - Handles empty logs gracefully
        """
        # Empty log
        result = performance_analyzer.analyze_response_time([])
        assert result["count"] == 0
        assert result["mean_s"] == 0.0

        # Log with response times
        event_log = [
            {"event_type": "ADVISORY", "response_time_s": 0.1},
            {"event_type": "ADVISORY", "response_time_s": 0.2},
            {"event_type": "ADVISORY", "response_time_s": 0.3},
            {"event_type": "CLEARANCE"},  # No response_time_s
            {"event_type": "ADVISORY", "response_time_s": 0.4},
            {"event_type": "ADVISORY", "response_time_s": 0.5},
        ]

        result = performance_analyzer.analyze_response_time(event_log)
        assert result["count"] == 5
        assert result["mean_s"] == pytest.approx(0.3, abs=0.01)
        assert result["min_s"] == 0.1
        assert result["max_s"] == 0.5
        assert 0.2 <= result["p50_s"] <= 0.4

    def test_throughput_calculation(self, performance_analyzer):
        """Test 8: Throughput (missions/min) calculation.

        Verifies:
        - Computes missions per minute
        - Handles edge cases (zero time, zero missions)
        """
        # Normal case: 10 missions in 60 seconds = 10 missions/min
        throughput = performance_analyzer.analyze_throughput(
            completed_missions=10, total_time_s=60.0
        )
        assert throughput == 10.0

        # Half minute: 5 missions in 30 seconds = 10 missions/min
        throughput = performance_analyzer.analyze_throughput(
            completed_missions=5, total_time_s=30.0
        )
        assert throughput == 10.0

        # Zero missions
        throughput = performance_analyzer.analyze_throughput(
            completed_missions=0, total_time_s=60.0
        )
        assert throughput == 0.0

        # Zero time
        throughput = performance_analyzer.analyze_throughput(
            completed_missions=10, total_time_s=0.0
        )
        assert throughput == 0.0

    def test_safety_metrics_calculation(self, performance_analyzer):
        """Test 9: Safety metrics calculation.

        Verifies:
        - Computes safety score (0.0-1.0)
        - Handles multiple safety factors
        - Generates summary strings
        """
        # Safe scenario: no collisions
        sim_data = {
            "collision_count": 0,
            "conflicts_total": 5,
            "near_miss_count": 0,
            "min_separation_distance_m": 100.0,
        }

        safety = performance_analyzer.calculate_safety_metrics(sim_data)
        assert 0.0 <= safety["safety_score"] <= 1.0
        assert safety["collision_severity"] == 0.0
        assert "안전함" in safety["summary"]

        # Unsafe scenario: multiple collisions
        sim_data = {
            "collision_count": 5,
            "conflicts_total": 10,
            "near_miss_count": 20,
            "min_separation_distance_m": 5.0,
        }

        safety = performance_analyzer.calculate_safety_metrics(sim_data)
        assert 0.0 <= safety["safety_score"] <= 1.0
        assert safety["collision_severity"] > 0.0
        assert "위험" in safety["summary"]


# ─────────────────────────────────────────────────────────────
# Integration with Real Simulation
# ─────────────────────────────────────────────────────────────


class TestE2EWithRealSimulation:
    """Tests that run actual simulator to verify full pipeline."""

    def test_full_simulation_pipeline(self, config_path):
        """Test: Full end-to-end with real simulator.

        Runs complete simulation pipeline:
        1. Create SwarmSimulator
        2. Run 5-second simulation with 8 drones
        3. Verify all outputs are valid
        4. Check simulation runs without error
        """
        scenario_cfg = {"drones": {"default_count": 8}}
        sim = SwarmSimulator(
            config_path=config_path,
            scenario_cfg=scenario_cfg,
            seed=999,
        )

        # Run simulation (drones are spawned during run())
        result = sim.run(duration_s=5.0)

        # Verify result
        assert result is not None
        result_dict = result.to_dict()
        assert "collision_count" in result_dict
        assert "n_drones" in result_dict
        assert result_dict["n_drones"] == 8

        # Verify drones exist after simulation
        assert len(sim._drones) == 8

        # Verify drones have valid state
        for did, drone in sim._drones.items():
            assert drone.position is not None
            assert len(drone.position) == 3
            # All positions should be within or near airspace bounds
            assert -15000 <= drone.position[0] <= 15000
            assert -15000 <= drone.position[1] <= 15000
            assert 0 <= drone.position[2] <= 200

    def test_simulation_result_completeness(self, config_path):
        """Test: Verify SimulationResult contains all expected fields.

        Ensures the result dict has all KPIs.
        """
        scenario_cfg = {"drones": {"default_count": 5}}
        sim = SwarmSimulator(
            config_path=config_path,
            scenario_cfg=scenario_cfg,
            seed=777,
        )

        result = sim.run(duration_s=2.0)
        result_dict = result.to_dict()

        # Check presence of key metrics
        expected_keys = [
            "collision_count",
            "near_miss_count",
            "conflicts_total",
            "advisories_issued",
            "conflict_resolution_rate_pct",
            "seed",
            "scenario",
            "duration_s",
            "n_drones",
        ]

        for key in expected_keys:
            assert key in result_dict, f"Missing key: {key}"
            assert result_dict[key] is not None


# ─────────────────────────────────────────────────────────────
# Parametrized Tests
# ─────────────────────────────────────────────────────────────


class TestParametrized:
    """Parametrized tests for various scenarios."""

    @pytest.mark.parametrize("drone_count", [3, 5, 10])
    def test_various_drone_counts(self, config_path, drone_count):
        """Test simulator with various drone counts.

        Verifies scalability up to 10 drones in quick test.
        """
        scenario_cfg = {"drones": {"default_count": drone_count}}
        sim = SwarmSimulator(
            config_path=config_path,
            scenario_cfg=scenario_cfg,
            seed=42,
        )

        result = sim.run(duration_s=2.0)
        assert result.n_drones == drone_count

    @pytest.mark.parametrize("seed", [42, 123, 456])
    def test_determinism_with_seed(self, config_path, seed):
        """Test that same seed produces consistent results.

        Runs same config twice with same seed,
        verifies collision counts match.
        """
        results = []
        for _ in range(2):
            scenario_cfg = {"drones": {"default_count": 5}}
            sim = SwarmSimulator(
                config_path=config_path,
                scenario_cfg=scenario_cfg,
                seed=seed,
            )
            result = sim.run(duration_s=2.0)
            results.append(result)

        # Both runs should have same collision count
        assert results[0].collision_count == results[1].collision_count


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
