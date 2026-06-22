"""ODYSSEY Phase 411 — 해외 파일럿 제안서(overseas pilot proposal) 적합성 게이트.

Global Expansion 트랙(Phase 401-420) 중 밴드 ``411-420``("해외 파일럿 제안서
3종 — 아세안 도서 배송·EU U-space 데모·미국 대학 연구 협력")의 칸. Phase 410
(`gutma_contribution`)이 국제 *커뮤니티 기고* 가능성을 평가한다면, 본 모듈은
SDACS 를 해외 현지에서 실증할 **파일럿 제안서**가 상대 기관에 제출될 형식·근거
요건을 갖췄는지를 사람이 매번 직관으로 점검하지 않도록 **결정적 게이트**로
명문화한다.

왜 별도 모듈인가 (중복 회피)
--------------------------
- **Phase 404 EN 완역** 은 *문서 산출물* 자체다(README.en 등).
- **Phase 405 국제 벤치마크** 는 *성능 비교 매트릭스*(BlueSky·U-TRAFMAN)다.
- **Phase 410 `gutma_contribution`** 은 GUTMA *작업 항목* 에 SDACS 자산을
  대응시키는 기여 가능성 평가다.
- **본 모듈(411)** 은 *특정 해외 실증 제안* 한 건이 상대 관할·기관에 제출
  가능한 요건을 갖췄는가를 판정한다 — "이 제안서를 지금 보내도 되나". 평가
  대상이 서로 다르다(문서 vs 벤치마크 vs 기여 vs 제안 준비도).

요건의 권위 근거 (추측 아님)
--------------------------
각 기준은 해외 무인기 실증을 규율하는 공개 규제·관행에서 도출하고 명문 근거를
결속한다.
- **규제 운영 근거**: EU 는 EASA Regulation (EU) 2019/947 + U-space 2021/664,
  미국은 FAA 14 CFR Part 107 + 공역 승인(COA)/BEYOND 프로그램, 싱가포르/아세안은
  CAAS Unmanned Aircraft (Public Safety and Security) Act + ASEAN UTM 협력 —
  *법적 운영 근거 없이는 실증 불가*.
- **현지 호스트/파트너**: 해외 실증은 현지 운영자·USS·대학 등 책임 주체가
  필수(보험·책임·현장 운용).
- **대상 언어 산출물**: 제안서·운용 문서가 상대 기관 작업 언어(영문)로 준비.
- **데이터 거주·개인정보**: EU GDPR 등 관할별 개인정보·데이터 이전 규율 충족.

설계 원칙
--------
- **자문이지 집행 아님**: 제안서를 *제출하지 않는다*. 현 후보의 적합성만 판정
  (부수효과 0).
- **정직한 자가 공시**: ``shipped_proposals()`` 는 현재 검토 중인 실제 후보 3종을
  격상 없이 판정해 미충족을 드러낸다. 세 후보 모두 현지 파트너(PP-03) 미확보가
  공통 결격임을 정직히 표면화한다.
- **기능 커버리지(PP-02)는 디스크 실재로 결속**: MET/PARTIAL 후보가 인용한
  SDACS 모듈은 리포에 실재해야 한다(``missing_module_refs`` + 테스트 강제).
- **판정은 코드가 유일 명세**: ``POLICY_MATRIX`` 가 권위 있는 진리표이며 테스트가
  ``assess`` 와 정확 일치를 강제한다(문서는 서술만, 중복 로직 0).

무작위성 0 · 결정적 · 기존 모듈 무수정 순수 추가.

CLI:
    python -m simulation.overseas_pilot_proposal --criteria   # 요건 매트릭스
    python -m simulation.overseas_pilot_proposal --status     # 현 후보 3종 판정
    python -m simulation.overseas_pilot_proposal --policy     # 판정 진리표
    python -m simulation.overseas_pilot_proposal --manifest   # JSON 매니페스트
"""
from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

# 리포 루트 — 인용 모듈 경로는 이 기준의 상대 경로다.
_REPO_ROOT = Path(__file__).resolve().parent.parent

