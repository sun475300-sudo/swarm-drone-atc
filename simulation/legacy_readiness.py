"""ODYSSEY Phase 490 — 디지털 유산(Digital Legacy) 준비도 체크리스트.

Continuum 트랙(Phase 481-500)의 한 칸이자 트랙의 마무리 선언. 졸업 후 10년,
원저자가 손을 뗀 뒤에도 이 프로젝트가 *재현 가능하고 인용 가능하며 법적으로
사용 가능한* 상태로 살아남는가를 사람이 매번 직관으로 점검하지 않도록
**결정적 체크리스트**로 명문화한다 — 같은 리포 상태는 항상 같은 판정을 낸다.

설계 원칙
--------
- **정책은 코드, 코드는 정책**: 유산 준비도 판정 규칙을 문서(``docs/
  standards/DIGITAL_LEGACY_CHECKLIST.md``)와 본 평가기에 *한 번씩만* 적기
  위해, 본 모듈이 유일한 실행 가능 명세다. 문서는 규칙을 서술할 뿐 중복
  로직을 두지 않는다(테스트가 ``CHECKLIST`` ↔ ``check_criterion`` 일치 강제).
- **증거는 디스크에 실재해야 한다**: 각 기준은 *리포에 실제로 존재하는 파일*
  로만 충족(SATISFIED)된다. "준비할 예정" 은 충족이 아니다(정직성).
- **자문이지 집행 아님**: 본 모듈은 *현 상태를 판정*할 뿐 누락 자산을
  생성하지 않는다(부수효과 0). 사람/CI 가 실제 보완을 집행한다.
- **CRITICAL 한 칸이라도 비면 READY 아님**: 재현성·라이선스·내구 아카이브는
  10년 생존의 필요조건이므로, 하나라도 미충족이면 전체 판정은 NOT_READY.
- **아카이브 차원은 Phase 489 에 위임**: 내구 사본 충분성은
  ``archive_redundancy`` 의 결정적 판정을 재사용한다(중복 로직 0).

무작위성 0 · 결정적 · 기존 모듈 무수정 순수 추가.

CLI:
    python -m simulation.legacy_readiness --checklist   # 기준 매트릭스 출력
    python -m simulation.legacy_readiness --status      # 리포 현 상태 판정
    python -m simulation.legacy_readiness --manifest    # 체크리스트 매니페스트(JSON)
"""
from __future__ import annotations

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from simulation.archive_redundancy import assess_redundancy, shipped_registry

# --- 유산 차원 -------------------------------------------------------------
DIM_REPRODUCIBILITY = "reproducibility"  # 동일 결과 재생성 가능성
DIM_LICENSING = "licensing"              # 법적 사용 가능성
DIM_ARCHIVAL = "archival"                # 내구 사본(단일 실패점 없음)
DIM_IDENTITY = "identity"                # 인용·식별 메타데이터
DIM_DOCUMENTATION = "documentation"      # 인수자가 읽을 문서
DIM_SECURITY = "security"                # 장기 보안 대응 절차
DIM_GOVERNANCE = "governance"            # 유지보수자 승계 규약

_DIMENSIONS = (
    DIM_REPRODUCIBILITY,
    DIM_LICENSING,
    DIM_ARCHIVAL,
    DIM_IDENTITY,
    DIM_DOCUMENTATION,
    DIM_SECURITY,
    DIM_GOVERNANCE,
)

# --- 심각도(가중치) --------------------------------------------------------
SEVERITY_CRITICAL = "CRITICAL"        # 미충족 시 10년 생존 불가 — READY 차단
SEVERITY_IMPORTANT = "IMPORTANT"      # 인수·재현 품질에 중대
SEVERITY_RECOMMENDED = "RECOMMENDED"  # 있으면 좋음

_SEVERITY_WEIGHT: dict[str, int] = {
    SEVERITY_CRITICAL: 3,
    SEVERITY_IMPORTANT: 2,
    SEVERITY_RECOMMENDED: 1,
}

# --- 기준 판정(개별) -------------------------------------------------------
STATE_SATISFIED = "SATISFIED"  # 증거 실재 — 충족
STATE_UNMET = "UNMET"          # 증거 누락/조건 미달

