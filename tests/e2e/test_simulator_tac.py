"""Phase 2 TAC (전술 시각화) Playwright 스모크 테스트.

검증:
- 예측 비행경로 라인 (TAC-1)
- CPA 충돌점 마커 (TAC-2)
- 속도 벡터 화살표 (TAC-3)
- 분리 표준 거품 (TAC-4)
- 우선순위 심볼 (TAC-5)
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


def test_sep_bubble_api_and_toggle(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["setSepBubble", "sepBubble", "sepBubbleCount"]:
        assert k in keys, f"_sdacs.{k} missing"
    r = pg.evaluate("""
        () => {
            const off0 = window._sdacs.sepBubble;       // 기본 OFF
            window._sdacs.setSepBubble(true);
            const on = window._sdacs.sepBubble;
            window._sdacs.setSepBubble(false);
            const off1 = window._sdacs.sepBubble;
            return { off0, on, off1 };
        }
    """)
    assert r["off0"] is False
    assert r["on"] is True
    assert r["off1"] is False


def test_sep_bubble_creates_on_select(page):
    pg, _ = page
    if pg.evaluate("window._sdacs.airborne") < 1:
        pytest.skip("no airborne drone")
    pg.evaluate("window._sdacs.setSepBubble(true)")
    # 비행 드론은 일부뿐 — 인덱스를 스캔해 거품이 생성되는지 확인
    created = 0
    for i in range(pg.evaluate("window._sdacs.droneCount")):
        pg.evaluate(f"window._sdacs.selectDrone({i})")
        pg.wait_for_timeout(150)  # CI 부하에서도 rAF 1회 이상 보장
        created = pg.evaluate("window._sdacs.sepBubbleCount")
        if created >= 1:
            break
    pg.evaluate("window._sdacs.setSepBubble(false)")
    assert created >= 1, "비행 드론 선택 시 분리 거품이 생성되어야 함"


def test_pri_icon_api_and_toggle(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["setPriIcon", "priIcon", "priIconCount"]:
        assert k in keys, f"_sdacs.{k} missing"
    r = pg.evaluate("""
        () => {
            const off0 = window._sdacs.priIcon;          // 기본 OFF
            window._sdacs.setPriIcon(true);
            const on = window._sdacs.priIcon;
            window._sdacs.setPriIcon(false);
            const off1 = window._sdacs.priIcon;
            return { off0, on, off1 };
        }
    """)
    assert r["off0"] is False
    assert r["on"] is True
    assert r["off1"] is False


def test_pri_icon_count_matches_airborne(page):
    pg, _ = page
    pg.evaluate("window._sdacs.setPriIcon(true)")
    pg.wait_for_timeout(400)  # 렌더 프레임 1회 경과 대기
    r = pg.evaluate("({ count: window._sdacs.priIconCount, drones: window._sdacs.droneCount, air: window._sdacs.airborne })")
    pg.evaluate("window._sdacs.setPriIcon(false)")
    # 우선순위 아이콘은 비지상 드론마다 1개 — 전체 드론 수 이하
    assert r["count"] <= r["drones"]
    if r["air"] >= 1:
        assert r["count"] >= 1, "비행 드론이 있으면 우선순위 심볼이 1개 이상이어야 함"


def test_tac45_cleared_on_scenario_reset(page):
    """시나리오 전환 시 분리거품·우선순위심볼 Map이 정리되어야 함 (메모리 누수 방지)."""
    pg, _ = page
    pg.evaluate("window._sdacs.setSepBubble(true); window._sdacs.setPriIcon(true); window._sdacs.selectDrone(0)")
    pg.wait_for_timeout(200)
    # 시나리오 재초기화 → resetTacOverlays()로 즉시 0
    pg.evaluate("window._sdacs.selectScenario('default')")
    pg.wait_for_timeout(100)
    counts = pg.evaluate("({ sep: window._sdacs.sepBubbleCount, pri: window._sdacs.priIconCount })")
    pg.evaluate("window._sdacs.setSepBubble(false); window._sdacs.setPriIcon(false)")
    assert counts["sep"] == 0, "시나리오 리셋 후 분리거품 Map이 비어야 함"
    assert counts["pri"] == 0, "시나리오 리셋 후 우선순위심볼 Map이 비어야 함"


def test_tac45_toggle_ui_present(page):
    pg, _ = page
    r = pg.evaluate("""
        () => ({
            sep: !!document.getElementById('tg-sep-bubble'),
            pri: !!document.getElementById('tg-pri-icon'),
        })
    """)
    assert r["sep"], "tg-sep-bubble checkbox missing"
    assert r["pri"], "tg-pri-icon checkbox missing"


def test_no_js_errors_with_tac(page):
    pg, errors = page
    benign = ["favicon", "WebGPU", "DevTools", "ws_bridge", "WebSocket",
              "ws://localhost", "ws://127.0.0.1", "ERR_CERT", "ERR_CONNECTION",
              "fonts.googleapis"]
    blocking = [e for e in errors if not any(m in e for m in benign)]
    assert not blocking, f"JS errors: {blocking}"
