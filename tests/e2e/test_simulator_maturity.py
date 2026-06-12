"""TRANSCENDENCE Phase 201-207 — API Maturity Honesty E2E.

391개 _sdacs API의 성숙도 분류(production/beta/mock/speculative)를 검증한다.
프로젝트 정직성: mock/speculative API를 명시적으로 라벨링.
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
        pg.wait_for_timeout(500)
        yield pg, errors
        ctx.close()
        browser.close()


def test_maturity_api_exposed(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    assert "apiMaturity" in keys
    assert "maturityReport" in keys


def test_maturity_production_classification(page):
    pg, _ = page
    r = pg.evaluate("""({
        atc: window._sdacs.apiMaturity('atcCommand'),
        mission: window._sdacs.apiMaturity('missionAdd'),
        inj: window._sdacs.apiMaturity('injectFault'),
        core: window._sdacs.apiMaturity('startSim'),
    })""")
    assert r["atc"] == "production"
    assert r["mission"] == "production"
    assert r["inj"] == "production"
    assert r["core"] == "production"


def test_maturity_beta_classification(page):
    pg, _ = page
    r = pg.evaluate("""({
        copilot: window._sdacs.apiMaturity('copilotPlan'),
        cuas: window._sdacs.apiMaturity('enableCuas'),
        wind: window._sdacs.apiMaturity('enableWindField'),
        pqc: window._sdacs.apiMaturity('enablePqc'),
    })""")
    assert r["copilot"] == "beta"
    assert r["cuas"] == "beta"
    assert r["wind"] == "beta"
    assert r["pqc"] == "beta"


def test_maturity_mock_classification(page):
    pg, _ = page
    r = pg.evaluate("""({
        rlhf: window._sdacs.apiMaturity('rlhfFeedback'),
        gpu: window._sdacs.apiMaturity('gpu100kInit'),
        cesium: window._sdacs.apiMaturity('cesiumGlobalInit'),
        qkd: window._sdacs.apiMaturity('qkdExchangeKey'),
        sat: window._sdacs.apiMaturity('satelliteInit'),
    })""")
    assert r["rlhf"] == "mock"
    assert r["gpu"] == "mock"
    assert r["cesium"] == "mock"
    assert r["qkd"] == "mock"
    assert r["sat"] == "mock"


def test_maturity_speculative_classification(page):
    pg, _ = page
    r = pg.evaluate("""({
        petaflop: window._sdacs.apiMaturity('petaflop101Activate'),
        universe: window._sdacs.apiMaturity('universeOS150Deploy'),
        unity: window._sdacs.apiMaturity('p200UnityAchieved'),
        galactic: window._sdacs.apiMaturity('p151Galactic'),
        nano: window._sdacs.apiMaturity('nano111Spawn'),
    })""")
    assert r["petaflop"] == "speculative"
    assert r["universe"] == "speculative"
    assert r["unity"] == "speculative"
    assert r["galactic"] == "speculative"
    assert r["nano"] == "speculative"


def test_maturity_report_distribution(page):
    pg, _ = page
    r = pg.evaluate("window._sdacs.maturityReport()")
    # 총 API 수가 합리적 범위
    assert r["total"] >= 380
    c = r["counts"]
    # 4개 카테고리 모두 존재
    assert c["production"] > 0
    assert c["beta"] > 0
    assert c["mock"] > 0
    assert c["speculative"] > 0
    # 합 = total
    assert c["production"] + c["beta"] + c["mock"] + c["speculative"] == r["total"]
    # production 코어가 충분히 많아야 함 (핵심 기능 신뢰성)
    assert c["production"] >= 50


def test_maturity_no_js_errors(page):
    pg, errors = page
    benign = ["favicon", "WebGPU", "DevTools", "ws_bridge", "WebSocket",
              "ws://localhost", "ws://127.0.0.1", "ERR_CERT", "ERR_CONNECTION",
              "fonts.googleapis", "AudioContext", "xr"]
    blocking = [e for e in errors if not any(m in e for m in benign)]
    assert not blocking, f"JS errors: {blocking}"
