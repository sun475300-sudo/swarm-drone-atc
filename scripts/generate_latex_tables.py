"""
논문용 LaTeX 실험 결과 테이블 자동 생성

실행: python scripts/generate_latex_tables.py
출력: docs/latex_tables.tex
"""
from __future__ import annotations

import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def generate_scenario_table() -> str:
    """7개 시나리오 실행 결과 LaTeX 테이블."""
    from simulation.scenario_runner import run_scenario

    scenarios = [
        "high_density", "weather_disturbance", "comms_loss",
        "emergency_failure", "adversarial_intrusion", "mass_takeoff",
        "route_conflict",
    ]

    rows = []
    for name in scenarios:
        results = run_scenario(name, n_runs=1, seed=42)
        r = results[0]
        rows.append({
            "name": name,
            "drones": r.get("n_drones", 100),
            "collisions": r.get("collision_count", 0),
            "near_miss": r.get("near_miss_count", 0),
            "resolve": r.get("conflict_resolution_rate", 0),
            "efficiency": r.get("route_efficiency", 0),
        })

    tex = r"""\begin{table}[htbp]
\centering
\caption{SDACS 시나리오별 시뮬레이션 결과}
\label{tab:scenario_results}
\begin{tabular}{lrrrrr}
\hline
\textbf{시나리오} & \textbf{드론} & \textbf{충돌} & \textbf{근접경고} & \textbf{해결률(\%)} & \textbf{경로효율} \\
\hline
"""
    for r in rows:
        tex += f"{r['name']} & {r['drones']} & {r['collisions']} & {r['near_miss']} & {r['resolve']:.1f} & {r['efficiency']:.3f} \\\\\n"

    tex += r"""\hline
\end{tabular}
\end{table}
"""
    return tex


def generate_gpu_table() -> str:
    """GPU 벤치마크 LaTeX 테이블."""
    tex = r"""\begin{table}[htbp]
\centering
\caption{APF GPU 가속 벤치마크 (RTX 5070 Ti)}
\label{tab:gpu_benchmark}
\begin{tabular}{rrrr}
\hline
\textbf{드론 수} & \textbf{CPU (ms)} & \textbf{GPU (ms)} & \textbf{가속비} \\
\hline
50 & 11.2 & 13.0 & 0.86$\times$ \\
100 & 42.7 & 18.1 & 2.37$\times$ \\
200 & 188.7 & 28.1 & 6.71$\times$ \\
500 & 1192.5 & 97.6 & 12.22$\times$ \\
1000 & N/A & 194.0 & -- \\
\hline
\end{tabular}
\end{table}
"""
    return tex


def main():
    print("시나리오 결과 생성 중...")
    scenario_tex = generate_scenario_table()
    gpu_tex = generate_gpu_table()

    output = f"""% SDACS 실험 결과 LaTeX 테이블
% 자동 생성: python scripts/generate_latex_tables.py

{scenario_tex}

{gpu_tex}
"""
    outpath = os.path.join(_ROOT, "docs", "latex_tables.tex")
    with open(outpath, "w", encoding="utf-8") as f:
        f.write(output)
    print(f"저장 완료: {outpath}")


if __name__ == "__main__":
    main()
