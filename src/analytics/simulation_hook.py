"""
시뮬레이션 분석 훅 — SwarmSimulator 통합

SimulationAnalyticsHook는 SwarmSimulator에 부착되어 시뮬레이션 실행 중 메트릭을 자동으로 수집합니다.

사용 예시:
    from simulation.simulator import SwarmSimulator
    from src.analytics.simulation_hook import SimulationAnalyticsHook

    sim = SwarmSimulator("config/default_simulation.yaml")
    hook = SimulationAnalyticsHook(simulator=sim)

    # 시뮬레이션 실행
    result = sim.run()

    # 라이브 대시보드 데이터 조회
    dashboard_data = hook.get_live_dashboard_data()

    # 최종 분석 보고서 생성
    hook.on_simulation_end(sim.env.now)

    # JSON으로 내보내기
    hook.export_to_json("analytics_output.json")
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import numpy as np

from src.analytics.core_analytics import (
    PerformanceAnalyzer,
    SwarmMetricsCollector,
    MonteCarloAnalyzer,
)

logger = logging.getLogger(__name__)


class SimulationAnalyticsHook:
    """
    SwarmSimulator에 부착되어 시뮬레이션 중 메트릭을 자동으로 수집하는 훅.

    책임:
      - 시뮬레이션 각 틱마다 메트릭 기록
      - 충돌/근접 경고 이벤트 처리
      - 라이브 대시보드 데이터 제공
      - 최종 분석 보고서 생성
      - JSON 내보내기
    """

    def __init__(self, simulator: Optional[Any] = None):
        """
        초기화.

        Parameters
        ----------
        simulator : Any, optional
            SwarmSimulator 인스턴스 (선택사항)
        """
        self.simulator = simulator
        self.events = []  # 모든 기록된 이벤트
        self.metrics_history = []  # 시간별 메트릭 히스토리
        self.conflict_events = []  # 충돌 관련 이벤트
        self.collision_events = []  # 실제 충돌 이벤트

        self.collector = SwarmMetricsCollector()
        self.analyzer = PerformanceAnalyzer()
        self.mc_analyzer = MonteCarloAnalyzer()

        self._start_time = None
        self._end_time = None
        self._last_collision_count = 0
        self._last_conflict_count = 0

    def on_tick(self, sim_time: float, drones: list[Any], controller: Any) -> None:
        """
        시뮬레이션 각 틱에서 호출되어 메트릭을 기록.

        Parameters
        ----------
        sim_time : float
            현재 시뮬레이션 시간 (초)
        drones : list[Any]
            현재 활성 드론 목록 (DroneState 객체)
        controller : Any
            AirspaceController 인스턴스
        """
        if self._start_time is None:
            self._start_time = sim_time

        # 드론 메트릭 수집
        try:
            drone_metrics = self.collector.collect_drone_metrics(drones)
        except Exception as e:
            logger.warning(f"Failed to collect drone metrics at t={sim_time}: {e}")
            drone_metrics = {}

        # 공역 메트릭 수집
        try:
            airspace_metrics = self.collector.collect_airspace_metrics(
                controller, active_drones=len(drones)
            )
        except Exception as e:
            logger.warning(f"Failed to collect airspace metrics at t={sim_time}: {e}")
            airspace_metrics = {}

        # 메트릭 히스토리 기록
        tick_data = {
            "sim_time": sim_time,
            "drone_metrics": drone_metrics,
            "airspace_metrics": airspace_metrics,
        }

        self.metrics_history.append(tick_data)

        # 이벤트 기록
        event = {
            "event_type": "TICK",
            "sim_time": sim_time,
            "drone_count": len(drones),
            "advisories_active": airspace_metrics.get("active_advisories", 0),
            "pending_requests": airspace_metrics.get("pending_requests", 0),
        }

        self.events.append(event)

    def on_conflict(self, conflict_data: dict[str, Any]) -> None:
        """
        충돌 위험 감지 시 호출.

        Parameters
        ----------
        conflict_data : dict[str, Any]
            충돌 데이터:
            {
              "sim_time": float,
              "drone_a": str,
              "drone_b": str,
              "separation_distance_m": float,
              "time_to_closest_approach_s": float,
              ...
            }
        """
        self.conflict_events.append(conflict_data)

        event = {
            "event_type": "CONFLICT",
            "sim_time": conflict_data.get("sim_time", 0.0),
            "drone_a": conflict_data.get("drone_a"),
            "drone_b": conflict_data.get("drone_b"),
            "separation_distance_m": conflict_data.get("separation_distance_m"),
            "time_to_closest_approach_s": conflict_data.get("time_to_closest_approach_s"),
        }

        self.events.append(event)
        logger.info(f"Conflict detected at t={conflict_data.get('sim_time')}: "
                   f"{conflict_data.get('drone_a')} ↔ {conflict_data.get('drone_b')}")

    def on_collision(self, collision_data: dict[str, Any]) -> None:
        """
        실제 충돌 발생 시 호출.

        Parameters
        ----------
        collision_data : dict[str, Any]
            충돌 데이터:
            {
              "sim_time": float,
              "drone_a": str,
              "drone_b": str,
              "position": np.ndarray,
              "relative_velocity_ms": float,
              ...
            }
        """
        self.collision_events.append(collision_data)

        event = {
            "event_type": "COLLISION",
            "sim_time": collision_data.get("sim_time", 0.0),
            "drone_a": collision_data.get("drone_a"),
            "drone_b": collision_data.get("drone_b"),
            "position": (
                collision_data.get("position").tolist()
                if isinstance(collision_data.get("position"), np.ndarray)
                else None
            ),
            "relative_velocity_ms": collision_data.get("relative_velocity_ms"),
        }

        self.events.append(event)
        logger.error(f"COLLISION at t={collision_data.get('sim_time')}: "
                    f"{collision_data.get('drone_a')} ✕ {collision_data.get('drone_b')}")

    def on_simulation_end(self, total_time: float) -> dict[str, Any]:
        """
        시뮬레이션 종료 시 호출되어 최종 분석 보고서 생성.

        Parameters
        ----------
        total_time : float
            총 시뮬레이션 시간 (초)

        Returns
        -------
        dict[str, Any]
            최종 분석 결과:
            {
              "duration_s": float,
              "total_events": int,
              "conflicts_detected": int,
              "collisions_occurred": int,
              "collision_resolution_rate": float,
              "safety_metrics": dict,
              ...
            }
        """
        self._end_time = total_time

        # 충돌 해결률 계산
        conflicts = len(self.conflict_events)
        collisions = len(self.collision_events)

        collision_resolution_rate = self.analyzer.analyze_collision_resolution_rate(
            conflicts=conflicts, collisions=collisions
        )

        # 응답 시간 분석 (모든 이벤트에서 response_time_s 추출)
        response_times = self.analyzer.analyze_response_time(self.events)

        # 처리량 (완료된 드론 미션 수 추정)
        # 실제 구현에서는 시뮬레이터에서 완료된 미션 수를 가져와야 함
        completed_missions = getattr(self.simulator, "completed_missions", 0)
        throughput = self.analyzer.analyze_throughput(
            completed_missions=completed_missions, total_time_s=total_time
        )

        # 안전 메트릭
        safety_metrics = self.analyzer.calculate_safety_metrics({
            "collision_count": collisions,
            "conflicts_total": conflicts,
            "near_miss_count": len([e for e in self.events if e.get("event_type") == "NEAR_MISS"]),
            "min_separation_distance_m": self._get_min_separation(),
        })

        result = {
            "duration_s": total_time,
            "total_events": len(self.events),
            "conflicts_detected": conflicts,
            "collisions_occurred": collisions,
            "collision_resolution_rate": collision_resolution_rate,
            "response_time_stats": response_times,
            "throughput_missions_per_min": throughput,
            "safety_metrics": safety_metrics,
            "metrics_history_length": len(self.metrics_history),
        }

        logger.info(f"Simulation completed: {collisions} collisions, "
                   f"{conflicts} conflicts, resolution rate: {collision_resolution_rate:.1%}")

        return result

    def get_live_dashboard_data(self) -> dict[str, Any]:
        """
        현재 수집된 메트릭을 실시간 대시보드용으로 반환.

        Returns
        -------
        dict[str, Any]
            {
              "current_time": float,
              "total_events": int,
              "conflicts_count": int,
              "collisions_count": int,
              "current_drone_metrics": dict,
              "current_airspace_metrics": dict,
              "collision_resolution_rate": float,
              "latest_events": list[dict],  # 최근 10개 이벤트
              ...
            }
        """
        if not self.metrics_history:
            return {
                "current_time": 0.0,
                "total_events": 0,
                "conflicts_count": 0,
                "collisions_count": 0,
                "message": "No data collected yet",
            }

        latest_tick = self.metrics_history[-1]
        conflicts = len(self.conflict_events)
        collisions = len(self.collision_events)

        collision_resolution_rate = self.analyzer.analyze_collision_resolution_rate(
            conflicts=conflicts, collisions=collisions
        )

        # 최근 10개 이벤트
        recent_events = self.events[-10:] if len(self.events) > 10 else self.events

        data = {
            "current_time": latest_tick.get("sim_time", 0.0),
            "total_events": len(self.events),
            "conflicts_count": conflicts,
            "collisions_count": collisions,
            "collision_resolution_rate": collision_resolution_rate,
            "current_drone_metrics": latest_tick.get("drone_metrics", {}),
            "current_airspace_metrics": latest_tick.get("airspace_metrics", {}),
            "recent_events": recent_events,
        }

        return data

    def export_to_json(self, filepath: str) -> None:
        """
        수집된 모든 데이터를 JSON 파일로 내보내기.

        Parameters
        ----------
        filepath : str
            출력 JSON 파일 경로
        """
        export_data = {
            "simulation_info": {
                "start_time": self._start_time,
                "end_time": self._end_time,
                "duration_s": (self._end_time - self._start_time)
                if self._start_time and self._end_time
                else None,
            },
            "summary": {
                "total_events": len(self.events),
                "conflicts_detected": len(self.conflict_events),
                "collisions_occurred": len(self.collision_events),
            },
            "events": self.events,
            "conflict_events": self.conflict_events,
            "collision_events": self.collision_events,
            "metrics_history": self.metrics_history,
        }

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, default=str)
            logger.info(f"Exported analytics to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export analytics to {filepath}: {e}")

    def get_conflict_log(self) -> list[dict[str, Any]]:
        """
        모든 충돌 관련 이벤트 반환.

        Returns
        -------
        list[dict[str, Any]]
            충돌 이벤트 목록
        """
        return self.conflict_events.copy()

    def get_collision_log(self) -> list[dict[str, Any]]:
        """
        모든 충돌 이벤트 반환.

        Returns
        -------
        list[dict[str, Any]]
            충돌 이벤트 목록
        """
        return self.collision_events.copy()

    def get_metrics_summary(self, start_time: float = 0.0, end_time: Optional[float] = None) -> dict[str, Any]:
        """
        지정된 시간 범위의 메트릭 요약.

        Parameters
        ----------
        start_time : float, optional
            시작 시간 (초, 기본: 0.0)
        end_time : float, optional
            종료 시간 (초, 기본: None = 모든 기간)

        Returns
        -------
        dict[str, Any]
            평균 메트릭 및 통계
        """
        if not self.metrics_history:
            return {}

        # 시간 범위로 필터링
        filtered = [
            m for m in self.metrics_history
            if start_time <= m.get("sim_time", 0) <= (end_time or float("inf"))
        ]

        if not filtered:
            return {}

        # 드론 메트릭 평균
        drone_speeds = [
            m.get("drone_metrics", {}).get("speed_mean_ms", 0.0)
            for m in filtered
        ]
        drone_batteries = [
            m.get("drone_metrics", {}).get("battery_mean_pct", 0.0)
            for m in filtered
        ]

        summary = {
            "time_range": {
                "start_s": start_time,
                "end_s": end_time,
                "duration_s": (end_time - start_time) if end_time else None,
            },
            "samples": len(filtered),
            "avg_drone_speed_ms": np.mean(drone_speeds) if drone_speeds else 0.0,
            "avg_battery_pct": np.mean(drone_batteries) if drone_batteries else 0.0,
        }

        return summary

    def _get_min_separation(self) -> float:
        """
        기록된 모든 충돌/근접 경고에서 최소 분리 거리 추출.

        Returns
        -------
        float
            최소 분리 거리 (m) 또는 inf
        """
        if self.conflict_events:
            separations = [
                e.get("separation_distance_m", float("inf"))
                for e in self.conflict_events
            ]
            return min(separations) if separations else float("inf")
        return float("inf")

    def reset(self) -> None:
        """
        모든 수집된 데이터를 초기화.
        """
        self.events = []
        self.metrics_history = []
        self.conflict_events = []
        self.collision_events = []
        self._start_time = None
        self._end_time = None
        self._last_collision_count = 0
        self._last_conflict_count = 0
        logger.info("SimulationAnalyticsHook reset")
