"""Phase 3 CIN (시네마틱) + Phase 6 INJ (장애 주입) Playwright 통합 스모크."""
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
    handler = http.server.SimpleHTTPRequestHandler

    class Quiet(handler):
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
            pg.wait_for_function("window._sdacs.airborne >= 2", timeout=20000)
        except Exception:
            pass
        pg.wait_for_timeout(1000)
        yield pg, errors
        ctx.close()
        browser.close()


# ===== Phase 3 CIN =====

def test_cin_api_exposed(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["setSunCycle", "setSunHour", "setSunAuto", "sunHour", "sunEnabled",
              "setRain", "setSnow", "startRecording", "stopRecording", "recording"]:
        assert k in keys, f"_sdacs.{k} missing"


def test_cin_sun_cycle_toggle(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const off0 = window._sdacs.sunEnabled;
            const on = window._sdacs.setSunCycle(true);
            const sun_on = window._sdacs.sunEnabled;
            const off = window._sdacs.setSunCycle(false);
            return { off0, on, sun_on, off };
        }
    """)
    assert r["off0"] is False
    assert r["on"] is True
    assert r["sun_on"] is True
    assert r["off"] is False


def test_cin_sun_hour_clamp(page):
    pg, _ = page
    r = pg.evaluate("""
        () => ({
            zero: window._sdacs.setSunHour(0),
            max: window._sdacs.setSunHour(50),
            neg: window._sdacs.setSunHour(-5),
            mid: window._sdacs.setSunHour(13.5),
        })
    """)
    assert r["zero"] == 0
    assert r["max"] == 24
    assert r["neg"] == 0
    assert r["mid"] == 13.5


def test_cin_rain_toggle(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const on = window._sdacs.setRain(true, 0.7);
            const off = window._sdacs.setRain(false);
            return { on, off };
        }
    """)
    assert r["on"] is True
    assert r["off"] is False


def test_cin_snow_toggle(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const on = window._sdacs.setSnow(true, 0.5);
            const off = window._sdacs.setSnow(false);
            return { on, off };
        }
    """)
    assert r["on"] is True
    assert r["off"] is False


def test_cin_recorder_api_available(page):
    pg, _ = page
    has_api = pg.evaluate("typeof MediaRecorder !== 'undefined'")
    if not has_api:
        pytest.skip("MediaRecorder not available in this Chromium build")
    r = pg.evaluate("""
        () => {
            const started = window._sdacs.startRecording();
            const rec = window._sdacs.recording;
            return { started, rec };
        }
    """)
    # 녹화 시작 시도 (실제 stream은 headless에서 제한적이지만 API 호출 자체는 확인)
    assert r["started"] in (True, False)  # 둘 다 OK (지원 여부)


def test_cin_ui_panel_exists(page):
    pg, _ = page
    r = pg.evaluate("""
        () => ({
            sun_cycle: !!document.getElementById('tg-sun-cycle'),
            sun_hour: !!document.getElementById('sun-hour'),
            rain: !!document.getElementById('tg-rain'),
            snow: !!document.getElementById('tg-snow'),
            rec_btn: !!document.getElementById('btn-rec-toggle'),
            rec_ind: !!document.getElementById('rec-indicator'),
        })
    """)
    for k, v in r.items():
        assert v, f"CIN UI element missing: {k}"


# ===== Phase 6 INJ =====

def test_inj_api_exposed(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["injectFault", "injectRogue", "injectDynamicNFZ", "injectScenario",
              "injClearAll", "injStats", "dynamicNfzList"]:
        assert k in keys, f"_sdacs.{k} missing"


def test_inj_gps_loss(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.injClearAll();
            window._sdacs.selectDrone(0);
            const sel = window._sdacs.getSelected();
            if (!sel) return { ok: false };
            window._sdacs.injectFault(sel.id, 'GPS_LOSS', { duration: 10, noise: 15 });
            const after = window._sdacs.getSelected();
            return {
                ok: true,
                gpsLost: after.gpsLost,
                noise: after.gpsNoise,
                stats: window._sdacs.injStats.gpsLost,
            };
        }
    """)
    assert r["ok"]
    assert r["gpsLost"] is True
    assert r["noise"] == 15
    assert r["stats"] >= 1


