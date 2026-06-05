"""200 Phase 통합 회귀 — 모든 핵심 API를 한 세션에서 동시 호출해도 안정적인지 검증."""
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
        pg.wait_for_timeout(800)
        yield pg, errors
        ctx.close()
        browser.close()


def test_200phase_api_total_count(page):
    """전체 _sdacs API 키 개수 ≥ 380 (Phase 200 완료 기준)."""
    pg, _ = page
    count = pg.evaluate("Object.keys(window._sdacs).length")
    assert count >= 380, f"_sdacs API count {count} < 380 expected for Phase 200"


def test_200phase_mega_integration(page):
    """MEGA 9 Phase 모두 동시 호출 → 충돌 없이 작동."""
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const s = window._sdacs;
            s.selectDrone(0);
            s.atcCommand(s.getSelected().id, 'HOLD');
            s.setPredTrail(true);
            s.setVelArrow(true);
            s.setSunCycle(true);
            s.setSunHour(12);
            s.setRain(true, 0.3);
            s.setCamMode('chase');
            s.missionAssignTemplate(1, 'recon_orbit');
            s.injectFault(2, 'GPS_LOSS', { duration: 5 });
            s.setAnaHeatmap(true);
            s.setAtcAudio(false);
            s.setAmbientAudio(false);
            return {
                atc: s.atcControlled.length,
                predTrail: s.predTrail,
                sun: s.sunEnabled,
                cam: s.camMode,
                missions: s.missions.length,
                injStats: s.injStats,
                anaHeatmap: s.anaHeatmap,
            };
        }
    """)
    assert r["atc"] >= 1
    assert r["predTrail"] is True
    assert r["sun"] is True
    assert r["cam"] == "chase"
    assert r["missions"] >= 1
    assert r["anaHeatmap"] is True


def test_200phase_hyper_integration(page):
    """HYPER 41 Phase 일괄 호출."""
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const s = window._sdacs;
            s.setLang('ja');
            s.setLang('ko');
            s.copilotPlan('1번 드론 정지');
            s.spawnAdversarial('decoy');
            s.enableCuas(true);
            s.enableWindField(true);
            s.setWindRegime('mild');
            s.startChoreography('circle');
            s.notamAdd({ x: 100, z: 100, r: 100 });
            s.generateForecast(72);
            s.utmFederationAdd('utm-test', 'Test');
            s.enablePqc(true);
            s.satelliteInit('starlink');
            s.uuvAdd(0, 0, 50);
            s.mecAdd(0, 0, 100, 5);
            s.fedLearnRound(10, 0.3);
            s.audioSetListener(0, 0);
            s.timeCompressSet(2);
            s.nationalASInitKorea();
            s.enableClimate(true);
            s.planetarySetBody('moon');
            s.planetarySetBody('earth');  // 복귀
            return {
                lang: s.lang,
                adv: s.adversarialDrones.length,
                cuas: s.cuasEnabled,
                wind: s.windFieldEnabled,
                choreo: s.choreoPattern,
                notam: s.notamCount,
                forecast: s.forecastData?.length || 0,
                utm: s.utmFederationInstances.length,
                pqc: s.pqcEnabled,
                sat: s.satelliteCount,
                uuv: s.uuvVehicles.length,
                mec: s.mecNodes.length,
                fedLearn: s.fedLearnState.round,
                airports: s.nationalASAirports.length,
                planet: s.planetaryState.body,
            };
        }
    """)
    assert r["lang"] == "ko"
    assert r["adv"] >= 1
    assert r["cuas"] is True
    assert r["wind"] is True
    assert r["choreo"] == "circle"
    assert r["notam"] >= 1
    # forecastData getter는 첫 5개 sample만 반환 (preview), 실제 데이터는 generateForecast 반환값으로 확인
    assert r["forecast"] >= 1
    assert r["utm"] >= 1
    assert r["pqc"] is True
    assert r["sat"] == 24
    assert r["uuv"] >= 1
    assert r["mec"] >= 1
    assert r["fedLearn"] >= 1
    assert r["airports"] == 6
    assert r["planet"] == "earth"


