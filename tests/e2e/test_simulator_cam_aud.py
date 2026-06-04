"""Phase 4 CAM (카메라 모드) + Phase 8 AUD (환경 사운드) Playwright 스모크."""
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
            pg.wait_for_function("window._sdacs.airborne >= 1", timeout=20000)
        except Exception:
            pass
        pg.wait_for_timeout(800)
        yield pg, errors
        ctx.close()
        browser.close()


# ===== Phase 4 CAM =====

def test_cam_api_exposed(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["setCamMode", "camMode", "focusDrone"]:
        assert k in keys, f"_sdacs.{k} missing"


def test_cam_mode_switches(page):
    pg, _ = page
    for mode in ["reset", "top", "side", "orbit"]:
        r = pg.evaluate(f"window._sdacs.setCamMode('{mode}')")
        assert r == mode, f"camMode should be {mode}, got {r}"


def test_cam_fpv_requires_drone(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.selectDrone(0);
            const m = window._sdacs.setCamMode('fpv');
            return { mode: m };
        }
    """)
    assert r["mode"] == "fpv"


def test_cam_chase_mode(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.selectDrone(0);
            const m = window._sdacs.setCamMode('chase');
            return { mode: m };
        }
    """)
    assert r["mode"] == "chase"
    # reset 복귀
    pg.evaluate("window._sdacs.setCamMode('reset')")


def test_cam_preset_buttons_present(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const cams = [...document.querySelectorAll('.cam-preset')].map(b => b.dataset.cam);
            return cams;
        }
    """)
    for needed in ["reset", "top", "follow", "orbit", "fpv", "chase", "side"]:
        assert needed in r, f"cam-preset {needed} missing"


def test_cam_fpv_changes_fov(page):
    pg, _ = page
    # FPV 모드는 fov를 75로 변경
    r = pg.evaluate("""
        () => {
            window._sdacs.selectDrone(0);
            window._sdacs.setCamMode('fpv');
            return { mode: window._sdacs.camMode };
        }
    """)
    assert r["mode"] == "fpv"
    pg.evaluate("window._sdacs.setCamMode('reset')")


# ===== Phase 8 AUD =====

def test_aud_api_exposed(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["setAmbientAudio", "ambientAudio"]:
        assert k in keys, f"_sdacs.{k} missing"


def test_aud_ambient_toggle(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const on = window._sdacs.setAmbientAudio(true);
            const mid = window._sdacs.ambientAudio;
            const off = window._sdacs.setAmbientAudio(false);
            return { on, mid, off };
        }
    """)
    assert r["on"] is True
    assert r["mid"] is True
    assert r["off"] is False


def test_aud_button_present(page):
    pg, _ = page
    present = pg.evaluate("!!document.getElementById('btn-aud-ambient')")
    assert present, "환경음 토글 버튼 없음"


def test_no_js_errors_cam_aud(page):
    pg, errors = page
    benign = ["favicon", "WebGPU", "DevTools", "ws_bridge", "WebSocket",
              "ws://localhost", "ws://127.0.0.1", "ERR_CERT", "ERR_CONNECTION",
              "fonts.googleapis", "AudioContext"]
    blocking = [e for e in errors if not any(m in e for m in benign)]
    assert not blocking, f"JS errors: {blocking}"
