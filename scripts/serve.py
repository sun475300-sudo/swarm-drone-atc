#!/usr/bin/env python3
"""SDACS 3D 시뮬레이터 로컬 실행 서버.

사용법:
    python3 scripts/serve.py            # 기본 포트 8123, 브라우저 자동 오픈
    python3 scripts/serve.py --port 9000 --no-open

저장소 루트를 정적 서빙하므로 swarm_3d_simulator.html이 ES module importmap으로
three.js를 정상 로드합니다(인터넷 필요 — three.js는 unpkg CDN 사용).
오프라인 실행은 scripts/vendor_three.sh로 three.js를 vendor/에 받은 뒤 importmap을
로컬 경로로 바꾸세요.
"""
from __future__ import annotations

import argparse
import http.server
import os
import socketserver
import threading
import webbrowser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    parser = argparse.ArgumentParser(description="SDACS 시뮬레이터 로컬 서버")
    parser.add_argument("--port", type=int, default=8123)
    parser.add_argument("--no-open", action="store_true", help="브라우저 자동 오픈 비활성화")
    args = parser.parse_args()

    os.chdir(ROOT)
    url = f"http://localhost:{args.port}/swarm_3d_simulator.html"

    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", args.port), handler) as httpd:
        print("=" * 60)
        print(f"  SDACS 시뮬레이터 로컬 서버  →  {url}")
        print(f"  랜딩 페이지                 →  http://localhost:{args.port}/docs/index.html")
        print("  종료: Ctrl+C")
        print("=" * 60)
        if not args.no_open:
            threading.Timer(0.8, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n서버 종료.")


if __name__ == "__main__":
    main()
