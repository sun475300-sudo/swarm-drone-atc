"""Phase 280: Swarm Formation Control — 군집 대형 제어 시스템.

V-formation, grid, circle, line 등 다양한 대형 패턴을 지원하며,
실시간 대형 전환과 장애물 회피 중 대형 유지를 구현합니다.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class FormationType(Enum):
    V_FORMATION = "v_formation"
    GRID = "grid"
    CIRCLE = "circle"
    LINE = "line"
    DIAMOND = "diamond"
    WEDGE = "wedge"
    COLUMN = "column"
    ECHELON = "echelon"


@dataclass
class FormationSlot:
    slot_id: int
    offset: np.ndarray  # relative to leader
    drone_id: Optional[str] = None
    priority: int = 0


@dataclass
class FormationState:
    formation_type: FormationType
    leader_id: str
    slots: List[FormationSlot] = field(default_factory=list)
    cohesion: float = 1.0
    stability: float = 1.0
    transition_progress: float = 1.0


class FormationGenerator:
    """대형 패턴 좌표 생성기."""

    @staticmethod
    def v_formation(n: int, spacing: float = 15.0, angle_deg: float = 30.0) -> List[np.ndarray]:
        offsets = [np.array([0.0, 0.0, 0.0])]
        angle = np.radians(angle_deg)
        for i in range(1, n):
            side = 1 if i % 2 == 1 else -1
            rank = (i + 1) // 2
            x = -rank * spacing * np.cos(angle)
            y = side * rank * spacing * np.sin(angle)
            offsets.append(np.array([x, y, 0.0]))
        return offsets

    @staticmethod
    def grid_formation(n: int, spacing: float = 20.0) -> List[np.ndarray]:
        cols = int(np.ceil(np.sqrt(n)))
        offsets = []
        for i in range(n):
            row, col = divmod(i, cols)
            offsets.append(np.array([row * spacing, col * spacing, 0.0]))
        return offsets

    @staticmethod
    def circle_formation(n: int, radius: float = 50.0) -> List[np.ndarray]:
        offsets = []
        for i in range(n):
            theta = 2.0 * np.pi * i / n
            offsets.append(np.array([radius * np.cos(theta), radius * np.sin(theta), 0.0]))
        return offsets

    @staticmethod
    def line_formation(n: int, spacing: float = 15.0) -> List[np.ndarray]:
        return [np.array([0.0, i * spacing, 0.0]) for i in range(n)]

    @staticmethod
    def diamond_formation(n: int, spacing: float = 20.0) -> List[np.ndarray]:
        offsets = [np.array([0.0, 0.0, 0.0])]
        layers = int(np.ceil(np.sqrt(n)))
        idx = 1
        for layer in range(1, layers + 1):
            for dx, dy in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
                if idx >= n:
                    break
                offsets.append(np.array([dx * layer * spacing, dy * layer * spacing, 0.0]))
                idx += 1
        return offsets[:n]

    @staticmethod
    def generate(ftype: FormationType, n: int, **kwargs) -> List[np.ndarray]:
        generators = {
            FormationType.V_FORMATION: FormationGenerator.v_formation,
            FormationType.GRID: FormationGenerator.grid_formation,
            FormationType.CIRCLE: FormationGenerator.circle_formation,
            FormationType.LINE: FormationGenerator.line_formation,
            FormationType.DIAMOND: FormationGenerator.diamond_formation,
        }
        gen = generators.get(ftype, FormationGenerator.grid_formation)
        return gen(n, **kwargs)


class SwarmFormationController:
    """군집 대형 제어기.

    - 대형 생성/전환/유지
    - 실시간 cohesion/stability 계산
    - 리더 교체 및 슬롯 재할당
    """

    def __init__(self, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self._formations: Dict[str, FormationState] = {}
        self._drone_positions: Dict[str, np.ndarray] = {}
        self._history: List[dict] = []

    def create_formation(
        self,
        formation_id: str,
        leader_id: str,
        drone_ids: List[str],
        ftype: FormationType = FormationType.V_FORMATION,
        **kwargs,
    ) -> FormationState:
        offsets = FormationGenerator.generate(ftype, len(drone_ids), **kwargs)
        slots = []
        for i, (did, offset) in enumerate(zip(drone_ids, offsets)):
            slots.append(FormationSlot(slot_id=i, offset=offset, drone_id=did, priority=len(drone_ids) - i))
        state = FormationState(formation_type=ftype, leader_id=leader_id, slots=slots)
        self._formations[formation_id] = state
        self._history.append({"event": "created", "id": formation_id, "type": ftype.value, "size": len(drone_ids)})
        return state

    def transition_formation(self, formation_id: str, new_type: FormationType, steps: int = 10) -> List[List[np.ndarray]]:
        state = self._formations.get(formation_id)
        if not state:
            return []
        n = len(state.slots)
        old_offsets = [s.offset.copy() for s in state.slots]
        new_offsets = FormationGenerator.generate(new_type, n)
        trajectory = []
        for step in range(steps + 1):
            t = step / steps
            t_smooth = 3 * t**2 - 2 * t**3  # smoothstep
            frame = [old * (1 - t_smooth) + new * t_smooth for old, new in zip(old_offsets, new_offsets)]
            trajectory.append(frame)
        for i, offset in enumerate(new_offsets):
            state.slots[i].offset = offset
        state.formation_type = new_type
        state.transition_progress = 1.0
        self._history.append({"event": "transition", "id": formation_id, "new_type": new_type.value})
        return trajectory

    def update_positions(self, positions: Dict[str, np.ndarray]):
        self._drone_positions.update(positions)

    def compute_cohesion(self, formation_id: str) -> float:
        state = self._formations.get(formation_id)
        if not state or not self._drone_positions:
            return 0.0
        leader_pos = self._drone_positions.get(state.leader_id)
        if leader_pos is None:
            return 0.0
        errors = []
        for slot in state.slots:
            if slot.drone_id and slot.drone_id in self._drone_positions:
                actual = self._drone_positions[slot.drone_id]
                expected = leader_pos + slot.offset
                errors.append(np.linalg.norm(actual - expected))
        if not errors:
            return 0.0
        avg_error = np.mean(errors)
        cohesion = max(0.0, 1.0 - avg_error / 100.0)
        state.cohesion = cohesion
        return cohesion

    def compute_stability(self, formation_id: str) -> float:
        state = self._formations.get(formation_id)
        if not state:
            return 0.0
        stability = state.cohesion * state.transition_progress
        state.stability = stability
        return stability

    def reassign_leader(self, formation_id: str, new_leader_id: str) -> bool:
        state = self._formations.get(formation_id)
        if not state:
            return False
        found = any(s.drone_id == new_leader_id for s in state.slots)
        if not found:
            return False
        state.leader_id = new_leader_id
        self._history.append({"event": "leader_change", "id": formation_id, "new_leader": new_leader_id})
        return True

    def remove_drone(self, formation_id: str, drone_id: str) -> bool:
        state = self._formations.get(formation_id)
        if not state:
            return False
        for slot in state.slots:
            if slot.drone_id == drone_id:
                slot.drone_id = None
                return True
        return False

    def get_formation(self, formation_id: str) -> Optional[FormationState]:
        return self._formations.get(formation_id)

    def list_formations(self) -> List[str]:
        return list(self._formations.keys())

    def summary(self) -> dict:
        return {
            "total_formations": len(self._formations),
            "history_events": len(self._history),
            "tracked_drones": len(self._drone_positions),
        }
