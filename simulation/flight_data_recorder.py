"""
비행 데이터 레코더 (FDR)
=========================
매 틱 드론의 위치/속도/배터리/상태를 기록하여
사후 리플레이 및 분석을 지원한다.

사용법:
    fdr = FlightDataRecorder()
    fdr.record_tick(t=1.0, drones=[d1, d2, ...])
    timeline = fdr.get_drone_timeline("DR001")
    fdr.export_csv("flight_log.csv")
"""
from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class FlightRecord:
    """단일 드론의 한 시점 기록"""
    t: float
    drone_id: str
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    speed: float
    battery_pct: float
    flight_phase: str
    profile_name: str
    failure_type: str = "NONE"


class FlightDataRecorder:
    """
    비행 데이터 레코더.

    매 틱 모든 활성 드론의 상태를 기록하고
    드론별/시간별 조회 및 CSV 내보내기를 지원.
    """

    def __init__(self, max_ticks: int = 0) -> None:
        """
        Parameters
        ----------
        max_ticks : 최대 기록 틱 수 (0=무제한)
        """
        self.max_ticks = max_ticks
        self._records: list[FlightRecord] = []
        self._by_drone: dict[str, list[FlightRecord]] = defaultdict(list)
        self._tick_count = 0

    def record_tick(self, t: float, drones: list) -> None:
        """
        매 틱 호출 — 드론 리스트에서 상태를 기록.

        Parameters
        ----------
        t : 시뮬레이션 시간 (s)
        drones : DroneState 리스트
        """
        if self.max_ticks > 0 and self._tick_count >= self.max_ticks:
            return

        for d in drones:
            pos = d.position if hasattr(d, 'position') else np.zeros(3)
            vel = d.velocity if hasattr(d, 'velocity') else np.zeros(3)
            speed = float(np.linalg.norm(vel))
            phase = d.flight_phase.name if hasattr(d.flight_phase, 'name') else str(d.flight_phase)
            failure = d.failure_type.name if hasattr(d, 'failure_type') and hasattr(d.failure_type, 'name') else "NONE"

            rec = FlightRecord(
                t=t,
                drone_id=d.drone_id,
                x=float(pos[0]),
                y=float(pos[1]),
                z=float(pos[2]),
                vx=float(vel[0]),
                vy=float(vel[1]),
                vz=float(vel[2]),
                speed=speed,
                battery_pct=float(d.battery_pct),
                flight_phase=phase,
                profile_name=getattr(d, 'profile_name', 'UNKNOWN'),
                failure_type=failure,
            )
            self._records.append(rec)
            self._by_drone[d.drone_id].append(rec)

        self._tick_count += 1

    def get_drone_timeline(self, drone_id: str) -> list[FlightRecord]:
        """특정 드론의 전체 타임라인 반환"""
        return list(self._by_drone.get(drone_id, []))

    def get_time_slice(self, t_start: float, t_end: float) -> list[FlightRecord]:
        """시간 구간 내 모든 기록 반환"""
        return [r for r in self._records if t_start <= r.t <= t_end]

    def get_drone_at_time(self, drone_id: str, t: float) -> FlightRecord | None:
        """특정 드론의 특정 시간 근방 기록 반환"""
        timeline = self._by_drone.get(drone_id, [])
        if not timeline:
            return None
        # 가장 가까운 시간의 기록
        return min(timeline, key=lambda r: abs(r.t - t))

    def drone_ids(self) -> list[str]:
        """기록된 모든 드론 ID 목록"""
        return sorted(self._by_drone.keys())

    def total_records(self) -> int:
        """전체 기록 수"""
        return len(self._records)

    def tick_count(self) -> int:
        """기록된 틱 수"""
        return self._tick_count

    def export_csv(self, path: str | Path) -> Path:
        """
        전체 비행 기록을 CSV로 내보내기.

        Returns
        -------
        Path : 저장된 파일 경로
        """
        path = Path(path)
        fields = [
            "t", "drone_id", "x", "y", "z",
            "vx", "vy", "vz", "speed",
            "battery_pct", "flight_phase", "profile_name", "failure_type",
        ]

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for rec in self._records:
                writer.writerow({
                    "t": f"{rec.t:.2f}",
                    "drone_id": rec.drone_id,
                    "x": f"{rec.x:.1f}",
                    "y": f"{rec.y:.1f}",
                    "z": f"{rec.z:.1f}",
                    "vx": f"{rec.vx:.2f}",
                    "vy": f"{rec.vy:.2f}",
                    "vz": f"{rec.vz:.2f}",
                    "speed": f"{rec.speed:.2f}",
                    "battery_pct": f"{rec.battery_pct:.1f}",
                    "flight_phase": rec.flight_phase,
                    "profile_name": rec.profile_name,
                    "failure_type": rec.failure_type,
                })

        return path

    def summary(self) -> dict[str, Any]:
        """기록 요약 정보"""
        if not self._records:
            return {"total_records": 0, "ticks": 0, "drones": 0}

        return {
            "total_records": len(self._records),
            "ticks": self._tick_count,
            "drones": len(self._by_drone),
            "time_range": (self._records[0].t, self._records[-1].t),
            "drone_ids": self.drone_ids(),
        }

    def clear(self) -> None:
        """기록 초기화"""
        self._records.clear()
        self._by_drone.clear()
        self._tick_count = 0
