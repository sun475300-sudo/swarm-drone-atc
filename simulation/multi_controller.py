"""
다중 컨트롤러 + 관제 구역 분할
================================
공역을 관제 구역(Sector)으로 분할하고
각 구역에 독립 ATC를 할당. 구역 경계 핸드오프 지원.

사용법:
    mcm = MultiControllerManager(bounds=5000.0, n_sectors=4)
    sector = mcm.assign_sector(drone_pos)
    mcm.handoff(drone_id, from_sector, to_sector)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class Sector:
    """관제 구역"""
    sector_id: str
    x_range: tuple[float, float]
    y_range: tuple[float, float]
    drones: set[str] = field(default_factory=set)

    # 구역별 메트릭
    conflicts: int = 0
    advisories: int = 0
    handoffs_in: int = 0
    handoffs_out: int = 0

    def contains(self, pos: np.ndarray) -> bool:
        """위치가 구역 내인지 판정"""
        return (self.x_range[0] <= pos[0] <= self.x_range[1]
                and self.y_range[0] <= pos[1] <= self.y_range[1])

    def center(self) -> np.ndarray:
        """구역 중심점"""
        cx = (self.x_range[0] + self.x_range[1]) / 2
        cy = (self.y_range[0] + self.y_range[1]) / 2
        return np.array([cx, cy, 0.0])

    def area_km2(self) -> float:
        """구역 면적 (km²)"""
        dx = (self.x_range[1] - self.x_range[0]) / 1000.0
        dy = (self.y_range[1] - self.y_range[0]) / 1000.0
        return dx * dy


class MultiControllerManager:
    """
    다중 관제 구역 관리자.

    공역을 n_sectors 개 구역으로 분할하고
    드론 위치에 따라 구역 할당 + 핸드오프를 수행.
    """

    def __init__(
        self,
        bounds: float = 5000.0,
        n_sectors: int = 4,
        handoff_margin: float = 100.0,
    ) -> None:
        """
        Parameters
        ----------
        bounds : 공역 반경 (±bounds)
        n_sectors : 구역 수 (4 또는 9)
        handoff_margin : 핸드오프 마진 (m, 구역 경계 이 거리 내 진입 시)
        """
        self.bounds = bounds
        self.handoff_margin = handoff_margin
        self.sectors: dict[str, Sector] = {}
        self._drone_sector: dict[str, str] = {}

        self._create_sectors(n_sectors)

        # 글로벌 메트릭
        self.total_handoffs = 0

    def _create_sectors(self, n: int) -> None:
        """격자형 구역 생성"""
        side = int(math.ceil(math.sqrt(n)))
        b = self.bounds
        step_x = 2 * b / side
        step_y = 2 * b / side

        idx = 0
        for row in range(side):
            for col in range(side):
                if idx >= n:
                    break
                x0 = -b + col * step_x
                x1 = x0 + step_x
                y0 = -b + row * step_y
                y1 = y0 + step_y
                sid = f"SEC_{idx:02d}"
                self.sectors[sid] = Sector(
                    sector_id=sid,
                    x_range=(x0, x1),
                    y_range=(y0, y1),
                )
                idx += 1

    def assign_sector(self, pos: np.ndarray) -> str | None:
        """위치에 해당하는 구역 ID 반환"""
        for sid, sector in self.sectors.items():
            if sector.contains(pos):
                return sid
        return None

    def register_drone(self, drone_id: str, pos: np.ndarray) -> str | None:
        """드론을 현재 위치의 구역에 등록"""
        sid = self.assign_sector(pos)
        if sid is None:
            return None

        # 이전 구역에서 제거
        old_sid = self._drone_sector.get(drone_id)
        if old_sid and old_sid in self.sectors:
            self.sectors[old_sid].drones.discard(drone_id)

        self.sectors[sid].drones.add(drone_id)
        self._drone_sector[drone_id] = sid
        return sid

    def update_drone_position(self, drone_id: str, pos: np.ndarray) -> str | None:
        """
        드론 위치 갱신 — 구역 변경 시 자동 핸드오프.

        Returns
        -------
        새 구역 ID (변경 없으면 기존 구역 ID)
        """
        current_sid = self._drone_sector.get(drone_id)
        new_sid = self.assign_sector(pos)

        if new_sid is None:
            return current_sid

        if current_sid != new_sid:
            self.handoff(drone_id, current_sid, new_sid)

        return new_sid

    def handoff(
        self,
        drone_id: str,
        from_sector: str | None,
        to_sector: str,
    ) -> None:
        """구역 간 핸드오프 수행"""
        if from_sector and from_sector in self.sectors:
            self.sectors[from_sector].drones.discard(drone_id)
            self.sectors[from_sector].handoffs_out += 1

        if to_sector in self.sectors:
            self.sectors[to_sector].drones.add(drone_id)
            self.sectors[to_sector].handoffs_in += 1

        self._drone_sector[drone_id] = to_sector
        self.total_handoffs += 1

    def get_drone_sector(self, drone_id: str) -> str | None:
        """드론이 속한 구역 ID"""
        return self._drone_sector.get(drone_id)

    def sector_stats(self) -> dict[str, dict]:
        """구역별 통계"""
        return {
            sid: {
                "drones": len(s.drones),
                "conflicts": s.conflicts,
                "advisories": s.advisories,
                "handoffs_in": s.handoffs_in,
                "handoffs_out": s.handoffs_out,
                "area_km2": s.area_km2(),
                "density": len(s.drones) / max(s.area_km2(), 0.001),
            }
            for sid, s in self.sectors.items()
        }

    def global_stats(self) -> dict:
        """글로벌 통계"""
        total_drones = sum(len(s.drones) for s in self.sectors.values())
        return {
            "total_sectors": len(self.sectors),
            "total_drones": total_drones,
            "total_handoffs": self.total_handoffs,
            "sector_stats": self.sector_stats(),
        }

    def is_near_boundary(self, pos: np.ndarray, margin: float | None = None) -> bool:
        """위치가 구역 경계 근처인지 판정"""
        m = margin or self.handoff_margin
        sid = self.assign_sector(pos)
        if sid is None:
            return True

        sector = self.sectors[sid]
        return bool(
            pos[0] - sector.x_range[0] < m
            or sector.x_range[1] - pos[0] < m
            or pos[1] - sector.y_range[0] < m
            or sector.y_range[1] - pos[1] < m
        )
