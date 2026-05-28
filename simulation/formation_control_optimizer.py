"""
Phase 439: Formation Control Optimizer for Coordinated Flight
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class FormationConfig:
    """``FormationConfig`` 데이터를 표현한다."""
    formation_type: str
    spacing: float
    altitude_diff: float


class FormationControlOptimizer:
    """``FormationControlOptimizer`` 관련 기능을 제공한다."""
    def __init__(self, formation_type: str = "wedge"):
        """인스턴스를 초기화한다."""
        self.formation_type = formation_type

    def compute_formation_positions(
        self,
        leader_pos: np.ndarray,
        num_drones: int,
        config: FormationConfig,
    ) -> list[np.ndarray]:
        """`formation positions` 값을 계산한다."""
        positions = [leader_pos.copy()]

        if config.formation_type == "wedge":
            for i in range(1, num_drones):
                row = i // 2 + 1
                col = (-1) ** i
                offset = np.array([row * config.spacing, col * config.spacing, 0])
                positions.append(leader_pos + offset)

        elif config.formation_type == "line":
            for i in range(1, num_drones):
                offset = np.array([i * config.spacing, 0, 0])
                positions.append(leader_pos + offset)

        elif config.formation_type == "circle":
            for i in range(1, num_drones):
                angle = 2 * np.pi * i / num_drones
                offset = np.array(
                    [config.spacing * np.cos(angle), config.spacing * np.sin(angle), 0]
                )
                positions.append(leader_pos + offset)

        return positions

    def compute_control_inputs(
        self,
        current_positions: list[np.ndarray],
        target_positions: list[np.ndarray],
        velocities: list[np.ndarray],
        gains: dict[str, float],
    ) -> list[np.ndarray]:
        """`control inputs` 값을 계산한다."""
        controls = []

        for i in range(len(current_positions)):
            error = target_positions[i] - current_positions[i]

            kp = gains.get("kp", 1.0)
            kd = gains.get("kd", 0.5)

            control = kp * error + kd * velocities[i]

            max_control = 20.0
            norm = np.linalg.norm(control)
            if norm > max_control:
                control = control / norm * max_control

            controls.append(control)

        return controls

    def maintain_connectivity(
        self,
        positions: list[np.ndarray],
        min_distance: float = 10.0,
    ) -> bool:
        """``maintain_connectivity`` 동작을 수행한다."""
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                dist = np.linalg.norm(positions[i] - positions[j])
                if dist > min_distance:
                    return False
        return True
