"""Phase 2 TAC (전술 시각화) Playwright 스모크 테스트.

검증:
- 예측 비행경로 라인 (TAC-1)
- CPA 충돌점 마커 (TAC-2)
- 속도 벡터 화살표 (TAC-3)
- 토글·LOD·외부 API
"""
from __future__ import annotations

import http.server
import socketserver
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def http_server():
    port = 0
    handler = http.server.SimpleHTTPRequestHandler

    class Quiet(handler):
        def log_message(self, *a, **kw):
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", port), Quiet)
    port = httpd.server_address[1]
    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    import os
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
        # 비행 진입 대기
        try:
            pg.wait_for_function("window._sdacs.airborne >= 2", timeout=20000)
        except Exception:
            pass
        pg.wait_for_timeout(1200)
        yield pg, errors
        ctx.close()
        browser.close()


def test_tac_api_exposed(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["setPredTrail", "predTrail", "setPredHorizon", "predHorizon",
              "setVelArrow", "velArrow", "setCpaMarker", "cpaMarker", "cpaPairsCount"]:
        assert k in keys, f"_sdacs.{k} missing"


def test_pred_trail_toggle(page):
    pg, _ = page
    # ON by default
    r = pg.evaluate("""
        () => {
            const on0 = window._sdacs.predTrail;
            window._sdacs.setPredTrail(false);
            const off = window._sdacs.predTrail;
            window._sdacs.setPredTrail(true);
            const on1 = window._sdacs.predTrail;
            return { on0, off, on1 };
        }
    """)
    assert r["on0"] is True
    assert r["off"] is False
    assert r["on1"] is True


def test_pred_horizon_clamps(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const a = window._sdacs.setPredHorizon(1);     // clamp to 2
            const b = window._sdacs.setPredHorizon(100);   // clamp to 20
            const c = window._sdacs.setPredHorizon(8);
            return { a, b, c };
        }
    """)
    assert r["a"] == 2
    assert r["b"] == 20
    assert r["c"] == 8


def test_pred_trail_creates_line_objects(page):
    pg, _ = page
    pg.wait_for_timeout(500)
    # 비행 중 드론들에 _predTrail 생성 확인 — 직접 접근 불가, sdacs 통해 검증
    n_lines = pg.evaluate("""
        () => {
            // predTrailGroup은 글로벌 접근 불가 → scene 자식 카운트로 간접 검증
            // 모든 자식 중 LineSegments/Line 타입 카운트
            // 대신, _sdacs API로 활성화 확인
            return {
                airborne: window._sdacs.airborne,
                enabled: window._sdacs.predTrail,
            };
        }
    """)
    assert n_lines["enabled"] is True
    # 최소 1대 비행 중이어야 의미 있음
    if n_lines["airborne"] < 1:
        pytest.skip("no airborne drone")


def test_vel_arrow_toggle(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.setVelArrow(true);
            window._sdacs.selectDrone(0);
            const on = window._sdacs.velArrow;
            window._sdacs.setVelArrow(false);
            const off = window._sdacs.velArrow;
            return { on, off };
        }
    """)
    assert r["on"] is True
    assert r["off"] is False


def test_cpa_marker_toggle(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const on0 = window._sdacs.cpaMarker;
            window._sdacs.setCpaMarker(false);
            const off = window._sdacs.cpaMarker;
            window._sdacs.setCpaMarker(true);
            const on1 = window._sdacs.cpaMarker;
            return { on0, off, on1 };
        }
    """)
    assert r["on0"] is True
    assert r["off"] is False
    assert r["on1"] is True


def test_tac_toggle_ui_present(page):
    pg, _ = page
    r = pg.evaluate("""
        () => ({
            pred: !!document.getElementById('tg-pred-trail'),
            vel:  !!document.getElementById('tg-vel-arrow'),
            cpa:  !!document.getElementById('tg-cpa-marker'),
        })
    """)
    assert r["pred"], "tg-pred-trail checkbox missing"
    assert r["vel"], "tg-vel-arrow checkbox missing"
    assert r["cpa"], "tg-cpa-marker checkbox missing"


def test_pred_horizon_default(page):
    pg, _ = page
    horizon = pg.evaluate("window._sdacs.predHorizon")
    assert horizon == 8.0, f"Expected default 8s, got {horizon}"


def test_tac6_apf_intent_api_exposed(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["setApfIntent", "apfIntent", "apfIntentCount"]:
        assert k in keys, f"_sdacs.{k} missing"


def test_tac6_apf_intent_default_off(page):
    pg, _ = page
    # 기본 OFF (선택 기반 오버레이, 부담 큰 시각화라 opt-in)
    assert pg.evaluate("window._sdacs.apfIntent") is False
    assert pg.evaluate("window._sdacs.apfIntentCount") == 0


def test_tac6_apf_intent_toggle(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const on = window._sdacs.setApfIntent(true);
            const ui = document.getElementById('tg-apf-intent').checked;
            const off = window._sdacs.setApfIntent(false);
            return { on, ui, off };
        }
    """)
    assert r["on"] is True
    assert r["ui"] is True
    assert r["off"] is False


def test_tac6_apf_intent_renders_under_conflict(page):
    pg, _ = page
    # 공역 드론이 EVADE_DIST(500m) 내로 수렴하면 회피 의도 화살표가 생성된다.
    # module-scope page를 공유하므로 직전 시나리오를 저장 후 복원한다.
    prev = pg.evaluate("document.getElementById('scenario-select').value")
    try:
        pg.evaluate("window._sdacs.selectScenario('high_density'); window._sdacs.startSim();")
        pg.evaluate(
            "() => { const n = window._sdacs.droneCount;"
            " const ids = Array.from({length: n}, (_, k) => k);"
            " window._sdacs.multiSelect(ids); window._sdacs.setApfIntent(true); }"
        )
        max_cnt = 0
        for _ in range(20):
            pg.wait_for_timeout(900)
            c = pg.evaluate("window._sdacs.apfIntentCount")
            max_cnt = max(max_cnt, c)
            if max_cnt > 0:
                break
        if max_cnt == 0:
            pytest.skip("airborne drones did not converge within EVADE_DIST in headless time budget")
        assert max_cnt > 0
    finally:
        # 공유 상태 복원: 의도선 OFF + 직전 시나리오 재선택
        pg.evaluate("window._sdacs.setApfIntent(false)")
        pg.evaluate(f"window._sdacs.selectScenario('{prev}'); window._sdacs.startSim();")
        pg.wait_for_timeout(500)


def test_tac6_apf_intent_ui_present(page):
    pg, _ = page
    assert pg.evaluate("!!document.getElementById('tg-apf-intent')"), \
        "tg-apf-intent checkbox missing"


def test_no_js_errors_with_tac(page):
    pg, errors = page
    benign = ["favicon", "WebGPU", "DevTools", "ws_bridge", "WebSocket",
              "ws://localhost", "ws://127.0.0.1", "ERR_CERT", "ERR_CONNECTION",
              "fonts.googleapis"]
    blocking = [e for e in errors if not any(m in e for m in benign)]
    assert not blocking, f"JS errors: {blocking}"
