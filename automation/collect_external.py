"""
외부 API 데이터 수집 모듈
========================
암호화폐 시세, 날씨/환경, SC2 래더 데이터를 수집한다.

각 수집기는 독립적으로 동작하며, 하나가 실패해도 나머지는 계속 실행.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError

logger = logging.getLogger("automation.collect_external")

_TIMEOUT = 15  # HTTP 요청 타임아웃 (초)


def _fetch_json(url: str, headers: Optional[dict] = None) -> Any:
    """URL에서 JSON 응답을 가져온다."""
    req = Request(url)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    with urlopen(req, timeout=_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ── 암호화폐 시세 (Upbit 공개 API) ───────────────────────────

def collect_crypto(
    markets: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Upbit 공개 API에서 암호화폐 시세를 수집.

    Args:
        markets: 마켓 코드 목록 (기본: BTC, ETH, XRP)

    Returns:
        {
            "type": "crypto",
            "timestamp": str,
            "source": "upbit",
            "tickers": [...],
            "error": str | None,
        }
    """
    if markets is None:
        markets = ["KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-SOL", "KRW-DOGE"]

    logger.info("암호화폐 시세 수집: %s", markets)
    result: dict[str, Any] = {
        "type": "crypto",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "upbit",
        "tickers": [],
        "error": None,
    }

    try:
        market_str = ",".join(markets)
        url = f"https://api.upbit.com/v1/ticker?markets={market_str}"
        data = _fetch_json(url)

        tickers = []
        for item in data:
            tickers.append({
                "market": item.get("market"),
                "trade_price": item.get("trade_price"),
                "signed_change_rate": item.get("signed_change_rate"),
                "acc_trade_volume_24h": item.get("acc_trade_volume_24h"),
                "acc_trade_price_24h": item.get("acc_trade_price_24h"),
                "high_price": item.get("high_price"),
                "low_price": item.get("low_price"),
                "timestamp": item.get("timestamp"),
            })
        result["tickers"] = tickers
        logger.info("  암호화폐 %d개 마켓 수집 완료", len(tickers))

    except Exception as e:
        logger.error("  암호화폐 수집 실패: %s", e)
        result["error"] = str(e)

    return result


# ── 날씨/환경 데이터 (Open-Meteo 무료 API) ───────────────────