# --- 기준 충족 상태(개별) --------------------------------------------------
STATUS_MET = "MET"          # 요건 완전 충족
STATUS_PARTIAL = "PARTIAL"  # 일부만 충족(보완 필요)
STATUS_UNMET = "UNMET"      # 미충족

_STATUSES = (STATUS_MET, STATUS_PARTIAL, STATUS_UNMET)

# --- 심각도 ---------------------------------------------------------------
SEVERITY_CRITICAL = "CRITICAL"        # 미충족 시 제안 접수 거부 위험 — 제출 차단
SEVERITY_RECOMMENDED = "RECOMMENDED"  # 채택률·신뢰도 향상

_SEVERITY_WEIGHT: Mapping[str, int] = MappingProxyType(
    {SEVERITY_CRITICAL: 2, SEVERITY_RECOMMENDED: 1}
)

# --- 전체 판정 -------------------------------------------------------------
VERDICT_READY_TO_PROPOSE = "READY_TO_PROPOSE"  # 전 기준 충족 — 제출 가능
VERDICT_NEEDS_WORK = "NEEDS_WORK"              # CRITICAL 은 미충족 없음, 보완 필요
VERDICT_NOT_READY = "NOT_READY"                # CRITICAL 미충족 — 제출 부적합


@dataclass(frozen=True)
class PilotCriterion:
    """해외 파일럿 제안서 적합성 기준 한 칸(불변).

    Attributes:
        criterion_id: 안정 식별자(중복 불가).
        severity: ``CRITICAL``(필수) 또는 ``RECOMMENDED``.
        description: 사람이 읽는 한 줄 요건.
        rationale: 권위 근거(추측 아님 — 명문 출처).
    """

    criterion_id: str
    severity: str
    description: str
    rationale: str

    def __post_init__(self) -> None:
        if not self.criterion_id or self.criterion_id != self.criterion_id.strip():
            raise ValueError("criterion_id must be non-empty and unpadded")
        if self.severity not in _SEVERITY_WEIGHT:
            raise ValueError(f"알 수 없는 심각도: {self.severity!r}")
        if not self.description.strip():
            raise ValueError("description must be non-empty")
        if not self.rationale.strip():
            raise ValueError("rationale must be non-empty")

    def weight(self) -> int:
        return _SEVERITY_WEIGHT[self.severity]


# 요건 6종(SSoT). 필수 4 + 권장 2. 각 기준은 위 docstring 의 권위 근거에서 도출.
CRITERIA: tuple[PilotCriterion, ...] = (
    PilotCriterion(
        "PP-01", SEVERITY_CRITICAL,
        "대상 관할의 규제 운영 근거 식별(법적 운영 카테고리·승인 경로)",
        "EASA 2019/947+U-space 2021/664 · FAA 14 CFR Part 107+COA/BEYOND · "
        "CAAS Unmanned Aircraft Act: 법적 운영 근거 없이는 실증 불가.",
    ),
    PilotCriterion(
        "PP-02", SEVERITY_CRITICAL,
        "유스케이스 ↔ SDACS 기능 커버리지(참조 구현 모듈 인용)",
        "제안 유스케이스를 뒷받침할 실재 기능 자산이 있어야 제안이 신뢰됨 — "
        "인용 모듈은 디스크 실재로 결속.",
    ),
    PilotCriterion(
        "PP-03", SEVERITY_CRITICAL,
        "현지 호스트/파트너 식별(운영자·USS·대학 등 책임 주체)",
        "해외 실증은 현지 책임 주체(보험·책임·현장 운용)가 필수.",
    ),
    PilotCriterion(
        "PP-04", SEVERITY_CRITICAL,
        "대상 언어(영문) 제안·운용 산출물 준비",
        "상대 기관 작업 언어 산출물 없이는 접수·검토 불가(Phase 404 연계).",
    ),
    PilotCriterion(
        "PP-05", SEVERITY_RECOMMENDED,
        "데이터 거주·개인정보 적합(GDPR 등 관할별 규율)",
        "EU GDPR 등 관할별 개인정보·데이터 이전 규율 충족 시 채택률 향상.",
    ),
    PilotCriterion(
        "PP-06", SEVERITY_RECOMMENDED,
        "자금·일정 계획(예산·마일스톤·기간)",
        "실행 가능성 입증 — 예산·마일스톤 명시가 제안 신뢰도 향상.",
    ),
)

