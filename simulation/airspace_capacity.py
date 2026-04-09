"""
공역 용량 분석기
================
섹터별 최대 수용량 계산, 포화도 예측, 자동 규제(유입 제한).
실시간 용량 모니터링 + 과밀 경고.

사용법:
    cap = AirspaceCapacity(bounds=(0, 0, 1000, 1000), sectors=(3, 3))
    cap.update_positions({"d1": (100, 200, 50), "d2": (800, 900, 60)})
    report = cap.analyze()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class SectorInfo:
    """섹터 정보"""
    sector_id: str
    row: int
    col: int
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    capacity: int  # 최대 수용량
    current_count: int = 0
    saturation: float = 0.0  # 0~1
    status: str = "NORMAL"  # NORMAL, BUSY, SATURATED, OVERLOADED
    restricted: bool = False


@dataclass
class CapacityReport:
    """용량 분석 보고서"""
    total_drones: int
    total_capacity: int
    overall_saturation: float
    overloaded_sectors: list[str]
    restricted_sectors: list[str]
    predicted_saturation_30s: float
    recommendation: str


class AirspaceCapacity:
    """
    공역 용량 분석 및 관리.

    격자 기반 섹터 분할 + 수용량 계산 + 포화도 예측.
    """

    def __init__(
        self,
        bounds: tuple[float, float, float, float] = (0, 0, 1000, 1000),
        sectors: tuple[int, int] = (3, 3),
        base_capacity_per_sector: int = 15,
        overload_threshold: float = 0.9,
        restrict_threshold: float = 1.0,
    ) -> None:
        self.x_min, self.y_min, self.x_max, self.y_max = bounds
        self.n_rows, self.n_cols = sectors
        self.base_capacity = base_capacity_per_sector
        self.overload_threshold = overload_threshold
        self.restrict_threshold = restrict_threshold

        self._sectors: dict[str, SectorInfo] = {}
        self._positions: dict[str, tuple[float, float, float]] = {}
        self._history: list[float] = []  # 시간별 전체 포화도
        self._max_history = 300

        self._init_sectors()

    def _init_sectors(self) -> None:
        dx = (self.x_max - self.x_min) / self.n_cols
        dy = (self.y_max - self.y_min) / self.n_rows

        for r in range(self.n_rows):
            for c in range(self.n_cols):
                sid = f"S{r}{c}"
                self._sectors[sid] = SectorInfo(
                    sector_id=sid,
                    row=r, col=c,
                    x_min=self.x_min + c * dx,
                    x_max=self.x_min + (c + 1) * dx,
                    y_min=self.y_min + r * dy,
                    y_max=self.y_min + (r + 1) * dy,
                    capacity=self.base_capacity,
                )

    def update_positions(
        self, positions: dict[str, tuple[float, float, float]]
    ) -> None:
        """드론 위치 갱신 및 섹터 카운트 업데이트"""
        self._positions = dict(positions)

        # 카운트 리셋
        for s in self._sectors.values():
            s.current_count = 0

        # 각 드론의 섹터 할당
        for did, pos in positions.items():
            sid = self._get_sector_id(pos[0], pos[1])
            if sid and sid in self._sectors:
                self._sectors[sid].current_count += 1

        # 포화도 및 상태 갱신
        for s in self._sectors.values():
            s.saturation = s.current_count / max(s.capacity, 1)
            s.status = self._determine_status(s)

        # 전체 포화도 기록
        overall = self.overall_saturation()
        self._history.append(overall)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def analyze(self) -> CapacityReport:
        """용량 분석 보고서 생성"""
        total_drones = sum(s.current_count for s in self._sectors.values())
        total_capacity = sum(s.capacity for s in self._sectors.values())
        overall = self.overall_saturation()

        overloaded = [
            s.sector_id for s in self._sectors.values()
            if s.status == "OVERLOADED"
        ]
        restricted = [
            s.sector_id for s in self._sectors.values()
            if s.restricted
        ]

        pred_30 = self._predict_saturation(30)

        if overloaded:
            rec = f"과밀 섹터 {len(overloaded)}개 — 유입 제한 및 리라우팅 권장"
        elif pred_30 > self.overload_threshold:
            rec = "30초 내 과밀 예상 — 사전 유입 제한 권장"
        elif overall > 0.7:
            rec = "높은 밀도 — 모니터링 강화 권장"
        else:
            rec = "정상 운영 가능"

        return CapacityReport(
            total_drones=total_drones,
            total_capacity=total_capacity,
            overall_saturation=overall,
            overloaded_sectors=overloaded,
            restricted_sectors=restricted,
            predicted_saturation_30s=pred_30,
            recommendation=rec,
        )

    def overall_saturation(self) -> float:
        """전체 포화도"""
        total_count = sum(s.current_count for s in self._sectors.values())
        total_cap = sum(s.capacity for s in self._sectors.values())
        return total_count / max(total_cap, 1)

    def sector_saturation(self, sector_id: str) -> float:
        s = self._sectors.get(sector_id)
        return s.saturation if s else 0.0

    def auto_restrict(self) -> list[str]:
        """과밀 섹터 자동 유입 제한"""
        restricted = []
        for s in self._sectors.values():
            if s.saturation >= self.restrict_threshold and not s.restricted:
                s.restricted = True
                restricted.append(s.sector_id)
            elif s.saturation < self.overload_threshold * 0.8 and s.restricted:
                s.restricted = False  # 해제
        return restricted

    def can_enter(self, sector_id: str) -> bool:
        """섹터 진입 가능 여부"""
        s = self._sectors.get(sector_id)
        if not s:
            return True
        return not s.restricted and s.saturation < self.restrict_threshold

    def set_capacity(self, sector_id: str, capacity: int) -> None:
        if sector_id in self._sectors:
            self._sectors[sector_id].capacity = capacity

    def get_least_busy_sector(self) -> str | None:
        """가장 여유 있는 섹터"""
        if not self._sectors:
            return None
        return min(self._sectors.values(), key=lambda s: s.saturation).sector_id

    def get_sector_for_position(
        self, x: float, y: float
    ) -> SectorInfo | None:
        sid = self._get_sector_id(x, y)
        return self._sectors.get(sid) if sid else None

    def _get_sector_id(self, x: float, y: float) -> str | None:
        dx = (self.x_max - self.x_min) / self.n_cols
        dy = (self.y_max - self.y_min) / self.n_rows
        col = int((x - self.x_min) / dx)
        row = int((y - self.y_min) / dy)
        col = max(0, min(col, self.n_cols - 1))
        row = max(0, min(row, self.n_rows - 1))
        return f"S{row}{col}"

    def _determine_status(self, sector: SectorInfo) -> str:
        if sector.saturation >= self.restrict_threshold:
            return "OVERLOADED"
        if sector.saturation >= self.overload_threshold:
            return "SATURATED"
        if sector.saturation >= 0.6:
            return "BUSY"
        return "NORMAL"

    def _predict_saturation(self, horizon_s: float) -> float:
        """포화도 트렌드 예측"""
        if len(self._history) < 3:
            return self.overall_saturation()

        recent = self._history[-min(30, len(self._history)):]
        times = np.arange(len(recent), dtype=float)
        coeffs = np.polyfit(times, recent, 1)
        predicted = coeffs[0] * (len(recent) + horizon_s) + coeffs[1]
        return float(max(0.0, min(2.0, predicted)))

    def summary(self) -> dict[str, Any]:
        report = self.analyze()
        return {
            "total_drones": report.total_drones,
            "total_capacity": report.total_capacity,
            "overall_saturation": round(report.overall_saturation, 3),
            "overloaded_sectors": report.overloaded_sectors,
            "restricted_sectors": report.restricted_sectors,
            "predicted_30s": round(report.predicted_saturation_30s, 3),
            "recommendation": report.recommendation,
            "sectors": {
                s.sector_id: {
                    "count": s.current_count,
                    "capacity": s.capacity,
                    "saturation": round(s.saturation, 3),
                    "status": s.status,
                }
                for s in self._sectors.values()
            },
        }
