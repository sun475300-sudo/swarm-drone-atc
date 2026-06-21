"""ODYSSEY Phase 500 — Centennial 선언(100년 준비도 종합 게이트).

Continuum 트랙(Phase 481-500)의 *마지막 칸*이자 전체 500-Phase 프로그램의
종착 선언. "이 프로젝트는 원저자·현 세대를 넘어 100년 단위로 살아남을 준비가
되었는가"를 사람이 매번 직관으로 선언하지 않도록 **결정적 종합 게이트**로
명문화한다 — 같은 리포 상태는 항상 같은 판정을 낸다.

설계 원칙
--------
- **종합이지 재정의 아님(DRY)**: Centennial 준비도는 네 기둥(pillar)의 합이며,
  각 기둥의 판정 규칙은 *이미 배포된 자매 모듈*에 한 번씩만 적혀 있다. 본
  모듈은 그 게이트들을 *호출만* 하고 판정 로직을 복제하지 않는다.
    - 유산 준비도 → Phase 490 ``legacy_readiness``
    - 아카이브 이중화 → Phase 489 ``archive_redundancy``
    - 거버넌스 승계 → Phase 487 ``governance_succession``
    - 세대 이양 집행 → Phase 492 ``track_handoff_readiness.select_track``
      (491 공모 게이트 → 492 선정 파이프라인의 *종착* 판정)
- **전부 충족이라야 선언(all-or-nothing)**: Centennial 선언은 *마일스톤*이다.
  네 기둥은 모두 100년 생존의 필요조건이므로, 하나라도 미충족이면 전체 판정은
  ``NOT_DECLARED``. 점수는 정직한 진척 공시용일 뿐 선언을 앞당기지 않는다.
- **자문이지 집행 아님**: 본 모듈은 *현 상태를 판정*할 뿐 누락 자산을 만들지
  않는다(부수효과 0). 사람/CI 가 실제 보완을 집행한다.
- **정직 공시**: 현 리포는 LICENSE 전문 부재·DOI 미발급·원저자 1인·2027+
  차세대 기수 미형성으로 네 기둥 모두 미충족 → ``NOT_DECLARED``. 어느 기둥이
  채워지면 자매 모듈의 회귀 핀이 *의도적으로* 깨져 본 선언 갱신을 강제한다.

무작위성 0 · 결정적 · 기존 모듈 무수정 순수 추가.

CLI:
    python -m simulation.centennial_declaration --pillars   # 기둥 매트릭스
    python -m simulation.centennial_declaration --status    # 리포 현 선언 판정
    python -m simulation.centennial_declaration --manifest  # 매니페스트(JSON)
"""
from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from simulation.archive_redundancy import (
    assess_redundancy,
    shipped_registry as archive_shipped_registry,
)
from simulation.governance_succession import (
    assess_succession,
    documents_complete,
    shipped_maintainers,
)
from simulation.legacy_readiness import assess_legacy_readiness
from simulation.track_handoff_readiness import (
    select_track,
    shipped_proposals,
)

# --- 기둥 식별자 -----------------------------------------------------------
PILLAR_LEGACY = "legacy_readiness"          # Phase 490 — 10년 재현/인용/법적
PILLAR_ARCHIVE = "archive_durability"       # Phase 489 — 단일 실패점 없는 사본
PILLAR_GOVERNANCE = "governance_succession"  # Phase 487 — 위원회 승계
PILLAR_HANDOVER = "generational_handover"   # Phase 492 — 차세대 이양 집행(선정)

# --- 기둥 판정(개별) -------------------------------------------------------
STATE_SATISFIED = "SATISFIED"  # 자매 게이트가 종착-준비 상태 보고
STATE_UNMET = "UNMET"          # 아직 미달

# --- 선언 판정(전체) -------------------------------------------------------
VERDICT_DECLARED = "DECLARED"          # 네 기둥 전부 충족 — Centennial 선언 가능
VERDICT_NOT_DECLARED = "NOT_DECLARED"  # 한 기둥이라도 미충족 — 선언 불가


@dataclass(frozen=True)
class CentennialPillar:
    """Centennial 선언을 떠받치는 기둥 하나(불변·메타데이터).

    판정 로직은 본 클래스에 없다 — ``phase`` 가 가리키는 자매 모듈이 유일한
    권위 명세이며, 본 기둥은 그 게이트를 *어디서 가져오는지*만 기술한다.

    Attributes:
        pillar_id: 안정 식별자(중복 불가).
        phase: 판정을 위임하는 자매 Phase 번호.
        description: 사람이 읽는 한 줄 설명.
        ready_state: 충족으로 인정되는 자매 게이트의 종착 상태 이름(공시용).
    """

    pillar_id: str
    phase: int
    description: str
    ready_state: str


