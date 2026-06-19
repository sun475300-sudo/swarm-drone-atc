"""ODYSSEY Phase 489 — 아카이브 이중화 정책.

Continuum 트랙(Phase 481-500)의 한 칸. 졸업 후 10년, 프로젝트가 *단일
보관처의 실패로 소실되지 않으려면* 서로 독립적인 보관처에 사본이 있어야
한다. 본 모듈은 "현재 아카이브 이중화가 단일 실패점(single point of
failure) 없이 충분한가" 를 사람이 매번 직관으로 판단하지 않도록 *결정적
정책*으로 명문화한다 — 같은 입력은 항상 같은 판정을 낸다.

설계 원칙
--------
- **정책은 코드, 코드는 정책**: 이중화 충분성 판정 규칙을 문서(``docs/
  standards/ARCHIVE_REDUNDANCY_POLICY.md``)와 본 평가기에 *한 번씩만* 적기
  위해, 본 모듈이 유일한 실행 가능 명세다. 문서는 규칙을 서술할 뿐 중복
  로직을 두지 않는다(테스트가 ``POLICY_MATRIX`` ↔ ``assess`` 일치 강제).
- **자문이지 집행 아님**: 본 모듈은 *현 상태를 판정*할 뿐 실제로 사본을
  업로드하지 않는다(부수효과 0). 사람/CI 가 실제 예치를 집행한다.
- **위치자 없는 주장은 예치가 아님**: 식별자(DOI·SWHID·핸들)가 없거나
  형식이 어긋난 예치 주장은 *검증됨* 으로 인정하지 않는다(정직성).
- **독립 보관처 우선**: 같은 기관(custodian)에 사본이 둘이어도 단일 실패점
  이다. 이중화는 *서로 다른 custodian* 으로 세고, 코드·데이터 두 차원을
  모두 덮어야 충분(REDUNDANT)하다.

무작위성 0 · 결정적 · 기존 모듈 무수정 순수 추가.

CLI:
    python -m simulation.archive_redundancy --policy     # 정책 매트릭스 출력
    python -m simulation.archive_redundancy --demo       # 예시 평가
    python -m simulation.archive_redundancy --status     # 리포 현 상태 판정
    python -m simulation.archive_redundancy --manifest   # 정책 매니페스트(JSON)
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# --- 아카이브(보관처) ------------------------------------------------------
ARCHIVE_ZENODO = "zenodo"                    # CERN 운영 · 버전 DOI
ARCHIVE_SOFTWARE_HERITAGE = "software_heritage"  # Inria 운영 · 소스 SWHID
ARCHIVE_INSTITUTIONAL = "institutional"      # 대학 기관 리포지터리 · 핸들

_ARCHIVES = (ARCHIVE_ZENODO, ARCHIVE_SOFTWARE_HERITAGE, ARCHIVE_INSTITUTIONAL)

# 아카이브 → 운영 기관(custodian). 독립성은 custodian 으로 센다. 같은
# custodian 의 사본 둘은 단일 실패점이므로 하나로 본다.
_DEFAULT_CUSTODIAN: dict[str, str] = {
    ARCHIVE_ZENODO: "CERN",
    ARCHIVE_SOFTWARE_HERITAGE: "Inria",
    ARCHIVE_INSTITUTIONAL: "university",
}

# --- 보존 차원 -------------------------------------------------------------
KIND_CODE = "code"  # 소스 코드 스냅샷(재빌드 가능성)
KIND_DATA = "data"  # 결과/데이터/문서 산출물(재현 검증 가능성)

_KINDS = (KIND_CODE, KIND_DATA)

# --- 예치 상태(주장) -------------------------------------------------------
STATUS_PLANNED = "planned"      # 계획만 됨 — 아직 업로드 안 함
STATUS_DEPOSITED = "deposited"  # 업로드함 — 식별자 발급 주장
STATUS_VERIFIED = "verified"    # 업로드 + 식별자 확인됨

_STATUSES = (STATUS_PLANNED, STATUS_DEPOSITED, STATUS_VERIFIED)

# --- 예치 판정(평가 결과) --------------------------------------------------
DEPOSIT_VERIFIED = "VERIFIED"  # 내구 사본으로 인정
DEPOSIT_PENDING = "PENDING"    # 계획 단계 — 아직 사본 아님
DEPOSIT_INVALID = "INVALID"    # 예치 주장하나 식별자 없음/형식 오류

# --- 이중화 판정(레지스트리 결과) ------------------------------------------
VERDICT_REDUNDANT = "REDUNDANT"  # 단일 실패점 없음 — 충분
VERDICT_PARTIAL = "PARTIAL"      # 일부 내구 사본 있으나 기준 미달
VERDICT_AT_RISK = "AT_RISK"      # 내구 사본 0 — 소실 위험

# 이중화 충분(REDUNDANT)의 필요조건: 서로 다른 custodian 최소 2곳 + 코드·
# 데이터 두 차원 모두 검증된 사본으로 덮임.
MIN_INDEPENDENT_CUSTODIANS = 2

# 식별자 형식(결정적). 형식이 어긋나면 INVALID 로 강등(정직성).
# Zenodo concept/version DOI: 10.5281/zenodo.<digits>
_ZENODO_DOI = re.compile(r"^10\.5281/zenodo\.\d+$")
# SWHID(core, 한정자 없음): swh:1:(cnt|dir|rev|rel|snp):<40 hex>
_SWHID = re.compile(r"^swh:1:(?:cnt|dir|rev|rel|snp):[0-9a-f]{40}$")
# Handle.net 스타일 기관 핸들: <prefix>/<suffix> (정확히 슬래시 1개, 양쪽
# 모두 비공백·슬래시 불가). URL(`https://.../x`)·다중 경로(`p/sub/x`)는 핸들이
# 아니므로 거부 — 위치자처럼 보이는 비핸들을 VERIFIED 로 오인하지 않는다.
_HANDLE = re.compile(r"^[^\s/]+/[^\s/]+$")

_IDENTIFIER_PATTERN: dict[str, re.Pattern[str]] = {
    ARCHIVE_ZENODO: _ZENODO_DOI,
    ARCHIVE_SOFTWARE_HERITAGE: _SWHID,
    ARCHIVE_INSTITUTIONAL: _HANDLE,
}


def identifier_valid(archive: str, identifier: str | None) -> bool:
    """아카이브별 식별자 형식이 유효한지 결정적으로 판정한다.

    빈 값/None 은 무효. 알 수 없는 아카이브도 무효(정책 적용 불가).
    앞뒤 공백은 무시한다(lenient) — 내부 공백은 패턴이 거부한다.
    """
    if not identifier or not identifier.strip():
        return False
    pattern = _IDENTIFIER_PATTERN.get(archive)
    if pattern is None:
        return False
    return pattern.match(identifier.strip()) is not None


@dataclass(frozen=True)
class ArchiveDeposit:
    """단일 아카이브 예치 한 건(불변).

    Attributes:
        archive: ``zenodo``·``software_heritage``·``institutional`` 중 하나.
        kinds: 이 예치가 덮는 보존 차원(``code``·``data`` 일부/전부).
        identifier: 발급된 영구 식별자(DOI·SWHID·핸들). 없으면 None.
        status: ``planned``·``deposited``·``verified``.
        custodian: 운영 기관. None 이면 아카이브 기본값으로 본다.
    """

    archive: str
    kinds: tuple[str, ...]
    identifier: str | None = None
    status: str = STATUS_PLANNED
    custodian: str | None = None

    def custodian_name(self) -> str:
        """독립성 계산에 쓰는 custodian 이름(기본값 폴백)."""
        if self.custodian and self.custodian.strip():
            return self.custodian.strip()
        return _DEFAULT_CUSTODIAN.get(self.archive, self.archive)


def deposit_state(deposit: ArchiveDeposit) -> str:
    """단일 예치의 판정을 결정적으로 산출한다.

    판정 순서(먼저 매칭되는 규칙이 결과):
        1. 알 수 없는 아카이브/상태/차원 → INVALID(정책 적용 불가).
        2. 차원 미지정 → INVALID(무엇을 보존하는지 불명).
        3. 상태 planned → PENDING(아직 사본 아님, 식별자 유무 무관 — 이 규칙이
           모든 planned 케이스를 소진한다).
        4. (deposited·verified) 식별자 무효/누락 → INVALID
           (위치자 없는 주장은 예치로 인정 안 함).
        5. 식별자 유효 → VERIFIED.
    """
    if deposit.archive not in _ARCHIVES:
        return DEPOSIT_INVALID
    if deposit.status not in _STATUSES:
        return DEPOSIT_INVALID
    if not deposit.kinds or any(k not in _KINDS for k in deposit.kinds):
        return DEPOSIT_INVALID
    if deposit.status == STATUS_PLANNED:
        return DEPOSIT_PENDING
    if not identifier_valid(deposit.archive, deposit.identifier):
        return DEPOSIT_INVALID
    return DEPOSIT_VERIFIED


@dataclass(frozen=True)
class RedundancyAssessment:
    """레지스트리 전체의 이중화 판정 결과(불변)."""

    verdict: str
    verified_custodians: tuple[str, ...]   # 정렬된 고유 custodian
    covered_kinds: tuple[str, ...]         # 정렬된 고유 차원
    missing_kinds: tuple[str, ...]         # 충분성에 부족한 차원
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def is_durable(self) -> bool:
        """단일 실패점 없는 충분한 이중화인가."""
        return self.verdict == VERDICT_REDUNDANT

    def summary(self) -> str:
        """사람이 읽는 한 줄 요약."""
        return f"{self.verdict}: {'; '.join(self.reasons)}"


def _custodian_bucket(count: int) -> str:
    """독립 custodian 수를 정책 매트릭스 버킷으로 사상한다."""
    if count <= 0:
        return "0"
    if count == 1:
        return "1"
    return ">=2"


def _verdict_for(custodian_count: int, both_dims: bool) -> str:
    """판정 핵심 규칙(매트릭스의 권위 있는 구현)."""
    if custodian_count <= 0:
        return VERDICT_AT_RISK
    if custodian_count >= MIN_INDEPENDENT_CUSTODIANS and both_dims:
        return VERDICT_REDUNDANT
    return VERDICT_PARTIAL


def assess_redundancy(deposits: tuple[ArchiveDeposit, ...]) -> RedundancyAssessment:
    """예치 레지스트리 전체의 이중화 충분성을 결정적으로 판정한다.

    VERIFIED 예치만 내구 사본으로 집계한다. 독립성은 custodian 으로 세며
    (같은 기관 둘=하나), 코드·데이터 두 차원을 *서로 다른 custodian* 최소
    2곳이 덮어야 REDUNDANT.
    """
    verified = tuple(d for d in deposits if deposit_state(d) == DEPOSIT_VERIFIED)
    custodians = tuple(sorted({d.custodian_name() for d in verified}))
    covered = tuple(
        k for k in _KINDS if any(k in d.kinds for d in verified)
    )
    missing = tuple(k for k in _KINDS if k not in covered)
    both_dims = not missing

    verdict = _verdict_for(len(custodians), both_dims)

    reasons: list[str] = []
    if not verified:
        reasons.append("검증된 내구 사본 0 — 소실 위험(단일 리포 의존)")
    else:
        reasons.append(
            f"독립 custodian {len(custodians)}곳({', '.join(custodians)}) · "
            f"차원 {', '.join(covered) or '없음'}"
        )
        if verdict != VERDICT_REDUNDANT:
            if len(custodians) < MIN_INDEPENDENT_CUSTODIANS:
                reasons.append(
                    f"독립 custodian {MIN_INDEPENDENT_CUSTODIANS}곳 미만 — 단일 실패점"
                )
            if missing:
                reasons.append(f"미덮인 차원: {', '.join(missing)}")

    return RedundancyAssessment(
        verdict=verdict,
        verified_custodians=custodians,
        covered_kinds=covered,
        missing_kinds=missing,
        reasons=tuple(reasons),
    )


# 정책 매트릭스. (custodian_bucket, both_dims) → verdict.
# assess_redundancy() 의 권위 있는 규칙을 사람이 한눈에 볼 수 있게 표로
# 투영한 것일 뿐, 판정은 항상 assess 가 내린다(테스트가 일치 강제).
POLICY_MATRIX: dict[tuple[str, bool], str] = {
    ("0", False): VERDICT_AT_RISK,
    ("0", True): VERDICT_AT_RISK,
    ("1", False): VERDICT_PARTIAL,
    ("1", True): VERDICT_PARTIAL,
    (">=2", False): VERDICT_PARTIAL,
    (">=2", True): VERDICT_REDUNDANT,
}


def policy_manifest() -> dict[str, Any]:
    """정책을 JSON 직렬화 가능한 매니페스트로 굳힌다."""
    return {
        "schema": "sdacs-archive-redundancy",
        "version": "1.0",
        "archives": list(_ARCHIVES),
        "custodians": dict(_DEFAULT_CUSTODIAN),
        "kinds": list(_KINDS),
        "verdicts": [VERDICT_REDUNDANT, VERDICT_PARTIAL, VERDICT_AT_RISK],
        "min_independent_custodians": MIN_INDEPENDENT_CUSTODIANS,
        "matrix": [
            {"custodian_bucket": bucket, "both_dims": both, "verdict": verdict}
            for (bucket, both), verdict in POLICY_MATRIX.items()
        ],
    }


# --- 리포 현 상태 정직 공시 ------------------------------------------------
# 디스크에 실재해야 예치를 *준비함* 으로 인정하는 보존 사전조건 파일.
_PREREQ_FILES = (".zenodo.json", "CITATION.cff", "docs/REPRODUCIBILITY.md")


def preservation_prerequisites(repo_root: str | Path) -> dict[str, bool]:
    """리포에 보존 사전조건 메타데이터가 실재하는지 디스크로 검증한다."""
    root = Path(repo_root)
    return {name: (root / name).is_file() for name in _PREREQ_FILES}


def shipped_registry() -> tuple[ArchiveDeposit, ...]:
    """리포의 *현 실제 상태* 를 정직하게 반영한 예치 레지스트리.

    ``.zenodo.json``·``CITATION.cff`` 메타데이터는 준비되어 있으나 첫 릴리스
    태그 전이라 DOI 가 발급되지 않았고(``.zenodo.json`` notes 명시), Software
    Heritage SWHID·기관 핸들도 미확인이다. 따라서 정직한 현 판정은 검증된
    내구 사본 0 → ``AT_RISK``. 메타데이터 준비를 예치 완료로 포장하지 않는다.
    """
    return (
        ArchiveDeposit(
            ARCHIVE_ZENODO, (KIND_CODE, KIND_DATA),
            identifier=None, status=STATUS_PLANNED,
        ),
        ArchiveDeposit(
            ARCHIVE_SOFTWARE_HERITAGE, (KIND_CODE,),
            identifier=None, status=STATUS_PLANNED,
        ),
        ArchiveDeposit(
            ARCHIVE_INSTITUTIONAL, (KIND_DATA,),
            identifier=None, status=STATUS_PLANNED,
        ),
    )


# 정책 동작을 보이는 결정적 예시(이중화 달성 시 형태).
_DEMO_DEPOSITS: tuple[ArchiveDeposit, ...] = (
    ArchiveDeposit(
        ARCHIVE_ZENODO, (KIND_CODE, KIND_DATA),
        identifier="10.5281/zenodo.1234567", status=STATUS_VERIFIED,
    ),
    ArchiveDeposit(
        ARCHIVE_SOFTWARE_HERITAGE, (KIND_CODE,),
        identifier="swh:1:dir:" + "a" * 40, status=STATUS_VERIFIED,
    ),
    ArchiveDeposit(
        ARCHIVE_INSTITUTIONAL, (KIND_DATA,),
        identifier="20.500.12345/sdacs-2026", status=STATUS_VERIFIED,
    ),
)


def _cmd_policy() -> None:
    print("아카이브 이중화 정책 매트릭스")
    print(f"{'CUSTODIANS':<12}{'BOTH_DIMS':<12}VERDICT")
    for (bucket, both), verdict in POLICY_MATRIX.items():
        print(f"{bucket:<12}{str(both):<12}{verdict}")
    print(
        f"\nREDUNDANT 조건: 독립 custodian ≥{MIN_INDEPENDENT_CUSTODIANS}곳 + "
        f"코드·데이터 두 차원 모두 VERIFIED"
    )


def _cmd_demo() -> None:
    print("예시 예치 판정:")
    for deposit in _DEMO_DEPOSITS:
        state = deposit_state(deposit)
        print(f"  {deposit.archive:<20} {state:<10} "
              f"kinds={','.join(deposit.kinds)} id={deposit.identifier}")
    result = assess_redundancy(_DEMO_DEPOSITS)
    print(f"\n레지스트리 판정: {result.summary()}")


def _cmd_status() -> None:
    print("리포 현 아카이브 이중화 상태(정직 공시):")
    prereqs = preservation_prerequisites(Path(__file__).resolve().parent.parent)
    for name, present in prereqs.items():
        print(f"  메타데이터 {name:<26} {'있음' if present else '없음'}")
    result = assess_redundancy(shipped_registry())
    print(f"\n판정: {result.summary()}")


_KNOWN_FLAGS = ("--policy", "--demo", "--status", "--manifest")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    unknown = [a for a in args if a not in _KNOWN_FLAGS]
    if unknown:
        print(f"알 수 없는 인자: {' '.join(unknown)}", file=sys.stderr)
        print(f"사용법: {' | '.join(_KNOWN_FLAGS)}", file=sys.stderr)
        return 2
    if "--manifest" in args:
        print(json.dumps(policy_manifest(), ensure_ascii=False, indent=2))
        return 0
    if "--demo" in args:
        _cmd_demo()
        return 0
    if "--status" in args:
        _cmd_status()
        return 0
    _cmd_policy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
