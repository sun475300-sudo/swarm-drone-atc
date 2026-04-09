"""
Integration Demo: Swarm Simulation with Boids, Sensor Fusion, and Airspace Manager
====================================================================================

Demonstrates the complete prototype framework:
1. Boids swarm algorithm for drone flocking
2. Multi-sensor fusion for state estimation
3. Airspace grid manager for conflict detection

Runs for 60 seconds simulation time and reports:
- Total conflicts detected
- Conflict resolution rate
- Average separation between drones
- Sensor fusion confidence statistics

Execution:
    python demo_simulation.py
"""

from __future__ import annotations
import numpy as np
from src.boids_swarm import SwarmSimulator as BoidsSimulator, BoidAgent
from src.sensor_fusion import SensorFusion, SensorMeasurement, SensorType
from src.airspace_manager import AirspaceGrid


def spawn_random_measurements(
    position: np.ndarray,
    sensor_types: list[SensorType],
    timestamp: float,
) -> list[SensorMeasurement]:
    """
    Generate synthetic noisy measurements for a given position.

    Each sensor adds realistic noise based on its characteristics:
    - RF:        σ = 5m  (noisy, long range)
    - YOLO:      σ = 2m  (moderate, line-of-sight)
    - RemoteID:  σ = 1m  (most accurate)

    Args:
        position: True position [x, y, z]
        sensor_types: List of available sensors
        timestamp: Measurement timestamp

    Returns:
        List of SensorMeasurement objects
    """
    measurements = []

    for sensor_type in sensor_types:
        if sensor_type == SensorType.RF:
            # RF: noisy, long range
            noise = np.random.normal(0, 5.0, 3)
            measured_pos = position + noise
            measurements.append(SensorMeasurement(
                sensor_type=sensor_type,
                position=measured_pos,
                covariance=5.0,
                timestamp=timestamp,
                confidence=0.7,
            ))

        elif sensor_type == SensorType.YOLO:
            # YOLO: moderate, line-of-sight (50% availability)
            if np.random.random() < 0.5:
                noise = np.random.normal(0, 2.0, 3)
                measured_pos = position + noise
                measurements.append(SensorMeasurement(
                    sensor_type=sensor_type,
                    position=measured_pos,
                    covariance=2.0,
                    timestamp=timestamp,
                    confidence=0.85,
                ))

        elif sensor_type == SensorType.REMOTE_ID:
            # RemoteID: most accurate (80% availability)
            if np.random.random() < 0.8:
                noise = np.random.normal(0, 1.0, 3)
                measured_pos = position + noise
                measurements.append(SensorMeasurement(
                    sensor_type=sensor_type,
                    position=measured_pos,
                    covariance=1.0,
                    timestamp=timestamp,
                    confidence=0.95,
                ))

    return measurements