_CRITERION_IDS = tuple(c.criterion_id for c in CRITERIA)


@dataclass(frozen=True)
class PilotProposal:
    """후보 해외 파일럿 제안서 한 건의 기준별 충족 상태(불변).

    Attributes:
        proposal_id: 안정 식별자(중복 불가).
        target: 사람이 읽는 제안 라벨.
        jurisdiction: 대상 관할(EU·US·ASEAN 등).
        statuses: ``criterion_id -> STATUS_*`` 매핑. 모든 기준 id 를 빠짐없이
            포함해야 한다(부분 입력 금지 — 정직성).
        module_refs: PP-02(기능 커버리지) 근거로 인용하는 SDACS 모듈의 리포
            상대 경로(비어 있지 않은 튜플). PP-02 가 MET/PARTIAL 이면 실재
            모듈이어야 한다(``missing_module_refs`` 가 강제).
    """

    proposal_id: str
    target: str
    jurisdiction: str
    statuses: Mapping[str, str]
    module_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.proposal_id or self.proposal_id != self.proposal_id.strip():
            raise ValueError("proposal_id must be non-empty and unpadded")
        if not self.target.strip():
            raise ValueError("target must be non-empty")
        if not self.jurisdiction.strip():
            raise ValueError("jurisdiction must be non-empty")
        missing = [cid for cid in _CRITERION_IDS if cid not in self.statuses]
        if missing:
            raise ValueError(f"누락된 기준 상태: {', '.join(missing)}")
        unknown = [cid for cid in self.statuses if cid not in _CRITERION_IDS]
        if unknown:
            raise ValueError(f"알 수 없는 기준 id: {', '.join(unknown)}")
        bad = sorted(
            f"{cid}={st}" for cid, st in self.statuses.items() if st not in _STATUSES
        )
        if bad:
            raise ValueError(f"알 수 없는 상태: {', '.join(bad)}")
        # 기능 커버리지를 주장(MET/PARTIAL)하면 근거 모듈을 반드시 인용해야 한다.
        if self.statuses["PP-02"] in (STATUS_MET, STATUS_PARTIAL) and not self.module_refs:
            raise ValueError(
                "PP-02 MET/PARTIAL 은 module_refs 로 근거 모듈을 인용해야 한다"
            )
        if any(not ref.strip() for ref in self.module_refs):
            raise ValueError("module_refs 항목은 비어 있을 수 없다")
        # 검증 후 읽기 전용 사본으로 고정 — frozen 의 불변 보장을 dict 내용까지 확장.
        object.__setattr__(self, "statuses", MappingProxyType(dict(self.statuses)))


@dataclass(frozen=True)
class PilotAssessment:
    """제안서 제출 적합성 판정 결과(불변)."""

    proposal_id: str
    verdict: str
    score: float                          # 가중 충족 비율 0.0~1.0(PARTIAL = 절반)
    met: tuple[str, ...]                   # MET 기준 id(정렬)
    unmet_critical: tuple[str, ...]        # CRITICAL UNMET id(정렬)
    partial_critical: tuple[str, ...]      # CRITICAL PARTIAL id(정렬)
    other_incomplete: tuple[str, ...]      # 비-CRITICAL 미완(정렬)
    reasons: tuple[str, ...] = ()

    def is_ready(self) -> bool:
        return self.verdict == VERDICT_READY_TO_PROPOSE

    def summary(self) -> str:
        pct = f"{self.score * 100:.1f}%"
        return f"{self.verdict} ({pct}): {'; '.join(self.reasons)}"


