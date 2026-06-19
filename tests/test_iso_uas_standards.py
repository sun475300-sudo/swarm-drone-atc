"""ODYSSEY Phase 462 — ISO/TC 20/SC 16 (UAS) 표준 동향 추적 매트릭스 테스트.

핵심 계약을 검증한다: 식별자 유일·범주/성숙도/커버리지 enum·정직성 결속
(none ⟺ 모듈 없음·full/partial 모듈 디스크 실재)·커버리지 점수 단조·집계 합
일치·매니페스트 JSON 직렬화 가능·Markdown 표 결정성.
"""
from __future__ import annotations

import json

import pytest

from simulation.iso_uas_standards import (
    AS_OF,
    CATEGORIES,
    COVERAGE_STATUSES,
    MATURITIES,
    REGISTRY,
    ISOStandard,
    all_standards,
    category_rollup,
    coverage_rollup,
    coverage_score,
    find_standard,
    gaps,
    manifest,
    markdown_table,
    standards_by_category,
    standards_by_coverage,
    validate,
)

pytestmark = pytest.mark.unit


class TestRegistryShape:
    def test_ids_are_unique(self):
        ids = [s.standard_id for s in REGISTRY]
        assert len(set(ids)) == len(ids)

    def test_all_standards_returns_same_registry(self):
        assert all_standards() == REGISTRY

    def test_entries_are_immutable(self):
        with pytest.raises(Exception):
            REGISTRY[0].coverage = "full"  # type: ignore[misc]

    def test_every_category_is_known(self):
        assert all(s.category in CATEGORIES for s in REGISTRY)

    def test_every_maturity_is_known(self):
        assert all(s.maturity in MATURITIES for s in REGISTRY)

    def test_every_coverage_is_known(self):
        assert all(s.coverage in COVERAGE_STATUSES for s in REGISTRY)

    def test_find_standard_round_trip(self):
        for entry in REGISTRY:
            assert find_standard(entry.standard_id) is entry

    def test_find_unknown_standard_raises(self):
        with pytest.raises(KeyError):
            find_standard("ISO-99999")

    def test_registry_is_non_empty(self):
        assert len(REGISTRY) >= 1


class TestHonestyBinding:
    def test_none_coverage_has_no_module(self):
        for entry in REGISTRY:
            if entry.coverage == "none":
                assert entry.sdacs_module is None

    def test_covered_standards_cite_existing_module(self):
        for entry in REGISTRY:
            if entry.coverage != "none":
                assert entry.sdacs_module is not None
                assert entry.module_exists(), f"{entry.standard_id} → {entry.sdacs_module}"

    def test_none_with_module_raises(self):
        with pytest.raises(ValueError):
            ISOStandard(
                "ISO-X", "ISO X", "t", "utm", "published", "none",
                "simulation/iso_uas_standards.py", "s",
            )

    def test_full_without_module_raises(self):
        with pytest.raises(ValueError):
            ISOStandard("ISO-X", "ISO X", "t", "utm", "published", "full", None, "s")

    def test_unknown_category_raises(self):
        with pytest.raises(ValueError):
            ISOStandard("ISO-X", "ISO X", "t", "nope", "published", "none", None, "s")

    def test_unknown_maturity_raises(self):
        with pytest.raises(ValueError):
            ISOStandard("ISO-X", "ISO X", "t", "utm", "nope", "none", None, "s")

    def test_blank_id_raises(self):
        with pytest.raises(ValueError):
            ISOStandard(" ", "ISO X", "t", "utm", "published", "none", None, "s")

    def test_id_with_space_raises(self):
        with pytest.raises(ValueError):
            ISOStandard("ISO X", "ISO X", "t", "utm", "published", "none", None, "s")


class TestValidation:
    def test_shipped_registry_is_valid(self):
        result = validate()
        assert result.is_valid, result.errors
        assert result.warnings == ()
        assert result.summary() == "VALID"

    def test_duplicate_id_is_invalid(self):
        dup = REGISTRY + (REGISTRY[0],)
        result = validate(dup)
        assert not result.is_valid

    def test_missing_module_is_invalid(self):
        bad = (
            ISOStandard(
                "ISO-X", "ISO X", "t", "utm", "published", "full",
                "simulation/does_not_exist_zzz.py", "s",
            ),
        )
        result = validate(bad)
        assert not result.is_valid

    def test_summary_singular_plural(self):
        # 1 error vs 2 errors 복수형 분기를 잘못된 레지스트리로 직접 검증.
        one = (
            ISOStandard("ISO-X", "ISO X", "t", "utm", "published", "full",
                        "simulation/nope_a.py", "s"),
        )
        assert "1 error" in validate(one).summary()
        two = one + (
            ISOStandard("ISO-Y", "ISO Y", "t", "utm", "published", "full",
                        "simulation/nope_b.py", "s"),
        )
        assert "2 errors" in validate(two).summary()


