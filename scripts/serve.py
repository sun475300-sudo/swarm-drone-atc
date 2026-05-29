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

# 같은 포트가 이미 쓰이는 경우(런처 두 번 클릭 등) 다음 포트를 자동 탐색한다.
PORT_SCAN_RANGE = 20

PAGE_ALIASES = {
    "swarm": "swarm_3d_simulator.html",
    "sim": "swarm_3d_simulator.html",
    "maritime": "maritime_detection_simulator.html",
    "ship": "maritime_detection_simulator.html",
    "landing": "docs/index.html",
    "home": "docs/index.html",
}


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """성공(2xx) 요청 로그만 숨겨 콘솔을 깔끔히 한다. 404/500 등은 그대로 노출."""

    def log_message(self, fmt: str, *args) -> None:  # noqa: A002
        if len(args) >= 2 and str(args[1]).startswith("2"):
            return  # 정상 응답은 조용히
        super().log_message(fmt, *args)


def _bind(port: int) -> tuple[socketserver.TCPServer, int]:
    """`port`부터 시작해 사용 가능한 포트를 찾아 서버를 바인딩한다.

    기본 TCPServer(allow_reuse_address=False)로 프로빙한다. SO_REUSEADDR를
    켜면 Windows에서는 활성 LISTEN 포트에도 중복 바인딩이 되어(=SO_REUSEPORT
    의미) 두 번째 런처가 같은 포트를 점유해 버린다 — 스캔이 무력화되므로 켜지 않는다.
    """
    last_err: OSError | None = None
    for candidate in range(port, port + PORT_SCAN_RANGE):
        try:
            return socketserver.TCPServer(("", candidate), QuietHandler), candidate
        except OSError as err:  # 포트 사용 중 → 다음 후보
            last_err = err
            continue
    raise SystemExit(
        f"포트 {port}~{port + PORT_SCAN_RANGE - 1} 가 모두 사용 중입니다: {last_err}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="SDACS 시뮬레이터 로컬 서버")
    parser.add_argument("--port", type=int, default=8123)
    parser.add_argument("--no-open", action="store_true", help="브라우저 자동 오픈 비활성화")
    parser.add_argument(
        "--page",
        default="swarm",
        help="자동으로 열 페이지(swarm|maritime|landing 또는 직접 경로)",
    )
    args = parser.parse_args()

    os.chdir(ROOT)
    page = PAGE_ALIASES.get(args.page, args.page)

    httpd, port = _bind(args.port)
    base = f"http://localhost:{port}"
    url = f"{base}/{page}"

    with httpd:
        print("=" * 60)
        print(f"  SDACS 3D 시뮬레이터   →  {base}/swarm_3d_simulator.html")
        print(f"  해양 소형선 감지       →  {base}/maritime_detection_simulator.html")
        print(f"  랜딩 페이지            →  {base}/docs/index.html")
        print("-" * 60)
        print(f"  브라우저가 자동으로 열립니다: {url}")
        print("  종료: 이 창에서 Ctrl+C")
        print("=" * 60)
        if not args.no_open:
            threading.Timer(0.8, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n서버 종료.")


if __name__ == "__main__":
    main()
