"""ODYSSEY Phase 447 — 시나리오 fuzzing.

시나리오 갤러리 + 시드 변이로 무작위 임의 입력에서 시뮬레이터 코어가
패닉/충돌(JS 미처리 예외) 없이 동작함을 검증한다.

Hypothesis로 _sdacs API 매개변수 공간을 샘플링:
  - injectDynamicNFZ(x,z,r,dur) 임의 좌표·반경·만료시간
  - atcCommand 임의 명령 시퀀스
  - setAltitude / scenarios 진입 등
"""
from __future__ import annotations

import http.server
import os
import socketserver
import threading
import time
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

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
        errors: list[str] = []
        pg.on("pageerror", lambda exc: errors.append(str(exc)))
        pg.goto(f"{http_server}/swarm_3d_simulator.html",
                wait_until="networkidle", timeout=20000)
        pg.wait_for_function("window._sdacs && window._sdacs.droneCount > 0", timeout=15000)
        yield pg, errors
        ctx.close()
        browser.close()


@settings(max_examples=80, deadline=None)
@given(
    x=st.floats(min_value=-2000, max_value=2000,
                allow_nan=False, allow_infinity=False),
    z=st.floats(min_value=-2000, max_value=2000,
                allow_nan=False, allow_infinity=False),
    r=st.floats(min_value=10, max_value=500,
                allow_nan=False, allow_infinity=False),
    dur=st.floats(min_value=1, max_value=120,
                  allow_nan=False, allow_infinity=False),
)
def test_dynamic_nfz_fuzz_no_panic(page, x, z, r, dur):
    pg, errors = page
    pre_errors = len(errors)
    result = pg.evaluate(
        f"window._sdacs.injectDynamicNFZ({x}, {z}, {r}, {dur})")
    assert result is not None
    assert result["r"] == r
    # 신규 JS 예외 0건
    new = errors[pre_errors:]
    benign = ["WebGPU", "ws://", "fonts.googleapis"]
    blocking = [e for e in new if not any(b in e for b in benign)]
    assert not blocking, f"fuzz x={x} z={z} r={r} dur={dur} → JS error: {blocking}"


@settings(max_examples=40, deadline=None)
@given(
    cmd=st.sampled_from(["HOLD", "RTB", "ALT_UP", "ALT_DOWN", "SPD_UP",
                         "SPD_DOWN", "TURN_L", "TURN_R", "CLEAR"]),
    drone_idx=st.integers(min_value=0, max_value=9),
)
def test_atc_command_fuzz_no_panic(page, cmd, drone_idx):
    pg, errors = page
    pre_errors = len(errors)
    pg.evaluate(f"""(() => {{
        const api = window._sdacs;
        const d = api.selectDrone({drone_idx});
        if (d) api.atcCommand(d, '{cmd}');
        api.deselectDrone();
    }})()""")
    new = errors[pre_errors:]
    benign = ["WebGPU", "ws://", "fonts.googleapis"]
    blocking = [e for e in new if not any(b in e for b in benign)]
    assert not blocking, f"fuzz cmd={cmd} idx={drone_idx} → {blocking}"


@settings(max_examples=20, deadline=None)
@given(
    density=st.sampled_from(["controlled", "sparse", "populated", "assembly"]),
    bvlos=st.booleans(),
)
def test_sora_assess_fuzz_returns_valid_sail(page, density, bvlos):
    """soraAssess는 어떤 입력에서도 (SAIL I-VI 또는 CERTIFIED)를 반환."""
    pg, _ = page
    r = pg.evaluate(
        f"window._sdacs.soraAssess({{populationDensity:'{density}', bvlos:{str(bvlos).lower()}}})")
    valid_sails = {"SAIL I", "SAIL II", "SAIL III", "SAIL IV",
                   "SAIL V", "SAIL VI", "CERTIFIED"}
    assert r["sail"] in valid_sails, r["sail"]
    assert 1 <= r["finalGrc"] <= 10
    assert r["arc"] in ("ARC-a", "ARC-b", "ARC-c", "ARC-d")
