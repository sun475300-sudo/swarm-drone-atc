"""TRANSCENDENCE Phase 207 — Maturity Badge SVG 자동 생성 단위 테스트.

`render_badge` 는 maturityReport().counts 로부터 결정적으로 SVG 를 생성한다.
브라우저/playwright 불필요 — 순수 함수 검증.
"""
from __future__ import annotations

import importlib.util
import re
import xml.dom.minidom
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "extract_sdacs_api", ROOT / "scripts" / "extract_sdacs_api.py"
)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)
BADGE = ROOT / "docs" / "badges" / "maturity.svg"


def _data(prod: int, beta: int, mock: int, spec: int) -> dict:
    return {"counts": {"production": prod, "beta": beta, "mock": mock, "speculative": spec}}


def test_badge_is_wellformed_xml():
    # Arrange / Act
    svg = mod.render_badge(_data(90, 98, 110, 103))
    # Assert — 파싱 가능한 well-formed SVG
    dom = xml.dom.minidom.parseString(svg)
    assert dom.documentElement.tagName == "svg"


def test_badge_reflects_each_count():
    svg = mod.render_badge(_data(1, 2, 3, 4))
    assert "prod 1" in svg
    assert "beta 2" in svg
    assert "mock 3" in svg
    assert "spec 4" in svg
    # <title> 은 정합성 게이트가 검사하는 전체 키 표기를 포함
    assert "production 1 / beta 2 / mock 3 / speculative 4" in svg


def test_badge_width_grows_with_digits():
    narrow = mod.render_badge(_data(1, 2, 3, 4))
    wide = mod.render_badge(_data(1000, 2000, 3000, 4000))
    nw = int(re.search(r'width="(\d+)"', narrow).group(1))
    ww = int(re.search(r'width="(\d+)"', wide).group(1))
    assert ww > nw


def test_badge_title_helper_matches_render():
    counts = _data(90, 98, 110, 103)["counts"]
    title = mod.badge_title(counts)
    assert title == "production 90 / beta 98 / mock 110 / speculative 103"
    assert title in mod.render_badge({"counts": counts})


def test_committed_badge_matches_generator():
    """커밋된 maturity.svg 가 render_badge 출력과 동일해야 한다(드리프트 방지)."""
    current = BADGE.read_text(encoding="utf-8")
    # 커밋 배지 <title> 에서 실제 counts 를 역추출
    m = re.search(
        r"production (\d+) / beta (\d+) / mock (\d+) / speculative (\d+)", current
    )
    assert m, "maturity.svg <title> 에 counts 표기가 있어야 한다"
    prod, beta, mock, spec = (int(x) for x in m.groups())
    expected = mod.render_badge(_data(prod, beta, mock, spec))
    assert current == expected
