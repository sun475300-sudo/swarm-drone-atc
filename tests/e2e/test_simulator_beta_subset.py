"""TRANSCENDENCE Phase 205 — Beta API 부분 검증 E2E.

beta 등급 API 중 핵심 그룹(Copilot · 적대 · C-UAS · WindField · PQC)을
실제 호출해 인터페이스 안정성 + 기본 응답 형태를 확인한다.
mock과 달리 beta는 "기능이 동작한다"를 보장해야 한다.
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
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    os.chdir(ROOT)
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


def test_beta_copilot_plan_returns_structured_response(page):
    r = page.evaluate("""(() => {
        const p = window._sdacs.copilotPlan('NFZ 100m 반경 주입하고 30초 후 해제');
        return { hasSteps: Array.isArray(p && p.steps), promptLen: (p && p.prompt || '').length };
    })()""")
    assert r["hasSteps"] is True
    assert r["promptLen"] > 0


def test_beta_adversarial_policies_listed_and_spawnable(page):
    r = page.evaluate("""(() => {
        const policies = window._sdacs.adversarialPolicies;
        const ok = Array.isArray(policies) && policies.length > 0;
        let spawned = null;
        if (ok) {
            spawned = window._sdacs.spawnAdversarial(policies[0]);
            window._sdacs.clearAdversarial();
        }
        return { policies, ok, spawned };
    })()""")
    assert r["ok"] is True
    assert isinstance(r["policies"], list) and len(r["policies"]) >= 1
    # spawnAdversarial returns adversarial drone id or count
    assert r["spawned"] is not None


def test_beta_cuas_lifecycle(page):
    r = page.evaluate("""(() => {
        const api = window._sdacs;
        api.enableCuas(true);
        const enabled = api.cuasEnabled;
        const modes = api.cuasModes;
        if (modes && modes.length) api.setCuasMode(modes[0]);
        const mode = api.cuasMode;
        api.enableCuas(false);
        return { enabled, modes, mode, disabled: api.cuasEnabled === false };
    })()""")
    assert r["enabled"] is True
    assert isinstance(r["modes"], list) and len(r["modes"]) >= 1
    assert r["mode"] in r["modes"]
    assert r["disabled"] is True


def test_beta_wind_field_toggle(page):
    r = page.evaluate("""(() => {
        const api = window._sdacs;
        const on = api.enableWindField(true);
        const off = api.enableWindField(false);
        return { on, off };
    })()""")
    assert r["on"] is True
    assert r["off"] is False


def test_beta_apis_all_classified_beta(page):
    """검증 대상 5종이 실제 beta 분류인지 확인 (회귀 방지)."""
    r = page.evaluate("""(() => ({
        copilot: window._sdacs.apiMaturity('copilotPlan'),
        adv: window._sdacs.apiMaturity('spawnAdversarial'),
        cuas: window._sdacs.apiMaturity('enableCuas'),
        wind: window._sdacs.apiMaturity('enableWindField'),
        pqc: window._sdacs.apiMaturity('enablePqc'),
    }))()""")
    for name, level in r.items():
        assert level == "beta", f"{name} 분류가 beta 아님: {level}"
