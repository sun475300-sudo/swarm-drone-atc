"""ODYSSEY Phase 463 — K-드론 시스템 고도화 정책 제안서 적합성 게이트.

국토교통부(MOLIT) 「드론 활용의 촉진 및 기반 조성에 관한 법률」 §6 드론산업기본계획
정렬을 목표로 하는 *K-드론 시스템 고도화 정책 제안서* 가 정부 제출 형식의 필수
구성을 갖췄는가를 결정적으로 판정하고, 현재의 *실제 제출 상태* 를 정직하게 공시한다.

Standards & Policy 트랙(Phase 461-480)에서 "우리 제안서가 국토부에 제출할 형식
요건을 충족했는가, 그리고 실제로 제출됐는가" 를 객관적으로 답하기 위한 게이트다.

자매 모듈과의 경계 (중복 없음)
------------------------------
- Phase 462(``iso_tc20_sc16_tracker``) 는 *외부 ISO 표준* 발행 동향을 추적한다.
- Phase 470(``standardization_tracker``) 는 SDACS 가 발신하는 *표준화 기고* 의
  단조 상태(PLANNED→ADOPTED)를 추적한다.
- 본 모듈(463)은 그 둘과 달리 *단일 정책 제안서 산출물* 의 필수 섹션 완비도와
  정부 제출 상태를 판정한다 — 즉 "제출할 준비가 됐는가" 와 "제출됐는가" 를 분리해
  표면화한다.

정직 공시 (CLAUDE.md)
--------------------
1. ``status`` 가 ``DRAFTED`` 인 섹션은 반드시 디스크에 실재하는 증거 산출물을
   인용한다 — 산출물 없는 작성 주장을 구조적으로 금지한다(``MISSING`` 은 증거
   인용 금지). 게이트의 가치는 작성 주장보다 *미작성 섹션의 가시화* 에 있다.
2. ``readiness`` 판정(제출 준비도)과 ``submission_status``(실제 제출 여부)는
   *독립* 이다. 모든 필수 섹션이 작성돼 ``READY_FOR_REVIEW`` 여도, 외부 기관
   제출은 본 리포 범위 밖이므로 현 상태는 항상 ``NOT_SUBMITTED`` 로 정직 공시한다.
   준비 완료가 제출을 의미하지 않는다.
3. 본 모듈은 정책 *제안* 의 형식 적합성 판정이며, 국토부의 채택·반영을 보장하지
   않는다. 채택 여부는 외부 정책 결정 절차에 달려 있다.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/k_drone_policy_proposal.py --matrix      # 전체 섹션 매트릭스
    python simulation/k_drone_policy_proposal.py --report      # 준비도·제출 상태 요약
    python simulation/k_drone_policy_proposal.py --gaps        # 미작성(필수) 섹션
    python simulation/k_drone_policy_proposal.py --submission  # 제출 상태만
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

# 섹션 작성 상태 (3값). DRAFTED=작성·OUTLINED=개요만·MISSING=미작성.
STATUSES: tuple[str, ...] = ("DRAFTED", "OUTLINED", "MISSING")

# 가중 점수: 작성 1.0·개요 0.5·미작성 0.0.
_STATUS_WEIGHT: dict[str, float] = {"DRAFTED": 1.0, "OUTLINED": 0.5, "MISSING": 0.0}

# 섹션 중요도 (2값). REQUIRED=정부 제출 필수·RECOMMENDED=권장.
CRITICALITIES: tuple[str, ...] = ("REQUIRED", "RECOMMENDED")

# 준비도 판정 (3값).
VERDICT_READY = "READY_FOR_REVIEW"
VERDICT_PARTIAL = "PARTIAL"
VERDICT_NOT_READY = "NOT_READY"

# 제출 상태 단조 진행 (현재 = NOT_SUBMITTED, 외부 절차 의존).
SUBMISSION_STAGES: tuple[str, ...] = (
    "NOT_SUBMITTED",
    "SUBMITTED",
    "ACKNOWLEDGED",
    "ADOPTED",
)


@dataclass(frozen=True)
class ProposalSection:
    """정책 제안서 한 섹션의 작성 추적 항목(불변)."""

    section_id: str             # 안정 식별자 (예: 'improvement-plan')
    title: str                  # 섹션 제목 (국토부 제출 형식)
    criticality: str            # REQUIRED·RECOMMENDED
    status: str                 # DRAFTED·OUTLINED·MISSING
    evidence: tuple[str, ...]   # 증거 산출물 리포 경로 (MISSING 이면 빈 튜플)
    summary: str                # 한 줄 설명

    def __post_init__(self) -> None:
        if not self.section_id or self.section_id != self.section_id.strip():
            raise ValueError("section_id must be non-empty and unpadded")
        if " " in self.section_id:
            raise ValueError("section_id must not contain internal spaces")
        if not self.title or not self.title.strip():
            raise ValueError("title must be a non-empty string")
        if not self.summary or not self.summary.strip():
            raise ValueError("summary must be a non-empty string")
        if self.criticality not in CRITICALITIES:
            raise ValueError(
                f"criticality must be one of {CRITICALITIES}, got {self.criticality!r}"
            )
        if self.status not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}, got {self.status!r}")
        if not isinstance(self.evidence, tuple):
            raise ValueError("evidence must be a tuple of repo paths")
        for path in self.evidence:
            if not path or path != path.strip():
                raise ValueError(f"evidence path must be non-empty and unpadded: {path!r}")
        # 정직성 결속: DRAFTED 는 반드시 증거 인용·MISSING 은 증거 인용 금지.
        if self.status == "DRAFTED" and not self.evidence:
            raise ValueError(
                f"section {self.section_id!r} is DRAFTED but cites no evidence"
            )
        if self.status == "MISSING" and self.evidence:
            raise ValueError(
                f"section {self.section_id!r} is MISSING but cites evidence"
            )

    @property
    def is_required(self) -> bool:
        """정부 제출 필수 섹션 여부."""
        return self.criticality == "REQUIRED"

    @property
    def is_drafted(self) -> bool:
        """작성 완료 여부."""
        return self.status == "DRAFTED"

    @property
    def weight(self) -> float:
        """가중 점수 기여 (DRAFTED 1.0·OUTLINED 0.5·MISSING 0.0)."""
        return _STATUS_WEIGHT[self.status]


# K-드론 정책 제안서 섹션 레지스트리 (정본, 국토부 제출 형식 순서).
# 증거는 리포 실재 산출물. 본 제안서 본문은 docs/standards/K_DRONE_POLICY_PROPOSAL.md.
_PROPOSAL_DOC = "docs/standards/K_DRONE_POLICY_PROPOSAL.md"

PROPOSAL_SECTIONS: tuple[ProposalSection, ...] = (
    ProposalSection(
        "background", "제안 배경 및 필요성", "REQUIRED", "DRAFTED",
        (_PROPOSAL_DOC, "docs/track_f/p746_k_uam.md"),
        "드론산업기본계획 정렬 배경 — K-UAM 사업 연계 필요성 근거",
    ),
    ProposalSection(
        "status-problem", "국내외 현황 및 문제점", "REQUIRED", "DRAFTED",
        (_PROPOSAL_DOC, "docs/certification/AIR_SAFETY_ACT_MATRIX.md"),
        "군집 공역 통제 공백 현황 — 항공안전법 매트릭스 기반 제도 갭 분석",
    ),
    ProposalSection(
        "improvement-plan", "정책 개선 방안", "REQUIRED", "DRAFTED",
        (_PROPOSAL_DOC,),
        "K-드론시스템 고도화 핵심 제안 — 5계층 안전망 표준화·자동 관제 의무화 단계",
    ),
    ProposalSection(
        "expected-effect", "기대 효과", "REQUIRED", "DRAFTED",
        (_PROPOSAL_DOC, "docs/track_f/p748_forest.md"),
        "공역 용량·안전·산업 파급 — 산림청 방제 등 공공 활용 효과 정량 근거",
    ),
    ProposalSection(
        "implementation-plan", "추진 체계 및 일정", "REQUIRED", "DRAFTED",
        (_PROPOSAL_DOC,),
        "단계별 추진 로드맵 — 실증·시범·확산 3단계 일정",
    ),
    ProposalSection(
        "legal-basis", "근거 법령 및 제도", "REQUIRED", "DRAFTED",
        (_PROPOSAL_DOC, "docs/certification/AIR_SAFETY_ACT_MATRIX.md"),
        "드론활용촉진법 §6·항공안전법 연계 — 제도 개정 소요 식별",
    ),
    ProposalSection(
        "budget", "소요 예산 및 재원 조달", "RECOMMENDED", "DRAFTED",
        (_PROPOSAL_DOC, "docs/track_f/README.md"),
        "고도화 사업 예산 개산 — Track F 산학 예산 종합 연계",
    ),
    ProposalSection(
        "risk-mitigation", "위험 요인 및 대응", "RECOMMENDED", "DRAFTED",
        (_PROPOSAL_DOC, "docs/standards/INCIDENT_INVESTIGATION_REPORT.md"),
        "추진 위험·기술 위험 식별 — 사고 조사 체계 기반 대응 방안",
    ),
)


# 로드 시점 무결성 게이트 — 중복 식별자를 임포트 시 즉시 차단.
_REGISTRY_IDS = [s.section_id for s in PROPOSAL_SECTIONS]
assert len(_REGISTRY_IDS) == len(set(_REGISTRY_IDS)), "duplicate section_id"

# 현 제안서의 실제 제출 상태 (외부 절차 의존, 정직 공시).
# 모든 섹션이 작성돼 준비가 됐어도 국토부 실제 제출 전까지 NOT_SUBMITTED.
CURRENT_SUBMISSION: str = "NOT_SUBMITTED"


def _repo_root() -> Path:
    """리포 루트 경로(이 파일의 상위 디렉터리)."""
    return Path(__file__).resolve().parent.parent


def evidence_present(section: ProposalSection, repo_root: str | Path) -> bool:
    """섹션의 모든 증거 산출물이 디스크에 실재하는지 결정적으로 확인한다."""
    root = Path(repo_root)
    return all((root / rel).is_file() for rel in section.evidence)


@dataclass(frozen=True)
class ProposalReadiness:
    """정책 제안서 전체의 제출 준비도 판정 결과(불변)."""

    verdict: str
    score: float                          # 가중 작성 비율 0.0~1.0
    submission_status: str                # 실제 제출 상태 (NOT_SUBMITTED 등)
    drafted: tuple[str, ...]              # 작성 완료 섹션 id(정렬)
    missing_required: tuple[str, ...]     # 미작성·증거 누락 필수 섹션 id(정렬)
    incomplete_other: tuple[str, ...]     # 미완 비-필수 섹션 id(정렬)
    by_criticality: Mapping[str, int]     # criticality -> count, read-only
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.by_criticality, MappingProxyType):
            object.__setattr__(
                self, "by_criticality", MappingProxyType(dict(self.by_criticality))
            )
        if self.verdict not in (VERDICT_READY, VERDICT_PARTIAL, VERDICT_NOT_READY):
            raise ValueError(f"unexpected verdict {self.verdict!r}")
        if self.submission_status not in SUBMISSION_STAGES:
            raise ValueError(
                f"submission_status must be one of {SUBMISSION_STAGES}, "
                f"got {self.submission_status!r}"
            )
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0, 1], got {self.score}")

    def is_ready(self) -> bool:
        """정부 제출 형식 준비가 완료됐는가(제출 여부와 무관)."""
        return self.verdict == VERDICT_READY

    def is_submitted(self) -> bool:
        """실제로 외부 기관에 제출됐는가."""
        return self.submission_status != "NOT_SUBMITTED"

    def summary(self) -> str:
        """사람이 읽는 한 줄 요약."""
        pct = f"{self.score * 100:.1f}%"
        return (
            f"{self.verdict} ({pct}) · 제출: {self.submission_status} — "
            f"{'; '.join(self.reasons)}"
        )


def find_section(section_id: str) -> ProposalSection:
    """식별자로 섹션을 조회한다. 없으면 KeyError."""
    for section in PROPOSAL_SECTIONS:
        if section.section_id == section_id:
            return section
    raise KeyError(f"unknown proposal section: {section_id!r}")


def sections_by_status(status: str) -> tuple[ProposalSection, ...]:
    """작성 상태별 섹션을 식별자 정렬로 반환한다."""
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}, got {status!r}")
    return tuple(
        sorted((s for s in PROPOSAL_SECTIONS if s.status == status),
               key=lambda s: s.section_id)
    )


def _verdict_for(has_missing_required: bool, all_drafted: bool) -> str:
    """판정 핵심 규칙(준비도의 권위 있는 구현).

    필수 섹션이 하나라도 미충족(미작성·증거 누락)이면 NOT_READY, 전부 작성이면
    READY_FOR_REVIEW, 그 사이(권장만 미완)는 PARTIAL.
    """
    if has_missing_required:
        return VERDICT_NOT_READY
    if all_drafted:
        return VERDICT_READY
    return VERDICT_PARTIAL


def assess_readiness(repo_root: str | Path | None = None) -> ProposalReadiness:
    """제안서 전체의 제출 준비도를 리포에 대해 결정적으로 판정한다.

    필수(REQUIRED) 섹션은 ``DRAFTED`` 이면서 인용 증거가 디스크에 실재해야만
    충족으로 본다 — 작성 주장만으로는 부족하다. 점수는 작성 가중치 합을 전체
    섹션 수로 나눈 비율(소수 넷째 자리 반올림 — 결정적).

    ``submission_status`` 는 ``repo_root`` 와 무관하게 ``CURRENT_SUBMISSION``
    (외부 절차 의존)으로 정직 공시한다 — 준비도와 독립이다.
    """
    root = Path(repo_root) if repo_root is not None else _repo_root()

    drafted: list[str] = []
    missing_required: list[str] = []
    incomplete_other: list[str] = []
    by_criticality: dict[str, int] = {}
    score_sum = 0.0

    for section in PROPOSAL_SECTIONS:
        by_criticality[section.criticality] = (
            by_criticality.get(section.criticality, 0) + 1
        )
        # 증거 인용이 없으면(OUTLINED 가능) all([])==True 공허 참을 차단 — 인용
        # 증거가 하나도 없으면 작성 주장을 인정하지 않는다(가중 0).
        present = bool(section.evidence) and evidence_present(section, root)
        effective_drafted = section.is_drafted and present
        score_sum += section.weight if present else 0.0

        if effective_drafted:
            drafted.append(section.section_id)
        elif section.is_required:
            missing_required.append(section.section_id)
        else:
            incomplete_other.append(section.section_id)

    total = len(PROPOSAL_SECTIONS)
    score = round(score_sum / total, 4) if total else 0.0
    # 빈 레지스트리는 "작성 완료"가 아니다 — total==0 의 공허 참(len([])==0)으로
    # READY 를 선언하지 않도록 명시 차단.
    verdict = _verdict_for(
        has_missing_required=bool(missing_required),
        all_drafted=(total > 0 and len(drafted) == total),
    )

    reasons: list[str] = []
    if missing_required:
        reasons.append(f"필수 미충족 {len(missing_required)}건")
    if incomplete_other:
        reasons.append(f"권장 미완 {len(incomplete_other)}건")
    if not reasons:
        reasons.append("전 섹션 작성 완료")
    reasons.append(f"제출 상태 {CURRENT_SUBMISSION}")

    return ProposalReadiness(
        verdict=verdict,
        score=score,
        submission_status=CURRENT_SUBMISSION,
        drafted=tuple(sorted(drafted)),
        missing_required=tuple(sorted(missing_required)),
        incomplete_other=tuple(sorted(incomplete_other)),
        by_criticality=MappingProxyType(by_criticality),
        reasons=tuple(reasons),
    )


def proposal_matrix() -> tuple[dict[str, object], ...]:
    """도구 간 교환용 섹션 매트릭스를 정의 순서로 반환한다."""
    return tuple(
        {
            "section_id": s.section_id,
            "title": s.title,
            "criticality": s.criticality,
            "status": s.status,
            "evidence": list(s.evidence),
            "summary": s.summary,
        }
        for s in PROPOSAL_SECTIONS
    )


_STATUS_MARK: dict[str, str] = {"DRAFTED": "✓", "OUTLINED": "◐", "MISSING": "✗"}
_CRIT_MARK: dict[str, str] = {"REQUIRED": "필수", "RECOMMENDED": "권장"}


def _format_matrix() -> str:
    lines = ["K-드론 정책 제안서 섹션 매트릭스 (국토부 제출 형식)", ""]
    for s in PROPOSAL_SECTIONS:
        mark = _STATUS_MARK[s.status]
        crit = _CRIT_MARK[s.criticality]
        lines.append(f"[{crit}] {mark} {s.title}")
        lines.append(f"      {s.summary}")
        lines.append(f"      → {', '.join(s.evidence) or '—'}")
    return "\n".join(lines)


def _format_report() -> str:
    r = assess_readiness()
    lines = [
        "K-드론 시스템 고도화 정책 제안서 — 제출 준비도 요약",
        "",
        f"준비도 판정 : {r.verdict} ({r.score * 100:.0f}%)",
        f"제출 상태   : {r.submission_status} (외부 절차 의존 — 정직 공시)",
        f"작성 완료   : {len(r.drafted)}/{len(PROPOSAL_SECTIONS)} 섹션",
    ]
    if r.missing_required:
        lines.append(f"필수 미충족 : {', '.join(r.missing_required)}")
    if r.incomplete_other:
        lines.append(f"권장 미완   : {', '.join(r.incomplete_other)}")
    lines.append("")
    lines.append("중요도별 섹션 수:")
    for crit in sorted(r.by_criticality):
        lines.append(f"  {_CRIT_MARK[crit]}: {r.by_criticality[crit]}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="K-드론 시스템 고도화 정책 제안서 적합성 게이트 (ODYSSEY Phase 463)"
    )
    parser.add_argument("--matrix", action="store_true", help="전체 섹션 매트릭스 출력")
    parser.add_argument("--report", action="store_true", help="준비도·제출 상태 요약 출력")
    parser.add_argument("--gaps", action="store_true", help="미작성(필수) 섹션 출력")
    parser.add_argument("--submission", action="store_true", help="제출 상태만 출력")
    args = parser.parse_args(argv)

    if args.matrix:
        print(_format_matrix())
    elif args.report:
        print(_format_report())
    elif args.gaps:
        r = assess_readiness()
        if not r.missing_required:
            print("필수 미충족 섹션 없음 (준비 완료)")
        for sid in r.missing_required:
            section = find_section(sid)
            print(f"{section.title}: {section.summary}")
    elif args.submission:
        print(CURRENT_SUBMISSION)
    else:
        print(_format_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
