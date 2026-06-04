"""Phase 5 MIS (임무 계획) + Phase 7 ANA (분석 강화) + Phase 9 MOB (모바일/PWA) Playwright 스모크."""
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
    handler = http.server.SimpleHTTPRequestHandler

    class Quiet(handler):
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
            pg.wait_for_function("window._sdacs.airborne >= 1", timeout=20000)
        except Exception:
            pass
        pg.wait_for_timeout(800)
        yield pg, errors
        ctx.close()
        browser.close()


# ===== Phase 5 MIS =====

def test_mis_api_exposed(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["missionAdd", "missionTemplate", "missionAssignTemplate", "missionClearAll", "missions"]:
        assert k in keys, f"_sdacs.{k} missing"


def test_mis_template_generates_waypoints(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const wps_search = window._sdacs.missionTemplate('search_grid', 0, 0);
            const wps_orbit = window._sdacs.missionTemplate('recon_orbit', 0, 0);
            const wps_deliv = window._sdacs.missionTemplate('delivery', 100, 200);
            return {
                search: wps_search.length,
                orbit: wps_orbit.length,
                deliv: wps_deliv.length,
                deliv_pt: wps_deliv[0],
            };
        }
    """)
    assert r["search"] == 16, f"search_grid should be 4x4=16 wp, got {r['search']}"
    assert r["orbit"] == 8
    assert r["deliv"] == 1
    assert r["deliv_pt"]["x"] == 100
    assert r["deliv_pt"]["z"] == 200


def test_mis_assign_template(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.missionClearAll();
            window._sdacs.selectDrone(0);
            const id = window._sdacs.getSelected().id;
            const m = window._sdacs.missionAssignTemplate(id, 'recon_orbit');
            return {
                ok: !!m,
                count: window._sdacs.missions.length,
                droneId: window._sdacs.missions[0]?.droneId,
                wpCount: window._sdacs.missions[0]?.wpCount,
            };
        }
    """)
    assert r["ok"]
    assert r["count"] >= 1
    assert r["wpCount"] == 8


def test_mis_clear_all(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.selectDrone(0);
            window._sdacs.missionAssignTemplate(window._sdacs.getSelected().id, 'delivery');
            const before = window._sdacs.missions.length;
            window._sdacs.missionClearAll();
            const after = window._sdacs.missions.length;
            return { before, after };
        }
    """)
    assert r["before"] >= 1
    assert r["after"] == 0


def test_mis_ui_present(page):
    pg, _ = page
    r = pg.evaluate("""
        () => ({
            tmpl: !!document.getElementById('mis-template'),
            assign: !!document.getElementById('btn-mis-assign'),
            clear: !!document.getElementById('btn-mis-clear'),
            list: !!document.getElementById('mis-list'),
        })
    """)
    for k, v in r.items():
        assert v, f"MIS UI element missing: {k}"


# ===== Phase 7 ANA =====

def test_ana_api_exposed(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["setAnaHeatmap", "anaHeatmap", "anaKpiWindow", "exportLatexKpi"]:
        assert k in keys, f"_sdacs.{k} missing"


def test_ana_heatmap_toggle(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const off0 = window._sdacs.anaHeatmap;
            const on = window._sdacs.setAnaHeatmap(true);
            const off = window._sdacs.setAnaHeatmap(false);
            return { off0, on, off };
        }
    """)
    assert r["off0"] is False
    assert r["on"] is True
    assert r["off"] is False


def test_ana_kpi_window_accumulates(page):
    pg, _ = page
    pg.wait_for_timeout(3000)  # 0.1s 간격으로 ≥ 3개 sample 누적
    r = pg.evaluate("window._sdacs.anaKpiWindow")
    assert len(r["time"]) >= 3, f"KPI window should accumulate samples, got {len(r['time'])}"
    assert all(0 <= v <= 100 for v in r["cr"]), "cr must be 0-100"


def test_ana_ui_present(page):
    pg, _ = page
    r = pg.evaluate("""
        () => ({
            heatmap: !!document.getElementById('tg-ana-heatmap'),
            latex: !!document.getElementById('btn-ana-latex'),
            blame: !!document.getElementById('tg-ana-blame'),
            blame_list: !!document.getElementById('ana-blame-list'),
        })
    """)
    for k, v in r.items():
        assert v, f"ANA UI element missing: {k}"


