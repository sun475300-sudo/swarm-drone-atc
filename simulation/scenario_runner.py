"""
시나리오 실행기
==============
config/scenario_params/*.yaml 의 명명된 시나리오를 SwarmSimulator에 연결해
단일 실행 또는 반복 실행(n_runs)을 수행하고 결과를 출력한다.

CLI:
    python simulation/scenario_runner.py --scenario weather_disturbance
    python simulation/scenario_runner.py --scenario adversarial_intrusion --runs 5
    python simulation/scenario_runner.py --list
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

# Windows cp949 터미널 한글 깨짐 방지
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf-8-sig"):
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from typing import Any

import numpy as np
import yaml

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

logger = logging.getLogger(__name__)

# 시나리오 파일 디렉터리
_SCENARIO_DIR = Path(_ROOT) / "config" / "scenario_params"
_SIM_CONFIG   = str(Path(_ROOT) / "config" / "default_simulation.yaml")


# ── 시나리오 YAML → simulator 오버라이드 변환 ─────────────────────────────

def _translate_scenario(raw: dict[str, Any]) -> dict[str, Any]:
    """
    scenario_params YAML 형식 → SwarmSimulator scenario_cfg 형식으로 변환.
    """
    cfg: dict[str, Any] = {}

    # 드론 수
    count = (raw.get("drone_count")
             or raw.get("base_drone_count")
             or raw.get("base_traffic", {}).get("drone_count"))
    if count is not None:
        cfg.setdefault("drones", {})["default_count"] = int(count)

    # 시뮬레이션 시간
    dur_s = raw.get("simulation_duration_s")
    dur_m = raw.get("simulation_duration_min")
    if dur_s is None and dur_m is not None:
        dur_s = float(dur_m) * 60.0
    if dur_s is not None:
        cfg["_duration_s"] = float(dur_s)

    # 기상 모델
    weather = raw.get("weather")
    if weather:
        cfg["weather"] = weather

    # 침입 드론
    intrusion = raw.get("intrusion")
    if intrusion:
        count_i = int(intrusion.get("count", 1))
        cfg.setdefault("scenario", {}).setdefault("drones", {})["n_rogue"] = count_i

    # 통신 두절
    comms = raw.get("comms_loss", {})
    if comms:
        cfg.setdefault("failure_injection", {})["comms_loss_rate"] = 0.05

    # 드론 장애
    fi = raw.get("failure_injection", {})
    if fi:
        cfg.setdefault("failure_injection", {}).update({
            "drone_failure_rate": float(fi.get("failure_rate_pct", 0.0)) / 100.0,
        })

    # lost-link 프로토콜 파라미터
    llp = raw.get("lost_link_protocol", {})
    if llp:
        cfg["lost_link_protocol"] = llp

    # 분리 기준 오버라이드 (강풍 시나리오 등)
    sep = raw.get("separation_standards", {})
    if sep:
        cfg["separation_standards"] = sep

    return cfg


# ── 시나리오 목록 ─────────────────────────────────────────────────────────

def list_scenarios() -> list[str]:
    return sorted(p.stem for p in _SCENARIO_DIR.glob("*.yaml"))


# ── 단일 시나리오 실행 ────────────────────────────────────────────────────

def run_scenario(
    scenario_name: str,
    n_runs: int = 1,
    seed: int = 42,
    verbose: bool = True,
    duration_override_s: float | None = None,
) -> list[dict[str, Any]]:
    """
    명명된 시나리오를 n_runs 회 실행하고 결과 dict 리스트를 반환한다.
    """
    from simulation.simulator import SwarmSimulator

    yaml_path = _SCENARIO_DIR / f"{scenario_name}.yaml"
    if not yaml_path.exists():
        available = list_scenarios()
        raise FileNotFoundError(
            f"시나리오 파일 없음: {yaml_path}\n"
            f"사용 가능: {available}"
        )

    with open(yaml_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    scenario_cfg = _translate_scenario(raw)
    duration_s   = float(duration_override_s
                         if duration_override_s is not None
                         else scenario_cfg.pop("_duration_s", 600.0))

    if verbose:
        print(f"\n{'='*60}")
        print(f"시나리오: {raw.get('scenario', scenario_name)}")
        print(f"  설명:   {raw.get('description', '')}")
        print(f"  실행:   {n_runs}회  |  시간: {duration_s}s  |  기본시드: {seed}")
        print(f"{'='*60}")

    results = []
    rng = np.random.default_rng(seed)

    for i in range(n_runs):
        run_seed = int(rng.integers(0, 2**31))
        t0 = time.monotonic()

        try:
            sim = SwarmSimulator(
                config_path=_SIM_CONFIG,
                scenario_cfg=scenario_cfg,
                seed=run_seed,
            )
            result = sim.run(duration_s=duration_s)
            row = result.to_dict()
            row["run_idx"]  = i
            row["scenario"] = scenario_name
            elapsed = time.monotonic() - t0

            if verbose:
                _print_run(i + 1, n_runs, row, elapsed)

        except Exception as exc:
            logger.error("run %d failed: %s", i, exc)
            row = {"run_idx": i, "scenario": scenario_name,
                   "collision_count": -1, "error": str(exc)}
            if verbose:
                print(f"  run {i+1}/{n_runs}  오류: {exc}")

        results.append(row)

    if verbose and n_runs > 1:
        _print_aggregate(results)

    return results


# ── 출력 헬퍼 ────────────────────────────────────────────────────────────

def _print_run(idx: int, total: int, row: dict, elapsed: float) -> None:
    col = row.get("collision_count", "?")
    nm  = row.get("near_miss_count", "?")
    eff = row.get("route_efficiency_mean", 0.0)
    res = row.get("conflict_resolution_rate_pct", 0.0)
    print(f"  run {idx:>3}/{total}  "
          f"collision={col}  near_miss={nm}  "
          f"eff={eff:.3f}  resolve={res:.1f}%  "
          f"[{elapsed:.1f}s]")


def _print_aggregate(results: list[dict]) -> None:
    import statistics

    valid = [r for r in results if r.get("collision_count", -1) >= 0]
    if not valid:
        print("\n  유효한 결과 없음")
        return

    def _stat(key: str) -> str:
        vals = [r[key] for r in valid if key in r]
        if not vals:
            return "N/A"
        return f"mean={statistics.mean(vals):.3f}  max={max(vals):.3f}"

    print(f"\n{'─'*60}")
    print(f"집계 ({len(valid)}/{len(results)} 성공)")
    print(f"  충돌:       {_stat('collision_count')}")
    print(f"  경로효율:   {_stat('route_efficiency_mean')}")
    print(f"  해결률(%):  {_stat('conflict_resolution_rate_pct')}")
    print(f"{'─'*60}\n")


# ── CLI ──────────────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(level=logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="SDACS 시나리오 실행기")
    parser.add_argument("--scenario", "-s",
                        help="실행할 시나리오 이름 (파일명 확장자 제외)")
    parser.add_argument("--list",  "-l", action="store_true",
                        help="사용 가능한 시나리오 목록 출력")
    parser.add_argument("--runs",  "-n", type=int, default=1,
                        help="반복 실행 횟수 (기본: 1)")
    parser.add_argument("--seed",       type=int, default=42)
    parser.add_argument("--output",     default=None,
                        help="결과 JSON 저장 경로 (선택)")
    parser.add_argument("--quiet", "-q", action="store_true")
    args = parser.parse_args()

    if args.list or not args.scenario:
        print("사용 가능한 시나리오:")
        for name in list_scenarios():
            yaml_path = _SCENARIO_DIR / f"{name}.yaml"
            with open(yaml_path, encoding="utf-8") as f:
                raw = yaml.safe_load(f)
            desc = raw.get("description", "").replace("\u2014", "-")
            print(f"  {name:<35} {desc}")
        return

    results = run_scenario(
        scenario_name=args.scenario,
        n_runs=args.runs,
        seed=args.seed,
        verbose=not args.quiet,
    )

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        print(f"결과 저장: {out}")


if __name__ == "__main__":
    main()
