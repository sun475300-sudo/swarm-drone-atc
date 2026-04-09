"""
파이프라인 오케스트레이터
=======================
수집 → 가공 → 저장 전체 흐름을 관리한다.

사용법:
    # Python에서 직접 호출
    from automation.pipeline import run_pipeline
    result = run_pipeline()

    # CLI 실행
    python -m automation.pipeline
    python -m automation.pipeline --mode quick --skip-sim
    python -m automation.pipeline --external-only
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

logger = logging.getLogger("automation.pipeline")

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "pipeline_config.yaml"
_LOG_DIR = Path(__file__).resolve().parent.parent / "data" / "pipeline" / "logs"


def _load_config(config_path: Optional[str] = None) -> dict:
    """파이프라인 설정을 로드."""
    path = Path(config_path) if config_path else _CONFIG_PATH
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    logger.warning("설정 파일 없음: %s — 기본값 사용", path)
    return {}


def _setup_logging(config: dict):
    """로깅 설정."""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    log_level = config.get("logging", {}).get("level", "INFO")
    log_file = _LOG_DIR / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    # 파일 핸들러
    file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
    file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s │ %(name)-28s │ %(levelname)-5s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s │ %(levelname)-5s │ %(message)s",
        datefmt="%H:%M:%S",
    ))

    root_logger = logging.getLogger("automation")
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return str(log_file)


# ── 메인 파이프라인 ───────────────────────────────────────────

def run_pipeline(
    config_path: Optional[str] = None,
    mc_mode: str = "quick",
    skip_sim: bool = False,
    skip_external: bool = False,
    skip_scenarios: bool = False,
    external_only: bool = False,
    scenario_runs: int = 3,
) -> dict[str, Any]:
    """
    전체 파이프라인을 실행.

    Args:
        config_path: 설정 파일 경로 (None=기본)
        mc_mode: Monte Carlo 모드 ("quick" 또는 "full")
        skip_sim: 시뮬레이션 수집 건너뛰기
        skip_external: 외부 API 수집 건너뛰기
        skip_scenarios: 시나리오 벤치마크 건너뛰기
        external_only: 외부 데이터만 수집
        scenario_runs: 시나리오당 반복 횟수

    Returns:
        파이프라인 실행 결과 (전체 상태 + 각 단계별 결과)
    """
    config = _load_config(config_path)
    log_file = _setup_logging(config)

    pipeline_result = {
        "pipeline_version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {
            "mc_mode": mc_mode,
            "skip_sim": skip_sim or external_only,
            "skip_external": skip_external,
            "skip_scenarios": skip_scenarios or external_only,
            "scenario_runs": scenario_runs,
        },
        "stages": {},
        "errors": [],
        "log_file": log_file,
        "status": "running",
    }

    if external_only:
        skip_sim = True
        skip_scenarios = True

    t0 = time.monotonic()
    logger.info("=" * 60)
    logger.info("SDACS 자동화 파이프라인 시작")
    logger.info("=" * 60)

    # ── Stage 1: 수집 ────────────────────────────────────────
    mc_data = None
    scenario_data = None
    external_data = None

    # 1a) Monte Carlo
    if not skip_sim:
        logger.info("── Stage 1a: Monte Carlo 수집 ──")
        try:
            from automation.collect_sim import collect_monte_carlo
            mc_data = collect_monte_carlo(mode=mc_mode)
            pipeline_result["stages"]["collect_mc"] = {
                "status": "success",
                "total_runs": mc_data.get("total_runs"),
                "elapsed_s": mc_data.get("elapsed_s"),
            }
        except Exception as e:
            _handle_error(pipeline_result, "collect_mc", e)

    # 1b) 시나리오 벤치마크
    if not skip_scenarios:
        logger.info("── Stage 1b: 시나리오 벤치마크 수집 ──")
        try:
            from automation.collect_sim import collect_scenario_benchmarks
            scenario_data = collect_scenario_benchmarks(n_runs=scenario_runs)
            pipeline_result["stages"]["collect_scenarios"] = {
                "status": "success",
                "scenario_count": len(scenario_data.get("scenarios", {})),
                "elapsed_s": scenario_data.get("elapsed_s"),
            }
        except Exception as e:
            _handle_error(pipeline_result, "collect_scenarios", e)

    # 1c) 외부 API
    if not skip_external:
        logger.info("── Stage 1c: 외부 API 수집 ──")
        try:
            from automation.collect_external import collect_all_external
            ext_config = config.get("external", {})
            external_data = collect_all_external(config=ext_config)
            pipeline_result["stages"]["collect_external"] = {
                "status": "success",
                "elapsed_s": external_data.get("elapsed_s"),
                "errors": external_data.get("errors", []),
            }
        except Exception as e:
            _handle_error(pipeline_result, "collect_external", e)

    # ── Stage 2: 가공 ────────────────────────────────────────
    logger.info("── Stage 2: 데이터 가공 ──")
    processed_data = None
    try:
        from automation.process import process_all
        filters = config.get("filters", {})
        processed_data = process_all(
            mc_data=mc_data,
            scenario_data=scenario_data,
            external_data=external_data,
            filters=filters,
        )
        pipeline_result["stages"]["process"] = {"status": "success"}
    except Exception as e:
        _handle_error(pipeline_result, "process", e)

    # ── Stage 3: 저장 ────────────────────────────────────────
    if processed_data:
        logger.info("── Stage 3: 데이터 저장 ──")
        try:
            from automation.store import store_all
            store_config = config.get("store", {})
            store_result = store_all(processed_data, config=store_config)
            pipeline_result["stages"]["store"] = {
                "status": "success",
                "local_files": store_result.get("local", {}).get("files", []),
                "db_tables": store_result.get("db", {}).get("tables_updated", []),
                "drive_status": store_result.get("drive", {}).get("status"),
                "errors": store_result.get("errors", []),
            }
        except Exception as e:
            _handle_error(pipeline_result, "store", e)
    else:
        logger.warning("가공된 데이터 없음 — 저장 단계 건너뜀")
        pipeline_result["stages"]["store"] = {"status": "skipped", "reason": "no data"}

    # ── 완료 ──────────────────────────────────────────────────
    elapsed = time.monotonic() - t0
    pipeline_result["elapsed_s"] = round(elapsed, 2)
    pipeline_result["status"] = "completed" if not pipeline_result["errors"] else "completed_with_errors"

    logger.info("=" * 60)
    logger.info("파이프라인 완료: %.1f초, 상태=%s", elapsed, pipeline_result["status"])
    if pipeline_result["errors"]:
        logger.warning("오류 %d건: %s", len(pipeline_result["errors"]), pipeline_result["errors"])
    logger.info("로그: %s", log_file)
    logger.info("=" * 60)

    return pipeline_result


def _handle_error(result: dict, stage: str, error: Exception):
    """오류 처리 및 기록."""
    tb = traceback.format_exc()
    logger.error("Stage [%s] 실패: %s\n%s", stage, error, tb)
    result["stages"][stage] = {
        "status": "error",
        "error": str(error),
        "traceback": tb,
    }
    result["errors"].append(f"{stage}: {error}")


# ── CLI ───────────────────────────────────────────────────────

def main():
    """CLI 진입점."""
    # Windows 인코딩 문제 방지
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="SDACS 자동화 파이프라인 — 수집 → 가공 → 저장",
    )
    parser.add_argument("--config", type=str, default=None,
                        help="설정 파일 경로")
    parser.add_argument("--mode", type=str, default="quick",
                        choices=["quick", "full"],
                        help="Monte Carlo 모드 (기본: quick)")
    parser.add_argument("--skip-sim", action="store_true",
                        help="시뮬레이션 수집 건너뛰기")
    parser.add_argument("--skip-external", action="store_true",
                        help="외부 API 수집 건너뛰기")
    parser.add_argument("--skip-scenarios", action="store_true",
                        help="시나리오 벤치마크 건너뛰기")
    parser.add_argument("--external-only", action="store_true",
                        help="외부 데이터만 수집")
    parser.add_argument("--scenario-runs", type=int, default=3,
                        help="시나리오당 반복 횟수 (기본: 3)")

    args = parser.parse_args()

    result = run_pipeline(
        config_path=args.config,
        mc_mode=args.mode,
        skip_sim=args.skip_sim,
        skip_external=args.skip_external,
        skip_scenarios=args.skip_scenarios,
        external_only=args.external_only,
        scenario_runs=args.scenario_runs,
    )

    # 결과 요약 출력
    print("\n" + "=" * 50)
    print(f"  파이프라인 상태: {result['status']}")
    print(f"  실행 시간: {result.get('elapsed_s', 0):.1f}초")
    print(f"  로그 파일: {result.get('log_file', 'N/A')}")
    if result["errors"]:
        print(f"  오류: {len(result['errors'])}건")
        for err in result["errors"]:
            print(f"    - {err}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
