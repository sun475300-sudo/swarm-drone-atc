"""TRANSCENDENCE Phase 211-220 — beta→production 격상 18종 결정적 E2E.

격상 대상 (검증 통과가 격상 전제조건):
- NOTAM 4종:        notamAdd · notamImportJson · notams · notamCount
- Wind Field 6종:   enableWindField · setWindRegime · sampleWindAt
                    · windFieldEnabled · windRegime · windFieldStats
- Choreography 4종: startChoreography · clearChoreography · choreoPattern · choreoPatterns
- Forecast 4종:     generateForecast · forecastQueryHour · forecastFlyableHours · forecastData

각 API 는 (1) 호출 안전 (2) 결정적 반환 형식 (3) 상태 왕복(설정→조회 일관)을 검증.
"""

from __future__ import annotations

import http.server
import os
import socketserver
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

PROMOTED = [
    "notamAdd", "notamImportJson", "notams", "notamCount",
    "enableWindField", "setWindRegime", "sampleWindAt",
    "windFieldEnabled", "windRegime", "windFieldStats",
    "startChoreography", "clearChoreography", "choreoPattern", "choreoPatterns",
    "generateForecast", "forecastQueryHour", "forecastFlyableHours", "forecastData",
]


@pytest.fixture(scope="module")
def http_server():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **kw):
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", 0), Quiet)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    os.chdir(ROOT)
    time.sleep(0.2)
    yield f"http://127.0.0.1:{port}"
    httpd.shutdown()
    httpd.server_close()


@pytest.fixture(scope="module")
def page(http_server):
    pw = pytest.importorskip("playwright.sync_api")
    with pw.sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        pg = ctx.new_page()
        pg.goto(f"{http_server}/swarm_3d_simulator.html",
                wait_until="networkidle", timeout=30000)
        pg.wait_for_function("window._sdacs && window._sdacs.droneCount > 0", timeout=20000)
        # choreography 는 비행 중 드론을 요구 — 시뮬 기동 후 이륙 대기 (느린 CI 45s)
        pg.evaluate("window._sdacs.startSim()")
        pg.wait_for_function("window._sdacs.airborne > 0", timeout=45000)
        yield pg
        ctx.close()
        browser.close()


# ── NOTAM 4종 ──────────────────────────────────────────────────────────────

def test_notam_add_and_count_roundtrip(page):
    r = page.evaluate("""(() => {
        const before = window._sdacs.notamCount;
        const id = window._sdacs.notamAdd({ type: 'TFR', x: 100, z: 100, radius: 200,
                                            reason: 'promotion-e2e' });
        return { before, after: window._sdacs.notamCount, id,
                 list: window._sdacs.notams };
    })()""")
    assert r["after"] == r["before"] + 1
    assert isinstance(r["list"], list) and len(r["list"]) == r["after"]


def test_notam_import_json_deterministic(page):
    r = page.evaluate("""(() => {
        const payload = JSON.stringify([{ type: 'TFR', x: -300, z: 250, radius: 150, reason: 'import-e2e' }]);
        const before = window._sdacs.notamCount;
        const imported = window._sdacs.notamImportJson(payload);
        return { before, imported, after: window._sdacs.notamCount };
    })()""")
    assert r["imported"] >= 1
    assert r["after"] == r["before"] + r["imported"]


# ── Wind Field 6종 ─────────────────────────────────────────────────────────

def test_windfield_enable_regime_roundtrip(page):
    r = page.evaluate("""(() => {
        window._sdacs.enableWindField(true);
        const ok = window._sdacs.setWindRegime('turbulent');   // 유효: mild|sheared|turbulent
        const rejected = window._sdacs.setWindRegime('gale');  // 미지원 → false (화이트리스트)
        return { enabled: window._sdacs.windFieldEnabled, ok, rejected,
                 regime: window._sdacs.windRegime };
    })()""")
    assert r["enabled"] is True
    assert r["ok"] is True and r["rejected"] is False
    assert r["regime"] == "turbulent"


def test_windfield_sample_finite_and_stats(page):
    r = page.evaluate("""(() => {
        const s = window._sdacs.sampleWindAt(100, 100);
        const st = window._sdacs.windFieldStats;
        return { s, st };
    })()""")
    s = r["s"]
    assert s is not None and all(
        isinstance(s.get(k), (int, float)) for k in ("u", "v")
    ), f"sampleWindAt 비수치: {s}"
    assert isinstance(r["st"], dict)


def test_windfield_disable_restores(page):
    r = page.evaluate("""(() => {
        window._sdacs.enableWindField(false);
        return window._sdacs.windFieldEnabled;
    })()""")
    assert r is False


# ── Choreography 4종 ───────────────────────────────────────────────────────

def test_choreo_patterns_catalog(page):
    pats = page.evaluate("window._sdacs.choreoPatterns")
    assert isinstance(pats, list) and len(pats) >= 3


def test_choreo_start_clear_roundtrip(page):
    r = page.evaluate("""(() => {
        const pats = window._sdacs.choreoPatterns;
        const started = window._sdacs.startChoreography(pats[0]);
        const active = window._sdacs.choreoPattern;
        window._sdacs.clearChoreography();
        return { started, active, cleared: window._sdacs.choreoPattern };
    })()""")
    assert r["active"] is not None
    assert r["cleared"] in (None, "", "none")


# ── Forecast 4종 ───────────────────────────────────────────────────────────

def test_forecast_generate_and_query(page):
    r = page.evaluate("""(() => {
        const count = window._sdacs.generateForecast(24);
        const data = window._sdacs.forecastData;
        const q = window._sdacs.forecastQueryHour(6);
        const flyable = window._sdacs.forecastFlyableHours(10, 5);
        return { count, n: Array.isArray(data) ? data.length : -1, q, flyable };
    })()""")
    assert r["count"] == 24
    assert r["n"] == 5  # forecastData getter 는 5개 미리보기 slice (설계 계약)
    assert r["q"] is not None and r["q"]["hour"] == 6
    assert isinstance(r["flyable"], (int, float, list))


def test_forecast_deterministic_requery(page):
    """동일 시간 재질의 → 동일 결과 (생성 후 조회는 순수)."""
    a = page.evaluate("window._sdacs.forecastQueryHour(3)")
    b = page.evaluate("window._sdacs.forecastQueryHour(3)")
    assert a == b


# ── 격상 분류 회귀 (격상 커밋 후 GREEN 되는 게이트) ─────────────────────────

def test_promoted_apis_classified_production(page):
    res = page.evaluate(
        "(names) => names.map(n => [n, window._sdacs.apiMaturity(n)])", PROMOTED
    )
    not_prod = [n for n, m in res if m != "production"]
    assert not_prod == [], f"미격상: {not_prod}"