# --- 준비도 판정(전체) -----------------------------------------------------
VERDICT_READY = "READY"          # 전 기준 충족 — 10년 인계 준비됨
VERDICT_PARTIAL = "PARTIAL"      # CRITICAL 은 충족, 일부 보완 권장
VERDICT_NOT_READY = "NOT_READY"  # CRITICAL 미충족 — 생존 위험


@dataclass(frozen=True)
class LegacyCriterion:
    """유산 준비도 기준 한 칸(불변).

    Attributes:
        criterion_id: 안정 식별자(중복 불가).
        dimension: ``_DIMENSIONS`` 중 하나.
        severity: ``CRITICAL``·``IMPORTANT``·``RECOMMENDED``.
        description: 사람이 읽는 한 줄 설명.
        evidence: 리포 루트 기준 상대 경로들. *모두* 실재해야 충족.
        requires_durable_archive: True 면 파일 실재에 더해 Phase 489 의
            내구 아카이브 판정(REDUNDANT)까지 통과해야 충족.
    """

    criterion_id: str
    dimension: str
    severity: str
    description: str
    evidence: tuple[str, ...]
    requires_durable_archive: bool = False

    def weight(self) -> int:
        """심각도 가중치(점수 집계용)."""
        return _SEVERITY_WEIGHT[self.severity]


# 체크리스트(SSoT). 각 evidence 경로는 리포에 실재하는 자산을 가리킨다 —
# 누락 자산(LICENSE·docs/GOVERNANCE.md)은 의도적으로 *현 미충족* 을 정직히
# 드러낸다. 본 튜플이 유일한 권위 명세이며, 문서는 이를 서술만 한다.
CHECKLIST: tuple[LegacyCriterion, ...] = (
    LegacyCriterion(
        "repro-pinned-deps", DIM_REPRODUCIBILITY, SEVERITY_CRITICAL,
        "의존성 핀 + 재현 컨테이너 + 독립 재현 스크립트",
        ("requirements.lock.txt", "Dockerfile.reproducible",
         "docs/REPRODUCIBILITY.md", "scripts/independent_reproduction.sh"),
    ),
    LegacyCriterion(
        "license-file", DIM_LICENSING, SEVERITY_CRITICAL,
        "최상위 LICENSE 전문(선언만으로는 부족 — 법적 사용 보장)",
        ("LICENSE",),
    ),
    LegacyCriterion(
        "archival-durable", DIM_ARCHIVAL, SEVERITY_CRITICAL,
        "단일 실패점 없는 내구 아카이브(Phase 489 판정 REDUNDANT)",
        # 이 두 파일은 citation-metadata 와 공유한다(같은 메타데이터가
        # 아카이브 예치·인용 식별 두 목적에 모두 쓰임). 파일 실재에 더해
        # requires_durable_archive 게이트가 추가로 걸린다.
        (".zenodo.json", "CITATION.cff"),
        requires_durable_archive=True,
    ),
    LegacyCriterion(
        "citation-metadata", DIM_IDENTITY, SEVERITY_IMPORTANT,
        "인용·식별 메타데이터(CITATION.cff + Zenodo 메타)",
        # archival-durable 와 동일 파일 공유(목적만 다름 — 게이트 없음).
        ("CITATION.cff", ".zenodo.json"),
    ),
    LegacyCriterion(
        "handover-docs", DIM_DOCUMENTATION, SEVERITY_IMPORTANT,
        "인수자용 README + 기여 가이드",
        ("README.md", "CONTRIBUTING.md"),
    ),
    LegacyCriterion(
        "security-support", DIM_SECURITY, SEVERITY_IMPORTANT,
        "보안 신고 창구 + CVE 대응 SLA(Phase 488)",
        ("SECURITY.md", "docs/standards/CVE_RESPONSE_SLA_POLICY.md"),
    ),
    LegacyCriterion(
        "dependency-policy", DIM_REPRODUCIBILITY, SEVERITY_RECOMMENDED,
        "의존성 자동 갱신 게이트 정책(Phase 481)",
        ("docs/standards/DEPENDENCY_AUTOMERGE_POLICY.md",),
    ),
    LegacyCriterion(
        "governance-succession", DIM_GOVERNANCE, SEVERITY_RECOMMENDED,
        "유지보수자 승계 규약(BDFL→위원회, Phase 487)",
        ("docs/GOVERNANCE.md",),
    ),
)