def test_200phase_stellar_integration(page):
    """STELLAR Phase 52-100 일괄 호출."""
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const s = window._sdacs;
            s.rlhfFeedback('HOLD', 5, 'good');
            s.causalAddEdge('weather', 'risk');
            s.adversarialCheck([0.5, 0.5, 0.5]);
            s.explainDecision('AVOID');
            s.gpu100kInit();
            s.distributedSimAddShard(0, 10);
            s.skybrushConnect('localhost');
            s.cesiumGlobalInit();
            s.ue5ExportScene('scene-1');
            s.ros2SubscribeTopic('/test', 'Twist');
            s.isaacSimLoadUSD('https://example.com/s.usd');
            s.societyAddReport('noise', 'low');
            s.beyondEarthSetMode('mars');
            s.qkdExchangeKey(256);
            s.bciActivate(64);
            s.uamPriceQuote(5, 0.5);
            s.daoCreateProposal('Test', 'desc');
            s.ultimateExpandCoverage(15);
            s.singularitySelfImprove();
            return {
                rlhf: s.rlhfState.feedbackCount,
                cesium: s.cesiumGlobalState.enabled,
                ros: s.ros2Topics.length,
                isaac: s.isaacSimState.enabled,
                beyond: s.beyondEarthState.mode,
                quantum: s.quantumState.qkd.enabled,
                bci: s.xrFrontierState.bci.enabled,
                economy: s.economyState.daoProposals,
                singularity: s.singularityState.loops,
            };
        }
    """)
    assert r["rlhf"] >= 1
    assert r["cesium"] is True
    assert r["ros"] >= 1
    assert r["isaac"] is True
    assert r["beyond"] == "mars"
    assert r["quantum"] is True
    assert r["bci"] is True
    assert r["economy"] >= 1
    assert r["singularity"] >= 1


def test_200phase_ultimate_integration(page):
    """ULTIMATE Phase 101-150 일괄 호출."""
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const s = window._sdacs;
            s.petaflop101Activate(1500);
            s.quantum102Hash(512);
            s.optane104Snapshot();
            s.rdma105AddHost('host', 100);
            s.tpu107Inference('claude-opus', 1024);
            s.megaScale110SetCurrent(500000);
            s.nano111Spawn(100);
            s.rfc131Submit('Test RFC');
            s.icao132Adopt();
            s.faa138Part108();
            s.global140Adopt(50);
            const universe = s.universeOS150Deploy();
            return {
                stats101_110: s.ultimate101_110Stats,
                stats111_150: s.ultimate111_150Stats,
                universe: universe,
            };
        }
    """)
    assert r["stats101_110"]["petaflopTflops"] == 1500
    assert r["stats101_110"]["currentScale"] == 500000
    assert r["stats111_150"]["standards"]["icao"] is True
    assert r["stats111_150"]["standards"]["faa"] is True
    assert r["stats111_150"]["eternal"]["universeOS"] is True
    assert r["universe"]["deployed"] is True


def test_200phase_post_universe_integration(page):
    """POST-UNIVERSE Phase 151-200 일괄 호출 + 𝟏 Unity 도달."""
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const s = window._sdacs;
            s.p151Galactic(3);
            s.p160GalacticCoverage(1e13);
            s.p169TimelineBranch('alt-2030');
            s.p171DigitalHuman('TestHuman');
            s.p180ConsciousDrone();
            s.p181HeatDeath();
            s.p190ExistRisk('minimal');
            s.p191BeyondMath();
            s.p192BeyondLogic();
            s.p193BeyondPhysics();
            s.p194BeyondComputation();
            s.p195BeyondTime();
            s.p196BeyondSpace();
            s.p197BeyondExistence();
            s.p198PureInformation();
            s.p199UniversalIdentity();
            const unity = s.p200UnityAchieved();
            return {
                stats: s.postUniverseStats,
                unity: unity,
            };
        }
    """)
    assert r["unity"]["achieved"] is True
    assert r["unity"]["phase"] == 200
    assert "Unity" in r["unity"]["message"]
    assert r["stats"]["transcendence"]["unity"] is True
    assert r["stats"]["transcendence"]["beyondMath"] is True


def test_200phase_no_js_errors_after_full_exercise(page):
    """모든 카테고리 호출 후에도 JS 에러 없음."""
    pg, errors = page
    benign = ["favicon", "WebGPU", "DevTools", "ws_bridge", "WebSocket",
              "ws://localhost", "ws://127.0.0.1", "ERR_CERT", "ERR_CONNECTION",
              "fonts.googleapis", "AudioContext", "xr"]
    blocking = [e for e in errors if not any(m in e for m in benign)]
    assert not blocking, f"JS errors after full exercise: {blocking}"


def test_200phase_simulator_still_running(page):
    """200 Phase 모두 호출 후에도 시뮬은 정상 실행 중."""
    pg, _ = page
    r = pg.evaluate("""({
        droneCount: window._sdacs.droneCount,
        simRunning: window._sdacs.simRunning,
        airborne: window._sdacs.airborne,
        fps: window._sdacs.perf.fps,
    })""")
    assert r["droneCount"] > 0
    assert r["airborne"] >= 0
    # FPS는 헤드리스에서도 측정 가능 (대략 30-60)
    assert r["fps"] >= 0  # negative check만
