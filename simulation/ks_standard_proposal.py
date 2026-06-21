"""ODYSSEY Phase 471 — KS 국가표준 제안 적합성 게이트.

Standards & Policy 트랙(Phase 461-480)의 "국내 표준(KS) 제안 1건" 칸. SDACS 의
군집 드론 공역통제 접근을 한국산업표준(KS)으로 *제안할 준비가 됐는가* 를
**결정적 게이트**로 명문화한다. Phase 470(``standardization_tracker``)이 SDACS 가
발신하는 기고의 *진행 상태* 를 추적한다면, 본 모듈은 KS 제안 한 건이 KATS(국가
기술표준원)에 접수되기 위한 *제안 요건* 을 충족하는지 판정한다.

설계 원칙
--------
- **자문이지 집행 아님**: 본 모듈은 제안 준비도를 *판정만* 하며 어떤 파일도
  변경하지 않는다(부수효과 0). 실제 제안서 작성·접수는 사람의 일이다.
- **요건의 근거는 법령·협정**: 제안 요건은 산업표준화법 시행령(표준안·제안
  사유)과 WTO/TBT 협정 제2.4조(국제표준 부합 원칙)에서 도출한 6개 기준이며,
  추측이 아니라 명문 근거를 기준 설명에 담는다.
- **정직한 자가 공시**: ``shipped_proposal`` 은 현 리포의 KS 제안 후보를 *있는
  그대로* 의 충족 상태로 판정한다. 격상시키는 낙관 없이, 미충족은 미충족으로
  표면화한다.

판정 우선순위(``assess``)
------------------------
1. 미지(unknown) 상태가 하나라도 있으면 → ``REVIEW``
2. CRITICAL 기준이 하나라도 UNMET → ``NOT_READY``
3. CRITICAL 기준이 하나라도 PARTIAL → ``NEEDS_WORK``
4. (비-CRITICAL 포함) UNMET 또는 PARTIAL 이 남으면 → ``NEEDS_WORK``
5. 그 외(전부 MET 또는 N/A) → ``READY_TO_PROPOSE``

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python -m simulation.ks_standard_proposal --criteria   # 제안 요건 목록
    python -m simulation.ks_standard_proposal --status     # 현 후보 판정
    python -m simulation.ks_standard_proposal --policy     # 결정 매트릭스
    python -m simulation.ks_standard_proposal --manifest   # 매니페스트(JSON)
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

# 리포 루트 — 증거 경로는 이 기준의 상대 경로로 보관한다.
_REPO_ROOT = Path(__file__).resolve().parent.parent

# --- 기준 충족 상태(순서형) ------------------------------------------------
STATE_MET = "MET"                  # 요건을 완전히 충족
STATE_PARTIAL = "PARTIAL"          # 부분 충족(보강 필요)
STATE_UNMET = "UNMET"              # 미충족
STATE_NOT_APPLICABLE = "N/A"       # 해당 제안에 비적용(게이트에서 제외)

# 점수 가중치. N/A 는 분모에서 제외하므로 여기 없다.
_STATE_WEIGHT: Mapping[str, float] = MappingProxyType({
    STATE_MET: 1.0,
    STATE_PARTIAL: 0.5,
    STATE_UNMET: 0.0,
})
_KNOWN_STATES: frozenset[str] = frozenset(
    {STATE_MET, STATE_PARTIAL, STATE_UNMET, STATE_NOT_APPLICABLE}
)

# --- 게이트 판정 ----------------------------------------------------------
VERDICT_READY = "READY_TO_PROPOSE"
VERDICT_NEEDS_WORK = "NEEDS_WORK"
VERDICT_NOT_READY = "NOT_READY"
VERDICT_REVIEW = "REVIEW"


@dataclass(frozen=True)
class KsCriterion:
    """KS 제안 요건 한 건(불변).

    Attributes:
        criterion_id: 안정 식별자 (KS-01..).
        name: 요건 이름.
        basis: 명문 근거(법령·협정 조항).
        critical: 미충족 시 제안 자체가 반려되는 필수 요건인지 여부.
        description: 요건이 요구하는 바.
    """

    criterion_id: str
    name: str
    basis: str
    critical: bool
    description: str


# KS 제안 요건 레지스트리 — 결정적 순서. 산업표준화법·WTO/TBT 근거.
CRITERIA: tuple[KsCriterion, ...] = (
    KsCriterion(
        "KS-01", "표준안 본문",
        "산업표준화법 시행령 §11(표준안 제출)",
        True,
        "제정하려는 표준의 적용범위·용어·요구사항·시험방법을 담은 표준안 본문.",
    ),
    KsCriterion(
        "KS-02", "제안 사유·필요성",
        "산업표준화법 시행령 §11(제안 사유)",
        True,
        "표준 제정의 산업적 필요성과 기대효과를 서술한 제안 사유서.",
    ),
    KsCriterion(
        "KS-03", "국제표준 부합성 검토",
        "WTO/TBT 협정 §2.4(국제표준 기반 원칙)",
        True,
        "대응 국제표준(ISO/IEC/ICAO)과의 부합 또는 이탈 사유 검토.",
    ),
    KsCriterion(
        "KS-04", "기존 KS 중복성 검토",
        "KS 운영요령(중복 제정 금지)",
        True,
        "동일·유사 범위의 기존 KS 가 없음을 확인한 중복성 검토.",
    ),
    KsCriterion(
        "KS-05", "기술적 타당성 근거",
        "KS 운영요령(기술 근거 첨부)",
        False,
        "요구사항·시험방법을 뒷받침하는 실측·시뮬레이션 등 기술 근거.",
    ),
    KsCriterion(
        "KS-06", "이해관계자 의견수렴",
        "산업표준화법 §5(예고고시 60일)",
        False,
        "제안 전 산업계·학계 등 이해관계자 의견을 수렴한 기록.",
    ),
)
_CRITERION_INDEX = {c.criterion_id: c for c in CRITERIA}


@dataclass(frozen=True)
class KsAssessment:
    """KS 제안 한 건의 준비도 판정 결과(불변)."""

    verdict: str
    score: float
    state_by_criterion: Mapping[str, str]
    blocking: tuple[str, ...]   # NOT_READY/NEEDS_WORK 를 유발한 기준 id
    notes: tuple[str, ...]

    def summary(self) -> str:
        """사람이 읽는 한 줄 요약."""
        pct = round(self.score * 100, 1)
        base = f"{self.verdict} ({pct}%)"
        if self.blocking:
            base += f" — 결격 {len(self.blocking)}건: {', '.join(self.blocking)}"
        return base


def all_criteria() -> tuple[KsCriterion, ...]:
    """결정적 순서의 전체 요건 목록."""
    return CRITERIA


def get_criterion(criterion_id: str) -> KsCriterion:
    """식별자로 요건을 조회한다.

    Raises:
        KeyError: 알 수 없는 식별자.
    """
    try:
        return _CRITERION_INDEX[criterion_id]
    except KeyError:
        raise KeyError(f"알 수 없는 요건 식별자: {criterion_id!r}") from None


def _normalize(states: Mapping[str, str]) -> dict[str, str]:
    """제안 상태를 전체 요건에 대해 정규화한다(미지정 요건은 UNMET).

    Raises:
        KeyError: 레지스트리에 없는 요건 id.
        ValueError: 알 수 없는 상태 값.
    """
    for cid, state in states.items():
        if cid not in _CRITERION_INDEX:
            raise KeyError(f"알 수 없는 요건 id: {cid!r}")
        if state not in _KNOWN_STATES:
            raise ValueError(
                f"{cid}: 알 수 없는 상태 {state!r} "
                f"(허용: {', '.join(sorted(_KNOWN_STATES))})"
            )
    # 명시되지 않은 요건은 보수적으로 UNMET 으로 본다.
    return {c.criterion_id: states.get(c.criterion_id, STATE_UNMET) for c in CRITERIA}


def assess(states: Mapping[str, str]) -> KsAssessment:
    """KS 제안 상태를 받아 제안 준비도를 결정적으로 판정한다.

    판정 우선순위는 모듈 docstring 의 1-5 단계를 따른다.

    Args:
        states: 요건 id → 상태 매핑. 미지정 요건은 UNMET 으로 간주.
    """
    normalized = _normalize(states)

    # 점수: N/A 제외, 가중 평균. 평가 대상이 0이면 0.0.
    weighted = 0.0
    denom = 0
    for cid, state in normalized.items():
        if state == STATE_NOT_APPLICABLE:
            continue
        denom += 1
        weighted += _STATE_WEIGHT[state]
    score = weighted / denom if denom else 0.0

    critical_unmet: list[str] = []
    critical_partial: list[str] = []
    other_incomplete: list[str] = []
    notes: list[str] = []

    for cid, state in normalized.items():
        crit = _CRITERION_INDEX[cid]
        if state == STATE_NOT_APPLICABLE:
            notes.append(f"{cid}: 비적용 — 게이트 제외")
            continue
        if state == STATE_MET:
            continue
        if crit.critical and state == STATE_UNMET:
            critical_unmet.append(cid)
        elif crit.critical and state == STATE_PARTIAL:
            critical_partial.append(cid)
        else:
            other_incomplete.append(cid)

    # 판정 우선순위.
    if critical_unmet:
        verdict = VERDICT_NOT_READY
        blocking = tuple(critical_unmet)
    elif critical_partial:
        verdict = VERDICT_NEEDS_WORK
        blocking = tuple(critical_partial)
    elif other_incomplete:
        verdict = VERDICT_NEEDS_WORK
        blocking = tuple(other_incomplete)
    else:
        verdict = VERDICT_READY
        blocking = ()

    return KsAssessment(
        verdict=verdict,
        score=round(score, 4),
        state_by_criterion=MappingProxyType(dict(normalized)),
        blocking=blocking,
        notes=tuple(notes),
    )


# --- 결정 매트릭스(테스트가 assess 와 일치를 강제) -------------------------
# (worst_critical_state, has_other_incomplete) → verdict.
# worst_critical_state 는 CRITICAL 기준 중 최악(UNMET > PARTIAL > MET/N/A 순).
POLICY_MATRIX: tuple[tuple[str, bool, str], ...] = (
    (STATE_UNMET, True, VERDICT_NOT_READY),
    (STATE_UNMET, False, VERDICT_NOT_READY),
    (STATE_PARTIAL, True, VERDICT_NEEDS_WORK),
    (STATE_PARTIAL, False, VERDICT_NEEDS_WORK),
    (STATE_MET, True, VERDICT_NEEDS_WORK),
    (STATE_MET, False, VERDICT_READY),
)


# --- 현 리포의 KS 제안 후보(정직한 자가 공시) -----------------------------
# 후보: "군집 드론 공역통제 시스템 — 안전 요구사항 및 시험 방법" KS 제안.
# 격상 없이 현 자산 상태를 그대로 반영한다.
SHIPPED_TITLE = "군집 드론 공역통제 시스템 — 안전 요구사항 및 시험 방법"
_SHIPPED_STATES: Mapping[str, str] = MappingProxyType({
    # 5계층 안전망 백서·벤치마크 스위트는 있으나 KS 형식 표준안 본문 미작성.
    "KS-01": STATE_PARTIAL,
    # 제안 사유는 로드맵·산학 문서에 산재, 단일 제안서로 정리 전.
    "KS-02": STATE_PARTIAL,
    # ICAO/ISO 부합성 추적 모듈(Phase 407·462) 존재.
    "KS-03": STATE_MET,
    # 기존 KS 중복성 공식 검토 미수행.
    "KS-04": STATE_UNMET,
    # 4,443 검증 자산·표준 벤치마크 스위트로 기술 근거 확보.
    "KS-05": STATE_MET,
    # 외부 이해관계자 의견수렴 미착수(사용자 환경 의존).
    "KS-06": STATE_UNMET,
})


def shipped_proposal() -> KsAssessment:
    """현 리포의 KS 제안 후보 판정(정직한 자가 공시)."""
    return assess(_SHIPPED_STATES)


def manifest() -> dict[str, Any]:
    """JSON 직렬화 가능한 매니페스트(요건 + 현 후보 판정)."""
    a = shipped_proposal()
    return {
        "schema": "sdacs-ks-standard-proposal",
        "version": "1.0",
        "title": SHIPPED_TITLE,
        "criteria": [
            {
                "criterion_id": c.criterion_id,
                "name": c.name,
                "basis": c.basis,
                "critical": c.critical,
                "description": c.description,
            }
            for c in CRITERIA
        ],
        "shipped": {
            "verdict": a.verdict,
            "score": a.score,
            "state_by_criterion": dict(a.state_by_criterion),
            "blocking": list(a.blocking),
            "notes": list(a.notes),
        },
    }


def _cmd_criteria() -> None:
    print(f"KS 국가표준 제안 요건 — {len(CRITERIA)}건")
    print(f"{'ID':<7}{'필수':<5}이름 / 근거")
    for c in CRITERIA:
        mark = "●" if c.critical else "○"
        print(f"{c.criterion_id:<7}{mark:<5}{c.name}  ({c.basis})")


def _cmd_status() -> None:
    a = shipped_proposal()
    print(f"KS 제안 후보: {SHIPPED_TITLE}")
    for c in CRITERIA:
        state = a.state_by_criterion[c.criterion_id]
        mark = "●" if c.critical else "○"
        print(f"  {mark} {c.criterion_id} {c.name:<18} {state}")
    print(f"\n{a.summary()}")


def _cmd_policy() -> None:
    print("결정 매트릭스 (worst_critical_state, has_other_incomplete) → verdict")
    for worst, other, verdict in POLICY_MATRIX:
        print(f"  ({worst:<8}, other={str(other):<5}) → {verdict}")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "--criteria" in args:
        _cmd_criteria()
        return 0
    if "--policy" in args:
        _cmd_policy()
        return 0
    if "--manifest" in args:
        print(json.dumps(manifest(), ensure_ascii=False, indent=2))
        return 0
    _cmd_status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
