"""
데이터 저장 모듈
===============
가공된 데이터를 로컬 파일, Google Drive/Sheets, SQLite DB에 동시 저장.
각 저장소가 독립적으로 동작 — 하나가 실패해도 나머지는 계속.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("automation.store")

_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DATA_DIR = _ROOT / "data" / "pipeline"
_DEFAULT_DB_PATH = _ROOT / "data" / "pipeline" / "sdacs_pipeline.db"


# ── 로컬 파일 저장 ───────────────────────────────────────────

def store_local(
    data: dict[str, Any],
    output_dir: Optional[str] = None,
    formats: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    가공된 데이터를 로컬 파일로 저장.

    Args:
        data: 저장할 데이터
        output_dir: 출력 디렉토리 (기본: data/pipeline/)
        formats: 저장 포맷 목록 (기본: ["csv", "json"])

    Returns:
        {"files": [str], "error": str|None}
    """
    formats = formats or ["csv", "json"]
    out_dir = Path(output_dir) if output_dir else _DEFAULT_DATA_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_files = []

    try:
        # JSON 저장
        if "json" in formats:
            json_path = out_dir / f"pipeline_{ts}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            saved_files.append(str(json_path))
            logger.info("  로컬 JSON 저장: %s", json_path)

        # CSV 저장 (시뮬레이션 결과가 있는 경우)
        if "csv" in formats:
            csv_files = _save_csv(data, out_dir, ts)
            saved_files.extend(csv_files)

        # Excel 저장
        if "xlsx" in formats:
            xlsx_files = _save_xlsx(data, out_dir, ts)
            saved_files.extend(xlsx_files)

        return {"files": saved_files, "error": None}

    except Exception as e:
        logger.error("  로컬 저장 실패: %s", e)
        return {"files": saved_files, "error": str(e)}


def _save_csv(data: dict, out_dir: Path, ts: str) -> list[str]:
    """DataFrame 변환 가능한 데이터를 CSV로 저장."""
    import pandas as pd
    saved = []

    # MC raw results → CSV
    sim = data.get("sim", {})
    mc = sim.get("mc", {})
    if isinstance(mc, dict):
        # pipeline 가공 결과에서 by_density 통계를 CSV로
        by_density = mc.get("by_density", {})
        if by_density:
            rows = []
            for density, metrics in by_density.items():
                row = {"drone_density": density}
                for metric_name, stats in metrics.items():
                    for stat_name, val in stats.items():
                        row[f"{metric_name}_{stat_name}"] = val
                rows.append(row)
            df = pd.DataFrame(rows)
            path = out_dir / f"mc_summary_{ts}.csv"
            df.to_csv(path, index=False, encoding="utf-8-sig")
            saved.append(str(path))
            logger.info("  CSV 저장: %s", path)

    # 시나리오 결과 → CSV
    scenarios = sim.get("scenarios", {})
    if isinstance(scenarios, dict) and scenarios:
        rows = []
        for name, sdata in scenarios.items():
            if isinstance(sdata, dict):
                row = {"scenario": name, "status": sdata.get("status")}
                for kpi_name, kpi_stats in sdata.get("kpis", {}).items():
                    if isinstance(kpi_stats, dict):
                        for stat, val in kpi_stats.items():
                            row[f"{kpi_name}_{stat}"] = val
                rows.append(row)
        if rows:
            df = pd.DataFrame(rows)
            path = out_dir / f"scenarios_{ts}.csv"
            df.to_csv(path, index=False, encoding="utf-8-sig")
            saved.append(str(path))
            logger.info("  CSV 저장: %s", path)

    # 암호화폐 시세 → CSV
    ext = data.get("external", {})
    crypto = ext.get("crypto_summary", {})
    prices = crypto.get("prices", {})
    if prices:
        rows = [{"market": k, "price": v} for k, v in prices.items()]
        df = pd.DataFrame(rows)
        path = out_dir / f"crypto_{ts}.csv"
        df.to_csv(path, index=False, encoding="utf-8-sig")
        saved.append(str(path))

    return saved


