"""ODYSSEY Phase 470 — 표준화 기고 추적 대시보드 테스트.

레지스트리의 핵심 계약을 검증한다: 식별자 유일·상태 순서형·진행률 단조·
PUBLISHED 산출물 실재 강제·매니페스트 JSON 직렬화 가능·집계 합 일치.
"""
from __future__ import annotations

import json

import pytest

from simulation.standardization_tracker import (
    REGISTRY,
    STATUS_ORDER,
    Contribution,
    all_contributions,
    body_rollup,
    get_contribution,
    manifest,
    markdown_table,
    progress,
    status_rollup,
    validate_registry,
)

pytestmark = pytest.mark.unit


class TestRegistryShape:
    def test_ids_are_unique(self):
        ids = [c.contribution_id for c in REGISTRY]
        assert len(set(ids)) == len(ids)

    def test_all_contributions_returns_same_registry(self):
        assert all_contributions() == REGISTRY

    def test_entries_are_immutable(self):
        with pytest.raises(Exception):
            REGISTRY[0].status = "ADOPTED"  # type: ignore[misc]

    def test_every_status_is_known(self):
        assert all(c.status in STATUS_ORDER for c in REGISTRY)

    def test_get_contribution_round_trip(self):
        for entry in REGISTRY:
            assert get_contribution(entry.contribution_id) is entry

    def test_get_unknown_contribution_raises(self):
        with pytest.raises(KeyError):
            get_contribution("STD-999")


class TestValidation:
    def test_shipped_registry_is_valid(self):
        result = validate_registry()
        assert result.is_valid, result.errors

    def test_published_without_artifact_is_invalid(self):
        bad = (Contribution("STD-X", "ASTM", "t", "ODYSSEY-1", "PUBLISHED", None),)
        result = validate_registry(bad)
        assert not result.is_valid
        assert any("산출물 경로가 필요" in e for e in result.errors)

    def test_published_with_missing_file_is_invalid(self):
        bad = (
            Contribution(
                "STD-X", "ASTM", "t", "ODYSSEY-1", "PUBLISHED",
                "docs/standards/does_not_exist.md",
            ),
        )
        result = validate_registry(bad)
        assert not result.is_valid
        assert any("산출물 없음" in e for e in result.errors)

    def test_planned_with_missing_artifact_is_invalid(self):
        bad = (
            Contribution(
                "STD-X", "ASTM", "t", "ODYSSEY-1", "PLANNED",
                "docs/standards/ghost.md",
            ),
        )
        result = validate_registry(bad)
        assert not result.is_valid

    def test_unknown_status_is_invalid(self):
        bad = (Contribution("STD-X", "ASTM", "t", "ODYSSEY-1", "MAYBE", None),)
        result = validate_registry(bad)
        assert not result.is_valid
        assert any("알 수 없는 상태" in e for e in result.errors)

    def test_duplicate_id_is_invalid(self):
        bad = (
            Contribution("STD-D", "ASTM", "t", "ODYSSEY-1", "PLANNED", None),
            Contribution("STD-D", "ISO", "u", "ODYSSEY-2", "PLANNED", None),
        )
        result = validate_registry(bad)
        assert not result.is_valid
        assert any("중복 식별자" in e for e in result.errors)

    def test_empty_field_is_invalid(self):
        bad = (Contribution("STD-X", "  ", "t", "ODYSSEY-1", "PLANNED", None),)
        result = validate_registry(bad)
        assert not result.is_valid

    def test_empty_contribution_id_is_invalid(self):
        bad = (Contribution("  ", "ASTM", "t", "ODYSSEY-1", "PLANNED", None),)
        result = validate_registry(bad)
        assert not result.is_valid
        assert any("contribution_id" in e for e in result.errors)

    def test_summary_uses_plural_for_multiple(self):
        bad = (
            Contribution("DUP", "ASTM", "t", "ODYSSEY-1", "PLANNED", None),
            Contribution("DUP", "ISO", "u", "ODYSSEY-2", "MAYBE", None),
        )
        result = validate_registry(bad)
        assert "errors" in result.summary()
        assert "error)" not in result.summary()

    def test_nonstandard_phase_is_warning_not_error(self):
        entry = (Contribution("STD-X", "ASTM", "t", "freeform", "PLANNED", None),)
        result = validate_registry(entry)
        assert result.is_valid
        assert result.warnings


class TestProgress:
    def test_progress_in_unit_interval(self):
        assert 0.0 <= progress() <= 1.0

    def test_all_planned_is_zero(self):
        reg = tuple(
            Contribution(f"STD-{i}", "B", "t", "ODYSSEY-1", "PLANNED", None)
            for i in range(3)
        )
        assert progress(reg) == 0.0

    def test_all_adopted_is_one(self):
        # 의도적으로 검증 불변식(ADOPTED 는 산출물 필요)을 무시한 픽스처 —
        # progress() 가 validate_registry() 와 독립적인 순수 산술임을 격리 검증.
        reg = tuple(
            Contribution(f"STD-{i}", "B", "t", "ODYSSEY-1", "ADOPTED", None)
            for i in range(3)
        )
        assert progress(reg) == 1.0

    def test_shipped_registry_progress_is_pinned(self):
        # 레지스트리 상태가 조용히 바뀌면(예: PLANNED→SUBMITTED) 감지하는 회귀 핀.
        assert progress() == pytest.approx(0.25)

    def test_empty_registry_is_zero(self):
        assert progress(()) == 0.0

    def test_progress_is_monotonic_in_status(self):
        planned = (Contribution("A", "B", "t", "P-1", "PLANNED", None),)
        drafting = (Contribution("A", "B", "t", "P-1", "DRAFTING", None),)
        assert progress(drafting) > progress(planned)


class TestRollups:
    def test_status_rollup_covers_all_statuses(self):
        rollup = status_rollup()
        assert set(rollup.keys()) == set(STATUS_ORDER)

    def test_status_rollup_sums_to_total(self):
        assert sum(status_rollup().values()) == len(REGISTRY)

    def test_body_rollup_sums_to_total(self):
        assert sum(body_rollup().values()) == len(REGISTRY)


class TestManifestAndRender:
    def test_manifest_is_json_serializable(self):
        text = json.dumps(manifest(), ensure_ascii=False)
        assert "sdacs-standardization-tracker" in text

    def test_manifest_count_matches_registry(self):
        m = manifest()
        assert m["count"] == len(REGISTRY)
        assert len(m["contributions"]) == len(REGISTRY)

    def test_manifest_reports_valid_registry(self):
        assert manifest()["is_valid"] is True

    def test_manifest_is_deterministic(self):
        assert manifest() == manifest()

    def test_markdown_lists_every_contribution(self):
        table = markdown_table()
        for entry in REGISTRY:
            assert entry.contribution_id in table

    def test_markdown_escapes_pipe_in_fields(self):
        reg = (Contribution("STD-X", "A|B", "t|u", "ODYSSEY-1", "PLANNED", None),)
        table = markdown_table(reg)
        assert "A\\|B" in table
        assert "t\\|u" in table
