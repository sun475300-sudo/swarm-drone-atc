"""ULTIMATE Phase 111-150 — Materials/Bio/Standards/Eternal E2E."""
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


# Materials & Nano (111-120)
def test_phase111_120_materials(page):
    pg, _ = page
    r = pg.evaluate("""({
        nano: window._sdacs.nano111Spawn(500),
        dust: window._sdacs.smartDust112Deploy(20000),
        graphene: window._sdacs.graphene113Boost(15),
        heal: window._sdacs.selfHeal114Cycle(),
        bio: window._sdacs.bioDeg115SetLife(48),
        atmo: window._sdacs.atmo116Harvest(5000),
        piezo: window._sdacs.piezo117Generate(2),
        solar: window._sdacs.solar118SetEff(0.95),
        meta: window._sdacs.meta119Activate(true),
        prog: window._sdacs.progMatter120Reshape('helix'),
    })""")
    assert r["nano"] == 500
    assert r["graphene"] == 15
    assert r["solar"] == 0.95
    assert r["meta"] is True
    assert r["prog"] == "helix"


# Bio-Hybrid (121-130)
def test_phase121_130_bio(page):
    pg, _ = page
    r = pg.evaluate("""({
        neuron: window._sdacs.neuron121Connect(5000),
        dna: window._sdacs.dna122Store(50),
        bact: window._sdacs.bacteria123Spawn(2000),
        algae: window._sdacs.algae124Power(10),
        myco: window._sdacs.mycelium125Repair(),
        bird: window._sdacs.bird126Partner('falcon'),
        insect: window._sdacs.insect127Join(50000),
        symb: window._sdacs.symbiotic128Bond('DR-001', 'dolphin'),
        fluor: window._sdacs.biofluor129Emit('cyan'),
        living: window._sdacs.living130Spawn('synthetic-v2'),
    })""")
    assert r["neuron"] == 5000
    assert r["bird"]["species"] == "falcon"
    assert r["living"] == 1


# Universal Standard (131-140)
def test_phase131_140_standards(page):
    pg, _ = page
    r = pg.evaluate("""({
        rfc: window._sdacs.rfc131Submit('SDACS Protocol v2.0'),
        icao: window._sdacs.icao132Adopt(),
        iso: window._sdacs.iso133Cert('ISO-21384-3-2025'),
        ieee: window._sdacs.ieee134Standard('802.UAS-2026'),
        itu: window._sdacs.itu135AllocateFreq(500),
        un: window._sdacs.un136Resolution(),
        easa: window._sdacs.easa137Integrate(),
        faa: window._sdacs.faa138Part108(),
        caac: window._sdacs.caac139Compat(),
        adoption: window._sdacs.global140Adopt(75),
    })""")
    assert r["rfc"]["title"] == "SDACS Protocol v2.0"
    assert r["icao"] is True
    assert r["adoption"] == 75


# SDACS Eternal (141-150)
def test_phase141_150_eternal(page):
    pg, _ = page
    r = pg.evaluate("""({
        aware: window._sdacs.selfAware141Activate(),
        recur: window._sdacs.recursion142Sim(),
        consc: window._sdacs.consciousness143Experiment(),
        blur: window._sdacs.realityBlur144Set(0.7),
        trans: window._sdacs.translator145Add(),
        eter: window._sdacs.eternalMission146Start(),
        loop: window._sdacs.timeLoop147Iterate(),
        para: window._sdacs.parallel148Universe(),
        toe: window._sdacs.toe149Unify(),
        univ: window._sdacs.universeOS150Deploy(),
    })""")
    assert r["aware"] is True
    assert r["blur"] == 0.7
    assert r["toe"] is True
    assert r["univ"]["deployed"] is True
    assert "Universe-OS-1.0" in r["univ"]["version"]


def test_ultimate_stats(page):
    pg, _ = page
    pg.evaluate("""() => {
        window._sdacs.icao132Adopt();
        window._sdacs.faa138Part108();
        window._sdacs.universeOS150Deploy();
    }""")
    r = pg.evaluate("window._sdacs.ultimate111_150Stats")
    assert r["standards"]["icao"] is True
    assert r["standards"]["faa"] is True
    assert r["eternal"]["universeOS"] is True


def test_no_js_errors_ultimate111_150(page):
    pg, errors = page
    benign = ["favicon", "WebGPU", "DevTools", "ws_bridge", "WebSocket",
              "ws://localhost", "ws://127.0.0.1", "ERR_CERT", "ERR_CONNECTION",
              "fonts.googleapis", "AudioContext", "xr"]
    blocking = [e for e in errors if not any(m in e for m in benign)]
    assert not blocking, f"JS errors: {blocking}"