def _evidence_present(criterion: LegacyCriterion, repo_root: Path) -> bool:
    """기준의 모든 증거 파일이 디스크에 실재하는지 결정적으로 확인한다."""
    return all((repo_root / rel).is_file() for rel in criterion.evidence)


def _default_archive_gate() -> bool:
    """현 프로젝트의 내구 아카이브 충분성(Phase 489 판정 REDUNDANT 여부).

    리포 경로에 무관하게 *이 프로젝트의 실제 예치 상태*(``shipped_registry``)를
    판정한다 — 아카이브 이중화는 디스크 파일이 아니라 외부 보관처(Zenodo 등)의
    상태이기 때문이다. 현재는 DOI 미발급으로 항상 False(AT_RISK).
    """
    return assess_redundancy(shipped_registry()).is_durable()


def check_criterion(
    criterion: LegacyCriterion,
    repo_root: str | Path,
    archive_gate: Callable[[], bool] | None = None,
) -> str:
    """단일 기준의 충족 여부를 결정적으로 판정한다.

    충족(SATISFIED)은 (1) 모든 증거 파일 실재 + (2) 아카이브 기준이면 추가로
    내구성 게이트 통과까지 모두 만족할 때만. 그 외 UNMET.

    ``requires_durable_archive`` 게이트는 ``repo_root`` 와 무관하게 평가된다
    (아카이브 상태는 디스크가 아닌 외부 보관처에 있음). 기본 게이트는
    현 프로젝트의 Phase 489 판정(``_default_archive_gate``)이며, 테스트는
    ``archive_gate`` 로 결정적 상태를 주입할 수 있다.
    """
    root = Path(repo_root)
    if not _evidence_present(criterion, root):
        return STATE_UNMET
    if criterion.requires_durable_archive:
        gate = archive_gate if archive_gate is not None else _default_archive_gate
        if not gate():
            return STATE_UNMET
    return STATE_SATISFIED


@dataclass(frozen=True)
class LegacyAssessment:
    """리포 전체의 유산 준비도 판정 결과(불변)."""

    verdict: str
    score: float                              # 가중 충족 비율 0.0~1.0
    satisfied: tuple[str, ...]                # 충족 기준 id(정렬)
    unmet_critical: tuple[str, ...]           # 미충족 CRITICAL id(정렬)
    unmet_other: tuple[str, ...]              # 미충족 비-CRITICAL id(정렬)
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def is_ready(self) -> bool:
        """10년 인계 준비가 완료됐는가."""
        return self.verdict == VERDICT_READY

    def summary(self) -> str:
        """사람이 읽는 한 줄 요약."""
        pct = f"{self.score * 100:.1f}%"
        return f"{self.verdict} ({pct}): {'; '.join(self.reasons)}"


def _verdict_for(has_unmet_critical: bool, no_unmet: bool) -> str:
    """판정 핵심 규칙(체크리스트의 권위 있는 구현)."""
    if has_unmet_critical:
        return VERDICT_NOT_READY
    if no_unmet:
        return VERDICT_READY
    return VERDICT_PARTIAL


