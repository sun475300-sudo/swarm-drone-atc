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
    """단일 SwarmSimulator 실행 후 KPI·이벤트·비행단계 요약 출력 (simulate 서브커맨드)"""
    _setup_logging(getattr(args, "log_level", "INFO"))
    import time as _time

    from simulation.simulator import SwarmSimulator

    duration = args.duration
    seed = args.seed
    drones = getattr(args, "drones", 100)
    from simulation.apf_engine import get_apf_backend_info
    backend = get_apf_backend_info()
    gpu_tag = f"🟢 GPU: {backend['gpu']}" if backend.get("gpu") else "⚪ CPU"
    print(f"\n🛸 시뮬레이션 시작: seed={seed}, drones={drones}, duration={duration}s [{gpu_tag}]\n")

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

    # --output: KPI 요약을 JSON 으로 저장 (나이틀리 벤치마크 CI 아티팩트용)
    output_arg = getattr(args, "output", None)
    if output_arg:
        import json
        from pathlib import Path

        out_path = Path(output_arg)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = result.to_dict()
        payload["drones"] = drones
        payload["elapsed_s"] = round(elapsed, 3)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
        print(f"📄 KPI JSON 저장: {out_path}")


# ── scenario ─────────────────────────────────────────────────

def cmd_scenario(args: argparse.Namespace) -> None:
    """명명된 시나리오를 n회 실행하고 집계 KPI를 출력 (--list 시 시나리오 목록만 표시)"""
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
    """Monte Carlo 파라미터 스윕 (quick/full) 실행 후 설정별 집계 결과를 표로 출력"""
    _setup_logging(getattr(args, "log_level", "INFO"))
    from simulation.monte_carlo import run_monte_carlo, summarize_results

    mode = args.mode
    print(f"\n🎲 Monte Carlo [{mode}] 스윕 시작...\n")

    results = run_monte_carlo(mode=mode)

    print(f"\n총 {len(results)}회 실행 완료\n")
    print(summarize_results(results))
    print()


# ── visualize ────────────────────────────────────────────────

def _normalize_benchmark_method(method: str) -> str:
    """사용자 입력 메서드 이름을 내부 어댑터 키로 정규화 (예: 'hybrid' → 'sdacs_hybrid')"""
    return {
        "hybrid": "sdacs_hybrid",
    }.get(method, method)


