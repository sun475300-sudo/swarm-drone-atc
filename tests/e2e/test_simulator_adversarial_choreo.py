"""HYPER Phase 21 (적대 드론 정책) + Phase 28 (Swarm Choreography) E2E."""
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
            pg.wait_for_function("window._sdacs.airborne >= 3", timeout=20000)
        except Exception:
            pass
        pg.wait_for_timeout(800)
        yield pg, errors
        ctx.close()
        browser.close()


# ===== Phase 21 — Adversarial =====

def test_adversarial_api_exposed(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["spawnAdversarial", "clearAdversarial", "adversarialPolicy",
              "adversarialDrones", "adversarialSafetyResponse", "adversarialPolicies"]:
        assert k in keys, f"_sdacs.{k} missing"


def test_adversarial_policies_list(page):
    pg, _ = page
    r = pg.evaluate("window._sdacs.adversarialPolicies")
    assert set(r) == {"decoy", "swarm_intrusion", "jamming", "direct_intercept"}


def test_adversarial_decoy_spawns(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.clearAdversarial();
            const before = window._sdacs.droneCount;
            const ids = window._sdacs.spawnAdversarial('decoy');
            return {
                ok: !!ids,
                added: window._sdacs.droneCount - before,
                policy: window._sdacs.adversarialPolicy,
                idCount: ids?.length || 0,
            };
        }
    """)
    assert r["ok"]
    assert r["added"] == 1
    assert r["policy"] == "decoy"
    assert r["idCount"] == 1


def test_adversarial_swarm_intrusion_spawns_3(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.clearAdversarial();
            const before = window._sdacs.droneCount;
            window._sdacs.spawnAdversarial('swarm_intrusion');
            return {
                added: window._sdacs.droneCount - before,
                ids: window._sdacs.adversarialDrones.length,
            };
        }
    """)
    assert r["added"] == 3
    assert r["ids"] == 3


def test_adversarial_clear_removes_policy(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.spawnAdversarial('jamming');
            const mid = window._sdacs.adversarialPolicy;
            window._sdacs.clearAdversarial();
            return { mid, after: window._sdacs.adversarialPolicy };
        }
    """)
    assert r["mid"] == "jamming"
    assert r["after"] is None


def test_adversarial_unknown_policy(page):
    pg, _ = page
    r = pg.evaluate("window._sdacs.spawnAdversarial('does_not_exist')")
    assert r is None


# ===== Phase 28 — Choreography =====

def test_choreography_api_exposed(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["startChoreography", "clearChoreography", "choreoPattern", "choreoPatterns"]:
        assert k in keys, f"_sdacs.{k} missing"


def test_choreography_patterns_list(page):
    pg, _ = page
    r = pg.evaluate("window._sdacs.choreoPatterns")
    assert set(r) == {"circle", "v_formation", "grid", "heart", "sdacs_logo"}


def test_choreography_circle_starts(page):
    pg, _ = page
    pg.evaluate("window._sdacs.clearAdversarial()")
    r = pg.evaluate("""
        () => {
            const ok = window._sdacs.startChoreography('circle');
            return { ok, pattern: window._sdacs.choreoPattern };
        }
    """)
    assert r["ok"] is True
    assert r["pattern"] == "circle"


def test_choreography_heart_starts(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const ok = window._sdacs.startChoreography('heart');
            return { ok, pattern: window._sdacs.choreoPattern };
        }
    """)
    assert r["ok"] is True
    assert r["pattern"] == "heart"


def test_choreography_clear(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.startChoreography('grid');
            const mid = window._sdacs.choreoPattern;
            window._sdacs.clearChoreography();
            return { mid, after: window._sdacs.choreoPattern };
        }
    """)
    assert r["mid"] == "grid"
    assert r["after"] is None


def test_choreography_unknown_pattern(page):
    pg, _ = page
    r = pg.evaluate("window._sdacs.startChoreography('not_real')")
    assert r is False


def test_phase21_28_no_js_errors(page):
    pg, errors = page
    benign = ["favicon", "WebGPU", "DevTools", "ws_bridge", "WebSocket",
              "ws://localhost", "ws://127.0.0.1", "ERR_CERT", "ERR_CONNECTION",
              "fonts.googleapis", "AudioContext", "xr"]
    blocking = [e for e in errors if not any(m in e for m in benign)]
    assert not blocking, f"JS errors: {blocking}"
