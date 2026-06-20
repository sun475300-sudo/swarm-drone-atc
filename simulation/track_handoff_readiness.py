"""ODYSSEY Phase 492 — 차세대 트랙 공모·선정 정책.

Continuum 트랙(Phase 481-500)의 한 칸. 로드맵은 Phase 491-499 를 *차세대
(2027+ 기수) 주도 신규 트랙 공모·선정·이양* 으로, Phase 500 을 Centennial
선언으로 비워 두었다. **Phase 491**(``track_handover_policy``)이 *개별 제안의
이양 검토 게이트*(ACCEPT/REVISE/DEFER/REJECT)를 다룬다면, 본 Phase 492 는 그
다음 단계인 *공모 전체에서 적격 제안을 가려 하나를 선정* 하는 문제를 다룬다 —
"제출된 차세대 트랙 제안이 적격인가(공모), 적격 제안 중 무엇을 선정하는가" 를
사람이 매번 직관으로 판단하지 않도록 *결정적 정책* 으로 명문화한다. 같은
입력은 항상 같은 판정·선정을 낸다. (491 게이트와 독립 기준: 491 은 *이양
수용 가능성*, 492 는 *적격 제안 간 우선순위* 를 본다.)

설계 원칙
--------
- **정책은 코드, 코드는 정책**: 공모·선정 규칙을 문서(``docs/standards/
  NEXTGEN_TRACK_HANDOFF_POLICY.md``)와 본 평가기에 *한 번씩만* 적기 위해,
  본 모듈이 유일한 실행 가능 명세다. 문서는 규칙을 서술할 뿐 중복 로직을
  두지 않는다(테스트가 ``POLICY_MATRIX`` ↔ ``assess_proposal`` 일치 강제).
- **자문이지 집행 아님**: 본 모듈은 *제안의 적격성을 판정* 하고 *선정 후보를
  지목* 할 뿐, 실제로 트랙을 개설하거나 권한을 이양하지 않는다(부수효과 0).
  사람/위원회가 실제 이양을 집행한다.
- **이양의 핵심은 독립성**: 차세대 트랙은 *원저자 없이 차세대 기수가 독립적
  으로 추진* 할 수 있어야 한다(``independent_of_principal``). 원저자에게 다시
  묶이는 제안은 이양이 아니라 위임이므로 필수 기준 미충족이다(Phase 487
  bus factor 정직성과 정합).
- **목표 주도(CLAUDE.md §4)**: 적격 제안은 *검증 가능한 성공 기준* 과 트랙
  헌장(스코프)을 둘 다 갖춰야 한다. "되게 해줘" 류 약한 기준은 공모 보완
  대상(NEEDS_WORK)이다.
- **선정 동률 분리는 안정 해시**: 적격 제안이 복수면 선택 가능한 *부가
  강점*(멘토 약속·재원 식별) 점수로 우선하고, 동점은 ``sha256(proposal_id)``
  안정 해시로 분리한다(Phase 424 연합 충돌 협상과 동일 idiom — 무작위성 0).

무작위성 0 · 결정적 · 기존 모듈 무수정 순수 추가.

CLI:
    python -m simulation.track_handoff_readiness --policy     # 정책 매트릭스
    python -m simulation.track_handoff_readiness --demo       # 예시 공모·선정
    python -m simulation.track_handoff_readiness --status     # 리포 현 상태 판정
    python -m simulation.track_handoff_readiness --manifest   # 정책 매니페스트(JSON)
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, field
from typing import Any

# --- 제안 적격 판정 --------------------------------------------------------
VERDICT_ELIGIBLE = "ELIGIBLE"        # 모든 필수 기준 충족 — 선정 후보
VERDICT_NEEDS_WORK = "NEEDS_WORK"    # 주체·범위는 있으나 필수 일부 미충족 — 보완
VERDICT_REJECTED = "REJECTED"        # 주체 없음·범위 없음 — 공모 성립 불가

# --- 코호트(공모 전체) 선정 결과 ------------------------------------------
SELECTION_HANDOFF_READY = "HANDOFF_READY"        # 적격 제안 ≥1 — 선정 완료
SELECTION_NO_ELIGIBLE = "NO_ELIGIBLE"            # 제안은 있으나 적격 0
SELECTION_AWAITING_PROPOSALS = "AWAITING_PROPOSALS"  # 제출된 제안 0

# 차세대 트랙으로 인정하는 최소 Phase 규모. 기존 트랙 블록(예: 481-490,
# 421-440)이 10 Phase 케이던스이므로, 한 칸짜리 작업은 트랙 이양이 아니라
# 단일 기여다 — 이양 대상 트랙은 최소 한 블록(10 Phase)을 계획해야 한다.
MIN_TRACK_PHASES = 10

# 범위 버킷(estimated_phases → 버킷).
SCOPE_NONE = "none"    # <=0 — 범위 없는 제안
SCOPE_SMALL = "small"  # 1..MIN-1 — 트랙 규모 미달
SCOPE_TRACK = "track"  # >=MIN — 트랙 규모


@dataclass(frozen=True)
class TrackProposal:
    """차세대 트랙 제안 하나(불변).

    Attributes:
        proposal_id: 제안 식별자(공모 접수번호 등). 선정 동률 분리 키.
        title: 트랙 제목.
        champion: 트랙을 주도할 차세대 기수 책임자 핸들(비면 주체 없음).
        has_charter: 트랙 헌장(스코프·범위 정의 문서) 보유.
        has_success_criteria: 검증 가능한 성공 기준 정의(CLAUDE.md §4).
        independent_of_principal: 원저자 없이 차세대 기수가 독립 추진 가능.
        prerequisites_met: 선행 트랙·인프라 의존성 충족.
        estimated_phases: 계획 Phase 수(트랙 규모).
        mentor_committed: (부가 강점) 지도교수/멘토 지속 약속 확보.
        funding_identified: (부가 강점) 트랙 추진 재원 식별.
    """

    proposal_id: str
    title: str
    champion: str
    has_charter: bool = False
    has_success_criteria: bool = False
    independent_of_principal: bool = False
    prerequisites_met: bool = False
    estimated_phases: int = 0
    mentor_committed: bool = False
    funding_identified: bool = False


def _has_champion(proposal: TrackProposal) -> bool:
    """주체(책임자)가 지정됐는가 — 빈/공백 핸들은 주체 없음."""
    return bool(proposal.champion and proposal.champion.strip())


def scope_bucket(estimated_phases: int) -> str:
    """계획 Phase 수를 범위 버킷으로 사상한다."""
    if estimated_phases <= 0:
        return SCOPE_NONE
    if estimated_phases < MIN_TRACK_PHASES:
        return SCOPE_SMALL
    return SCOPE_TRACK


def _musts_complete(proposal: TrackProposal) -> bool:
    """이양 필수 기준(헌장·성공 기준·독립성·선행 의존성) 전부 충족인가."""
    return (
        proposal.has_charter
        and proposal.has_success_criteria
        and proposal.independent_of_principal
        and proposal.prerequisites_met
    )


def readiness_score(proposal: TrackProposal) -> int:
    """적격 제안의 *부가 강점* 점수(0..2) — 선정 1순위 정렬 키.

    필수 기준이 아니라, 동등하게 적격인 제안 중 무엇을 먼저 선정할지를 가르는
    선택적 강점(멘토 지속 약속·재원 식별)만 센다.
    """
    return int(proposal.mentor_committed) + int(proposal.funding_identified)


@dataclass(frozen=True)
class ProposalAssessment:
    """제안 한 건의 적격 판정 결과(불변)."""

    proposal_id: str
    verdict: str
    scope: str
    score: int                        # 적격일 때 부가 강점 점수(아니면 0)
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def is_eligible(self) -> bool:
        return self.verdict == VERDICT_ELIGIBLE

    def summary(self) -> str:
        return f"{self.proposal_id} {self.verdict}: {'; '.join(self.reasons)}"


def _verdict_for(has_champion: bool, scope: str, musts: bool) -> str:
    """판정 핵심 규칙(매트릭스의 권위 있는 구현).

    주체(champion)가 없으면 공모가 성립하지 않고(REJECTED), 범위가 없으면
    (estimated_phases<=0) 무엇을 이양할지 정의되지 않아 REJECTED. 주체·범위는
    있으나 트랙 규모 미달이거나 필수 기준 미충족이면 보완 대상(NEEDS_WORK).
    """
    if not has_champion:
        return VERDICT_REJECTED
    if scope == SCOPE_NONE:
        return VERDICT_REJECTED
    if scope == SCOPE_SMALL:
        return VERDICT_NEEDS_WORK
    # scope == SCOPE_TRACK
    return VERDICT_ELIGIBLE if musts else VERDICT_NEEDS_WORK


def assess_proposal(proposal: TrackProposal) -> ProposalAssessment:
    """차세대 트랙 제안 한 건의 이양 적격성을 결정적으로 판정한다."""
    has_champion = _has_champion(proposal)
    scope = scope_bucket(proposal.estimated_phases)
    musts = _musts_complete(proposal)
    verdict = _verdict_for(has_champion, scope, musts)
    # 부가 강점 점수는 적격일 때만 의미가 있다 — 함수 전체에서 단일 값 보장.
    score = readiness_score(proposal) if verdict == VERDICT_ELIGIBLE else 0

    reasons: list[str] = []
    if not has_champion:
        reasons.append("주체(차세대 기수 책임자) 미지정 — 공모 성립 불가")
    elif scope == SCOPE_NONE:
        reasons.append("계획 Phase 범위 없음 — 이양 대상 미정의")
    elif scope == SCOPE_SMALL:
        reasons.append(
            f"트랙 규모 미달({proposal.estimated_phases} < "
            f"{MIN_TRACK_PHASES} Phase) — 단일 기여이지 트랙 이양 아님"
        )
    elif not musts:
        missing: list[str] = []
        if not proposal.has_charter:
            missing.append("트랙 헌장")
        if not proposal.has_success_criteria:
            missing.append("검증 가능한 성공 기준")
        if not proposal.independent_of_principal:
            missing.append("원저자 독립성")
        if not proposal.prerequisites_met:
            missing.append("선행 의존성")
        reasons.append("필수 기준 미충족: " + ", ".join(missing))
    else:
        reasons.append(
            f"적격 — 필수 기준 완비 · 부가 강점 {score}/2"
            f" (멘토={proposal.mentor_committed}, 재원={proposal.funding_identified})"
        )

    return ProposalAssessment(
        proposal_id=proposal.proposal_id,
        verdict=verdict,
        scope=scope,
        score=score,
        reasons=tuple(reasons),
    )


def _tiebreak_hash(proposal_id: str) -> str:
    """동률 분리용 안정 해시(Phase 424 협상과 동일 idiom — 무작위성 0)."""
    return hashlib.sha256(proposal_id.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SelectionResult:
    """공모 전체에 대한 선정 결과(불변)."""

    verdict: str                          # SELECTION_* 중 하나
    selected_id: str | None               # 선정된 제안 id(없으면 None)
    eligible_ids: tuple[str, ...]          # 정렬된 적격 제안 id 목록
    proposal_count: int                    # 접수 제안 총수
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def is_handoff_ready(self) -> bool:
        return self.verdict == SELECTION_HANDOFF_READY

    def summary(self) -> str:
        return f"{self.verdict}: {'; '.join(self.reasons)}"


def select_track(proposals: tuple[TrackProposal, ...]) -> SelectionResult:
    """접수 제안에서 이양할 차세대 트랙을 결정적으로 선정한다.

    적격(ELIGIBLE) 제안만 후보로 보고, 부가 강점 점수 최고를 선정하되 동점은
    ``sha256(proposal_id)`` 안정 해시 최소로 분리한다(무작위성 0). 적격 제안이
    없으면 선정하지 않는다 — 이양은 적격 제안이 나타날 때까지 진행 불가.
    """
    if not proposals:
        return SelectionResult(
            verdict=SELECTION_AWAITING_PROPOSALS,
            selected_id=None,
            eligible_ids=(),
            proposal_count=0,
            reasons=("접수된 차세대 트랙 제안 없음 — 공모 대기",),
        )

    assessments = [assess_proposal(p) for p in proposals]
    eligible = [a for a in assessments if a.is_eligible()]
    eligible_ids = tuple(sorted(a.proposal_id for a in eligible))

    if not eligible:
        return SelectionResult(
            verdict=SELECTION_NO_ELIGIBLE,
            selected_id=None,
            eligible_ids=(),
            proposal_count=len(proposals),
            reasons=(
                f"접수 {len(proposals)}건 중 적격 0 — 전부 보완·결격",
            ),
        )

    # 부가 강점 점수 최고(내림차순) → 안정 해시 최소(오름차순)로 결정적 선정.
    winner = min(eligible, key=lambda a: (-a.score, _tiebreak_hash(a.proposal_id)))
    return SelectionResult(
        verdict=SELECTION_HANDOFF_READY,
        selected_id=winner.proposal_id,
        eligible_ids=eligible_ids,
        proposal_count=len(proposals),
        reasons=(
            f"적격 {len(eligible)}건 중 '{winner.proposal_id}' 선정"
            f"(부가 강점 {winner.score}/2)",
        ),
    )


# 정책 매트릭스. (has_champion, scope, musts_complete) → 제안 판정.
# assess_proposal() 의 권위 있는 규칙을 사람이 한눈에 볼 수 있게 표로 투영한
# 것일 뿐, 판정은 항상 assess_proposal 이 내린다(테스트가 일치 강제).
POLICY_MATRIX: dict[tuple[bool, str, bool], str] = {
    (False, SCOPE_NONE, False): VERDICT_REJECTED,
    (False, SCOPE_NONE, True): VERDICT_REJECTED,
    (False, SCOPE_SMALL, False): VERDICT_REJECTED,
    (False, SCOPE_SMALL, True): VERDICT_REJECTED,
    (False, SCOPE_TRACK, False): VERDICT_REJECTED,
    (False, SCOPE_TRACK, True): VERDICT_REJECTED,
    (True, SCOPE_NONE, False): VERDICT_REJECTED,
    (True, SCOPE_NONE, True): VERDICT_REJECTED,
    (True, SCOPE_SMALL, False): VERDICT_NEEDS_WORK,
    (True, SCOPE_SMALL, True): VERDICT_NEEDS_WORK,
    (True, SCOPE_TRACK, False): VERDICT_NEEDS_WORK,
    (True, SCOPE_TRACK, True): VERDICT_ELIGIBLE,
}


def policy_manifest() -> dict[str, Any]:
    """정책을 JSON 직렬화 가능한 매니페스트로 굳힌다."""
    return {
        "schema": "sdacs-nextgen-track-handoff",
        "version": "1.0",
        "min_track_phases": MIN_TRACK_PHASES,
        "scope_buckets": [SCOPE_NONE, SCOPE_SMALL, SCOPE_TRACK],
        "proposal_verdicts": [
            VERDICT_ELIGIBLE,
            VERDICT_NEEDS_WORK,
            VERDICT_REJECTED,
        ],
        "selection_verdicts": [
            SELECTION_HANDOFF_READY,
            SELECTION_NO_ELIGIBLE,
            SELECTION_AWAITING_PROPOSALS,
        ],
        "matrix": [
            {
                "has_champion": champ,
                "scope": scope,
                "musts_complete": musts,
                "verdict": verdict,
            }
            for (champ, scope, musts), verdict in POLICY_MATRIX.items()
        ],
    }


# --- 리포 현 상태 정직 공시 ------------------------------------------------
def shipped_proposals() -> tuple[TrackProposal, ...]:
    """리포의 *현 실제 상태* 를 정직하게 반영한 접수 제안 목록.

    본 프로젝트는 목포대 캡스톤으로 아직 차세대(2027+ 기수)가 형성되지 않았고,
    이양 대상 신규 트랙 제안이 접수된 바 없다 → ``AWAITING_PROPOSALS``. 공모를
    "준비됨" 으로 포장하지 않는다(정직성, Phase 487/490 자매 패턴). 실제 차세대
    제안이 접수되면 회귀 핀이 *의도적으로* 깨져 로드맵·본 목록 갱신을 강제한다.
    """
    return ()


# 정책 동작을 보이는 결정적 예시(적격·보완·결격 혼합 공모).
_DEMO_PROPOSALS: tuple[TrackProposal, ...] = (
    TrackProposal(
        proposal_id="NT-001",
        title="온디바이스 RL 추론 트랙",
        champion="cohort2027-lead",
        has_charter=True,
        has_success_criteria=True,
        independent_of_principal=True,
        prerequisites_met=True,
        estimated_phases=10,
        mentor_committed=True,
        funding_identified=False,
    ),
    TrackProposal(
        proposal_id="NT-002",
        title="해양-공중 통합 관제 트랙",
        champion="cohort2027-mar",
        has_charter=True,
        has_success_criteria=True,
        independent_of_principal=True,
        prerequisites_met=True,
        estimated_phases=12,
        mentor_committed=True,
        funding_identified=True,   # 부가 강점 2/2 → 선정
    ),
    TrackProposal(
        proposal_id="NT-003",
        title="아이디어만 있는 제안",
        champion="someone",
        has_charter=False,
        has_success_criteria=False,
        independent_of_principal=False,
        prerequisites_met=False,
        estimated_phases=3,        # 트랙 규모 미달 → NEEDS_WORK
    ),
    TrackProposal(
        proposal_id="NT-004",
        title="주체 없는 제안",
        champion="",               # 주체 없음 → REJECTED
        estimated_phases=10,
    ),
)


def _cmd_policy() -> None:
    print("차세대 트랙 공모·선정 정책 매트릭스")
    print(f"{'CHAMPION':<10}{'SCOPE':<8}{'MUSTS':<8}VERDICT")
    for (champ, scope, musts), verdict in POLICY_MATRIX.items():
        print(f"{str(champ):<10}{scope:<8}{str(musts):<8}{verdict}")
    print(
        f"\nELIGIBLE 조건: 주체 지정 + 트랙 규모(≥{MIN_TRACK_PHASES} Phase) + "
        f"필수 기준(헌장·성공 기준·원저자 독립성·선행 의존성) 완비"
    )


def _cmd_demo() -> None:
    print("예시 공모 제안 판정:")
    for p in _DEMO_PROPOSALS:
        a = assess_proposal(p)
        print(f"  {a.proposal_id:<8} {a.verdict:<12} {a.reasons[0]}")
    result = select_track(_DEMO_PROPOSALS)
    print(f"\n선정 결과: {result.summary()}")


def _cmd_status() -> None:
    print("리포 현 차세대 트랙 이양 상태(정직 공시):")
    result = select_track(shipped_proposals())
    print(f"  접수 제안 수: {result.proposal_count}")
    print(f"  판정: {result.summary()}")


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
