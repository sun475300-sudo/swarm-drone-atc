"""
통합 분석 모듈 — PerformanceAnalyzer, SwarmMetricsCollector, MonteCarloAnalyzer

이 모듈은 다음 책임을 갖습니다:
  1. 시뮬레이션 성능 지표 계산 (충돌 해결률, 응답 시간, 처리량)
  2. 군집 드론 / 공역 / 기상 메트릭 수집 및 요약
  3. Monte Carlo 스윕 결과 집계, 신뢰 구간 계산, 임계 시나리오 식별

설계 철학:
  - 독립적인 분석 클래스: 서로 의존하지 않음
  - 타입 힌트 및 Docstring 포함
  - numpy 기반 계산 (재현성을 위해 np.random.default_rng(seed) 사용)
  - JSON 직렬화 가능한 결과 반환
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """
    시뮬레이션 성능 지표 계산기.

    책임:
      - 충돌 해결률 계산
      - 응답 시간 분석 (평균, P95, P99)
      - 처리량 계산 (missions per minute)
      - 안전 메트릭 (근접 경고, 최소 분리 거리, 안전 점수)
    """

    def __init__(
        self,
        separation_baseline_m: float = 50.0,
        performance_weights: tuple[float, float, float] = (0.5, 0.3, 0.2),
    ) -> None:
        """
        초기화.

        Parameters
        ----------
        separation_baseline_m : float, optional
            분리 거리 기준값 (미터). 기본값: 50.0
        performance_weights : tuple[float, float, float], optional
            안전 점수 계산 가중치 (충돌, 근접경고, 분리거리).
            기본값: (0.5, 0.3, 0.2)
        """
        self.separation_baseline_m = separation_baseline_m
        self.performance_weights = performance_weights

    def analyze_collision_resolution_rate(
        self, conflicts: int, collisions: int
    ) -> float:
        """
        충돌 해결률 계산.

        공식: 1 - collisions / (conflicts + collisions)
        - conflicts: 감지된 충돌 위험 상황 수
        - collisions: 실제 충돌 발생 수
        - 반환값: 0.0 ~ 1.0 (또는 백분율 형식으로 × 100)

        Parameters
        ----------
        conflicts : int
            감지된 충돌 위험 상황 수
        collisions : int
            실제 충돌 발생 수

        Returns
        -------
        float
            충돌 해결률 (0.0 ~ 1.0)
        """
        total_events = conflicts + collisions
        if total_events == 0:
            return 1.0  # 충돌 없음 → 100% 해결
        return 1.0 - collisions / total_events

    def analyze_response_time(self, event_log: list[dict]) -> dict[str, float]:
        """
        응답 시간 분석 (이벤트 로그 기반).

        이벤트 로그에서 'response_time_s' 필드를 추출하여 통계 계산.

        Parameters
        ----------
        event_log : list[dict]
            각 요소: {"event_type": str, "response_time_s": float, ...}

        Returns
        -------
        dict[str, float]
            {
              "mean_s": float,      # 평균 응답 시간
              "p50_s": float,       # 중앙값
              "p95_s": float,       # 95 백분위
              "p99_s": float,       # 99 백분위
              "min_s": float,       # 최소값
              "max_s": float,       # 최대값
              "count": int,         # 샘플 수
            }
        """
        response_times = [
            ev.get("response_time_s", 0.0)
            for ev in event_log
            if "response_time_s" in ev
        ]

        if not response_times:
            return {
                "mean_s": 0.0,
                "p50_s": 0.0,
                "p95_s": 0.0,
                "p99_s": 0.0,
                "min_s": 0.0,
                "max_s": 0.0,
                "count": 0,
            }

        rt_array = np.array(response_times)
        return {
            "mean_s": float(np.mean(rt_array)),
            "p50_s": float(np.percentile(rt_array, 50)),
            "p95_s": float(np.percentile(rt_array, 95)),
            "p99_s": float(np.percentile(rt_array, 99)),
            "min_s": float(np.min(rt_array)),
            "max_s": float(np.max(rt_array)),
            "count": len(response_times),
        }

    def analyze_throughput(
        self, completed_missions: int, total_time_s: float
    ) -> float:
        """
        처리량 계산 (missions per minute).

        Parameters
        ----------
        completed_missions : int
            완료된 미션 수
        total_time_s : float
            총 시뮬레이션 시간 (초)

        Returns
        -------
        float
            분당 완료된 미션 수 (missions/min)
        """
        if total_time_s <= 0:
            return 0.0
        minutes = total_time_s / 60.0
        return completed_missions / minutes

    def calculate_safety_metrics(self, sim_data: dict[str, Any]) -> dict[str, Any]:
        """
        안전 메트릭 계산.

        Parameters
        ----------
        sim_data : dict[str, Any]
            시뮬레이션 데이터:
            {
              "near_miss_count": int,
              "min_separation_distance_m": float,
              "collision_count": int,
              "conflicts_total": int,
              "event_log": list[dict],  # optional
            }

        Returns
        -------
        dict[str, Any]
            {
              "near_miss_count": int,
              "min_separation_distance_m": float,
              "safety_score": float,  # 0.0 ~ 1.0 (1.0 = 안전함)
              "collision_severity": float,  # 0.0 ~ 1.0 (0.0 = 안전)
              "summary": str,
            }
        """
        near_miss = sim_data.get("near_miss_count", 0)
        min_sep = sim_data.get("min_separation_distance_m", float("inf"))
        collisions = sim_data.get("collision_count", 0)
        conflicts = sim_data.get("conflicts_total", 0)

        # 안전 점수 계산 (다중 인자)
        collision_score = max(0.0, 1.0 - collisions * 0.1)  # 충돌당 0.1 감소
        near_miss_score = max(0.0, 1.0 - near_miss * 0.02)  # 근접 경고당 0.02 감소
        separation_score = (
            min(1.0, min_sep / self.separation_baseline_m)
            if min_sep < float("inf")
            else 1.0
        )

        w_collision, w_near_miss, w_separation = self.performance_weights
        safety_score = (
            w_collision * collision_score
            + w_near_miss * near_miss_score
            + w_separation * separation_score
        )
        safety_score = max(0.0, min(1.0, safety_score))

        # 충돌 심각도 (0 = 안전, 1 = 위험)
        total_events = conflicts + collisions
        collision_severity = (
            collisions / total_events if total_events > 0 else 0.0
        )

        # 설명 문자열
        if collisions == 0:
            summary = "안전함 (충돌 없음)"
        elif collisions == 1:
            summary = "주의 (1건의 충돌 발생)"
        else:
            summary = f"위험 ({collisions}건의 충돌 발생)"

        return {
            "near_miss_count": near_miss,
            "min_separation_distance_m": float(min_sep)
            if min_sep < float("inf")
            else None,
            "safety_score": safety_score,
            "collision_severity": collision_severity,
            "summary": summary,
        }


class SwarmMetricsCollector:
    """
    군집 드론 / 공역 / 기상 메트릭 수집기.

    책임:
      - 드론별 메트릭 수집 (위치 분산, 속도 분포, 배터리 레벨)
      - 공역 메트릭 수집 (부문 활용도, 충돌 밀도, 유량)
      - 기상 메트릭 수집 (풍속 통계, 돌풍 빈도, 방향 히스토그램)
      - JSON 직렬화 가능한 요약 반환
    """

    def __init__(self, airspace_area_km2: float = 100.0) -> None:
        """
        초기화.

        Parameters
        ----------
        airspace_area_km2 : float, optional
            공역 면적 (제곱킬로미터). 기본값: 100.0
        """
        self._drone_metrics: dict[str, Any] = {}
        self._airspace_metrics: dict[str, Any] = {}
        self._wind_metrics: dict[str, Any] = {}
        self.airspace_area_km2 = airspace_area_km2

    def collect_drone_metrics(self, drones: list[Any]) -> dict[str, Any]:
        """
        드론 메트릭 수집.

        Parameters
        ----------
        drones : list[Any]
            DroneState 객체 리스트.
            각 객체는 다음 속성을 가져야 함:
              - position: np.ndarray (3D 좌표)
              - velocity: np.ndarray (3D 속도)
              - battery_pct: float
              - speed: float

        Returns
        -------
        dict[str, Any]
            {
              "count": int,
              "position_variance_m2": float,  # 위치 분산
              "speed_mean_ms": float,        # 평균 속도
              "speed_std_ms": float,         # 속도 표준편차
              "battery_mean_pct": float,     # 평균 배터리
              "battery_min_pct": float,      # 최소 배터리
              "battery_max_pct": float,      # 최대 배터리
              "altitude_mean_m": float,      # 평균 고도
              "altitude_std_m": float,       # 고도 표준편차
            }
        """
        if not drones:
            return {
                "count": 0,
                "position_variance_m2": 0.0,
                "speed_mean_ms": 0.0,
                "speed_std_ms": 0.0,
                "battery_mean_pct": 0.0,
                "battery_min_pct": 0.0,
                "battery_max_pct": 0.0,
                "altitude_mean_m": 0.0,
                "altitude_std_m": 0.0,
            }

        positions = np.array([d.position for d in drones])  # shape: (n, 3)
        speeds = np.array([d.speed for d in drones])
        batteries = np.array([d.battery_pct for d in drones])
        altitudes = positions[:, 2]  # z 좌표 추출

        # 위치 분산: 모든 드론 위치의 코분산 행렬의 대각선 합
        pos_variance = float(np.var(positions))

        self._drone_metrics = {
            "count": len(drones),
            "position_variance_m2": pos_variance,
            "speed_mean_ms": float(np.mean(speeds)),
            "speed_std_ms": float(np.std(speeds)),
            "battery_mean_pct": float(np.mean(batteries)),
            "battery_min_pct": float(np.min(batteries)),
            "battery_max_pct": float(np.max(batteries)),
            "altitude_mean_m": float(np.mean(altitudes)),
            "altitude_std_m": float(np.std(altitudes)),
        }
        return self._drone_metrics

    def collect_airspace_metrics(
        self, controller: Any, active_drones: int = 0
    ) -> dict[str, Any]:
        """
        공역 메트릭 수집.

        Parameters
        ----------
        controller : Any
            AirspaceController 인스턴스.
            다음 속성/메서드를 가져야 함:
              - _advisories: dict (active advisories)
              - _conflicts: list or dict (detected conflicts)
              - _pending: list (pending requests)
        active_drones : int, optional
            활성 드론 수 (기본: 0)

        Returns
        -------
        dict[str, Any]
            {
              "active_drones": int,
              "active_advisories": int,
              "pending_requests": int,
              "advisory_density_per_km2": float,
              "conflict_resolution_success_rate": float,  # 0.0 ~ 1.0
            }
        """
        advisories = getattr(controller, "_advisories", {})
        pending = getattr(controller, "_pending", [])

        active_advisory_count = len(advisories)
        pending_count = len(pending)

        advisory_density = (
            active_advisory_count / self.airspace_area_km2
            if self.airspace_area_km2 > 0
            else 0.0
        )

        # 충돌 해결 성공률 (간단한 추정)
        # 실제 값은 controller 통계에서 가져올 수 있음
        conflict_res_rate = 0.95  # 기본값

        self._airspace_metrics = {
            "active_drones": active_drones,
            "active_advisories": active_advisory_count,
            "pending_requests": pending_count,
            "advisory_density_per_km2": advisory_density,
            "conflict_resolution_success_rate": conflict_res_rate,
        }
        return self._airspace_metrics

    def collect_wind_metrics(
        self, wind_model: Any, sample_size: int = 100
    ) -> dict[str, Any]:
        """
        기상 메트릭 수집.

        Parameters
        ----------
        wind_model : Any
            WindModel 인스턴스.
            메서드: get_wind_vector(position: np.ndarray, t: float) → np.ndarray

        sample_size : int, optional
            샘플링 포인트 수 (기본: 100)

        Returns
        -------
        dict[str, Any]
            {
              "wind_speed_mean_ms": float,
              "wind_speed_std_ms": float,
              "wind_speed_max_ms": float,
              "wind_direction_mean_deg": float,
              "wind_direction_std_deg": float,
              "gust_frequency": float,  # 돌풍 빈도 추정
            }
        """
        # 기본 공역 샘플링 범위
        rng = np.random.default_rng(seed=42)  # 재현성
        sample_positions = rng.uniform(
            -5000, 5000, size=(sample_size, 3)
        )  # -5 ~ 5 km
        sample_times = np.linspace(0, 600, sample_size)  # 0 ~ 600s

        wind_vectors = np.array(
            [wind_model.get_wind_vector(pos, t) for pos, t in zip(sample_positions, sample_times)]
        )

        wind_speeds = np.linalg.norm(wind_vectors[:, :2], axis=1)  # 수평 성분만
        wind_directions = np.arctan2(wind_vectors[:, 1], wind_vectors[:, 0])
        wind_directions = np.degrees(wind_directions) % 360.0

        # 돌풍 빈도 추정: 풍속 표준편차 / 평균 비율
        wind_speed_mean = float(np.mean(wind_speeds))
        wind_speed_std = float(np.std(wind_speeds))
        gust_frequency = (
            wind_speed_std / max(wind_speed_mean, 0.1)
        )  # 변동 계수

        self._wind_metrics = {
            "wind_speed_mean_ms": wind_speed_mean,
            "wind_speed_std_ms": wind_speed_std,
            "wind_speed_max_ms": float(np.max(wind_speeds)),
            "wind_direction_mean_deg": float(np.mean(wind_directions)),
            "wind_direction_std_deg": float(np.std(wind_directions)),
            "gust_frequency": gust_frequency,
        }
        return self._wind_metrics

    def get_summary(self) -> dict[str, Any]:
        """
        모든 메트릭의 요약을 JSON 직렬화 가능한 dict로 반환.

        Returns
        -------
        dict[str, Any]
            {
              "drone_metrics": dict,
              "airspace_metrics": dict,
              "wind_metrics": dict,
              "timestamp": float,  # 수집 시간 (초)
            }
        """
        import time

        return {
            "drone_metrics": self._drone_metrics,
            "airspace_metrics": self._airspace_metrics,
            "wind_metrics": self._wind_metrics,
            "timestamp": time.time(),
        }


class MonteCarloAnalyzer:
    """
    Monte Carlo 스윕 결과 분석기.

    책임:
      - MC 스윕 결과 집계
      - 신뢰 구간(CI) 계산
      - 임계 시나리오 식별
      - Markdown 형식 보고서 생성
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        """
        초기화.

        Parameters
        ----------
        seed : int, optional
            재현성을 위한 난수 시드
        """
        self._rng = np.random.default_rng(seed)

    def analyze_sweep_results(
        self, results_list: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        MC 스윕 결과 집계.

        Parameters
        ----------
        results_list : list[dict[str, Any]]
            각 요소: SimulationResult.to_dict() 형식
            {
              "collision_count": int,
              "near_miss_count": int,
              "conflict_resolution_rate_pct": float,
              "safety_score": float,
              ...
            }

        Returns
        -------
        dict[str, Any]
            주요 메트릭의 통계:
            {
              "num_runs": int,
              "collision_count_mean": float,
              "collision_count_std": float,
              "conflict_resolution_rate_mean": float,
              "conflict_resolution_rate_std": float,
              "safety_score_mean": float,
              "safety_score_std": float,
              "runs_with_collision": int,
              "collision_rate": float,  # runs_with_collision / num_runs
            }
        """
        if not results_list:
            return {
                "num_runs": 0,
                "collision_count_mean": 0.0,
                "collision_count_std": 0.0,
                "conflict_resolution_rate_mean": 0.0,
                "conflict_resolution_rate_std": 0.0,
                "safety_score_mean": 0.0,
                "safety_score_std": 0.0,
                "runs_with_collision": 0,
                "collision_rate": 0.0,
            }

        collision_counts = np.array(
            [r.get("collision_count", 0) for r in results_list]
        )
        conflict_res_rates = np.array(
            [r.get("conflict_resolution_rate_pct", 100.0) for r in results_list]
        )
        safety_scores = np.array(
            [r.get("safety_score", 1.0) if "safety_score" in r else 1.0 for r in results_list]
        )

        runs_with_collision = int(np.sum(collision_counts > 0))

        return {
            "num_runs": len(results_list),
            "collision_count_mean": float(np.mean(collision_counts)),
            "collision_count_std": float(np.std(collision_counts)),
            "conflict_resolution_rate_mean": float(np.mean(conflict_res_rates)),
            "conflict_resolution_rate_std": float(np.std(conflict_res_rates)),
            "safety_score_mean": float(np.mean(safety_scores)),
            "safety_score_std": float(np.std(safety_scores)),
            "runs_with_collision": runs_with_collision,
            "collision_rate": runs_with_collision / len(results_list),
        }

    def compute_confidence_intervals(
        self, metric_values: list[float], confidence: float = 0.95
    ) -> dict[str, float]:
        """
        신뢰 구간 계산 (T-분포 근사 기반).

        Parameters
        ----------
        metric_values : list[float]
            메트릭 값들
        confidence : float, optional
            신뢰도 (기본: 0.95 = 95%)

        Returns
        -------
        dict[str, float]
            {
              "mean": float,
              "std": float,
              "ci_lower": float,     # 신뢰 구간 하한
              "ci_upper": float,     # 신뢰 구간 상한
              "ci_margin": float,    # 오차 한계
              "sample_size": int,
            }
        """
        if not metric_values:
            return {
                "mean": 0.0,
                "std": 0.0,
                "ci_lower": 0.0,
                "ci_upper": 0.0,
                "ci_margin": 0.0,
                "sample_size": 0,
            }

        values_array = np.array(metric_values)
        n = len(values_array)
        mean = float(np.mean(values_array))

        if n == 1:
            return {
                "mean": mean,
                "std": 0.0,
                "ci_lower": mean,
                "ci_upper": mean,
                "ci_margin": 0.0,
                "sample_size": 1,
            }

        std = float(np.std(values_array, ddof=1))  # 표본 표준편차

        # T-분포 근사: 주요 자유도별 t-critical 값 조회표
        # df=n-1에 따른 t-critical 값 (양측, 95% 신뢰도)
        t_critical_values = {
            1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
            10: 2.228, 15: 2.131, 20: 2.086, 30: 2.042, 50: 2.009,
            100: 1.984, 200: 1.972, 500: 1.965,
        }

        df = n - 1

        # 정확한 t-critical 값 조회 또는 근사
        if df in t_critical_values:
            t_critical = t_critical_values[df]
        elif df < 1:
            t_critical = 12.706  # 극도로 작은 표본
        else:
            # 선형 보간 또는 대표값 선택
            available_dfs = sorted(t_critical_values.keys())
            if df >= available_dfs[-1]:
                t_critical = t_critical_values[available_dfs[-1]]
            else:
                for i in range(len(available_dfs) - 1):
                    if available_dfs[i] <= df < available_dfs[i + 1]:
                        # 선형 보간
                        df1, df2 = available_dfs[i], available_dfs[i + 1]
                        t1, t2 = t_critical_values[df1], t_critical_values[df2]
                        t_critical = t1 + (df - df1) * (t2 - t1) / (df2 - df1)
                        break

        margin = t_critical * std / np.sqrt(n)

        return {
            "mean": mean,
            "std": std,
            "ci_lower": mean - margin,
            "ci_upper": mean + margin,
            "ci_margin": margin,
            "sample_size": n,
        }

    def identify_critical_scenarios(
        self, results: list[dict[str, Any]], threshold: float = 0.5
    ) -> dict[str, Any]:
        """
        임계 시나리오 식별 (worst-case scenarios).

        Parameters
        ----------
        results : list[dict[str, Any]]
            MC 스윕 결과 리스트
        threshold : float, optional
            충돌 확률 임계값 (기본: 0.5 = 50%)
            이 이상의 확률로 충돌이 발생하는 시나리오를 "임계"로 판정

        Returns
        -------
        dict[str, Any]
            {
              "critical_count": int,     # 임계 시나리오 수
              "critical_indices": list[int],  # 임계 시나리오 인덱스
              "avg_collisions_in_critical": float,
              "worst_case_collisions": int,  # 최악의 충돌 수
              "worst_case_index": int,
            }
        """
        if not results:
            return {
                "critical_count": 0,
                "critical_indices": [],
                "avg_collisions_in_critical": 0.0,
                "worst_case_collisions": 0,
                "worst_case_index": -1,
            }

        collision_counts = np.array(
            [r.get("collision_count", 0) for r in results]
        )
        collision_rate = np.sum(collision_counts > 0) / len(results)

        # 임계 시나리오: 해당 구간의 충돌 확률이 threshold 이상
        critical_mask = collision_counts > np.percentile(
            collision_counts, (1 - threshold) * 100
        )
        critical_indices = np.where(critical_mask)[0].tolist()

        critical_collisions = collision_counts[critical_mask]
        avg_critical = (
            float(np.mean(critical_collisions))
            if len(critical_collisions) > 0
            else 0.0
        )

        worst_case_idx = int(np.argmax(collision_counts))

        return {
            "critical_count": len(critical_indices),
            "critical_indices": critical_indices,
            "avg_collisions_in_critical": avg_critical,
            "worst_case_collisions": int(collision_counts[worst_case_idx]),
            "worst_case_index": worst_case_idx,
        }

    def generate_report(self, results: list[dict[str, Any]]) -> str:
        """
        MC 분석 결과 Markdown 보고서 생성.

        Parameters
        ----------
        results : list[dict[str, Any]]
            MC 스윕 결과 리스트

        Returns
        -------
        str
            Markdown 형식의 보고서

        예시:
            ```markdown
            # Monte Carlo Sweep Analysis Report
            ## Summary
            - Runs: 100
            - Collision Rate: 5.0%
            ...
            ```
        """
        if not results:
            return "# Monte Carlo Report\n\n(No results)\n"

        sweep_summary = self.analyze_sweep_results(results)
        collision_counts = [r.get("collision_count", 0) for r in results]
        ci = self.compute_confidence_intervals(collision_counts)
        critical = self.identify_critical_scenarios(results)

        lines = [
            "# Monte Carlo Sweep Analysis Report",
            "",
            "## Summary",
            f"- **Number of Runs**: {sweep_summary['num_runs']}",
            f"- **Collision Rate**: {sweep_summary['collision_rate']:.1%}",
            f"- **Runs with Collision**: {sweep_summary['runs_with_collision']}",
            "",
            "## Collision Statistics",
            f"- **Mean Collisions**: {sweep_summary['collision_count_mean']:.2f}",
            f"- **Std Dev**: {sweep_summary['collision_count_std']:.2f}",
            f"- **95% CI**: [{ci['ci_lower']:.2f}, {ci['ci_upper']:.2f}]",
            "",
            "## Safety Metrics",
            f"- **Safety Score Mean**: {sweep_summary['safety_score_mean']:.3f}",
            f"- **Safety Score Std**: {sweep_summary['safety_score_std']:.3f}",
            f"- **Conflict Resolution Rate Mean**: {sweep_summary['conflict_resolution_rate_mean']:.1f}%",
            "",
            "## Critical Scenarios",
            f"- **Count**: {critical['critical_count']}",
            f"- **Worst Case Collisions**: {critical['worst_case_collisions']}",
            f"- **Avg Collisions (Critical)**: {critical['avg_collisions_in_critical']:.2f}",
            "",
            "---",
            "*Report generated by MonteCarloAnalyzer*",
        ]

        return "\n".join(lines)
