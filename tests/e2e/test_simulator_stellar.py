"""STELLAR Phase 52-100 — 49 Phase 일괄 E2E."""
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
        pg.wait_for_timeout(500)
        yield pg, errors
        ctx.close()
        browser.close()


# Track Ω 자율결정 (Phase 51-55)
def test_phase51_llm_delegate(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const grp = window._sdacs.stellar51DelegateGroup([0, 1], 'claude-opus-4-8');
            const n = window._sdacs.stellar51Tick();
            const groups = window._sdacs.stellar51Groups;
            const missing = window._sdacs.stellar51Recommend('NOPE');
            const removed = window._sdacs.stellar51Revoke(grp.id);
            return { provider: grp.llmProvider, decisions: n, groupCount: groups.length, missing, removed };
        }
    """)
    assert r["provider"] == "claude-opus-4-8"
    assert r["decisions"] == 2
    assert r["groupCount"] == 1
    assert r["missing"] == "NOOP"
    assert r["removed"] == 1


# Track Ω 자율결정 (Phase 52-55)
def test_phase52_rlhf(page):
    pg, _ = page
    r = pg.evaluate("""({
        a: window._sdacs.rlhfFeedback('HOLD', 5, 'good'),
        b: window._sdacs.rlhfFeedback('REROUTE', 2, 'bad'),
        state: window._sdacs.rlhfState,
    })""")
    assert r["a"]["rating"] == 5
    assert r["state"]["feedbackCount"] >= 2


def test_phase53_causal(page):
    pg, _ = page
    r = pg.evaluate("""({
        edges: [
            window._sdacs.causalAddEdge('weather', 'risk', 0.7),
            window._sdacs.causalAddEdge('risk', 'collision', 0.5),
        ],
        q: window._sdacs.causalDoQuery('weather', 'collision'),
        dag: window._sdacs.causalDag,
    })""")
    assert r["dag"]["edges"]
    assert r["q"]["target"] == "collision"


def test_phase54_adversarial(page):
    pg, _ = page
    r = pg.evaluate("""({
        a: window._sdacs.adversarialCheck([0.5, 0.5, 0.5]),
        b: window._sdacs.adversarialCheck([10, 10, 10]),
        detected: window._sdacs.adversarialDetected,
    })""")
    assert "norm" in r["a"]
    assert r["detected"] >= 0


def test_phase55_explainable(page):
    pg, _ = page
    r = pg.evaluate("""window._sdacs.explainDecision('AVOID', { distance: 0.8, battery: 0.3, threat: 0.9 })""")
    assert "attributions" in r
    assert r["method"] == "shap"


# Track Σ 초대규모 (Phase 56-60)
def test_phase56_gpu100k(page):
    pg, _ = page
    r = pg.evaluate("""({ init: window._sdacs.gpu100kInit(), stats: window._sdacs.gpu100kStats })""")
    assert r["init"]["capacity"] == 100000
    assert r["stats"]["gridSize"] == 512


def test_phase57_distributed_sim(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.distributedSimAddShard(0, 25);
            window._sdacs.distributedSimAddShard(25, 50);
            const n = window._sdacs.distributedSimRebalance();
            return { shards: window._sdacs.distributedShards.length, rebalanced: n };
        }
    """)
    assert r["shards"] == 2
    assert r["rebalanced"] == 2


def test_phase58_cloud_burst(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            // cloudBurst를 활성화하지 않으면 null 반환
            return { res: window._sdacs.cloudBurstScale(0.9), state: window._sdacs.cloudBurstState };
        }
    """)
    # enabled=false 상태에서는 null 반환 (정상)
    assert r["state"] is not None


def test_phase59_streaming(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const sent = window._sdacs.streamingReplayPush({ t: 0, d: [[0,0,0,'OK',100]] });
            return { sent, stats: window._sdacs.streamingStats };
        }
    """)
    assert "sent" in r["stats"]
    assert "dropped" in r["stats"]


def test_phase60_video_proc(page):
    pg, _ = page
    r = pg.evaluate("""({ enc: window._sdacs.videoProcEncode({}), stats: window._sdacs.videoProcStats })""")
    # enabled=false → null
    assert r["stats"]["codec"] == "av1"


# Track Φ 물리트윈 (Phase 61-65)
def test_phase61_skybrush(page):
    pg, _ = page
    r = pg.evaluate("""window._sdacs.skybrushConnect('localhost:5000')""")
    assert r["connected"] is True


