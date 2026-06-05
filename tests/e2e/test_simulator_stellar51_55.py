"""STELLAR Phase 51-55 — Track Ω (자율 결정) E2E 검증.

Phase 51 LLM Multi-Agent · 52 RLHF · 53 Causal Inference ·
54 Adversarial Robustness · 55 Explainable AI.
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


# Phase 51 LLM Multi-Agent
def test_stellar51_delegate_and_record(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const grp = window._sdacs.stellar51DelegateGroup([1, 2, 3], 'claude-opus-4-7');
            const d1 = window._sdacs.stellar51RecordDecision(grp.id);
            const d2 = window._sdacs.stellar51RecordDecision(grp.id);
            const miss = window._sdacs.stellar51RecordDecision('NO-SUCH');
            return { provider: grp.llmProvider, n: grp.droneIds.length, d1, d2, miss };
        }
    """)
    assert r["provider"] == "claude-opus-4-7"
    assert r["n"] == 3
    assert r["d1"] == 1 and r["d2"] == 2
    assert r["miss"] is None


# Phase 52 RLHF
def test_stellar52_reward_model_learns_preference(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            // A=[1,0,0] 를 B=[0,0,0] 보다 선호 → feature0 가중치 상승
            window._sdacs.stellar52AddFeedback([1, 0, 0], [0, 0, 0], 'a');
            window._sdacs.stellar52AddFeedback([1, 0, 0], [0, 0, 0], 'a');
            const w = window._sdacs.stellar52Weights;
            const rPref = window._sdacs.stellar52RewardModel([1, 0, 0]);
            const rOther = window._sdacs.stellar52RewardModel([0, 0, 0]);
            return { w0: w[0], rPref, rOther };
        }
    """)
    assert r["w0"] > 0
    assert r["rPref"] > r["rOther"]


# Phase 53 Causal Inference
def test_stellar53_intervene_and_ate(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const sep = window._sdacs.stellar53Intervene('separation', 1);
            const spd = window._sdacs.stellar53Intervene('speed', 1);
            const ate = window._sdacs.stellar53ATE('separation');
            const bad = window._sdacs.stellar53Intervene('nope', 1);
            return { sep, spd, ate, bad };
        }
    """)
    # 간격 증가 → 충돌위험 감소(음수), 속도 증가 → 위험 증가(양수)
    assert r["sep"] < 0
    assert r["spd"] > 0
    assert r["ate"] == r["sep"]
    assert r["bad"] is None


# Phase 54 Adversarial Robustness
def test_stellar54_attack_and_defend(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const clean = [1, 1, 1, 1, 1];
            const adv = window._sdacs.stellar54Attack(clean, 'fgsm', 0.2);
            const pgd = window._sdacs.stellar54Attack(clean, 'pgd', 0.2);
            const defended = window._sdacs.stellar54Defend(adv);
            const stats = window._sdacs.stellar54Stats;
            const advDist = adv.reduce((a, x, i) => a + Math.abs(x - clean[i]), 0);
            const defDist = defended.reduce((a, x, i) => a + Math.abs(x - clean[i]), 0);
            const pgdDist = pgd.reduce((a, x, i) => a + Math.abs(x - clean[i]), 0);
            return { advDist, defDist, pgdDist, attacks: stats.attacks, defenses: stats.defenses };
        }
    """)
    assert r["advDist"] > 0
    # PGD(다단계)가 FGSM(단일)보다 섭동 크기 큼
    assert r["pgdDist"] > r["advDist"]
    # 방어(평활화)가 adversarial 거리 감소
    assert r["defDist"] < r["advDist"]
    assert r["attacks"] >= 2 and r["defenses"] >= 1


# Phase 55 Explainable AI
def test_stellar55_additive_attribution(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const exp = window._sdacs.stellar55Explain([2, 3, 4], [1, 2, 0.5]);
            const last = window._sdacs.stellar55LastExplanation;
            return { contributions: exp.contributions, prediction: exp.prediction, last: last.prediction };
        }
    """)
    # contribution_i = w_i * x_i = [2, 6, 2], sum=10
    assert r["contributions"] == [2, 6, 2]
    assert r["prediction"] == 10
    assert r["last"] == 10


def test_no_js_errors_stellar51_55(page):
    pg, errors = page
    benign = ["favicon", "WebGPU", "DevTools", "ws_bridge", "WebSocket",
              "ws://localhost", "ws://127.0.0.1", "ERR_CERT", "ERR_CONNECTION",
              "fonts.googleapis", "AudioContext", "xr"]
    blocking = [e for e in errors if not any(m in e for m in benign)]
    assert not blocking, f"JS errors: {blocking}"