def _save_xlsx(data: dict, out_dir: Path, ts: str) -> list[str]:
    """데이터를 Excel 워크북으로 저장."""
    try:
        import pandas as pd

        path = out_dir / f"pipeline_report_{ts}.xlsx"
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            # MC 요약 시트
            sim = data.get("sim", {})
            mc = sim.get("mc", {})
            by_density = mc.get("by_density", {}) if isinstance(mc, dict) else {}
            if by_density:
                rows = []
                for density, metrics in by_density.items():
                    row = {"drone_density": density}
                    for m, s in metrics.items():
                        for sn, v in s.items():
                            row[f"{m}_{sn}"] = v
                    rows.append(row)
                pd.DataFrame(rows).to_excel(writer, sheet_name="MC_Summary", index=False)

            # 시나리오 시트
            scenarios = sim.get("scenarios", {})
            if isinstance(scenarios, dict) and scenarios:
                rows = []
                for name, sd in scenarios.items():
                    if isinstance(sd, dict):
                        row = {"scenario": name, "status": sd.get("status")}
                        for k, v in sd.get("kpis", {}).items():
                            if isinstance(v, dict):
                                for sn, sv in v.items():
                                    row[f"{k}_{sn}"] = sv
                        rows.append(row)
                if rows:
                    pd.DataFrame(rows).to_excel(writer, sheet_name="Scenarios", index=False)

            # 날씨 시트
            ext = data.get("external", {})
            weather = ext.get("weather_summary", {})
            if weather:
                pd.DataFrame([weather]).to_excel(writer, sheet_name="Weather", index=False)

            # 암호화폐 시트
            prices = ext.get("crypto_summary", {}).get("prices", {})
            if prices:
                rows = [{"market": k, "price": v} for k, v in prices.items()]
                pd.DataFrame(rows).to_excel(writer, sheet_name="Crypto", index=False)

        logger.info("  Excel 저장: %s", path)
        return [str(path)]

    except ImportError:
        logger.warning("  openpyxl 미설치 — Excel 저장 건너뜀")
        return []
    except Exception as e:
        logger.error("  Excel 저장 실패: %s", e)
        return []


# ── SQLite DB 저장 ────────────────────────────────────────────

