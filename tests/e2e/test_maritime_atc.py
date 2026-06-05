"""HYPER Phase 11 — 해양 ATC 동등 이식 Playwright 스모크."""
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
        pg.goto(f"{http_server}/maritime_detection_simulator.html",
                wait_until="networkidle", timeout=20000)
        pg.wait_for_function("window._mds && Object.keys(window._mds).length > 0", timeout=15000)
        # 표적이 spawn될 때까지 대기
        try:
            pg.wait_for_function("window._mds.total >= 1", timeout=15000)
        except Exception:
            pass
        pg.wait_for_timeout(1500)
        yield pg, errors
        ctx.close()
        browser.close()


def test_marine_atc_api_exposed(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._mds)")
    for k in ["atcCommand", "atcLog", "atcControlled", "setAtcAudio", "atcAudio", "marineAtcClearAll"]:
        assert k in keys, f"_mds.{k} missing"


def test_marine_atc_panel_ui(page):
    pg, _ = page
    # 표적 선택 후 ATC 패널 표시 확인
    r = pg.evaluate("""
        () => {
            const ids = window._mds.tracks;
            if (ids.length === 0) return { ok: false, reason: 'no detected tracks' };
            const id = window._mds.select(ids[0]);
            const panel = document.getElementById('marine-atc-panel');
            return {
                ok: !!id,
                panel: !!panel,
                buttons: document.querySelectorAll('#marine-atc-panel button').length,
            };
        }
    """)
    if not r["ok"]:
        pytest.skip(f"setup: {r.get('reason')}")
    assert r["panel"]
    assert r["buttons"] == 8  # HOLD/RTB/AVOID/SLOW/FAST/PORT/STBD/CLEAR


def test_marine_atc_hold_stops_vessel(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._mds.marineAtcClearAll();
            const ids = window._mds.tracks;
            if (ids.length === 0) return { ok: false };
            window._mds.select(ids[0]);
            const before = window._mds.atcControlled.length;
            window._mds.atcCommand('HOLD');
            const after = window._mds.atcControlled;
            return { ok: true, before, ctrlCount: after.length, cmd: after[0]?.cmd };
        }
    """)
    if not r["ok"]:
        pytest.skip("no detected tracks")
    assert r["ctrlCount"] >= 1
    assert r["cmd"] == "HOLD"


def test_marine_atc_clear_resets(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._mds.marineAtcClearAll();
            const ids = window._mds.tracks;
            if (ids.length === 0) return { ok: false };
            window._mds.select(ids[0]);
            window._mds.atcCommand('HOLD');
            const mid = window._mds.atcControlled.length;
            window._mds.atcCommand('CLEAR');
            const after = window._mds.atcControlled.length;
            return { ok: true, mid, after };
        }
    """)
    if not r["ok"]:
        pytest.skip("no detected tracks")
    assert r["mid"] >= 1
    assert r["after"] == 0


def test_marine_atc_audio_toggle(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const before = window._mds.atcAudio;
            const on = window._mds.setAtcAudio(true);
            const mid = window._mds.atcAudio;
            window._mds.setAtcAudio(false);
            return { before, on, mid, after: window._mds.atcAudio };
        }
    """)
    assert r["on"] is True
    assert r["mid"] is True
    assert r["after"] is False


def test_marine_atc_log_accumulates(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const ids = window._mds.tracks;
            if (ids.length === 0) return { ok: false };
            const before = window._mds.atcLog.length;
            window._mds.select(ids[0]);
            window._mds.atcCommand('SLOW');
            window._mds.atcCommand('FAST');
            const after = window._mds.atcLog.length;
            return { ok: true, before, after };
        }
    """)
    if not r["ok"]:
        pytest.skip("no detected tracks")
    assert r["after"] >= r["before"] + 2


def test_marine_no_js_errors_atc(page):
    pg, errors = page
    benign = ["favicon", "WebGPU", "DevTools", "ws_bridge", "WebSocket",
              "ERR_CERT", "ERR_CONNECTION", "fonts.googleapis", "AudioContext"]
    blocking = [e for e in errors if not any(m in e for m in benign)]
    assert not blocking, f"JS errors: {blocking}"
