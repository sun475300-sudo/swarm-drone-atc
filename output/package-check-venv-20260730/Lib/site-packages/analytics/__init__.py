"""
공역 통제 분석 모듈
===================

분석 클래스들:
  PerformanceAnalyzer        — 충돌 해결률, 응답 시간, 처리량, 안전 메트릭
  SwarmMetricsCollector      — 드론/공역/기상 메트릭 수집 및 요약
  MonteCarloAnalyzer         — MC 스윕 결과 집계, 신뢰 구간, 임계 시나리오

사용 예시:
  from src.analytics import PerformanceAnalyzer, SwarmMetricsCollector, MonteCarloAnalyzer

  perf = PerformanceAnalyzer()
  safety = perf.calculate_safety_metrics(sim_data)

  collector = SwarmMetricsCollector()
  metrics = collector.collect_drone_metrics(drones)

  mc = MonteCarloAnalyzer()
  report = mc.generate_report(results_list)
"""

from src.analytics.core_analytics import (
    PerformanceAnalyzer,
    SwarmMetricsCollector,
    MonteCarloAnalyzer,
)

__all__ = [
    "PerformanceAnalyzer",
    "SwarmMetricsCollector",
    "MonteCarloAnalyzer",
]
