"""
Unit Tests for Prototype Framework
===================================
Tests for boids_swarm, sensor_fusion, and airspace_manager modules.
"""

import pytest
import numpy as np
from src.boids_swarm import BoidAgent, SwarmSimulator as BoidsSimulator
from src.sensor_fusion import (
    SensorMeasurement,
    SensorType,
    KalmanFilter,
    SensorFusion,
)
from src.airspace_manager import Corridor, AirspaceGrid


class TestBoidAgent:
    """Tests for BoidAgent class."""

    def test_boid_creation(self):
        """Test basic boid creation."""
        pos = np.array([0.0, 0.0, 0.0])
        boid = BoidAgent(boid_id=1, position=pos)

        assert boid.boid_id == 1
        assert np.allclose(boid.position, pos)
        assert np.allclose(boid.velocity, np.zeros(3))

    def test_boid_update_position(self):
        """Test position update with velocity."""
        pos = np.array([0.0, 0.0, 0.0])
        vel = np.array([1.0, 0.0, 0.0])
        boid = BoidAgent(boid_id=1, position=pos, velocity=vel)

        boid.update_position(dt=1.0)

        assert np.allclose(boid.position, [1.0, 0.0, 0.0])

    def test_boid_distance(self):
        """Test distance calculation between boids."""
        boid1 = BoidAgent(boid_id=1, position=[0.0, 0.0, 0.0])
        boid2 = BoidAgent(boid_id=2, position=[3.0, 4.0, 0.0])

        distance = boid1.distance_to(boid2)

        assert np.isclose(distance, 5.0)

    def test_max_speed_limit(self):
        """Test velocity is limited to max_speed."""
        boid = BoidAgent(boid_id=1, position=[0.0, 0.0, 0.0], max_speed=10.0)
        boid.velocity = np.array([20.0, 0.0, 0.0])

        boid.update_velocity()

        speed = np.linalg.norm(boid.velocity)
        assert np.isclose(speed, 10.0)


class TestSwarmSimulator:
    """Tests for SwarmSimulator class."""

    def test_swarm_creation(self):
        """Test swarm creation with N boids."""
        swarm = BoidsSimulator(n_boids=5, dimension=3, seed=42)

        assert len(swarm.boids) == 5
        assert all(b.boid_id < 5 for b in swarm.boids)

    def test_get_positions(self):
        """Test get_positions returns correct shape."""
        swarm = BoidsSimulator(n_boids=10, seed=42)
        positions = swarm.get_positions()

        assert positions.shape == (10, 3)
        assert positions.dtype == np.float64

    def test_separation_rule(self):
        """Test separation rule generates repulsive force."""
        swarm = BoidsSimulator(n_boids=2, seed=42)

        # Place boids close together
        swarm.boids[0].position = np.array([0.0, 0.0, 0.0])
        swarm.boids[1].position = np.array([5.0, 0.0, 0.0])
        swarm.boids[0].acceleration = np.zeros(3)

        neighbors = [swarm.boids[1]]
        force = swarm._separation(swarm.boids[0], neighbors)

        # Force should point away (negative x direction)
        assert force[0] < 0

    def test_cohesion_rule(self):
        """Test cohesion rule generates attractive force."""
        swarm = BoidsSimulator(n_boids=2, seed=42)

        # Place boids
        swarm.boids[0].position = np.array([0.0, 0.0, 0.0])
        swarm.boids[1].position = np.array([100.0, 0.0, 0.0])
        swarm.boids[0].acceleration = np.zeros(3)

        neighbors = [swarm.boids[1]]
        force = swarm._cohesion(swarm.boids[0], neighbors)

        # Force should point toward center (positive x direction)
        assert force[0] > 0

    def test_step_updates_positions(self):
        """Test simulation step updates boid positions."""
        swarm = BoidsSimulator(n_boids=3, seed=42)
        initial_positions = swarm.get_positions().copy()

        swarm.step(dt=0.1)
        updated_positions = swarm.get_positions()

        # At least some positions should have changed
        assert not np.allclose(initial_positions, updated_positions)

    def test_bounds_enforcement(self):
        """Test boids reflect off boundaries."""
        swarm = BoidsSimulator(
            n_boids=1,
            bounds=((-100, 100), (-100, 100), (0, 1000)),
        )

        swarm.boids[0].position = np.array([-100.0, 0.0, 0.0])
        swarm.boids[0].velocity = np.array([-10.0, 0.0, 0.0])

        swarm._enforce_bounds(swarm.boids[0])

        # Position should be at boundary
        assert swarm.boids[0].position[0] >= -100.0
        # Velocity should reflect
        assert swarm.boids[0].velocity[0] > 0


class TestKalmanFilter:
    """Tests for KalmanFilter class."""

    def test_filter_creation(self):
        """Test Kalman filter initialization."""
        kf = KalmanFilter(
            initial_position=np.array([0.0, 0.0, 0.0]),
            initial_velocity=np.array([1.0, 0.0, 0.0]),
        )

        assert kf.state.shape == (6,)
        assert np.allclose(kf.state[:3], [0.0, 0.0, 0.0])
        assert np.allclose(kf.state[3:], [1.0, 0.0, 0.0])

    def test_predict_step(self):
        """Test prediction step."""
        kf = KalmanFilter(
            initial_position=np.array([0.0, 0.0, 0.0]),
            initial_velocity=np.array([1.0, 0.0, 0.0]),
            dt=1.0,
        )

        kf.predict()

        # Position should increase by velocity * dt
        assert np.isclose(kf.state[0], 1.0)

    def test_update_step(self):
        """Test measurement update."""
        kf = KalmanFilter(
            initial_position=np.array([0.0, 0.0, 0.0]),
            initial_velocity=np.zeros(3),
        )

        measurement = np.array([1.0, 1.0, 1.0])
        kf.update(measurement, measurement_noise=0.1)

        # Position should move toward measurement
        pos = kf.get_position()
        assert np.linalg.norm(pos) > 0


