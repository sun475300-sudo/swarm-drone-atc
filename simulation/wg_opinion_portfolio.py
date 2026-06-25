"""ODYSSEY Phase 473 — 국제 워킹그룹 의견서 포트폴리오 추적기.

Standards & Policy 트랙(Phase 461-480) 밴드 `471-480`("국내 표준(KS) 제안 1건
+ **국제 워킹그룹 의견서 3건**")의 *국제 의견서 3건* 목표를 단일 SSoT 로
추적한다. Phase 472(`intl_wg_opinion_gate`)가 *의견서 한 건*의 제출 적합성을
판정하는 게이트라면, 본 모듈은 그 게이트를 밴드 목표 수(3건)의 후보 의견서
포트폴리오에 적용해 "3건 중 몇 건이 제출 가능한가, 무엇이 가장 흔히 발목을
잡는가" 를 결정적으로 집계한다.

왜 별도 모듈인가 (중복 회피)
--------------------------
- **Phase 470 `standardization_tracker`** 는 SDACS 가 발신한 *모든* 기고의
  진행 상태(PLANNED→…→ADOPTED)를 추적하는 광역 대시보드다.
- **Phase 472 `intl_wg_opinion_gate`** 는 *의견서 한 건*의 형식·근거 요건을
  판정하는 게이트다("이 의견을 지금 보내도 되나").
- **본 모듈(473)** 은 밴드가 명시한 *3건 목표*에 대해 472 게이트를 적용해
  밴드 완성도를 집계한다("3건 목표에 얼마나 도달했나"). 판정 로직은 472 의
  `assess` 를 *호출만* 하며 복제하지 않는다(DRY — 정책 진리표는 472 가 유일
  명세).

설계 원칙
--------
- **판정 위임(DRY)**: 의견서별 적합성은 전적으로 Phase 472 `assess` 가
  결정한다. 본 모듈은 집계·롤업만 더한다.
- **정직한 자가 공시**: `portfolio()` 는 현재 준비 중인 실제 3건 후보를 격상
  없이 등록한다 — 첫 건(JARUS SORA)은 Phase 472 `shipped_letter` 를 *재사용*
  (복제 0)하고, 잔여 2건(EUROCAE WG-105·ISO/TC 20/SC 16)은 초안 단계 그대로
  드러낸다. 따라서 현 밴드 진행도는 의도적으로 낮게 표면화된다.
- **발목 잡는 요건 롤업**: 제출 불가 의견서들에서 *어떤 기준이 가장 흔히*
  미완인지 집계해, 보완 노력을 어디에 집중할지 결정적으로 안내한다.

무작위성 0 · 결정적 · 기존 모듈 무수정 순수 추가.

CLI:
    python -m simulation.wg_opinion_portfolio --portfolio  # 후보별 판정
    python -m simulation.wg_opinion_portfolio --report     # 밴드 진행 요약
    python -m simulation.wg_opinion_portfolio --blockers    # 발목 요건 롤업
    python -m simulation.wg_opinion_portfolio --manifest    # JSON 매니페스트
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any

from simulation.intl_wg_opinion_gate import (
    CRITERIA,
    STATUS_MET,
    STATUS_PARTIAL,
    STATUS_UNMET,
    VERDICT_NEEDS_WORK,
    VERDICT_NOT_READY,
    VERDICT_READY_TO_SUBMIT,
    OpinionAssessment,
    OpinionLetter,
    assess,
    shipped_letter,
)

# 밴드 471-480 이 명시한 국제 의견서 목표 수("의견서 3건").
BAND_TARGET = 3

_CRITERION_IDS = tuple(c.criterion_id for c in CRITERIA)
_SEVERITY_BY_ID = {c.criterion_id: c.severity for c in CRITERIA}
_DESC_BY_ID = {c.criterion_id: c.description for c in CRITERIA}


@dataclass(frozen=True)
class PortfolioEntry:
    """포트폴리오 내 후보 의견서 한 건 + 그 게이트 판정(불변).

    Attributes:
        letter: 후보 의견서(Phase 472 ``OpinionLetter``).
        assessment: Phase 472 ``assess`` 가 내린 판정(복제 아님 — 위임 결과).
    """

    letter: OpinionLetter
    assessment: OpinionAssessment

    @property
    def label(self) -> str:
        """후보 의견서의 사람이 읽는 라벨(``PortfolioReport.target`` 정수와 구별)."""
        return self.letter.target

    def is_ready(self) -> bool:
        return self.assessment.is_ready()


@dataclass(frozen=True)
class PortfolioReport:
    """밴드 의견서 포트폴리오 집계 결과(불변)."""

    target: int                      # 밴드 목표 의견서 수(3)
    ready: tuple[str, ...]           # READY_TO_SUBMIT 후보 target 라벨(정렬)
    needs_work: tuple[str, ...]      # NEEDS_WORK 후보(정렬)
    not_ready: tuple[str, ...]       # NOT_READY 후보(정렬)

    @property
    def ready_count(self) -> int:
        return len(self.ready)

    @property
    def total(self) -> int:
        return len(self.ready) + len(self.needs_work) + len(self.not_ready)

    @property
    def progress(self) -> float:
        """밴드 목표 대비 제출 가능 의견서 비율(0.0~1.0, 넷째 자리 반올림)."""
        if self.target <= 0:
            return 0.0
        return round(min(self.ready_count, self.target) / self.target, 4)

    @property
    def is_band_complete(self) -> bool:
        """목표 수만큼 제출 가능 의견서를 확보했는가.

        ``target <= 0`` 은 의미 있는 목표가 아니므로 항상 미완으로 본다
        (``progress`` 가 0.0 을 반환하는 것과 정합).
        """
        return self.target > 0 and self.ready_count >= self.target

    def summary(self) -> str:
        pct = f"{self.progress * 100:.1f}%"
        state = "밴드 완료" if self.is_band_complete else "진행 중"
        return (
            f"{state} ({pct}): 제출 가능 {self.ready_count}/{self.target}"
            f" (등록 {self.total}건 · 보완 {len(self.needs_work)} · 부적합 "
            f"{len(self.not_ready)})"
        )


def _eurocae_wg105_letter() -> OpinionLetter:
    """잔여 후보 ①: EUROCAE WG-105 SORA 부속 군집 ConOps 의견(초안).

    대상 문서·절·기술 근거·유형 분류는 갖췄으나 실행 가능한 제안 변경(WG-02)이
    아직 redline 미완(PARTIAL), 공식 NB 채널·기한(WG-06)도 미확인(UNMET) —
    격상 없이 NEEDS_WORK 로 드러낸다.
    """
    return OpinionLetter(
        target="EUROCAE WG-105 — 군집 ConOps 부속 의견",
        statuses={
            "WG-01": STATUS_MET,      # 대상 문서·버전·절 지정 완료
            "WG-02": STATUS_PARTIAL,  # 제안 변경 redline 미완
            "WG-03": STATUS_MET,      # SDACS 시뮬 데이터 결속
            "WG-04": STATUS_MET,      # te 분류
            "WG-05": STATUS_MET,      # 소속 공개
            "WG-06": STATUS_UNMET,    # NB 채널·기한 미확인
        },
    )


def _iso_tc20_letter() -> OpinionLetter:
    """잔여 후보 ②: ISO/TC 20/SC 16 23629 시리즈 의견(초기 초안).

    기여 의향·대상 시리즈는 식별했으나 절/줄 지정(WG-01)·제안 변경(WG-02)이
    아직 미완(UNMET) — CRITICAL 미충족으로 NOT_READY 정직 공시(가장 이른 단계).
    """
    return OpinionLetter(
        target="ISO/TC 20/SC 16 — 23629 시리즈 의견",
        statuses={
            "WG-01": STATUS_UNMET,    # 절/줄 지정 미완
            "WG-02": STATUS_UNMET,    # 제안 변경 미작성
            "WG-03": STATUS_PARTIAL,  # 기술 근거 일부만 결속
            "WG-04": STATUS_MET,      # 유형 분류는 결정
            "WG-05": STATUS_MET,      # 소속 공개
            "WG-06": STATUS_UNMET,    # NB 채널 미확인
        },
    )


def portfolio() -> tuple[PortfolioEntry, ...]:
    """현재 준비 중인 밴드 목표 3건 후보 의견서 + 각 게이트 판정(정직 공시).

    첫 건은 Phase 472 ``shipped_letter`` 를 그대로 재사용(복제 0)하고, 잔여
    2건은 본 모듈이 등록한다. 각 후보는 Phase 472 ``assess`` 로 판정한다.
    """
    letters = (
        shipped_letter(),
        _eurocae_wg105_letter(),
        _iso_tc20_letter(),
    )
    return tuple(
        PortfolioEntry(letter=ltr, assessment=assess(ltr)) for ltr in letters
    )


def assess_portfolio(
    entries: tuple[PortfolioEntry, ...] | None = None,
    target: int = BAND_TARGET,
) -> PortfolioReport:
    """후보 의견서 포트폴리오를 밴드 목표 대비 결정적으로 집계한다."""
    if target < 0:
        raise ValueError(f"target 은 0 이상이어야 함: {target!r}")
    items = portfolio() if entries is None else entries
    ready: list[str] = []
    needs_work: list[str] = []
    not_ready: list[str] = []
    for entry in items:
        verdict = entry.assessment.verdict
        if verdict == VERDICT_READY_TO_SUBMIT:
            ready.append(entry.label)
        elif verdict == VERDICT_NEEDS_WORK:
            needs_work.append(entry.label)
        elif verdict == VERDICT_NOT_READY:
            not_ready.append(entry.label)
        else:  # 상위 게이트가 새 판정값을 추가하면 조용히 NOT_READY 로 흡수하지 않고 즉시 실패
            raise ValueError(f"unexpected verdict from assess(): {verdict!r}")
    return PortfolioReport(
        target=target,
        ready=tuple(sorted(ready)),
        needs_work=tuple(sorted(needs_work)),
        not_ready=tuple(sorted(not_ready)),
    )


def blocking_criteria(
    entries: tuple[PortfolioEntry, ...] | None = None,
) -> tuple[tuple[str, int], ...]:
    """제출 불가 후보들에서 각 기준이 *미완(MET 아님)* 인 빈도를 집계한다.

    어느 요건을 보완하면 가장 많은 의견서가 풀리는지 결정적으로 안내한다.
    빈도 내림차순, 동률은 기준 id 오름차순으로 안정 정렬한다. 빈도 0 기준은
    제외한다(잡음 억제).

    빈도 집계는 PARTIAL 과 UNMET 을 구분하지 않는다(둘 다 "미완" 1건) — CRITICAL
    UNMET 이 NEEDS_WORK 보다 시급할 수 있으므로, 상세 우선순위는 각 후보의 판정
    결과(`unmet_critical` 등)를 직접 참조할 것.
    """
    items = portfolio() if entries is None else entries
    counts: dict[str, int] = dict.fromkeys(_CRITERION_IDS, 0)
    for entry in items:
        if entry.is_ready():
            continue
        for cid in _CRITERION_IDS:
            if entry.letter.statuses[cid] != STATUS_MET:
                counts[cid] += 1
    ranked = sorted(
        ((cid, n) for cid, n in counts.items() if n > 0),
        key=lambda item: (-item[1], item[0]),
    )
    return tuple(ranked)


def portfolio_manifest() -> dict[str, Any]:
    """포트폴리오·집계를 JSON 직렬화 가능한 매니페스트로 굳힌다."""
    entries = portfolio()
    report = assess_portfolio(entries)
    return {
        "schema": "sdacs-wg-opinion-portfolio",
        "version": "1.0",
        "band": "471-480",
        "target": report.target,
        "ready_count": report.ready_count,
        "progress": report.progress,
        "is_band_complete": report.is_band_complete,
        "entries": [
            {
                "target": e.label,
                "verdict": e.assessment.verdict,
                "score": e.assessment.score,
                "unmet_critical": list(e.assessment.unmet_critical),
                "partial_critical": list(e.assessment.partial_critical),
                "other_incomplete": list(e.assessment.other_incomplete),
            }
            for e in entries
        ],
        "blocking_criteria": [
            {
                "id": cid,
                "severity": _SEVERITY_BY_ID[cid],
                "description": _DESC_BY_ID[cid],
                "blocked_letters": n,
            }
            for cid, n in blocking_criteria(entries)
        ],
    }


def _cmd_portfolio() -> None:
    print(f"국제 WG 의견서 포트폴리오 (밴드 471-480 목표 {BAND_TARGET}건)")
    marks = {
        VERDICT_READY_TO_SUBMIT: "READY",
        VERDICT_NEEDS_WORK: "WORK ",
        VERDICT_NOT_READY: "STOP ",
    }
    for e in portfolio():
        mark = marks[e.assessment.verdict]
        print(f"  [{mark}] {e.label}")
        print(f"          {e.assessment.summary()}")


def _cmd_report() -> None:
    report = assess_portfolio()
    print(report.summary())
    if report.ready:
        print(f"  제출 가능: {', '.join(report.ready)}")
    if report.needs_work:
        print(f"  보완 필요: {', '.join(report.needs_work)}")
    if report.not_ready:
        print(f"  제출 부적합: {', '.join(report.not_ready)}")


def _cmd_blockers() -> None:
    print("발목 잡는 요건 (제출 불가 후보 기준 미완 빈도)")
    rows = blocking_criteria()
    if not rows:
        print("  (없음 — 전 후보 제출 가능)")
        return
    for cid, n in rows:
        print(f"  {cid} [{_SEVERITY_BY_ID[cid]:<11}] {n}건 발목 — {_DESC_BY_ID[cid]}")


_KNOWN_FLAGS = ("--portfolio", "--report", "--blockers", "--manifest")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    unknown = [a for a in args if a not in _KNOWN_FLAGS]
    if unknown:
        print(f"알 수 없는 인자: {' '.join(unknown)}", file=sys.stderr)
        print(f"사용법: {' | '.join(_KNOWN_FLAGS)}", file=sys.stderr)
        return 2
    if "--manifest" in args:
        print(json.dumps(portfolio_manifest(), ensure_ascii=False, indent=2))
        return 0
    if "--blockers" in args:
        _cmd_blockers()
        return 0
    if "--report" in args:
        _cmd_report()
        return 0
    _cmd_portfolio()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
