"""
Boids Swarm Algorithm Implementation
======================================
Boids algorithm (Boid = bird-oid object) for multi-agent swarm simulation.
Implements three core rules: separation, alignment, and cohesion.

Classes:
    BoidAgent      — Individual boid with position, velocity, acceleration
    SwarmSimulator — Manages N boids and simulation state
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class BoidAgent:
    """
    Individual boid agent with position, velocity, and acceleration.

    Attributes:
        boid_id: Unique identifier
        position: 2D or 3D position vector (numpy array)
        velocity: 2D or 3D velocity vector (numpy array)
        acceleration: 2D or 3D acceleration vector (numpy array)
        max_speed: Maximum allowed speed (m/s)
        max_force: Maximum steering force magnitude
        is_leader: Whether this boid is a leader (affects behavior)
        neighbor_distance: Perception radius for detecting neighbors (m)
    """

    boid_id: int
    position: np.ndarray
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))
    acceleration: np.ndarray = field(default_factory=lambda: np.zeros(3))
    max_speed: float = 15.0
    max_force: float = 0.5
    is_leader: bool = False
    neighbor_distance: float = 50.0

    def __post_init__(self):
        """Ensure position, velocity, acceleration are numpy arrays."""
        self.position = np.asarray(self.position, dtype=np.float64)
        self.velocity = np.asarray(self.velocity, dtype=np.float64)
        self.acceleration = np.asarray(self.acceleration, dtype=np.float64)

        # Ensure 3D vectors (pad with zeros if 2D)
        if self.position.ndim == 1:
            if len(self.position) == 2:
                self.position = np.append(self.position, 0.0)
            if len(self.velocity) == 2:
                self.velocity = np.append(self.velocity, 0.0)
            if len(self.acceleration) == 2:
                self.acceleration = np.append(self.acceleration, 0.0)

    def apply_force(self, force: np.ndarray) -> None:
        """Apply force to acceleration (F = ma, assume m=1)."""
        self.acceleration += np.asarray(force, dtype=np.float64)

    def update_velocity(self) -> None:
        """Update velocity based on acceleration, applying max speed limit."""
        self.velocity += self.acceleration
        speed = np.linalg.norm(self.velocity)
        if speed > self.max_speed:
            self.velocity = (self.velocity / speed) * self.max_speed
        self.acceleration[:] = 0.0  # Reset acceleration each cycle

    def update_position(self, dt: float) -> None:
        """Update position based on velocity."""
        self.position += self.velocity * dt

    def distance_to(self, other: BoidAgent) -> float:
        """Euclidean distance to another boid."""
        return float(np.linalg.norm(self.position - other.position))


class SwarmSimulator:
    """
    Manager for N boids in 2D or 3D space.
    Implements Boids algorithm with separation, alignment, and cohesion.

    Attributes:
        boids: List of BoidAgent instances
        dimension: 2 or 3 (dimensionality of simulation space)
        bounds: Simulation space bounds ((min_x, max_x), (min_y, max_y), (min_z, max_z))
        separation_weight: Weight for separation rule (0-1)
        alignment_weight: Weight for alignment rule (0-1)
        cohesion_weight: Weight for cohesion rule (0-1)
        obstacle_avoidance_weight: Weight for obstacle avoidance (0-1)
        leader_follow_weight: Weight for leader-follower mode (0-1)
    """

    def __init__(
        self,
        n_boids: int = 10,
        dimension: int = 3,
        bounds: Optional[tuple] = None,
        separation_weight: float = 1.5,
        alignment_weight: float = 1.0,
        cohesion_weight: float = 1.0,
        obstacle_avoidance_weight: float = 2.0,
        leader_follow_weight: float = 0.5,
        seed: Optional[int] = None,
    ):
        """
        Initialize SwarmSimulator.

        Args:
            n_boids: Number of boids to spawn
            dimension: 2 or 3 (spatial dimensionality)
            bounds: Space bounds as tuple of (min, max) per dimension
                   If None, defaults to 1000m cube
            separation_weight: Weight for separation rule
            alignment_weight: Weight for alignment rule
            cohesion_weight: Weight for cohesion rule
            obstacle_avoidance_weight: Weight for obstacle avoidance
            leader_follow_weight: Weight for leader-follower behavior
            seed: Random seed for reproducibility
        """
        if seed is not None:
            np.random.seed(seed)

        self.dimension = dimension
        self.boids: list[BoidAgent] = []
        self.obstacles: list[np.ndarray] = []  # List of obstacle positions

        # Default bounds: 1000m cube
        if bounds is None:
            bounds = (
                (-500.0, 500.0),
                (-500.0, 500.0),
                (0.0, 1000.0),
            )
        self.bounds = bounds

        # Boids algorithm weights
        self.separation_weight = separation_weight
        self.alignment_weight = alignment_weight
        self.cohesion_weight = cohesion_weight
        self.obstacle_avoidance_weight = obstacle_avoidance_weight
        self.leader_follow_weight = leader_follow_weight

        # Spawn boids
        self._spawn_boids(n_boids)

    def _spawn_boids(self, n_boids: int) -> None:
        """Spawn n_boids with random initial positions and velocities."""
        for i in range(n_boids):
            # Random position within bounds
            pos = np.array([
                np.random.uniform(self.bounds[0][0], self.bounds[0][1]),
                np.random.uniform(self.bounds[1][0], self.bounds[1][1]),
                np.random.uniform(self.bounds[2][0], self.bounds[2][1]),
            ], dtype=np.float64)

            # Random velocity (-5 to 5 m/s)
            vel = np.random.uniform(-5.0, 5.0, 3).astype(np.float64)

            # First boid is the leader
            is_leader = (i == 0)

            boid = BoidAgent(
                boid_id=i,
                position=pos,
                velocity=vel,
                is_leader=is_leader,
            )
            self.boids.append(boid)

    def add_obstacle(self, position: np.ndarray, radius: float = 10.0) -> None:
        """Add an obstacle sphere at the given position with given radius."""
        self.obstacles.append(np.asarray(position, dtype=np.float64))

    def _separation(self, boid: BoidAgent, neighbors: list[BoidAgent]) -> np.ndarray:
        """
        Separation rule: steer to avoid crowding local neighbors.

        Returns force vector pointing away from neighbors.
        """
        force = np.zeros(3, dtype=np.float64)
        if not neighbors:
            return force

        desired_separation = 20.0  # meters
        count = 0

        for neighbor in neighbors:
            distance = boid.distance_to(neighbor)
            if 0 < distance < desired_separation:
                # Vector pointing away from neighbor
                diff = boid.position - neighbor.position
                diff = diff / distance  # Normalize
                diff = diff / (distance + 1e-6)  # Weight by distance
                force += diff
                count += 1

        if count > 0:
            force = force / count

        # Limit force magnitude
        force_mag = np.linalg.norm(force)
        if force_mag > 0:
            force = (force / force_mag) * boid.max_force

        return force

    def _alignment(self, boid: BoidAgent, neighbors: list[BoidAgent]) -> np.ndarray:
        """
        Alignment rule: steer towards the average heading of local neighbors.

        Returns force vector to align velocity with neighbors.
        """
        force = np.zeros(3, dtype=np.float64)
        if not neighbors:
            return force

        # Average velocity of neighbors
        avg_velocity = np.zeros(3, dtype=np.float64)
        for neighbor in neighbors:
            avg_velocity += neighbor.velocity
        avg_velocity = avg_velocity / len(neighbors)

        # Steering vector (desired - current)
        steering = avg_velocity - boid.velocity

        # Limit force magnitude
        force_mag = np.linalg.norm(steering)
        if force_mag > 0:
            steering = (steering / force_mag) * boid.max_force

        return steering

    def _cohesion(self, boid: BoidAgent, neighbors: list[BoidAgent]) -> np.ndarray:
        """
        Cohesion rule: steer to move toward the average location of neighbors.

        Returns force vector toward center of neighbors.
        """
        force = np.zeros(3, dtype=np.float64)
        if not neighbors:
            return force

        # Average position of neighbors
        center = np.zeros(3, dtype=np.float64)
        for neighbor in neighbors:
            center += neighbor.position
        center = center / len(neighbors)

        # Steering toward center
        steering = center - boid.position

        # Limit force magnitude
        force_mag = np.linalg.norm(steering)
        if force_mag > 0:
            steering = (steering / force_mag) * boid.max_force

        return steering

    def _obstacle_avoidance(self, boid: BoidAgent) -> np.ndarray:
        """
        Obstacle avoidance: steer to avoid spherical obstacles.

        Returns force vector away from nearby obstacles.
        """
        force = np.zeros(3, dtype=np.float64)
        obstacle_radius = 10.0
        avoidance_distance = 50.0

        for obstacle_pos in self.obstacles:
            distance = np.linalg.norm(boid.position - obstacle_pos)

            if 0 < distance < avoidance_distance:
                # Vector pointing away from obstacle
                away = boid.position - obstacle_pos
                away = away / (distance + 1e-6)

                # Strength based on distance
                strength = (avoidance_distance - distance) / avoidance_distance
                force += away * strength

        # Limit force magnitude
        force_mag = np.linalg.norm(force)
        if force_mag > 0:
            force = (force / force_mag) * boid.max_force

        return force

    def _leader_follow(self, boid: BoidAgent, leader: BoidAgent) -> np.ndarray:
        """
        Leader-follower mode: steer to follow the leader boid.

        Returns force vector toward leader.
        """
        if boid.is_leader:
            return np.zeros(3, dtype=np.float64)

        force = np.zeros(3, dtype=np.float64)
        follow_distance = 40.0

        # Steer toward leader
        steering = leader.position - boid.position
        distance = np.linalg.norm(steering)

        if distance > 0:
            steering = (steering / distance) * boid.max_force

        return steering

    def _get_neighbors(self, boid: BoidAgent) -> list[BoidAgent]:
        """Get all neighbors within perception distance."""
        neighbors = []
        for other in self.boids:
            if other.boid_id != boid.boid_id:
                distance = boid.distance_to(other)
                if distance < boid.neighbor_distance:
                    neighbors.append(other)
        return neighbors

    def step(self, dt: float = 0.1) -> None:
        """
        Execute one simulation step.

        Applies Boids algorithm rules to all boids:
        1. Find neighbors
        2. Compute separation, alignment, cohesion forces
        3. Apply obstacle avoidance and leader-following
        4. Update velocities and positions
        5. Enforce boundary conditions

        Args:
            dt: Time step in seconds
        """
        leader = self.boids[0] if self.boids else None

        for boid in self.boids:
            # Get neighbors within perception distance
            neighbors = self._get_neighbors(boid)

            # Compute forces
            sep_force = self._separation(boid, neighbors) * self.separation_weight
            ali_force = self._alignment(boid, neighbors) * self.alignment_weight
            coh_force = self._cohesion(boid, neighbors) * self.cohesion_weight
            obs_force = self._obstacle_avoidance(boid) * self.obstacle_avoidance_weight

            # Apply forces
            boid.apply_force(sep_force)
            boid.apply_force(ali_force)
            boid.apply_force(coh_force)
            boid.apply_force(obs_force)

            # Leader-follower mode (if leader exists and not self)
            if leader and boid.boid_id != leader.boid_id:
                lead_force = self._leader_follow(boid, leader) * self.leader_follow_weight
                boid.apply_force(lead_force)

            # Update dynamics
            boid.update_velocity()
            boid.update_position(dt)

            # Enforce boundary conditions (wrap around or reflect)
            self._enforce_bounds(boid)

    def _enforce_bounds(self, boid: BoidAgent) -> None:
        """Enforce boundary conditions (reflect off boundaries)."""
        for dim in range(3):
            min_bound, max_bound = self.bounds[dim]

            if boid.position[dim] <= min_bound:
                boid.position[dim] = min_bound
                # Reflect: flip direction (ensure velocity points inward)
                if boid.velocity[dim] < 0:
                    boid.velocity[dim] = -boid.velocity[dim]
            elif boid.position[dim] >= max_bound:
                boid.position[dim] = max_bound
                # Reflect: flip direction (ensure velocity points inward)
                if boid.velocity[dim] > 0:
                    boid.velocity[dim] = -boid.velocity[dim]

    def get_positions(self) -> np.ndarray:
        """
        Get positions of all boids as a numpy array.

        Returns:
            Array of shape (n_boids, 3) containing all boid positions
        """
        return np.array([boid.position for boid in self.boids], dtype=np.float64)

    def get_velocities(self) -> np.ndarray:
        """
        Get velocities of all boids as a numpy array.

        Returns:
            Array of shape (n_boids, 3) containing all boid velocities
        """
        return np.array([boid.velocity for boid in self.boids], dtype=np.float64)

    def get_state(self) -> dict:
        """Get complete state of all boids."""
        return {
            "positions": self.get_positions(),
            "velocities": self.get_velocities(),
            "boid_ids": [b.boid_id for b in self.boids],
            "is_leaders": [b.is_leader for b in self.boids],
        }
