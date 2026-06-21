"""ODYSSEY Phase 410 — GUTMA 회원 기고 적합성 매트릭스 단위 테스트."""
from __future__ import annotations

from pathlib import Path

import pytest

from simulation.gutma_contribution import (
    CONTRIBUTION_STATUSES,
    GUTMA_WORK_ITEMS,
    WORKING_GROUPS,
    ContributionReport,
    GutmaWorkItem,
    contribution_matrix,
    contribution_report,
    find_work_item,
    gaps,
    items_by_group,
    items_by_status,
    main,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- #
# 카탈로그 정합성
# --------------------------------------------------------------------------- #
def test_catalog_non_empty():
    assert len(GUTMA_WORK_ITEMS) >= 8


def test_item_ids_unique():
    ids = [i.item_id for i in GUTMA_WORK_ITEMS]
    assert len(ids) == len(set(ids))


def test_all_groups_referenced_exist():
    for item in GUTMA_WORK_ITEMS:
        assert item.group in WORKING_GROUPS


def test_all_statuses_valid():
    for item in GUTMA_WORK_ITEMS:
        assert item.status in CONTRIBUTION_STATUSES


def test_every_working_group_has_at_least_one_item():
    used = {i.group for i in GUTMA_WORK_ITEMS}
    assert used == set(WORKING_GROUPS)


# --------------------------------------------------------------------------- #
# 정직성 결속 (핵심 불변식)
# --------------------------------------------------------------------------- #
def test_gap_status_iff_module_none():
    for item in GUTMA_WORK_ITEMS:
        if item.status == "gap":
            assert item.sdacs_module is None
        else:
            assert item.sdacs_module is not None


def test_cited_modules_exist_on_disk():
    """ready/partial 항목이 인용한 모듈은 디스크에 실재해야 한다."""
    for item in GUTMA_WORK_ITEMS:
        if item.sdacs_module is not None:
            path = _REPO_ROOT / item.sdacs_module
            assert path.is_file(), f"{item.item_id} cites missing module {item.sdacs_module}"


def test_has_at_least_one_honest_gap():
    """미대응 항목을 정직히 표면화한다 — 갭이 최소 1건 존재."""
    assert len(gaps()) >= 1


def test_spec_refs_non_empty():
    for item in GUTMA_WORK_ITEMS:
        assert item.spec_ref.strip()


# --------------------------------------------------------------------------- #
# GutmaWorkItem 검증 (__post_init__)
# --------------------------------------------------------------------------- #
def _valid_kwargs(**over):
    base = dict(
        item_id="x", name="X", group="FDP", status="ready",
        spec_ref="ref", sdacs_module="simulation/gutma_contribution.py", summary="s",
    )
    base.update(over)
    return base


def test_rejects_empty_item_id():
    with pytest.raises(ValueError):
        GutmaWorkItem(**_valid_kwargs(item_id=""))


def test_rejects_padded_item_id():
    with pytest.raises(ValueError):
        GutmaWorkItem(**_valid_kwargs(item_id=" x "))


def test_rejects_item_id_with_space():
    with pytest.raises(ValueError):
        GutmaWorkItem(**_valid_kwargs(item_id="a b"))


def test_rejects_item_id_with_tab():
    with pytest.raises(ValueError):
        GutmaWorkItem(**_valid_kwargs(item_id="a\tb"))


def test_rejects_item_id_with_newline():
    with pytest.raises(ValueError):
        GutmaWorkItem(**_valid_kwargs(item_id="a\nb"))


def test_rejects_empty_name():
    with pytest.raises(ValueError):
        GutmaWorkItem(**_valid_kwargs(name="  "))


def test_rejects_empty_summary():
    with pytest.raises(ValueError):
        GutmaWorkItem(**_valid_kwargs(summary=""))


def test_rejects_empty_spec_ref():
    with pytest.raises(ValueError):
        GutmaWorkItem(**_valid_kwargs(spec_ref="  "))


def test_rejects_unknown_group():
    with pytest.raises(ValueError):
        GutmaWorkItem(**_valid_kwargs(group="ZZZ"))


def test_rejects_unknown_status():
    with pytest.raises(ValueError):
        GutmaWorkItem(**_valid_kwargs(status="maybe"))


def test_rejects_gap_with_module():
    with pytest.raises(ValueError):
        GutmaWorkItem(**_valid_kwargs(status="gap", sdacs_module="simulation/x.py"))


def test_rejects_ready_without_module():
    with pytest.raises(ValueError):
        GutmaWorkItem(**_valid_kwargs(status="ready", sdacs_module=None))


def test_rejects_partial_with_blank_module():
    with pytest.raises(ValueError):
        GutmaWorkItem(**_valid_kwargs(status="partial", sdacs_module="   "))


def test_can_contribute_property():
    ready = GutmaWorkItem(**_valid_kwargs(status="ready"))
    gap = GutmaWorkItem(**_valid_kwargs(status="gap", sdacs_module=None))
    assert ready.can_contribute is True
    assert gap.can_contribute is False


def test_weight_property():
    assert GutmaWorkItem(**_valid_kwargs(status="ready")).weight == 1.0
    assert GutmaWorkItem(**_valid_kwargs(status="partial")).weight == 0.5
    assert GutmaWorkItem(**_valid_kwargs(status="gap", sdacs_module=None)).weight == 0.0


def test_item_is_frozen():
    item = GUTMA_WORK_ITEMS[0]
    with pytest.raises(Exception):
        item.status = "gap"  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# 조회 API
# --------------------------------------------------------------------------- #
def test_find_work_item_found():
    item = find_work_item("flight_declaration")
    assert item.name == "Flight Declaration Protocol"


def test_find_work_item_missing():
    with pytest.raises(KeyError):
        find_work_item("nope")


def test_items_by_group_sorted():
    items = items_by_group("FDP")
    assert all(i.group == "FDP" for i in items)
    assert list(items) == sorted(items, key=lambda i: i.item_id)


def test_items_by_group_invalid():
    with pytest.raises(ValueError):
        items_by_group("ZZZ")


def test_items_by_status_sorted():
    items = items_by_status("ready")
    assert all(i.status == "ready" for i in items)
    assert list(items) == sorted(items, key=lambda i: i.item_id)


def test_items_by_status_invalid():
    with pytest.raises(ValueError):
        items_by_status("unknown")


def test_gaps_matches_status():
    assert gaps() == items_by_status("gap")


# --------------------------------------------------------------------------- #
# ContributionReport
# --------------------------------------------------------------------------- #
def test_report_counts_sum_to_total():
    r = contribution_report()
    assert r.ready + r.partial + r.gaps == r.total
    assert r.total == len(GUTMA_WORK_ITEMS)


def test_report_score_in_range():
    r = contribution_report()
    assert 0.0 <= r.score <= 1.0
    assert r.score_pct == pytest.approx(100.0 * r.score)


def test_report_contributable():
    r = contribution_report()
    assert r.contributable == r.ready + r.partial


def test_report_by_group_total_matches():
    r = contribution_report()
    group_total = sum(tot for _impl, tot in r.by_group.values())
    assert group_total == r.total


def test_report_by_group_is_readonly():
    r = contribution_report()
    with pytest.raises(TypeError):
        r.by_group["FDP"] = (0, 0)  # type: ignore[index]


def test_report_score_matches_weights():
    r = contribution_report()
    expected = sum(i.weight for i in GUTMA_WORK_ITEMS) / len(GUTMA_WORK_ITEMS)
    assert r.score == pytest.approx(expected)


def test_report_rejects_inconsistent_counts():
    with pytest.raises(ValueError):
        ContributionReport(total=5, ready=1, partial=1, gaps=1, score=0.5,
                           by_group={})


def test_report_rejects_out_of_range_score():
    from types import MappingProxyType
    with pytest.raises(ValueError):
        ContributionReport(total=1, ready=1, partial=0, gaps=0, score=2.0,
                           by_group=MappingProxyType({"FDP": (1, 1)}))


def test_report_rejects_group_total_mismatch():
    from types import MappingProxyType
    with pytest.raises(ValueError):
        ContributionReport(total=2, ready=2, partial=0, gaps=0, score=1.0,
                           by_group=MappingProxyType({"FDP": (1, 1)}))


def test_report_rejects_contributable_exceeds_group_total():
    from types import MappingProxyType
    with pytest.raises(ValueError):
        ContributionReport(total=2, ready=2, partial=0, gaps=0, score=1.0,
                           by_group=MappingProxyType({"FDP": (99, 2)}))


# --------------------------------------------------------------------------- #
# contribution_matrix (도구 간 교환)
# --------------------------------------------------------------------------- #
def test_matrix_row_count():
    assert len(contribution_matrix()) == len(GUTMA_WORK_ITEMS)


def test_matrix_keys():
    expected = {"item_id", "name", "group", "status", "can_contribute",
                "spec_ref", "sdacs_module"}
    for row in contribution_matrix():
        assert set(row) == expected


def test_matrix_grouped_order():
    group_order = list(WORKING_GROUPS)
    rows = contribution_matrix()
    seen_index = [group_order.index(str(r["group"])) for r in rows]
    assert seen_index == sorted(seen_index)


def test_matrix_gap_module_none():
    for row in contribution_matrix():
        if row["status"] == "gap":
            assert row["sdacs_module"] is None
            assert row["can_contribute"] is False


def test_matrix_rows_are_readonly():
    """각 행은 MappingProxyType 읽기 전용이어야 한다."""
    for row in contribution_matrix():
        with pytest.raises(TypeError):
            row["item_id"] = "hacked"  # type: ignore[index]


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def test_cli_default(capsys):
    assert main([]) == 0
    assert "준비도" in capsys.readouterr().out


def test_cli_matrix(capsys):
    assert main(["--matrix"]) == 0
    assert "매트릭스" in capsys.readouterr().out


def test_cli_report(capsys):
    assert main(["--report"]) == 0
    assert "준비도" in capsys.readouterr().out


def test_cli_group(capsys):
    assert main(["--group", "FDP"]) == 0
    assert "flight_declaration" in capsys.readouterr().out


def test_cli_gaps(capsys):
    assert main(["--gaps"]) == 0
    out = capsys.readouterr().out
    assert out.strip()


def test_cli_groups(capsys):
    assert main(["--groups"]) == 0
    out = capsys.readouterr().out
    for group in WORKING_GROUPS:
        assert group in out
