"""Phase 307: AR/VR Visualization Bridge — AR/VR 시각화 브릿지.

WebXR/Unity/Unreal 연동을 위한 장면 그래프 직렬화,
실시간 드론 위치 스트리밍, 인터랙션 이벤트 처리.
"""

from __future__ import annotations

import logging
import numpy as np
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

_logger = logging.getLogger(__name__)


class RenderPrimitive(Enum):
    SPHERE = "sphere"
    CUBE = "cube"
    CYLINDER = "cylinder"
    ARROW = "arrow"
    LINE = "line"
    TEXT = "text"
    MODEL_3D = "model_3d"


class InteractionType(Enum):
    SELECT = "select"
    HOVER = "hover"
    GRAB = "grab"
    TELEPORT = "teleport"
    GAZE = "gaze"


@dataclass
class SceneObject:
    obj_id: str
    primitive: RenderPrimitive
    position: np.ndarray
    rotation: np.ndarray = field(default_factory=lambda: np.zeros(3))
    scale: np.ndarray = field(default_factory=lambda: np.ones(3))
    color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    metadata: dict = field(default_factory=dict)
    visible: bool = True
    interactive: bool = False


@dataclass
class InteractionEvent:
    event_type: InteractionType
    target_id: str
    controller: str = "right"  # left/right/gaze
    position: Optional[np.ndarray] = None
    timestamp: float = 0.0


@dataclass
class SceneFrame:
    frame_id: int
    timestamp: float
    objects: List[dict] = field(default_factory=list)
    camera_position: np.ndarray = field(default_factory=lambda: np.array([0, 0, 100]))
    camera_target: np.ndarray = field(default_factory=lambda: np.zeros(3))


class ARVRBridge:
    """AR/VR 시각화 브릿지.

    - 장면 그래프 관리
    - 실시간 프레임 직렬화 (JSON)
    - 인터랙션 이벤트 처리
    - 드론 위치 → 3D 오브젝트 매핑
    """

    DRONE_COLORS = {
        "normal": (0.0, 0.7, 1.0, 1.0),
        "warning": (1.0, 0.7, 0.0, 1.0),
        "critical": (1.0, 0.0, 0.0, 1.0),
        "inactive": (0.5, 0.5, 0.5, 0.5),
    }

    def __init__(self):
        self._objects: Dict[str, SceneObject] = {}
        self._interaction_log: List[InteractionEvent] = []
        self._frame_count = 0
        self._callbacks: Dict[InteractionType, List] = {}

    def add_object(self, obj: SceneObject):
        self._objects[obj.obj_id] = obj

    def remove_object(self, obj_id: str) -> bool:
        return self._objects.pop(obj_id, None) is not None

    def update_drone_positions(self, positions: Dict[str, np.ndarray],
                                statuses: Optional[Dict[str, str]] = None):
        statuses = statuses or {}
        for drone_id, pos in positions.items():
            status = statuses.get(drone_id, "normal")
            color = self.DRONE_COLORS.get(status, self.DRONE_COLORS["normal"])
            if drone_id in self._objects:
                self._objects[drone_id].position = pos
                self._objects[drone_id].color = color
            else:
                self.add_object(SceneObject(
                    obj_id=drone_id, primitive=RenderPrimitive.SPHERE,
                    position=pos, scale=np.array([2.0, 2.0, 2.0]),
                    color=color, interactive=True,
                    metadata={"type": "drone", "status": status},
                ))

    def add_trajectory(self, drone_id: str, waypoints: List[np.ndarray], color: Tuple = (0.0, 1.0, 0.0, 0.5)):
        for i, wp in enumerate(waypoints):
            obj = SceneObject(
                obj_id=f"{drone_id}_wp_{i}", primitive=RenderPrimitive.SPHERE,
                position=wp, scale=np.array([0.5, 0.5, 0.5]), color=color,
                metadata={"type": "waypoint", "drone": drone_id, "index": i},
            )
            self._objects[obj.obj_id] = obj

    def add_zone(self, zone_id: str, center: np.ndarray, radius: float,
                 color: Tuple = (1.0, 0.0, 0.0, 0.2)):
        obj = SceneObject(
            obj_id=zone_id, primitive=RenderPrimitive.CYLINDER,
            position=center, scale=np.array([radius, 100.0, radius]),
            color=color, metadata={"type": "zone"},
        )
        self._objects[obj.obj_id] = obj

    def generate_frame(self, timestamp: float = 0.0) -> SceneFrame:
        self._frame_count += 1
        objects_data = []
        for obj in self._objects.values():
            if not obj.visible:
                continue
            objects_data.append({
                "id": obj.obj_id,
                "primitive": obj.primitive.value,
                "position": obj.position.tolist(),
                "rotation": obj.rotation.tolist(),
                "scale": obj.scale.tolist(),
                "color": list(obj.color),
                "metadata": obj.metadata,
                "interactive": obj.interactive,
            })
        return SceneFrame(
            frame_id=self._frame_count, timestamp=timestamp,
            objects=objects_data,
        )

    def serialize_frame(self, frame: SceneFrame) -> str:
        return json.dumps({
            "frameId": frame.frame_id,
            "timestamp": frame.timestamp,
            "objects": frame.objects,
            "camera": {
                "position": frame.camera_position.tolist(),
                "target": frame.camera_target.tolist(),
            },
        })

    def handle_interaction(self, event: InteractionEvent):
        self._interaction_log.append(event)
        callbacks = self._callbacks.get(event.event_type, [])
        for cb in callbacks:
            try:
                cb(event)
            except Exception as exc:
                # 단일 callback 실패가 다른 callback 차단을 막지 않도록 swallow 유지하되,
                # silent 는 디버깅을 어렵게 하므로 WARN 로그.
                _logger.warning(
                    "ar/vr interaction callback failed for %s: %s",
                    event.event_type, exc, exc_info=True,
                )

    def on_interaction(self, event_type: InteractionType, callback):
        self._callbacks.setdefault(event_type, []).append(callback)

    def get_object(self, obj_id: str) -> Optional[SceneObject]:
        return self._objects.get(obj_id)

    def summary(self) -> dict:
        types = {}
        for obj in self._objects.values():
            types[obj.primitive.value] = types.get(obj.primitive.value, 0) + 1
        return {
            "total_objects": len(self._objects),
            "object_types": types,
            "frame_count": self._frame_count,
            "interactions": len(self._interaction_log),
        }
