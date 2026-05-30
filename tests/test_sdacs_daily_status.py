"""tests for scripts/sdacs_daily_status.py"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sdacs_daily_status import (
    _count_roadmap_items,
    _count_test_files,
    generate_report,
)

pytestmark = pytest.mark.unit

_SAMPLE_ROADMAP = """\
## Completed

### Phase 1: Core

## In Progress

### Track A — Hardware

- [x] **P691** — done
- [ ] **P692** — todo
- [ ] **P693** — todo

### Track B — Research

- [x] **P701** — done
- [x] **P702** — done
- [ ] **P706** — todo
"""


class TestCountRoadmapItems:
    def test_counts_done_and_todo(self, tmp_path: Path) -> None:
        f = tmp_path / "ROADMAP.md"
        f.write_text(_SAMPLE_ROADMAP, encoding="utf-8")
        items = _count_roadmap_items(f)
        assert items["Track A"]["done"] == 1
        assert items["Track A"]["todo"] == 2
        assert items["Track B"]["done"] == 2
        assert items["Track B"]["todo"] == 1

    def test_empty_file_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "ROADMAP.md"
        f.write_text("", encoding="utf-8")
        assert _count_roadmap_items(f) == {}


class TestCountTestFiles:
    def test_counts_test_py_files(self, tmp_path: Path) -> None:
        (tmp_path / "test_foo.py").write_text("", encoding="utf-8")
        (tmp_path / "test_bar.py").write_text("", encoding="utf-8")
        (tmp_path / "helper.py").write_text("", encoding="utf-8")
        assert _count_test_files(tmp_path) == 2

    def test_recursive_count(self, tmp_path: Path) -> None:
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "test_nested.py").write_text("", encoding="utf-8")
        (tmp_path / "test_root.py").write_text("", encoding="utf-8")
        assert _count_test_files(tmp_path) == 2


class TestGenerateReport:
    def _setup_fake_root(self, tmp_path: Path) -> Path:
        (tmp_path / "ROADMAP.md").write_text(_SAMPLE_ROADMAP, encoding="utf-8")
        (tmp_path / "tests").mkdir()
        (tmp_path / "reports").mkdir()
        return tmp_path

    def test_creates_file(self, tmp_path: Path) -> None:
        root = self._setup_fake_root(tmp_path)
        out = tmp_path / "reports" / "status.md"
        path = generate_report(output_path=out, no_git=True, root=root)
        assert path == out
        assert out.exists()

    def test_report_contains_required_sections(self, tmp_path: Path) -> None:
        root = self._setup_fake_root(tmp_path)
        out = tmp_path / "reports" / "status.md"
        generate_report(output_path=out, no_git=True, root=root)
        content = out.read_text(encoding="utf-8")
        assert "SDACS 일일 상태 보고서" in content
        assert "전체 진행률" in content
        assert "프로젝트 지표" in content
        assert "사람이 필요한 항목" in content
        assert "Track A" in content
        assert "Track B" in content

    def test_rejects_path_outside_root(self, tmp_path: Path) -> None:
        root = self._setup_fake_root(tmp_path)
        outside = tmp_path.parent / "evil.md"
        with pytest.raises(ValueError, match="프로젝트 루트 밖"):
            generate_report(output_path=outside, no_git=True, root=root)

    def test_default_output_path_inside_root(self, tmp_path: Path) -> None:
        root = self._setup_fake_root(tmp_path)
        path = generate_report(no_git=True, root=root)
        assert str(path).startswith(str(root.resolve()))
