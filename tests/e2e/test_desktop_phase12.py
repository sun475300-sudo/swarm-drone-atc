"""HYPER Phase 12 — Electron 멀티 윈도우 + IPC 시간축 동기 정적 검증.

브라우저 환경에선 Electron 실제 IPC 호출은 불가하므로:
1. desktop/main.js 의 멀티 윈도우/IPC 핸들러 구조 검증
2. desktop/preload.js 의 contextBridge 노출 API 구조 검증
3. AppImage ASAR 내 main.js/preload.js 정상 패키징 확인
4. 시뮬레이터 HTML에 IPC hook 코드 존재 확인
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_main_js_has_split_mode():
    src = (ROOT / "desktop" / "main.js").read_text(encoding="utf-8")
    assert "openSplitMode" in src
    assert "closeSplitMode" in src
    assert "secondaryWin" in src
    assert "allWins" in src


def test_main_js_has_ipc_handlers():
    src = (ROOT / "desktop" / "main.js").read_text(encoding="utf-8")
    # ipcMain 등록
    assert "ipcMain.on('sim-time-tick'" in src
    assert "ipcMain.on('atc-broadcast'" in src
    assert "ipcMain.handle('windows-count'" in src


def test_main_js_menu_has_split_shortcuts():
    src = (ROOT / "desktop" / "main.js").read_text(encoding="utf-8")
    # CmdOrCtrl+Shift+S 분할, CmdOrCtrl+Shift+W 복귀
    assert "CmdOrCtrl+Shift+S" in src
    assert "CmdOrCtrl+Shift+W" in src
    assert "분할 모드" in src


def test_preload_js_exposes_ipc_api():
    src = (ROOT / "desktop" / "preload.js").read_text(encoding="utf-8")
    assert "contextBridge.exposeInMainWorld" in src
    for api in ["sendTimeTick", "onTimeSync", "sendAtcBroadcast", "onAtcBroadcast", "onSplitMode", "windowsCount"]:
        assert api in src, f"preload missing {api}"


def test_preload_js_no_node_globals_leaked():
    src = (ROOT / "desktop" / "preload.js").read_text(encoding="utf-8")
    # contextIsolation + sandbox 활성화 상태에서 node global 직접 노출 금지
    assert "nodeIntegration: true" not in src
    assert "exposeInMainWorld('process'" not in src
    assert "exposeInMainWorld('require'" not in src


def test_node_check_main_js():
    r = subprocess.run(
        ["node", "--check", str(ROOT / "desktop" / "main.js")],
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0, f"main.js syntax error: {r.stderr}"


def test_node_check_preload_js():
    r = subprocess.run(
        ["node", "--check", str(ROOT / "desktop" / "preload.js")],
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0, f"preload.js syntax error: {r.stderr}"


def test_swarm_simulator_has_ipc_hook():
    src = (ROOT / "swarm_3d_simulator.html").read_text(encoding="utf-8")
    assert "window.sdacs && window.sdacs.isElectron" in src
    assert "sendTimeTick" in src
    assert "onTimeSync" in src
    assert "sendAtcBroadcast" in src


def test_maritime_simulator_has_ipc_hook():
    src = (ROOT / "maritime_detection_simulator.html").read_text(encoding="utf-8")
    assert "window.sdacs && window.sdacs.isElectron" in src
    assert "sendTimeTick" in src
    assert "onTimeSync" in src


def test_appimage_exists_and_packaged():
    appimg = ROOT / "dist-desktop" / "SDACS-Simulator-1.1.0-x86_64.AppImage"
    if not appimg.exists():
        pytest.skip(f"AppImage not built (run npm run dist:linux): {appimg}")
    sz = appimg.stat().st_size
    assert sz > 50_000_000, f"AppImage too small ({sz} bytes), build likely failed"
    assert sz < 200_000_000, f"AppImage too large ({sz} bytes), unexpected bloat"


def test_appimage_includes_phase12_code():
    appimg = ROOT / "dist-desktop" / "SDACS-Simulator-1.1.0-x86_64.AppImage"
    if not appimg.exists():
        pytest.skip("AppImage not built")
    import tempfile, os
    with tempfile.TemporaryDirectory() as td:
        os.chdir(td)
        subprocess.run([str(appimg), "--appimage-extract"], capture_output=True, timeout=60)
        asar_path = Path(td) / "squashfs-root" / "resources" / "app.asar"
        assert asar_path.exists(), "app.asar not found in AppImage"
        # asar extract-file (npx asar 사용)
        extracted = Path(td) / "asar-out"
        subprocess.run(
            ["npx", "--yes", "asar", "e", str(asar_path), str(extracted)],
            capture_output=True, timeout=60, cwd=str(ROOT),
        )
        main_js = (extracted / "desktop" / "main.js").read_text(encoding="utf-8")
        assert "openSplitMode" in main_js
        assert "ipcMain.on('sim-time-tick'" in main_js
        os.chdir(str(ROOT))