# 기둥 레지스트리(SSoT). 순서·식별자는 안정적이며, 각 기둥의 실제 판정은
# ``_default_gates`` 가 자매 모듈에 위임한다.
PILLARS: tuple[CentennialPillar, ...] = (
    CentennialPillar(
        PILLAR_LEGACY, 490,
        "10년 재현·인용·법적 사용 준비(디지털 유산 체크리스트)",
        "READY",
    ),
    CentennialPillar(
        PILLAR_ARCHIVE, 489,
        "단일 실패점 없는 내구 아카이브(독립 보관처 ≥2곳 검증)",
        "REDUNDANT",
    ),
    CentennialPillar(
        PILLAR_GOVERNANCE, 487,
        "원저자를 넘는 위원회 승계 준비(연속성 보유자 ≥3인 + 문서)",
        "COMMITTEE_READY",
    ),
    CentennialPillar(
        PILLAR_HANDOVER, 492,
        "차세대 트랙 이양 집행(491 공모 → 492 적격 제안 선정 완료)",
        "HANDOFF_READY",
    ),
)


@dataclass(frozen=True)
class PillarStatus:
    """단일 기둥의 충족 여부 + 위임 게이트의 한 줄 근거(불변)."""

    pillar_id: str
    state: str
    detail: str

    def is_satisfied(self) -> bool:
        return self.state == STATE_SATISFIED


@dataclass(frozen=True)
class CentennialDeclaration:
    """리포 전체의 Centennial(100년) 준비도 판정 결과(불변)."""

    verdict: str
    progress: float                  # 충족 기둥 비율 0.0~1.0
    satisfied: tuple[str, ...]       # 충족 기둥 id(정렬)
    unmet: tuple[str, ...]           # 미충족 기둥 id(정렬)
    pillars: tuple[PillarStatus, ...]  # 기둥별 상세(레지스트리 순서)
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def is_declared(self) -> bool:
        """Centennial 선언 가능 상태인가."""
        return self.verdict == VERDICT_DECLARED

    def summary(self) -> str:
        """사람이 읽는 한 줄 요약."""
        pct = f"{self.progress * 100:.1f}%"
        return f"{self.verdict} ({pct}): {'; '.join(self.reasons)}"


def _legacy_gate(repo_root: Path) -> tuple[bool, str]:
    """Phase 490 유산 준비도 게이트(READY 여야 충족)."""
    result = assess_legacy_readiness(repo_root)
    return result.is_ready(), f"Phase 490 → {result.verdict}"


def _archive_gate(_repo_root: Path) -> tuple[bool, str]:
    """Phase 489 아카이브 이중화 게이트(REDUNDANT 여야 충족).

    아카이브 상태는 디스크가 아닌 외부 보관처(Zenodo 등)에 있으므로
    ``repo_root`` 와 무관하게 *이 프로젝트의 실제 예치 상태*를 판정한다.
    """
    result = assess_redundancy(archive_shipped_registry())
    return result.is_durable(), f"Phase 489 → {result.verdict}"


def _governance_gate(repo_root: Path) -> tuple[bool, str]:
    """Phase 487 거버넌스 승계 게이트(COMMITTEE_READY 여야 충족)."""
    result = assess_succession(
        shipped_maintainers(), docs_complete=documents_complete(repo_root)
    )
    return result.is_ready(), f"Phase 487 → {result.verdict}"


def _handover_gate(_repo_root: Path) -> tuple[bool, str]:
    """Phase 491/492 세대 이양 집행 게이트(HANDOFF_READY 여야 충족).

    이양 집행 = 적격 제안에서 차세대 트랙이 *선정*됨. 2027+ 기수가 아직
    형성되지 않아 현재는 ``AWAITING_PROPOSALS`` (선정 0).
    """
    result = select_track(shipped_proposals())
    return result.is_handoff_ready(), f"Phase 492 → {result.verdict}"


# 기둥 id → 위임 게이트 함수(레지스트리 순서 고정).
_GATE_FUNCS = {
    PILLAR_LEGACY: _legacy_gate,
    PILLAR_ARCHIVE: _archive_gate,
    PILLAR_GOVERNANCE: _governance_gate,
    PILLAR_HANDOVER: _handover_gate,
}


def _default_gates(
    repo_root: Path,
    skip: frozenset[str] = frozenset(),
) -> dict[str, tuple[bool, str]]:
    """리포 상태에 대해 기둥을 자매 모듈에 위임 평가한다.

    ``skip`` 에 든 기둥은 *실제 게이트를 호출하지 않는다* — 호출자가 주입값으로
    대체하므로, 주입은 위임 평가를 진짜로 건너뛴다(부수효과·계약 정합).
    """
    return {
        pid: func(repo_root)
        for pid, func in _GATE_FUNCS.items()
        if pid not in skip
    }


