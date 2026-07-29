"""ODYSSEY Phase 472 — 국제 워킹그룹 의견서(opinion letter) 제출 적합성 게이트.

Standards & Policy 트랙(Phase 461-480) 중 밴드 `471-480`("국내 표준(KS) 제안 1건
+ 국제 워킹그룹 의견서 3건")의 한 칸. Phase 471(`ks_standard_proposal`)이 *국내*
KS 제안 준비도를 판정한다면, 본 모듈은 *국제* 표준 워킹그룹(JARUS·EUROCAE WG-105·
ISO/TC 20/SC 16 등)이 회람하는 초안 문서에 SDACS 가 **의견서(comment/opinion
letter)** 를 제출할 때 그 의견서가 실제로 채택될 형식·근거 요건을 갖췄는지를
사람이 매번 직관으로 점검하지 않도록 **결정적 게이트**로 명문화한다.

왜 별도 모듈인가 (중복 회피)
--------------------------
- **Phase 470 `standardization_tracker`** 는 SDACS 가 *발신한* 기고들의 진행
  *상태*(PLANNED→…→ADOPTED)를 추적하는 대시보드다 — "어디까지 갔나".
- **Phase 471 `ks_standard_proposal`** 는 *국내 KS 신규 제정* 제안의 준비도를
  국내 산업표준화법 기준으로 판정한다.
- **본 모듈(472)** 은 *국제 WG 초안에 다는 개별 의견*이 채택 가능한 형식·근거를
  갖췄는가를 판정한다 — "이 의견을 지금 보내도 되나". 셋은 평가 대상이 서로
  다르다(상태 vs 국내 제정 vs 국제 의견).

요건의 권위 근거 (추측 아님)
--------------------------
각 기준은 국제 표준 의견 처리 규약에서 도출하고 명문 근거를 결속한다.
- **ISO/IEC Directives Part 1, Annex(comment template)**: 모든 의견은 (1)대상
  문서·절(clause)·줄 지정, (2)의견 유형 `ge`(general)/`te`(technical)/
  `ed`(editorial) 분류, (3)관찰(observation)과 **제안 변경(proposed change)**
  문안을 *함께* 적어야 처리 대상이 된다("comments without a proposed change may
  not be considered").
- **JARUS Terms of Reference / EUROCAE WG-105 Rules of Procedure**: 의견은 특정
  *문서 버전*을 대상으로 하며 기여자의 소속·이해관계를 공개한다.
- **WTO/TBT §2.4 · ISO 부합 원칙**: 기존 국제 표준과의 정합·중복 관계를 밝힌다.

설계 원칙
--------
- **자문이지 집행 아님**: 의견서를 *제출하지 않는다*. 현 초안의 적합성만 판정
  (부수효과 0).
- **정직한 자가 공시**: `shipped_letter()` 는 현재 준비 중인 실제 후보 의견서를
  격상 없이 판정해 미충족을 드러낸다.
- **판정은 코드가 유일 명세**: `POLICY_MATRIX` 가 권위 있는 진리표이며 테스트가
  `assess` 와 정확 일치를 강제한다(문서는 서술만, 중복 로직 0).

무작위성 0 · 결정적 · 기존 모듈 무수정 순수 추가.

CLI:
    python -m simulation.intl_wg_opinion_gate --criteria   # 요건 매트릭스
    python -m simulation.intl_wg_opinion_gate --status     # 현 후보 의견서 판정
    python -m simulation.intl_wg_opinion_gate --policy     # 판정 진리표
    python -m simulation.intl_wg_opinion_gate --manifest   # JSON 매니페스트
"""
from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

# --- 기준 충족 상태(개별) --------------------------------------------------
STATUS_MET = "MET"          # 요건 완전 충족
STATUS_PARTIAL = "PARTIAL"  # 일부만 충족(보완 필요)
STATUS_UNMET = "UNMET"      # 미충족