def collect_weather(
    lat: float = 35.1595,
    lon: float = 126.8526,
) -> dict[str, Any]:
    """
    Open-Meteo API에서 현재 기상 데이터를 수집.
    (기본 좌표: 광주광역시 — SDACS 시뮬레이션 기준점)

    Returns:
        {
            "type": "weather",
            "timestamp": str,
            "source": "open-meteo",
            "location": {"lat": ..., "lon": ...},
            "current": {...},
            "hourly_forecast": [...],
            "error": str | None,
        }
    """
    logger.info("날씨 데이터 수집: lat=%.4f, lon=%.4f", lat, lon)
    result: dict[str, Any] = {
        "type": "weather",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "open-meteo",
        "location": {"lat": lat, "lon": lon},
        "current": {},
        "hourly_forecast": [],
        "error": None,
    }

    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,wind_speed_10m,wind_direction_10m,"
            f"wind_gusts_10m,relative_humidity_2m,precipitation"
            f"&hourly=temperature_2m,wind_speed_10m,wind_direction_10m,"
            f"wind_gusts_10m,precipitation_probability"
            f"&forecast_hours=24&timezone=Asia/Seoul"
        )
        data = _fetch_json(url)

        # 현재 기상
        current = data.get("current", {})
        result["current"] = {
            "temperature_c": current.get("temperature_2m"),
            "wind_speed_ms": current.get("wind_speed_10m"),
            "wind_direction_deg": current.get("wind_direction_10m"),
            "wind_gusts_ms": current.get("wind_gusts_10m"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "precipitation_mm": current.get("precipitation"),
        }

        # 24시간 예보 (시간별)
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        for i, t in enumerate(times):
            result["hourly_forecast"].append({
                "time": t,
                "temperature_c": hourly.get("temperature_2m", [None])[i] if i < len(hourly.get("temperature_2m", [])) else None,
                "wind_speed_ms": hourly.get("wind_speed_10m", [None])[i] if i < len(hourly.get("wind_speed_10m", [])) else None,
                "wind_direction_deg": hourly.get("wind_direction_10m", [None])[i] if i < len(hourly.get("wind_direction_10m", [])) else None,
                "wind_gusts_ms": hourly.get("wind_gusts_10m", [None])[i] if i < len(hourly.get("wind_gusts_10m", [])) else None,
                "precipitation_prob_pct": hourly.get("precipitation_probability", [None])[i] if i < len(hourly.get("precipitation_probability", [])) else None,
            })

        logger.info("  날씨 수집 완료: 풍속=%.1f m/s, 기온=%.1f°C",
                     result["current"].get("wind_speed_ms", 0) or 0,
                     result["current"].get("temperature_c", 0) or 0)

    except Exception as e:
        logger.error("  날씨 수집 실패: %s", e)
        result["error"] = str(e)

    return result


# ── SC2 래더/리플레이 (Aligulac 공개 API) ─────────────────────

def collect_sc2(
    player_ids: Optional[list[int]] = None,
) -> dict[str, Any]:
    """
    SC2 공개 API에서 래더 및 최근 경기 데이터를 수집.

    Args:
        player_ids: Aligulac 플레이어 ID 목록 (기본: 상위 플레이어)

    Returns:
        {
            "type": "sc2",
            "timestamp": str,
            "source": "aligulac",
            "rankings": [...],
            "recent_matches": [...],
            "error": str | None,
        }
    """
    logger.info("SC2 데이터 수집 시작")
    result: dict[str, Any] = {
        "type": "sc2",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "aligulac",
        "rankings": [],
        "recent_matches": [],
        "error": None,
    }

    try:
        # Aligulac 현재 래더 랭킹 (상위 10명)
        url = "http://aligulac.com/api/v1/period/?order_by=-id&limit=1&format=json"
        period_data = _fetch_json(url)
        if period_data.get("objects"):
            period_id = period_data["objects"][0]["id"]

            ranking_url = (
                f"http://aligulac.com/api/v1/rating/"
                f"?period={period_id}&order_by=-rating&limit=10&format=json"
            )
            rank_data = _fetch_json(ranking_url)
            for entry in rank_data.get("objects", []):
                result["rankings"].append({
                    "player": entry.get("player", {}).get("tag", "?"),
                    "race": entry.get("player", {}).get("race", "?"),
                    "rating": round(entry.get("rating", 0), 1),
                    "position": entry.get("position"),
                })

        logger.info("  SC2 랭킹 %d명 수집 완료", len(result["rankings"]))

    except Exception as e:
        logger.error("  SC2 수집 실패: %s", e)
        result["error"] = str(e)

    return result


# ── 통합 수집 함수 ────────────────────────────────────────────

def collect_all_external(
    config: Optional[dict] = None,
) -> dict[str, Any]:
    """
    모든 외부 데이터를 수집하고 통합 결과를 반환.
    개별 수집기가 실패해도 나머지는 계속 실행.

    Args:
        config: 수집 설정 (선택)

    Returns:
        {
            "type": "external_all",
            "timestamp": str,
            "elapsed_s": float,
            "crypto": {...},
            "weather": {...},
            "sc2": {...},
            "errors": [str],
        }
    """
    config = config or {}
    t0 = time.monotonic()
    errors = []

    crypto = collect_crypto(
        markets=config.get("crypto_markets"),
    )
    if crypto.get("error"):
        errors.append(f"crypto: {crypto['error']}")

    weather = collect_weather(
        lat=config.get("weather_lat", 35.1595),
        lon=config.get("weather_lon", 126.8526),
    )
    if weather.get("error"):
        errors.append(f"weather: {weather['error']}")

    sc2 = collect_sc2(
        player_ids=config.get("sc2_player_ids"),
    )
    if sc2.get("error"):
        errors.append(f"sc2: {sc2['error']}")

    elapsed = time.monotonic() - t0

    return {
        "type": "external_all",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "elapsed_s": round(elapsed, 2),
        "crypto": crypto,
        "weather": weather,
        "sc2": sc2,
        "errors": errors,
    }
