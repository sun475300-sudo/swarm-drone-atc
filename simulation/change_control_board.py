"""GENESIS Phase 318 — CCB(변경통제위원회) 변경통제 적합성 게이트.

Certification & Compliance 트랙(Phase 301-320)의 잔여 칸. SDACS 의 실제 변경
관리 절차(GitHub PR·CI 게이트·canonical hash·RTM·CHANGELOG)가 형상관리 표준
(ISO 10007 형상관리 지침 · DO-178C §7 SCM · SCMP 변경통제 절차)의 **변경통제
위원회(CCB)** 요건을 어디까지 충족하는가를 *결정적*으로 자가 평가한다.

설계 원칙(프로젝트 정직성 규약)
-------------------------------
- **정직성 결속**: 한 기준이 ``MET`` 이면 반드시 실재하는 증거 산출물 경로를
  인용해야 하고(디스크 실재 강제), ``UNMET`` 이면 증거를 인용해선 안 된다.
  ``PARTIAL`` 은 증거는 있으나 형식 요건(전담 CCB 역할·정족수 등)이 미비한 칸.
- **격상 금지**: SDACS 는 *학생 캡스톤* 이라 전담 CCB 조직·긴급변경 절차가
  없다 — 이를 숨기지 않고 ``PARTIAL``/``UNMET`` 으로 그대로 드러낸다.
- **무작위성 0 · 부수효과 0 · 기존 모듈 무수정 순수 추가.**

CLI:
    python -m simulation.change_control_board --matrix   # 기준별 판정
    python -m simulation.change_control_board --report   # 종합 적합성 요약
    python -m simulation.change_control_board --gaps     # 미충족 기준만
    python -m simulation.change_control_board --json     # JSON 매니페스트
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

# ── 판정 상수 ────────────────────────────────────────────────────────────────
STATUS_MET = "met"
STATUS_PARTIAL = "partial"
STATUS_UNMET = "unmet"
_VALID_STATUS = (STATUS_MET, STATUS_PARTIAL, STATUS_UNMET)

SEVERITY_CRITICAL = "critical"
SEVERITY_RECOMMENDED = "recommended"
_VALID_SEVERITY = (SEVERITY_CRITICAL, SEVERITY_RECOMMENDED)

VERDICT_CONFORMANT = "conformant"
VERDICT_PARTIAL = "partial"
VERDICT_NONCONFORMANT = "nonconformant"

# 가중 점수: met=1.0, partial=0.5, unmet=0.0. CONFORMANT 판정 임계값.
_SCORE = {STATUS_MET: 1.0, STATUS_PARTIAL: 0.5, STATUS_UNMET: 0.0}
_CONFORMANT_THRESHOLD = 0.80


@dataclass(frozen=True)
class CcbCriterion:
    """CCB 변경통제 기준 한 칸(불변).

    Attributes:
        criterion_id: 안정 식별자(``CCB-01`` 형식).
        title: 사람이 읽는 기준 제목.
        severity: ``critical`` 또는 ``recommended``.
        status: ``met``/``partial``/``unmet``.
        evidence: 충족 증거 산출물 경로(리포 루트 상대). ``unmet`` 이면 None.
        rationale: 판정 근거(정직 공시).
    """

    criterion_id: str
    title: str
    severity: str
    status: str
    evidence: str | None
    rationale: str

    def __post_init__(self) -> None:
        if self.status not in _VALID_STATUS:
            raise ValueError(f"status 부적합: {self.status!r}")
        if self.severity not in _VALID_SEVERITY:
            raise ValueError(f"severity 부적합: {self.severity!r}")
        # 정직성 결속: met/partial 은 증거 필수, unmet 은 증거 금지.
        if self.status in (STATUS_MET, STATUS_PARTIAL) and not self.evidence:
            raise ValueError(f"{self.criterion_id}: {self.status} 는 증거 경로 필수")
        if self.status == STATUS_UNMET and self.evidence is not None:
            raise ValueError(f"{self.criterion_id}: unmet 는 증거를 인용할 수 없음")


# ── SDACS 실제 변경통제 절차 ↔ CCB 요건 매핑(결정적) ──────────────────────────
# 인용 증거는 모두 리포에 실재하는 산출물이며 test 가 디스크 실재를 강제한다.
_CRITERIA: tuple[CcbCriterion, ...] = (
    CcbCriterion(
        "CCB-01", "변경 요청(CR) 단일 채널", SEVERITY_CRITICAL, STATUS_MET,
        "CHANGELOG.md",
        "모든 변경은 GitHub PR/Issue 로 발의되고 CHANGELOG 에 단일 기록된다.",
    ),
    CcbCriterion(
        "CCB-02", "변경 영향 분석", SEVERITY_CRITICAL, STATUS_PARTIAL,
        "docs/certification/RTM_5LAYER_COVERAGE.md",
        "RTM 5계층으로 변경 영향을 추적하나, 형식화된 영향분석 템플릿(CR별 "
        "필수 필드)은 미비 → PARTIAL.",
    ),
    CcbCriterion(
        "CCB-03", "변경 검토·승인 권한 게이트", SEVERITY_CRITICAL, STATUS_PARTIAL,
        "ROADMAP.md",
        "PR 리뷰·머지 승인 절차는 있으나 전담 CCB 역할·정족수(quorum)·서명 "
        "기록이 없음 → PARTIAL(단독 결정 위험 표면화).",
    ),
    CcbCriterion(
        "CCB-04", "베이스라인 형상 통제", SEVERITY_CRITICAL, STATUS_MET,
        ".github/workflows/canonical_hash.yml",
        "git 태그 + canonical hash 검증 워크플로로 베이스라인 무결성을 통제한다.",
    ),
    CcbCriterion(
        "CCB-05", "변경 추적성(CR↔변경↔검증)", SEVERITY_CRITICAL, STATUS_MET,
        "docs/certification/RTM_5LAYER_COVERAGE.md",
        "REQ↔DSN↔IMP↔VER 5계층 RTM 으로 요구↔변경↔검증을 추적한다.",
    ),
    CcbCriterion(
        "CCB-06", "변경 전 회귀 검증 게이트", SEVERITY_CRITICAL, STATUS_MET,
        ".github/workflows/ci.yml",
        "CI 가 머지 전 전체 회귀·커버리지·정적분석 게이트를 강제한다.",
    ),
    CcbCriterion(
        "CCB-07", "긴급 변경 절차", SEVERITY_RECOMMENDED, STATUS_UNMET,
        None,
        "사후 승인·롤백 기준을 갖춘 형식 긴급변경(emergency change) 절차 부재.",
    ),
    CcbCriterion(
        "CCB-08", "변경 이력·감사 로그", SEVERITY_RECOMMENDED, STATUS_MET,
        "CHANGELOG.md",
        "CHANGELOG + git 이력으로 변경 사유·일자·범위를 감사 가능하게 보존한다.",
    ),
)

_CRITERIA_BY_ID = MappingProxyType({c.criterion_id: c for c in _CRITERIA})


@dataclass(frozen=True)
class CcbReport:
    """CCB 변경통제 적합성 종합 판정(불변)."""

    verdict: str
    score: float                       # 가중 점수 0.0~1.0(넷째 자리 반올림)
    met: tuple[str, ...]
    partial: tuple[str, ...]
    unmet: tuple[str, ...]
    unmet_critical: tuple[str, ...]    # severity=critical 인 미충족(unmet) 기준

    @property
    def total(self) -> int:
        return len(self.met) + len(self.partial) + len(self.unmet)

    def summary(self) -> str:
        pct = f"{self.score * 100:.1f}%"
        label = {
            VERDICT_CONFORMANT: "적합",
            VERDICT_PARTIAL: "부분 적합",
            VERDICT_NONCONFORMANT: "부적합",
        }[self.verdict]
        return (
            f"CCB 변경통제 {label} ({pct}): "
            f"충족 {len(self.met)} · 부분 {len(self.partial)} · 미충족 {len(self.unmet)}"
            f" / 총 {self.total} (핵심 미충족 {len(self.unmet_critical)})"
        )


def criteria() -> tuple[CcbCriterion, ...]:
    """CCB 변경통제 기준 매트릭스(결정적·불변)."""
    return _CRITERIA


def assess(items: tuple[CcbCriterion, ...] | None = None) -> CcbReport:
    """변경통제 절차의 CCB 적합성을 결정적으로 판정한다.

    판정 규칙:
      - 핵심(critical) 기준이 하나라도 ``unmet`` 이면 NONCONFORMANT(가중점수 무관).
      - 그 외에는 가중 점수 ≥ 0.80 이면 CONFORMANT, 미만이면 PARTIAL.
    """
    rows = _CRITERIA if items is None else items
    if not rows:
        raise ValueError("기준이 비어 있음")
    met: list[str] = []
    partial: list[str] = []
    unmet: list[str] = []
    unmet_critical: list[str] = []
    for c in rows:
        if c.status == STATUS_MET:
            met.append(c.criterion_id)
        elif c.status == STATUS_PARTIAL:
            partial.append(c.criterion_id)
        else:
            unmet.append(c.criterion_id)
            if c.severity == SEVERITY_CRITICAL:
                unmet_critical.append(c.criterion_id)
    score = round(sum(_SCORE[c.status] for c in rows) / len(rows), 4)
    if unmet_critical:
        verdict = VERDICT_NONCONFORMANT
    elif score >= _CONFORMANT_THRESHOLD:
        verdict = VERDICT_CONFORMANT
    else:
        verdict = VERDICT_PARTIAL
    return CcbReport(
        verdict=verdict,
        score=score,
        met=tuple(sorted(met)),
        partial=tuple(sorted(partial)),
        unmet=tuple(sorted(unmet)),
        unmet_critical=tuple(sorted(unmet_critical)),
    )


def cited_evidence_paths() -> tuple[str, ...]:
    """met/partial 기준이 인용한 증거 산출물 경로(중복 제거·정렬)."""
    paths = {c.evidence for c in _CRITERIA if c.evidence is not None}
    return tuple(sorted(paths))


def verify_evidence_on_disk(repo_root: Path) -> tuple[str, ...]:
    """인용 증거 중 디스크에 실재하지 않는 경로를 반환한다(없으면 빈 튜플).

    정직성 게이트 — 허위 충족 주장을 차단한다.
    """
    missing = [p for p in cited_evidence_paths() if not (repo_root / p).exists()]
    return tuple(missing)


def manifest() -> dict[str, Any]:
    """기준·판정을 JSON 직렬화 가능한 매니페스트로 굳힌다."""
    report = assess()
    return {
        "schema": "sdacs-ccb-change-control",
        "version": "1.0",
        "phase": 318,
        "verdict": report.verdict,
        "score": report.score,
        "criteria": [
            {
                "id": c.criterion_id,
                "title": c.title,
                "severity": c.severity,
                "status": c.status,
                "evidence": c.evidence,
                "rationale": c.rationale,
            }
            for c in _CRITERIA
        ],
        "unmet_critical": list(report.unmet_critical),
    }


# ── CLI ──────────────────────────────────────────────────────────────────────
_STATUS_MARK = {STATUS_MET: "MET ", STATUS_PARTIAL: "PART", STATUS_UNMET: "GAP "}


def _cmd_matrix() -> None:
    print("CCB 변경통제 기준 매트릭스 (GENESIS Phase 318)")
    for c in _CRITERIA:
        print(f"  [{_STATUS_MARK[c.status]}] {c.criterion_id} ({c.severity:<11}) {c.title}")
        print(f"          {c.rationale}")
        if c.evidence:
            print(f"          근거: {c.evidence}")


def _cmd_report() -> None:
    print(assess().summary())


def _cmd_gaps() -> None:
    print("미충족·부분 기준 (보완 대상)")
    rows = [c for c in _CRITERIA if c.status != STATUS_MET]
    if not rows:
        print("  (없음 — 전 기준 충족)")
        return
    for c in rows:
        print(f"  [{_STATUS_MARK[c.status]}] {c.criterion_id} ({c.severity}) — {c.title}")
        print(f"          {c.rationale}")


_KNOWN_FLAGS = ("--matrix", "--report", "--gaps", "--json")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    unknown = [a for a in args if a not in _KNOWN_FLAGS]
    if unknown:
        print(f"알 수 없는 인자: {' '.join(unknown)}", file=sys.stderr)
        print(f"사용법: {' | '.join(_KNOWN_FLAGS)}", file=sys.stderr)
        return 2
    if "--json" in args:
        print(json.dumps(manifest(), ensure_ascii=False, indent=2))
        return 0
    if "--gaps" in args:
        _cmd_gaps()
        return 0
    if "--report" in args:
        _cmd_report()
        return 0
    _cmd_matrix()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
