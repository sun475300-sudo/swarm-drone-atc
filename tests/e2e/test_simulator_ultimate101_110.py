"""ULTIMATE Phase 101-110 — Performance Beyond E2E."""
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
        pg.wait_for_timeout(400)
        yield pg, errors
        ctx.close()
        browser.close()


def test_phase101_petaflop(page):
    pg, _ = page
    r = pg.evaluate("window._sdacs.petaflop101Activate(2500)")
    assert r["tflops"] == 2500


def test_phase102_quantum_hash(page):
    pg, _ = page
    r = pg.evaluate("window._sdacs.quantum102Hash(1024)")
    assert 9 <= r <= 11  # log2(1024) = 10


def test_phase103_photonic(page):
    pg, _ = page
    r = pg.evaluate("window._sdacs.photonic103Init([1310, 1550, 1625])")
    assert 1625 in r


def test_phase104_optane(page):
    pg, _ = page
    r = pg.evaluate("window._sdacs.optane104Snapshot()")
    assert "droneCount" in r
    assert "stats" in r


def test_phase105_rdma(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.rdma105AddHost('host-a', 100);
            window._sdacs.rdma105AddHost('host-b', 200);
            return window._sdacs.ultimate101_110Stats;
        }
    """)
    assert r["rdmaHosts"] >= 2
    assert r["rdmaGbps"] >= 300


def test_phase106_fpga(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.fpga106AddInstance();
            window._sdacs.fpga106AddInstance();
            window._sdacs.fpga106AddInstance();
            return window._sdacs.ultimate101_110Stats;
        }
    """)
    assert r["fpgaInstances"] >= 3


def test_phase107_tpu(page):
    pg, _ = page
    r = pg.evaluate("window._sdacs.tpu107Inference('claude-opus-4-7', 1024)")
    assert "model" in r
    assert r["inferences"] >= 1


def test_phase108_neuromorphic(page):
    pg, _ = page
    r = pg.evaluate("window._sdacs.neuromorphic108Spike(5000000)")
    assert r == 5_000_000


def test_phase109_dpu(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.dpu109Offload(1024);
            window._sdacs.dpu109Offload(2048);
            return window._sdacs.ultimate101_110Stats;
        }
    """)
    assert r["dpuBytes"] >= 3072


def test_phase110_mega_scale(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const s = window._sdacs.megaScale110SetCurrent(1000000000);
            return { setVal: s, capacity: window._sdacs.ultimate101_110Stats.megaCapacity };
        }
    """)
    # capacity = 1e9, so set 1B should equal capacity (clamp)
    assert r["capacity"] == 1e9
    assert r["setVal"] == 1e9


def test_no_js_errors_ultimate(page):
    pg, errors = page
    benign = ["favicon", "WebGPU", "DevTools", "ws_bridge", "WebSocket",
              "ws://localhost", "ws://127.0.0.1", "ERR_CERT", "ERR_CONNECTION",
              "fonts.googleapis", "AudioContext", "xr"]
    blocking = [e for e in errors if not any(m in e for m in benign)]
    assert not blocking, f"JS errors: {blocking}"
