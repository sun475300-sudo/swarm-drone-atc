"""Phase 4 CAM (카메라 모드 — FPV 온보드 · 측면 뷰 · FOV · 카메라 흔들림) Playwright 스모크."""
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


def test_cam_api_exposed(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["setCamMode", "camMode", "fpvActive", "fov", "setFov", "cameraShake"]:
        assert k in keys, f"_sdacs.{k} missing"


def test_cam_preset_modes_switch(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const out = {};
            for (const m of ['reset', 'top', 'side', 'orbit']) {
                window._sdacs.setCamMode(m);
                out[m] = window._sdacs.camMode;
            }
            return out;
        }
    """)
    assert r["reset"] == "reset"
    assert r["top"] == "top"
    assert r["side"] == "side"
    assert r["orbit"] == "orbit"


def test_cam_fpv_requires_selection(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.deselectDrone && window._sdacs.deselectDrone();
            window._sdacs.setCamMode('reset');
            window._sdacs.setCamMode('fpv');  // 선택 없음 → 진입 거부
            return window._sdacs.camMode;
        }
    """)
    assert r != "fpv"


def test_cam_fpv_activates_with_drone(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.selectDrone(0);
            window._sdacs.setCamMode('fpv');
            const active = window._sdacs.fpvActive;
            const hud = document.getElementById('fpv-hud');
            const visible = hud && hud.style.display !== 'none';
            window._sdacs.setCamMode('reset');  // 정리: HUD 숨김 + 컨트롤 복원
            const hudAfter = hud && hud.style.display === 'none';
            return { active, visible, hudAfter };
        }
    """)
    assert r["active"] is True
    assert r["visible"] is True
    assert r["hudAfter"] is True


def test_cam_fov_clamp(page):
    pg, _ = page
    r = pg.evaluate("""
        () => ({
            lo: window._sdacs.setFov(10),
            hi: window._sdacs.setFov(140),
            mid: window._sdacs.setFov(55),
        })
    """)
    assert r["lo"] == 30
    assert r["hi"] == 90
    assert r["mid"] == 55


def test_cam_shake_callable(page):
    pg, _ = page
    r = pg.evaluate("() => window._sdacs.cameraShake(0.3)")
    assert r is True


def test_cam_ui_buttons_present(page):
    pg, _ = page
    r = pg.evaluate("""
        () => ({
            fpv: !!document.querySelector('.cam-preset[data-cam=\"fpv\"]'),
            side: !!document.querySelector('.cam-preset[data-cam=\"side\"]'),
            hud: !!document.getElementById('fpv-hud'),
        })
    """)
    for k, v in r.items():
        assert v, f"CAM UI element missing: {k}"


def test_no_js_errors_with_cam(page):
    pg, errors = page
    benign = ["favicon", "WebGPU", "DevTools", "ws_bridge", "WebSocket",
              "ws://localhost", "ws://127.0.0.1", "ERR_CERT", "ERR_CONNECTION",
              "fonts.googleapis"]
    blocking = [e for e in errors if not any(m in e for m in benign)]
    assert not blocking, f"JS errors: {blocking}"
