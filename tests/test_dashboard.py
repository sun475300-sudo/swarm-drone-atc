"""
테스트 결과 대시보드 및 스케줄러
===============================
- 테스트 결과 대시보드 UI (차트/그래프)
- 테스트 스케줄링 (정기 실행)
- 테스트 비교 분석
- 커스텀 테스트 시나리오 정의
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional

import numpy as np


@dataclass
class SuiteTestResult:
    """단일 테스트 결과"""

    name: str
    status: str  # PASSED, FAILED, SKIPPED, ERROR
    duration_ms: float
    timestamp: str
    error_message: Optional[str] = None


@dataclass
class SuiteResult:
    """테스트 스위트 결과"""

    name: str
    total: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration_s: float
    timestamp: str
    results: list[SuiteTestResult] = field(default_factory=list)


class DashboardRunner:
    """테스트 결과 대시보드"""

    def __init__(self, output_dir: str = "data/test_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.history: list[SuiteResult] = []

    def run_tests(
        self,
        test_path: str = "tests/",
        timeout: int = 300,
        verbose: bool = True,
    ) -> SuiteResult:
        """pytest 실행 및 결과 수집"""
        start_time = time.time()

        cmd = [
            "pytest",
            test_path,
            "-v",
            "--tb=short",
            f"--timeout={timeout}",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 30,
            )
            duration = time.time() - start_time

            # 결과 파싱 (stdout에서 라인별 파싱)
            lines = result.stdout.split("\n")
            passed = sum(1 for l in lines if " PASSED" in l)
            failed = sum(1 for l in lines if " FAILED" in l)
            skipped = sum(1 for l in lines if " SKIPPED" in l)
            errors = sum(1 for l in lines if " ERROR" in l)

            total = passed + failed + skipped + errors

            suite_result = SuiteResult(
                name=test_path,
                total=total,
                passed=passed,
                failed=failed,
                skipped=skipped,
                errors=errors,
                duration_s=duration,
                timestamp=datetime.now().isoformat(),
            )

            self.history.append(suite_result)
            self._save_result(suite_result)

            return suite_result

        except subprocess.TimeoutExpired:
            return SuiteResult(
                name=test_path,
                total=0,
                passed=0,
                failed=0,
                skipped=0,
                errors=1,
                duration_s=time.time() - start_time,
                timestamp=datetime.now().isoformat(),
                results=[
                    SuiteTestResult(
                        name="TIMEOUT", status="ERROR", duration_ms=0, timestamp="", error_message="Test timeout"
                    )
                ],
            )

    def _save_result(self, result: SuiteResult) -> None:
        """결과를 JSON으로 저장"""
        report_file = self.output_dir / f"test_{result.timestamp.replace(':', '-')}.json"

        data = {
            "name": result.name,
            "total": result.total,
            "passed": result.passed,
            "failed": result.failed,
            "skipped": result.skipped,
            "errors": result.errors,
            "duration_s": result.duration_s,
            "timestamp": result.timestamp,
        }

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def generate_charts(self) -> dict[str, Any]:
        """차트 데이터 생성"""
        if not self.history:
            return {}

        # 통과율 추이
        success_rates = []
        timestamps = []
        for r in self.history:
            rate = (r.passed / r.total * 100) if r.total > 0 else 0
            success_rates.append(rate)
            timestamps.append(r.timestamp[:10])

        # 테스트별 소요 시간
        durations = [r.duration_s for r in self.history]

        # 상태 분포 (가장 최근)
        latest = self.history[-1]
        status_dist = {
            "passed": latest.passed,
            "failed": latest.failed,
            "skipped": latest.skipped,
            "errors": latest.errors,
        }

        return {
            "success_rate_trend": {
                "labels": timestamps,
                "values": success_rates,
            },
            "duration_trend": {
                "labels": timestamps,
                "values": durations,
            },
            "status_distribution": status_dist,
        }

    def generate_dashboard_html(self) -> str:
        """대시보드 HTML 생성"""
        charts = self.generate_charts()

        html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SDACS 테스트 대시보드</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }}
        .header h1 {{ font-size: 24px; color: #58a6ff; }}
        .stats {{ display: flex; gap: 20px; }}
        .stat-card {{ background: #161b22; padding: 20px; border-radius: 8px; min-width: 150px; }}
        .stat-card .label {{ font-size: 12px; color: #8b949e; }}
        .stat-card .value {{ font-size: 28px; font-weight: bold; margin-top: 5px; }}
        .stat-card.passed .value {{ color: #3fb950; }}
        .stat-card.failed .value {{ color: #f85149; }}
        .stat-card.skipped .value {{ color: #d29922; }}
        .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }}
        .chart-card {{ background: #161b22; padding: 20px; border-radius: 8px; }}
        .chart-card h3 {{ margin-bottom: 15px; color: #58a6ff; }}
        .run-btn {{ background: #238636; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 14px; }}
        .run-btn:hover {{ background: #2ea043; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 SDACS 테스트 대시보드</h1>
        <button class="run-btn" onclick="location.reload()">🔄 새로고침</button>
    </div>
    
    <div class="stats">
        <div class="stat-card passed">
            <div class="label">통과</div>
            <div class="value">{charts.get("status_distribution", {}).get("passed", 0)}</div>
        </div>
        <div class="stat-card failed">
            <div class="label">실패</div>
            <div class="value">{charts.get("status_distribution", {}).get("failed", 0)}</div>
        </div>
        <div class="stat-card skipped">
            <div class="label">건너뛰기</div>
            <div class="value">{charts.get("status_distribution", {}).get("skipped", 0)}</div>
        </div>
    </div>
    
    <br>
    
    <div class="grid">
        <div class="chart-card">
            <h3>📈 통과율 추이</h3>
            <div id="successChart"></div>
        </div>
        <div class="chart-card">
            <h3>⏱️ 테스트 소요 시간</h3>
            <div id="durationChart"></div>
        </div>
    </div>
    
    <script>
        const successData = {json.dumps(charts.get("success_rate_trend", {}))};
        const durationData = {json.dumps(charts.get("duration_trend", {}))};
        
        Plotly.newPlot('successChart', [{{
            x: successData.labels || [],
            y: successData.values || [],
            type: 'scatter',
            mode: 'lines+markers',
            line: {{ color: '#58a6ff', width: 2 }},
            marker: {{ color: '#58a6ff', size: 8 }}
        }}], {{
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            xaxis: {{ color: '#8b949e' }},
            yaxis: {{ color: '#8b949e', range: [0, 100] }}
        }}, {{ responsive: true }});
        
        Plotly.newPlot('durationChart', [{{
            x: durationData.labels || [],
            y: durationData.values || [],
            type: 'bar',
            marker: {{ color: '#3fb950' }}
        }}], {{
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            xaxis: {{ color: '#8b949e' }},
            yaxis: {{ color: '#8b949e' }}
        }}, {{ responsive: true }});
    </script>
</body>
</html>
"""
        return html

    def save_dashboard(self, filepath: Optional[str] = None) -> str:
        """대시보드 HTML 파일 저장"""
        if filepath is None:
            filepath = self.output_dir / "dashboard.html"

        html = self.generate_dashboard_html()

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        return str(filepath)


