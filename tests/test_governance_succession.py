"""ODYSSEY Phase 487 — 유지보수자 승계 규약 정책 테스트.

핵심 계약 검증: 연속성 보유자 판정(merge+admin+active 동시 필요)·bus factor
고유 집계·단계 분류·승계 판정 우선순위(1인이면 문서 완비라도 BUS_FACTOR_RISK)·
POLICY_MATRIX 와 assess 의 일치·결정론·매니페스트 JSON 직렬화·리포 현 상태
정직성.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import pytest

from simulation.governance_succession import (
    MIN_COMMITTEE_SIZE,
    POLICY_MATRIX,
    ROLE_CO,
    ROLE_EMERITUS,
    ROLE_PRINCIPAL,
    ROLE_RESERVE,
    STAGE_ABANDONED,
    STAGE_BDFL,
    STAGE_COMMITTEE,
    STAGE_DUAL,
    VERDICT_ABANDONED,
    VERDICT_BUS_FACTOR_RISK,
    VERDICT_COMMITTEE_READY,
    VERDICT_TRANSITIONAL,
    Maintainer,
    assess_succession,
    bus_factor,
    classify_stage,
    documents_complete,
    governance_documents,
    is_continuity_holder,
    main,
    policy_manifest,
    shipped_maintainers,
)

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _holder(handle: str, role: str = ROLE_CO) -> Maintainer:
    return Maintainer(handle, role, active=True,
                      has_merge_rights=True, has_admin_access=True)


# --- 연속성 보유자 판정 ----------------------------------------------------

def test_holder_requires_merge_and_admin_and_active() -> None:
    assert is_continuity_holder(_holder("a"))


@pytest.mark.parametrize("merge,admin,active", [
    (True, True, False),   # 비활성
    (True, False, True),   # admin 없음
    (False, True, True),   # merge 없음
    (False, False, True),  # 둘 다 없음
])
def test_holder_rejects_partial_authority(
    merge: bool, admin: bool, active: bool
) -> None:
    m = Maintainer("x", ROLE_CO, active=active,
                   has_merge_rights=merge, has_admin_access=admin)
    assert not is_continuity_holder(m)


def test_holder_rejects_empty_handle() -> None:
    m = Maintainer("   ", ROLE_PRINCIPAL, True, True, True)
    assert not is_continuity_holder(m)


def test_holder_rejects_unknown_role() -> None:
    m = Maintainer("x", "overlord", True, True, True)
    assert not is_continuity_holder(m)


def test_emeritus_inactive_not_holder() -> None:
    m = Maintainer("retired", ROLE_EMERITUS, active=False,
                   has_merge_rights=False, has_admin_access=False)
    assert not is_continuity_holder(m)


def test_emeritus_with_full_rights_not_holder() -> None:
    """역할이 emeritus면 권한 전부 있어도 연속성 보유자 아님 — 정책 문서와 일치."""
    m = Maintainer("ghost", ROLE_EMERITUS, active=True,
                   has_merge_rights=True, has_admin_access=True)
    assert not is_continuity_holder(m)


# --- bus factor / 단계 -----------------------------------------------------

def test_bus_factor_counts_unique_holders() -> None:
    ms = (_holder("a"), _holder("b"), _holder("c"))
    assert bus_factor(ms) == 3


def test_bus_factor_dedupes_same_handle() -> None:
    ms = (_holder("a"), _holder(" a "), _holder("b"))
    assert bus_factor(ms) == 2


def test_bus_factor_ignores_non_holders() -> None:
    ms = (
        _holder("a"),
        Maintainer("b", ROLE_RESERVE, True, True, False),  # admin 없음
    )
    assert bus_factor(ms) == 1


@pytest.mark.parametrize("count,stage", [
    (0, STAGE_ABANDONED),
    (1, STAGE_BDFL),
    (2, STAGE_DUAL),
    (3, STAGE_COMMITTEE),
    (9, STAGE_COMMITTEE),
])
def test_classify_stage(count: int, stage: str) -> None:
    assert classify_stage(count) == stage


# --- 승계 판정 -------------------------------------------------------------

def test_zero_holders_abandoned() -> None:
    result = assess_succession((), docs_complete=True)
    assert result.verdict == VERDICT_ABANDONED
    assert result.holder_count == 0
    assert not result.is_ready()


def test_single_holder_bus_factor_risk_even_with_docs() -> None:
    """문서가 완비돼도 1인이면 단일 실패점 — 문서가 사람을 대체하지 않는다."""
    result = assess_succession((_holder("a", ROLE_PRINCIPAL),),
                               docs_complete=True)
    assert result.verdict == VERDICT_BUS_FACTOR_RISK
    assert result.stage == STAGE_BDFL


def test_two_holders_transitional_regardless_of_docs() -> None:
    ms = (_holder("a"), _holder("b"))
    for docs in (True, False):
        result = assess_succession(ms, docs_complete=docs)
        assert result.verdict == VERDICT_TRANSITIONAL
        assert result.stage == STAGE_DUAL


def test_committee_without_docs_transitional() -> None:
    ms = (_holder("a"), _holder("b"), _holder("c"))
    result = assess_succession(ms, docs_complete=False)
    assert result.verdict == VERDICT_TRANSITIONAL
    assert result.stage == STAGE_COMMITTEE
    assert any("문서 미완비" in r for r in result.reasons)


def test_committee_with_docs_ready() -> None:
    ms = (_holder("a"), _holder("b"), _holder("c"))
    result = assess_succession(ms, docs_complete=True)
    assert result.verdict == VERDICT_COMMITTEE_READY
    assert result.is_ready()
    assert result.holders == ("a", "b", "c")


def test_min_committee_size_boundary() -> None:
    """정족 미만(2) → TRANSITIONAL, 정족(3) → READY 경계."""
    holders = [_holder(chr(ord("a") + i)) for i in range(MIN_COMMITTEE_SIZE)]
    below = assess_succession(tuple(holders[:-1]), docs_complete=True)
    at = assess_succession(tuple(holders), docs_complete=True)
    assert below.verdict == VERDICT_TRANSITIONAL
    assert at.verdict == VERDICT_COMMITTEE_READY


# --- POLICY_MATRIX ↔ assess 일치 -------------------------------------------

def _make_holders(n: int) -> tuple[Maintainer, ...]:
    return tuple(_holder(f"m{i}") for i in range(n))


@pytest.mark.parametrize("bucket,count", [
    ("0", 0), ("1", 1), ("2", 2), (">=3", 3), (">=3", 5),
])
@pytest.mark.parametrize("docs", [True, False])
def test_matrix_matches_assess(bucket: str, count: int, docs: bool) -> None:
    expected = POLICY_MATRIX[(bucket, docs)]
    result = assess_succession(_make_holders(count), docs_complete=docs)
    assert result.verdict == expected


def test_matrix_covers_all_buckets() -> None:
    buckets = {"0", "1", "2", ">=3"}
    assert {b for (b, _) in POLICY_MATRIX} == buckets
    assert len(POLICY_MATRIX) == len(buckets) * 2  # docs True/False


# --- 결정론 ----------------------------------------------------------------

def test_deterministic() -> None:
    ms = (_holder("c"), _holder("a"), _holder("b"))
    first = assess_succession(ms, docs_complete=True)
    second = assess_succession(ms, docs_complete=True)
    assert first == second
    assert first.holders == ("a", "b", "c")  # 정렬 안정성


# --- 매니페스트 ------------------------------------------------------------

def test_manifest_json_serializable() -> None:
    manifest = policy_manifest()
    dumped = json.dumps(manifest, ensure_ascii=False)
    assert json.loads(dumped) == manifest


def test_manifest_matrix_matches_policy() -> None:
    manifest = policy_manifest()
    from_manifest = {
        (row["holder_bucket"], row["docs_complete"]): row["verdict"]
        for row in manifest["matrix"]
    }
    assert from_manifest == POLICY_MATRIX
    assert manifest["min_committee_size"] == MIN_COMMITTEE_SIZE


# --- 리포 현 상태 정직성 ---------------------------------------------------

def test_governance_documents_reports_disk_state() -> None:
    docs = governance_documents(_REPO_ROOT)
    # 세 거버넌스 문서 모두 리포에 실재한다(본 Phase 가 프로토콜 문서 추가).
    assert docs["CONTRIBUTING.md"] is True
    assert docs["SECURITY.md"] is True
    assert docs["docs/standards/MAINTAINER_SUCCESSION_PROTOCOL.md"] is True


def test_two_holders_docs_complete_reason_explicit() -> None:
    """2인+문서완비 시 '보유자 추가만 남음' 진단이 요약에 드러난다(MEDIUM)."""
    result = assess_succession((_holder("a"), _holder("b")), docs_complete=True)
    assert any("추가만 남음" in r for r in result.reasons)


def test_shipped_status_is_bus_factor_risk() -> None:
    """현 리포는 원저자 1인(BDFL) — 정직한 판정은 BUS_FACTOR_RISK."""
    result = assess_succession(
        shipped_maintainers(),
        docs_complete=documents_complete(_REPO_ROOT),
    )
    assert result.verdict == VERDICT_BUS_FACTOR_RISK
    assert result.holder_count == 1


def test_shipped_pin_breaks_when_second_holder_added() -> None:
    """둘째 연속성 보유자 추가 시 1인 가정이 깨지도록 핀(방향: 상태 개선 시)."""
    assert bus_factor(shipped_maintainers()) == 1


# --- CLI -------------------------------------------------------------------

@pytest.mark.parametrize("flag", ["--policy", "--demo", "--status", "--manifest"])
def test_cli_known_flags_succeed(flag: str) -> None:
    assert main([flag]) == 0


def test_cli_default_is_policy() -> None:
    assert main([]) == 0


def test_cli_unknown_flag_errors() -> None:
    assert main(["--bogus"]) == 2


def test_cli_manifest_outputs_valid_json(capsys: pytest.CaptureFixture) -> None:
    main(["--manifest"])
    out = capsys.readouterr().out
    assert json.loads(out)["schema"] == "sdacs-governance-succession"
