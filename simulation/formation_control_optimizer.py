"""
Phase 439: Formation Control Optimizer for Coordinated Flight
"""

import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class FormationConfig:
    formation_type: str
    spacing: float
    altitude_diff: float


class FormationControlOptimizer:
    def __init__(self, formation_type: str = "wedge"):
        self.formation_type = formation_type

    def compute_formation_positions(
        self,
        leader_pos: np.ndarray,
        num_drones: int,
        config: FormationConfig,
    ) -> List[np.ndarray]:
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
        current_positions: List[np.ndarray],
        target_positions: List[np.ndarray],
        velocities: List[np.ndarray],
        gains: Dict[str, float],
    ) -> List[np.ndarray]:
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
        positions: List[np.ndarray],
        min_distance: float = 10.0,
    ) -> bool:
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                dist = np.linalg.norm(positions[i] - positions[j])
                if dist > min_distance:
                    return False
        return True
