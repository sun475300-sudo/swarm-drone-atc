"""HYPER Phase 20 — AI Copilot 규칙 기반 자연어 → ATC 명령 분해 검증."""
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
            pg.wait_for_function("window._sdacs.airborne >= 1", timeout=15000)
        except Exception:
            pass
        pg.wait_for_timeout(500)
        yield pg, errors
        ctx.close()
        browser.close()


def test_copilot_api_exposed(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["copilotPlan", "copilotExecute", "copilotHistory"]:
        assert k in keys, f"_sdacs.{k} missing"


def test_copilot_plan_hold_command(page):
    pg, _ = page
    r = pg.evaluate("window._sdacs.copilotPlan('7번 드론을 정지시켜')")
    assert r["steps"], "HOLD 명령 인식 실패"
    assert r["steps"][0]["cmd"] == "HOLD"
    assert r["steps"][0]["droneIdx"] == 7


def test_copilot_plan_rtb_command(page):
    pg, _ = page
    r = pg.evaluate("window._sdacs.copilotPlan('드론 3 귀환')")
    assert r["steps"]
    assert r["steps"][0]["cmd"] == "RTB"
    assert r["steps"][0]["droneIdx"] == 3


def test_copilot_plan_all_hover(page):
    pg, _ = page
    r = pg.evaluate("window._sdacs.copilotPlan('모든 드론 정지')")
    assert r["steps"]
    assert r["steps"][0]["cmd"] == "HOLD"
    assert r["steps"][0]["target"] == "all"


def test_copilot_plan_alt_up(page):
    pg, _ = page
    r = pg.evaluate("window._sdacs.copilotPlan('5번 드론 상승')")
    assert r["steps"]
    assert r["steps"][0]["cmd"] == "ALT"
    assert r["steps"][0]["params"]["delta"] == 10


def test_copilot_plan_meta_rain(page):
    pg, _ = page
    r = pg.evaluate("window._sdacs.copilotPlan('비 켜')")
    assert r["steps"]
    assert r["steps"][0]["cmd"] == "RAIN_ON"
    assert r["steps"][0]["target"] == "meta"


def test_copilot_execute_hold_changes_drone_phase(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.clearAllAtc();
            const plan = window._sdacs.copilotPlan('1번 드론을 정지시켜');
            const res = window._sdacs.copilotExecute(plan);
            const ctrl = window._sdacs.atcControlled;
            return { res, ctrl };
        }
    """)
    assert r["res"]["ok"]
    # 1번 드론(또는 인덱스)이 제어 중이어야
    assert len(r["ctrl"]) >= 1
    assert any(c["cmd"] == "HOLD" for c in r["ctrl"])


def test_copilot_execute_meta_rain_on(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const plan = window._sdacs.copilotPlan('비 켜');
            const res = window._sdacs.copilotExecute(plan);
            // window 내부 cinParticles 직접 접근 불가 → 후속 영향으로 검증
            return { res };
        }
    """)
    assert r["res"]["ok"]
    assert r["res"]["executed"] >= 1


def test_copilot_history_accumulates(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const before = window._sdacs.copilotHistory.length;
            window._sdacs.copilotExecute(window._sdacs.copilotPlan('1번 드론 정지'));
            window._sdacs.copilotExecute(window._sdacs.copilotPlan('비 꺼'));
            const after = window._sdacs.copilotHistory.length;
            return { added: after - before };
        }
    """)
    assert r["added"] == 2


def test_copilot_plan_unknown_returns_empty(page):
    pg, _ = page
    r = pg.evaluate("window._sdacs.copilotPlan('foo bar baz qux')")
    assert r["steps"] == []
    assert "실패" in r["summary"]


def test_copilot_no_js_errors(page):
    pg, errors = page
    benign = ["favicon", "WebGPU", "DevTools", "ws_bridge", "WebSocket",
              "ws://localhost", "ws://127.0.0.1", "ERR_CERT", "ERR_CONNECTION",
              "fonts.googleapis", "AudioContext"]
    blocking = [e for e in errors if not any(m in e for m in benign)]
    assert not blocking, f"JS errors: {blocking}"