def assess_legacy_readiness(
    repo_root: str | Path,
    archive_gate: Callable[[], bool] | None = None,
) -> LegacyAssessment:
    """체크리스트 전체를 리포에 대해 결정적으로 평가한다.

    CRITICAL 기준이 하나라도 미충족이면 NOT_READY, 전부 충족이면 READY,
    그 사이(중요/권장만 미충족)는 PARTIAL. 점수는 충족 기준의 가중치 합을
    전체 가중치 합으로 나눈 비율(소수 넷째 자리 반올림 — 결정적).

    ``archive_gate`` 는 ``check_criterion`` 으로 전달된다(테스트용 주입점,
    기본은 현 프로젝트의 Phase 489 판정).
    """
    root = Path(repo_root)
    satisfied: list[str] = []
    unmet_critical: list[str] = []
    unmet_other: list[str] = []
    satisfied_weight = 0
    total_weight = 0

    for crit in CHECKLIST:
        total_weight += crit.weight()
        if check_criterion(crit, root, archive_gate) == STATE_SATISFIED:
            satisfied.append(crit.criterion_id)
            satisfied_weight += crit.weight()
        elif crit.severity == SEVERITY_CRITICAL:
            unmet_critical.append(crit.criterion_id)
        else:
            unmet_other.append(crit.criterion_id)

    score = round(satisfied_weight / total_weight, 4) if total_weight else 0.0
    verdict = _verdict_for(bool(unmet_critical), not unmet_critical and not unmet_other)

    reasons: list[str] = []
    if unmet_critical:
        reasons.append(f"미충족 CRITICAL: {', '.join(sorted(unmet_critical))}")
    if unmet_other:
        reasons.append(f"보완 권장: {', '.join(sorted(unmet_other))}")
    if not reasons:
        reasons.append("전 기준 충족 — 10년 인계 준비 완료")

    return LegacyAssessment(
        verdict=verdict,
        score=score,
        satisfied=tuple(sorted(satisfied)),
        unmet_critical=tuple(sorted(unmet_critical)),
        unmet_other=tuple(sorted(unmet_other)),
        reasons=tuple(reasons),
    )


def checklist_manifest() -> dict[str, Any]:
    """체크리스트를 JSON 직렬화 가능한 매니페스트로 굳힌다."""
    return {
        "schema": "sdacs-digital-legacy-checklist",
        "version": "1.0",
        "dimensions": list(_DIMENSIONS),
        "severities": {k: _SEVERITY_WEIGHT[k] for k in
                       (SEVERITY_CRITICAL, SEVERITY_IMPORTANT, SEVERITY_RECOMMENDED)},
        "verdicts": [VERDICT_READY, VERDICT_PARTIAL, VERDICT_NOT_READY],
        "criteria": [
            {
                "id": c.criterion_id,
                "dimension": c.dimension,
                "severity": c.severity,
                "description": c.description,
                "evidence": list(c.evidence),
                "requires_durable_archive": c.requires_durable_archive,
            }
            for c in CHECKLIST
        ],
    }


def _repo_root() -> Path:
    """리포 루트(이 파일의 부모의 부모)."""
    return Path(__file__).resolve().parent.parent


def _cmd_checklist() -> None:
    print("디지털 유산 준비도 체크리스트")
    print(f"{'ID':<24}{'DIMENSION':<18}{'SEVERITY':<13}EVIDENCE")
    for c in CHECKLIST:
        print(f"{c.criterion_id:<24}{c.dimension:<18}{c.severity:<13}"
              f"{', '.join(c.evidence)}")
    print("\nCRITICAL 한 칸이라도 미충족이면 전체 판정은 NOT_READY")


def _cmd_status() -> None:
    root = _repo_root()
    print("리포 현 유산 준비도(정직 공시):")
    for c in CHECKLIST:
        state = check_criterion(c, root)
        mark = "OK  " if state == STATE_SATISFIED else "MISS"
        print(f"  {mark} {c.criterion_id:<24}{c.severity:<13}{state}")
    result = assess_legacy_readiness(root)
    print(f"\n판정: {result.summary()}")


_KNOWN_FLAGS = ("--checklist", "--status", "--manifest")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    unknown = [a for a in args if a not in _KNOWN_FLAGS]
    if unknown:
        print(f"알 수 없는 인자: {' '.join(unknown)}", file=sys.stderr)
        print(f"사용법: {' | '.join(_KNOWN_FLAGS)}", file=sys.stderr)
        return 2
    if "--manifest" in args:
        print(json.dumps(checklist_manifest(), ensure_ascii=False, indent=2))
        return 0
    if "--status" in args:
        _cmd_status()
        return 0
    _cmd_checklist()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
