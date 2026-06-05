"""HYPER Phase 32-50 — 마지막 19 Phase 일괄 검증 E2E."""
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
        pg.evaluate("window._sdacs.startSim()")
        try:
            pg.wait_for_function("window._sdacs.airborne >= 2", timeout=15000)
        except Exception:
            pass
        pg.wait_for_timeout(700)
        yield pg, errors
        ctx.close()
        browser.close()


# Phase 32 Satellite
def test_satellite_init_starlink(page):
    pg, _ = page
    r = pg.evaluate("""({
        cnt: window._sdacs.satelliteInit('starlink'),
        constellation: window._sdacs.satelliteConstellation,
        visible: window._sdacs.satelliteVisibleAt(37.5, 127),
    })""")
    assert r["cnt"] == 24
    assert r["constellation"] == "starlink"


def test_satellite_oneweb(page):
    pg, _ = page
    r = pg.evaluate("window._sdacs.satelliteInit('oneweb')")
    assert r == 18


def test_satellite_handoff(page):
    pg, _ = page
    r = pg.evaluate("window._sdacs.satelliteHandoff()")
    assert r >= 1


# Phase 33 UUV
def test_uuv_add_and_budget(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.uuvAdd(100, 200, 30);
            window._sdacs.uuvAdd(-100, 50, 80);
            const b = window._sdacs.uuvAcousticBudget();
            return { count: window._sdacs.uuvVehicles.length, budget: b };
        }
    """)
    assert r["count"] == 2
    assert r["budget"]["totalKbps"] == 2.0


# Phase 34 Sensor Fusion
def test_sensor_fusion_toggle(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const a = window._sdacs.sensorFusionToggle('lidar', false);
            const b = window._sdacs.sensorFusionEffectiveNoise();
            window._sdacs.sensorFusionSetFilter('particle');
            return { lidar: a, noise: b, state: window._sdacs.sensorFusionState };
        }
    """)
    assert r["lidar"] is False
    assert r["state"]["filter"] == "particle"
    assert r["noise"] > 0


# Phase 35 MEC
def test_mec_add_and_assign(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.mecAdd(0, 0, 100, 5);
            window._sdacs.mecAdd(500, 500, 80, 7);
            const id = window._sdacs.selectDrone(0);
            const node = window._sdacs.mecAssign(id, 500);
            return { mecCount: window._sdacs.mecNodes.length, assigned: node, workloads: window._sdacs.mecWorkloads.length };
        }
    """)
    assert r["mecCount"] == 2
    assert r["assigned"] is not None


# Phase 36 Federated Learning
def test_fed_learn_round(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const m1 = window._sdacs.fedLearnRound(50, 0.4);
            const m2 = window._sdacs.fedLearnRound(60, 0.35);
            return { m1, m2, state: window._sdacs.fedLearnState, hist: window._sdacs.fedLearnHistory.length };
        }
    """)
    assert r["state"]["round"] == 2
    assert r["state"]["epsilon"] < 1.0  # 소진됨
    assert r["hist"] == 2


# Phase 37 Multi-Domain
def test_multi_domain_handoff(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.ugvAdd(100, 200, 'GROUND-1');
            window._sdacs.multiDomainHandoff('DR-001', 'air', 'ground', 'M-001');
            window._sdacs.multiDomainHandoff('DR-002', 'ground', 'maritime', 'M-002');
            return { ugvs: window._sdacs.ugvs.length, log: window._sdacs.multiDomainHandoffLog.length };
        }
    """)
    assert r["ugvs"] == 1
    assert r["log"] >= 2


# Phase 38 Realistic Audio (Doppler)
def test_audio_doppler(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.audioSetListener(0, 0);
            const f = window._sdacs.audioDopplerShift(0, 440);
            return { listenerSet: window._sdacs.audioEngineState.listenerX, doppler: f };
        }
    """)
    # Doppler shift는 정수가 아닐 수 있으나 numeric
    assert isinstance(r["doppler"], (int, float))


# Phase 39 Photogrammetry
def test_photogrammetry_import(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.photogrammetryImport('서울 시청', 2.0, 'https://example.com/scene.glb');
            return { count: window._sdacs.photogrammetryScenes.length };
        }
    """)
    assert r["count"] == 1


# Phase 40 Esports
def test_esports_players(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const p1 = window._sdacs.esportsAddPlayer('Alice', 'defender');
            const p2 = window._sdacs.esportsAddPlayer('Bob', 'attacker');
            window._sdacs.esportsScore(p1.id, 50);
            window._sdacs.esportsScore(p2.id, 30);
            return { players: window._sdacs.esportsPlayers.length, aliceScore: window._sdacs.esportsPlayers[0].score };
        }
    """)
    assert r["players"] == 2
    assert r["aliceScore"] == 50


