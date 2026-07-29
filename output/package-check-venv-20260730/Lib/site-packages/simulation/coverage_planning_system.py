"""
Phase 467: Coverage Planning System for Area Survey
"""

from dataclasses import dataclass


@dataclass
class CoverageRegion:
    """``CoverageRegion`` 관련 기능을 제공한다."""
    x_min: float
    x_max: float
    y_min: float
    y_max: float


class CoveragePlanningSystem:
    """``CoveragePlanningSystem`` 역할을 담당한다."""
    def __init__(self):
        """인스턴스를 초기화한다."""
        self.regions: list[CoverageRegion] = []

    def add_region(self, region: CoverageRegion):
        """`region` 항목을 추가한다."""
        self.regions.append(region)

    def plan_survey_path(
        self, drone_count: int
    ) -> list[list[tuple[float, float, float]]]:
        """`survey path` 작업을 계획한다."""
        if not self.regions:
            return []

        all_paths = []
        for region in self.regions:
            path = self._generate_lawnmower(region, drone_count)
            all_paths.append(path)

        return all_paths

    def _generate_lawnmower(
        self, region: CoverageRegion, drones: int
    ) -> list[tuple[float, float, float]]:
        path = []
        x = region.x_min
        y = region.y_min
        z = 50

        while y <= region.y_max:
            path.append((x, y, z))
            x = region.x_max if (y - region.y_min) % 20 == 0 else region.x_min
            y += 10

        return path
