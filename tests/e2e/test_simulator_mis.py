"""Phase 5 MIS (임무 계획 UI) Playwright 스모크."""
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


def test_mis_api_exposed(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["setMissionMode", "missionMode", "addWaypoint", "waypoints",
              "clearWaypoints", "missionTemplate", "assignMission", "missions"]:
        assert k in keys, f"_sdacs.{k} missing"


def test_mis_panel_present(page):
    pg, _ = page
    r = pg.evaluate("""
        () => ({
            plan: !!document.getElementById('btn-mis-plan'),
            tpl: !!document.getElementById('btn-mis-tpl'),
            assign: !!document.getElementById('btn-mis-assign'),
            clear: !!document.getElementById('btn-mis-clear'),
            list: !!document.getElementById('mis-active-list'),
        })
    """)
    assert all(r.values()), f"MIS 패널 요소 누락: {r}"


def test_mis_planning_mode_toggle(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const on = window._sdacs.setMissionMode(true);
            const mid = window._sdacs.missionMode;
            const off = window._sdacs.setMissionMode(false);
            return { on, mid, off };
        }
    """)
    assert r["on"] is True and r["mid"] is True and r["off"] is False


def test_mis_add_waypoint(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.clearWaypoints();
            window._sdacs.addWaypoint(100, 200);
            window._sdacs.addWaypoint(-300, 400, 120);
            const wps = window._sdacs.waypoints;
            window._sdacs.clearWaypoints();
            return wps;
        }
    """)
    assert len(r) == 2
    assert r[1]["alt"] == 120


def test_mis_template_search_16(page):
    pg, _ = page
    n = pg.evaluate("""
        () => {
            const n = window._sdacs.missionTemplate('search');
            window._sdacs.clearWaypoints();
            return n;
        }
    """)
    assert n == 16, f"수색 격자는 16 WP여야 함, got {n}"


def test_mis_template_recon_8(page):
    pg, _ = page
    n = pg.evaluate("""
        () => {
            const n = window._sdacs.missionTemplate('recon');
            window._sdacs.clearWaypoints();
            return n;
        }
    """)
    assert n == 8, f"정찰 원형은 8 WP여야 함, got {n}"


def test_mis_assign_creates_mission(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.clearWaypoints();
            window._sdacs.addWaypoint(500, 500);
            window._sdacs.addWaypoint(-500, -500);
            const id = window._sdacs.selectDrone(0);
            const assigned = window._sdacs.assignMission(id);
            const ms = window._sdacs.missions;
            const remainingWp = window._sdacs.waypoints.length;
            return { assigned, count: ms.length, total: ms[0] && ms[0].total, remainingWp };
        }
    """)
    assert r["assigned"] is not None
    assert r["count"] >= 1
    assert r["total"] == 2
    # 할당 후 계획 웨이포인트는 초기화됨
    assert r["remainingWp"] == 0


def test_mis_assign_requires_waypoints(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.clearWaypoints();
            const id = window._sdacs.selectDrone(0);
            return window._sdacs.assignMission(id);
        }
    """)
    assert r is None, "웨이포인트 없이 할당되면 안 됨"


def test_no_js_errors_mis(page):
    pg, errors = page
    benign = ["favicon", "WebGPU", "DevTools", "ws_bridge", "WebSocket",
              "ws://localhost", "ws://127.0.0.1", "ERR_CERT", "ERR_CONNECTION",
              "fonts.googleapis", "AudioContext"]
    blocking = [e for e in errors if not any(m in e for m in benign)]
    assert not blocking, f"JS errors: {blocking}"