# Phase 41 Procedural City
def test_proc_city_generate(page):
    pg, _ = page
    r = pg.evaluate("""({
        cnt: window._sdacs.procCityGenerate(2, 0.5),
        actual: window._sdacs.procCityBuildingCount,
    })""")
    assert r["cnt"] > 50
    assert r["actual"] == r["cnt"]


# Phase 42 Eye Tracking
def test_eye_track_heatmap(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            for (let i = 0; i < 20; i++) window._sdacs.eyeTrackAdd(Math.random() * 1400, Math.random() * 900);
            const gridSize = window._sdacs.eyeTrackBuildHeatmap();
            return { points: window._sdacs.eyeTrackPointCount, grid: gridSize };
        }
    """)
    assert r["points"] == 20
    assert r["grid"] == 32 * 32


# Phase 43 Voice Macros
def test_voice_macro_define_execute(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.voiceMacroDefine('alpha_pattern', [
                { type: 'atc', target: 'DR-001', cmd: 'HOLD' },
                { type: 'atc', target: 'DR-002', cmd: 'RTB' },
            ]);
            const res = window._sdacs.voiceMacroExecute('alpha_pattern');
            return { macros: window._sdacs.voiceMacros, res };
        }
    """)
    assert 'alpha_pattern' in r["macros"]
    assert r["res"]["name"] == "alpha_pattern"


# Phase 44 Time Compression
def test_time_compress(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const a = window._sdacs.timeCompressSet(10);
            const b = window._sdacs.timeCompressSet(99999);  // clamp 10000
            const c = window._sdacs.timeCompressReset();
            return { a, b, c };
        }
    """)
    assert r["a"] == 10
    assert r["b"] == 10000
    assert r["c"] == 1


# Phase 45 HITL Cluster
def test_hitl_cluster(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.hitlAdd('HITL-PX4-1', 'Pixhawk-1');
            window._sdacs.hitlAdd('HITL-PX4-2', 'Pixhawk-2');
            const ok = window._sdacs.hitlConnect('HITL-PX4-1');
            return { ok, nodes: window._sdacs.hitlNodes.length };
        }
    """)
    assert r["ok"] is True
    assert r["nodes"] == 2


# Phase 46 National Airspace
def test_national_as_korea(page):
    pg, _ = page
    r = pg.evaluate("""({
        cnt: window._sdacs.nationalASInitKorea(),
        airports: window._sdacs.nationalASAirports.map(a => a.icao),
    })""")
    assert r["cnt"] == 6
    assert "RKSI" in r["airports"]
    assert "RKPC" in r["airports"]


# Phase 47 Climate
def test_climate_score(page):
    pg, _ = page
    pg.evaluate("window._sdacs.enableClimate(true)")
    pg.wait_for_timeout(1500)
    r = pg.evaluate("window._sdacs.climateScore")
    assert r is not None
    # 시간이 지나면 누적
    assert r["flightHours"] >= 0
    assert r["co2Kg"] >= 0


# Phase 48 Cross-Border
def test_cross_border_transit(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.crossBorderTransit('DR-007', 'KR', 'JP', true);
            window._sdacs.crossBorderTransit('DR-013', 'JP', 'KR', false);
            return window._sdacs.crossBorderTransitsLog;
        }
    """)
    assert len(r) >= 2
    assert r[0]["fromCountry"] == "KR"
    assert r[1]["approved"] is False


# Phase 49 Planetary
def test_planetary_set_body(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const r1 = window._sdacs.planetarySetBody('moon');
            const s1 = window._sdacs.planetaryState;
            const r2 = window._sdacs.planetarySetBody('mars');
            const s2 = window._sdacs.planetaryState;
            window._sdacs.planetarySetBody('earth');
            return { r1, s1, r2, s2 };
        }
    """)
    assert r["s1"]["gravity"] < 2
    assert r["s2"]["gravity"] < 4 and r["s2"]["gravity"] > 3


# Phase 50 Public Demo
def test_public_demo_leaderboard(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.publicDemoLeaderboardAdd('Alice', 100);
            window._sdacs.publicDemoLeaderboardAdd('Bob', 200);
            window._sdacs.publicDemoLeaderboardAdd('Carol', 150);
            const lb = window._sdacs.publicDemoLeaderboard;
            const dc = window._sdacs.publicDemoDailyChallenge();
            return { topScore: lb[0].score, topName: lb[0].name, dailyDate: dc.date };
        }
    """)
    assert r["topScore"] == 200
    assert r["topName"] == "Bob"
    assert len(r["dailyDate"]) == 10


def test_no_js_errors_phase32_50(page):
    pg, errors = page
    benign = ["favicon", "WebGPU", "DevTools", "ws_bridge", "WebSocket",
              "ws://localhost", "ws://127.0.0.1", "ERR_CERT", "ERR_CONNECTION",
              "fonts.googleapis", "AudioContext", "xr"]
    blocking = [e for e in errors if not any(m in e for m in benign)]
    assert not blocking, f"JS errors: {blocking}"
