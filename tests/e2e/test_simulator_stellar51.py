"""STELLAR Phase 51 — LLM Multi-Agent 규칙 기반 위임 E2E.

실 LLM API 키 없이 동작하는 결정적 스탠드인(_stellar51Recommend)을 검증한다.
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
        pg.evaluate("window._sdacs.startSim()")
        try:
            pg.wait_for_function("window._sdacs.airborne >= 2", timeout=15000)
        except Exception:
            pass
        pg.wait_for_timeout(700)
        yield pg, errors
        ctx.close()
        browser.close()


def test_delegate_group_creates_record(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const g = window._sdacs.stellar51DelegateGroup(['DR-001', 'DR-002'], 'gpt-4o');
            return {
                id: g.id,
                provider: g.llmProvider,
                droneCount: g.droneIds.length,
                groups: window._sdacs.stellar51Groups.length,
            };
        }
    """)
    assert r["id"].startswith("GRP-")
    assert r["provider"] == "gpt-4o"
    assert r["droneCount"] == 2
    assert r["groups"] >= 1


def test_default_provider_is_claude(page):
    pg, _ = page
    provider = pg.evaluate(
        "window._sdacs.stellar51DelegateGroup(['DR-003']).llmProvider")
    assert provider == "claude-opus-4-7"


def test_tick_produces_decisions(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const g = window._sdacs.stellar51DelegateGroup(['DR-001', 'DR-002']);
            const before = g.decisions;
            const produced = window._sdacs.stellar51Tick();
            const after = window._sdacs.stellar51Groups.find(x => x.id === g.id);
            return {
                produced,
                beforeDecisions: before,
                afterDecisions: after.decisions,
                lastDecisionCount: after.lastDecisions.length,
                firstAction: after.lastDecisions[0] ? after.lastDecisions[0].action : null,
            };
        }
    """)
    assert r["produced"] >= 2
    assert r["afterDecisions"] >= r["beforeDecisions"] + 2
    assert r["lastDecisionCount"] == 2
    assert r["firstAction"] in {
        "STANDBY", "RTB", "ISOLATE", "REROUTE", "RESUME", "MAINTAIN", "NOOP"}


def test_recommend_unknown_drone_is_noop(page):
    pg, _ = page
    action = pg.evaluate(
        "window._stellar51Recommend('DR-NOPE').action")
    assert action == "NOOP"


def test_revoke_removes_group(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const g = window._sdacs.stellar51DelegateGroup(['DR-001']);
            const removed = window._sdacs.stellar51Revoke(g.id);
            const stillThere = window._sdacs.stellar51Groups.some(x => x.id === g.id);
            const revokeMissing = window._sdacs.stellar51Revoke('GRP-DOES-NOT-EXIST');
            return { removed, stillThere, revokeMissing };
        }
    """)
    assert r["removed"] is True
    assert r["stillThere"] is False
    assert r["revokeMissing"] is False


def test_no_page_errors(page):
    _, errors = page
    assert errors == []
