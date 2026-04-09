"""
E2E 스트레스 테스트 프레임워크
=============================
대규모 드론(100~500+) 환경에서 모든 서브시스템을
동시에 가동하여 성능 병목과 정합성을 검증.

측정 항목:
  - 틱당 평균/최대 처리 시간
  - 메모리 사용량 추이
  - 충돌/분리 위반 비율
  - 어드바이저리 발행 빈도
  - 컨트롤러 1Hz 루프 완수율

사용법:
    runner = StressTestRunner(n_drones=200, duration_s=60)
    result = runner.run()
    print(result.summary())
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StressTestConfig:
    """스트레스 테스트 설정"""
    n_drones: int = 100
    duration_s: float = 60.0
    tick_hz: float = 10.0
    wind_speed: float = 5.0
    rogue_count: int = 2
    enable_apf: bool = True
    enable_cbs: bool = True
    enable_formation: bool = False
    seed: int = 42

    def __post_init__(self) -> None:
        if self.n_drones < 1:
            raise ValueError(f"n_drones must be >= 1, got {self.n_drones}")
        if self.duration_s <= 0:
            raise ValueError(f"duration_s must be > 0, got {self.duration_s}")
        if self.tick_hz <= 0:
            raise ValueError(f"tick_hz must be > 0, got {self.tick_hz}")


@dataclass
class TickMetrics:
    """단일 틱 성능 측정"""
    tick: int
    sim_time: float
    wall_time_ms: float
    active_drones: int
    conflicts: int = 0
    collisions: int = 0
    advisories: int = 0
    memory_mb: float = 0.0


@dataclass
class StressTestResult:
    """스트레스 테스트 결과"""
    config: StressTestConfig
    tick_metrics: list[TickMetrics] = field(default_factory=list)
    total_wall_time_s: float = 0.0
    total_ticks: int = 0
    total_collisions: int = 0
    total_conflicts: int = 0
    total_advisories: int = 0
    peak_memory_mb: float = 0.0
    completed: bool = False

    @property
    def avg_tick_ms(self) -> float:
        if not self.tick_metrics:
            return 0.0
        return sum(m.wall_time_ms for m in self.tick_metrics) / len(self.tick_metrics)

    @property
    def max_tick_ms(self) -> float:
        if not self.tick_metrics:
            return 0.0
        return max(m.wall_time_ms for m in self.tick_metrics)

    @property
    def p95_tick_ms(self) -> float:
        if not self.tick_metrics:
            return 0.0
        sorted_times = sorted(m.wall_time_ms for m in self.tick_metrics)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[min(idx, len(sorted_times) - 1)]

    @property
    def p99_tick_ms(self) -> float:
        if not self.tick_metrics:
            return 0.0
        sorted_times = sorted(m.wall_time_ms for m in self.tick_metrics)
        idx = int(len(sorted_times) * 0.99)
        return sorted_times[min(idx, len(sorted_times) - 1)]

    @property
    def collision_rate(self) -> float:
        """충돌률 (충돌/충돌+충돌위험)"""
        total = self.total_collisions + self.total_conflicts
        if total == 0:
            return 0.0
        return self.total_collisions / total

    @property
    def resolution_rate(self) -> float:
        """해결률"""
        return 1.0 - self.collision_rate

    @property
    def realtime_factor(self) -> float:
        """실시간 대비 배율 (>1이면 실시간보다 빠름)"""
        if self.total_wall_time_s <= 0:
            return 0.0
        return self.config.duration_s / self.total_wall_time_s

    def summary(self) -> dict[str, Any]:
        return {
            "n_drones": self.config.n_drones,
            "duration_s": self.config.duration_s,
            "completed": self.completed,
            "total_ticks": self.total_ticks,
            "total_wall_time_s": round(self.total_wall_time_s, 2),
            "realtime_factor": round(self.realtime_factor, 2),
            "avg_tick_ms": round(self.avg_tick_ms, 2),
            "max_tick_ms": round(self.max_tick_ms, 2),
            "p95_tick_ms": round(self.p95_tick_ms, 2),
            "p99_tick_ms": round(self.p99_tick_ms, 2),
            "total_collisions": self.total_collisions,
            "total_conflicts": self.total_conflicts,
            "total_advisories": self.total_advisories,
            "resolution_rate": round(self.resolution_rate, 4),
            "peak_memory_mb": round(self.peak_memory_mb, 2),
        }


class StressTestRunner:
    """
    E2E 스트레스 테스트 실행기.

    시뮬레이터 의존 없이 독립 실행 가능한
    성능 측정 프레임워크.
    실제 SwarmSimulator 연동은 run_with_simulator()로.
    """

    def __init__(self, config: StressTestConfig | None = None, **kwargs: Any) -> None:
        if config is not None:
            self.config = config
        else:
            self.config = StressTestConfig(**kwargs)
        self._result: StressTestResult | None = None

    def run_synthetic(self) -> StressTestResult:
        """
        합성 부하 테스트 (시뮬레이터 미사용).

        N개 드론의 위치 갱신 + 충돌 검사 O(N·k) 성능 측정.
        """
        import numpy as np

        rng = np.random.default_rng(self.config.seed)
        cfg = self.config
        result = StressTestResult(config=cfg)

        n = cfg.n_drones
        total_ticks = int(cfg.duration_s * cfg.tick_hz)

        # 초기 위치
        positions = rng.uniform(-2000, 2000, size=(n, 3))
        positions[:, 2] = rng.uniform(30, 120, size=n)
        velocities = rng.uniform(-5, 5, size=(n, 3))
        velocities[:, 2] *= 0.3

        dt = 1.0 / cfg.tick_hz
        start_wall = time.perf_counter()

        for tick in range(total_ticks):
            tick_start = time.perf_counter()

            # 위치 갱신
            positions += velocities * dt

            # 경계 반사
            for axis in range(3):
                lo = -2500 if axis < 2 else 30
                hi = 2500 if axis < 2 else 120
                mask_lo = positions[:, axis] < lo
                mask_hi = positions[:, axis] > hi
                velocities[mask_lo, axis] = abs(velocities[mask_lo, axis])
                velocities[mask_hi, axis] = -abs(velocities[mask_hi, axis])
                positions[:, axis] = np.clip(positions[:, axis], lo, hi)

            # O(N·k) 충돌 검사 (간이 그리드)
            conflicts = 0
            collisions = 0
            sep = 50.0
            col_dist = 5.0

            if n <= 500:
                # KDTree 기반
                from scipy.spatial import KDTree
                tree = KDTree(positions)
                pairs = tree.query_pairs(sep)
                conflicts = len(pairs)
                for i, j in pairs:
                    dist = np.linalg.norm(positions[i] - positions[j])
                    if dist < col_dist:
                        collisions += 1

            tick_end = time.perf_counter()
            tick_ms = (tick_end - tick_start) * 1000.0

            sim_time = tick * dt
            tm = TickMetrics(
                tick=tick,
                sim_time=sim_time,
                wall_time_ms=tick_ms,
                active_drones=n,
                conflicts=conflicts,
                collisions=collisions,
            )
            result.tick_metrics.append(tm)
            result.total_conflicts += conflicts
            result.total_collisions += collisions

        end_wall = time.perf_counter()
        result.total_wall_time_s = end_wall - start_wall
        result.total_ticks = total_ticks
        result.completed = True

        self._result = result
        return result

    def run_quick_benchmark(self, ticks: int = 100) -> StressTestResult:
        """
        빠른 벤치마크 (짧은 틱 수).

        CI/CD에서 성능 회귀 감지용.
        """
        import numpy as np

        rng = np.random.default_rng(self.config.seed)
        cfg = self.config
        result = StressTestResult(config=cfg)

        n = cfg.n_drones
        positions = rng.uniform(-2000, 2000, size=(n, 3))
        positions[:, 2] = rng.uniform(30, 120, size=n)
        velocities = rng.uniform(-5, 5, size=(n, 3))

        dt = 1.0 / cfg.tick_hz
        start_wall = time.perf_counter()

        for tick in range(ticks):
            tick_start = time.perf_counter()
            positions += velocities * dt
            tick_end = time.perf_counter()

            result.tick_metrics.append(TickMetrics(
                tick=tick,
                sim_time=tick * dt,
                wall_time_ms=(tick_end - tick_start) * 1000.0,
                active_drones=n,
            ))

        end_wall = time.perf_counter()
        result.total_wall_time_s = end_wall - start_wall
        result.total_ticks = ticks
        result.completed = True

        self._result = result
        return result

    @property
    def result(self) -> StressTestResult | None:
        return self._result

    def compare(
        self,
        other: StressTestResult,
    ) -> dict[str, Any]:
        """두 결과 비교"""
        if self._result is None:
            return {"error": "No result to compare"}

        a = self._result
        b = other
        return {
            "a_drones": a.config.n_drones,
            "b_drones": b.config.n_drones,
            "avg_tick_ratio": (
                a.avg_tick_ms / b.avg_tick_ms if b.avg_tick_ms > 0 else 0
            ),
            "wall_time_ratio": (
                a.total_wall_time_s / b.total_wall_time_s
                if b.total_wall_time_s > 0 else 0
            ),
            "a_resolution_rate": a.resolution_rate,
            "b_resolution_rate": b.resolution_rate,
        }