class SchedulerRunner:
    """테스트 스케줄러 (정기 실행)"""

    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback
        self.scheduled_jobs: list[dict] = []
        self.running = False

    def schedule(
        self,
        name: str,
        test_path: str,
        interval_minutes: int = 60,
        enabled: bool = True,
    ) -> None:
        """테스트 스케줄 추가"""
        job = {
            "name": name,
            "test_path": test_path,
            "interval_minutes": interval_minutes,
            "enabled": enabled,
            "last_run": None,
            "next_run": datetime.now(),
            "total_runs": 0,
            "success_count": 0,
        }
        self.scheduled_jobs.append(job)

    def run_scheduled(self) -> list[dict]:
        """정기 테스트 실행"""
        results = []
        now = datetime.now()

        for job in self.scheduled_jobs:
            if not job["enabled"]:
                continue

            if now >= job["next_run"]:
                print(f"🕐 실행: {job['name']}")

                dashboard = DashboardRunner()
                result = dashboard.run_tests(job["test_path"], timeout=300)

                job["last_run"] = now.isoformat()
                job["next_run"] = now + timedelta(minutes=job["interval_minutes"])
                job["total_runs"] += 1

                if result.passed > 0:
                    job["success_count"] += 1

                results.append(
                    {
                        "job": job["name"],
                        "result": result,
                        "success_rate": result.passed / result.total * 100 if result.total > 0 else 0,
                    }
                )

        return results

    def get_status(self) -> list[dict]:
        """스케줄 상태 조회"""
        return [
            {
                "name": job["name"],
                "test_path": job["test_path"],
                "interval_minutes": job["interval_minutes"],
                "enabled": job["enabled"],
                "last_run": job["last_run"],
                "next_run": job["next_run"].isoformat() if job["next_run"] else None,
                "total_runs": job["total_runs"],
                "success_rate": job["success_count"] / job["total_runs"] * 100 if job["total_runs"] > 0 else 0,
            }
            for job in self.scheduled_jobs
        ]