def test_phase62_cesium(page):
    pg, _ = page
    r = pg.evaluate("""window._sdacs.cesiumGlobalInit()""")
    assert r["enabled"] is True


def test_phase63_ue5(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.ue5ExportScene('seoul_scene');
            window._sdacs.ue5ExportScene('busan_scene');
            return window._sdacs.ue5SceneCount;
        }
    """)
    assert r == 2


def test_phase64_ros2(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.ros2SubscribeTopic('/mavlink', 'GLOBAL_POSITION_INT');
            window._sdacs.ros2SubscribeTopic('/cmd_vel', 'Twist');
            return window._sdacs.ros2Topics;
        }
    """)
    assert len(r) >= 2


def test_phase65_isaac(page):
    pg, _ = page
    r = pg.evaluate("""window._sdacs.isaacSimLoadUSD('https://example.com/scene.usd')""")
    assert r["loaded"] is True


# Track Ψ 사회 (Phase 66-70)
def test_phase66_society(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.societyAddReport('noise', 'high');
            const q = window._sdacs.societyInsuranceQuote('delivery', 500, 'clean');
            return { reports: window._sdacs.societyReports, quote: q };
        }
    """)
    assert len(r["reports"]) >= 1
    assert r["quote"] > 0


# Track Ξ 지구 너머 (Phase 71-75)
def test_phase71_beyond_earth(page):
    pg, _ = page
    r = pg.evaluate("""({
        moon: window._sdacs.beyondEarthSetMode('moon'),
        mars: window._sdacs.beyondEarthSetMode('mars'),
        debris: window._sdacs.beyondEarthAddDebris(400, 0.5),
        state: window._sdacs.beyondEarthState,
    })""")
    assert r["moon"] is True
    assert r["state"]["mode"] == "mars"
    assert r["state"]["debrisCount"] >= 1


# Track Δ 양자 (Phase 76-80)
def test_phase76_quantum(page):
    pg, _ = page
    r = pg.evaluate("""({
        qkd: window._sdacs.qkdExchangeKey(512),
        anneal: window._sdacs.annealingSolve(20),
        state: window._sdacs.quantumState,
    })""")
    assert r["qkd"]["keyBits"] == 512
    assert "energy" in r["anneal"]


# Track Λ XR (Phase 81-85)
def test_phase81_xr_frontier(page):
    pg, _ = page
    r = pg.evaluate("""({
        bci: window._sdacs.bciActivate(128),
        olfactory: window._sdacs.olfactorySpray('ocean'),
        state: window._sdacs.xrFrontierState,
    })""")
    assert r["bci"] == 128
    assert r["state"]["scents"] >= 1


# Track Π 경제 (Phase 86-90)
def test_phase86_economy(page):
    pg, _ = page
    r = pg.evaluate("""({
        price: window._sdacs.uamPriceQuote(5, 0.8),
        dao: window._sdacs.daoCreateProposal('Increase nightOps fee', 'proposal text'),
        state: window._sdacs.economyState,
    })""")
    assert r["price"] > 0
    assert r["state"]["daoProposals"] >= 1


# Track Π+ Ultimate (Phase 91-95)
def test_phase91_ultimate(page):
    pg, _ = page
    r = pg.evaluate("""({
        coverage: window._sdacs.ultimateExpandCoverage(25.5),
        un: window._sdacs.ultimateUnProposal('Global Drone Treaty'),
        state: window._sdacs.ultimateState,
    })""")
    assert r["coverage"] == 25.5
    assert r["state"]["unProposals"] >= 1


# Track Ω+ Singularity (Phase 96-100)
def test_phase96_singularity(page):
    pg, _ = page
    r = pg.evaluate("""({
        loops: window._sdacs.singularitySelfImprove(),
        meta: window._sdacs.singularityMetaverseConnect('vrchat'),
        std: window._sdacs.singularityStdProposal('ATC OS v2.0'),
        state: window._sdacs.singularityState,
    })""")
    assert r["loops"] >= 1
    assert r["state"]["version"].startswith("2.0")


def test_no_js_errors_stellar(page):
    pg, errors = page
    benign = ["favicon", "WebGPU", "DevTools", "ws_bridge", "WebSocket",
              "ws://localhost", "ws://127.0.0.1", "ERR_CERT", "ERR_CONNECTION",
              "fonts.googleapis", "AudioContext", "xr"]
    blocking = [e for e in errors if not any(m in e for m in benign)]
    assert not blocking, f"JS errors: {blocking}"
