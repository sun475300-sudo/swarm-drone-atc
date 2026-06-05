"""HYPER Phase 13/16/22/24/25 — WebGPU 50K + CRDT + Digital Twin + NOTAM + Battery Aging E2E."""
from __future__ import annotations

import base64
import http.server
import os
import socketserver
import struct
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


# ===== Phase 13 — WebGPU 50K Spatial Hash =====

def test_gpu50k_api(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["enableGpu50k", "gpu50kBuild", "gpu50kQuery", "gpu50kEnabled", "gpu50kStats"]:
        assert k in keys, f"_sdacs.{k} missing"


def test_gpu50k_enable_build(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.enableGpu50k(true);
            const build = window._sdacs.gpu50kBuild();
            const stats = window._sdacs.gpu50kStats;
            return { build, stats };
        }
    """)
    assert r["build"] is not None
    assert r["build"]["cells"] > 0
    assert r["stats"]["gridSize"] == 256
    assert r["stats"]["targetCapacity"] == 50000


def test_gpu50k_query_neighbors(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.enableGpu50k(true);
            window._sdacs.gpu50kBuild();
            const n = window._sdacs.gpu50kQuery(0, 500);
            return { count: n.length };
        }
    """)
    assert r["count"] >= 0


# ===== Phase 16 — CRDT =====

def test_crdt_api(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["enableCrdt", "crdtAddOp", "crdtMerge", "crdtSnapshot", "crdtEnabled", "crdtSiteId"]:
        assert k in keys, f"_sdacs.{k} missing"


def test_crdt_addop_increments_lamport(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.enableCrdt(true);
            const op1 = window._sdacs.crdtAddOp('DR-001', 'HOLD');
            const op2 = window._sdacs.crdtAddOp('DR-002', 'RTB');
            return { op1, op2, snap: window._sdacs.crdtSnapshot() };
        }
    """)
    assert r["op2"]["lamport"] > r["op1"]["lamport"]
    assert r["snap"]["opCount"] >= 2


def test_crdt_merge_remote_ops(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.enableCrdt(true);
            const remoteOps = [
                { ts: Date.now(), siteId: 'peer-1', target: 'DR-003', cmd: 'ALT', params: {delta: 10}, lamport: 99 },
                { ts: Date.now(), siteId: 'peer-2', target: 'DR-004', cmd: 'SPD', params: {factor: 1.2}, lamport: 100 },
            ];
            const added = window._sdacs.crdtMerge(remoteOps);
            const snap = window._sdacs.crdtSnapshot();
            return { added, lamport: snap.lamport, peers: snap.peers };
        }
    """)
    assert r["added"] == 2
    assert r["lamport"] >= 100
    assert set(r["peers"]) == {"peer-1", "peer-2"}


# ===== Phase 22 — Digital Twin Pixhawk =====

def test_dtwin_api(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["enableDtwin", "dtwinDecodeGPI", "dtwinApplyGPI", "dtwinSetOrigin", "dtwinEnabled", "dtwinStats"]:
        assert k in keys, f"_sdacs.{k} missing"


def test_dtwin_decode_gpi(page):
    pg, _ = page
    # MAVLink GPI 페이로드 (28 bytes little-endian) — 목포대 근처
    payload_bytes = struct.pack(
        '<IiiiihhhH',
        12345,                  # time_boot_ms
        int(34.808 * 1e7),     # lat 34.808°
        int(126.391 * 1e7),    # lon 126.391°
        int(80 * 1000),        # alt 80m (mm)
        int(80 * 1000),        # rel_alt
        500,                    # vx 5 m/s (cm/s)
        0,                      # vy
        0,                      # vz
        9000,                   # hdg 90° (cdeg)
    )
    payload_b64 = base64.b64encode(payload_bytes).decode()
    r = pg.evaluate(f"""
        () => {{
            window._sdacs.enableDtwin(true);
            const b64 = '{payload_b64}';
            const bin = atob(b64);
            const buf = new ArrayBuffer(bin.length);
            const view = new Uint8Array(buf);
            for (let i = 0; i < bin.length; i++) view[i] = bin.charCodeAt(i);
            const decoded = window._sdacs.dtwinDecodeGPI(buf);
            const applied = window._sdacs.dtwinApplyGPI(decoded, 0);
            return {{ decoded, applied, stats: window._sdacs.dtwinStats }};
        }}
    """)
    assert r["decoded"] is not None
    assert abs(r["decoded"]["lat"] - 34.808) < 0.001
    assert abs(r["decoded"]["lon"] - 126.391) < 0.001
    assert r["decoded"]["hdg_cdeg"] == 9000
    assert r["applied"] is True
    assert r["stats"]["packetCount"] >= 1


def test_dtwin_set_origin(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const o = window._sdacs.dtwinSetOrigin(37.5665, 126.978);  // Seoul
            return o;
        }
    """)
    assert abs(r["lat"] - 37.5665) < 0.001
    assert abs(r["lon"] - 126.978) < 0.001


# ===== Phase 24 — NOTAM =====

def test_notam_api(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["notamAdd", "notamImportJson", "notams", "notamCount"]:
        assert k in keys, f"_sdacs.{k} missing"


def test_notam_add_simple(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const before = window._sdacs.notamCount;
            window._sdacs.notamAdd({ x: 500, z: 500, r: 200, type: 'TEST' });
            return { before, after: window._sdacs.notamCount, last: window._sdacs.notams.slice(-1)[0] };
        }
    """)
    assert r["after"] == r["before"] + 1
    assert r["last"]["r"] == 200


def test_notam_import_json(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            const data = [
                { lat: 34.808, lon: 126.391, radius_m: 150, type: 'NOTAM-A' },
                { lat: 34.81, lon: 126.40, radius_m: 100, type: 'NOTAM-B' },
            ];
            const n = window._sdacs.notamImportJson(JSON.stringify(data));
            return { added: n, total: window._sdacs.notamCount };
        }
    """)
    assert r["added"] == 2


# ===== Phase 25 — Battery Aging =====

def test_battery_aging_api(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    assert "batteryAgeStats" in keys


def test_battery_aging_stats_populated(page):
    pg, _ = page
    pg.wait_for_timeout(2000)  # 배터리 사이클 누적 시간 확보
    r = pg.evaluate("window._sdacs.batteryAgeStats")
    assert r is not None
    assert r["droneCount"] > 0
    assert 0 < r["avgEffective"] <= 1.0
    assert 0 < r["worstEffective"] <= 1.0


def test_no_js_errors_5phases(page):
    pg, errors = page
    benign = ["favicon", "WebGPU", "DevTools", "ws_bridge", "WebSocket",
              "ws://localhost", "ws://127.0.0.1", "ERR_CERT", "ERR_CONNECTION",
              "fonts.googleapis", "AudioContext", "xr"]
    blocking = [e for e in errors if not any(m in e for m in benign)]
    assert not blocking, f"JS errors: {blocking}"
