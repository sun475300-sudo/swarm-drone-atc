"""
위험도 평가기
=============
지상 인구 밀도 기반 비행 위험도 + 낙하 확률 + 피해 반경.
비행 경로별 위험 점수 산출 + 최소 위험 경로 추천.

사용법:
    ra = RiskAssessor()
    ra.set_population_grid(grid)
    score = ra.assess_position(x=500, y=500, altitude=60)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class RiskProfile:
    """위험 프로파일"""
    position: tuple[float, float, float]
    ground_risk_score: float  # 0~100
    fall_probability: float  # 0~1
    impact_radius_m: float
    population_density: float  # 인/km²
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    recommended_altitude: float = 60.0


class RiskAssessor:
    """
    지상 위험도 평가기.

    인구 밀도 + 낙하 확률 + 피해 반경 기반 위험 점수.
    """

    def __init__(
        self,
        bounds: tuple[float, float, float, float] = (0, 0, 1000, 1000),
        grid_resolution: int = 20,
        drone_mass_kg: float = 5.0,
        base_failure_rate: float = 1e-5,  # 고장률 (per second)
    ) -> None:
        self.bounds = bounds
        self.resolution = grid_resolution
        self.drone_mass = drone_mass_kg
        self.failure_rate = base_failure_rate

        # 인구 밀도 격자 (인/km²)
        self._pop_grid = np.zeros((grid_resolution, grid_resolution))
        # 기본값: 중심부 밀집
        self._generate_default_population()

    def set_population_grid(self, grid: np.ndarray) -> None:
        """인구 밀도 격자 직접 설정"""
        self._pop_grid = grid

    def set_population_zone(
        self,
        center: tuple[float, float],
        radius: float,
        density: float,
    ) -> None:
        """원형 인구 밀집 구역 설정"""
        x_min, y_min, x_max, y_max = self.bounds
        dx = (x_max - x_min) / self.resolution
        dy = (y_max - y_min) / self.resolution

        for i in range(self.resolution):
            for j in range(self.resolution):
                gx = x_min + j * dx + dx / 2
                gy = y_min + i * dy + dy / 2
                dist = np.sqrt((gx - center[0])**2 + (gy - center[1])**2)
                if dist <= radius:
                    self._pop_grid[i, j] = max(self._pop_grid[i, j], density)

    def assess_position(
        self, x: float, y: float, altitude: float = 60.0
    ) -> RiskProfile:
        """위치별 위험도 평가"""
        pop_density = self._get_population(x, y)
        fall_prob = self._fall_probability(altitude)
        impact_r = self._impact_radius(altitude)
        ground_risk = self._ground_risk_score(pop_density, fall_prob, impact_r)
        level = self._risk_level(ground_risk)
        rec_alt = self._recommended_altitude(pop_density)

        return RiskProfile(
            position=(x, y, altitude),
            ground_risk_score=ground_risk,
            fall_probability=fall_prob,
            impact_radius_m=impact_r,
            population_density=pop_density,
            risk_level=level,
            recommended_altitude=rec_alt,
        )

    def assess_path(
        self,
        waypoints: list[tuple[float, float, float]],
    ) -> dict[str, Any]:
        """경로 전체 위험도"""
        if not waypoints:
            return {"avg_risk": 0, "max_risk": 0, "risk_level": "LOW"}

        risks = [
            self.assess_position(x, y, z) for x, y, z in waypoints
        ]
        scores = [r.ground_risk_score for r in risks]

        return {
            "avg_risk": float(np.mean(scores)),
            "max_risk": float(max(scores)),
            "min_risk": float(min(scores)),
            "risk_level": self._risk_level(max(scores)),
            "waypoints_assessed": len(waypoints),
            "high_risk_segments": sum(1 for s in scores if s > 70),
        }

    def risk_map(self, altitude: float = 60.0) -> np.ndarray:
        """위험도 지도 (2D grid)"""
        x_min, y_min, x_max, y_max = self.bounds
        grid = np.zeros((self.resolution, self.resolution))
        dx = (x_max - x_min) / self.resolution
        dy = (y_max - y_min) / self.resolution

        for i in range(self.resolution):
            for j in range(self.resolution):
                x = x_min + j * dx + dx / 2
                y = y_min + i * dy + dy / 2
                profile = self.assess_position(x, y, altitude)
                grid[i, j] = profile.ground_risk_score

        return grid

    def _get_population(self, x: float, y: float) -> float:
        """격자에서 인구 밀도 조회"""
        x_min, y_min, x_max, y_max = self.bounds
        col = int((x - x_min) / (x_max - x_min) * self.resolution)
        row = int((y - y_min) / (y_max - y_min) * self.resolution)
        col = max(0, min(col, self.resolution - 1))
        row = max(0, min(row, self.resolution - 1))
        return float(self._pop_grid[row, col])

    def _fall_probability(self, altitude: float) -> float:
        """낙하 확률 (고도 비례 증가)"""
        # 체공 시간이 길수록 고장 확률 증가
        return min(1.0, self.failure_rate * max(altitude, 1.0))

    def _impact_radius(self, altitude: float) -> float:
        """낙하 피해 반경 (m)"""
        # 탄도 계산: r = v_horizontal * sqrt(2h/g)
        v_h = 5.0  # 수평 속도 추정 (m/s)
        g = 9.81
        fall_time = np.sqrt(2 * max(altitude, 1.0) / g)
        return float(v_h * fall_time + self.drone_mass * 0.5)

    def _ground_risk_score(
        self, pop_density: float, fall_prob: float, impact_r: float
    ) -> float:
        """종합 지상 위험 점수 (0~100)"""
        # 인구 밀도 기여 (0~50)
        pop_factor = min(50, pop_density / 200)  # 10000인/km² → 50점

        # 낙하 확률 기여 (0~25)
        fall_factor = min(25, fall_prob * 25000)

        # 피해 반경 기여 (0~25)
        impact_factor = min(25, impact_r / 2)

        return float(min(100, pop_factor + fall_factor + impact_factor))

    def _risk_level(self, score: float) -> str:
        if score >= 80:
            return "CRITICAL"
        if score >= 60:
            return "HIGH"
        if score >= 30:
            return "MEDIUM"
        return "LOW"

    def _recommended_altitude(self, pop_density: float) -> float:
        """인구 밀도에 따른 권장 고도"""
        if pop_density > 5000:
            return 100.0  # 고밀도: 높이 비행
        if pop_density > 1000:
            return 80.0
        return 60.0  # 기본

    def _generate_default_population(self) -> None:
        """기본 인구 분포 (중심 밀집)"""
        cx, cy = self.resolution / 2, self.resolution / 2
        for i in range(self.resolution):
            for j in range(self.resolution):
                dist = np.sqrt((i - cy)**2 + (j - cx)**2)
                # 중심부 고밀도, 외곽 저밀도
                self._pop_grid[i, j] = max(0, 5000 * np.exp(-dist / 5))

    def summary(self) -> dict[str, Any]:
        return {
            "grid_resolution": self.resolution,
            "max_population": float(np.max(self._pop_grid)),
            "avg_population": float(np.mean(self._pop_grid)),
            "drone_mass_kg": self.drone_mass,
            "failure_rate": self.failure_rate,
        }
