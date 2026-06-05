"""`docs/SDACS_API.md`가 `swarm_3d_simulator.html`의 `_sdacs` API와 동기 상태인지 검증.

Phase 14/15처럼 시뮬레이터에 API가 추가됐는데 문서를 재생성하지 않으면 실패한다.
재생성: `python scripts/gen_sdacs_api.py`
"""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "scripts" / "gen_sdacs_api.py"
OUT = ROOT / "docs" / "SDACS_API.md"


def _load_generator():
    spec = importlib.util.spec_from_file_location("gen_sdacs_api", GEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _strip_date(text: str) -> str:
    return re.sub(r"\*자동 생성:.*?\*", "", text)


def test_doc_is_in_sync_with_simulator():
    gen = _load_generator()
    expected = gen.generate()
    actual = OUT.read_text(encoding="utf-8")
    assert _strip_date(actual) == _strip_date(expected), (
        "docs/SDACS_API.md 가 시뮬레이터와 불일치합니다. "
        "`python scripts/gen_sdacs_api.py` 로 재생성하세요."
    )


def test_entry_count_matches_parsed_block():
    gen = _load_generator()
    html = gen.SIM_HTML.read_text(encoding="utf-8")
    entries = gen.parse_entries(gen.extract_block(html))
    # 문서 헤더의 "전체 항목 수: N개" 와 파싱 결과 일치
    doc = OUT.read_text(encoding="utf-8")
    n_doc = int(re.search(r"전체 항목 수: (\d+)개", doc).group(1))
    assert n_doc == len(entries)
    assert len(entries) >= 92  # Phase 0-15 누적 하한


def test_phase_14_15_api_present():
    gen = _load_generator()
    html = gen.SIM_HTML.read_text(encoding="utf-8")
    names = {name for _, _, name, _ in gen.parse_entries(gen.extract_block(html))}
    # HYPER Phase 14(갤러리) / 15(다국어) 신규 API
    for required in ("openGallery", "closeGallery", "scenarioCategories", "availableLangs"):
        assert required in names, f"{required} API 누락"
