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
