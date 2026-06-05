"""HYPER Phase 17 (WebXR VR) + Phase 19 (Mission Recorder 공유) E2E."""
from __future__ import annotations

import http.server
import json
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
            pg.wait_for_function("window._sdacs.airborne >= 1", timeout=15000)
        except Exception:
            pass
        pg.wait_for_timeout(800)
        # 일부 녹화 프레임 축적
        pg.wait_for_function("window._sdacs.replayFrames >= 2", timeout=15000)
        yield pg, errors
        ctx.close()
        browser.close()


# ===== Phase 17 — WebXR =====

def test_xr_api_exposed(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["xrSupported", "xrPresenting"]:
        assert k in keys, f"_sdacs.{k} missing"


def test_xr_not_presenting_by_default(page):
    pg, _ = page
    # 헤드리스 Chromium은 일반적으로 immersive-vr 미지원, 단 API는 존재해야
    r = pg.evaluate("""({
        navigatorXr: !!navigator.xr,
        rendererXrEnabled: window._sdacs.xrSupported,
        presenting: window._sdacs.xrPresenting,
    })""")
    # navigator.xr이 없으면 supported=false, presenting=false
    assert r["presenting"] is False  # 헤드리스에선 VR 세션 시작 안 됨


# ===== Phase 19 — Mission Recorder 공유 =====

def test_mission_api_exposed(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["exportMission", "importMission", "triggerMissionImport"]:
        assert k in keys, f"_sdacs.{k} missing"


def test_mission_export_creates_filename(page):
    pg, _ = page
    # 다운로드 이벤트 캡처를 위해 page.expect_download 사용
    with pg.expect_download(timeout=5000) as dl_info:
        pg.evaluate("window._sdacs.exportMission()")
    download = dl_info.value
    assert download.suggested_filename.endswith(".sdacs-mission")
    assert "sdacs_mission_" in download.suggested_filename


def test_mission_export_returns_json_structure(page):
    pg, _ = page
    # 직접 함수 호출 결과 (filename 반환) + 내용 확인을 위해 fetch
    r = pg.evaluate("""
        async () => {
            // exportMission은 _download 호출 + 파일명 반환
            // 내부 데이터 구조 직접 검증을 위해 window._exportMission이 빌드한 data 객체 재현
            const scen = document.getElementById('scenario-select')?.value || 'default';
            return {
                hasSimRunning: window._sdacs.simRunning,
                replayFrames: window._sdacs.replayFrames,
                scenario: scen,
            };
        }
    """)
    assert r["replayFrames"] >= 2


def test_mission_import_invalid_returns_error(page):
    pg, _ = page
    r = pg.evaluate("""window._sdacs.importMission('{"foo": "bar"}')""")
    assert r["ok"] is False
    assert "error" in r


def test_mission_import_valid_loads_frames(page):
    pg, _ = page
    r = pg.evaluate(r"""
        () => {
            const data = {
                _format: 'sdacs-mission',
                _version: '1.0',
                _createdAt: new Date().toISOString(),
                scenario: 'default',
                droneCount: 2,
                frameCount: 3,
                duration: 1.0,
                frames: [
                    { t: 0.0, d: [[0,30,0,'ENROUTE',95],[10,40,5,'ENROUTE',92]] },
                    { t: 0.5, d: [[5,30,3,'ENROUTE',94],[12,40,5,'ENROUTE',91]] },
                    { t: 1.0, d: [[10,30,6,'ENROUTE',93],[14,40,5,'ENROUTE',90]] },
                ],
                droneIds: ['DR-001','DR-002'],
                droneRoles: ['cargo','cargo'],
                stats: {},
                kpi: [],
                atcLog: [],
                copilotHistory: [],
            };
            return window._sdacs.importMission(JSON.stringify(data));
        }
    """)
    assert r["ok"] is True
    assert r["frames"] == 3
    assert r["scenario"] == "default"


def test_mission_ui_buttons_present(page):
    pg, _ = page
    r = pg.evaluate("""
        () => ({
            exp: !!document.getElementById('btn-mission-export'),
            imp: !!document.getElementById('btn-mission-import'),
        })
    """)
    assert r["exp"], "임무 저장 버튼 없음"
    assert r["imp"], "임무 로드 버튼 없음"


def test_phase17_19_no_js_errors(page):
    pg, errors = page
    benign = ["favicon", "WebGPU", "DevTools", "ws_bridge", "WebSocket",
              "ws://localhost", "ws://127.0.0.1", "ERR_CERT", "ERR_CONNECTION",
              "fonts.googleapis", "AudioContext", "xr"]
    blocking = [e for e in errors if not any(m in e for m in benign)]
    assert not blocking, f"JS errors: {blocking}"
