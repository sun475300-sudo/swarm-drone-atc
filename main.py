"""
SDACS — 군집드론 공역통제 자동화 시스템
메인 진입점

사용법:
    python main.py simulate              # 기본 시뮬레이션 1회 실행
    python main.py scenario --list       # 시나리오 목록
    python main.py scenario weather_disturbance --runs 3
    python main.py monte-carlo --mode quick
    python main.py visualize             # 3D 대시보드 실행
    python main.py visualize-3d          # Three.js 3D 시뮬레이터
    python main.py chatbot               # 보세전시장 민원상담 챗봇
    python main.py chatbot-sim           # 챗봇 CLI 시뮬레이터
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

# Windows CP949 인코딩 문제 방지
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s │ %(name)-20s │ %(levelname)-5s │ %(message)s",
        datefmt="%H:%M:%S",
    )


# ── simulate ─────────────────────────────────────────────────

def cmd_simulate(args: argparse.Namespace) -> None:
    _setup_logging(getattr(args, "log_level", "INFO"))
    import time as _time
    from simulation.simulator import SwarmSimulator

    duration = args.duration
    seed = args.seed
    drones = getattr(args, "drones", 100)
    print(f"\n🛸 시뮬레이션 시작: seed={seed}, drones={drones}, duration={duration}s\n")

    t0 = _time.monotonic()
    override = {"drones": {"default_count": drones}}
    sim = SwarmSimulator(seed=seed, scenario_cfg=override)
    result = sim.run(duration_s=duration)
    elapsed = _time.monotonic() - t0

    # KPI 요약 테이블
    print(result.summary_table())

    # 이벤트 타임라인 요약
    events = sim.analytics.events
    event_counts: dict[str, int] = {}
    for ev in events:
        event_counts[ev["type"]] = event_counts.get(ev["type"], 0) + 1

    if event_counts:
        print("\n┌──────────────────────────────┬──────────────────┐")
        print("│ 이벤트 유형                  │ 발생 횟수        │")
        print("├──────────────────────────────┼──────────────────┤")
        for etype, cnt in sorted(event_counts.items(), key=lambda x: -x[1]):
            print(f"│ {etype:<28} │ {cnt:>16} │")
        print("└──────────────────────────────┴──────────────────┘")

    # 비행 단계별 최종 분포
    phase_counts: dict[str, int] = {}
    for d in sim._drones.values():
        name = d.flight_phase.name
        phase_counts[name] = phase_counts.get(name, 0) + 1

    print("\n┌──────────────────────────────┬──────────────────┐")
    print("│ 비행 단계                    │ 드론 수          │")
    print("├──────────────────────────────┼──────────────────┤")
    for phase, cnt in sorted(phase_counts.items(), key=lambda x: -x[1]):
        bar = "█" * min(cnt, 30)
        print(f"│ {phase:<28} │ {cnt:>5}  {bar:<10}│")
    print("└──────────────────────────────┴──────────────────┘")

    # 통신 버스 통계
    cs = sim.comm_bus.stats
    print(f"\n📡 통신: sent={cs['sent']}  delivered={cs['delivered']}  dropped={cs['dropped']}")

    print(f"\n✅ 시뮬레이션 완료 ({duration:.0f}s, {drones}기, 실행시간 {elapsed:.1f}s)\n")


# ── scenario ─────────────────────────────────────────────────

def cmd_scenario(args: argparse.Namespace) -> None:
    _setup_logging(getattr(args, "log_level", "INFO"))
    from simulation.scenario_runner import list_scenarios, run_scenario

    if args.list or not args.name:
        scenarios = list_scenarios()
        print()
        print("  ┌──────────────────────────┬────────────────────────────────────────────────┐")
        print("  │ 시나리오                  │ 설명                                           │")
        print("  ├──────────────────────────┼────────────────────────────────────────────────┤")
        for s in scenarios:
            if isinstance(s, dict):
                n = s.get("name", str(s))
                d = s.get("description", "")[:44]
            else:
                n = str(s)
                d = ""
            print(f"  │ {n:<24} │ {d:<46} │")
        print("  └──────────────────────────┴────────────────────────────────────────────────┘")
        print()
        return

    name = args.name
    runs = args.runs
    seed = args.seed
    print(f"\n시나리오 [{name}] - {runs}회 실행 (seed={seed})\n")

    results = run_scenario(name, n_runs=runs, seed=seed)

    for i, row in enumerate(results):
        print(f"-- Run #{i+1} --")
        for k, v in row.items():
            if k not in ("run_idx", "config_params"):
                print(f"  {k}: {v}")
        print()

    if runs > 1:
        import numpy as np
        numeric_keys = [k for k, v in results[0].items()
                        if isinstance(v, (int, float)) and k != "run_idx"]
        print("==== 집계 결과 ====")
        for k in numeric_keys:
            vals = [r[k] for r in results if k in r]
            print(f"  {k}: mean={np.mean(vals):.3f}  std={np.std(vals):.3f}")
        print()


# ── monte-carlo ──────────────────────────────────────────────

def cmd_monte_carlo(args: argparse.Namespace) -> None:
    _setup_logging(getattr(args, "log_level", "INFO"))
    from simulation.monte_carlo import run_monte_carlo, summarize_results

    mode = args.mode
    print(f"\n🎲 Monte Carlo [{mode}] 스윕 시작...\n")

    results = run_monte_carlo(mode=mode)

    print(f"\n총 {len(results)}회 실행 완료\n")
    print(summarize_results(results))
    print()


# ── visualize ────────────────────────────────────────────────

def cmd_visualize(args: argparse.Namespace) -> None:
    _setup_logging(getattr(args, "log_level", "INFO"))
    import threading
    from visualization.simulator_3d import SIM, _sim_loop, app

    port = getattr(args, "port", 8050)
    drones = getattr(args, "drones", 30)

    SIM.reset(drones)
    bg = threading.Thread(target=_sim_loop, args=(SIM,), daemon=True)
    bg.start()

    print(f"\n🛸 3D 실시간 대시보드 시작: http://127.0.0.1:{port}")
    print("  ▶ 시작 버튼을 눌러 시뮬레이션을 실행하세요.\n")
    app.run(debug=False, host="0.0.0.0", port=port)


# ── visualize-3d ────────────────────────────────────────────

def cmd_visualize_3d(args: argparse.Namespace) -> None:
    import webbrowser
    from pathlib import Path

    html_path = Path(__file__).parent / "visualization" / "swarm_3d_simulator.html"
    if not html_path.exists():
        print("❌ swarm_3d_simulator.html 파일을 찾을 수 없습니다.")
        return

    url = html_path.as_uri()
    print(f"\n🌐 Three.js 3D 시뮬레이터 열기: {url}\n")
    webbrowser.open(url)


# ── chatbot ────────────────────────────────────────────────

def cmd_chatbot(args: argparse.Namespace) -> None:
    _setup_logging(getattr(args, "log_level", "INFO"))
    from chatbot.app import run_chatbot

    port = getattr(args, "port", 8051)
    engine_type = getattr(args, "engine", "rule")

    print(f"\n보세전시장 민원상담 챗봇 시작: http://127.0.0.1:{port}")
    print("  브라우저에서 접속하여 질문하세요.\n")
    run_chatbot(port=port, engine_type=engine_type)


# ── chatbot-sim ───────────────────────────────────────────────

def cmd_chatbot_sim(args: argparse.Namespace) -> None:
    _setup_logging(getattr(args, "log_level", "INFO"))
    from chatbot.simulator import run_simulator

    run_simulator()


# ── main ─────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="sdacs",
        description="군집드론 공역통제 자동화 시스템 (SDACS)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── simulate ────────────────────────────────────────────────
    p_sim = sub.add_parser("simulate", help="단일 시뮬레이션 실행")
    p_sim.add_argument("--duration", type=float, default=600.0, help="시뮬레이션 시간 (초)")
    p_sim.add_argument("--seed",     type=int,   default=42, help="랜덤 시드")
    p_sim.add_argument("--drones",   type=int,   default=100, help="드론 수")
    p_sim.add_argument("--log-level", default="INFO")

    # ── scenario ────────────────────────────────────────────────
    p_sc = sub.add_parser("scenario", help="명명된 시나리오 실행")
    p_sc.add_argument("name", nargs="?", help="시나리오 이름")
    p_sc.add_argument("--list",  "-l", action="store_true")
    p_sc.add_argument("--runs",  "-n", type=int, default=1, help="반복 횟수")
    p_sc.add_argument("--seed",        type=int, default=42, help="기본 시드")
    p_sc.add_argument("--log-level", default="INFO")

    # ── monte-carlo ─────────────────────────────────────────────
    p_mc = sub.add_parser("monte-carlo", help="Monte Carlo 파라미터 스윕")
    p_mc.add_argument("--mode",      default="quick", choices=["quick", "full"])
    p_mc.add_argument("--log-level", default="INFO")

    # ── visualize ───────────────────────────────────────────────
    p_vis = sub.add_parser("visualize", help="3D 대시보드 실행 (Dash/Plotly)")
    p_vis.add_argument("--port",     type=int,   default=8050, help="대시보드 포트")
    p_vis.add_argument("--drones",   type=int,   default=30, help="데모 드론 수")
    p_vis.add_argument("--log-level", default="INFO")

    # ── visualize-3d ─────────────────────────────────────────────
    p_v3d = sub.add_parser("visualize-3d", help="Three.js 3D 시뮬레이터 (브라우저)")

    # ── chatbot ────────────────────────────────────────────────
    p_chat = sub.add_parser("chatbot", help="보세전시장 민원상담 챗봇")
    p_chat.add_argument("--port", type=int, default=8051, help="챗봇 포트")
    p_chat.add_argument(
        "--engine", default="rule", choices=["rule", "llm"],
        help="응답 엔진 (rule: 규칙기반, llm: vLLM)",
    )
    p_chat.add_argument("--log-level", default="INFO")

    # ── chatbot-sim ─────────────────────────────────────────────
    p_chatsim = sub.add_parser("chatbot-sim", help="보세전시장 챗봇 CLI 시뮬레이터 (터미널)")
    p_chatsim.add_argument("--log-level", default="INFO")

    args = parser.parse_args()

    dispatch = {
        "simulate":      cmd_simulate,
        "scenario":      cmd_scenario,
        "monte-carlo":   cmd_monte_carlo,
        "visualize":     cmd_visualize,
        "visualize-3d":  cmd_visualize_3d,
        "chatbot":       cmd_chatbot,
        "chatbot-sim":   cmd_chatbot_sim,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
