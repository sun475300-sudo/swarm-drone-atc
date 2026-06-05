"""HYPER Phase 12 — 데스크탑 멀티 윈도우 배치 로직 + Electron 파일 구문 검증.

Electron 런타임(디스플레이)이 없는 CI에서도 검증 가능한 부분만 테스트한다:
  - desktop/layout.js 의 순수 타일 배치 계산 (computeTileBounds)
  - desktop/{main,preload,layout}.js 의 `node --check` 구문 유효성
  - preload.js 가 윈도우 동기 IPC API를 노출하는지
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "desktop"

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node not installed")


def _run_node(script: str) -> str:
    res = subprocess.run(
        [NODE, "-e", script], cwd=DESKTOP,
        capture_output=True, text=True, timeout=30,
    )
    assert res.returncode == 0, res.stderr
    return res.stdout.strip()


def _tile(displays, count, mode):
    script = (
        "const {computeTileBounds}=require('./layout');"
        f"console.log(JSON.stringify("
        f"computeTileBounds({json.dumps(displays)},{count},{json.dumps(mode)})));"
    )
    return json.loads(_run_node(script))


@pytest.mark.parametrize("fname", ["main.js", "preload.js", "layout.js"])
def test_electron_files_syntax_valid(fname):
    res = subprocess.run(
        [NODE, "--check", str(DESKTOP / fname)],
        capture_output=True, text=True, timeout=30,
    )
    assert res.returncode == 0, res.stderr


def test_single_display_horizontal_splits_width():
    d = [{"workArea": {"x": 0, "y": 0, "width": 1920, "height": 1080}}]
    b = _tile(d, 2, "horizontal")
    assert len(b) == 2
    assert b[0] == {"x": 0, "y": 0, "width": 960, "height": 1080}
    assert b[1] == {"x": 960, "y": 0, "width": 960, "height": 1080}


def test_single_display_vertical_splits_height():
    d = [{"workArea": {"x": 0, "y": 0, "width": 1920, "height": 1080}}]
    b = _tile(d, 2, "vertical")
    assert b[0] == {"x": 0, "y": 0, "width": 1920, "height": 540}
    assert b[1] == {"x": 0, "y": 540, "width": 1920, "height": 540}


def test_dual_display_assigns_one_window_per_monitor():
    d = [
        {"workArea": {"x": 0, "y": 0, "width": 1920, "height": 1080}},
        {"workArea": {"x": 1920, "y": 0, "width": 2560, "height": 1440}},
    ]
    b = _tile(d, 2, "horizontal")
    assert b[0] == {"x": 0, "y": 0, "width": 1920, "height": 1080}
    assert b[1] == {"x": 1920, "y": 0, "width": 2560, "height": 1440}


def test_single_window_uses_full_work_area():
    d = [{"workArea": {"x": 0, "y": 0, "width": 1920, "height": 1080}}]
    b = _tile(d, 1, "horizontal")
    assert b == [{"x": 0, "y": 0, "width": 1920, "height": 1080}]


def test_three_windows_single_display_horizontal():
    d = [{"workArea": {"x": 0, "y": 0, "width": 1920, "height": 1080}}]
    b = _tile(d, 3, "horizontal")
    assert len(b) == 3
    assert [w["width"] for w in b] == [640, 640, 640]
    assert [w["x"] for w in b] == [0, 640, 1280]


def test_last_tile_absorbs_remainder_pixels():
    # 1921 / 2 = 960.5 → 첫 타일 960, 마지막 타일이 나머지 흡수해 작업영역 빈틈 없음
    d = [{"workArea": {"x": 0, "y": 0, "width": 1921, "height": 1080}}]
    b = _tile(d, 2, "horizontal")
    assert b[0]["width"] == 960
    assert b[1]["x"] == 960
    assert b[1]["width"] == 961
    assert b[1]["x"] + b[1]["width"] == 1921  # 우측 끝까지 덮음


def test_zero_count_raises():
    script = (
        "const {computeTileBounds}=require('./layout');"
        "try{computeTileBounds([{workArea:{x:0,y:0,width:100,height:100}}],0,'horizontal');"
        "console.log('NO_THROW');}catch(e){console.log('THREW');}"
    )
    assert _run_node(script) == "THREW"


def test_empty_displays_raises():
    script = (
        "const {computeTileBounds}=require('./layout');"
        "try{computeTileBounds([],1,'horizontal');console.log('NO_THROW');}"
        "catch(e){console.log('THREW');}"
    )
    assert _run_node(script) == "THREW"


def test_preload_exposes_sync_api():
    text = (DESKTOP / "preload.js").read_text(encoding="utf-8")
    for k in ("emitSimTime", "onSimTime", "openWindow"):
        assert k in text, f"preload missing {k}"
