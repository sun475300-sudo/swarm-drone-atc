"""POST-UNIVERSE Phase 151-200 E2E."""
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


def test_cosmic_151_160(page):
    pg, _ = page
    r = pg.evaluate("""({
        gal: window._sdacs.p151Galactic(5),
        dm: window._sdacs.p152DarkMatter(),
        pulsar: window._sdacs.p153Pulsar('PSR-J0437'),
        worm: window._sdacs.p154Wormhole('A', 'B'),
        gw: window._sdacs.p155GravWave(),
        am: window._sdacs.p156Antimatter(0.005),
        bh: window._sdacs.p157BlackHole(1e30),
        cr: window._sdacs.p158CosmicRayShield(100),
        is_: window._sdacs.p159Interstellar(50),
        cov: window._sdacs.p160GalacticCoverage(1e13),
    })""")
    assert r["gal"] == 5
    assert r["pulsar"] >= 1
    assert r["cov"] == 1e13


def test_time_reality_161_170(page):
    pg, _ = page
    r = pg.evaluate("""({
        rc: window._sdacs.p161Retrocausal(),
        cl: window._sdacs.p162CausalityLoop(),
        ta: window._sdacs.p163Tachyon(),
        bu: window._sdacs.p164BlockUniverse(),
        se: window._sdacs.p165SpacetimeEdit(),
        cc: window._sdacs.p166CollapseCtrl(),
        qe: window._sdacs.p167QuantumEraser(),
        dc: window._sdacs.p168Decoherence(),
        tb: window._sdacs.p169TimelineBranch('alt-2026'),
        re: window._sdacs.p170RealityEdit(),
    })""")
    assert r["rc"] == 1
    assert r["tb"] >= 2


def test_consciousness_171_180(page):
    pg, _ = page
    r = pg.evaluate("""({
        dh: window._sdacs.p171DigitalHuman('Alice'),
        mu: window._sdacs.p172MindUpload(),
        me: window._sdacs.p173MemoryEncode(10),
        ds: window._sdacs.p174DreamShare(),
        tp: window._sdacs.p175Telepathy('A', 'B'),
        em: window._sdacs.p176Empathy(0.9),
        fw: window._sdacs.p177FreeWillSample(),
        pt: window._sdacs.p178PersonalityTransfer(),
        sc: window._sdacs.p179SoulContinuity(),
        cd: window._sdacs.p180ConsciousDrone(),
    })""")
    assert r["dh"] == 1
    assert r["em"] == 0.9


def test_final_hurdles_181_190(page):
    pg, _ = page
    r = pg.evaluate("""({
        hd: window._sdacs.p181HeatDeath(),
        er: window._sdacs.p182EntropyReverse(5),
        ip: window._sdacs.p183InfoPreserve(),
        bp: window._sdacs.p184BoltzmannPrevent(),
        sh: window._sdacs.p185SimHypothesis(),
        vs: window._sdacs.p186VacuumShield(),
        st: window._sdacs.p187StrangeletContain(3),
        gg: window._sdacs.p188GreyGooMitigate(),
        pc: window._sdacs.p189PaperclipPrevent(),
        ex: window._sdacs.p190ExistRisk('minimal'),
    })""")
    assert r["hd"] is True
    assert r["er"] == 5
    assert r["ex"] == "minimal"


def test_transcendence_191_200(page):
    pg, _ = page
    r = pg.evaluate("""({
        m: window._sdacs.p191BeyondMath(),
        l: window._sdacs.p192BeyondLogic(),
        p: window._sdacs.p193BeyondPhysics(),
        c: window._sdacs.p194BeyondComputation(),
        t: window._sdacs.p195BeyondTime(),
        sp: window._sdacs.p196BeyondSpace(),
        e: window._sdacs.p197BeyondExistence(),
        pi: window._sdacs.p198PureInformation(),
        ui: window._sdacs.p199UniversalIdentity(),
        unity: window._sdacs.p200UnityAchieved(),
    })""")
    assert r["unity"]["achieved"] is True
    assert r["unity"]["phase"] == 200
    assert "Unity" in r["unity"]["message"]


def test_post_universe_stats(page):
    pg, _ = page
    pg.evaluate("""() => {
        window._sdacs.p151Galactic(3);
        window._sdacs.p171DigitalHuman('Bob');
        window._sdacs.p200UnityAchieved();
    }""")
    r = pg.evaluate("window._sdacs.postUniverseStats")
    assert r["transcendence"]["unity"] is True


def test_no_js_errors_post_universe(page):
    pg, errors = page
    benign = ["favicon", "WebGPU", "DevTools", "ws_bridge", "WebSocket",
              "ws://localhost", "ws://127.0.0.1", "ERR_CERT", "ERR_CONNECTION",
              "fonts.googleapis", "AudioContext", "xr"]
    blocking = [e for e in errors if not any(m in e for m in benign)]
    assert not blocking, f"JS errors: {blocking}"
