"""GENESIS Phase 303 — 비행계획 신고 양식 자동 생성(Drone One-Stop) E2E.

`_sdacs.flightPlanExport()` 가 현재 시뮬 상태 + SORA(302) 평가를 결합해
항공안전법 시행규칙 별지 제122호서식(비행승인신청서)에 대응하는
결정적 양식을 추출하는지 검증한다.
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


def test_flight_plan_export_default_structure(page):
    r = page.evaluate("window._sdacs.flightPlanExport()")
    # 한국 공식 서식·포털 매핑
    assert "제122호서식" in r["form"]
    assert "Drone One-Stop" in r["portal"]
    # 항공기 항목은 현재 군집 규모와 일치
    assert r["aircraft"]["count"] == page.evaluate("window._sdacs.droneCount")
    assert r["aircraft"]["weightClass"].startswith("최대이륙중량 25kg")
    # 기본 = 군집 자동 관제 → BVLOS
    assert r["flightMethod"].startswith("BVLOS")
    # 고도는 시뮬 천장(180m AGL) 이내
    assert 0 <= r["altitude"]["maxAGLm"] <= r["altitude"]["ceilingM"] == 180


def test_flight_plan_export_purpose_tracks_scenario(page):
    r = page.evaluate("window._sdacs.flightPlanExport()")
    # 비행목적은 현재 시나리오 라벨 기반 (기본 시나리오 = '기본')
    assert "군집 비행 실증" in r["aircraft"]["purpose"]


def test_flight_plan_export_links_sora_safety(page):
    r = page.evaluate("window._sdacs.flightPlanExport()")
    # SORA(302) 연동 → SAIL 등급 + 5계층 안전망 명시
    assert r["safety"]["sail"].startswith("SAIL")
    assert "5계층 안전망" in r["safety"]["safetyNet"]


def test_flight_plan_export_vlos_option(page):
    r = page.evaluate("window._sdacs.flightPlanExport({ bvlos: false })")
    assert r["flightMethod"].startswith("VLOS")


def test_flight_plan_export_assembly_requires_approval(page):
    r = page.evaluate("window._sdacs.flightPlanExport({ populationDensity: 'assembly' })")
    # 군중 위 비행 → 고위험 SAIL + 인구밀집 사유로 승인 필요
    assert r["safety"]["sail"] == "SAIL V"
    assert r["approvalRequired"] is True
    assert any("인구밀집" in x for x in r["approvalReasons"])


def test_flight_plan_export_nfz_drives_approval(page):
    on = page.evaluate("""(() => {
        window._sdacs.setLayer('nfz', true);
        return window._sdacs.flightPlanExport({ populationDensity: 'sparse' });
    })()""")
    off = page.evaluate("""(() => {
        window._sdacs.setLayer('nfz', false);
        const r = window._sdacs.flightPlanExport({ populationDensity: 'sparse' });
        window._sdacs.setLayer('nfz', true);
        return r;
    })()""")
    assert any("NFZ" in x for x in on["approvalReasons"])
    assert all("NFZ" not in x for x in off["approvalReasons"])


def test_flight_plan_export_applicant_override(page):
    r = page.evaluate(
        "window._sdacs.flightPlanExport({ applicantName: '홍길동', contact: '010-1234-5678' })")
    assert r["applicant"]["name"] == "홍길동"
    assert r["applicant"]["contact"] == "010-1234-5678"


def test_flight_plan_export_is_production_maturity(page):
    assert page.evaluate("window._sdacs.apiMaturity('flightPlanExport')") == "production"