def _verdict_for(has_critical_unmet: bool, has_any_incomplete: bool) -> str:
    """판정 핵심 규칙(POLICY_MATRIX 의 권위 있는 구현).

    우선순위: CRITICAL UNMET → NOT_READY > 그 외 미완(CRITICAL PARTIAL 또는
    권장 PARTIAL/UNMET) → NEEDS_WORK > 전부 MET → READY_TO_PROPOSE.

    CRITICAL PARTIAL 은 정책상 권장 미완과 동일 판정(NEEDS_WORK)을 내므로 별도
    인자로 가르지 않는다. ``POLICY_MATRIX`` 가 ``critical_partial`` 플래그를 별도
    칸으로 유지하는 것은 *실현 가능한 상태 공간*을 정직히 드러내기 위함이며 판정
    가중은 ``has_any_incomplete`` 에 흡수된다.
    """
    if has_critical_unmet:
        return VERDICT_NOT_READY
    if has_any_incomplete:
        return VERDICT_NEEDS_WORK
    return VERDICT_READY_TO_PROPOSE


# 판정 진리표(SSoT). (critical_unmet, critical_partial, any_incomplete) → verdict.
# 테스트가 본 표와 ``assess`` 의 정확 일치를 강제한다.
# any_incomplete 는 CRITICAL UNMET/PARTIAL 을 포함하므로 critical_unmet=True
# 또는 critical_partial=True 이면 any_incomplete=True 만 실현 가능(그 외 모순 → 제외).
POLICY_MATRIX: tuple[tuple[tuple[bool, bool, bool], str], ...] = (
    ((True, False, True), VERDICT_NOT_READY),
    ((True, True, True), VERDICT_NOT_READY),
    ((False, True, True), VERDICT_NEEDS_WORK),
    ((False, False, True), VERDICT_NEEDS_WORK),
    ((False, False, False), VERDICT_READY_TO_PROPOSE),
)


def _status_credit(status: str) -> float:
    """충족 점수 기여 비율(MET=1, PARTIAL=0.5, UNMET=0)."""
    if status == STATUS_MET:
        return 1.0
    if status == STATUS_PARTIAL:
        return 0.5
    return 0.0


def assess(proposal: PilotProposal) -> PilotAssessment:
    """후보 제안서를 요건 전체에 대해 결정적으로 판정한다.

    CRITICAL 이 하나라도 UNMET 이면 NOT_READY, CRITICAL 은 통과하나 어떤
    기준이든 MET 미만이면 NEEDS_WORK, 전부 MET 이면 READY_TO_PROPOSE. 점수는
    가중 충족(PARTIAL=절반) 비율(소수 넷째 자리 반올림 — 결정적).
    """
    met: list[str] = []
    unmet_critical: list[str] = []
    partial_critical: list[str] = []
    other_incomplete: list[str] = []
    credit = 0.0
    total_weight = 0

    for crit in CRITERIA:
        status = proposal.statuses[crit.criterion_id]
        total_weight += crit.weight()
        credit += _status_credit(status) * crit.weight()
        if status == STATUS_MET:
            met.append(crit.criterion_id)
            continue
        if crit.severity == SEVERITY_CRITICAL:
            if status == STATUS_UNMET:
                unmet_critical.append(crit.criterion_id)
            else:
                partial_critical.append(crit.criterion_id)
        else:
            other_incomplete.append(crit.criterion_id)

    has_any_incomplete = bool(unmet_critical or partial_critical or other_incomplete)
    verdict = _verdict_for(bool(unmet_critical), has_any_incomplete)
    score = round(credit / total_weight, 4) if total_weight else 0.0

    # 권장 미완은 PARTIAL/UNMET 을 구분해 정직히 표기(같은 NEEDS_WORK 라도 상태가 다름).
    rec_partial = sorted(
        c for c in other_incomplete if proposal.statuses[c] == STATUS_PARTIAL
    )
    rec_unmet = sorted(
        c for c in other_incomplete if proposal.statuses[c] == STATUS_UNMET
    )
    reasons: list[str] = []
    if unmet_critical:
        reasons.append(f"미충족 CRITICAL: {', '.join(sorted(unmet_critical))}")
    if partial_critical:
        reasons.append(f"부분 CRITICAL: {', '.join(sorted(partial_critical))}")
    if rec_partial:
        reasons.append(f"부분 권장: {', '.join(rec_partial)}")
    if rec_unmet:
        reasons.append(f"미충족 권장: {', '.join(rec_unmet)}")
    if not reasons:
        reasons.append("전 요건 충족 — 제안서 제출 가능")

    return PilotAssessment(
        proposal_id=proposal.proposal_id,
        verdict=verdict,
        score=score,
        met=tuple(sorted(met)),
        unmet_critical=tuple(sorted(unmet_critical)),
        partial_critical=tuple(sorted(partial_critical)),
        other_incomplete=tuple(sorted(other_incomplete)),
        reasons=tuple(reasons),
    )


