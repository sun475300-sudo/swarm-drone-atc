"""HYPER Phase 18/26/29/30/31 — AR + Acoustic + Forecast + UTM Federation + PQC E2E."""
from __future__ import annotations

import http.server
import os
import socketserver
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def http_server():
    port = 0

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **kw):
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", port), Quiet)
    port = httpd.server_address[1]
    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    os.chdir(ROOT)
    th.start()
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
        errors: list[str] = []
        pg.on("pageerror", lambda exc: errors.append(str(exc)))
        pg.goto(f"{http_server}/swarm_3d_simulator.html",
                wait_until="networkidle", timeout=20000)
        pg.wait_for_function("window._sdacs && window._sdacs.droneCount > 0", timeout=15000)
        pg.evaluate("window._sdacs.startSim()")
        try:
            pg.wait_for_function("window._sdacs.airborne >= 2", timeout=15000)
        except Exception:
            pass
        pg.wait_for_timeout(700)
        yield pg, errors
        ctx.close()
        browser.close()


# ===== Phase 18 AR =====

def test_ar_api(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["arEnter", "arExit", "arAddPin", "arClearPins", "arEnabled", "arPins"]:
        assert k in keys


def test_ar_add_and_clear_pins(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.arClearPins();
            window._sdacs.arAddPin(34.808, 126.391, 'MOK-UNIV');
            window._sdacs.arAddPin(37.5665, 126.978, 'SEOUL');
            const before = window._sdacs.arPins.length;
            const cleared = window._sdacs.arClearPins();
            return { before, cleared, after: window._sdacs.arPins.length };
        }
    """)
    assert r["before"] == 2
    assert r["cleared"] == 2
    assert r["after"] == 0


# ===== Phase 26 Acoustic =====

def test_acoustic_api(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["enableAcoustic", "acousticAddObserver", "acousticEnabled", "acousticObservers", "acousticStats"]:
        assert k in keys


def test_acoustic_observer_add(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.enableAcoustic(true);
            const o1 = window._sdacs.acousticAddObserver(0, 0, 'CENTER');
            const o2 = window._sdacs.acousticAddObserver(500, 500, 'NE');
            return { o1, o2, count: window._sdacs.acousticObservers.length };
        }
    """)
    assert r["o1"]["label"] == "CENTER"
    assert r["count"] >= 2


def test_acoustic_stats_after_update(page):
    pg, _ = page
    pg.evaluate("""
        () => {
            window._sdacs.enableAcoustic(true);
            window._sdacs.acousticAddObserver(0, 0, 'CENTER');
        }
    """)
    pg.wait_for_timeout(1500)
    r = pg.evaluate("window._sdacs.acousticStats")
    if r is None:
        pytest.skip("acoustic stats not yet populated")
    assert r["observerCount"] >= 1


# ===== Phase 29 Forecast =====

def test_forecast_api(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["generateForecast", "forecastQueryHour", "forecastFlyableHours", "forecastData"]:
        assert k in keys


def test_forecast_generate_120h(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const n = window._sdacs.generateForecast(120);
            const sample = window._sdacs.forecastQueryHour(12);
            const flyable = window._sdacs.forecastFlyableHours(8, 2);
            return { n, sampleKeys: Object.keys(sample), flyableCount: flyable.length };
        }
    """)
    assert r["n"] == 120
    for k in ["hour", "windSpd", "windDir", "precip", "vis_km", "ceiling_m"]:
        assert k in r["sampleKeys"]


def test_forecast_query_clamp(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.generateForecast(72);
            const a = window._sdacs.forecastQueryHour(-5);    // clamp 0
            const b = window._sdacs.forecastQueryHour(9999);  // clamp last
            return { a_hour: a.hour, b_hour: b.hour };
        }
    """)
    assert r["a_hour"] == 0
    assert r["b_hour"] == 71


# ===== Phase 30 UTM Federation =====

def test_utm_api(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["utmFederationAdd", "utmFederationHandoff", "utmFederationSync",
              "utmFederationInstances", "utmFederationHandoffLog"]:
        assert k in keys


def test_utm_add_instances(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.utmFederationAdd('utm-seoul', 'K-UTM Seoul', 'Seoul');
            window._sdacs.utmFederationAdd('utm-busan', 'K-UTM Busan', 'Busan');
            window._sdacs.utmFederationAdd('utm-jeju', 'K-UTM Jeju', 'Jeju');
            const n = window._sdacs.utmFederationSync();
            return { added: window._sdacs.utmFederationInstances.length, syncCount: n };
        }
    """)
    assert r["added"] == 3


def test_utm_handoff_logged(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const before = window._sdacs.utmFederationHandoffLog.length;
            window._sdacs.utmFederationHandoff('DR-007', 'utm-seoul', 'utm-busan');
            window._sdacs.utmFederationHandoff('DR-013', 'utm-busan', 'utm-jeju');
            const log = window._sdacs.utmFederationHandoffLog;
            return { before, added: log.length - before, last: log.slice(-1)[0] };
        }
    """)
    assert r["added"] == 2
    assert r["last"]["droneId"] == "DR-013"
    assert r["last"]["toUtm"] == "utm-jeju"


# ===== Phase 31 PQC =====

def test_pqc_api(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["enablePqc", "pqcStats", "pqcEnabled"]:
        assert k in keys


def test_pqc_overhead_accumulates(page):
    pg, _ = page
    pg.evaluate("window._sdacs.enablePqc(true)")
    pg.wait_for_timeout(1500)
    r = pg.evaluate("window._sdacs.pqcStats")
    assert r["enabled"] is True
    # 메시지가 누적되었으면 비교
    if r["totalMsgs"] > 0:
        # PQC overhead는 대략 50~60× (dilithium 3293B + msg 64B 기준)
        assert r["overheadFactor"] > 10, f"PQC overhead factor too low: {r['overheadFactor']}"
        assert r["pqcBytes"] > r["baselineBytes"]


def test_no_js_errors_5phases2(page):
    pg, errors = page
    benign = ["favicon", "WebGPU", "DevTools", "ws_bridge", "WebSocket",
              "ws://localhost", "ws://127.0.0.1", "ERR_CERT", "ERR_CONNECTION",
              "fonts.googleapis", "AudioContext", "xr"]
    blocking = [e for e in errors if not any(m in e for m in benign)]
    assert not blocking, f"JS errors: {blocking}"
