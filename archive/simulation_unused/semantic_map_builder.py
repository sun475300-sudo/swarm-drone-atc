"""
Semantic Map Builder
Phase 357 - Voxel Grid, Object Tagging, 3D Reconstruction
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict
import heapq


class VoxelState:
    FREE = 0
    OCCUPIED = 1
    UNKNOWN = 2


@dataclass
class Voxel:
    position: Tuple[int, int, int]
    state: int = VoxelState.UNKNOWN
    probability: float = 0.5
    color: Optional[Tuple[int, int, int]] = None
    semantic_label: Optional[str] = None
    confidence: float = 0.0


@dataclass
class SemanticObject:
    object_id: str
    label: str
    bounding_box: Tuple[float, float, float, float, float, float]
    center: Tuple[float, float, float]
    points: List[Tuple[float, float, float]]
    confidence: float


class OctreeNode:
    def __init__(self, center: Tuple[float, float, float], size: float):
        self.center = center
        self.size = size
        self.children: Optional[List["OctreeNode"]] = None
        self.voxel: Optional[Voxel] = None
        self.point_count: int = 0


class VoxelGrid:
    def __init__(
        self,
        resolution: float = 1.0,
        bounds: Tuple[float, float, float] = (100, 100, 50),
    ):
        self.resolution = resolution
        self.bounds = bounds
        self.voxels: Dict[Tuple[int, int, int], Voxel] = {}
        self.grid_size = (
            int(bounds[0] / resolution),
            int(bounds[1] / resolution),
            int(bounds[2] / resolution),
        )

    def world_to_voxel(
        self, position: Tuple[float, float, float]
    ) -> Tuple[int, int, int]:
        vx = int(position[0] / self.resolution)
        vy = int(position[1] / self.resolution)
        vz = int(position[2] / self.resolution)
        return (vx, vy, vz)

    def voxel_to_world(self, voxel: Tuple[int, int, int]) -> Tuple[float, float, float]:
        wx = voxel[0] * self.resolution + self.resolution / 2
        wy = voxel[1] * self.resolution + self.resolution / 2
        wz = voxel[2] * self.resolution + self.resolution / 2
        return (wx, wy, wz)

    def set_voxel(
        self, position: Tuple[float, float, float], state: int, probability: float = 0.5
    ):
        voxel_coord = self.world_to_voxel(position)

        if voxel_coord not in self.voxels:
            self.voxels[voxel_coord] = Voxel(position=voxel_coord)

        self.voxels[voxel_coord].state = state
        self.voxels[voxel_coord].probability = probability

    def get_voxel(self, position: Tuple[float, float, float]) -> Optional[Voxel]:
        voxel_coord = self.world_to_voxel(position)
        return self.voxels.get(voxel_coord)

    def ray_cast(
        self,
        origin: Tuple[float, float, float],
        direction: Tuple[float, float, float],
        max_distance: float = 100.0,
    ) -> List[Tuple[float, float, float]]:
        hits = []
        step_size = self.resolution

        t = 0.0
        while t < max_distance:
            point = (
                origin[0] + direction[0] * t,
                origin[1] + direction[1] * t,
                origin[2] + direction[2] * t,
            )

            if not self.is_in_bounds(point):
                break

            voxel = self.get_voxel(point)
            if voxel and voxel.state == VoxelState.OCCUPIED:
                hits.append(point)
                break

            t += step_size

        return hits

    def is_in_bounds(self, position: Tuple[float, float, float]) -> bool:
        return (
            0 <= position[0] < self.bounds[0]
            and 0 <= position[1] < self.bounds[1]
            and 0 <= position[2] < self.bounds[2]
        )

    def get_occupancy_grid(self) -> np.ndarray:
        grid = np.full(self.grid_size, VoxelState.UNKNOWN)

        for (vx, vy, vz), voxel in self.voxels.items():
            if (
                0 <= vx < self.grid_size[0]
                and 0 <= vy < self.grid_size[1]
                and 0 <= vz < self.grid_size[2]
            ):
                grid[vx, vy, vz] = voxel.state

        return grid


class SemanticSegmenter:
    def __init__(self):
        self.class_names = [
            "building",
            "tree",
            "road",
            "vehicle",
            "person",
            "power_line",
            "structure",
            "water",
            "grass",
            "unknown",
        ]

        self.color_map = {
            "building": (128, 64, 128),
            "tree": (0, 255, 0),
            "road": (64, 64, 64),
            "vehicle": (255, 0, 0),
            "person": (255, 255, 0),
            "power_line": (128, 128, 0),
            "structure": (0, 128, 128),
            "water": (0, 0, 255),
            "grass": (0, 255, 128),
            "unknown": (128, 128, 128),
        }

    def segment_point(
        self, point: Tuple[float, float, float], features: Dict
    ) -> Tuple[str, float]:
        height = point[2]

        if height < 2:
            return "road", 0.9
        elif height < 5:
            return "vehicle", 0.7
        elif height < 20:
            return "building", 0.8
        elif height < 40:
            return "tree", 0.85
        else:
            return "unknown", 0.5

    def segment_pointcloud(
        self, points: List[Tuple[float, float, float]]
    ) -> List[SemanticObject]:
        clusters = self._cluster_points(points)

        objects = []
        for i, cluster in enumerate(clusters):
            if len(cluster) < 10:
                continue

            center = np.mean(cluster, axis=0)

            min_coords = np.min(cluster, axis=0)
            max_coords = np.max(cluster, axis=0)
            bbox = (*min_coords, *max_coords)

            label, confidence = self.segment_point(tuple(center), {})

            obj = SemanticObject(
                object_id=f"obj_{i}",
                label=label,
                bounding_box=bbox,
                center=tuple(center),
                points=cluster,
                confidence=confidence,
            )
            objects.append(obj)

        return objects

    def _cluster_points(
        self, points: List[Tuple[float, float, float]], eps: float = 2.0
    ) -> List[List[Tuple[float, float, float]]]:
        if not points:
            return []

        points_array = np.array(points)
        n = len(points_array)
        visited = [False] * n
        clusters = []

        for i in range(n):
            if visited[i]:
                continue

            cluster = []
            queue = [i]
            visited[i] = True

            while queue:
                idx = queue.pop(0)
                cluster.append(tuple(points_array[idx]))

                for j in range(n):
                    if not visited[j]:
                        dist = np.linalg.norm(points_array[idx] - points_array[j])
                        if dist < eps:
                            visited[j] = True
                            queue.append(j)

            if cluster:
                clusters.append(cluster)

        return clusters


class SemanticMapBuilder:
    def __init__(self, resolution: float = 1.0):
        self.voxel_grid = VoxelGrid(resolution)
        self.segmenter = SemanticSegmenter()

        self.semantic_objects: Dict[str, SemanticObject] = {}
        self.timestamped_updates: List[Dict] = []

    def update_from_lidar(
        self, points: List[Tuple[float, float, float]], timestamp: float
    ):
        for point in points:
            if self.voxel_grid.is_in_bounds(point):
                self.voxel_grid.set_voxel(point, VoxelState.OCCUPIED, 0.9)

        objects = self.segmenter.segment_pointcloud(points)

        for obj in objects:
            self.semantic_objects[obj.object_id] = obj

        self.timestamped_updates.append(
            {
                "timestamp": timestamp,
                "num_points": len(points),
                "num_objects": len(objects),
            }
        )

    def update_from_camera(self, detections: List[Dict], timestamp: float):
        for det in detections:
            label = det.get("label", "unknown")
            bbox = det.get("bbox")
            confidence = det.get("confidence", 0.5)

            if bbox:
                x_min, y_min, x_max, y_max = bbox
                center = (
                    (x_min + x_max) / 2,
                    (y_min + y_max) / 2,
                    det.get("depth", 10),
                )

                obj = SemanticObject(
                    object_id=f"cam_{det.get('id', 0)}",
                    label=label,
                    bounding_box=(x_min, y_min, x_max, y_max, 0, 0),
                    center=center,
                    points=[],
                    confidence=confidence,
                )

                self.semantic_objects[obj.object_id] = obj

    def raycast_update(
        self,
        sensor_position: Tuple[float, float, float],
        directions: List[Tuple[float, float, float]],
    ):
        for direction in directions:
            hits = self.voxel_grid.ray_cast(sensor_position, direction)

            t = 0.0
            for point in hits:
                self.voxel_grid.set_voxel(point, VoxelState.OCCUPIED, 0.9)

            if hits:
                endpoint = hits[0]
            else:
                max_dist = 100.0
                endpoint = (
                    sensor_position[0] + direction[0] * max_dist,
                    sensor_position[1] + direction[1] * max_dist,
                    sensor_position[2] + direction[2] * max_dist,
                )

            num_steps = int(
                np.linalg.norm(np.array(endpoint) - np.array(sensor_position))
                / self.voxel_grid.resolution
            )
            for i in range(num_steps):
                point = (
                    sensor_position[0] + direction[0] * i * self.voxel_grid.resolution,
                    sensor_position[1] + direction[1] * i * self.voxel_grid.resolution,
                    sensor_position[2] + direction[2] * i * self.voxel_grid.resolution,
                )
                if self.voxel_grid.is_in_bounds(point) and point != endpoint:
                    self.voxel_grid.set_voxel(point, VoxelState.FREE, 0.9)

    def get_map_summary(self) -> Dict:
        voxel_counts = defaultdict(int)
        for voxel in self.voxel_grid.voxels.values():
            voxel_counts[voxel.state] += 1

        label_counts = defaultdict(int)
        for obj in self.semantic_objects.values():
            label_counts[obj.label] += 1

        return {
            "total_voxels": len(self.voxel_grid.voxels),
            "free_voxels": voxel_counts[VoxelState.FREE],
            "occupied_voxels": voxel_counts[VoxelState.OCCUPIED],
            "unknown_voxels": voxel_counts[VoxelState.UNKNOWN],
            "semantic_objects": len(self.semantic_objects),
            "label_distribution": dict(label_counts),
            "updates": len(self.timestamped_updates),
        }


def simulate_semantic_mapping():
    map_builder = SemanticMapBuilder(resolution=1.0)

    print("=== Semantic Map Building Simulation ===")

    for frame in range(10):
        num_points = np.random.randint(100, 500)

        points = []
        for _ in range(num_points):
            x = np.random.uniform(0, 50)
            y = np.random.uniform(0, 50)
            z = np.random.uniform(0, 30)

            if np.random.random() < 0.1:
                z = np.random.uniform(15, 25)

            points.append((x, y, z))

        map_builder.update_from_lidar(points, timestamp=frame * 0.1)

        if frame % 3 == 0:
            detections = [
                {
                    "id": 0,
                    "label": "building",
                    "bbox": (10, 10, 30, 30),
                    "confidence": 0.9,
                    "depth": 20,
                },
                {
                    "id": 1,
                    "label": "vehicle",
                    "bbox": (40, 40, 50, 50),
                    "confidence": 0.8,
                    "depth": 15,
                },
            ]
            map_builder.update_from_camera(detections, timestamp=frame * 0.1)

        if frame % 5 == 0:
            sensor_pos = (25, 25, 25)
            directions = [
                (np.cos(a) * np.sin(b), np.sin(a) * np.sin(b), np.cos(b))
                for a in np.linspace(0, 2 * np.pi, 8)
                for b in np.linspace(0, np.pi / 2, 4)
            ]
            map_builder.raycast_update(sensor_pos, directions)

        if frame % 2 == 0:
            summary = map_builder.get_map_summary()
            print(
                f"Frame {frame}: {summary['occupied_voxels']} occupied, {summary['semantic_objects']} objects"
            )

    final_summary = map_builder.get_map_summary()
    print(f"\n=== Final Map Summary ===")
    print(f"Total Voxels: {final_summary['total_voxels']}")
    print(f"Occupied: {final_summary['occupied_voxels']}")
    print(f"Semantic Objects: {final_summary['semantic_objects']}")
    print(f"Labels: {final_summary['label_distribution']}")

    return final_summary


if __name__ == "__main__":
    simulate_semantic_mapping()