class ResultComparator:
    """테스트 비교 분석"""

    def __init__(self):
        self.baseline: Optional[SuiteResult] = None
        self.comparisons: list[dict] = []

    def set_baseline(self, result: SuiteResult) -> None:
        """베이스라인 설정"""
        self.baseline = result

    def compare(self, result: SuiteResult) -> dict[str, Any]:
        """베이스라인 대비 비교"""
        if self.baseline is None:
            self.baseline = result
            return {"status": "baseline_set", "result": result.name}

        comparison = {
            "name": result.name,
            "timestamp": result.timestamp,
            "baseline_timestamp": self.baseline.timestamp,
            "changes": {
                "total": result.total - self.baseline.total,
                "passed": result.passed - self.baseline.passed,
                "failed": result.failed - self.baseline.failed,
                "duration_s": result.duration_s - self.baseline.duration_s,
            },
            "regression": result.failed > self.baseline.failed,
            "improvement": result.passed > self.baseline.passed,
        }

        self.comparisons.append(comparison)

        return comparison

    def get_trend(self) -> dict[str, Any]:
        """추이 분석"""
        if not self.comparisons:
            return {}

        passed_trend = [c["changes"]["passed"] for c in self.comparisons]
        failed_trend = [c["changes"]["failed"] for c in self.comparisons]

        return {
            "total_comparisons": len(self.comparisons),
            "regressions": sum(1 for c in self.comparisons if c["regression"]),
            "improvements": sum(1 for c in self.comparisons if c["improvement"]),
            "passed_trend": passed_trend,
            "failed_trend": failed_trend,
        }

    def generate_report(self) -> str:
        """비교 리포트 생성"""
        trend = self.get_trend()

        if not trend:
            return "비교 데이터가 없습니다."

        report = f"""
## 테스트 비교 분석 리포트

### 전체 개요
- 총 비교 횟수: {trend["total_comparisons"]}
- 회귀 발생: {trend["regressions"]}회
- 개선 확인: {trend["improvements"]}회

### 통과율 추이
"""

        for i, comp in enumerate(self.comparisons):
            status = "⬆️" if comp["improvement"] else ("⬇️" if comp["regression"] else "➡️")
            report += f"- Run {i + 1}: {status} passed={comp['changes']['passed']:+d}, failed={comp['changes']['failed']:+d}\n"

        return report


class CustomTestScenario:
    """커스텀 테스트 시나리오 정의"""

    def __init__(self, name: str):
        self.name = name
        self.tests: list[dict] = []
        self.config: dict = {}

    def add_test(
        self,
        test_file: str,
        markers: Optional[list[str]] = None,
        kwargs: Optional[dict] = None,
    ) -> "CustomTestScenario":
        """테스트 추가"""
        self.tests.append(
            {
                "file": test_file,
                "markers": markers or [],
                "kwargs": kwargs or {},
            }
        )
        return self

    def set_config(
        self,
        timeout: int = 300,
        parallel: bool = False,
        n_workers: int = 4,
        random_seed: Optional[int] = None,
    ) -> "CustomTestScenario":
        """설정"""
        self.config = {
            "timeout": timeout,
            "parallel": parallel,
            "n_workers": n_workers,
            "random_seed": random_seed,
        }
        return self

    def run(self) -> SuiteResult:
        """시나리오 실행"""
        dashboard = DashboardRunner()

        test_paths = [t["file"] for t in self.tests]
        combined_path = " ".join(test_paths)

        return dashboard.run_tests(combined_path, timeout=self.config.get("timeout", 300))

    def save(self, filepath: str) -> None:
        """시나리오 JSON 저장"""
        data = {
            "name": self.name,
            "tests": self.tests,
            "config": self.config,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def load(filepath: str) -> "CustomTestScenario":
        """시나리오 JSON 로드"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        scenario = CustomTestScenario(data["name"])
        for test in data["tests"]:
            scenario.add_test(test["file"], test.get("markers"), test.get("kwargs"))
        scenario.set_config(**data.get("config", {}))

        return scenario


if __name__ == "__main__":
    print("=== SDACS 테스트 시스템 ===\n")

    # 1. 대시보드 실행
    print("1. 테스트 실행...")
    dashboard = DashboardRunner()
    result = dashboard.run_tests("tests/test_apf.py tests/test_cbs.py tests/test_voronoi.py", timeout=60)
    print(f"   결과: {result.passed}/{result.total} 통과\n")

    # 2. 스케줄러 설정
    print("2. 스케줄러 설정...")
    scheduler = SchedulerRunner()
    scheduler.schedule("nightly", "tests/", interval_minutes=60)
    print(f"   스케줄: {scheduler.get_status()}\n")

    # 3. 비교 분석
    print("3. 비교 분석...")
    comparator = ResultComparator()
    comparator.set_baseline(result)
    print("   베이스라인 설정됨\n")

    # 4. 커스텀 시나리오
    print("4. 커스텀 시나리오...")
    scenario = CustomTestScenario("알고리즘 검증")
    scenario.add_test("tests/test_apf.py").add_test("tests/test_cbs.py").set_config(timeout=60)
    scenario.save("config/custom_test_scenario.json")
    print("   시나리오 저장: config/custom_test_scenario.json\n")

    # 5. 대시보드 HTML 생성
    print("5. 대시보드 생성...")
    dashboard_path = dashboard.save_dashboard()
    print(f"   저장됨: {dashboard_path}\n")

    print("=== 완료 ===")