def _load_benchmark_manifest(scenario_id: str) -> dict:
    """벤치마크 시나리오 매니페스트 YAML 로드 (benchmarks/scenarios/{id}/manifest.yaml)"""
    from pathlib import Path

    import yaml

    manifest_path = Path(__file__).parent / "benchmarks" / "scenarios" / scenario_id / "manifest.yaml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"benchmark manifest not found: {manifest_path}")
    with open(manifest_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def cmd_benchmark(args: argparse.Namespace) -> None:
    """재현 가능한 벤치마크 셀 실행: 시나리오·메서드·시드 고정 → 메트릭(NMR/PE/RTF 등) JSON 출력"""
    _setup_logging(getattr(args, "log_level", "INFO"))

    import json
    import time
    from pathlib import Path

    from benchmarks.baselines._base import make_adapter
    from src.analytics.metrics import Evaluator, EvaluatorConfig
    from src.analytics.types import AirspaceCapacity, SimulationTrace

    scenario = args.scenario
    method = _normalize_benchmark_method(getattr(args, "method", "sdacs_hybrid"))
    seed = int(getattr(args, "seed", 0))
    hard_wall_s = float(getattr(args, "hard_wall_s", 120.0))
    quiet = bool(getattr(args, "quiet", False))

    manifest = _load_benchmark_manifest(scenario)
    if not quiet:
        print(f"[benchmark] scenario={scenario} method={method} seed={seed}")

    adapter = make_adapter(method, manifest, seed)
    t0 = time.perf_counter()
    trace = adapter.run(hard_wall_time_s=hard_wall_s)
    wall_time_s = time.perf_counter() - t0

    trace_dict = trace.to_dict()
    if float(trace_dict.get("wall_clock_seconds", 0.0) or 0.0) <= 0:
        trace_dict["wall_clock_seconds"] = wall_time_s
        trace = SimulationTrace.from_dict(trace_dict)

    airspace_cfg = manifest.get("airspace", {}) if isinstance(manifest, dict) else {}
    capacity_max_agents = airspace_cfg.get("capacity_max_agents")
    capacity = (
        AirspaceCapacity(max_agents=int(capacity_max_agents))
        if capacity_max_agents is not None
        else None
    )
    metrics = Evaluator(EvaluatorConfig(capacity=capacity)).evaluate(trace)

    result = {
        "scenario_id": scenario,
        "method": method,
        "seed": seed,
        "wall_time_s": wall_time_s,
        "agent_count": len(trace.agents),
        "tick_count": len(trace.tick_latencies_ms),
        "near_miss_rate": metrics["NMR"],
        "min_separation_m": metrics["MSD"],
        "path_efficiency": metrics["PE"],
        "makespan_s": metrics["MS_s"],
        "flowtime_s": metrics["FT_drone_s"],
        "airspace_utilization": metrics["AU"],
        "rid_compliance_rate": metrics["RID_CR"],
        "rtf": metrics["RTF"],
        "metrics": metrics,
    }

    output_arg = getattr(args, "output", None)
    if output_arg:
        out_path = Path(output_arg)
    else:
        out_path = Path("results") / scenario / method / f"seed{seed}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, sort_keys=True)

    if not quiet:
        print(f"[benchmark] wrote {out_path}")
        print(
            f"[benchmark] nmr={result['near_miss_rate']:.6g} "
            f"pe={result['path_efficiency']:.4f} "
            f"rtf={result['rtf']:.4f}"
        )


def cmd_visualize(args: argparse.Namespace) -> None:
    """Dash 3D 실시간 대시보드 실행 (별도 스레드에서 시뮬레이션, Plotly 렌더링)"""
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
    """기본 브라우저로 Three.js 3D 시뮬레이터 HTML 파일 오픈 (visualization/swarm_3d_simulator.html)"""
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
    """보세전시장 민원상담 챗봇 웹 서버 실행 (rule 또는 llm 엔진 선택 가능)"""
    _setup_logging(getattr(args, "log_level", "INFO"))
    from chatbot.app import run_chatbot

    port = getattr(args, "port", 8051)
    engine_type = getattr(args, "engine", "rule")

    print(f"\n보세전시장 민원상담 챗봇 시작: http://127.0.0.1:{port}")
    print("  브라우저에서 접속하여 질문하세요.\n")
    run_chatbot(port=port, engine_type=engine_type)


# ── chatbot-sim ───────────────────────────────────────────────

def cmd_chatbot_sim(args: argparse.Namespace) -> None:
    """챗봇 CLI 시뮬레이터 실행 (브라우저 없이 터미널에서 대화형 테스트)"""
    _setup_logging(getattr(args, "log_level", "INFO"))
    from chatbot.simulator import run_simulator

    run_simulator()


def cmd_api(args: argparse.Namespace) -> None:
    """FastAPI 백엔드 서버 실행 (uvicorn, pip install .[api] 필요)"""
    _setup_logging(getattr(args, "log_level", "INFO"))
    try:
        from api.fastapi_server import run_dev_server
    except Exception as exc:
        raise RuntimeError(
            "API backend dependencies are not available. "
            "Install with `pip install .[api]` or install fastapi/uvicorn manually."
        ) from exc

    host = getattr(args, "host", "0.0.0.0")
    port = int(getattr(args, "port", 8000))
    log_level = str(getattr(args, "log_level", "info")).lower()
    print(f"\nSDACS API 시작: http://{host}:{port}\n")
    run_dev_server(host=host, port=port, log_level=log_level)


def cmd_ops_report(args: argparse.Namespace) -> None:
    """E2E 운영 리포트 번들 생성: 배송·컴플라이언스·교통·기상 데이터 통합 → JSON/Markdown 출력"""
    _setup_logging(getattr(args, "log_level", "INFO"))
    from simulation.compliance_engine import ComplianceEngine
    from simulation.delivery_simulation import DeliverySimulation
    from simulation.e2e_reporter import E2EReporter
    from simulation.perf_benchmark import PerfBenchmark
    from simulation.sim_recorder import SimRecorder
    from simulation.traffic_simulator import TrafficSimulator
    from simulation.weather_api_client import WeatherApiClient

    scenario = getattr(args, "scenario", "ops_report")
    seed = int(getattr(args, "seed", 42))
    city = getattr(args, "city", "Seoul")
    hour = int(getattr(args, "hour", 18))
    capacity = int(getattr(args, "capacity", 180))
    base_demand = int(getattr(args, "base_demand", 110))
    out_dir = getattr(args, "out_dir", "data/e2e_reports")
    window_sec = float(getattr(args, "window_sec", 60.0))
    stem = getattr(args, "stem", None)

    delivery = DeliverySimulation()
    delivery.register_drone("D1", position=(0, 0), max_payload_kg=3.0, speed_mps=12.0)
    delivery.register_drone("D2", position=(220, 50), max_payload_kg=4.5, speed_mps=11.0)
    delivery.add_order("ORD-001", destination=(90, 30), weight_kg=1.0, priority=8, created_min=0)
    delivery.add_order("ORD-002", destination=(180, 110), weight_kg=1.4, priority=6, created_min=2)

    weather_client = WeatherApiClient(ttl_seconds=300)
    weather = weather_client.fetch(city=city, now_ts=float(seed))
    weather_factor = weather_client.traffic_factor(weather)

    traffic = TrafficSimulator(base_demand=base_demand, seed=seed)
    traffic_state = traffic.step(hour=hour, weather_factor=weather_factor, capacity=capacity)

    recorder = SimRecorder()
    recorder.record(
        0.0,
        "SCENARIO_START",
        scenario=scenario,
        city=city,
        weather_condition=weather.condition,
    )

    benchmark = PerfBenchmark()
    benchmark.add_sample(9.5, success=True)

    dispatched = []
    dispatch_idx = 0
    while delivery.pending_orders() > 0:
        record = delivery.dispatch_with_traffic_state(traffic_state, weather_factor=weather_factor)
        if record is None:
            recorder.record(float((dispatch_idx + 1) * 10), "DISPATCH_BLOCKED", pending=delivery.pending_orders())
            benchmark.add_sample(30.0, success=False)
            break
        dispatch_idx += 1
        dispatched.append(record)
        event_t = float(dispatch_idx * 10)
        recorder.record(event_t, "DISPATCHED", order_id=record.order_id, drone_id=record.drone_id)
        benchmark.add_sample(12.0 + (dispatch_idx * 3.5), success=True)
        delivery.complete_delivery(record.order_id)
        recorder.record(event_t + 4.0, "DELIVERED", order_id=record.order_id, drone_id=record.drone_id)

    compliance = ComplianceEngine()
    compliance.evaluate_batch(
        [
            {
                "drone_id": record.drone_id,
                "altitude_m": 75.0,
                "speed_mps": 14.0,
                "battery_pct": 68.0,
            }
            for record in dispatched
        ]
    )

    recorder.record(float((dispatch_idx + 1) * 10), "SCENARIO_COMPLETE", delivered=delivery.summary()["delivered"])

    reporter = E2EReporter(
        green_threshold=float(getattr(args, "green_threshold", 0.85)),
        yellow_threshold=float(getattr(args, "yellow_threshold", 0.65)),
    )
    report = reporter.build_with_observability(
        delivery_summary=delivery.summary(),
        compliance_report=compliance.violation_report(),
        recorder=recorder,
        benchmark=benchmark,
        traffic_summary=traffic.summary(),
        window_sec=window_sec,
        meta={
            "scenario": scenario,
            "city": city,
            "seed": seed,
            "weather_condition": weather.condition,
            "weather_factor": round(weather_factor, 4),
        },
        scenario_summary={
            "scenario": scenario,
            "seed": seed,
            "duration_s": recorder.summary()["duration_sec"],
            "n_drones": delivery.summary()["drones"],
            "source": "ops_report_cli",
        },
    )
    artifacts = reporter.export_bundle(
        report,
        output_dir=out_dir,
        stem=stem or f"{scenario}-seed{seed}",
    )

    print(f"\n[ops-report] scenario={scenario} status={report['status']} health={report['kpi']['health_score']:.4f}")
    print(f"[ops-report] json={artifacts['json_path']}")
    print(f"[ops-report] markdown={artifacts['markdown_path']}\n")
    print(f"[ops-report] manifest={artifacts['manifest_path']}\n")


# ── main ─────────────────────────────────────────────────────

def main() -> None:
    """CLI 진입점: argparse 서브커맨드 파싱 후 해당 cmd_* 핸들러로 디스패치"""
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
    p_sim.add_argument("--output",   default=None, help="KPI 요약 JSON 저장 경로")
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

    p_bench = sub.add_parser("benchmark", help="Reproducible benchmark cell runner")
    p_bench.add_argument("--scenario", required=True, help="benchmark scenario id, e.g. 01_corridor_crossing")
    p_bench.add_argument("--method", default="sdacs_hybrid", help="orca | vo | cbs | sdacs_hybrid")
    p_bench.add_argument("--seed", type=int, default=0, help="deterministic seed")
    p_bench.add_argument("--output", default=None, help="output JSON path")
    p_bench.add_argument("--hard-wall-s", type=float, default=120.0, help="per-run wall time ceiling")
    p_bench.add_argument("--quiet", action="store_true", help="suppress progress prints")
    p_bench.add_argument("--log-level", default="INFO")

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

    # ── api ─────────────────────────────────────────────────────
    p_api = sub.add_parser("api", help="FastAPI 백엔드 실행")
    p_api.add_argument("--host", default="0.0.0.0", help="API 바인드 호스트")
    p_api.add_argument("--port", type=int, default=8000, help="API 포트")
    p_api.add_argument("--log-level", default="INFO")

    p_ops = sub.add_parser("ops-report", help="E2E 운영 리포트 번들 생성")
    p_ops.add_argument("--scenario", default="ops_report", help="리포트 시나리오 이름")
    p_ops.add_argument("--seed", type=int, default=42, help="샘플 데이터 생성 시드")
    p_ops.add_argument("--city", default="Seoul", help="기상 샘플 도시")
    p_ops.add_argument("--hour", type=int, default=18, help="교통 샘플 시간")
    p_ops.add_argument("--capacity", type=int, default=180, help="공역 처리 용량")
    p_ops.add_argument("--out-dir", default="data/e2e_reports", help="리포트 저장 경로")
    p_ops.add_argument("--log-level", default="INFO")

    p_ops.add_argument("--base-demand", type=int, default=110, help="base traffic demand")
    p_ops.add_argument("--window-sec", type=float, default=60.0, help="performance report window")
    p_ops.add_argument("--green-threshold", type=float, default=0.85, help="GREEN status threshold")
    p_ops.add_argument("--yellow-threshold", type=float, default=0.65, help="YELLOW status threshold")
    p_ops.add_argument("--stem", default=None, help="artifact filename stem")

    args = parser.parse_args()

    dispatch = {
        "simulate":      cmd_simulate,
        "scenario":      cmd_scenario,
        "monte-carlo":   cmd_monte_carlo,
        "benchmark":     cmd_benchmark,
        "visualize":     cmd_visualize,
        "visualize-3d":  cmd_visualize_3d,
        "chatbot":       cmd_chatbot,
        "chatbot-sim":   cmd_chatbot_sim,
        "api":           cmd_api,
        "ops-report":    cmd_ops_report,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
