"""ODYSSEY Phase 487 — 유지보수자 승계 규약(거버넌스) 정책.

Continuum 트랙(Phase 481-500)의 한 칸. 졸업 후 10년, 프로젝트가 *원저자
한 사람에게 묶여* 있으면 그 한 사람이 손을 떼는 순간(졸업·이직·사고)
머지·릴리스·보안 대응이 전부 멈춘다(bus factor 1). 본 모듈은 "현재
거버넌스가 원저자(BDFL)를 넘어 위원회로 승계될 준비가 됐는가" 를 사람이
매번 직관으로 판단하지 않도록 *결정적 정책* 으로 명문화한다 — 같은 입력은
항상 같은 판정을 낸다.

설계 원칙
--------
- **정책은 코드, 코드는 정책**: 승계 준비 판정 규칙을 문서(``docs/standards/
  MAINTAINER_SUCCESSION_PROTOCOL.md``)와 본 평가기에 *한 번씩만* 적기 위해,
  본 모듈이 유일한 실행 가능 명세다. 문서는 규칙을 서술할 뿐 중복 로직을
  두지 않는다(테스트가 ``POLICY_MATRIX`` ↔ ``assess`` 일치 강제).
- **자문이지 집행 아님**: 본 모듈은 *현 상태를 판정* 할 뿐 실제로 유지보수자를
  임명하거나 권한을 부여하지 않는다(부수효과 0). 사람/조직이 실제 승계를
  집행한다.
- **연속성 보유자만 센다(bus factor)**: 머지 권한과 관리자(admin) 접근을
  *둘 다* 가진 활성 유지보수자만 "그 한 사람이 사라져도 프로젝트를 독립적으로
  이어갈 수 있는 사람" 으로 집계한다. 이름만 올린 기여자·권한 없는 명예
  유지보수자는 승계 연속성에 기여하지 않는다(정직성).
- **위원회 우선**: 단일 BDFL 은 한 사람의 사정으로 전체가 멈추는 단일
  실패점이다. 승계 준비 완료(COMMITTEE_READY)는 *서로 다른* 연속성 보유자
  최소 3인(투표·교착 해소 가능) + 승계 거버넌스 문서 완비를 요구한다.

무작위성 0 · 결정적 · 기존 모듈 무수정 순수 추가.

CLI:
    python -m simulation.governance_succession --policy     # 정책 매트릭스
    python -m simulation.governance_succession --demo       # 예시 평가
    python -m simulation.governance_succession --status     # 리포 현 상태 판정
    python -m simulation.governance_succession --manifest   # 정책 매니페스트(JSON)
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# --- 유지보수자 역할 -------------------------------------------------------
ROLE_PRINCIPAL = "principal"      # 원저자/주 유지보수자(BDFL 자리)
ROLE_CO = "co_maintainer"         # 공동 유지보수자(동등 권한)
ROLE_RESERVE = "reserve"          # 지명된 승계 후보(아직 권한 일부)
ROLE_EMERITUS = "emeritus"        # 명예(은퇴) — 권한 없음, 연속성 미기여

_ROLES = (ROLE_PRINCIPAL, ROLE_CO, ROLE_RESERVE, ROLE_EMERITUS)

# --- 거버넌스 단계(현 구조 서술) -------------------------------------------
STAGE_ABANDONED = "ABANDONED"   # 연속성 보유자 0 — 사실상 방치
STAGE_BDFL = "BDFL"             # 1인 — 단일 실패점
STAGE_DUAL = "DUAL_CONTROL"     # 2인 — 이중 통제(교착 해소 불가)
STAGE_COMMITTEE = "COMMITTEE"   # ≥3인 — 위원회 가능

# --- 승계 준비 판정 --------------------------------------------------------
VERDICT_COMMITTEE_READY = "COMMITTEE_READY"  # 위원회 승계 준비 완료
VERDICT_TRANSITIONAL = "TRANSITIONAL"        # 진행 중 — 일부 충족, 기준 미달
VERDICT_BUS_FACTOR_RISK = "BUS_FACTOR_RISK"  # 연속성 보유자 1인 — 단일 실패점
VERDICT_ABANDONED = "ABANDONED"              # 연속성 보유자 0 — 승계 불가

# 위원회 성립(투표·교착 해소)에 필요한 최소 연속성 보유자 수.
MIN_COMMITTEE_SIZE = 3


@dataclass(frozen=True)
class Maintainer:
    """유지보수자 한 명(불변).

    Attributes:
        handle: 식별 핸들(GitHub 사용자명 등).
        role: ``principal``·``co_maintainer``·``reserve``·``emeritus`` 중 하나.
        active: 현재 활동 중인가(은퇴/장기 부재면 False).
        has_merge_rights: 보호 브랜치 머지 권한 보유.
        has_admin_access: 리포·패키지 레지스트리·도메인 관리자 접근 보유.
    """

    handle: str
    role: str
    active: bool = True
    has_merge_rights: bool = False
    has_admin_access: bool = False


def is_continuity_holder(maintainer: Maintainer) -> bool:
    """그 한 사람이 사라져도 프로젝트를 독립적으로 이어갈 수 있는 사람인가.

    결정적 판정: *활성* 이고 머지 권한과 관리자 접근을 *둘 다* 가진 경우만
    연속성 보유자로 본다. 알 수 없는 역할·빈 핸들은 인정하지 않는다(정직성).
    머지 권한만 있고 관리자 접근이 없으면(또는 그 반대) 릴리스/키 관리/계정
    복구를 단독 수행할 수 없으므로 연속성 보유자가 아니다.
    """
    if not maintainer.handle or not maintainer.handle.strip():
        return False
    if maintainer.role not in _ROLES:
        return False
    # 은퇴(emeritus)는 권한 플래그가 남아 있어도 연속성에 기여하지 않는다 —
    # 문서·상수 주석과 코드를 일치시킨다(정직성).
    if maintainer.role == ROLE_EMERITUS:
        return False
    return (
        maintainer.active
        and maintainer.has_merge_rights
        and maintainer.has_admin_access
    )


def bus_factor(maintainers: tuple[Maintainer, ...]) -> int:
    """연속성 보유자 수(서로 다른 핸들 기준 고유 집계)."""
    holders = {
        m.handle.strip() for m in maintainers if is_continuity_holder(m)
    }
    return len(holders)


def classify_stage(holder_count: int) -> str:
    """연속성 보유자 수를 거버넌스 단계로 사상한다(현 구조 서술)."""
    if holder_count <= 0:
        return STAGE_ABANDONED
    if holder_count == 1:
        return STAGE_BDFL
    if holder_count == 2:
        return STAGE_DUAL
    return STAGE_COMMITTEE


@dataclass(frozen=True)
class SuccessionAssessment:
    """거버넌스 승계 준비 판정 결과(불변)."""

    verdict: str
    stage: str
    holder_count: int
    holders: tuple[str, ...]          # 정렬된 고유 연속성 보유자 핸들
    docs_complete: bool               # 승계 거버넌스 문서 완비 여부
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def is_ready(self) -> bool:
        """위원회 승계 준비가 완료됐는가."""
        return self.verdict == VERDICT_COMMITTEE_READY

    def summary(self) -> str:
        """사람이 읽는 한 줄 요약."""
        return f"{self.verdict}: {'; '.join(self.reasons)}"


def _holder_bucket(count: int) -> str:
    """연속성 보유자 수를 정책 매트릭스 버킷으로 사상한다."""
    if count <= 0:
        return "0"
    if count == 1:
        return "1"
    if count == 2:
        return "2"
    return ">=3"


def _verdict_for(holder_count: int, docs_complete: bool) -> str:
    """판정 핵심 규칙(매트릭스의 권위 있는 구현).

    문서 완비는 보유자가 위원회 규모(≥3)일 때만 판정을 끌어올린다. 보유자가
    1인이면 문서가 아무리 완비돼도 그 한 사람이 사라지면 멈추므로
    BUS_FACTOR_RISK 다(문서가 사람을 대체하지 않는다 — 정직성).
    """
    if holder_count <= 0:
        return VERDICT_ABANDONED
    if holder_count == 1:
        return VERDICT_BUS_FACTOR_RISK
    if holder_count >= MIN_COMMITTEE_SIZE and docs_complete:
        return VERDICT_COMMITTEE_READY
    return VERDICT_TRANSITIONAL


def assess_succession(
    maintainers: tuple[Maintainer, ...],
    docs_complete: bool,
) -> SuccessionAssessment:
    """유지보수자 명단·거버넌스 문서 완비 여부로 승계 준비를 결정적으로 판정한다.

    연속성 보유자(``is_continuity_holder``)만 집계한다. ``docs_complete`` 는
    승계 거버넌스 문서 완비 여부로, 디스크 검증은 호출자(``--status``)가
    수행하고 본 함수는 주입받는다(테스트 주입 가능·``repo_root`` 무관).
    """
    holders = tuple(sorted({
        m.handle.strip() for m in maintainers if is_continuity_holder(m)
    }))
    count = len(holders)
    stage = classify_stage(count)
    verdict = _verdict_for(count, docs_complete)

    reasons: list[str] = []
    if count <= 0:
        reasons.append("연속성 보유자 0 — 머지·릴리스·보안 대응 주체 없음(방치)")
    elif count == 1:
        reasons.append(
            f"연속성 보유자 1인({holders[0]}) — 단일 실패점(bus factor 1)"
        )
    else:
        reasons.append(
            f"연속성 보유자 {count}인({', '.join(holders)}) · 단계 {stage}"
        )
        if verdict != VERDICT_COMMITTEE_READY:
            if count < MIN_COMMITTEE_SIZE:
                reasons.append(
                    f"위원회 정족({MIN_COMMITTEE_SIZE}인) 미만 — 교착 해소 불가"
                )
            if not docs_complete:
                reasons.append("승계 거버넌스 문서 미완비")
            elif count < MIN_COMMITTEE_SIZE:
                # 문서는 완비됐고 정족만 남았음을 요약에 명시(진단 가치).
                reasons.append("승계 거버넌스 문서 완비 — 연속성 보유자 추가만 남음")

    return SuccessionAssessment(
        verdict=verdict,
        stage=stage,
        holder_count=count,
        holders=holders,
        docs_complete=docs_complete,
        reasons=tuple(reasons),
    )


# 정책 매트릭스. (holder_bucket, docs_complete) → verdict.
# assess_succession() 의 권위 있는 규칙을 사람이 한눈에 볼 수 있게 표로
# 투영한 것일 뿐, 판정은 항상 assess 가 내린다(테스트가 일치 강제).
POLICY_MATRIX: dict[tuple[str, bool], str] = {
    ("0", False): VERDICT_ABANDONED,
    ("0", True): VERDICT_ABANDONED,
    ("1", False): VERDICT_BUS_FACTOR_RISK,
    ("1", True): VERDICT_BUS_FACTOR_RISK,
    ("2", False): VERDICT_TRANSITIONAL,
    ("2", True): VERDICT_TRANSITIONAL,
    (">=3", False): VERDICT_TRANSITIONAL,
    (">=3", True): VERDICT_COMMITTEE_READY,
}


def policy_manifest() -> dict[str, Any]:
    """정책을 JSON 직렬화 가능한 매니페스트로 굳힌다."""
    return {
        "schema": "sdacs-governance-succession",
        "version": "1.0",
        "roles": list(_ROLES),
        "stages": [STAGE_ABANDONED, STAGE_BDFL, STAGE_DUAL, STAGE_COMMITTEE],
        "verdicts": [
            VERDICT_COMMITTEE_READY,
            VERDICT_TRANSITIONAL,
            VERDICT_BUS_FACTOR_RISK,
            VERDICT_ABANDONED,
        ],
        "min_committee_size": MIN_COMMITTEE_SIZE,
        "matrix": [
            {
                "holder_bucket": bucket,
                "docs_complete": docs,
                "verdict": verdict,
            }
            for (bucket, docs), verdict in POLICY_MATRIX.items()
        ],
    }


# --- 리포 현 상태 정직 공시 ------------------------------------------------
# 디스크에 실재해야 승계 거버넌스가 *문서화됨* 으로 인정하는 문서.
_GOVERNANCE_DOCS = (
    "docs/standards/MAINTAINER_SUCCESSION_PROTOCOL.md",  # 승계 절차(본 Phase)
    "CONTRIBUTING.md",                                    # 기여·머지 절차
    "SECURITY.md",                                        # 보안 대응 책임
)


def governance_documents(repo_root: str | Path) -> dict[str, bool]:
    """리포에 승계 거버넌스 문서가 실재하는지 디스크로 검증한다."""
    root = Path(repo_root)
    return {name: (root / name).is_file() for name in _GOVERNANCE_DOCS}


def documents_complete(repo_root: str | Path) -> bool:
    """승계 거버넌스 문서가 전부 실재하는가."""
    return all(governance_documents(repo_root).values())


def shipped_maintainers() -> tuple[Maintainer, ...]:
    """리포의 *현 실제 상태* 를 정직하게 반영한 유지보수자 명단.

    본 프로젝트는 목포대 캡스톤으로 원저자 1인이 머지·릴리스·관리자 접근을
    단독 보유한다(BDFL). 공동 유지보수자·지명 승계 후보가 아직 없어 연속성
    보유자는 1인 → ``BUS_FACTOR_RISK``. 문서 완비를 위원회 성립으로 포장하지
    않는다(정직성). 둘째 연속성 보유자가 추가되면 회귀 핀이 *의도적으로* 깨져
    로드맵·본 명단 갱신을 강제한다.
    """
    return (
        Maintainer(
            handle="principal-maintainer",
            role=ROLE_PRINCIPAL,
            active=True,
            has_merge_rights=True,
            has_admin_access=True,
        ),
    )


# 정책 동작을 보이는 결정적 예시(위원회 승계 준비 완료 형태).
_DEMO_MAINTAINERS: tuple[Maintainer, ...] = (
    Maintainer("alice", ROLE_PRINCIPAL, True, True, True),
    Maintainer("bob", ROLE_CO, True, True, True),
    Maintainer("carol", ROLE_CO, True, True, True),
    Maintainer("dave", ROLE_RESERVE, True, True, False),   # admin 없음 → 미집계
    Maintainer("erin", ROLE_EMERITUS, False, False, False),  # 은퇴 → 미집계
)


def _cmd_policy() -> None:
    print("유지보수자 승계 정책 매트릭스")
    print(f"{'HOLDERS':<12}{'DOCS':<10}VERDICT")
    for (bucket, docs), verdict in POLICY_MATRIX.items():
        print(f"{bucket:<12}{str(docs):<10}{verdict}")
    print(
        f"\nCOMMITTEE_READY 조건: 연속성 보유자 ≥{MIN_COMMITTEE_SIZE}인 + "
        f"승계 거버넌스 문서 완비"
    )


def _cmd_demo() -> None:
    print("예시 유지보수자 연속성 판정:")
    for m in _DEMO_MAINTAINERS:
        holder = "연속성보유" if is_continuity_holder(m) else "미집계"
        print(f"  {m.handle:<10} {m.role:<14} {holder:<10} "
              f"merge={m.has_merge_rights} admin={m.has_admin_access} "
              f"active={m.active}")
    result = assess_succession(_DEMO_MAINTAINERS, docs_complete=True)
    print(f"\n명단 판정: {result.summary()}")


def _cmd_status() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    print("리포 현 거버넌스 승계 상태(정직 공시):")
    docs = governance_documents(repo_root)
    for name, present in docs.items():
        print(f"  문서 {name:<48} {'있음' if present else '없음'}")
    result = assess_succession(
        shipped_maintainers(), docs_complete=documents_complete(repo_root)
    )
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
