"""
Phase 421: AR/VR Interface Engine
AR/VR interface for drone swarm visualization and control.
"""

import numpy as np
import json
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Any, Callable


class RealityMode(Enum):
    """Reality mode types."""

    AR = auto()
    VR = auto()
    MIXED = auto()
    PASSTHROUGH = auto()


class RenderMode(Enum):
    """Render modes."""

    WIREFRAME = auto()
    SOLID = auto()
    TEXTURED = auto()
    HOLOGRAPHIC = auto()
    XRAY = auto()


class InteractionMode(Enum):
    """Interaction modes."""

    GAZE = auto()
    CONTROLLER = auto()
    HAND_TRACKING = auto()
    VOICE = auto()
    GESTURE = auto()


@dataclass
class Transform3D:
    """3D transformation."""

    position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    rotation: np.ndarray = field(default_factory=lambda: np.zeros(3))
    scale: np.ndarray = field(default_factory=lambda: np.ones(3))

    def to_matrix(self) -> np.ndarray:
        cx, cy, cz = np.cos(self.rotation)
        sx, sy, sz = np.sin(self.rotation)
        R = np.array(
            [
                [cy * cz, sx * sy * cz - cx * sz, cx * sy * cz + sx * sz],
                [cy * sz, sx * sy * sz + cx * cz, cx * sy * sz - sx * cz],
                [-sy, sx * cy, cx * cy],
            ]
        )
        T = np.eye(4)
        T[:3, :3] = R * self.scale
        T[:3, 3] = self.position
        return T


@dataclass
class ARObject:
    """AR/VR object."""

    obj_id: str
    obj_type: str
    transform: Transform3D = field(default_factory=Transform3D)
    color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    visible: bool = True
    interactive: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ARScene:
    """AR/VR scene."""

    scene_id: str
    objects: Dict[str, ARObject] = field(default_factory=dict)
    lights: List[Dict[str, Any]] = field(default_factory=list)
    camera_transform: Transform3D = field(default_factory=Transform3D)
    skybox: Optional[str] = None
    ambient_color: Tuple[float, float, float] = (0.2, 0.2, 0.2)


@dataclass
class HapticFeedback:
    """Haptic feedback data."""

    controller: str
    intensity: float
    duration_ms: float
    pattern: str = "pulse"


@dataclass
class SpatialAnchor:
    """Spatial anchor for AR."""

    anchor_id: str
    position: np.ndarray
    rotation: np.ndarray
    confidence: float = 1.0
    persistent: bool = True


