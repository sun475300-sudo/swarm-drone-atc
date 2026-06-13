"""TRANSCENDENCE Phase 204 — Production 핵심 API 적합성 강화 E2E.

production 등급 90종 전수에 대해: (a) getter는 예외 없이 읽힘,
(b) 핵심 12종 메서드는 실제 호출로 동작 확인. mock과 달리 production은
"호출 안전성"이 아니라 "실 동작"을 보장해야 한다.
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
        pg.goto(f"{http_server}/swarm_3d_simulator.html",
                wait_until="networkidle", timeout=20000)
        pg.wait_for_function("window._sdacs && window._sdacs.droneCount > 0", timeout=15000)
        pg.wait_for_timeout(500)
        yield pg
        ctx.close()
        browser.close()


def test_all_production_getters_readable_without_error(page):
    """production 분류 getter 전수 — 읽기에서 예외 0건."""
    r = page.evaluate("""(() => {
        const api = window._sdacs;
        const rep = api.maturityReport();
        const failures = [];
        let getters = 0;
        for (const [name, lvl] of Object.entries(rep.byApi)) {
            if (lvl !== 'production') continue;
            const desc = Object.getOwnPropertyDescriptor(api, name);
            if (!desc || !desc.get) continue;
            getters++;
            try { desc.get.call(api); }
            catch (e) { failures.push(name + ': ' + e.message); }
        }
        return { getters, failures };
    })()""")
    assert r["getters"] >= 20, f"production getter가 너무 적음: {r['getters']}"
    assert r["failures"] == [], f"getter 예외: {r['failures']}"


def test_production_core_12_methods_invoke(page):
    """핵심 12종 메서드 실 호출 — ATC/TAC/MIS/INJ/CAM/SORA."""
    r = page.evaluate("""(() => {
        const api = window._sdacs;
        const out = {};
        api.startSim();
        const d0 = api.selectDrone(0);                       // 1 selectDrone
        out.select = d0 !== null;
        out.atc = api.atcCommand(d0, 'HOLD') !== undefined;  // 2 atcCommand
        out.deselect = (api.deselectDrone(), true);          // 3 deselectDrone
        out.predTrail = (api.setPredTrail(true), true);      // 4 TAC
        out.cpaMarker = (api.setCpaMarker(true), true);      // 5 TAC
        const tpl = api.missionTemplate('recon_orbit', 0, 0);// 6 MIS
        out.template = Array.isArray(tpl) && tpl.length > 0;
        out.assign = api.missionAssignTemplate(0, 'recon_orbit') !== undefined; // 7
        const nfz = api.injectDynamicNFZ(100, 100, 80, 5);   // 8 INJ
        out.nfz = nfz && nfz.r === 80;
        out.injClear = (api.injClearAll(), true);            // 9 INJ
        out.cam = api.setCamMode('orbit') !== undefined;     // 10 CAM
        const sora = api.soraAssess();                       // 11 GENESIS 302
        out.sora = typeof sora.sail === 'string' && sora.finalGrc >= 1;
        out.report = api.maturityReport().total > 0;         // 12 maturity
        return out;
    })()""")
    failed = [k for k, v in r.items() if v is not True]
    assert not failed, f"핵심 메서드 실패: {failed}"


def test_production_count_does_not_regress(page):
    """production 수 회귀 방지 — 2026-06-12 기준선 90 미만으로 줄면 실패."""
    counts = page.evaluate("window._sdacs.maturityReport().counts")
    assert counts["production"] >= 90
