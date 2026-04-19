"""
Airspace Grid Manager for Drone Traffic Management
====================================================
3D grid-based airspace management with corridor assignment and conflict detection.

Classes:
    GridCell      — Single cell in 3D airspace grid
    Corridor      — Flight corridor definition
    AirspaceGrid  — 3D grid manager for airspace
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class GridCell:
    """
    Single cell in 3D airspace grid.

    Attributes:
        cell_id: Unique cell identifier
        bounds: Spatial bounds ((min_x, max_x), (min_y, max_y), (min_z, max_z))
        occupying_corridors: Set of corridor IDs in this cell
        occupancy_count: Number of drones passing through cell
    """
    cell_id: tuple  # (grid_x, grid_y, grid_z)
    bounds: tuple
    occupying_corridors: set[int] = field(default_factory=set)
    occupancy_count: int = 0

    def contains_point(self, point: np.ndarray) -> bool:
        """Check if point is within cell bounds."""
        for dim in range(3):
            min_b, max_b = self.bounds[dim]
            if not (min_b <= point[dim] <= max_b):
                return False
        return True


@dataclass
class Corridor:
    """
    Flight corridor definition.

    Attributes:
        corridor_id: Unique corridor identifier
        drone_id: ID of drone using this corridor
        start: Start waypoint (x, y, z)
        end: End waypoint (x, y, z)
        radius: Corridor radius in meters
        expiry_time: Corridor expiry time (seconds, for TTL simulation)
        cells: List of grid cells this corridor passes through
        is_active: Whether corridor is currently active
    """
    corridor_id: int
    drone_id: int
    start: np.ndarray
    end: np.ndarray
    radius: float = 20.0
    expiry_time: float = 60.0
    cells: list[GridCell] = field(default_factory=list)
    is_active: bool = True
    creation_time: float = 0.0

    def __post_init__(self):
        """Ensure start and end are numpy arrays."""
        self.start = np.asarray(self.start, dtype=np.float64)
        self.end = np.asarray(self.end, dtype=np.float64)

    def is_expired(self, current_time: float) -> bool:
        """Check if corridor has expired based on TTL."""
        return current_time > (self.creation_time + self.expiry_time)

    def point_in_corridor(self, point: np.ndarray) -> bool:
        """
        Check if point is within corridor (cylindrical volume).

        Corridor is a cylinder between start and end with given radius.
        """
        point = np.asarray(point, dtype=np.float64)

        # Vector from start to end
        vec = self.end - self.start
        vec_len = np.linalg.norm(vec)

        if vec_len < 1e-6:
            # Start and end are same point, use sphere
            dist = np.linalg.norm(point - self.start)
            return bool(dist <= self.radius)

        # Vector from start to point
        to_point = point - self.start

        # Project onto corridor axis
        t = np.dot(to_point, vec) / (vec_len ** 2)
        t = np.clip(t, 0.0, 1.0)

        # Closest point on corridor axis
        closest = self.start + t * vec

        # Distance from point to axis
        dist = np.linalg.norm(point - closest)

        return bool(dist <= self.radius)


class AirspaceGrid:
    """
    3D grid-based airspace manager.

    Manages corridors, conflict detection, and separation violations.

    Attributes:
        grid_size: Cell size in meters (creates cubic cells)
        bounds: Airspace bounds ((min_x, max_x), (min_y, max_y), (min_z, max_z))
        cells: Dict of GridCell indexed by (grid_x, grid_y, grid_z)
        corridors: Dict of Corridor indexed by corridor_id
        min_separation: Minimum separation distance between drones (meters)
    """

    def __init__(
        self,
        grid_size: float = 50.0,
        bounds: Optional[tuple] = None,
        min_separation: float = 30.0,
    ):
        """
        Initialize AirspaceGrid.

        Args:
            grid_size: Size of each grid cell in meters
            bounds: Airspace bounds, default 1000m cube
            min_separation: Minimum separation distance (meters)
        """
        self.grid_size = grid_size
        self.min_separation = min_separation

        # Default bounds: 1000m cube
        if bounds is None:
            bounds = (
                (-500.0, 500.0),
                (-500.0, 500.0),
                (0.0, 1000.0),
            )
        self.bounds = bounds

        self.cells: dict[tuple, GridCell] = {}
        self.corridors: dict[int, Corridor] = {}
        self.next_corridor_id = 1000

        # Initialize grid cells
        self._initialize_grid()

    def _initialize_grid(self) -> None:
        """Create grid cells covering the airspace."""
        for dim in range(3):
            min_b, max_b = self.bounds[dim]
            num_cells = int(np.ceil((max_b - min_b) / self.grid_size))

        # Generate all cell IDs
        x_range = range(int((self.bounds[0][0]) // self.grid_size),
                       int((self.bounds[0][1] // self.grid_size)) + 1)
        y_range = range(int((self.bounds[1][0]) // self.grid_size),
                       int((self.bounds[1][1] // self.grid_size)) + 1)
        z_range = range(int((self.bounds[2][0]) // self.grid_size),
                       int((self.bounds[2][1] // self.grid_size)) + 1)

        for gx in x_range:
            for gy in y_range:
                for gz in z_range:
                    cell_id = (gx, gy, gz)

                    # Cell bounds
                    bounds = (
                        (gx * self.grid_size, (gx + 1) * self.grid_size),
                        (gy * self.grid_size, (gy + 1) * self.grid_size),
                        (gz * self.grid_size, (gz + 1) * self.grid_size),
                    )

                    self.cells[cell_id] = GridCell(
                        cell_id=cell_id,
                        bounds=bounds,
                    )

    def _get_cell_id(self, point: np.ndarray) -> Optional[tuple]:
        """Get grid cell ID for a point."""
        point = np.asarray(point, dtype=np.float64)

        cell_id = (
            int(np.floor(point[0] / self.grid_size)),
            int(np.floor(point[1] / self.grid_size)),
            int(np.floor(point[2] / self.grid_size)),
        )

        return cell_id if cell_id in self.cells else None

    def _corridor_cells(self, corridor: Corridor) -> list[GridCell]:
        """Get all cells that a corridor passes through."""
        cells = set()

        # Sample corridor at multiple points
        num_samples = max(5, int(np.linalg.norm(corridor.end - corridor.start) / self.grid_size))
        for i in range(num_samples + 1):
            t = i / (num_samples + 1) if num_samples > 0 else 0.5
            point = corridor.start + t * (corridor.end - corridor.start)

            # Check cells in a radius around this point
            cell_id = self._get_cell_id(point)
            if cell_id:
                cells.add(cell_id)

                # Add neighboring cells within corridor radius
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        for dz in [-1, 0, 1]:
                            neighbor_id = (
                                cell_id[0] + dx,
                                cell_id[1] + dy,
                                cell_id[2] + dz,
                            )
                            if neighbor_id in self.cells:
                                cells.add(neighbor_id)

        return [self.cells[cid] for cid in cells]

    def assign_corridor(
        self,
        drone_id: int,
        start: np.ndarray,
        end: np.ndarray,
        radius: float = 20.0,
        ttl: float = 60.0,
        current_time: float = 0.0,
    ) -> int:
        """
        Assign a flight corridor to a drone.

        Args:
            drone_id: Drone identifier
            start: Start waypoint [x, y, z]
            end: End waypoint [x, y, z]
            radius: Corridor radius in meters
            ttl: Time-to-live in seconds (corridor expiry)
            current_time: Current simulation time

        Returns:
            Corridor ID
        """
        corridor_id = self.next_corridor_id
        self.next_corridor_id += 1

        corridor = Corridor(
            corridor_id=corridor_id,
            drone_id=drone_id,
            start=start,
            end=end,
            radius=radius,
            expiry_time=ttl,
            creation_time=current_time,
        )

        # Get cells this corridor passes through
        corridor.cells = self._corridor_cells(corridor)

        # Register corridor in cells
        for cell in corridor.cells:
            cell.occupying_corridors.add(corridor_id)

        self.corridors[corridor_id] = corridor
        return corridor_id

    def check_conflict(
        self,
        corridor_id1: int,
        corridor_id2: int,
    ) -> bool:
        """
        Check if two corridors have overlapping regions.

        Args:
            corridor_id1: First corridor ID
            corridor_id2: Second corridor ID

        Returns:
            True if corridors conflict (overlap), False otherwise
        """
        if corridor_id1 not in self.corridors or corridor_id2 not in self.corridors:
            return False

        c1 = self.corridors[corridor_id1]
        c2 = self.corridors[corridor_id2]

        # Check if corridor cells overlap
        cells1 = set(c.cell_id for c in c1.cells)
        cells2 = set(c.cell_id for c in c2.cells)

        if cells1 & cells2:  # If cells overlap
            # Do more precise check: sample points from both corridors
            num_samples = 10
            for i in range(num_samples):
                t = i / (num_samples - 1) if num_samples > 1 else 0.5
                p1 = c1.start + t * (c1.end - c1.start)

                # Check if this point is in corridor 2
                if c2.point_in_corridor(p1):
                    return True

            # Check reverse direction
            for i in range(num_samples):
                t = i / (num_samples - 1) if num_samples > 1 else 0.5
                p2 = c2.start + t * (c2.end - c2.start)

                # Check if this point is in corridor 1
                if c1.point_in_corridor(p2):
                    return True

        return False

    def get_separation_violations(
        self,
        drones: dict[int, np.ndarray],
        min_separation: Optional[float] = None,
    ) -> list[tuple[int, int, float]]:
        """
        Find pairs of drones that violate minimum separation.

        Args:
            drones: Dict of drone_id -> position (numpy array)
            min_separation: Override minimum separation (use self.min_separation if None)

        Returns:
            List of tuples (drone_id1, drone_id2, distance) where distance < min_separation
        """
        if min_separation is None:
            min_separation = self.min_separation

        violations = []
        drone_ids = list(drones.keys())

        for i, d1 in enumerate(drone_ids):
            for d2 in drone_ids[i + 1:]:
                pos1 = np.asarray(drones[d1], dtype=np.float64)
                pos2 = np.asarray(drones[d2], dtype=np.float64)

                distance = float(np.linalg.norm(pos1 - pos2))

                if distance < min_separation:
                    violations.append((d1, d2, distance))

        return violations

    def update_expiry(self, current_time: float) -> None:
        """
        Remove expired corridors (TTL-based cleanup).

        Args:
            current_time: Current simulation time
        """
        expired_ids = [
            cid for cid, corridor in self.corridors.items()
            if corridor.is_expired(current_time)
        ]

        for cid in expired_ids:
            corridor = self.corridors.pop(cid)
            # Unregister from cells
            for cell in corridor.cells:
                cell.occupying_corridors.discard(cid)

    def get_statistics(self) -> dict:
        """Get airspace usage statistics."""
        active_corridors = sum(1 for c in self.corridors.values() if c.is_active)
        total_cells = len(self.cells)
        occupied_cells = sum(1 for c in self.cells.values() if c.occupying_corridors)

        return {
            "total_cells": total_cells,
            "occupied_cells": occupied_cells,
            "total_corridors": len(self.corridors),
            "active_corridors": active_corridors,
            "grid_utilization": occupied_cells / total_cells if total_cells > 0 else 0.0,
        }
