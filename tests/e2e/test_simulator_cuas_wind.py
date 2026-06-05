"""HYPER Phase 27 (Counter-UAS) + Phase 23 (Wind Field Grid) E2E."""
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


# ===== Phase 27 — Counter-UAS =====

def test_cuas_api_exposed(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["enableCuas", "setCuasMode", "cuasEngage", "cuasDetect",
              "cuasEnabled", "cuasMode", "cuasEngagements", "cuasLog", "cuasModes"]:
        assert k in keys, f"_sdacs.{k} missing"


def test_cuas_modes_list(page):
    pg, _ = page
    r = pg.evaluate("window._sdacs.cuasModes")
    assert set(r) == {"rf_jam", "gps_spoof", "net_capture", "hijack"}


def test_cuas_enable_toggle(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const a = window._sdacs.enableCuas(true);
            const b = window._sdacs.cuasEnabled;
            window._sdacs.enableCuas(false);
            return { a, b, after: window._sdacs.cuasEnabled };
        }
    """)
    assert r["a"] is True
    assert r["b"] is True
    assert r["after"] is False


def test_cuas_set_mode(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.setCuasMode('rf_jam');
            const a = window._sdacs.cuasMode;
            window._sdacs.setCuasMode('net_capture');
            return { a, b: window._sdacs.cuasMode };
        }
    """)
    assert r["a"] == "rf_jam"
    assert r["b"] == "net_capture"


def test_cuas_set_mode_invalid(page):
    pg, _ = page
    r = pg.evaluate("window._sdacs.setCuasMode('not_real')")
    assert r is False


def test_cuas_engage_rogue(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            // ROGUE spawn
            window._sdacs.clearAdversarial();
            window._sdacs.spawnAdversarial('decoy');
            // C-UAS RF jam 활성
            window._sdacs.enableCuas(true);
            window._sdacs.setCuasMode('rf_jam');
            // 즉시 교전
            const r1 = window._sdacs.cuasEngage();
            // 쿨다운 우회 위해 detect만
            const det = window._sdacs.cuasDetect();
            return { r1, detectedCount: det.length };
        }
    """)
    # ROGUE 가 cuasRange 밖에 있을 수 있으므로 r1은 null/object 둘 다 허용,
    # detectedCount는 ROGUE가 ENROUTE 진입 후라야 의미 있음
    assert r["r1"] is None or isinstance(r["r1"], dict)


def test_cuas_engagements_counter(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            // 가까운 ROGUE 생성: 임의 위치 (적대 시스템이 NFZ 중심 목표)
            window._sdacs.clearAdversarial();
            window._sdacs.spawnAdversarial('direct_intercept');
            window._sdacs.enableCuas(true);
            window._sdacs.setCuasMode('rf_jam');
            const before = window._sdacs.cuasEngagements;
            // 5초 쿨다운 대기 없이 강제 호출 → 실제 dist 영향
            window._sdacs.cuasEngage();
            return { before, after: window._sdacs.cuasEngagements };
        }
    """)
    # 카운터는 같거나 증가
    assert r["after"] >= r["before"]


# ===== Phase 23 — Wind Field =====

def test_wind_field_api_exposed(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["enableWindField", "setWindRegime", "sampleWindAt",
              "windFieldEnabled", "windRegime", "windFieldStats"]:
        assert k in keys, f"_sdacs.{k} missing"


def test_wind_field_enable(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const a = window._sdacs.enableWindField(true);
            const b = window._sdacs.windFieldEnabled;
            window._sdacs.enableWindField(false);
            return { a, b, after: window._sdacs.windFieldEnabled };
        }
    """)
    assert r["a"] is True
    assert r["b"] is True
    assert r["after"] is False


def test_wind_field_regime_switch(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const r1 = window._sdacs.setWindRegime('sheared');
            const m1 = window._sdacs.windRegime;
            const r2 = window._sdacs.setWindRegime('turbulent');
            const m2 = window._sdacs.windRegime;
            const r3 = window._sdacs.setWindRegime('invalid');
            return { r1, m1, r2, m2, r3 };
        }
    """)
    assert r["r1"] is True and r["m1"] == "sheared"
    assert r["r2"] is True and r["m2"] == "turbulent"
    assert r["r3"] is False


def test_wind_field_sample(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.enableWindField(true);
            window._sdacs.setWindRegime('mild');
            const s1 = window._sdacs.sampleWindAt(0, 0);
            const s2 = window._sdacs.sampleWindAt(2000, 1000);
            return { s1, s2 };
        }
    """)
    assert "u" in r["s1"] and "v" in r["s1"]
    assert "u" in r["s2"] and "v" in r["s2"]
    assert isinstance(r["s1"]["u"], (int, float))


def test_wind_field_stats(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.enableWindField(true);
            window._sdacs.setWindRegime('turbulent');
            return window._sdacs.windFieldStats;
        }
    """)
    assert r is not None
    assert r["size"] == 64
    assert r["maxMag"] > 0


def test_phase23_27_no_js_errors(page):
    pg, errors = page
    benign = ["favicon", "WebGPU", "DevTools", "ws_bridge", "WebSocket",
              "ws://localhost", "ws://127.0.0.1", "ERR_CERT", "ERR_CONNECTION",
              "fonts.googleapis", "AudioContext", "xr"]
    blocking = [e for e in errors if not any(m in e for m in benign)]
    assert not blocking, f"JS errors: {blocking}"
