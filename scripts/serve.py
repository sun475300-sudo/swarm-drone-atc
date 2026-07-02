#!/usr/bin/env python3
"""SDACS 로컬 시뮬레이터 런처 — 정적 HTML을 http:// 로 서빙한다.

HTML을 파일 더블클릭(file://)으로 열면 three.js ES 모듈이 브라우저 CORS
정책에 막혀 로드되지 않아 화면이 뜨지 않는다. 이 스크립트는 저장소 루트를
로컬 HTTP 서버로 제공해 시뮬레이터가 정상 동작하도록 한다.

사용법:
    python scripts/serve.py                    # 군집 드론 시뮬레이터
    python scripts/serve.py --page maritime    # 해양 소형선 감지
    python scripts/serve.py --port 9000 --no-browser
"""
from __future__ import annotations

import argparse
import functools
import http.server
import socket
import sys
import threading
import webbrowser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# 실행 가능한 시뮬레이터 페이지 (저장소 루트 기준 상대 경로)
PAGES = {
    "swarm": "swarm_3d_simulator.html",
    "maritime": "maritime_detection_simulator.html",
}

DEFAULT_PORT = 8123
PORT_SCAN_RANGE = 20


def _find_open_port(preferred: int, host: str) -> int:
    """preferred 포트가 사용 중이면 다음 빈 포트를 찾는다."""
    for port in range(preferred, preferred + PORT_SCAN_RANGE):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            if probe.connect_ex((host, port)) != 0:  # 연결 실패 = 비어 있음
                return port
    return preferred


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SDACS 시뮬레이터 로컬 서버")
    parser.add_argument("--page", choices=sorted(PAGES), default="swarm",
                        help="열 시뮬레이터 페이지 (기본: swarm)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"HTTP 포트 (기본: {DEFAULT_PORT})")
    parser.add_argument("--host", default="127.0.0.1",
                        help="바인드 주소 (기본: 127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true",
                        help="브라우저 자동 열기 비활성화")
    args = parser.parse_args(argv)

    page = PAGES[args.page]
    if not (REPO_ROOT / page).exists():
        print(f"[ERROR] 페이지를 찾을 수 없습니다: {page}", file=sys.stderr)
        return 1

    port = _find_open_port(args.port, args.host)
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(REPO_ROOT)
    )
    httpd = http.server.ThreadingHTTPServer((args.host, port), handler)

    url = f"http://{args.host}:{port}/{page}"
    print("=" * 60)
    print("  SDACS 시뮬레이터 서버 시작")
    print(f"  URL : {url}")
    print(f"  루트: {REPO_ROOT}")
    print("  중지: Ctrl+C")
    print("=" * 60)

    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n서버를 종료합니다.")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
