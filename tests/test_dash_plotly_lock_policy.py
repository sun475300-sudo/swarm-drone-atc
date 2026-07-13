"""dash/plotly 버전 정합 정책 테스트.

plotly 6.x의 bdata(base64 typed-array) 직렬화는 dash 2.x 내장 plotly.js가
디코드하지 못해 3D 대시보드가 빈 그래프로 렌더된다(dependabot #496 보류 사유).
매니페스트 3종(requirements.txt·requirements.lock.txt·pyproject.toml)의
하한·핀이 깨진 조합(dash<3 + plotly>=6)으로 회귀하지 않도록 CI에서 잡아준다.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]

# dash 3.0부터 설치된 plotly 패키지의 plotly.js를 서빙하므로 bdata를 디코드한다.
MIN_DASH_MAJOR_FOR_PLOTLY6 = 3
MIN_PLOTLY_MAJOR = 6


def _spec_major(text: str, package: str) -> int:
    """매니페스트 본문에서 package의 하한/핀 major를 추출한다."""
    match = re.search(rf"^\s*\"?{package}\s*[>=]=\s*(\d+)", text, re.MULTILINE)
    assert match is not None, f"{package} 스펙을 찾지 못함"
    return int(match.group(1))


def test_lock_pins_are_coherent():
    text = (REPO_ROOT / "requirements.lock.txt").read_text(encoding="utf-8")
    plotly_major = _spec_major(text, "plotly")
    dash_major = _spec_major(text, "dash")
    assert plotly_major >= MIN_PLOTLY_MAJOR
    assert dash_major >= MIN_DASH_MAJOR_FOR_PLOTLY6, (
        f"lock이 깨진 조합: plotly {plotly_major}.x + dash {dash_major}.x — "
        "dash 2.x 내장 plotly.js는 plotly 6.x bdata를 렌더하지 못함"
    )


def test_requirements_floor_forbids_dash2():
    text = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert _spec_major(text, "plotly") >= MIN_PLOTLY_MAJOR
    assert _spec_major(text, "dash") >= MIN_DASH_MAJOR_FOR_PLOTLY6


def test_pyproject_floor_forbids_dash2():
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert _spec_major(text, "plotly") >= MIN_PLOTLY_MAJOR
    assert _spec_major(text, "dash") >= MIN_DASH_MAJOR_FOR_PLOTLY6


def test_installed_combination_renders_bdata():
    dash = pytest.importorskip("dash")
    plotly = pytest.importorskip("plotly")
    plotly_major = int(plotly.__version__.split(".")[0])
    dash_major = int(dash.__version__.split(".")[0])
    if plotly_major >= MIN_PLOTLY_MAJOR:
        assert dash_major >= MIN_DASH_MAJOR_FOR_PLOTLY6, (
            f"설치 조합 dash {dash.__version__} + plotly {plotly.__version__}은 "
            "3D 대시보드가 빈 그래프로 렌더됨"
        )
