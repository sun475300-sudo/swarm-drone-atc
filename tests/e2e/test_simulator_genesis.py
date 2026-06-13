"""GENESIS Phase 302 — SORA 자동 계산기 E2E.

JARUS SORA 2.0 결정적 구현(`_sdacs.soraAssess()`)을 검증한다.
iGRC 표 + 완화(M1/M3) + ARC + SAIL 결정 표의 일관성을 확인.
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
        yield pg
        ctx.close()
        browser.close()


def test_sora_assess_default_is_sparse_bvlos(page):
    r = page.evaluate("window._sdacs.soraAssess()")
    # 기본: 인구 희박 + BVLOS → iGRC 3, M1+M3 완화로 final GRC 1
    assert r["density"] == "sparse"
    assert r["bvlos"] is True
    assert r["iGrc"] == 3
    assert r["finalGrc"] == 1
    assert r["arc"] == "ARC-b"
    assert r["sail"] == "SAIL II"
    assert len(r["mitigations"]) == 2


def test_sora_assess_populated_bvlos(page):
    r = page.evaluate("window._sdacs.soraAssess({ populationDensity: 'populated' })")
    # 인구 밀집 BVLOS: iGRC 4 → 완화 2 → GRC 2, ARC-c → 전술 완화로 ARC-b → SAIL II
    assert r["iGrc"] == 4
    assert r["finalGrc"] == 2
    assert r["arc"] == "ARC-b"
    assert r["sail"] == "SAIL II"


def test_sora_assess_assembly_is_high_risk(page):
    r = page.evaluate("window._sdacs.soraAssess({ populationDensity: 'assembly' })")
    # 군중 위 BVLOS: iGRC 8 → 완화 후 GRC 6 → SAIL V (고위험 정직 반영)
    assert r["iGrc"] == 8
    assert r["finalGrc"] == 6
    assert r["sail"] == "SAIL V"


def test_sora_assess_vlos_lowers_grc(page):
    bvlos = page.evaluate("window._sdacs.soraAssess({ populationDensity: 'sparse' })")
    vlos = page.evaluate(
        "window._sdacs.soraAssess({ populationDensity: 'sparse', bvlos: false })")
    assert vlos["iGrc"] < bvlos["iGrc"]


def test_sora_assess_nfz_mitigation_tracks_layer_toggle(page):
    on = page.evaluate("""(() => {
        window._sdacs.setLayer('nfz', true);
        return window._sdacs.soraAssess();
    })()""")
    off = page.evaluate("""(() => {
        window._sdacs.setLayer('nfz', false);
        const r = window._sdacs.soraAssess();
        window._sdacs.setLayer('nfz', true);
        return r;
    })()""")
    # NFZ 토글 off → M1 완화 미적용 → GRC 1 높음
    assert off["finalGrc"] == on["finalGrc"] + 1
    assert any("M1" in m for m in on["mitigations"])
    assert not any("M1" in m for m in off["mitigations"])


def test_sora_assess_is_production_maturity(page):
    assert page.evaluate("window._sdacs.apiMaturity('soraAssess')") == "production"