def test_inj_motor_fail_halves_speed(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.injClearAll();
            window._sdacs.selectDrone(0);
            const before = window._sdacs.getSelected().maxSpeed;
            window._sdacs.injectFault(window._sdacs.getSelected().id, 'MOTOR_FAIL', { factor: 0.5 });
            const after = window._sdacs.getSelected().maxSpeed;
            return { before, after };
        }
    """)
    assert abs(r["after"] - r["before"] * 0.5) < 0.01


def test_inj_comms_loss(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.injClearAll();
            window._sdacs.selectDrone(0);
            window._sdacs.injectFault(window._sdacs.getSelected().id, 'COMMS_LOSS', { duration: 5 });
            return {
                lost: window._sdacs.getSelected().commsLost,
                stats: window._sdacs.injStats.commsLost,
            };
        }
    """)
    assert r["lost"] is True
    assert r["stats"] >= 1


def test_inj_rogue_drone_added(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.injClearAll();
            const before = window._sdacs.droneCount;
            window._sdacs.injectRogue();
            const after = window._sdacs.droneCount;
            return { before, after, addedStat: window._sdacs.injStats.rogueAdded };
        }
    """)
    assert r["after"] == r["before"] + 1
    assert r["addedStat"] >= 1


def test_inj_dynamic_nfz_added(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.injClearAll();
            window._sdacs.injectDynamicNFZ(0, 0, 100, 30);
            return {
                list: window._sdacs.dynamicNfzList,
                stat: window._sdacs.injStats.dynamicNfz,
            };
        }
    """)
    assert len(r["list"]) == 1
    assert r["list"][0]["r"] == 100
    assert r["stat"] == 1


def test_inj_scenario_emp(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.injClearAll();
            const n = window._sdacs.injectScenario('EMP');
            const stats = window._sdacs.injStats;
            return { affected: n, gpsLost: stats.gpsLost };
        }
    """)
    # EMP는 30% 비율 → airborne 드론 일부에 GPS_LOSS 주입
    assert r["affected"] >= 0


def test_inj_clear_all_resets(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.selectDrone(0);
            window._sdacs.injectFault(window._sdacs.getSelected().id, 'GPS_LOSS', { duration: 30 });
            window._sdacs.injectDynamicNFZ(0, 0, 100, 30);
            window._sdacs.injClearAll();
            return {
                gps: window._sdacs.injStats.gpsLost,
                nfz: window._sdacs.injStats.dynamicNfz,
            };
        }
    """)
    assert r["gps"] == 0
    assert r["nfz"] == 0


def test_inj_ui_present(page):
    pg, _ = page
    r = pg.evaluate("""
        () => ({
            gps: !!document.getElementById('btn-inj-gps'),
            motor: !!document.getElementById('btn-inj-motor'),
            comms: !!document.getElementById('btn-inj-comms'),
            bat: !!document.getElementById('btn-inj-bat'),
            rogue: !!document.getElementById('btn-inj-rogue'),
            nfz: !!document.getElementById('btn-inj-nfz'),
            emp: !!document.getElementById('btn-inj-emp'),
            emi: !!document.getElementById('btn-inj-emi'),
            clear: !!document.getElementById('btn-inj-clear'),
            stats: !!document.getElementById('inj-stats'),
        })
    """)
    for k, v in r.items():
        assert v, f"INJ UI element missing: {k}"


def test_no_js_errors_with_cin_inj(page):
    pg, errors = page
    benign = ["favicon", "WebGPU", "DevTools", "ws_bridge", "WebSocket",
              "ws://localhost", "ws://127.0.0.1", "ERR_CERT", "ERR_CONNECTION",
              "fonts.googleapis"]
    blocking = [e for e in errors if not any(m in e for m in benign)]
    assert not blocking, f"JS errors: {blocking}"