def assess_centennial(
    repo_root: str | Path,
    gate_overrides: Mapping[str, bool] | None = None,
) -> CentennialDeclaration:
    """네 기둥을 종합해 Centennial 선언 가능 여부를 결정적으로 판정한다.

    한 기둥이라도 미충족이면 ``NOT_DECLARED``, 전부 충족이면 ``DECLARED``.
    진척(``progress``)은 충족 기둥 수를 전체 기둥 수로 나눈 비율(소수 넷째
    자리 반올림 — 결정적)이며 선언 자체에는 영향을 주지 않는다(공시용).

    ``gate_overrides`` 는 기둥 id → bool 매핑으로, 주어지면 해당 기둥의 위임
    평가를 대체한다(테스트용 결정적 주입점). 알 수 없는 id 는 ``KeyError``.
    """
    root = Path(repo_root)
    overrides = dict(gate_overrides) if gate_overrides is not None else {}
    unknown = set(overrides) - set(_GATE_FUNCS)
    if unknown:
        raise KeyError(f"알 수 없는 기둥 id: {', '.join(sorted(unknown))}")

    # 주입된 기둥은 실제 게이트를 건너뛴다(계약: override 는 위임을 대체).
    evaluated = _default_gates(root, skip=frozenset(overrides))
    statuses: list[PillarStatus] = []
    satisfied: list[str] = []
    unmet: list[str] = []

    for pillar in PILLARS:
        if pillar.pillar_id in overrides:
            ok = bool(overrides[pillar.pillar_id])
            detail = f"주입값 → {'충족' if ok else '미충족'}"
        else:
            ok, detail = evaluated[pillar.pillar_id]
        state = STATE_SATISFIED if ok else STATE_UNMET
        statuses.append(PillarStatus(pillar.pillar_id, state, detail))
        (satisfied if ok else unmet).append(pillar.pillar_id)

    total = len(PILLARS)
    progress = round(len(satisfied) / total, 4) if total else 0.0
    verdict = VERDICT_DECLARED if not unmet else VERDICT_NOT_DECLARED

    if unmet:
        reasons = (f"미충족 기둥 {len(unmet)}/{total}: {', '.join(sorted(unmet))}",)
    else:
        reasons = ("네 기둥 전부 충족 — Centennial 선언 준비 완료",)

    return CentennialDeclaration(
        verdict=verdict,
        progress=progress,
        satisfied=tuple(sorted(satisfied)),
        unmet=tuple(sorted(unmet)),
        pillars=tuple(statuses),
        reasons=reasons,
    )


def declaration_manifest() -> dict[str, Any]:
    """기둥 레지스트리를 JSON 직렬화 가능한 매니페스트로 굳힌다."""
    return {
        "schema": "sdacs-centennial-declaration",
        "version": "1.0",
        "verdicts": [VERDICT_DECLARED, VERDICT_NOT_DECLARED],
        "pillars": [
            {
                "id": p.pillar_id,
                "phase": p.phase,
                "description": p.description,
                "ready_state": p.ready_state,
            }
            for p in PILLARS
        ],
    }


def _repo_root() -> Path:
    """리포 루트(이 파일의 부모의 부모)."""
    return Path(__file__).resolve().parent.parent


def _cmd_pillars() -> None:
    print("Centennial(100년) 선언 기둥 매트릭스")
    print(f"{'PILLAR':<24}{'PHASE':<8}{'READY':<18}DESCRIPTION")
    for p in PILLARS:
        print(f"{p.pillar_id:<24}{p.phase:<8}{p.ready_state:<18}{p.description}")
    print("\n네 기둥 전부 충족이라야 DECLARED — 하나라도 미충족이면 NOT_DECLARED")


def _cmd_status() -> None:
    root = _repo_root()
    result = assess_centennial(root)
    print("리포 현 Centennial 준비도(정직 공시):")
    for status in result.pillars:
        mark = "OK  " if status.is_satisfied() else "MISS"
        print(f"  {mark} {status.pillar_id:<24}{status.state:<12}{status.detail}")
    print(f"\n판정: {result.summary()}")


_KNOWN_FLAGS = ("--pillars", "--status", "--manifest")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    unknown = [a for a in args if a not in _KNOWN_FLAGS]
    if unknown:
        print(f"알 수 없는 인자: {' '.join(unknown)}", file=sys.stderr)
        print(f"사용법: {' | '.join(_KNOWN_FLAGS)}", file=sys.stderr)
        return 2
    if "--manifest" in args:
        print(json.dumps(declaration_manifest(), ensure_ascii=False, indent=2))
        return 0
    if "--status" in args:
        _cmd_status()
        return 0
    _cmd_pillars()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