def shipped_proposals() -> tuple[PilotProposal, ...]:
    """현재 검토 중인 실제 해외 파일럿 후보 3종(정직한 자가 공시).

    아세안 도서 배송·EU U-space 데모·미국 대학 연구 협력. 세 후보 모두 현지
    호스트/파트너(PP-03) 미확보가 공통 CRITICAL 결격이라 격상 없이 NOT_READY 로
    드러낸다(해외 실증의 실제 병목, 아세안은 PP-04 영문 산출물 추가 결격).
    기능 커버리지(PP-02)는 리포에 실재하는 모듈을 인용해 결속한다.
    """
    return (
        PilotProposal(
            proposal_id="asean_island_delivery",
            target="아세안 도서 의약품 배송 실증 (CAAS Singapore / ASEAN UTM)",
            jurisdiction="ASEAN",
            statuses={
                "PP-01": STATUS_PARTIAL,  # CAAS 경로 식별, BVLOS 승인 미확정
                "PP-02": STATUS_MET,      # 도서 의료 배송 거점·공역 모델 실재
                "PP-03": STATUS_UNMET,    # 현지 운영자 미확보
                "PP-04": STATUS_UNMET,    # 영문 제안서 미작성(README.en 미머지)
                "PP-05": STATUS_UNMET,    # 데이터 거주 정책 미수립
                "PP-06": STATUS_UNMET,    # 예산·일정 미수립
            },
            module_refs=(
                "src/applications/jeonnam_island_sites.py",
                "simulation/flight_plan_filing.py",
                "simulation/geo_zones.py",
            ),
        ),
        PilotProposal(
            proposal_id="eu_uspace_demo",
            target="EU U-space 디컨플릭션 데모 (EASA 2021/664)",
            jurisdiction="EU",
            statuses={
                "PP-01": STATUS_MET,      # EASA U-space 운영 근거 명확
                "PP-02": STATUS_MET,      # U-space 매핑·운영 의도 모델 실재
                "PP-03": STATUS_UNMET,    # EU USS/USP 파트너 미확보
                "PP-04": STATUS_PARTIAL,  # 핵심 문서 영문화 일부
                "PP-05": STATUS_PARTIAL,  # GDPR 고려, 완결 미흡
                "PP-06": STATUS_UNMET,    # 예산·일정 미수립
            },
            module_refs=(
                "simulation/geo_zones.py",
                "simulation/operational_intent.py",
                "simulation/sora_category.py",
            ),
        ),
        PilotProposal(
            proposal_id="us_university_research",
            target="미국 대학 UAS 연구 협력 (FAA Part 107 / COA·BEYOND)",
            jurisdiction="US",
            statuses={
                "PP-01": STATUS_PARTIAL,  # Part 107 + 대학 COA 경로, 미확정
                "PP-02": STATUS_MET,      # 시뮬레이터·Ablation 연구 도구 실재
                "PP-03": STATUS_UNMET,    # 미국 대학 MOU 미체결
                "PP-04": STATUS_PARTIAL,  # 연구 산출물 영문 일부
                "PP-05": STATUS_MET,      # 시뮬 데이터, 개인정보 비해당
                "PP-06": STATUS_UNMET,    # 연구비·일정 미수립
            },
            module_refs=(
                "scripts/ablation_study.py",
                "simulation/icao_utm_conformance.py",
            ),
        ),
    )


def find_proposal(proposal_id: str) -> PilotProposal:
    """식별자로 후보 제안서를 조회한다. 없으면 KeyError."""
    for proposal in shipped_proposals():
        if proposal.proposal_id == proposal_id:
            return proposal
    raise KeyError(f"unknown pilot proposal: {proposal_id!r}")


