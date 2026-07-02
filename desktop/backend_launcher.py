"""
SDACS Desktop Backend Launcher
Electron 데스크톱 앱이 spawn 하는 얇은 진입점.

역할:
    - Dash 3D 대시보드를 127.0.0.1:<PORT> 로 부팅한다.
    - 포트/드론수 등 최소 인자만 받는다 (Electron이 CLI로 전달).
    - stdout 에 준비 완료 신호를 찍는다 → Electron 이 이를 감지해 창을 로드한다.

관계:
    - main.py 의 cmd_visualize 를 재사용한다 (중복 로직 제거, DRY).
    - PyInstaller 로 단일 exe 로 번들되며 dist-python/sdacs-backend.exe 로 배포된다.
    - 서명 없음 방침이므로 Windows Defender 오탐 가능성 있음 → Electron 이 실행 실패 시 폴백 수행.
"""
from __future__ import annotations

import argparse
import os
import sys

# PyInstaller 번들 실행 시 임시 추출 경로가 sys._MEIPASS 에 잡힌다.
# 프로젝트 루트를 sys.path 앞에 두어 simulation/ visualization/ 임포트를 보장.
_ROOT = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Windows 콘솔 인코딩 안전화 (main.py 와 동일)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


READY_SENTINEL = "SDACS_BACKEND_READY"  # Electron 이 stdout 에서 이 문자열을 grep


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="sdacs-backend", description="SDACS Dash 백엔드 런처")
    p.add_argument("--port", type=int, default=8050, help="Dash 서버 포트 (기본 8050)")
    p.add_argument("--drones", type=int, default=30, help="초기 드론 수 (기본 30)")
    p.add_argument("--host", type=str, default="127.0.0.1", help="바인딩 호스트 (기본 127.0.0.1 로 방화벽 팝업 방지)")
    p.add_argument("--log-level", type=str, default="INFO", help="로깅 레벨 (INFO/WARNING/ERROR)")
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    # 로깅 초기화
    import logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s │ %(name)-20s │ %(levelname)-5s │ %(message)s",
        datefmt="%H:%M:%S",
    )

    import threading
    from visualization.simulator_3d import SIM, _sim_loop, app

    SIM.reset(args.drones)
    bg = threading.Thread(target=_sim_loop, args=(SIM,), daemon=True)
    bg.start()

    # Electron 에 준비 완료 신호 (Dash 부팅 직전에 미리 찍는 것도 옵션이지만,
    # 실제로 포트를 listen 하기 전에는 클라이언트가 붙을 수 없으므로 Electron 은
    # port 폴링과 stdout grep 을 함께 사용한다).
    print(f"{READY_SENTINEL} host={args.host} port={args.port} drones={args.drones}", flush=True)

    try:
        app.run(debug=False, host=args.host, port=args.port)
    except OSError as e:
        # 포트 충돌 등
        print(f"[BACKEND_ERROR] Dash 부팅 실패: {e}", file=sys.stderr, flush=True)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
