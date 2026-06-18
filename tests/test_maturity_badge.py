"""Phase 207 — Maturity Badge SVG 자동 생성 단위 테스트.

`render_badge_svg`는 라이브 maturity counts에서 결정적으로 SVG 배지를 만든다.
브라우저 없이 순수 함수만 검증한다 (배지 드리프트 방지 게이트).
"""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "extract_sdacs_api.py"
BADGE = ROOT / "docs" / "badges" / "maturity.svg"


def _load_module():
    spec = importlib.util.spec_from_file_location("extract_sdacs_api", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MOD = _load_module()
SAMPLE = {"production": 90, "beta": 98, "mock": 110, "speculative": 103}


def test_badge_contains_all_counts():
    svg = MOD.render_badge_svg(SAMPLE)
    assert "prod 90" in svg
    assert "beta 98" in svg
    assert "mock 110" in svg
    assert "spec 103" in svg


def test_badge_title_matches_counts():
    svg = MOD.render_badge_svg(SAMPLE)
    assert (
        "API Maturity: production 90 / beta 98 / mock 110 / speculative 103" in svg
    )


def test_badge_is_well_formed_svg():
    svg = MOD.render_badge_svg(SAMPLE)
    assert svg.startswith("<svg xmlns=")
    assert svg.rstrip().endswith("</svg>")
    # 여는 태그와 닫는 태그 수가 일치 (rect/text)
    assert svg.count("<rect") == 6  # base + 4 segment + gradient overlay
    assert svg.count("<text") == 5  # maturity label + 4 segment


def test_badge_total_width_is_sum_of_segments():
    svg = MOD.render_badge_svg(SAMPLE)
    width = int(re.search(r'<svg[^>]*width="(\d+)"', svg).group(1))
    seg_widths = [len(f"{s} {SAMPLE[k]}") * 7 + 14 for s, k, _ in MOD.BADGE_SEGMENTS]
    assert width == MOD.BADGE_LABEL_W + sum(seg_widths)


def test_badge_is_deterministic():
    assert MOD.render_badge_svg(SAMPLE) == MOD.render_badge_svg(dict(SAMPLE))


def test_badge_handles_count_digit_change():
    """자릿수가 바뀌면 폭도 따라 변해야 정렬이 유지된다."""
    narrow = MOD.render_badge_svg({"production": 9, "beta": 9, "mock": 9, "speculative": 9})
    wide = MOD.render_badge_svg({"production": 999, "beta": 999, "mock": 999, "speculative": 999})
    nw = int(re.search(r'<svg[^>]*width="(\d+)"', narrow).group(1))
    ww = int(re.search(r'<svg[^>]*width="(\d+)"', wide).group(1))
    assert ww > nw


def test_committed_badge_matches_generator():
    """저장소의 maturity.svg가 생성기 출력과 일치해야 한다 (드리프트 방지).

    저장된 배지의 title에서 counts를 역추출해 생성기에 넣고 비교한다.
    """
    committed = BADGE.read_text(encoding="utf-8")
    m = re.search(
        r"production (\d+) / beta (\d+) / mock (\d+) / speculative (\d+)", committed
    )
    assert m, "배지 title에서 counts를 찾을 수 없음"
    counts = {
        "production": int(m.group(1)),
        "beta": int(m.group(2)),
        "mock": int(m.group(3)),
        "speculative": int(m.group(4)),
    }
    assert committed == MOD.render_badge_svg(counts), (
        "maturity.svg가 생성기 출력과 불일치 — "
        "python scripts/extract_sdacs_api.py 로 재생성 필요"
    )
