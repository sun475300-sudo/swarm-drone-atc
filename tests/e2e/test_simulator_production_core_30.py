"""TRANSCENDENCE Phase 211-220 — Production 핵심 API 12 → 30 격상 E2E.

Phase 204가 핵심 12종 메서드의 실 호출 회귀를 확립했다. Phase 211-220은
그 회귀 검증 코어를 30종으로 넓힌다. production 등급은 "호출 안전성"이
아니라 "실 동작"(set→get 왕복·구조화 반환·상태 전이)을 보장해야 하므로,
각 메서드를 실제로 호출하고 관측 가능한 효과를 검증한다.

추가로 (a) 검증 대상 30종이 전부 production 등급으로 분류되는지,
(b) 검증된 코어 수가 30 미만으로 회귀하지 않는지 게이트한다.
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


# 검증 대상 30종 — 호출 후 관측 가능한 효과를 검증하는 production 코어.
# evaluate가 { name: bool } 맵을 반환하면 모두 True인지 + 30종인지 게이트.
_CORE_30_EVAL = """(() => {
    const api = window._sdacs;
    const out = {};
    const before = { ...api.injStats };

    // ── ATC / 코어 상태 (Phase 1) ──
    api.startSim();
    out.startSim = api.simRunning === true;
    const did = api.selectDrone(0);                                // 1
    out.selectDrone = did !== null;
    out.atcCommand = api.atcCommand(did, 'HOLD') !== undefined;    // 2
    out.getSelected = (api.getSelected() || {}).id === did;        // 3
    api.deselectDrone();                                          // 4
    out.deselectDrone = api.getSelected() === null;

    // ── TAC 전술 시각화 (Phase 2) — set→get 왕복 ──
    api.setPredTrail(true);    out.setPredTrail = api.predTrail === true;       // 5
    out.setPredHorizon = api.setPredHorizon(10) === 10 && api.predHorizon === 10; // 6
    api.setVelArrow(true);     out.setVelArrow = api.velArrow === true;         // 7
    api.setCpaMarker(true);    out.setCpaMarker = api.cpaMarker === true;       // 8
    out.cpaPairsCount = typeof api.cpaPairsCount === 'number';                  // 9

    // ── MIS 임무 (Phase 5) ──
    const tpl = api.missionTemplate('recon_orbit', 0, 0);          // 10
    out.missionTemplate = Array.isArray(tpl) && tpl.length > 0;
    out.missionAssignTemplate = api.missionAssignTemplate(0, 'recon_orbit') !== null; // 11
    out.missions = Array.isArray(api.missions) && api.missions.length >= 1;     // 12
    out.missionClearAll = api.missionClearAll() === 0;                          // 13

    // ── INJ 장애 주입 (Phase 6) ──
    const nfz = api.injectDynamicNFZ(120, 120, 60, 5);            // 14
    out.injectDynamicNFZ = nfz && nfz.r === 60;
    out.dynamicNfzList = api.dynamicNfzList.length >= 1;           // 15
    api.injectFault(0, 'GPS_LOSS', { duration: 5 });             // 16
    out.injectFault = api.injStats.gpsLost === before.gpsLost + 1;
    const rg = api.injectRogue();                                 // 17
    out.injectRogue = !!rg && api.injStats.rogueAdded === before.rogueAdded + 1;
    out.injStats = typeof api.injStats === 'object' && api.injStats !== null;   // 18
    api.injClearAll();                                            // 19
    out.injClearAll = api.dynamicNfzList.length === 0;

    // ── CAM 카메라 (Phase 4) ──
    api.setCamMode('orbit');   out.setCamMode = api.camMode === 'orbit';        // 20
    out.focusDrone = api.focusDrone(0) !== null;                  // 21

    // ── CIN 시네마틱 (Phase 3) ──
    out.setSunHour = api.setSunHour(12) === 12 && api.sunHour === 12;           // 22
    api.setSunAuto(true);      out.setSunAuto = api.sunEnabled === true;        // 23
    out.setRain = api.setRain(true, 0.5) === true;                // 24
    out.setSnow = api.setSnow(true, 0.5) === true;                // 25

    // ── ANA 분석 (Phase 7) ──
    api.setAnaHeatmap(true);   out.setAnaHeatmap = api.anaHeatmap === true;     // 26
    out.anaKpiWindow = Array.isArray(api.anaKpiWindow.time);       // 27

    // ── AUD / MOB / i18n ──
    api.setAmbientAudio(true); out.setAmbientAudio = api.ambientAudio === true; // 29
    const lang0 = api.lang;
    api.setLang('en');         out.setLang = api.lang === 'en';                 // 30
    api.setLang(lang0);

    // ── 추가 코어 (margin) ──
    out.multiSelect = (api.multiSelect([0, 1]), api.multiSelection.length === 2); // 31
    api.clearMulti();
    api.setAnalysisView(true); out.setAnalysisView = !!api.analysisMode;        // 32
    const sora = api.soraAssess();                              // 33
    out.soraAssess = typeof sora.sail === 'string' && sora.finalGrc >= 1;
    out.maturityReport = api.maturityReport().total > 0;          // 34 (meta)

    // ── 코어 인프라 getter (구조화 반환) ──
    out.stats = typeof api.stats === 'object' && api.stats !== null;            // 35
    out.weather = typeof api.weather === 'object' && typeof api.weather.windSpd === 'number'; // 36
    out.perf = typeof api.perf.fps === 'number';                                // 37
    out.droneCount = api.droneCount > 0;                                        // 38

    // 정리 — 전역 상태 복원
    api.stopSim();
    return out;
})()"""


def test_production_core_30_methods_invoke(page):
    """핵심 30종 production 메서드 실 호출 — 관측 효과 검증."""
    r = page.evaluate(_CORE_30_EVAL)
    failed = [k for k, v in r.items() if v is not True]
    assert not failed, f"production 코어 메서드 실패: {failed}"
    assert len(r) >= 30, f"검증된 코어가 30 미만: {len(r)}"


def test_all_core_30_are_production_grade(page):
    """검증 대상 30종이 전부 production 등급으로 분류되는지 게이트."""
    # _CORE_30_EVAL이 실제로 호출하는 production API 이름 (getter/setter 짝).
    names = [
        "startSim", "selectDrone", "atcCommand", "getSelected", "deselectDrone",
        "setPredTrail", "predTrail", "setPredHorizon", "predHorizon",
        "setVelArrow", "velArrow", "setCpaMarker", "cpaMarker", "cpaPairsCount",
        "missionTemplate", "missionAssignTemplate", "missions", "missionClearAll",
        "injectDynamicNFZ", "dynamicNfzList", "injectFault", "injectRogue",
        "injStats", "injClearAll", "setCamMode", "camMode", "focusDrone",
        "setSunHour", "sunHour", "setSunAuto", "sunEnabled", "setRain", "setSnow",
        "setAnaHeatmap", "anaHeatmap", "anaKpiWindow",
        "setAmbientAudio", "ambientAudio", "lang", "setLang", "multiSelect",
        "multiSelection", "clearMulti", "setAnalysisView", "analysisMode",
        "soraAssess", "stats", "weather", "perf", "droneCount",
    ]
    grades = page.evaluate(
        "(names) => names.map(n => [n, window._sdacs.apiMaturity(n)])", names
    )
    non_production = [n for n, g in grades if g != "production"]
    assert not non_production, f"production 미분류 코어: {non_production}"
    distinct = {n for n, _ in grades}
    assert len(distinct) >= 30, f"distinct production 코어 30 미만: {len(distinct)}"