class TestSensorFusion:
    """Tests for SensorFusion class."""

    def test_fusion_creation(self):
        """Test sensor fusion initialization."""
        fusion = SensorFusion()

        assert fusion.outlier_threshold == 3.0
        assert len(fusion.kalman_filters) == 0

    def test_fuse_single_measurement(self):
        """Test fusion with single measurement."""
        fusion = SensorFusion()

        measurement = SensorMeasurement(
            sensor_type=SensorType.RF,
            position=np.array([0.0, 0.0, 0.0]),
            covariance=5.0,
        )

        fused = fusion.fuse(
            drone_id=1,
            measurements=[measurement],
        )

        assert fused.position.shape == (3,)
        assert fused.velocity.shape == (3,)
        assert fused.num_sensors == 1

    def test_fuse_multiple_measurements(self):
        """Test fusion with multiple sensors."""
        fusion = SensorFusion()

        measurements = [
            SensorMeasurement(
                sensor_type=SensorType.RF,
                position=np.array([0.0, 0.0, 0.0]),
                covariance=5.0,
                confidence=0.7,
            ),
            SensorMeasurement(
                sensor_type=SensorType.REMOTE_ID,
                position=np.array([0.1, 0.0, 0.0]),
                covariance=1.0,
                confidence=0.95,
            ),
        ]

        fused = fusion.fuse(
            drone_id=1,
            measurements=measurements,
        )

        assert fused.num_sensors == 2
        assert fused.confidence_score > 0.5

    def test_outlier_rejection(self):
        """Test outlier rejection in sensor fusion."""
        fusion = SensorFusion(outlier_threshold=2.0)

        # Create a KF first
        fusion.kalman_filters[1] = KalmanFilter(
            initial_position=np.array([0.0, 0.0, 0.0])
        )
        fusion.kalman_filters[1].predict()

        # Outlier measurement far from predicted state
        outlier = SensorMeasurement(
            sensor_type=SensorType.RF,
            position=np.array([1000.0, 1000.0, 1000.0]),
            covariance=5.0,
        )

        fused = fusion.fuse(
            drone_id=1,
            measurements=[outlier],
        )

        # Should detect as outlier and reduce confidence
        assert fused.num_sensors < 1 or fused.confidence_score < 0.5


class TestAirspaceGrid:
    """Tests for AirspaceGrid class."""

    def test_grid_creation(self):
        """Test airspace grid creation."""
        grid = AirspaceGrid(grid_size=50.0)

        assert len(grid.cells) > 0
        assert grid.min_separation == 30.0

    def test_corridor_assignment(self):
        """Test corridor assignment."""
        grid = AirspaceGrid()

        corridor_id = grid.assign_corridor(
            drone_id=1,
            start=np.array([0.0, 0.0, 0.0]),
            end=np.array([100.0, 0.0, 0.0]),
        )

        assert corridor_id in grid.corridors
        assert grid.corridors[corridor_id].drone_id == 1

    def test_corridor_point_containment(self):
        """Test corridor point containment check."""
        corridor = Corridor(
            corridor_id=1,
            drone_id=1,
            start=np.array([0.0, 0.0, 0.0]),
            end=np.array([100.0, 0.0, 0.0]),
            radius=10.0,
        )

        # Point on axis should be in corridor
        assert corridor.point_in_corridor(np.array([50.0, 0.0, 0.0]))

        # Point outside should not be in corridor
        assert not corridor.point_in_corridor(np.array([50.0, 50.0, 0.0]))

    def test_separation_violation_detection(self):
        """Test separation violation detection."""
        grid = AirspaceGrid(min_separation=50.0)

        drones = {
            1: np.array([0.0, 0.0, 0.0]),
            2: np.array([10.0, 0.0, 0.0]),  # Too close
            3: np.array([100.0, 0.0, 0.0]),  # Far away
        }

        violations = grid.get_separation_violations(drones)

        assert len(violations) == 1
        assert violations[0][:2] == (1, 2) or violations[0][:2] == (2, 1)

    def test_corridor_expiry(self):
        """Test corridor TTL-based expiry."""
        grid = AirspaceGrid()

        corridor_id = grid.assign_corridor(
            drone_id=1,
            start=np.array([0.0, 0.0, 0.0]),
            end=np.array([100.0, 0.0, 0.0]),
            ttl=10.0,
            current_time=0.0,
        )

        assert corridor_id in grid.corridors

        # Update at t=15 (after expiry)
        grid.update_expiry(current_time=15.0)

        assert corridor_id not in grid.corridors

    def test_grid_statistics(self):
        """Test grid statistics computation."""
        grid = AirspaceGrid()

        grid.assign_corridor(
            drone_id=1,
            start=np.array([0.0, 0.0, 0.0]),
            end=np.array([100.0, 0.0, 0.0]),
        )

        stats = grid.get_statistics()

        assert "total_cells" in stats
        assert "occupied_cells" in stats
        assert stats["total_corridors"] == 1
        assert stats["grid_utilization"] >= 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