def missing_module_refs(proposal: PilotProposal) -> tuple[str, ...]:
    """인용 모듈 중 리포에 실재하지 않는 경로를 정렬로 반환한다(정직성 검사)."""
    return tuple(
        sorted(ref for ref in proposal.module_refs if not (_REPO_ROOT / ref).is_file())
    )


def most_ready() -> PilotAssessment:
    """가장 준비도(점수)가 높은 후보의 판정을 반환한다(동점 시 식별자 정렬 우선)."""
    assessments = [assess(p) for p in shipped_proposals()]
    # 점수 내림차순, 동점은 식별자 오름차순으로 결정적 선택.
    return sorted(assessments, key=lambda a: (-a.score, a.proposal_id))[0]


def criteria_manifest() -> dict[str, Any]:
    """요건·진리표·후보 판정을 JSON 직렬화 가능한 매니페스트로 굳힌다."""
    return {
        "schema": "sdacs-overseas-pilot-proposal",
        "version": "1.0",
        "severities": {
            SEVERITY_CRITICAL: _SEVERITY_WEIGHT[SEVERITY_CRITICAL],
            SEVERITY_RECOMMENDED: _SEVERITY_WEIGHT[SEVERITY_RECOMMENDED],
        },
        "statuses": list(_STATUSES),
        "verdicts": [
            VERDICT_READY_TO_PROPOSE,
            VERDICT_NEEDS_WORK,
            VERDICT_NOT_READY,
        ],
        "criteria": [
            {
                "id": c.criterion_id,
                "severity": c.severity,
                "description": c.description,
                "rationale": c.rationale,
            }
            for c in CRITERIA
        ],
        "policy_matrix": [
            {
                "critical_unmet": k[0],
                "critical_partial": k[1],
                "any_incomplete": k[2],
                "verdict": v,
            }
            for k, v in POLICY_MATRIX
        ],
        "proposals": [
            {
                "id": p.proposal_id,
                "target": p.target,
                "jurisdiction": p.jurisdiction,
                "verdict": (a := assess(p)).verdict,
                "score": a.score,
            }
            for p in shipped_proposals()
        ],
    }


def _cmd_criteria() -> None:
    print("해외 파일럿 제안서 적합성 요건")
    print(f"{'ID':<8}{'SEVERITY':<13}DESCRIPTION")
    for c in CRITERIA:
        print(f"{c.criterion_id:<8}{c.severity:<13}{c.description}")
    print("\nCRITICAL 한 칸이라도 UNMET 이면 전체 판정은 NOT_READY")


def _cmd_status() -> None:
    marks = {STATUS_MET: "OK  ", STATUS_PARTIAL: "PART", STATUS_UNMET: "FAIL"}
    for proposal in shipped_proposals():
        print(f"\n[{proposal.jurisdiction}] {proposal.target}")
        for c in CRITERIA:
            st = proposal.statuses[c.criterion_id]
            print(f"  {marks[st]} {c.criterion_id:<8}{c.severity:<13}{st}")
        print(f"  판정: {assess(proposal).summary()}")


def _cmd_policy() -> None:
    print("판정 진리표 (critical_unmet, critical_partial, any_incomplete) → verdict")
    for (cu, cp, ai), verdict in POLICY_MATRIX:
        print(f"  ({cu!s:<5}, {cp!s:<5}, {ai!s:<5}) → {verdict}")


_KNOWN_FLAGS = ("--criteria", "--status", "--policy", "--manifest")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    unknown = [a for a in args if a not in _KNOWN_FLAGS]
    if unknown:
        print(f"알 수 없는 인자: {' '.join(unknown)}", file=sys.stderr)
        print(f"사용법: {' | '.join(_KNOWN_FLAGS)}", file=sys.stderr)
        return 2
    if "--manifest" in args:
        print(json.dumps(criteria_manifest(), ensure_ascii=False, indent=2))
        return 0
    if "--policy" in args:
        _cmd_policy()
        return 0
    if "--status" in args:
        _cmd_status()
        return 0
    _cmd_criteria()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
