"""200 Phase Showcase 자동 녹화 — Playwright headed (chromium-headless-shell)에서
showcase.js 를 실행하고 MediaRecorder 출력을 캡처해 WebM 파일로 저장 시도.

주의: 헤드리스 Chromium은 MediaRecorder 동작 가능하나 화면 출력 보장은 환경 의존.
"""
from __future__ import annotations

import http.server
import os
import socketserver
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHOWCASE = ROOT.parent / "docs" / "demo" / "all_phases_showcase.js"


def serve_root():
    port = 0

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **kw):
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", port), Quiet)
    port = httpd.server_address[1]
    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    os.chdir(Path(__file__).resolve().parents[1])
    th.start()
    time.sleep(0.2)
    return httpd, f"http://127.0.0.1:{port}"


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed")
        return

    httpd, base_url = serve_root()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=[
                "--disable-features=IsolateOrigins,site-per-process",
                "--use-gl=swiftshader",
            ])
            ctx = browser.new_context(
                viewport={"width": 1400, "height": 900},
                record_video_dir=str(ROOT / "recordings"),
                record_video_size={"width": 1400, "height": 900},
            )
            pg = ctx.new_page()
            pg.goto(f"{base_url}/swarm_3d_simulator.html", wait_until="networkidle", timeout=20000)
            pg.wait_for_function("window._sdacs && window._sdacs.droneCount > 0", timeout=15000)
            print("[Showcase] 시뮬 로드 완료")
            # showcase 실행 (수동 트리거)
            with open(SHOWCASE, encoding="utf-8") as f:
                script = f.read()
            pg.evaluate(script)
            print("[Showcase] 스크립트 주입 완료, 60초 대기")
            pg.wait_for_timeout(60000)
            ctx.close()
            browser.close()
        # 녹화 파일 찾기
        for f in (ROOT / "recordings").glob("*.webm"):
            print(f"[Showcase] 녹화 저장: {f} ({f.stat().st_size} bytes)")
        print("[Showcase] 완료")
    finally:
        httpd.shutdown()
        httpd.server_close()


if __name__ == "__main__":
    main()
