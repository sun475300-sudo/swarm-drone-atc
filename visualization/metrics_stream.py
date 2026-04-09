"""
실시간 메트릭 스트리밍 — 대시보드 시계열 데이터 수집
=================================================
SimState에 연동되어 매 틱 메트릭을 수집하고 시계열로 저장한다.
Dash 콜백에서 차트용 데이터를 꺼내 쓸 수 있도록 설계.
"""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class MetricsSnapshot:
    """한 시점의 메트릭 스냅샷"""
    t: float = 0.0
    active_drones: int = 0
    avg_battery_pct: float = 100.0
    min_battery_pct: float = 100.0
    max_battery_pct: float = 100.0
    battery_histogram: list[int] = field(default_factory=lambda: [0] * 10)
    total_energy_wh: float = 0.0
    conflicts_cumulative: int = 0
    collisions_cumulative: int = 0
    near_misses_cumulative: int = 0
    advisories_cumulative: int = 0
    evading_count: int = 0
    phase_counts: dict[str, int] = field(default_factory=dict)
    conflict_resolution_rate: float = 100.0


class MetricsCollector:
    """시계열 메트릭 수집기 — 최대 max_history 개 스냅샷 보관"""

    def __init__(self, max_history: int = 600) -> None:
        self.max_history = max_history
        self._history: deque[MetricsSnapshot] = deque(maxlen=max_history)
        self._lock = threading.Lock()
        self._total_energy_wh = 0.0

    def reset(self) -> None:
        with self._lock:
            self._history.clear()
            self._total_energy_wh = 0.0

    def record(self, *, t: float, drones: list, conflicts: int,
               collisions: int, near_misses: int, advisories: int,
               dt: float = 0.1) -> None:
        """매 틱 호출 — 드론 리스트에서 메트릭을 추출하여 기록"""
        from src.airspace_control.agents.drone_state import FlightPhase

        active = [d for d in drones if d.is_active]
        n_active = len(active)

        batteries = [d.battery_pct for d in drones] if drones else [100.0]
        avg_bat = sum(batteries) / len(batteries)
        min_bat = min(batteries)
        max_bat = max(batteries)

        # 배터리 히스토그램: 10% 구간 (0-10, 10-20, ..., 90-100)
        hist = [0] * 10
        for b in batteries:
            idx = min(int(b // 10), 9)
            hist[idx] += 1

        # 에너지 추정: 활성 드론 평균 전력 × dt
        for d in active:
            speed = float(np.linalg.norm(d.velocity)) if hasattr(d, 'velocity') else 0.0
            power_w = 50.0 + 0.5 * speed ** 2  # 간이 전력 모델
            self._total_energy_wh += power_w * dt / 3600.0

        evading = sum(1 for d in drones if d.flight_phase == FlightPhase.EVADING)

        phase_counts: dict[str, int] = {}
        for d in drones:
            name = d.flight_phase.name
            phase_counts[name] = phase_counts.get(name, 0) + 1

        # 충돌 해결률
        denom = conflicts + collisions
        cr_rate = (1.0 - collisions / denom) * 100.0 if denom > 0 else 100.0

        snap = MetricsSnapshot(
            t=t,
            active_drones=n_active,
            avg_battery_pct=avg_bat,
            min_battery_pct=min_bat,
            max_battery_pct=max_bat,
            battery_histogram=hist,
            total_energy_wh=self._total_energy_wh,
            conflicts_cumulative=conflicts,
            collisions_cumulative=collisions,
            near_misses_cumulative=near_misses,
            advisories_cumulative=advisories,
            evading_count=evading,
            phase_counts=phase_counts,
            conflict_resolution_rate=cr_rate,
        )

        with self._lock:
            self._history.append(snap)

    @property
    def latest(self) -> MetricsSnapshot | None:
        with self._lock:
            return self._history[-1] if self._history else None

    def time_series(self, field_name: str) -> tuple[list[float], list[float]]:
        """특정 필드의 시계열 (t_list, value_list) 반환"""
        with self._lock:
            snaps = list(self._history)
        ts = [s.t for s in snaps]
        vals = [getattr(s, field_name, 0.0) for s in snaps]
        return ts, vals

    def battery_distribution(self) -> list[int]:
        """최신 배터리 분포 히스토그램 반환"""
        with self._lock:
            if self._history:
                return list(self._history[-1].battery_histogram)
            return [0] * 10

    def history_len(self) -> int:
        with self._lock:
            return len(self._history)
