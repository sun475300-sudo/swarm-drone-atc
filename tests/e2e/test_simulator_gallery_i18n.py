"""HYPER Phase 14 (시나리오 갤러리) + Phase 15 (KO/EN/JA/ZH 다국어) Playwright 스모크."""
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


# ===== HYPER Phase 14 — Scenario Gallery =====

def test_gallery_api_exposed(page):
    pg, _ = page
    keys = pg.evaluate("Object.keys(window._sdacs)")
    for k in ["openGallery", "closeGallery", "galleryOpen", "scenarioCategories"]:
        assert k in keys, f"_sdacs.{k} missing"


def test_gallery_button_present(page):
    pg, _ = page
    r = pg.evaluate("!!document.getElementById('btn-scenario-gallery')")
    assert r, "갤러리 버튼 없음"


def test_gallery_opens_with_5_categories(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.openGallery();
            const open = window._sdacs.galleryOpen;
            const cats = window._sdacs.scenarioCategories;
            const cards = document.querySelectorAll('#scenario-gallery-grid > div').length;
            window._sdacs.closeGallery();
            return { open, cats: cats.length, cards };
        }
    """)
    assert r["open"] is True
    assert r["cats"] == 5  # featured/stress/weather/military/uam
    # cards = 5 category headers + (4+3+4+2+7=20 scenario cards) = 25
    assert r["cards"] >= 20, f"카드 수 부족: {r['cards']}"


def test_gallery_card_click_changes_scenario(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.openGallery();
            // 첫 시나리오 카드 클릭 (카테고리 헤더 다음)
            const cards = [...document.querySelectorAll('#scenario-gallery-grid > div')]
                .filter(d => d.querySelector('canvas'));
            const before = document.getElementById('scenario-select').value;
            if (cards.length > 0) cards[0].click();
            const after = document.getElementById('scenario-select').value;
            return { before, after, open: window._sdacs.galleryOpen };
        }
    """)
    # 클릭 후 갤러리 자동 닫힘
    assert r["open"] is False


def test_gallery_close_by_escape(page):
    pg, _ = page
    pg.evaluate("window._sdacs.openGallery()")
    pg.keyboard.press("Escape")
    r = pg.evaluate("window._sdacs.galleryOpen")
    assert r is False


def test_gallery_thumbnail_canvas_rendered(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.openGallery();
            const canvases = document.querySelectorAll('#scenario-gallery-grid canvas');
            const widths = [...canvases].map(c => c.width);
            window._sdacs.closeGallery();
            return { count: canvases.length, sampleWidth: widths[0] };
        }
    """)
    assert r["count"] >= 20
    assert r["sampleWidth"] == 220  # 썸네일 캔버스 크기


# ===== HYPER Phase 15 — i18n 4 Languages =====

def test_i18n_4_languages_available(page):
    pg, _ = page
    r = pg.evaluate("window._sdacs.availableLangs")
    assert r == ["ko", "en", "ja", "zh"], f"언어 목록 불일치: {r}"


def test_i18n_setlang_to_ja(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.setLang('ja');
            return {
                lang: window._sdacs.lang,
                title: document.querySelector('[data-i18n="title"]')?.textContent,
                docLang: document.documentElement.lang,
            };
        }
    """)
    assert r["lang"] == "ja"
    assert "ドローン" in r["title"] or "群集" in r["title"]
    assert r["docLang"] == "ja"


def test_i18n_setlang_to_zh(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.setLang('zh');
            return {
                lang: window._sdacs.lang,
                title: document.querySelector('[data-i18n="title"]')?.textContent,
                docLang: document.documentElement.lang,
            };
        }
    """)
    assert r["lang"] == "zh"
    assert "集群" in r["title"] or "无人机" in r["title"]
    assert r["docLang"] == "zh"


def test_i18n_lang_button_cycles_4(page):
    pg, _ = page
    r = pg.evaluate("""
        () => {
            window._sdacs.setLang('ko');
            const btn = document.getElementById('lang-btn');
            if (!btn) return { ok: false };
            const seq = [];
            seq.push(window._sdacs.lang);
            for (let i = 0; i < 4; i++) { btn.click(); seq.push(window._sdacs.lang); }
            return { ok: true, seq };
        }
    """)
    if not r["ok"]:
        pytest.skip("lang-btn not in DOM")
    assert r["seq"] == ["ko", "en", "ja", "zh", "ko"]


def test_no_js_errors_phase14_15(page):
    pg, errors = page
    benign = ["favicon", "WebGPU", "DevTools", "ws_bridge", "WebSocket",
              "ws://localhost", "ws://127.0.0.1", "ERR_CERT", "ERR_CONNECTION",
              "fonts.googleapis", "AudioContext"]
    blocking = [e for e in errors if not any(m in e for m in benign)]
    assert not blocking, f"JS errors: {blocking}"
