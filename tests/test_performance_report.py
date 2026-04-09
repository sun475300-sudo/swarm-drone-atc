"""
성능 분석 리포트 생성기
======================
시뮬레이션 결과를 기반으로 차트/리포트 생성
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import numpy as np


@dataclass
class PerformanceMetrics:
    """성능 지표"""

    total_drones: int
    duration_s: int
    conflicts: int
    collisions: int
    advisories: int
    near_misses: int
    clearances_approved: int
    clearances_denied: int
    cbs_success: int
    cbs_fallback: int
    astar_calls: int
    comm_sent: int
    comm_delivered: int
    comm_dropped: float
    avg_speed_ms: float
    total_distance_km: float
    energy_efficiency_wh_km: float
    advisory_latency_p50_s: float
    advisory_latency_p99_s: float


class PerformanceReport:
    """성능 분석 리포트 생성"""

    def __init__(self, output_dir: str = "data/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.history: list[PerformanceMetrics] = []

    def generate_from_simulation(self, metrics: dict) -> PerformanceMetrics:
        """시뮬레이션 결과에서 성능 지표 생성"""
        m = PerformanceMetrics(
            total_drones=metrics.get("total_drones", 100),
            duration_s=metrics.get("duration_s", 30),
            conflicts=metrics.get("conflicts", 0),
            collisions=metrics.get("collisions", 0),
            advisories=metrics.get("advisories_issued", 0),
            near_misses=metrics.get("near_misses", 0),
            clearances_approved=metrics.get("clearances_approved", 0),
            clearances_denied=metrics.get("clearances_denied", 0),
            cbs_success=metrics.get("cbs_success", 0),
            cbs_fallback=metrics.get("cbs_fallback", 0),
            astar_calls=metrics.get("astar_calls", 0),
            comm_sent=metrics.get("comm_sent", 0),
            comm_delivered=metrics.get("comm_delivered", 0),
            comm_dropped=metrics.get("comm_dropped_pct", 0.0),
            avg_speed_ms=metrics.get("avg_speed_ms", 0.0),
            total_distance_km=metrics.get("total_distance_km", 0.0),
            energy_efficiency_wh_km=metrics.get("energy_efficiency_wh_km", 0.0),
            advisory_latency_p50_s=metrics.get("advisory_latency_p50_s", 0.0),
            advisory_latency_p99_s=metrics.get("advisory_latency_p99_s", 0.0),
        )

        self.history.append(m)
        self._save_metrics(m)

        return m

    def _save_metrics(self, m: PerformanceMetrics) -> None:
        """메트릭 JSON 저장"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "total_drones": m.total_drones,
            "duration_s": m.duration_s,
            "conflicts": m.conflicts,
            "collisions": m.collisions,
            "advisories": m.advisories,
            "resolution_rate": (m.advisories / m.conflicts * 100) if m.conflicts > 0 else 100.0,
            "near_misses": m.near_misses,
            "clearances": f"{m.clearances_approved}/{m.clearances_denied}",
            "cbs_stats": f"{m.cbs_success}/{m.cbs_fallback}",
            "comm_stats": f"{m.comm_delivered}/{m.comm_sent} ({m.comm_dropped:.1f}%)",
            "avg_speed_ms": round(m.avg_speed_ms, 1),
            "total_distance_km": round(m.total_distance_km, 1),
        }

        filepath = self.output_dir / f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def generate_charts(self) -> dict[str, Any]:
        """차트 데이터 생성"""
        if not self.history:
            return {}

        # 충돌 해결률 추이
        resolution_rates = []
        timestamps = []
        for m in self.history:
            rate = (m.advisories / m.conflicts * 100) if m.conflicts > 0 else 100.0
            resolution_rates.append(rate)
            timestamps.append(f"{m.total_drones}d")

        # 드론 수별 성능
        drone_counts = [m.total_drones for m in self.history]
        distances = [m.total_distance_km for m in self.history]

        return {
            "resolution_rate_trend": {
                "labels": timestamps,
                "values": resolution_rates,
            },
            "drone_count_vs_distance": {
                "x": drone_counts,
                "y": distances,
            },
            "current_metrics": {
                "conflicts": self.history[-1].conflicts,
                "advisories": self.history[-1].advisories,
                "collisions": self.history[-1].collisions,
                "resolution_rate": (self.history[-1].advisories / self.history[-1].conflicts * 100)
                if self.history[-1].conflicts > 0
                else 100.0,
            },
        }

    def generate_html_report(self) -> str:
        """HTML 리포트 생성"""
        charts = self.generate_charts()
        current = charts.get("current_metrics", {})

        html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SDACS 성능 분석 리포트</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }}
        .header h1 {{ font-size: 24px; color: #58a6ff; }}
        .timestamp {{ color: #8b949e; font-size: 14px; }}
        .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }}
        .stat-card {{ background: #161b22; padding: 20px; border-radius: 8px; text-align: center; }}
        .stat-card .label {{ font-size: 12px; color: #8b949e; margin-bottom: 8px; }}
        .stat-card .value {{ font-size: 32px; font-weight: bold; }}
        .stat-card.conflicts .value {{ color: #f85149; }}
        .stat-card.advisories .value {{ color: #3fb950; }}
        .stat-card.collisions .value {{ color: #d29922; }}
        .stat-card.resolution .value {{ color: #58a6ff; }}
        .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }}
        .chart-card {{ background: #161b22; padding: 20px; border-radius: 8px; }}
        .chart-card h3 {{ margin-bottom: 15px; color: #58a6ff; }}
        .summary {{ background: #161b22; padding: 20px; border-radius: 8px; margin-top: 20px; }}
        .summary h3 {{ color: #58a6ff; margin-bottom: 15px; }}
        .summary table {{ width: 100%; border-collapse: collapse; }}
        .summary th, .summary td {{ padding: 10px; text-align: left; border-bottom: 1px solid #30363d; }}
        .summary th {{ color: #8b949e; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>📊 SDACS 성능 분석 리포트</h1>
            <div class="timestamp">생성: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
        </div>
    </div>
    
    <div class="stats">
        <div class="stat-card conflicts">
            <div class="label">충돌 감지</div>
            <div class="value">{current.get("conflicts", 0)}</div>
        </div>
        <div class="stat-card advisories">
            <div class="label">어드바이저리 발령</div>
            <div class="value">{current.get("advisories", 0)}</div>
        </div>
        <div class="stat-card collisions">
            <div class="label">실제 충돌</div>
            <div class="value">{current.get("collisions", 0)}</div>
        </div>
        <div class="stat-card resolution">
            <div class="label">해결률 (%)</div>
            <div class="value">{current.get("resolution_rate", 0):.1f}%</div>
        </div>
    </div>
    
    <div class="grid">
        <div class="chart-card">
            <h3>📈 충돌 해결률 추이</h3>
            <div id="resolutionChart"></div>
        </div>
        <div class="chart-card">
            <h3>🚁 드론 수 vs 비행 거리</h3>
            <div id="distanceChart"></div>
        </div>
    </div>
    
    <div class="summary">
        <h3>📋 상세 분석</h3>
        <table>
            <tr><th>지표</th><th>값</th><th>비고</th></tr>
            <tr><td>총 드론 수</td><td>{current.get("total_drones", "-")}</td><td>시뮬레이션 설정</td></tr>
            <tr><td>충돌 감지</td><td>{current.get("conflicts", "-")}</td><td>CPA 기반</td></tr>
            <tr><td>어드바이저리</td><td>{current.get("advisories", "-")}</td><td>회피 명령</td></tr>
            <tr><td>실제 충돌</td><td>{current.get("collisions", "-")}</td><td>잔여 충돌</td></tr>
            <tr><td>해결률</td><td>{current.get("resolution_rate", 0):.1f}%</td><td>어드바이저리/충돌</td></tr>
        </table>
    </div>
    
    <script>
        const resolutionData = {json.dumps(charts.get("resolution_rate_trend", {}))};
        const distanceData = {json.dumps(charts.get("drone_count_vs_distance", {}))};
        
        if (resolutionData.labels) {{
            Plotly.newPlot('resolutionChart', [{{
                x: resolutionData.labels,
                y: resolutionData.values,
                type: 'scatter',
                mode: 'lines+markers',
                line: {{ color: '#58a6ff', width: 2 }},
                marker: {{ color: '#58a6ff', size: 8 }}
            }}], {{
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                xaxis: {{ color: '#8b949e' }},
                yaxis: {{ color: '#8b949e', range: [0, 100] }},
                yaxis: {{ title: '해결률 (%)' }}
            }}, {{ responsive: true }});
        }}
        
        if (distanceData.x) {{
            Plotly.newPlot('distanceChart', [{{
                x: distanceData.x,
                y: distanceData.y,
                type: 'bar',
                marker: {{ color: '#3fb950' }}
            }}], {{
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                xaxis: {{ title: '드론 수', color: '#8b949e' }},
                yaxis: {{ title: '비행 거리 (km)', color: '#8b949e' }}
            }}, {{ responsive: true }});
        }}
    </script>
</body>
</html>
"""
        return html

    def save_report(self, filepath: Optional[str] = None) -> str:
        """리포트 HTML 저장"""
        if filepath is None:
            filepath = self.output_dir / f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

        html = self.generate_html_report()

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        return str(filepath)


if __name__ == "__main__":
    print("=== SDACS 성능 분석 리포트 ===\n")

    # 샘플 데이터로 테스트
    report = PerformanceReport()

    # 시뮬레이션 결과에서 메트릭 생성 (예시)
    sample_metrics = {
        "total_drones": 100,
        "duration_s": 30,
        "conflicts": 49,
        "collisions": 0,
        "advisories_issued": 33,
        "near_misses": 2,
        "clearances_approved": 68,
        "clearances_denied": 27,
        "cbs_success": 16,
        "cbs_fallback": 0,
        "astar_calls": 7,
        "comm_sent": 6139,
        "comm_delivered": 6139,
        "comm_dropped_pct": 0.0,
        "avg_speed_ms": 8.5,
        "total_distance_km": 6.1,
        "energy_efficiency_wh_km": 529.53,
        "advisory_latency_p50_s": 0.0,
        "advisory_latency_p99_s": 0.0,
    }

    m = report.generate_from_simulation(sample_metrics)
    print(
        f"메트릭 생성: 충돌={m.conflicts}, 어드바이저리={m.advisories}, 해결률={m.advisories / m.conflicts * 100:.1f}%"
    )

    # HTML 리포트 저장
    path = report.save_report()
    print(f"리포트 저장: {path}")

    print("\n=== 완료 ===")