def store_db(
    data: dict[str, Any],
    db_path: Optional[str] = None,
) -> dict[str, Any]:
    """
    가공된 데이터를 SQLite DB에 저장.

    테이블:
        pipeline_runs    — 파이프라인 실행 이력
        mc_summaries     — MC 드론밀도별 통계
        scenario_results — 시나리오별 KPI
        weather_logs     — 기상 데이터 이력
        crypto_prices    — 암호화폐 시세 이력
    """
    db = Path(db_path) if db_path else _DEFAULT_DB_PATH
    db.parent.mkdir(parents=True, exist_ok=True)

    result = {"db_path": str(db), "tables_updated": [], "error": None}

    try:
        conn = sqlite3.connect(str(db))
        _init_tables(conn)

        ts = datetime.now(timezone.utc).isoformat()

        # pipeline_runs
        conn.execute(
            "INSERT INTO pipeline_runs (timestamp, data_json) VALUES (?, ?)",
            (ts, json.dumps(data, default=str, ensure_ascii=False)),
        )
        result["tables_updated"].append("pipeline_runs")

        # mc_summaries
        sim = data.get("sim", {})
        mc = sim.get("mc", {})
        by_density = mc.get("by_density", {}) if isinstance(mc, dict) else {}
        for density, metrics in by_density.items():
            cr = metrics.get("conflict_resolution_rate", {})
            col = metrics.get("collision_count", {})
            conn.execute(
                """INSERT INTO mc_summaries
                   (timestamp, drone_density, collision_mean, collision_max,
                    resolution_rate_mean, resolution_rate_p95)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (ts, density,
                 col.get("mean"), col.get("p95"),
                 cr.get("mean"), cr.get("p95")),
            )
        if by_density:
            result["tables_updated"].append("mc_summaries")

        # scenario_results
        scenarios = sim.get("scenarios", {})
        if isinstance(scenarios, dict):
            for name, sd in scenarios.items():
                if isinstance(sd, dict):
                    conn.execute(
                        """INSERT INTO scenario_results
                           (timestamp, scenario_name, status, kpis_json)
                           VALUES (?, ?, ?, ?)""",
                        (ts, name, sd.get("status"),
                         json.dumps(sd.get("kpis", {}), default=str)),
                    )
            if scenarios:
                result["tables_updated"].append("scenario_results")

        # weather_logs
        ext = data.get("external", {})
        weather = ext.get("weather_summary", {})
        if weather:
            conn.execute(
                """INSERT INTO weather_logs
                   (timestamp, wind_speed_ms, wind_direction_deg,
                    temperature_c, flight_condition)
                   VALUES (?, ?, ?, ?, ?)""",
                (ts, weather.get("wind_speed_ms"),
                 weather.get("wind_direction_deg"),
                 weather.get("temperature_c"),
                 weather.get("flight_condition")),
            )
            result["tables_updated"].append("weather_logs")

        # crypto_prices
        crypto = ext.get("crypto_summary", {})
        prices = crypto.get("prices", {})
        for market, price in prices.items():
            conn.execute(
                "INSERT INTO crypto_prices (timestamp, market, price) VALUES (?, ?, ?)",
                (ts, market, price),
            )
        if prices:
            result["tables_updated"].append("crypto_prices")

        conn.commit()
        conn.close()
        logger.info("  DB 저장 완료: %s (테이블: %s)", db, result["tables_updated"])

    except Exception as e:
        logger.error("  DB 저장 실패: %s", e)
        result["error"] = str(e)

    return result


def _init_tables(conn: sqlite3.Connection):
    """DB 테이블이 없으면 생성."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            data_json TEXT
        );

        CREATE TABLE IF NOT EXISTS mc_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            drone_density INTEGER,
            collision_mean REAL,
            collision_max REAL,
            resolution_rate_mean REAL,
            resolution_rate_p95 REAL
        );

        CREATE TABLE IF NOT EXISTS scenario_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            scenario_name TEXT,
            status TEXT,
            kpis_json TEXT
        );

        CREATE TABLE IF NOT EXISTS weather_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            wind_speed_ms REAL,
            wind_direction_deg REAL,
            temperature_c REAL,
            flight_condition TEXT
        );

        CREATE TABLE IF NOT EXISTS crypto_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            market TEXT,
            price REAL
        );
    """)


# ── Google Drive 저장 (placeholder) ──────────────────────────

def store_google_drive(
    data: dict[str, Any],
    config: Optional[dict] = None,
) -> dict[str, Any]:
    """
    Google Drive/Sheets에 데이터를 저장.

    NOTE: 실제 구현은 Google API 인증이 필요합니다.
    현재는 로컬에 Google Drive 업로드용 파일을 준비하고
    Cowork의 Google Drive MCP를 통해 업로드하는 방식을 권장합니다.
    """
    config = config or {}
    logger.info("  Google Drive 저장 준비 중...")

    # Google Drive MCP가 연결되어 있으면 그것을 사용할 수 있음
    # 여기서는 로컬에 Drive 업로드 대기 파일을 준비
    drive_dir = _DEFAULT_DATA_DIR / "drive_upload"
    drive_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = drive_dir / f"sdacs_report_{ts}.json"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    logger.info("  Drive 업로드 대기 파일: %s", json_path)

    return {
        "prepared_file": str(json_path),
        "status": "ready_for_upload",
        "note": "Cowork Google Drive MCP를 통해 업로드 가능",
    }


# ── 통합 저장 함수 ────────────────────────────────────────────

def store_all(
    data: dict[str, Any],
    config: Optional[dict] = None,
) -> dict[str, Any]:
    """
    모든 저장소에 동시 저장.

    Args:
        data: 가공된 데이터
        config: 저장 설정
            - output_dir: str (로컬 출력 디렉토리)
            - formats: list[str] (로컬 포맷)
            - db_path: str (DB 경로)
            - enable_drive: bool (Drive 저장 활성화)
    """
    config = config or {}
    logger.info("데이터 저장 시작 (3곳)")

    results = {
        "type": "store_results",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "local": {},
        "db": {},
        "drive": {},
        "errors": [],
    }

    # 1) 로컬 파일
    results["local"] = store_local(
        data,
        output_dir=config.get("output_dir"),
        formats=config.get("formats", ["csv", "json"]),
    )
    if results["local"].get("error"):
        results["errors"].append(f"local: {results['local']['error']}")

    # 2) SQLite DB
    results["db"] = store_db(
        data,
        db_path=config.get("db_path"),
    )
    if results["db"].get("error"):
        results["errors"].append(f"db: {results['db']['error']}")

    # 3) Google Drive
    if config.get("enable_drive", True):
        results["drive"] = store_google_drive(data, config)

    logger.info("저장 완료: 로컬 %d파일, DB %d테이블, Drive %s",
                len(results["local"].get("files", [])),
                len(results["db"].get("tables_updated", [])),
                results["drive"].get("status", "skip"))

    return results
