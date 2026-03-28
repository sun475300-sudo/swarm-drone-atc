"""
시뮬레이션 결과 영속 저장 및 비교 도구

JSON 또는 CSV로 SimulationResult를 저장/로드하고
다수 결과를 비교하는 유틸리티.

사용법:
    from simulation.result_store import ResultStore
    store = ResultStore("data/results")
    store.save(result, tag="high_density_v2")
    df = store.load_all()
    print(store.compare(["high_density_v1", "high_density_v2"]))
"""
from __future__ import annotations

import json
import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from simulation.analytics import SimulationResult


class ResultStore:
    """시뮬레이션 결과 파일 저장소"""

    def __init__(self, base_dir: str = "data/results") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        result: SimulationResult,
        tag: str = "",
        fmt: str = "json",
    ) -> Path:
        """
        SimulationResult를 파일로 저장.

        Parameters
        ----------
        result : SimulationResult
        tag : 식별 태그 (비어있으면 타임스탬프 사용)
        fmt : "json" 또는 "csv"

        Returns
        -------
        Path : 저장된 파일 경로
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"{tag}_{ts}" if tag else ts
        data = result.to_dict()
        data["_saved_at"] = ts
        data["_tag"] = tag

        if fmt == "json":
            path = self.base_dir / f"{name}.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        elif fmt == "csv":
            path = self.base_dir / f"{name}.csv"
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(data.keys())
                writer.writerow(data.values())
        else:
            raise ValueError(f"지원하지 않는 형식: {fmt}")

        return path

    def load_json(self, path: str | Path) -> dict:
        """JSON 결과 파일 로드"""
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def load_all(self) -> list[dict]:
        """base_dir 내 모든 JSON 결과 로드"""
        results = []
        for p in sorted(self.base_dir.glob("*.json")):
            try:
                results.append(self.load_json(p))
            except (json.JSONDecodeError, OSError):
                continue
        return results

    def find_by_tag(self, tag: str) -> list[dict]:
        """태그로 결과 필터"""
        return [r for r in self.load_all() if r.get("_tag", "").startswith(tag)]

    def compare(
        self,
        tags: list[str],
        metrics: Optional[list[str]] = None,
    ) -> str:
        """
        태그별 결과를 비교 테이블로 출력.

        Parameters
        ----------
        tags : 비교할 태그 목록
        metrics : 비교할 메트릭 이름 (None이면 주요 메트릭 자동 선택)
        """
        if metrics is None:
            metrics = [
                "collision_count", "near_miss_count",
                "conflict_resolution_rate_pct",
                "route_efficiency_mean", "total_distance_km",
                "energy_efficiency_wh_per_km",
                "advisory_latency_p50", "advisory_latency_p99",
                "cbs_attempts", "cbs_successes",
                "comm_messages_sent", "comm_drop_rate",
            ]

        # 태그별 최신 결과 수집
        results_by_tag: dict[str, dict] = {}
        for tag in tags:
            found = self.find_by_tag(tag)
            if found:
                results_by_tag[tag] = found[-1]  # 최신

        if not results_by_tag:
            return "비교할 결과가 없습니다."

        # 테이블 생성
        col_width = 18
        header = f"{'메트릭':<30}" + "".join(f"{t:>{col_width}}" for t in tags)
        sep = "-" * (30 + col_width * len(tags))

        lines = [sep, header, sep]
        for m in metrics:
            row = f"{m:<30}"
            for tag in tags:
                val = results_by_tag.get(tag, {}).get(m, "N/A")
                if isinstance(val, float):
                    row += f"{val:>{col_width}.4f}"
                else:
                    row += f"{str(val):>{col_width}}"
            lines.append(row)
        lines.append(sep)

        return "\n".join(lines)

    def compare_chart(
        self,
        tags: list[str],
        metrics: list[str] | None = None,
        output_path: str | Path | None = None,
    ) -> Path | None:
        """
        태그별 결과를 matplotlib 바 차트로 시각화.

        Parameters
        ----------
        tags : 비교할 태그 목록
        metrics : 비교할 메트릭 (None이면 주요 4개 자동)
        output_path : 저장 경로 (None이면 base_dir/comparison.png)
        """
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            return None

        if metrics is None:
            metrics = [
                "collision_count",
                "conflict_resolution_rate_pct",
                "route_efficiency_mean",
                "energy_efficiency_wh_per_km",
            ]

        results_by_tag: dict[str, dict] = {}
        for tag in tags:
            found = self.find_by_tag(tag)
            if found:
                results_by_tag[tag] = found[-1]

        if not results_by_tag:
            return None

        n_metrics = len(metrics)
        fig, axes = plt.subplots(1, n_metrics, figsize=(4 * n_metrics, 4))
        if n_metrics == 1:
            axes = [axes]

        tag_list = list(results_by_tag.keys())
        colors = ["#58a6ff", "#f78166", "#3fb950", "#d2a8ff", "#ff7b72"]

        for i, metric in enumerate(metrics):
            vals = [results_by_tag[t].get(metric, 0) for t in tag_list]
            bars = axes[i].bar(
                tag_list, vals,
                color=[colors[j % len(colors)] for j in range(len(tag_list))],
            )
            axes[i].set_title(metric.replace("_", " ").title(), fontsize=9)
            axes[i].tick_params(axis="x", rotation=30, labelsize=7)
            axes[i].tick_params(axis="y", labelsize=8)
            for bar, v in zip(bars, vals):
                axes[i].text(
                    bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    f"{v:.2f}" if isinstance(v, float) else str(v),
                    ha="center", va="bottom", fontsize=7,
                )

        fig.suptitle("Simulation Result Comparison", fontsize=12, y=1.02)
        plt.tight_layout()

        out = Path(output_path) if output_path else self.base_dir / "comparison.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return out

    def sensitivity_analysis(
        self,
        param_name: str,
        metric_name: str = "collision_count",
    ) -> tuple[list, list]:
        """
        단일 파라미터 민감도 분석.

        저장된 결과에서 param_name 값의 변화에 따른 metric_name 변화 추출.

        Returns
        -------
        (param_values, metric_values) : 정렬된 리스트 쌍
        """
        all_results = self.load_all()
        pairs = []
        for r in all_results:
            p_val = r.get(param_name)
            m_val = r.get(metric_name)
            if p_val is not None and m_val is not None:
                pairs.append((p_val, m_val))

        if not pairs:
            return [], []

        pairs.sort(key=lambda x: x[0])
        return [p[0] for p in pairs], [p[1] for p in pairs]

    def export_html_report(
        self,
        tags: list[str],
        output_path: str | Path | None = None,
    ) -> Path:
        """
        비교 결과를 HTML 리포트로 내보내기.

        Parameters
        ----------
        tags : 비교할 태그 목록
        output_path : 저장 경로 (None이면 base_dir/report.html)
        """
        metrics = [
            "collision_count", "near_miss_count",
            "conflict_resolution_rate_pct",
            "route_efficiency_mean", "total_distance_km",
            "energy_efficiency_wh_per_km",
            "advisory_latency_p50", "advisory_latency_p99",
            "cbs_attempts", "cbs_successes",
            "comm_messages_sent", "comm_drop_rate",
        ]

        results_by_tag: dict[str, dict] = {}
        for tag in tags:
            found = self.find_by_tag(tag)
            if found:
                results_by_tag[tag] = found[-1]

        # HTML 테이블 생성
        header_cells = "".join(f"<th>{t}</th>" for t in tags)
        rows = ""
        for m in metrics:
            cells = ""
            for tag in tags:
                val = results_by_tag.get(tag, {}).get(m, "N/A")
                if isinstance(val, float):
                    cells += f"<td>{val:.4f}</td>"
                else:
                    cells += f"<td>{val}</td>"
            rows += f"<tr><td><b>{m}</b></td>{cells}</tr>\n"

        html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>SDACS Simulation Comparison Report</title>
<style>
body {{ font-family: 'Segoe UI', sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; }}
h1 {{ color: #58a6ff; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
th, td {{ border: 1px solid #30363d; padding: 8px 12px; text-align: right; }}
th {{ background: #161b22; color: #58a6ff; }}
td:first-child {{ text-align: left; }}
tr:hover {{ background: #161b22; }}
.footer {{ margin-top: 24px; color: #6e7681; font-size: 12px; }}
</style>
</head><body>
<h1>SDACS Simulation Comparison Report</h1>
<p>Tags: {', '.join(tags)}</p>
<table>
<tr><th>Metric</th>{header_cells}</tr>
{rows}
</table>
<div class="footer">Generated by SDACS ResultStore</div>
</body></html>"""

        out = Path(output_path) if output_path else self.base_dir / "report.html"
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        return out