_STATUSES = (STATUS_MET, STATUS_PARTIAL, STATUS_UNMET)

# --- 심각도 ---------------------------------------------------------------
SEVERITY_CRITICAL = "CRITICAL"        # 미충족 시 의견 처리 거부 위험 — 제출 차단
SEVERITY_RECOMMENDED = "RECOMMENDED"  # 채택률·신뢰도 향상

_SEVERITY_WEIGHT: dict[str, int] = {
    SEVERITY_CRITICAL: 2,
    SEVERITY_RECOMMENDED: 1,
}

# --- 전체 판정 -------------------------------------------------------------
VERDICT_READY_TO_SUBMIT = "READY_TO_SUBMIT"  # 전 기준 충족 — 제출 가능
VERDICT_NEEDS_WORK = "NEEDS_WORK"            # CRITICAL 은 미충족 없음, 보완 필요
VERDICT_NOT_READY = "NOT_READY"              # CRITICAL 미충족 — 제출 부적합


@dataclass(frozen=True)
class OpinionCriterion:
    """국제 WG 의견서 적합성 기준 한 칸(불변).

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
        if self.severity not in _SEVERITY_WEIGHT:
            raise ValueError(f"알 수 없는 심각도: {self.severity!r}")

    def weight(self) -> int:
        return _SEVERITY_WEIGHT[self.severity]


# 요건 6종(SSoT). 필수 4 + 권장 2. 각 기준은 위 docstring 의 권위 근거에서 도출.
CRITERIA: tuple[OpinionCriterion, ...] = (
    OpinionCriterion(
        "WG-01", SEVERITY_CRITICAL,
        "대상 문서·버전·절(clause)/줄 지정",
        "ISO/IEC Directives Part 1 Annex: 의견은 대상 문서와 절/줄을 명시. "
        "EUROCAE/JARUS RoP: 특정 문서 버전을 대상으로 함.",
    ),
    OpinionCriterion(
        "WG-02", SEVERITY_CRITICAL,
        "제안 변경(proposed change) 문안 — 실행 가능한 redline",
        "ISO/IEC Directives: proposed change 없는 의견은 처리 대상이 아닐 수 있음.",
    ),
    OpinionCriterion(
        "WG-03", SEVERITY_CRITICAL,
        "기술 근거(SDACS 실측·시뮬 데이터) 결속 — 의견 아님",
        "te(technical) 의견은 관찰을 뒷받침할 기술적 정당화를 요구.",
    ),
    OpinionCriterion(
        "WG-04", SEVERITY_CRITICAL,
        "의견 유형 분류 ge/te/ed",
        "ISO/IEC Directives Part 1 comment template: 유형 분류 칸 필수.",
    ),
    OpinionCriterion(
        "WG-05", SEVERITY_RECOMMENDED,
        "기여자 소속·이해관계 공개",
        "JARUS/EUROCAE 참여 규약: 소속·이해상충 공개.",
    ),
    OpinionCriterion(
        "WG-06", SEVERITY_RECOMMENDED,
        "제출 기한·공식 채널(National Body 라우팅) 확인",
        "ISO 의견은 회원국 표준화기구(NB) 경유 기한 내 제출.",
    ),
)

_CRITERION_IDS = tuple(c.criterion_id for c in CRITERIA)


@dataclass(frozen=True)
class OpinionLetter:
    """후보 의견서 한 건의 기준별 충족 상태(불변).

    Attributes:
        target: 대상 WG·문서 식별(사람이 읽는 라벨).
        statuses: ``criterion_id -> STATUS_*`` 매핑. 모든 기준 id 를 빠짐없이
            포함해야 한다(부분 입력 금지 — 정직성).
    """

    target: str
    statuses: Mapping[str, str]

    def __post_init__(self) -> None:
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
        # 검증 후 읽기 전용 사본으로 고정 — frozen 의 불변 보장을 dict 내용까지 확장
        # (구성 이후 외부 변형으로 invariant 가 깨지는 것을 차단).
        object.__setattr__(self, "statuses", MappingProxyType(dict(self.statuses)))


@dataclass(frozen=True)
class OpinionAssessment:
    """의견서 제출 적합성 판정 결과(불변)."""

    verdict: str
    score: float                          # 가중 충족 비율 0.0~1.0(PARTIAL = 절반)
    met: tuple[str, ...]                   # MET 기준 id(정렬)
    unmet_critical: tuple[str, ...]        # CRITICAL UNMET id(정렬)
    partial_critical: tuple[str, ...]      # CRITICAL PARTIAL id(정렬)
    other_incomplete: tuple[str, ...]      # 비-CRITICAL 미완(정렬)
    reasons: tuple[str, ...] = ()

    def is_ready(self) -> bool:
        return self.verdict == VERDICT_READY_TO_SUBMIT

    def summary(self) -> str:
        pct = f"{self.score * 100:.1f}%"
        return f"{self.verdict} ({pct}): {'; '.join(self.reasons)}"


def _verdict_for(has_critical_unmet: bool, has_any_incomplete: bool) -> str:
    """판정 핵심 규칙(POLICY_MATRIX 의 권위 있는 구현).

    우선순위: CRITICAL UNMET → NOT_READY > 그 외 미완(CRITICAL PARTIAL 또는
    권장 PARTIAL/UNMET) → NEEDS_WORK > 전부 MET → READY_TO_SUBMIT.

    CRITICAL PARTIAL 은 정책상 권장 미완과 동일 판정(NEEDS_WORK)을 내므로 별도
    인자로 가르지 않는다. ``POLICY_MATRIX`` 가 ``critical_partial`` 플래그를
    별도 칸으로 유지하는 것은 *실현 가능한 상태 공간*을 정직히 드러내기 위함이며
    판정 가중은 ``has_any_incomplete`` 에 흡수된다.
    """
    if has_critical_unmet:
        return VERDICT_NOT_READY
    if has_any_incomplete:
        return VERDICT_NEEDS_WORK
    return VERDICT_READY_TO_SUBMIT


# 판정 진리표(SSoT). (critical_unmet, critical_partial, any_incomplete) → verdict.
# 테스트가 본 표와 ``assess`` 의 정확 일치를 강제한다.
# any_incomplete 는 CRITICAL UNMET/PARTIAL 을 포함하므로, critical_unmet=True
# 또는 critical_partial=True 이면 any_incomplete=True 만 실현 가능하다
# (그 외 조합은 모순 → 표에서 제외).
POLICY_MATRIX: tuple[tuple[tuple[bool, bool, bool], str], ...] = (
    ((True, False, True), VERDICT_NOT_READY),
    ((True, True, True), VERDICT_NOT_READY),
    ((False, True, True), VERDICT_NEEDS_WORK),
    ((False, False, True), VERDICT_NEEDS_WORK),
    ((False, False, False), VERDICT_READY_TO_SUBMIT),
)


def _status_credit(status: str) -> float:
    """충족 점수 기여 비율(MET=1, PARTIAL=0.5, UNMET=0)."""
    if status == STATUS_MET:
        return 1.0
    if status == STATUS_PARTIAL:
        return 0.5
    return 0.0


def assess(letter: OpinionLetter) -> OpinionAssessment:
    """후보 의견서를 요건 전체에 대해 결정적으로 판정한다.

    CRITICAL 이 하나라도 UNMET 이면 NOT_READY, CRITICAL 은 통과하나 어떤
    기준이든 MET 미만이면 NEEDS_WORK, 전부 MET 이면 READY_TO_SUBMIT. 점수는
    가중 충족(PARTIAL=절반) 비율(소수 넷째 자리 반올림 — 결정적).
    """
    met: list[str] = []
    unmet_critical: list[str] = []
    partial_critical: list[str] = []
    other_incomplete: list[str] = []
    credit = 0.0
    total_weight = 0

    for crit in CRITERIA:
        status = letter.statuses[crit.criterion_id]
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

    has_any_incomplete = bool(
        unmet_critical or partial_critical or other_incomplete
    )
    verdict = _verdict_for(bool(unmet_critical), has_any_incomplete)
    score = round(credit / total_weight, 4) if total_weight else 0.0

    # 권장 미완은 PARTIAL/UNMET 을 구분해 정직히 표기(같은 NEEDS_WORK 라도 상태가 다름).
    rec_partial = sorted(
        c for c in other_incomplete if letter.statuses[c] == STATUS_PARTIAL
    )
    rec_unmet = sorted(
        c for c in other_incomplete if letter.statuses[c] == STATUS_UNMET
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
        reasons.append("전 요건 충족 — 의견서 제출 가능")

    return OpinionAssessment(
        verdict=verdict,
        score=score,
        met=tuple(sorted(met)),
        unmet_critical=tuple(sorted(unmet_critical)),
        partial_critical=tuple(sorted(partial_critical)),
        other_incomplete=tuple(sorted(other_incomplete)),
        reasons=tuple(reasons),
    )


def shipped_letter() -> OpinionLetter:
    """현재 준비 중인 실제 후보 의견서(정직한 자가 공시).

    SDACS 가 JARUS SORA 초안에 다는 군집 운용(swarm operation) 보완 의견.
    작성 모듈(`jarus_sora_opinion`)이 동봉 의견서 문서를 실제로 작성해 실행
    가능한 redline(WG-02)까지 완성했으므로, 본 함수는 그 작성 결과를 *위임
    재사용*하며(DRY — 상태 하드코딩 복제 0) 디스크 증거로부터 도출한다:
    WG-01~WG-05 MET, WG-06 은 WG 회람 기한 외부 의존으로 PARTIAL 상한 →
    NEEDS_WORK(점수 0.95). redline 완성으로 산문 초안(0.8) 대비 정직하게
    격상되었다.
    """
    # 지연 임포트 — jarus_sora_opinion 이 본 모듈의 게이트 계약(OpinionLetter·
    # assess 등)을 임포트하므로 모듈 최상위 임포트는 순환을 만든다.
    from simulation.jarus_sora_opinion import authored_letter

    return authored_letter()


def criteria_manifest() -> dict[str, Any]:
    """요건·진리표를 JSON 직렬화 가능한 매니페스트로 굳힌다."""
    return {
        "schema": "sdacs-intl-wg-opinion-gate",
        "version": "1.0",
        "severities": {
            SEVERITY_CRITICAL: _SEVERITY_WEIGHT[SEVERITY_CRITICAL],
            SEVERITY_RECOMMENDED: _SEVERITY_WEIGHT[SEVERITY_RECOMMENDED],
        },
        "statuses": list(_STATUSES),
        "verdicts": [
            VERDICT_READY_TO_SUBMIT,
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
    }


def _cmd_criteria() -> None:
    print("국제 WG 의견서 적합성 요건")
    print(f"{'ID':<8}{'SEVERITY':<13}DESCRIPTION")
    for c in CRITERIA:
        print(f"{c.criterion_id:<8}{c.severity:<13}{c.description}")
    print("\nCRITICAL 한 칸이라도 UNMET 이면 전체 판정은 NOT_READY")


def _cmd_status() -> None:
    letter = shipped_letter()
    print(f"현 후보 의견서: {letter.target}")
    marks = {STATUS_MET: "OK  ", STATUS_PARTIAL: "PART", STATUS_UNMET: "FAIL"}
    for c in CRITERIA:
        st = letter.statuses[c.criterion_id]
        print(f"  {marks[st]} {c.criterion_id:<8}{c.severity:<13}{st}")
    result = assess(letter)
    print(f"\n판정: {result.summary()}")


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