# ===== Phase 7 ANA-5 충돌 책임 분석 =====

def test_ana_blame_api_exposed(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["setAnaBlame", "anaBlame", "anaBlameCount", "anaBlameActive",
              "anaBlameRecords", "resetAnaBlame"]:
        assert k in keys, f"_sdacs.{k} missing"


def test_ana_blame_default_off(page):
    pg, _ = page
    assert pg.evaluate("window._sdacs.anaBlame") is False
    assert pg.evaluate("window._sdacs.setAnaBlame(true)") is True
    assert pg.evaluate("document.getElementById('tg-ana-blame').checked") is True
    pg.evaluate("window._sdacs.setAnaBlame(false)")


def test_ana_blame_records_responsibility(page):
    """분리위반(충돌·근접) 발생 시 양보 위반 드론을 판정·기록하고 발광 링을 표시한다."""
    pg, _ = page
    # 고밀도 시나리오로 전환해 분리위반을 유도
    pg.evaluate("""
        () => {
            window._sdacs.resetAnaBlame();
            window._sdacs.setAnaBlame(true);
            const s = document.getElementById('scenario');
            if (s) { s.value = 'high_density'; s.dispatchEvent(new Event('change')); }
            window._sdacs.setAnaBlame(true);
            window._sdacs.startSim();
        }
    """)
    pg.wait_for_function("window._sdacs.anaBlameCount > 0", timeout=30000)
    rec = pg.evaluate("""
        () => ({
            count: window._sdacs.anaBlameCount,
            active: window._sdacs.anaBlameActive,
            sample: window._sdacs.anaBlameRecords.slice(-1)[0],
        })
    """)
    assert rec["count"] > 0, "책임 기록이 누적되어야 함"
    assert rec["active"] > 0, "책임 드론 발광 링이 활성이어야 함"
    s = rec["sample"]
    assert s and "failed to yield" in s["msg"], f"메시지 포맷 불일치: {s}"
    assert s["responsibleId"] and s["otherId"], "책임/상대 드론 ID 기록 필요"
    assert s["responsibleId"] != s["otherId"], "책임/상대는 서로 다른 드론"


def test_ana_blame_reset_clears(page):
    pg, _ = page
    after = pg.evaluate("window._sdacs.resetAnaBlame()")
    assert after == 0
    assert pg.evaluate("window._sdacs.anaBlameCount") == 0


# ===== Phase 9 MOB =====

def test_mob_api_exposed(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["isMobile", "mobileLOD", "applyMobileLOD"]:
        assert k in keys, f"_sdacs.{k} missing"


def test_mob_viewport_meta(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const m = document.querySelector('meta[name="viewport"]');
            const tm = document.querySelector('meta[name="theme-color"]');
            return { vp: m?.content || '', theme: tm?.content || '' };
        }
    """)
    assert "viewport-fit" in r["vp"]
    assert r["theme"] == "#03050a"


def test_mob_manifest_link(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const l = document.querySelector('link[rel="manifest"]');
            return l?.href || '';
        }
    """)
    assert "manifest" in r, f"manifest link missing: {r}"


def test_mob_manifest_served(page, http_server):
    pg, _ = page
    r = pg.evaluate(f"""
        async () => {{
            const resp = await fetch('{http_server}/manifest.webmanifest');
            if (!resp.ok) return {{ ok: false, status: resp.status }};
            const json = await resp.json();
            return {{ ok: true, name: json.name, display: json.display }};
        }}
    """)
    assert r["ok"], f"manifest fetch failed: {r}"
    assert r["name"].startswith("SDACS")
    assert r["display"] == "standalone"


def test_mob_sw_served(page, http_server):
    pg, _ = page
    r = pg.evaluate(f"""
        async () => {{
            const resp = await fetch('{http_server}/sdacs-sw.js');
            return {{ ok: resp.ok, status: resp.status }};
        }}
    """)
    assert r["ok"], f"Service Worker file not served: {r}"


def test_no_js_errors_mis_ana_mob(page):
    pg, errors = page
    benign = ["favicon", "WebGPU", "DevTools", "ws_bridge", "WebSocket",
              "ws://localhost", "ws://127.0.0.1", "ERR_CERT", "ERR_CONNECTION",
              "fonts.googleapis", "AudioContext"]
    blocking = [e for e in errors if not any(m in e for m in benign)]
    assert not blocking, f"JS errors: {blocking}"