class AREngine:
    """AR rendering and interaction engine."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.scene = ARScene("main")
        self.anchors: Dict[str, SpatialAnchor] = {}
        self.interaction_callbacks: Dict[str, List[Callable]] = {}
        self.render_mode = RenderMode.SOLID
        self.reality_mode = RealityMode.AR
        self.frame_count = 0
        self.fps = 60.0

    def create_drone_object(
        self,
        drone_id: str,
        position: np.ndarray,
        color: Tuple[float, float, float, float] = (0, 1, 0, 1),
    ) -> ARObject:
        obj = ARObject(
            obj_id=f"drone_{drone_id}",
            obj_type="drone",
            transform=Transform3D(position=position.copy()),
            color=color,
            interactive=True,
            metadata={"drone_id": drone_id, "status": "active"},
        )
        self.scene.objects[obj.obj_id] = obj
        return obj

    def create_airspace_volume(
        self,
        zone_id: str,
        center: np.ndarray,
        radius: float,
        color: Tuple[float, float, float, float] = (1, 0, 0, 0.3),
    ) -> ARObject:
        obj = ARObject(
            obj_id=f"zone_{zone_id}",
            obj_type="airspace_zone",
            transform=Transform3D(
                position=center.copy(), scale=np.array([radius, radius, radius])
            ),
            color=color,
            metadata={"zone_id": zone_id, "radius": radius},
        )
        self.scene.objects[obj.obj_id] = obj
        return obj

    def create_waypoint_marker(
        self, waypoint_id: str, position: np.ndarray
    ) -> ARObject:
        obj = ARObject(
            obj_id=f"waypoint_{waypoint_id}",
            obj_type="waypoint",
            transform=Transform3D(position=position.copy()),
            color=(0, 0, 1, 0.8),
            interactive=True,
        )
        self.scene.objects[obj.obj_id] = obj
        return obj

    def create_flight_path(
        self,
        path_id: str,
        waypoints: List[np.ndarray],
        color: Tuple[float, float, float, float] = (1, 1, 0, 0.7),
    ) -> List[ARObject]:
        objects = []
        for i in range(len(waypoints) - 1):
            obj = ARObject(
                obj_id=f"path_{path_id}_{i}",
                obj_type="path_segment",
                transform=Transform3D(position=waypoints[i]),
                color=color,
                metadata={
                    "start": waypoints[i].tolist(),
                    "end": waypoints[i + 1].tolist(),
                },
            )
            objects.append(obj)
            self.scene.objects[obj.obj_id] = obj
        return objects

    def create_hud_overlay(self, data: Dict[str, Any]) -> ARObject:
        obj = ARObject(
            obj_id="hud_overlay",
            obj_type="hud",
            transform=Transform3D(position=np.array([0, 0, -2])),
            color=(1, 1, 1, 0.9),
            metadata=data,
        )
        self.scene.objects[obj.obj_id] = obj
        return obj

    def update_drone_position(
        self, drone_id: str, position: np.ndarray, rotation: np.ndarray = None
    ) -> None:
        obj_id = f"drone_{drone_id}"
        if obj_id in self.scene.objects:
            self.scene.objects[obj_id].transform.position = position.copy()
            if rotation is not None:
                self.scene.objects[obj_id].transform.rotation = rotation.copy()

    def create_spatial_anchor(
        self, position: np.ndarray, rotation: np.ndarray = None
    ) -> SpatialAnchor:
        if rotation is None:
            rotation = np.zeros(3)
        anchor_id = f"anchor_{len(self.anchors)}"
        anchor = SpatialAnchor(anchor_id, position.copy(), rotation.copy())
        self.anchors[anchor_id] = anchor
        return anchor

    def register_interaction(self, event_type: str, callback: Callable) -> None:
        if event_type not in self.interaction_callbacks:
            self.interaction_callbacks[event_type] = []
        self.interaction_callbacks[event_type].append(callback)

    def handle_interaction(
        self, event_type: str, obj_id: str, data: Dict[str, Any]
    ) -> List[Any]:
        results = []
        for callback in self.interaction_callbacks.get(event_type, []):
            result = callback(obj_id, data)
            results.append(result)
        return results

    def render_frame(self) -> Dict[str, Any]:
        self.frame_count += 1
        visible_objects = [
            {
                "id": obj_id,
                "type": obj.obj_type,
                "position": obj.transform.position.tolist(),
                "color": obj.color,
            }
            for obj_id, obj in self.scene.objects.items()
            if obj.visible
        ]
        return {
            "frame": self.frame_count,
            "objects": visible_objects,
            "camera": self.scene.camera_transform.position.tolist(),
            "fps": self.fps,
            "mode": self.reality_mode.name,
        }

    def get_scene_stats(self) -> Dict[str, Any]:
        return {
            "total_objects": len(self.scene.objects),
            "visible_objects": sum(1 for o in self.scene.objects.values() if o.visible),
            "interactive_objects": sum(
                1 for o in self.scene.objects.values() if o.interactive
            ),
            "anchors": len(self.anchors),
            "frame_count": self.frame_count,
        }


class VREngine:
    """VR simulation engine."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.scene = ARScene("vr_main")
        self.user_transform = Transform3D()
        self.controllers: Dict[str, Transform3D] = {
            "left": Transform3D(),
            "right": Transform3D(),
        }
        self.haptics: List[HapticFeedback] = []
        self.teleport_targets: Dict[str, np.ndarray] = {}
        self.immersive_mode = True

    def set_user_position(self, position: np.ndarray) -> None:
        self.user_transform.position = position.copy()

    def set_controller_transform(self, controller: str, transform: Transform3D) -> None:
        self.controllers[controller] = transform

    def create_immersive_environment(self, env_type: str = "control_room") -> ARScene:
        if env_type == "control_room":
            self._create_control_room()
        elif env_type == "open_sky":
            self._create_open_sky()
        elif env_type == "command_center":
            self._create_command_center()
        return self.scene

    def _create_control_room(self) -> None:
        floor = ARObject(
            "floor",
            "plane",
            Transform3D(position=np.array([0, -1, 0]), scale=np.array([10, 0.1, 10])),
            color=(0.3, 0.3, 0.3, 1),
        )
        self.scene.objects["floor"] = floor
        screen = ARObject(
            "main_screen",
            "screen",
            Transform3D(position=np.array([0, 1, -5]), scale=np.array([4, 2.25, 0.1])),
            color=(0.1, 0.1, 0.1, 1),
            interactive=True,
        )
        self.scene.objects["main_screen"] = screen

    def _create_open_sky(self) -> None:
        ground = ARObject(
            "ground",
            "plane",
            Transform3D(
                position=np.array([0, -50, 0]), scale=np.array([1000, 1, 1000])
            ),
            color=(0.2, 0.5, 0.2, 1),
        )
        self.scene.objects["ground"] = ground

    def _create_command_center(self) -> None:
        desk = ARObject(
            "desk",
            "cube",
            Transform3D(position=np.array([0, 0, -1]), scale=np.array([2, 0.1, 1])),
            color=(0.4, 0.2, 0.1, 1),
        )
        self.scene.objects["desk"] = desk

    def teleport(self, target_id: str) -> bool:
        if target_id in self.teleport_targets:
            self.user_transform.position = self.teleport_targets[target_id].copy()
            return True
        return False

    def add_teleport_target(self, target_id: str, position: np.ndarray) -> None:
        self.teleport_targets[target_id] = position.copy()

    def trigger_haptic(
        self, controller: str, intensity: float = 0.5, duration_ms: float = 100
    ) -> None:
        feedback = HapticFeedback(controller, intensity, duration_ms)
        self.haptics.append(feedback)

    def render_vr_frame(self) -> Dict[str, Any]:
        left_eye = self.user_transform.position + np.array([-0.03, 0, 0])
        right_eye = self.user_transform.position + np.array([0.03, 0, 0])
        return {
            "left_eye": left_eye.tolist(),
            "right_eye": right_eye.tolist(),
            "controllers": {
                name: t.position.tolist() for name, t in self.controllers.items()
            },
            "objects": len(self.scene.objects),
            "haptics": len(self.haptics),
        }


