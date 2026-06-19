"""ODYSSEY Phase 489 — 아카이브 이중화 정책 테스트.

핵심 계약 검증: 아카이브별 식별자 형식·예치 판정 우선순위(위치자 없는
주장은 INVALID)·custodian 독립성 집계·이중화 판정(POLICY_MATRIX 와
assess 의 일치)·결정론·매니페스트 JSON 직렬화·리포 현 상태 정직성.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import pytest

from simulation.archive_redundancy import (
    ARCHIVE_INSTITUTIONAL,
    ARCHIVE_SOFTWARE_HERITAGE,
    ARCHIVE_ZENODO,
    DEPOSIT_INVALID,
    DEPOSIT_PENDING,
    DEPOSIT_VERIFIED,
    KIND_CODE,
    KIND_DATA,
    MIN_INDEPENDENT_CUSTODIANS,
    POLICY_MATRIX,
    STATUS_DEPOSITED,
    STATUS_PLANNED,
    STATUS_VERIFIED,
    VERDICT_AT_RISK,
    VERDICT_PARTIAL,
    VERDICT_REDUNDANT,
    ArchiveDeposit,
    assess_redundancy,
    deposit_state,
    identifier_valid,
    policy_manifest,
    preservation_prerequisites,
    shipped_registry,
)

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _verified(archive: str, kinds: tuple[str, ...], ident: str,
              custodian: str | None = None) -> ArchiveDeposit:
    return ArchiveDeposit(archive, kinds, identifier=ident,
                          status=STATUS_VERIFIED, custodian=custodian)


# --- 식별자 형식 -----------------------------------------------------------

@pytest.mark.parametrize("ident", [
    "10.5281/zenodo.1234567",
    "10.5281/zenodo.1",
])
def test_zenodo_doi_valid(ident: str) -> None:
    assert identifier_valid(ARCHIVE_ZENODO, ident)


@pytest.mark.parametrize("ident", [
    "10.5281/zenodo.",      # 숫자 없음
    "10.5281/zenodo.abc",   # 비숫자
    "zenodo.1234567",       # 접두 누락
    "10.1234/zenodo.1",     # 잘못된 prefix
    "https://doi.org/10.5281/zenodo.1",  # URL 형태 비허용
])
def test_zenodo_doi_invalid(ident: str) -> None:
    assert not identifier_valid(ARCHIVE_ZENODO, ident)


def test_swhid_valid() -> None:
    assert identifier_valid(ARCHIVE_SOFTWARE_HERITAGE, "swh:1:dir:" + "0" * 40)
    assert identifier_valid(ARCHIVE_SOFTWARE_HERITAGE, "swh:1:rev:" + "a" * 40)


@pytest.mark.parametrize("ident", [
    "swh:1:dir:" + "a" * 39,   # 너무 짧음
    "swh:1:dir:" + "g" * 40,   # 비 hex
    "swh:1:dir:" + "A" * 40,   # 대문자 hex (SWHID 는 소문자 전용)
    "swh:1:xxx:" + "a" * 40,   # 잘못된 객체 타입
    "swh:2:dir:" + "a" * 40,   # 잘못된 버전
])
def test_swhid_invalid(ident: str) -> None:
    assert not identifier_valid(ARCHIVE_SOFTWARE_HERITAGE, ident)


def test_handle_valid() -> None:
    assert identifier_valid(ARCHIVE_INSTITUTIONAL, "20.500.12345/sdacs-2026")


@pytest.mark.parametrize("ident", [
    "nopath",                            # 슬래시 없음
    "has space/x",                       # 내부 공백
    "/leadingslash",                     # 접두 비공백 누락
    "https://repo.uni.edu/datasets/x",   # URL — 영구 핸들 아님
    "prefix/sub/path",                   # 다중 슬래시
    "10.5281/zenodo.1234567",            # Zenodo DOI — 기관 핸들 아님(DOI 네임스페이스)
    "10.1234/foo",                       # 임의 DOI 접두 — 기관 핸들로 오인 금지
])
def test_handle_invalid(ident: str) -> None:
    assert not identifier_valid(ARCHIVE_INSTITUTIONAL, ident)


def test_doi_not_accepted_as_institutional_handle() -> None:
    # 정직성 결속: 한 archive 의 식별자를 다른 archive 형식으로 오인하지 않는다.
    # 순수 숫자 핸들 접두(20.x)는 여전히 유효해야 한다.
    assert identifier_valid(ARCHIVE_INSTITUTIONAL, "20.500.12345/sdacs-2026")
    assert not identifier_valid(ARCHIVE_INSTITUTIONAL, "10.5281/zenodo.42")


def test_identifier_empty_or_unknown_archive_invalid() -> None:
    assert not identifier_valid(ARCHIVE_ZENODO, None)
    assert not identifier_valid(ARCHIVE_ZENODO, "")
    assert not identifier_valid(ARCHIVE_ZENODO, "   ")
    assert not identifier_valid("dropbox", "10.5281/zenodo.1")


# --- 예치 판정 -------------------------------------------------------------

def test_planned_is_pending() -> None:
    d = ArchiveDeposit(ARCHIVE_ZENODO, (KIND_CODE,), status=STATUS_PLANNED)
    assert deposit_state(d) == DEPOSIT_PENDING


def test_deposited_without_identifier_is_invalid() -> None:
    # 위치자 없는 예치 주장은 검증됨으로 인정하지 않는다(정직성).
    d = ArchiveDeposit(ARCHIVE_ZENODO, (KIND_CODE,), identifier=None,
                       status=STATUS_DEPOSITED)
    assert deposit_state(d) == DEPOSIT_INVALID


def test_verified_with_bad_identifier_is_invalid() -> None:
    d = ArchiveDeposit(ARCHIVE_ZENODO, (KIND_CODE,), identifier="not-a-doi",
                       status=STATUS_VERIFIED)
    assert deposit_state(d) == DEPOSIT_INVALID


def test_valid_identifier_is_verified() -> None:
    d = _verified(ARCHIVE_ZENODO, (KIND_CODE, KIND_DATA), "10.5281/zenodo.42")
    assert deposit_state(d) == DEPOSIT_VERIFIED


def test_unknown_archive_status_kind_invalid() -> None:
    assert deposit_state(
        ArchiveDeposit("dropbox", (KIND_CODE,), "x/y", STATUS_VERIFIED)
    ) == DEPOSIT_INVALID
    assert deposit_state(
        ArchiveDeposit(ARCHIVE_ZENODO, (KIND_CODE,), "10.5281/zenodo.1",
                       status="archived")
    ) == DEPOSIT_INVALID
    assert deposit_state(
        ArchiveDeposit(ARCHIVE_ZENODO, (), "10.5281/zenodo.1", STATUS_VERIFIED)
    ) == DEPOSIT_INVALID
    assert deposit_state(
        ArchiveDeposit(ARCHIVE_ZENODO, ("audio",), "10.5281/zenodo.1",
                       STATUS_VERIFIED)
    ) == DEPOSIT_INVALID


# --- custodian 독립성 ------------------------------------------------------

def test_custodian_defaults_from_archive() -> None:
    assert ArchiveDeposit(ARCHIVE_ZENODO, (KIND_CODE,)).custodian_name() == "CERN"
    assert ArchiveDeposit(
        ARCHIVE_SOFTWARE_HERITAGE, (KIND_CODE,)
    ).custodian_name() == "Inria"


def test_same_custodian_counts_once() -> None:
    # 같은 기관(Zenodo=CERN)에 사본 둘 → 독립 custodian 1곳, 단일 실패점.
    deposits = (
        _verified(ARCHIVE_ZENODO, (KIND_CODE,), "10.5281/zenodo.1"),
        _verified(ARCHIVE_ZENODO, (KIND_DATA,), "10.5281/zenodo.2"),
    )
    result = assess_redundancy(deposits)
    assert result.verified_custodians == ("CERN",)
    assert result.verdict == VERDICT_PARTIAL  # 두 차원 덮어도 custodian 1곳


def test_custodian_override_creates_independence() -> None:
    deposits = (
        _verified(ARCHIVE_INSTITUTIONAL, (KIND_CODE, KIND_DATA), "20.1/a",
                  custodian="univ-A"),
        _verified(ARCHIVE_INSTITUTIONAL, (KIND_CODE, KIND_DATA), "20.2/b",
                  custodian="univ-B"),
    )
    result = assess_redundancy(deposits)
    assert result.verified_custodians == ("univ-A", "univ-B")
    assert result.verdict == VERDICT_REDUNDANT


# --- 이중화 판정 -----------------------------------------------------------

def test_empty_registry_at_risk() -> None:
    result = assess_redundancy(())
    assert result.verdict == VERDICT_AT_RISK
    assert result.verified_custodians == ()
    assert result.missing_kinds == (KIND_CODE, KIND_DATA)
    assert not result.is_durable()


def test_two_custodians_both_dims_redundant() -> None:
    deposits = (
        _verified(ARCHIVE_ZENODO, (KIND_CODE, KIND_DATA), "10.5281/zenodo.9"),
        _verified(ARCHIVE_SOFTWARE_HERITAGE, (KIND_CODE,),
                  "swh:1:dir:" + "b" * 40),
    )
    result = assess_redundancy(deposits)
    assert result.verdict == VERDICT_REDUNDANT
    assert result.is_durable()
    assert result.missing_kinds == ()
    assert set(result.verified_custodians) == {"CERN", "Inria"}


def test_two_custodians_missing_data_dim_partial() -> None:
    # 두 custodian 이나 둘 다 code 만 → 데이터 차원 미덮임.
    deposits = (
        _verified(ARCHIVE_ZENODO, (KIND_CODE,), "10.5281/zenodo.9"),
        _verified(ARCHIVE_SOFTWARE_HERITAGE, (KIND_CODE,),
                  "swh:1:dir:" + "c" * 40),
    )
    result = assess_redundancy(deposits)
    assert result.verdict == VERDICT_PARTIAL
    assert result.missing_kinds == (KIND_DATA,)


def test_invalid_deposits_excluded_from_assessment() -> None:
    # 검증 실패 예치는 집계에서 빠진다 → 유효 사본 0 → AT_RISK.
    deposits = (
        ArchiveDeposit(ARCHIVE_ZENODO, (KIND_CODE,), None, STATUS_DEPOSITED),
        ArchiveDeposit(ARCHIVE_SOFTWARE_HERITAGE, (KIND_CODE,), "bad",
                       STATUS_VERIFIED),
    )
    result = assess_redundancy(deposits)
    assert result.verdict == VERDICT_AT_RISK


# --- POLICY_MATRIX ↔ assess 일치 (중복 로직 없음 강제) --------------------

def test_matrix_has_all_cells() -> None:
    for bucket in ("0", "1", ">=2"):
        for both in (False, True):
            assert (bucket, both) in POLICY_MATRIX


def _registry_for(custodian_count: int, both_dims: bool
                  ) -> tuple[ArchiveDeposit, ...]:
    """원하는 (독립 custodian 수, 양차원 여부)를 내는 합성 레지스트리."""
    if custodian_count == 0:
        return ()
    kinds_cycle = ([KIND_CODE, KIND_DATA] if both_dims else [KIND_CODE])
    deposits = []
    for i in range(custodian_count):
        deposits.append(
            ArchiveDeposit(
                ARCHIVE_INSTITUTIONAL,
                tuple(kinds_cycle),
                identifier=f"20.{i}/x",
                status=STATUS_VERIFIED,
                custodian=f"org-{i}",
            )
        )
    return tuple(deposits)


@pytest.mark.parametrize("custodian_count,both_dims", [
    (0, False), (0, True), (1, False), (1, True), (2, False), (2, True),
    (3, True),
])
def test_assess_matches_matrix(custodian_count: int, both_dims: bool) -> None:
    bucket = "0" if custodian_count == 0 else ("1" if custodian_count == 1
                                               else ">=2")
    expected = POLICY_MATRIX[(bucket, both_dims)]
    result = assess_redundancy(_registry_for(custodian_count, both_dims))
    assert result.verdict == expected


def test_redundant_requires_min_custodians_constant() -> None:
    assert MIN_INDEPENDENT_CUSTODIANS == 2


# --- 결정론 ----------------------------------------------------------------

def test_deterministic() -> None:
    deposits = (
        _verified(ARCHIVE_ZENODO, (KIND_CODE, KIND_DATA), "10.5281/zenodo.9"),
        _verified(ARCHIVE_SOFTWARE_HERITAGE, (KIND_CODE,),
                  "swh:1:dir:" + "d" * 40),
    )
    runs = [assess_redundancy(deposits) for _ in range(5)]
    assert all(r == runs[0] for r in runs)


def test_order_independent() -> None:
    deposits = [
        _verified(ARCHIVE_ZENODO, (KIND_DATA,), "10.5281/zenodo.9"),
        _verified(ARCHIVE_SOFTWARE_HERITAGE, (KIND_CODE,),
                  "swh:1:dir:" + "e" * 40),
    ]
    verdicts = {
        assess_redundancy(tuple(p)).verdict
        for p in itertools.permutations(deposits)
    }
    assert verdicts == {VERDICT_REDUNDANT}


# --- 매니페스트 ------------------------------------------------------------

def test_manifest_json_serializable() -> None:
    manifest = policy_manifest()
    encoded = json.dumps(manifest, ensure_ascii=False)
    assert json.loads(encoded) == manifest
    assert manifest["min_independent_custodians"] == MIN_INDEPENDENT_CUSTODIANS
    assert len(manifest["matrix"]) == len(POLICY_MATRIX)


# --- 리포 현 상태 정직성 ---------------------------------------------------

def test_shipped_registry_is_honestly_at_risk() -> None:
    # 메타데이터는 준비됐으나 DOI 미발급 — 정직한 현 판정은 AT_RISK.
    result = assess_redundancy(shipped_registry())
    assert result.verdict == VERDICT_AT_RISK
    assert result.verified_custodians == ()


def test_preservation_prerequisites_present_on_disk() -> None:
    prereqs = preservation_prerequisites(_REPO_ROOT)
    assert prereqs[".zenodo.json"] is True
    assert prereqs["CITATION.cff"] is True
    assert prereqs["docs/REPRODUCIBILITY.md"] is True


def test_preservation_prerequisites_missing_dir() -> None:
    prereqs = preservation_prerequisites(_REPO_ROOT / "does-not-exist")
    assert all(v is False for v in prereqs.values())