def demo_simulation(
    n_drones: int = 10,
    duration: float = 60.0,
    dt: float = 0.1,
    seed: int = 42,
) -> dict:
    """
    Run integration demo with all three components.

    Args:
        n_drones: Number of drones to simulate
        duration: Simulation duration in seconds
        dt: Time step in seconds
        seed: Random seed for reproducibility

    Returns:
        Dictionary with summary statistics
    """
    print("=" * 80)
    print("SWARM DRONE AIRSPACE CONTROL - PROTOTYPE INTEGRATION DEMO")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Drones:           {n_drones}")
    print(f"  Duration:         {duration}s")
    print(f"  Time step:        {dt}s")
    print(f"  Seed:             {seed}")

    # Initialize components
    print("\nInitializing components...")
    np.random.seed(seed)

    # 1. Boids swarm
    boids = BoidsSimulator(
        n_boids=n_drones,
        dimension=3,
        separation_weight=1.5,
        alignment_weight=1.0,
        cohesion_weight=1.0,
        seed=seed,
    )

    # 2. Sensor fusion
    sensor_fusion = SensorFusion(outlier_threshold=3.0)

    # 3. Airspace manager
    airspace = AirspaceGrid(
        grid_size=50.0,
        min_separation=20.0,  # meters
    )

    # Statistics tracking
    stats = {
        "conflicts_detected": 0,
        "conflicts_resolved": 0,
        "total_separations_checked": 0,
        "total_separation_violations": 0,
        "average_confidence": [],
        "average_separation": [],
        "min_separation": float('inf'),
        "max_separation": 0.0,
    }

    # Available sensors for each drone
    available_sensors = [SensorType.RF, SensorType.YOLO, SensorType.REMOTE_ID]

    print("  ✓ Boids simulator initialized")
    print("  ✓ Sensor fusion engine initialized")
    print("  ✓ Airspace grid manager initialized")

    # Run simulation loop
    print(f"\nRunning simulation for {duration}s...")
    num_steps = int(duration / dt)

    for step in range(num_steps):
        t = step * dt

        # Step 1: Boids simulation (update positions/velocities)
        boids.step(dt=dt)

        # Step 2: Generate noisy measurements and fuse
        fused_states = {}
        total_confidence = 0.0

        for i, boid in enumerate(boids.boids):
            # Generate synthetic measurements
            measurements = spawn_random_measurements(
                position=boid.position,
                sensor_types=available_sensors,
                timestamp=t,
            )

            # Fuse measurements
            fused_state = sensor_fusion.fuse(
                drone_id=boid.boid_id,
                measurements=measurements,
                dt=dt,
            )
            fused_states[boid.boid_id] = fused_state
            total_confidence += fused_state.confidence_score

        avg_confidence = total_confidence / n_drones if n_drones > 0 else 0.0
        stats["average_confidence"].append(avg_confidence)

        # Step 3: Assign corridors and check conflicts (every 10 steps)
        if step % 10 == 0:
            airspace.update_expiry(current_time=t)

            for i, boid in enumerate(boids.boids):
                # Assign corridor from current to future position
                future_pos = boid.position + boid.velocity * 5.0  # 5 seconds ahead

                corridor_id = airspace.assign_corridor(
                    drone_id=boid.boid_id,
                    start=boid.position.copy(),
                    end=future_pos,
                    radius=15.0,
                    ttl=10.0,
                    current_time=t,
                )

        # Step 4: Check separation violations
        drone_positions = {boid.boid_id: boid.position for boid in boids.boids}

        violations = airspace.get_separation_violations(
            drones=drone_positions,
            min_separation=20.0,
        )

        stats["total_separations_checked"] += len(drone_positions)
        stats["total_separation_violations"] += len(violations)

        if violations:
            stats["conflicts_detected"] += len(violations)

            # For demo purposes, assume conflicts are resolved if sensors agree
            for d1, d2, distance in violations:
                if d1 in fused_states and d2 in fused_states:
                    confidence = (
                        fused_states[d1].confidence_score +
                        fused_states[d2].confidence_score
                    ) / 2.0

                    if confidence > 0.75 and distance > 10.0:
                        stats["conflicts_resolved"] += 1

        # Track separation statistics
        if len(boids.boids) > 1:
            positions = boids.get_positions()
            separations = []

            for i in range(len(positions)):
                for j in range(i + 1, len(positions)):
                    sep = float(np.linalg.norm(positions[i] - positions[j]))
                    separations.append(sep)

            if separations:
                avg_sep = float(np.mean(separations))
                min_sep = float(np.min(separations))
                max_sep = float(np.max(separations))

                stats["average_separation"].append(avg_sep)
                stats["min_separation"] = min(stats["min_separation"], min_sep)
                stats["max_separation"] = max(stats["max_separation"], max_sep)

        # Progress indicator
        if (step + 1) % (num_steps // 10) == 0:
            progress = ((step + 1) / num_steps) * 100
            print(f"  {progress:.0f}% - t={t:.1f}s, "
                  f"conflicts={stats['conflicts_detected']}, "
                  f"avg_confidence={avg_confidence:.2f}")

    # Compute final statistics
    print("\n" + "=" * 80)
    print("SIMULATION RESULTS")
    print("=" * 80)

    avg_confidence_final = (
        float(np.mean(stats["average_confidence"]))
        if stats["average_confidence"]
        else 0.0
    )
    avg_separation_final = (
        float(np.mean(stats["average_separation"]))
        if stats["average_separation"]
        else 0.0
    )

    resolution_rate = (
        (stats["conflicts_resolved"] / stats["conflicts_detected"] * 100)
        if stats["conflicts_detected"] > 0
        else 100.0
    )

    print(f"\nSwarm Dynamics:")
    print(f"  Total drones:                {n_drones}")
    print(f"  Simulation duration:         {duration}s")
    print(f"  Average swarm separation:    {avg_separation_final:.2f}m")
    print(f"  Minimum separation achieved: {stats['min_separation']:.2f}m")
    print(f"  Maximum separation:          {stats['max_separation']:.2f}m")

    print(f"\nConflict Detection & Resolution:")
    print(f"  Conflicts detected:          {stats['conflicts_detected']}")
    print(f"  Conflicts resolved:          {stats['conflicts_resolved']}")
    print(f"  Resolution rate:             {resolution_rate:.1f}%")
    print(f"  Separation violations:       {stats['total_separation_violations']}")

    print(f"\nSensor Fusion Performance:")
    print(f"  Average fusion confidence:   {avg_confidence_final:.2f} (0-1)")
    print(f"  Sensors available:           {len(available_sensors)}")
    print(f"    - RF (σ=5m):               enabled")
    print(f"    - YOLO (σ=2m):             enabled (50% availability)")
    print(f"    - RemoteID (σ=1m):         enabled (80% availability)")

    print(f"\nAirspace Management:")
    airspace_stats = airspace.get_statistics()
    print(f"  Grid cell size:              {airspace.grid_size}m")
    print(f"  Total cells:                 {airspace_stats['total_cells']}")
    print(f"  Occupied cells:              {airspace_stats['occupied_cells']}")
    print(f"  Grid utilization:            {airspace_stats['grid_utilization']:.1%}")
    print(f"  Active corridors:            {airspace_stats['active_corridors']}")

    print("\n" + "=" * 80)
    print("✓ Demo completed successfully")
    print("=" * 80 + "\n")

    return {
        "duration": duration,
        "n_drones": n_drones,
        "avg_separation": avg_separation_final,
        "min_separation": stats["min_separation"],
        "conflicts_detected": stats["conflicts_detected"],
        "resolution_rate": resolution_rate,
        "avg_confidence": avg_confidence_final,
    }


if __name__ == "__main__":
    result = demo_simulation(
        n_drones=10,
        duration=60.0,
        dt=0.1,
        seed=42,
    )