class MixedRealityEngine:
    """Mixed reality engine combining AR and VR."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.ar_engine = AREngine(seed)
        self.vr_engine = VREngine(seed)
        self.mode = RealityMode.MIXED
        self.passthrough_enabled = True
        self.depth_estimation: Dict[str, float] = {}

    def switch_mode(self, mode: RealityMode) -> None:
        self.mode = mode

    def create_mixed_drone_view(
        self, drone_id: str, position: np.ndarray, telemetry: Dict[str, Any]
    ) -> Dict[str, Any]:
        ar_obj = self.ar_engine.create_drone_object(drone_id, position)
        vr_obj = ARObject(
            f"vr_drone_{drone_id}",
            "drone",
            Transform3D(position=position),
            metadata=telemetry,
        )
        self.vr_engine.scene.objects[vr_obj.obj_id] = vr_obj
        return {
            "ar_object": ar_obj.obj_id,
            "vr_object": vr_obj.obj_id,
            "mode": self.mode.name,
        }

    def create_depth_layer(self, layer_id: str, depth: float) -> None:
        self.depth_estimation[layer_id] = depth

    def occlusion_handling(self, objects: List[ARObject]) -> List[ARObject]:
        sorted_objects = sorted(
            objects, key=lambda o: np.linalg.norm(o.transform.position)
        )
        return sorted_objects

    def render_mixed_frame(self) -> Dict[str, Any]:
        ar_frame = self.ar_engine.render_frame()
        vr_frame = self.vr_engine.render_vr_frame()
        return {
            "mode": self.mode.name,
            "passthrough": self.passthrough_enabled,
            "ar": ar_frame,
            "vr": vr_frame,
            "depth_layers": len(self.depth_estimation),
        }


class DroneARVRController:
    """AR/VR controller for drone operations."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.mr_engine = MixedRealityEngine(seed)
        self.drone_positions: Dict[str, np.ndarray] = {}
        self.selected_drone: Optional[str] = None

    def add_drone(self, drone_id: str, position: np.ndarray) -> None:
        self.drone_positions[drone_id] = position.copy()
        self.mr_engine.ar_engine.create_drone_object(drone_id, position)

    def update_drone_positions(self, positions: Dict[str, np.ndarray]) -> None:
        for drone_id, pos in positions.items():
            self.drone_positions[drone_id] = pos.copy()
            self.mr_engine.ar_engine.update_drone_position(drone_id, pos)

    def select_drone(self, drone_id: str) -> bool:
        if drone_id in self.drone_positions:
            self.selected_drone = drone_id
            self.mr_engine.vr_engine.trigger_haptic("right", 0.7, 150)
            return True
        return False

    def create_airspace_visualization(self, zones: List[Dict[str, Any]]) -> None:
        for zone in zones:
            self.mr_engine.ar_engine.create_airspace_volume(
                zone.get("id", "zone"),
                np.array(zone.get("center", [0, 0, 0])),
                zone.get("radius", 100),
                tuple(zone.get("color", [1, 0, 0, 0.3])),
            )

    def render_dashboard(self) -> Dict[str, Any]:
        hud_data = {
            "selected_drone": self.selected_drone,
            "total_drones": len(self.drone_positions),
            "mode": self.mr_engine.mode.name,
        }
        self.mr_engine.ar_engine.create_hud_overlay(hud_data)
        return self.mr_engine.render_mixed_frame()

    def get_control_stats(self) -> Dict[str, Any]:
        return {
            "drones": len(self.drone_positions),
            "selected": self.selected_drone,
            "ar_objects": len(self.mr_engine.ar_engine.scene.objects),
            "vr_objects": len(self.mr_engine.vr_engine.scene.objects),
        }


if __name__ == "__main__":
    controller = DroneARVRController(seed=42)
    for i in range(5):
        controller.add_drone(f"D{i:03d}", np.array([i * 100, 50, i * 50]))
    controller.create_airspace_visualization(
        [
            {
                "id": "airport",
                "center": [0, 0, 0],
                "radius": 5000,
                "color": [1, 0, 0, 0.3],
            }
        ]
    )
    controller.select_drone("D001")
    frame = controller.render_dashboard()
    print(f"Control stats: {controller.get_control_stats()}")
    print(f"Frame objects: {len(frame['ar']['objects'])}")
