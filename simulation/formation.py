"""
군집드론 편대 비행 알고리즘
=========================
Formation 패턴 정의 + 리더-팔로워 프로토콜 + 동적 대형 전환.

패턴:
  - V자 (V_SHAPE): 리더 선두, 팔로워 좌우 날개
  - 라인 (LINE): 일렬 종대
  - 서클 (CIRCLE): 원형 배치
  - 그리드 (GRID): 격자형 배치

사용법:
    fc = FormationController(pattern="V_SHAPE", spacing=80.0)
    offsets = fc.compute_offsets(n_followers=4)
    targets = fc.follower_targets(leader_pos, leader_heading, n_followers=4)
"""
from __future__ import annotations

import math
from enum import Enum
from typing import Optional

import numpy as np


class FormationPattern(str, Enum):
    """편대 패턴 종류"""
    V_SHAPE = "V_SHAPE"
    LINE = "LINE"
    CIRCLE = "CIRCLE"
    GRID = "GRID"


class FormationController:
    """
    편대 비행 제어기.

    리더 드론의 위치/방향에 따라 팔로워들의 목표 위치를 계산한다.
    """

    def __init__(
        self,
        pattern: str | FormationPattern = FormationPattern.V_SHAPE,
        spacing: float = 80.0,
        altitude_offset: float = 0.0,
    ) -> None:
        """
        Parameters
        ----------
        pattern : 편대 패턴
        spacing : 드론 간 간격 (m)
        altitude_offset : 팔로워 고도 오프셋 (m, 음수=낮게)
        """
        self.pattern = FormationPattern(pattern)
        self.spacing = spacing
        self.altitude_offset = altitude_offset

    def compute_offsets(self, n_followers: int) -> list[np.ndarray]:
        """
        편대 패턴에 따른 로컬 오프셋 벡터 계산.

        리더 기준 상대 위치 (x=전방, y=좌측, z=위).
        """
        if n_followers <= 0:
            return []

        s = self.spacing
        az = self.altitude_offset

        if self.pattern == FormationPattern.V_SHAPE:
            offsets = []
            for i in range(n_followers):
                rank = (i // 2) + 1
                side = -1 if i % 2 == 0 else 1
                x_off = -rank * s * 0.7   # 뒤쪽
                y_off = side * rank * s * 0.5
                offsets.append(np.array([x_off, y_off, az * rank]))
            return offsets

        elif self.pattern == FormationPattern.LINE:
            return [
                np.array([-(i + 1) * s, 0.0, az * (i + 1)])
                for i in range(n_followers)
            ]

        elif self.pattern == FormationPattern.CIRCLE:
            offsets = []
            for i in range(n_followers):
                angle = 2 * math.pi * i / n_followers
                x_off = s * math.cos(angle)
                y_off = s * math.sin(angle)
                offsets.append(np.array([x_off, y_off, az]))
            return offsets

        elif self.pattern == FormationPattern.GRID:
            cols = max(1, int(math.ceil(math.sqrt(n_followers))))
            offsets = []
            for i in range(n_followers):
                row = i // cols
                col = i % cols
                x_off = -(row + 1) * s
                y_off = (col - cols // 2) * s
                offsets.append(np.array([x_off, y_off, az]))
            return offsets

        return []

    def follower_targets(
        self,
        leader_pos: np.ndarray,
        leader_heading_rad: float,
        n_followers: int,
    ) -> list[np.ndarray]:
        """
        리더 위치와 방향에 따라 팔로워들의 월드 좌표 목표 위치 계산.

        Parameters
        ----------
        leader_pos : 리더 위치 [x, y, z]
        leader_heading_rad : 리더 기수 방향 (라디안, 0=동, pi/2=북)
        n_followers : 팔로워 수

        Returns
        -------
        list[np.ndarray] : 팔로워별 목표 위치 [x, y, z]
        """
        offsets = self.compute_offsets(n_followers)
        cos_h = math.cos(leader_heading_rad)
        sin_h = math.sin(leader_heading_rad)

        # 2D 회전 행렬 (기수 방향으로)
        rot = np.array([
            [cos_h, -sin_h],
            [sin_h,  cos_h],
        ])

        targets = []
        for off in offsets:
            rotated_xy = rot @ off[:2]
            world_pos = leader_pos.copy()
            world_pos[0] += rotated_xy[0]
            world_pos[1] += rotated_xy[1]
            world_pos[2] += off[2]
            targets.append(world_pos)

        return targets

    def change_pattern(self, new_pattern: str | FormationPattern) -> None:
        """편대 패턴 동적 변경"""
        self.pattern = FormationPattern(new_pattern)

    def compute_follow_velocity(
        self,
        follower_pos: np.ndarray,
        target_pos: np.ndarray,
        max_speed: float = 15.0,
        gain: float = 0.8,
    ) -> np.ndarray:
        """
        팔로워가 목표 위치로 이동하기 위한 속도 벡터 계산.

        비례 제어 (P-controller) 기반.
        """
        diff = target_pos - follower_pos
        dist = float(np.linalg.norm(diff))

        if dist < 1.0:
            return np.zeros(3)

        direction = diff / dist
        speed = min(dist * gain, max_speed)
        return direction * speed

    def should_break_formation(
        self,
        follower_pos: np.ndarray,
        target_pos: np.ndarray,
        threat_distance: float = 50.0,
        obstacles: list[np.ndarray] | None = None,
    ) -> bool:
        """
        장애물/위협 근접 시 편대 해체 필요 여부 판단.

        팔로워 위치에서 threat_distance 내 장애물이 있으면 True.
        """
        if not obstacles:
            return False

        for obs in obstacles:
            dist = float(np.linalg.norm(follower_pos[:2] - obs[:2]))
            if dist < threat_distance:
                return True

        return False
