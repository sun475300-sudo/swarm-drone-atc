"""ODYSSEY Standards 잔여 완결 — ISO/TC 20/SC 16 23629 시리즈 의견서 검증.

Standards & Policy 트랙(Phase 461-480) 밴드 `471-480`("국내 표준(KS) 제안 1건
+ 국제 워킹그룹 의견서 3건")의 *국제 의견서 잔여 마지막 1건* 을 실행 가능한
redline 까지 완성한다. Phase 473(`wg_opinion_portfolio`)은 ISO/TC 20/SC 16
후보를 초기 초안(WG-01·WG-02 UNMET → NOT_READY)으로 *격상 없이* 드러냈다.
본 모듈은 동봉 의견서 문서(`docs/standards/ISO_TC20_SC16_23629_OPINION.md`)를
실제로 작성해 그 초안을 **substantiated redline** 으로 정직하게 격상한다.

왜 별도 모듈인가 (중복 회피)
--------------------------
- **Phase 462 `iso_tc20_sc16_tracker`** 는 *외부 ISO 표준 문서 자체* 의 발행
  동향과 SDACS 정렬을 추적한다 — 의견서가 아니다.
- **Phase 472 `intl_wg_opinion_gate`** 는 *의견서 한 건*이 채택될 형식·근거
  요건(WG-01~WG-06)을 판정하는 *일반 게이트* 다. 판정 진리표(SSoT)는 472 다.
- **Phase 473 `wg_opinion_portfolio`** 는 밴드 목표 3건을 *집계* 한다.
- **본 모듈** 은 *ISO/TC 20/SC 16 의견서 그 자체* 를 작성·검증한다. 각 요건
  충족 여부를 동봉 문서의 *디스크 실재·필수 절* 로부터 결정적으로 도출하고,
  판정은 Phase 472 `assess` 를 *호출만* 한다(DRY — 복제 0). 구조는 자매편
  `eurocae_wg105_opinion`(Phase 474)과 동형이다.

정직성 결속
--------
- **증거 기반 상태**: 각 기준은 동봉 문서에 해당 절(앵커 제목)이 실재해야만
  충족으로 본다. WG-02(redline)는 절 제목에 더해 실행 가능한 변경(After 문안)
  센티넬까지 있어야 MET — *산문 수준* 의견과 *실행 가능한 redline* 을 가른다.
- **외부 의존 천장(WG-06)**: NB 라우팅 채널(KATS/KSA 경유)은 문서화 가능하나
  발행 표준(ISO 23629-12:2022)의 체계적 검토(systematic review) 투표·의견
  접수 *기한* 은 ISO 일정에 의존한다. 따라서 채널 절이 실재해도 WG-06 은
  **PARTIAL** 로 상한이 고정된다(채널 ○·기한 ✗). 준비도와 제출 상태는 독립.
- 따라서 현 상태 판정은 `NEEDS_WORK`(점수 0.95) — sandbox 도달 가능한 정직한
  천장이며 `READY_TO_SUBMIT` 은 외부 기한 확정 후에만 가능하다.

무작위성 0 · 결정적 · 부수효과 0(읽기 전용) · 기존 모듈 무수정 순수 추가.

CLI:
    python -m simulation.iso_tc20_sc16_opinion --evidence  # 기준별 증거·상태
    python -m simulation.iso_tc20_sc16_opinion --status    # 게이트 판정
    python -m simulation.iso_tc20_sc16_opinion --manifest  # JSON 매니페스트
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from simulation.intl_wg_opinion_gate import (
    STATUS_MET,
    STATUS_PARTIAL,
    STATUS_UNMET,
    OpinionAssessment,
    OpinionLetter,
    assess,
)

# 동봉 의견서 문서(증거 SSoT). 모듈 위치(simulation/)의 상위가 리포 루트.
DOC_PATH: Path = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "standards"
    / "ISO_TC20_SC16_23629_OPINION.md"
)

# 대상 WG·문서(사람이 읽는 라벨) — Phase 473 포트폴리오 라벨과 동일.
TARGET_LABEL = "ISO/TC 20/SC 16 — 23629 시리즈 의견"


@dataclass(frozen=True)
class CriterionEvidence:
    """기준 한 건의 증거 출처와 판정(불변).

    Attributes:
        criterion_id: Phase 472 기준 id(WG-01~WG-06).
        anchor: 동봉 문서에서 충족을 입증하는 필수 절 제목.
        status: 디스크 증거로부터 도출한 ``STATUS_*``.
        note: 판정 사유(사람이 읽는 한 줄).
    """

    criterion_id: str
    anchor: str
    status: str
    note: str


# 기준 → (필수 절 제목, 추가 콘텐츠 센티넬 | None, 외부 의존 천장 | None).
# 센티넬이 있으면 절 제목 + 센티넬 둘 다 있어야 MET(예: WG-02 redline 의 After 문안).
# 천장이 있으면 절 실재 시에도 그 상태로 상한이 고정된다(WG-06 외부 기한 의존).
_SPEC: tuple[tuple[str, str, str | None, str | None], ...] = (
    ("WG-01", "## 1. 대상 문서·버전·절(clause)", None, None),
    ("WG-02", "## 4. 제안 변경(Proposed Change) — Redline", "**After (제안):**", None),
    ("WG-03", "## 3. 기술 근거 (SDACS 시뮬 증거)", None, None),
    ("WG-04", "## 2. 의견 유형 분류", None, None),
    ("WG-05", "## 5. 기여자 소속·이해관계 공개", None, None),
    ("WG-06", "## 6. 제출 채널 및 기한", None, STATUS_PARTIAL),
)

# 불변식: 한 기준은 센티넬(redline 미완 판별)과 외부 의존 천장을 동시에 갖지
# 않는다 — 둘이 함께면 _status_for/_note_for 의 분기 우선순위가 모호해진다.
assert all(
    sentinel is None or ceiling is None for _, _, sentinel, ceiling in _SPEC
), "한 기준에 sentinel 과 ceiling 을 동시에 둘 수 없음"


def _read_doc(doc_path: Path | None) -> str | None:
    """동봉 문서 텍스트를 읽는다. 부재·읽기 실패 시 ``None``(증거 없음)."""
    path = DOC_PATH if doc_path is None else doc_path
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, IsADirectoryError, PermissionError, OSError):
        return None


def _status_for(
    text: str | None, anchor: str, sentinel: str | None, ceiling: str | None
) -> str:
    """단일 기준의 디스크 증거 상태를 결정적으로 도출한다.

    - 문서 부재 또는 절 제목 부재 → UNMET.
    - 센티넬 요구가 있는데 부재 → PARTIAL(절은 있으나 실행 가능한 변경 미완).
    - 그 외 충족이나 외부 의존 천장이 있으면 그 천장으로 상한 고정.
    """
    if text is None or anchor not in text:
        return STATUS_UNMET
    if sentinel is not None and sentinel not in text:
        return STATUS_PARTIAL
    if ceiling is not None:
        return ceiling
    return STATUS_MET


def evidence(doc_path: Path | None = None) -> tuple[CriterionEvidence, ...]:
    """기준별 증거·상태를 동봉 문서로부터 결정적으로 도출한다(읽기 전용)."""
    text = _read_doc(doc_path)
    out: list[CriterionEvidence] = []
    for cid, anchor, sentinel, ceiling in _SPEC:
        status = _status_for(text, anchor, sentinel, ceiling)
        out.append(
            CriterionEvidence(
                criterion_id=cid,
                anchor=anchor,
                status=status,
                note=_note_for(status, anchor, sentinel, ceiling),
            )
        )
    return tuple(out)


def _note_for(status: str, anchor: str, sentinel: str | None, ceiling: str | None) -> str:
    if status == STATUS_UNMET:
        return f"절 '{anchor}' 부재 — 미충족"
    if status == STATUS_PARTIAL and sentinel is not None:
        return f"절 실재하나 센티넬 '{sentinel}' 부재 — 부분 충족"
    if status == STATUS_PARTIAL and ceiling is not None:
        return "절 실재(NB 채널 문서화). 체계적 검토 기한 외부 의존으로 PARTIAL 상한 고정"
    return f"절 '{anchor}' 실재 — 충족"


def authored_letter(doc_path: Path | None = None) -> OpinionLetter:
    """동봉 문서 증거로부터 ISO/TC 20/SC 16 의견서를 구성한다(Phase 472 형식)."""
    statuses = {ev.criterion_id: ev.status for ev in evidence(doc_path)}
    return OpinionLetter(target=TARGET_LABEL, statuses=statuses)


def assess_letter(doc_path: Path | None = None) -> OpinionAssessment:
    """작성된 의견서를 Phase 472 게이트로 판정한다(DRY — 판정 위임)."""
    return assess(authored_letter(doc_path))


def manifest(doc_path: Path | None = None) -> dict[str, object]:
    """의견서·증거·판정을 JSON 직렬화 가능한 매니페스트로 굳힌다."""
    evs = evidence(doc_path)
    result = assess(authored_letter(doc_path))
    return {
        "schema": "sdacs-iso-tc20-sc16-opinion",
        "version": "1.0",
        "band": "471-480",
        "target": TARGET_LABEL,
        "doc_path": str(DOC_PATH if doc_path is None else doc_path),
        "verdict": result.verdict,
        "score": result.score,
        "evidence": [
            {
                "id": ev.criterion_id,
                "anchor": ev.anchor,
                "status": ev.status,
                "note": ev.note,
            }
            for ev in evs
        ],
    }


def _cmd_evidence() -> None:
    print(f"ISO/TC 20/SC 16 의견서 기준별 증거 (문서: {DOC_PATH.name})")
    marks = {STATUS_MET: "OK  ", STATUS_PARTIAL: "PART", STATUS_UNMET: "FAIL"}
    for ev in evidence():
        print(f"  [{marks[ev.status]}] {ev.criterion_id}  {ev.note}")


def _cmd_status() -> None:
    result = assess_letter()
    print(f"{TARGET_LABEL}")
    print(f"  판정: {result.summary()}")


_KNOWN_FLAGS = ("--evidence", "--status", "--manifest")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    unknown = [a for a in args if a not in _KNOWN_FLAGS]
    if unknown:
        print(f"알 수 없는 인자: {' '.join(unknown)}", file=sys.stderr)
        print(f"사용법: {' | '.join(_KNOWN_FLAGS)}", file=sys.stderr)
        return 2
    if "--manifest" in args:
        print(json.dumps(manifest(), ensure_ascii=False, indent=2))
        return 0
    if "--status" in args:
        _cmd_status()
        return 0
    _cmd_evidence()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
