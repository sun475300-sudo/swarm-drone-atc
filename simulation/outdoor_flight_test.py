"""3~5대 드론 편대 비행 테스트 프레임워크 (SW 시뮬레이션)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np


@dataclass
class FlightTestConfig:
    """편대 비행 테스트 설정."""

    drone_count: int          # 드론 수 (권장 3~5)
    formation: str            # 편대 유형: "line" | "triangle" | "diamond" | "circle"
    duration_s: float         # 시뮬레이션 지속 시간 (초)
    gps_replay_file: str | None = None  # GPS 재현 파일 경로 (None = 합성 경로)

    def __post_init__(self) -> None:
        if self.drone_count < 2:
            raise ValueError("드론은 최소 2대 필요")
        if self.duration_s <= 0:
            raise ValueError("duration_s는 양수여야 합니다")
        valid_formations = {"line", "triangle", "diamond", "circle"}
        if self.formation not in valid_formations:
            raise ValueError(f"지원 편대: {valid_formations}, 입력: {self.formation!r}")


@dataclass
class FlightTestResult:
    """편대 비행 테스트 결과."""

    success: bool
    max_separation_m: float         # 최대 드론 간 거리 (m)
    min_separation_m: float         # 최소 드론 간 거리 (m)
    position_errors: list[float]    # 각 드론의 목표 위치 오차 (m)


def _formation_offsets(formation: str, count: int, spacing_m: float = 5.0) -> list[tuple[float, float]]:
    """편대 유형에 따라 드론별 (dx, dy) 오프셋을 반환한다 (미터 단위)."""
    if formation == "line":
        return [(i * spacing_m, 0.0) for i in range(count)]

    if formation == "triangle":
        offsets = [(0.0, 0.0), (spacing_m, 0.0), (spacing_m / 2, spacing_m * math.sqrt(3) / 2)]
        # 4대 이상: 추가 드론을 뒤에 직선 배치
        for i in range(3, count):
            offsets.append(((i - 2) * spacing_m / 2, -(i - 2) * spacing_m))
        return offsets[:count]

    if formation == "diamond":
        base = [(0.0, spacing_m), (spacing_m, 0.0), (0.0, -spacing_m), (-spacing_m, 0.0)]
        offsets = [(0.0, 0.0)] + base
        return offsets[:count]

    # circle
    offsets = []
    for i in range(count):
        angle = 2 * math.pi * i / count
        offsets.append((spacing_m * math.cos(angle), spacing_m * math.sin(angle)))
    return offsets


def _pairwise_distances(positions: list[tuple[float, float, float]]) -> list[float]:
    """모든 드론 쌍의 3D 거리를 반환한다."""
    distances = []
    n = len(positions)
    for i in range(n):
        for j in range(i + 1, n):
            dx = positions[i][0] - positions[j][0]
            dy = positions[i][1] - positions[j][1]
            dz = positions[i][2] - positions[j][2]
            distances.append(math.sqrt(dx**2 + dy**2 + dz**2))
    return distances


class OutdoorFlightTest:
    """편대 비행 시뮬레이션을 실행하고 결과를 반환한다."""

    # 안전 최소 이격 거리 (m)
    _MIN_SAFE_SEPARATION_M = 1.5
    # 목표 위치 오차 허용값 (m)
    _MAX_POSITION_ERROR_M = 2.0

    def __init__(self, seed: int = 42) -> None:
        self._rng = np.random.default_rng(seed)

    def run_formation_sim(self, config: FlightTestConfig) -> FlightTestResult:
        """편대 비행 시뮬레이션을 실행한다.

        GPS 재현 파일 없이 합성 궤적을 생성하여 이격 거리 및 위치 오차를 계산한다.

        Args:
            config: FlightTestConfig 설정.

        Returns:
            FlightTestResult (성공 여부, 이격 통계, 위치 오차).
        """
        offsets = _formation_offsets(config.formation, config.drone_count)
        dt = 0.1        # 시뮬레이션 스텝 (초)
        steps = int(config.duration_s / dt)

        all_separations: list[float] = []
        position_error_sums = [0.0] * config.drone_count
        step_count = 0

        # 기준 경로: 원형 (반경 20m, 10초 주기)
        omega = 2 * math.pi / 10.0
        altitude = 30.0  # 고정 고도 (m)

        for s in range(steps):
            t = s * dt
            # 기준 드론(리더) 위치
            ref_x = 20.0 * math.cos(omega * t)
            ref_y = 20.0 * math.sin(omega * t)

            # GPS 노이즈 (σ = 0.3 m, RTK 정밀도 가정)
            noise = self._rng.normal(0.0, 0.3, size=(config.drone_count, 2))

            positions: list[tuple[float, float, float]] = []
            for i, (ox, oy) in enumerate(offsets):
                x = ref_x + ox + noise[i, 0]
                y = ref_y + oy + noise[i, 1]
                positions.append((x, y, altitude))

            # 이격 거리 기록
            dists = _pairwise_distances(positions)
            all_separations.extend(dists)

            # 위치 오차: 목표 위치(노이즈 없음)와 실제 위치 차이
            for i, (ox, oy) in enumerate(offsets):
                target_x = ref_x + ox
                target_y = ref_y + oy
                err = math.sqrt((positions[i][0] - target_x)**2 + (positions[i][1] - target_y)**2)
                position_error_sums[i] += err

            step_count += 1

        # 통계 집계
        max_sep = max(all_separations) if all_separations else 0.0
        min_sep = min(all_separations) if all_separations else 0.0
        avg_errors = [position_error_sums[i] / step_count for i in range(config.drone_count)]

        success = (
            min_sep >= self._MIN_SAFE_SEPARATION_M
            and all(e <= self._MAX_POSITION_ERROR_M for e in avg_errors)
        )

        return FlightTestResult(
            success=success,
            max_separation_m=round(max_sep, 3),
            min_separation_m=round(min_sep, 3),
            position_errors=[round(e, 3) for e in avg_errors],
        )
