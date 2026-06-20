"""ODYSSEY Phase 491 — 차세대 신규 트랙 이양 검토 게이트 정책.

Continuum 트랙(Phase 481-500)의 한 칸. Phase 491-499 는 *차세대(2027+ 기수)가
주도* 하는 신규 트랙을 공모·선정·이양하는 구간이다. ODYSSEY 거버넌스 게이트
#4("세대 이양: 491+ 신규 트랙은 차세대 주도, 현 세대는 리뷰만")가 본 단계의
핵심 규약이다 — 현 세대(원저자)는 새 트랙을 *직접 만들지 않고*, 차세대가
제출한 제안을 *리뷰만* 한다.

본 모듈은 "차세대가 제출한 신규 트랙 제안을 이양해도 되는가" 라는 리뷰 판단을
사람이 매번 직관으로 내리지 않도록 *결정적 정책* 으로 명문화한다 — 같은 제안은
항상 같은 판정을 낸다.

설계 원칙
--------
- **정책은 코드, 코드는 정책**: 이양 판정 규칙을 문서(``docs/standards/
  GENERATIONAL_HANDOVER_POLICY.md``)와 본 평가기에 *한 번씩만* 적기 위해, 본
  모듈이 유일한 실행 가능 명세다. 문서는 규칙을 서술할 뿐 중복 로직을 두지
  않는다(테스트가 ``POLICY_MATRIX`` ↔ ``assess`` 일치 강제).
- **자문이지 집행 아님**: 본 모듈은 *제안의 이양 준비 상태를 판정* 할 뿐 실제로
  트랙을 등록하거나 권한을 이양하지 않는다(부수효과 0). 사람/위원회가 실제
  이양을 집행한다.
- **차세대 주도가 정의 요건**: 제안에 *차세대 소유자* (연속성 보유 의지를 가진
  2027+ 기수)가 없으면, 그 트랙은 현 세대가 떠안아야만 굴러간다 — 이는 세대
  이양의 정의 자체에 어긋나므로 구조적 반려(REJECT)다. 헌장이 아무리 좋아도
  소유자가 사람을 대체하지 못한다(정직성).
- **현 세대는 리뷰만**: 게이트 #4 에 따라, 현 세대 리뷰가 끝나기 전에는 어떤
  긍정 판정도 내리지 않는다(미검토 → 보류 DEFER). 리뷰는 절차이지 내용의
  대체가 아니다.

무작위성 0 · 결정적 · 기존 모듈 무수정 순수 추가.

CLI:
    python -m simulation.track_handover_policy --policy     # 정책 매트릭스
    python -m simulation.track_handover_policy --demo       # 예시 평가
    python -m simulation.track_handover_policy --status     # 리포 현 상태 판정
    python -m simulation.track_handover_policy --manifest   # 정책 매니페스트(JSON)
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Any

# --- 이양 판정 -------------------------------------------------------------
VERDICT_ACCEPT = "ACCEPT"    # 이양 수용 — 차세대 주도로 트랙 개시 준비 완료
VERDICT_REVISE = "REVISE"    # 보완 요청 — 고칠 수 있는 결함(헌장·범위·sandbox)
VERDICT_DEFER = "DEFER"      # 보류 — 현 세대 리뷰 미완(게이트 #4 미통과)
VERDICT_REJECT = "REJECT"    # 반려 — 차세대 소유자 부재(구조적 결격)

# --- 프로그램(공모 전체) 상태 ---------------------------------------------
PROGRAM_AWAITING = "AWAITING_PROPOSALS"      # 등록된 제안 0건
PROGRAM_REGISTERED = "PROPOSALS_REGISTERED"  # 1건 이상 제안 등록됨

# 기존 ODYSSEY 트랙(범위 중복 검토의 기준 — 실재 로드맵 근거).
# 신규 제안이 이 중 하나와 본질적으로 같은 범위면 중복으로 본다.
EXISTING_TRACKS: tuple[tuple[str, str], ...] = (
    ("🌏", "Global Expansion (Phase 401-420)"),
    ("🛰", "Federation Operations (Phase 421-440)"),
    ("🔬", "Formal & Research Frontier (Phase 441-460)"),
    ("🏛", "Standards & Policy (Phase 461-480)"),
    ("♾️", "Continuum (Phase 481-500)"),
)


@dataclass(frozen=True)
class TrackProposal:
    """차세대가 제출한 신규 트랙 제안 한 건(불변).

    Attributes:
        track_id: 제안 식별자(빈 값 불허).
        title: 제안 제목(빈 값 불허).
        charter_present: 헌장(범위·목표·산출물·종료 기준)이 명문화돼 있는가.
        scope_overlaps_existing: 기존 트랙과 범위가 본질적으로 중복되는가.
        has_next_gen_owner: 연속성 보유 의지를 가진 차세대 소유자가 지정됐는가.
        sandbox_feasible: 외부 HW/비밀키 없이 sandbox 에서 재현 가능한가.
    """

    track_id: str
    title: str
    charter_present: bool = False
    scope_overlaps_existing: bool = False
    has_next_gen_owner: bool = False
    sandbox_feasible: bool = False

    def __post_init__(self) -> None:
        if not self.track_id or not self.track_id.strip():
            raise ValueError("track_id must be non-empty")
        if not self.title or not self.title.strip():
            raise ValueError("title must be non-empty")


def is_clean(proposal: TrackProposal) -> bool:
    """헌장·범위·sandbox 의 보완형 결함이 *하나도* 없는가.

    소유자 유무는 구조적 결격(REJECT)이라 여기서 다루지 않는다 — clean 은
    "리뷰를 통과한 제안에 남은 보완 사항이 없는가" 만 본다.
    """
    return (
        proposal.charter_present
        and not proposal.scope_overlaps_existing
        and proposal.sandbox_feasible
    )


@dataclass(frozen=True)
class HandoverAssessment:
    """신규 트랙 이양 검토 판정 결과(불변)."""

    verdict: str
    track_id: str
    reviewed: bool
    blockers: tuple[str, ...] = field(default_factory=tuple)
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def is_accepted(self) -> bool:
        """이양 수용으로 판정됐는가."""
        return self.verdict == VERDICT_ACCEPT

    def summary(self) -> str:
        """사람이 읽는 한 줄 요약."""
        return f"{self.verdict} [{self.track_id}]: {'; '.join(self.reasons)}"


def _verdict_for(
    has_next_gen_owner: bool, reviewed: bool, clean: bool
) -> str:
    """판정 핵심 규칙(매트릭스의 권위 있는 구현).

    우선순위(서로소 단계):
    1. 차세대 소유자 부재 → REJECT(구조적 결격 — 검토·헌장과 무관).
    2. 현 세대 리뷰 미완 → DEFER(게이트 #4 절차 미통과).
    3. 보완형 결함 존재(헌장 부재·범위 중복·sandbox 미검증) → REVISE.
    4. 그 외 → ACCEPT.
    """
    if not has_next_gen_owner:
        return VERDICT_REJECT
    if not reviewed:
        return VERDICT_DEFER
    if not clean:
        return VERDICT_REVISE
    return VERDICT_ACCEPT


def assess_handover(
    proposal: TrackProposal, current_gen_reviewed: bool
) -> HandoverAssessment:
    """제안과 현 세대 리뷰 완료 여부로 이양 준비를 결정적으로 판정한다.

    ``current_gen_reviewed`` 는 현 세대(원저자)가 제안을 리뷰했는지로, 절차
    플래그다(게이트 #4). 디스크/외부 상태에 의존하지 않으므로 테스트 주입이
    가능하다.
    """
    clean = is_clean(proposal)
    verdict = _verdict_for(
        proposal.has_next_gen_owner, current_gen_reviewed, clean
    )

    blockers: list[str] = []
    if not proposal.has_next_gen_owner:
        blockers.append("차세대 소유자 미지정")
    if not proposal.charter_present:
        blockers.append("헌장 부재")
    if proposal.scope_overlaps_existing:
        blockers.append("기존 트랙과 범위 중복")
    if not proposal.sandbox_feasible:
        blockers.append("sandbox 재현 미검증")

    reasons: list[str] = []
    if verdict == VERDICT_REJECT:
        reasons.append("차세대 소유자 부재 — 현 세대가 떠안아야 굴러감(세대 이양 정의 위반)")
    elif verdict == VERDICT_DEFER:
        reasons.append("현 세대 리뷰 미완 — 게이트 #4 절차 미통과")
        # 미검토 단계에서도 보이는 결함은 미리 알려 재제출 비용을 줄인다.
        fixable = [b for b in blockers if b != "차세대 소유자 미지정"]
        if fixable:
            reasons.append("리뷰 전 표면화된 보완 사항: " + ", ".join(fixable))
    elif verdict == VERDICT_REVISE:
        reasons.append(
            "보완 요청: " + ", ".join(
                b for b in blockers if b != "차세대 소유자 미지정"
            )
        )
    else:  # ACCEPT
        reasons.append("차세대 주도 트랙 이양 수용 — 헌장·범위·sandbox 충족·리뷰 완료")

    return HandoverAssessment(
        verdict=verdict,
        track_id=proposal.track_id,
        reviewed=current_gen_reviewed,
        blockers=tuple(blockers),
        reasons=tuple(reasons),
    )


# 정책 매트릭스. (has_next_gen_owner, reviewed, clean) → verdict.
# assess_handover() 의 권위 있는 규칙을 사람이 한눈에 볼 수 있게 표로 투영한
# 것일 뿐, 판정은 항상 assess 가 내린다(테스트가 일치 강제).
POLICY_MATRIX: dict[tuple[bool, bool, bool], str] = {
    (False, False, False): VERDICT_REJECT,
    (False, False, True): VERDICT_REJECT,
    (False, True, False): VERDICT_REJECT,
    (False, True, True): VERDICT_REJECT,
    (True, False, False): VERDICT_DEFER,
    (True, False, True): VERDICT_DEFER,
    (True, True, False): VERDICT_REVISE,
    (True, True, True): VERDICT_ACCEPT,
}


def program_status(proposals: tuple[TrackProposal, ...]) -> str:
    """공모 전체의 현 상태(등록 제안 유무)."""
    return PROGRAM_AWAITING if not proposals else PROGRAM_REGISTERED


def policy_manifest() -> dict[str, Any]:
    """정책을 JSON 직렬화 가능한 매니페스트로 굳힌다."""
    return {
        "schema": "sdacs-track-handover",
        "version": "1.0",
        "verdicts": [
            VERDICT_ACCEPT,
            VERDICT_REVISE,
            VERDICT_DEFER,
            VERDICT_REJECT,
        ],
        "program_states": [PROGRAM_AWAITING, PROGRAM_REGISTERED],
        "existing_tracks": [
            {"icon": icon, "name": name} for icon, name in EXISTING_TRACKS
        ],
        "matrix": [
            {
                "has_next_gen_owner": owner,
                "reviewed": reviewed,
                "clean": clean,
                "verdict": verdict,
            }
            for (owner, reviewed, clean), verdict in POLICY_MATRIX.items()
        ],
    }


# --- 리포 현 상태 정직 공시 ------------------------------------------------
def shipped_proposals() -> tuple[TrackProposal, ...]:
    """리포의 *현 실제 상태* 를 정직하게 반영한 신규 트랙 제안 명단.

    2027+ 차세대 기수가 아직 형성되지 않아 등록된 신규 트랙 제안은 0건이다.
    빈 레지스트리를 ``AWAITING_PROPOSALS`` 로 정직 공시한다. 첫 제안이 등록되면
    회귀 핀이 *의도적으로* 깨져 본 명단·로드맵 갱신을 강제한다.
    """
    return ()


# 정책 동작을 보이는 결정적 예시(네 판정을 모두 보임).
_DEMO_PROPOSALS: tuple[tuple[TrackProposal, bool], ...] = (
    (TrackProposal("Q1", "양자 항법 융합", charter_present=True,
                   scope_overlaps_existing=False, has_next_gen_owner=True,
                   sandbox_feasible=True), True),                  # ACCEPT
    (TrackProposal("Q2", "도심 소음 모델", charter_present=False,
                   scope_overlaps_existing=False, has_next_gen_owner=True,
                   sandbox_feasible=True), True),                  # REVISE
    (TrackProposal("Q3", "신경망 관제", charter_present=True,
                   scope_overlaps_existing=False, has_next_gen_owner=True,
                   sandbox_feasible=True), False),                 # DEFER
    (TrackProposal("Q4", "표준 재기고", charter_present=True,
                   scope_overlaps_existing=False, has_next_gen_owner=False,
                   sandbox_feasible=True), True),                  # REJECT(소유자 부재)
)


def _cmd_policy() -> None:
    print("차세대 트랙 이양 검토 정책 매트릭스")
    print(f"{'OWNER':<8}{'REVIEWED':<10}{'CLEAN':<8}VERDICT")
    for (owner, reviewed, clean), verdict in POLICY_MATRIX.items():
        print(f"{str(owner):<8}{str(reviewed):<10}{str(clean):<8}{verdict}")
    print(
        "\nACCEPT 조건: 차세대 소유자 지정 + 현 세대 리뷰 완료 + "
        "헌장·범위 비중복·sandbox 재현 모두 충족"
    )


def _cmd_demo() -> None:
    print("예시 신규 트랙 제안 이양 판정:")
    for proposal, reviewed in _DEMO_PROPOSALS:
        result = assess_handover(proposal, reviewed)
        print(f"  {result.summary()}")


def _cmd_status() -> None:
    proposals = shipped_proposals()
    status = program_status(proposals)
    print("리포 현 차세대 트랙 공모 상태(정직 공시):")
    print(f"  등록된 신규 트랙 제안: {len(proposals)}건")
    if status == PROGRAM_AWAITING:
        print(f"  판정: {status} — 2027+ 차세대 기수 미형성")
        return
    # 제안이 등록되면 구조적 사실(식별자·소유자 부재 등 결함)만 표면화한다.
    # 현 세대 리뷰 완료 여부는 외부 추적 사항이라 여기서 단정하지 않는다 —
    # 실제 판정은 호출자가 리뷰 상태를 주입해 assess_handover() 로 수행한다.
    print(f"  판정: {status} — 리뷰 상태 주입 후 assess_handover() 로 평가")
    for proposal in proposals:
        gaps = ", ".join(
            b for b in assess_handover(
                proposal, current_gen_reviewed=True
            ).blockers
        ) or "구조적 결함 없음"
        print(f"  [{proposal.track_id}] {proposal.title} — {gaps}")


_KNOWN_FLAGS = ("--policy", "--demo", "--status", "--manifest")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    unknown = [a for a in args if a not in _KNOWN_FLAGS]
    if unknown:
        print(f"알 수 없는 인자: {' '.join(unknown)}", file=sys.stderr)
        print(
            f"사용법: [{' | '.join(_KNOWN_FLAGS)}] (기본: --policy)",
            file=sys.stderr,
        )
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