class TestQueries:
    def test_standards_by_category_partitions(self):
        total = sum(len(standards_by_category(c)) for c in CATEGORIES)
        assert total == len(REGISTRY)

    def test_standards_by_category_sorted(self):
        for category in CATEGORIES:
            members = standards_by_category(category)
            assert list(members) == sorted(members, key=lambda s: s.standard_id)

    def test_unknown_category_query_raises(self):
        with pytest.raises(ValueError):
            standards_by_category("nope")

    def test_gaps_equals_none_coverage(self):
        assert gaps() == standards_by_coverage("none")

    def test_gaps_have_no_module(self):
        assert all(g.sdacs_module is None for g in gaps())

    def test_unknown_coverage_query_raises(self):
        with pytest.raises(ValueError):
            standards_by_coverage("nope")


class TestRollups:
    def test_category_rollup_sums_to_total(self):
        assert sum(category_rollup().values()) == len(REGISTRY)

    def test_coverage_rollup_sums_to_total(self):
        assert sum(coverage_rollup().values()) == len(REGISTRY)

    def test_category_rollup_keys_are_all_categories(self):
        assert tuple(category_rollup().keys()) == CATEGORIES

    def test_coverage_rollup_keys_are_all_statuses(self):
        assert tuple(coverage_rollup().keys()) == COVERAGE_STATUSES


class TestCoverageScore:
    def test_score_in_unit_interval(self):
        assert 0.0 <= coverage_score() <= 1.0

    def test_empty_registry_score_is_zero(self):
        assert coverage_score(()) == 0.0

    def test_all_full_is_one(self):
        reg = (
            ISOStandard("ISO-A", "ISO A", "t", "utm", "published", "full",
                        "simulation/iso_uas_standards.py", "s"),
        )
        assert coverage_score(reg) == 1.0

    def test_all_none_is_zero(self):
        reg = (
            ISOStandard("ISO-A", "ISO A", "t", "utm", "published", "none", None, "s"),
        )
        assert coverage_score(reg) == 0.0

    def test_partial_is_monotonic(self):
        none_reg = (
            ISOStandard("ISO-A", "ISO A", "t", "utm", "published", "none", None, "s"),
        )
        partial_reg = (
            ISOStandard("ISO-A", "ISO A", "t", "utm", "published", "partial",
                        "simulation/iso_uas_standards.py", "s"),
        )
        full_reg = (
            ISOStandard("ISO-A", "ISO A", "t", "utm", "published", "full",
                        "simulation/iso_uas_standards.py", "s"),
        )
        assert coverage_score(none_reg) < coverage_score(partial_reg) < coverage_score(full_reg)


class TestManifest:
    def test_manifest_is_json_serializable(self):
        blob = json.dumps(manifest())
        assert isinstance(blob, str)

    def test_manifest_count_matches(self):
        assert manifest()["count"] == len(REGISTRY)

    def test_manifest_carries_as_of(self):
        assert manifest()["as_of"] == AS_OF

    def test_manifest_is_valid_flag(self):
        assert manifest()["is_valid"] is True

    def test_manifest_standards_have_module_exists(self):
        for row in manifest()["standards"]:
            if row["coverage"] != "none":
                assert row["module_exists"] is True


class TestMarkdown:
    def test_markdown_is_deterministic(self):
        assert markdown_table() == markdown_table()

    def test_markdown_rows_follow_registry_order(self):
        # set 정렬 회귀로 행 순서가 흔들리면 감지 — REGISTRY 삽입 순서 고정.
        table = markdown_table()
        positions = [table.index(s.designation.replace("|", "\\|")) for s in REGISTRY]
        assert positions == sorted(positions)

    def test_markdown_has_header_and_all_rows(self):
        table = markdown_table()
        assert "지정번호" in table
        for entry in REGISTRY:
            assert entry.designation.replace("|", "\\|") in table


class TestShippedContent:
    """배포된 레지스트리 내용 회귀 핀."""

    def test_operations_part3_is_full_coverage(self):
        # ISO 21384-3(운영 절차)는 SDACS 핵심 도메인 — 완전 커버리지.
        assert find_standard("ISO-21384-3").coverage == "full"

    def test_product_parts_are_gaps(self):
        # 기체 제품 사양(21384-1·-2)은 SDACS 범위 밖 — 정직한 gap.
        assert find_standard("ISO-21384-1").is_gap
        assert find_standard("ISO-21384-2").is_gap

    def test_has_at_least_one_gap_and_one_covered(self):
        assert len(gaps()) >= 1
        assert any(not s.is_gap for s in REGISTRY)
