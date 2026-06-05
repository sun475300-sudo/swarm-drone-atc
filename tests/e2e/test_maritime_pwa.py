"""해양 시뮬레이터 PWA + 모바일 viewport 스모크 (자체 피드백 라운드 추가)."""
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
        pg.wait_for_timeout(500)
        yield pg, errors
        ctx.close()
        browser.close()


def test_maritime_viewport_fit_cover(page):
    pg, _ = page
    r = pg.evaluate("document.querySelector('meta[name=\"viewport\"]').content")
    assert "viewport-fit=cover" in r, f"viewport-fit=cover missing: {r}"
    assert "user-scalable=no" in r


def test_maritime_theme_color(page):
    pg, _ = page
    r = pg.evaluate("document.querySelector('meta[name=\"theme-color\"]')?.content")
    assert r == "#02060d", f"theme-color mismatch: {r}"


def test_maritime_manifest_link(page):
    pg, _ = page
    r = pg.evaluate("document.querySelector('link[rel=\"manifest\"]')?.href || ''")
    assert "manifest" in r


def test_maritime_apple_mobile_meta(page):
    pg, _ = page
    r = pg.evaluate("""
        () => ({
            cap: document.querySelector('meta[name="apple-mobile-web-app-capable"]')?.content,
            status: document.querySelector('meta[name="apple-mobile-web-app-status-bar-style"]')?.content,
        })
    """)
    assert r["cap"] == "yes"
    assert r["status"] == "black-translucent"


def test_maritime_serves_manifest(page, http_server):
    pg, _ = page
    r = pg.evaluate(f"""
        async () => {{
            const resp = await fetch('{http_server}/manifest.webmanifest');
            if (!resp.ok) return {{ ok: false }};
            const j = await resp.json();
            return {{ ok: true, name: j.name, shortcuts: j.shortcuts?.length || 0 }};
        }}
    """)
    assert r["ok"]
    assert r["name"].startswith("SDACS")
    assert r["shortcuts"] == 2, f"manifest shortcuts must contain ATC + Maritime: {r}"


def test_maritime_no_js_errors(page):
    pg, errors = page
    benign = ["favicon", "WebGPU", "DevTools", "ws_bridge", "WebSocket",
              "ERR_CERT", "ERR_CONNECTION", "fonts.googleapis", "AudioContext"]
    blocking = [e for e in errors if not any(m in e for m in benign)]
    assert not blocking, f"JS errors: {blocking}"
