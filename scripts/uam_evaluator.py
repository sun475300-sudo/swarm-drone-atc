"""P742: K-UAM Grand Challenge 자동 평가기.

results CSV를 읽어 K-UAM 통과 기준 5개를 자동 판정.

실행:
    python scripts/uam_evaluator.py results/uam_kpi.csv
"""
from __future__ import annotations

import csv
import sys
from contextlib import suppress
from dataclasses import dataclass


@dataclass(frozen=True)
class KUAMCriteria:
    """K-UAM Grand Challenge 2단계 통과 기준."""

    nmr_max: float = 0.05               # Near Miss Rate ≤ 5%
    msd_min_m: float = 50.0             # Mean Separation ≥ 50m
    au_min: float = 0.60               # Airspace Utilization ≥ 60%
    rtf_min: float = 1.0               # Real-Time Factor ≥ 1.0
    completion_min: float = 0.95       # Scenario Completion ≥ 95%


@dataclass
class EvalResult:
    """단일 메트릭 평가 결과."""

    metric: str
    value: float
    target: float
    direction: str   # 'max' (≤target pass) | 'min' (≥target pass)
    passed: bool


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def load_kpi_csv(path: str) -> dict[str, list[float]]:
    """KPI CSV → metric → [seed values]."""
    data: dict[str, list[float]] = {}
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for key, val in row.items():
                if key in ("seed", "scenario"):
                    continue
                with suppress(ValueError, TypeError):
                    data.setdefault(key, []).append(float(val))
    return data


def evaluate(kpi: dict[str, list[float]], criteria: KUAMCriteria | None = None) -> list[EvalResult]:
    """KPI 평균 vs 기준 비교."""
    c = criteria or KUAMCriteria()
    results = []

    checks = [
        ("NMR", _mean(kpi.get("NMR", [])), c.nmr_max, "max"),
        ("MSD", _mean(kpi.get("MSD", [])), c.msd_min_m, "min"),
        ("AU", _mean(kpi.get("AU", [])), c.au_min, "min"),
        ("RTF", _mean(kpi.get("RTF", [])), c.rtf_min, "min"),
        ("Completion", _mean(kpi.get("Completion", [])), c.completion_min, "min"),
    ]

    for metric, value, target, direction in checks:
        passed = value <= target if direction == "max" else value >= target
        results.append(EvalResult(metric, value, target, direction, passed))

    return results


def format_report(results: list[EvalResult]) -> str:
    """평가 결과 → 사람이 읽는 보고서."""
    lines = []
    all_pass = all(r.passed for r in results)
    for r in results:
        icon = "✅" if r.passed else "❌"
        op = "≤" if r.direction == "max" else "≥"
        lines.append(f"  {icon} {r.metric}: {r.value:.3f} (target {op}{r.target})")
    status = "PASS K-UAM Grand Challenge 2단계" if all_pass else "FAIL — 미달 항목 존재"
    lines.append(f"\n  STATUS: {status}")
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python scripts/uam_evaluator.py <kpi.csv>")
        return 2
    kpi = load_kpi_csv(sys.argv[1])
    results = evaluate(kpi)
    print(format_report(results))
    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
