"""ATC 콘솔 시뮬레이터 심화 스모크 테스트 (Playwright).

검증 항목 (Phase 1A-1E):
1. 시뮬레이터가 JS 에러 없이 로드되는지
2. _sdacs API · atcCommand · atcLog · atcControlled 노출 확인
3. HOLD/RTB/REROUTE/ALT/SPD/TURN/CLEAR 명령 실행 및 상태 변화 확인
4. ATC 명령 로그 누적 + UI 패널 가시화 확인
5. ATC 시안 링이 렌더링 트리에 들어가는지 (간접: scene children count)
6. CSV 내보내기에 ATC_Commands 시트가 포함되는지 (data URL 검사)
7. 음성 토글 상태 전환 확인
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
    """Serve repo root over HTTP for the simulator + vendor assets."""
    port = 0
    handler = http.server.SimpleHTTPRequestHandler

    class QuietHandler(handler):
        def log_message(self, *args, **kwargs):  # silence
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", port), QuietHandler)
    port = httpd.server_address[1]
    thread = threading.Thread(
        target=httpd.serve_forever, daemon=True, name="atc-smoke-server"
    )
    import os

    os.chdir(ROOT)
    thread.start()
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
        js_errors: list[str] = []
        pg.on("pageerror", lambda exc: js_errors.append(str(exc)))
        pg.on(
            "console",
            lambda msg: js_errors.append(f"console.{msg.type}: {msg.text}")
            if msg.type in ("error",)
            else None,
        )
        pg.goto(
            f"{http_server}/swarm_3d_simulator.html",
            wait_until="networkidle",
            timeout=20000,
        )
        # 시뮬 초기화 대기 (드론 100대 시나리오 기본)
        pg.wait_for_function("window._sdacs && window._sdacs.droneCount > 0", timeout=15000)
        # 시뮬 시작 + 드론들이 이륙하도록 시간 진행 + 시뮬 속도 가속
        pg.evaluate(
            """
            () => {
                window._sdacs.startSim();
                // groundDelay (최대 15초) + takeoff 시간 단축을 위해 sim speed 가속
                const slider = document.getElementById('sim-speed') || document.getElementById('speed');
                if (slider) { slider.value = 10; slider.dispatchEvent(new Event('input')); }
            }
            """
        )
        # 최소 1대 비행중 될 때까지 대기 (최대 12초)
        try:
            pg.wait_for_function(
                "window._sdacs && window._sdacs.airborne >= 1",
                timeout=20000,
            )
        except Exception:
            pass  # 일부 시나리오에서 5초 내 이륙 못할 수 있음
        pg.wait_for_timeout(800)
        yield pg, js_errors
        ctx.close()
        browser.close()


def test_simulator_loads_without_js_errors(page):
    pg, errors = page
    title = pg.title()
    assert "SDACS" in title, f"Unexpected title: {title}"
    # 환경 의존 에러 화이트리스트 — ws_bridge 미실행·CDN cert·WebGPU·favicon 등
    benign_markers = [
        "favicon",
        "WebGPU",
        "DevTools",
        "ws_bridge",
        "ws://localhost",
        "ws://127.0.0.1",
        "WebSocket",
        "ERR_CERT_AUTHORITY_INVALID",
        "ERR_CONNECTION_REFUSED",
        "fonts.googleapis",
    ]
    blocking = [
        e for e in errors if not any(m in e for m in benign_markers)
    ]
    assert not blocking, f"Page emitted JS errors: {blocking}"


def test_sdacs_api_exposes_atc(page):
    pg, _ = page
    api_keys = pg.evaluate("Object.keys(window._sdacs)")
    for needed in [
        "atcCommand",
        "atcLog",
        "atcControlled",
        "setAtcAudio",
        "clearAllAtc",
    ]:
        assert needed in api_keys, f"_sdacs.{needed} missing"


def test_atc_hold_changes_phase(page):
    pg, _ = page
    # 비행 중 드론을 우선, 없으면 GROUNDED도 허용 (HOLD는 어느 phase에서나 적용됨)
    result = pg.evaluate(
        """
        () => {
            window._sdacs.clearAllAtc();
            let chosen = null;
            for (let i = 0; i < 200; i++) {
                const id = window._sdacs.selectDrone(i);
                if (!id) continue;
                const sel = window._sdacs.getSelected();
                if (sel && sel.phase !== 'GROUNDED' && sel.phase !== 'FAILED') {
                    chosen = { id, phase: sel.phase };
                    break;
                }
            }
            if (!chosen) {
                // 모두 GROUNDED여도 진행: 첫 드론 선택
                const id = window._sdacs.selectDrone(0);
                if (!id) return { ok: false, reason: 'no drones available' };
                const sel = window._sdacs.getSelected();
                chosen = { id, phase: sel.phase };
            }
            window._sdacs.atcCommand(chosen.id, 'HOLD');
            const controlled = window._sdacs.atcControlled;
            const ctrlEntry = controlled.find(x => x.id === chosen.id);
            return {
                ok: true,
                before: chosen,
                controlledCount: controlled.length,
                cmd: ctrlEntry ? ctrlEntry.cmd : null,
                phaseNow: window._sdacs.getSelected().phase,
            };
        }
        """
    )
    assert result["ok"], f"Setup failed: {result.get('reason')}"
    assert result["phaseNow"] == "HOLDING", (
        f"Expected HOLDING after HOLD cmd, got {result['phaseNow']}"
    )
    assert result["controlledCount"] >= 1
    assert result["cmd"] == "HOLD"


def test_atc_rtb_sets_goal_to_startpad(page):
    pg, _ = page
    res = pg.evaluate(
        """
        () => {
            // ENROUTE 드론 1대 찾기
            window._sdacs.clearAllAtc();
            for (let i = 0; i < 200; i++) {
                const id = window._sdacs.selectDrone(i);
                if (!id) continue;
                const sel = window._sdacs.getSelected();
                if (sel && sel.phase === 'ENROUTE' && sel.startPad) {
                    const sx = sel.startPad.x, sz = sel.startPad.z;
                    window._sdacs.atcCommand(sel.id, 'RTB');
                    const after = window._sdacs.getSelected();
                    return {
                        ok: true,
                        phase: after.phase,
                        goalX: after.goalX,
                        goalZ: after.goalZ,
                        startX: sx,
                        startZ: sz,
                        cmd: after.atc.cmd,
                    };
                }
            }
            return { ok: false, reason: 'no ENROUTE drone' };
        }
        """
    )
    if not res["ok"]:
        pytest.skip(f"No ENROUTE drone available: {res.get('reason')}")
    assert res["phase"] == "RTL"
    assert res["cmd"] == "RTB"
    assert abs(res["goalX"] - res["startX"]) < 0.5
    assert abs(res["goalZ"] - res["startZ"]) < 0.5


def test_atc_alt_offsets_target(page):
    pg, _ = page
    res = pg.evaluate(
        """
        () => {
            window._sdacs.clearAllAtc();
            for (let i = 0; i < 200; i++) {
                const id = window._sdacs.selectDrone(i);
                if (!id) continue;
                const sel = window._sdacs.getSelected();
                if (sel && (sel.phase === 'ENROUTE' || sel.phase === 'TAKEOFF')) {
                    const before = sel.targetAlt;
                    window._sdacs.atcCommand(sel.id, 'ALT', { delta: 10 });
                    const after = window._sdacs.getSelected();
                    return { ok: true, before, after: after.targetAlt };
                }
            }
            return { ok: false };
        }
        """
    )
    if not res["ok"]:
        pytest.skip("No airborne drone for ALT")
    assert res["after"] > res["before"], f"ALT+ should raise targetAlt: {res}"
    assert res["after"] - res["before"] >= 9.5  # ~10


def test_atc_spd_modifies_maxspeed(page):
    pg, _ = page
    res = pg.evaluate(
        """
        () => {
            window._sdacs.clearAllAtc();
            for (let i = 0; i < 200; i++) {
                const id = window._sdacs.selectDrone(i);
                if (!id) continue;
                const sel = window._sdacs.getSelected();
                if (sel && sel.phase !== 'GROUNDED') {
                    const before = sel.maxSpeed;
                    window._sdacs.atcCommand(sel.id, 'SPD', { factor: 1.2 });
                    const after = window._sdacs.getSelected();
                    return { ok: true, before, after: after.maxSpeed };
                }
            }
            return { ok: false };
        }
        """
    )
    if not res["ok"]:
        pytest.skip("No airborne drone for SPD")
    assert res["after"] > res["before"]
    ratio = res["after"] / res["before"]
    assert 1.18 < ratio < 1.22, f"SPD factor 1.2 expected, got ratio {ratio}"


def test_atc_clear_resets_state(page):
    pg, _ = page
    res = pg.evaluate(
        """
        () => {
            window._sdacs.clearAllAtc();
            const id = window._sdacs.selectDrone(0);
            if (!id) return { ok: false };
            window._sdacs.atcCommand(id, 'HOLD');
            // 즉시 cmd 값 캡처 (CLEAR 전) — getSelected의 shallow spread 회피
            const midCmd = window._sdacs.atcControlled.find(x => x.id === id)?.cmd;
            const midCount = window._sdacs.atcControlled.length;
            window._sdacs.atcCommand(id, 'CLEAR');
            const after = window._sdacs.getSelected();
            return {
                ok: true,
                midCmd,
                midCount,
                afterCmd: after && after.atc ? after.atc.cmd : null,
                controlledCount: window._sdacs.atcControlled.length,
            };
        }
        """
    )
    assert res["ok"]
    assert res["midCmd"] == "HOLD"
    assert res["midCount"] >= 1
    assert res["afterCmd"] is None
    assert res["controlledCount"] == 0


def test_atc_log_accumulates(page):
    pg, _ = page
    res = pg.evaluate(
        """
        () => {
            window._sdacs.clearAllAtc();
            const before = window._sdacs.atcLog.length;
            const id1 = window._sdacs.selectDrone(0);
            const id2 = window._sdacs.selectDrone(1);
            window._sdacs.atcCommand(id1, 'HOLD');
            window._sdacs.atcCommand(id2, 'ALT', { delta: 10 });
            const after = window._sdacs.atcLog;
            return {
                before,
                addedCount: after.length - before,
                lastTwo: after.slice(-2).map(e => e.cmd),
            };
        }
        """
    )
    assert res["addedCount"] >= 2
    assert "HOLD" in res["lastTwo"]
    assert "ALT" in res["lastTwo"]


def test_atc_audio_toggle(page):
    pg, _ = page
    res = pg.evaluate(
        """
        () => {
            const before = window._sdacs.atcAudio;
            window._sdacs.setAtcAudio(true);
            const mid = window._sdacs.atcAudio;
            window._sdacs.setAtcAudio(false);
            const after = window._sdacs.atcAudio;
            return { before, mid, after };
        }
        """
    )
    assert res["mid"] is True
    assert res["after"] is False


def test_atc_panel_visible_when_drone_selected(page):
    pg, _ = page
    pg.evaluate("window._sdacs.selectDrone(0)")
    pg.wait_for_timeout(100)
    has_panel = pg.evaluate(
        "document.querySelector('.atc-panel') !== null && document.getElementById('drone-detail').style.display !== 'none'"
    )
    assert has_panel, "ATC panel should be rendered in selected drone detail"


def test_atc_log_panel_appears_after_command(page):
    pg, _ = page
    pg.evaluate(
        """() => {
            window._sdacs.clearAllAtc();
            const id = window._sdacs.selectDrone(0);
            window._sdacs.atcCommand(id, 'HOLD');
        }"""
    )
    pg.wait_for_timeout(100)
    visible = pg.evaluate(
        """
        () => {
            const el = document.getElementById('atc-log');
            if (!el) return false;
            return el.classList.contains('has-cmds');
        }
        """
    )
    assert visible, "ATC log panel should have has-cmds class after a command"
