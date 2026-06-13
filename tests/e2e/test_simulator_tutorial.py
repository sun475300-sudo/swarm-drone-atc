"""GENESIS Phase 381 — 시뮬레이터 교육 튜토리얼 E2E.

5단계(ATC·TAC·UTM·APF·Maturity) 결정적 진행 검증.
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


@pytest.fixture(scope="module")
def http_server():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **kw):
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", 0), Quiet)
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
        pg.goto(f"{http_server}/swarm_3d_simulator.html",
                wait_until="networkidle", timeout=20000)
        pg.wait_for_function("window._sdacs && window._sdacs.droneCount > 0", timeout=15000)
        yield pg
        ctx.close()
        browser.close()


def test_tutorial_api_exposed_and_production(page):
    keys = page.evaluate("Object.keys(window._sdacs)")
    for k in ("tutorialStart", "tutorialNext", "tutorialStatus"):
        assert k in keys
    levels = page.evaluate("""({
        s: window._sdacs.apiMaturity('tutorialStart'),
        n: window._sdacs.apiMaturity('tutorialNext'),
        q: window._sdacs.apiMaturity('tutorialStatus'),
    })""")
    assert all(v == "production" for v in levels.values())


def test_tutorial_complete_five_steps(page):
    r = page.evaluate("""(() => {
        const api = window._sdacs;
        api.startSim();
        const start = api.tutorialStart();
        const log = [];
        let cur = start;
        for (let i = 0; i < start.totalSteps + 1; i++) {
            const n = api.tutorialNext();
            log.push(n);
            if (n && n.done) break;
        }
        return { start, final: log[log.length - 1], status: api.tutorialStatus() };
    })()""")
    assert r["start"]["totalSteps"] == 5
    assert r["final"]["done"] is True
    assert len(r["final"]["log"]) == 5
    # 모든 단계가 성공 종료 (verify 함수 결과)
    assert all(s["ok"] for s in r["final"]["log"]), r["final"]["log"]
    assert r["status"]["active"] is False
    assert r["status"]["step"] == 5
