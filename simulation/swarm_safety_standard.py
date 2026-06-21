"""ODYSSEY Phase 464 — 군집 비행 안전 기준 백서 (5계층 안전망 사례 연구).

군집(swarm) 무인기 공역 운용의 안전 기준을 SDACS 의 **5계층 안전망**(L1 APF →
L5 UTM)을 사례로 제안하는 백서의 *기계 검증 가능한 골격* 이다. 동반 백서 산문은
[`docs/standards/SWARM_SAFETY_STANDARD_WHITEPAPER.md`](../docs/standards/SWARM_SAFETY_STANDARD_WHITEPAPER.md)
이 유일 출처(SSoT)이며, 본 모듈은 그 산문이 주장하는 각 계층의 안전 근거가
*실제로 리포에 선적된 산출물로 뒷받침되는가* 를 결정적으로 감사한다.

자매 모듈과의 경계 (중복 없음)
------------------------------
- Phase 306(`docs/certification/RTM_5LAYER_COVERAGE.md`) 은 REQ→DSN→IMP→VER
  *추적성 매트릭스* 다(각 계층이 무엇인가의 산문 SSoT).
- Phase 441(`simulation/safety_net_invariant.py`) 은 계층 우선순위 단조성
  불변식의 *형식 모델 검사* 다.
- Phase 286(`scripts/ablation_study.py`) 은 계층 제거의 *경험적* 효과 측정이다.
- 본 모듈(464)은 위 셋을 *백서 사례 연구* 관점에서 한데 모아 "제안하는 5계층
  안전 기준이 선적된 산출물로 입증되는가" 를 단일 결정적 판정으로 답한다 —
  지표를 재계산하지 않고(중복 없음) 인용 산출물의 *디스크 실재* 만 감사한다.

정직 공시 (CLAUDE.md)
--------------------
1. 본 모듈이 제안하는 안전 기준 임계는 모두 *제안(proposed)* 이며 채택된 표준이
   아니다. 본 모듈은 *근거 산출물 실재* 를 감사할 뿐 런타임 안전을 보증하지
   않는다. 실 안전은 하드웨어 검증(Track A)에 의존한다(미충족 공시).
2. 계층 상태는 인용 근거의 디스크 실재로만 판정한다. 인용 근거가 모두 존재하고
   그중 실행/형식(module·spec·script) 근거가 1개 이상이면 SUBSTANTIATED,
   일부만 존재하거나 문서만이면 PARTIAL, 하나도 없으면 UNSUBSTANTIATED.
3. 모든 계층은 최소 1개 근거를 인용해야 한다(근거 없는 안전 주장 구조적 금지).
   인용 경로는 리포 상대 경로이며 테스트가 디스크 실재를 강제한다.

무작위성 0 · 결정적 · 부수효과 0. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/swarm_safety_standard.py --layers     # 5계층 정의·근거
    python simulation/swarm_safety_standard.py --report     # 백서 입증 현황 요약
    python simulation/swarm_safety_standard.py --markdown   # 사례 연구 매트릭스
    python simulation/swarm_safety_standard.py --gaps       # 누락 근거(미실재)
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType

# 리포 루트 (이 파일은 <root>/simulation/swarm_safety_standard.py).
_REPO_ROOT = Path(__file__).resolve().parent.parent

# 근거 산출물 종류 (4값). 실행/형식 근거는 module·spec·script.
KINDS: tuple[str, ...] = ("module", "doc", "spec", "script")
_EXECUTABLE_KINDS: frozenset[str] = frozenset({"module", "spec", "script"})

# 계층 입증 상태 (3값).
STATUSES: tuple[str, ...] = ("SUBSTANTIATED", "PARTIAL", "UNSUBSTANTIATED")

# 가중 점수: 완전 입증 1.0·부분 0.5·미입증 0.0.
_STATUS_WEIGHT: dict[str, float] = {
    "SUBSTANTIATED": 1.0,
    "PARTIAL": 0.5,
    "UNSUBSTANTIATED": 0.0,
}


@dataclass(frozen=True)
class SafetyEvidence:
    """한 안전 계층(또는 시스템 전반)을 뒷받침하는 산출물 한 건(불변).

    ``path`` 는 리포 루트 기준 상대 경로다. ``kind`` 는 KINDS 중 하나.
    """

    path: str
    kind: str
    role: str  # 이 산출물이 무엇을 입증하는지 한 줄 설명

    def __post_init__(self) -> None:
        if not self.path or self.path != self.path.strip():
            raise ValueError("path must be non-empty and unpadded")
        if self.path.startswith("/"):
            raise ValueError(f"path must be repo-relative, got {self.path!r}")
        if ".." in PurePosixPath(self.path).parts:
            raise ValueError(f"path must not escape the repo root via '..': {self.path!r}")
        if self.kind not in KINDS:
            raise ValueError(f"kind must be one of {KINDS}, got {self.kind!r}")
        if not self.role or not self.role.strip():
            raise ValueError("role must be a non-empty string")

    @property
    def is_executable(self) -> bool:
        """실행/형식(module·spec·script) 근거 여부."""
        return self.kind in _EXECUTABLE_KINDS

    def exists(self, root: Path | None = None) -> bool:
        """인용 산출물이 디스크에 실재하는지 검사한다."""
        base = _REPO_ROOT if root is None else root
        return (base / self.path).exists()


@dataclass(frozen=True)
class SafetyLayer:
    """5계층 안전망의 한 계층 정의(불변).

    계층 *정의* 산문은 RTM(Phase 306)이 SSoT 이며, 본 dataclass 는 사례 연구
    감사에 필요한 구조 메타데이터(주기·결정 단위·역할·근거)만 보유한다.
    """

    layer_id: str          # 'L1'..'L5'
    name: str              # 'Artificial Potential Field'
    abbrev: str            # 'APF'
    rate_hz: float         # 제어 주기 (Hz)
    decision_scope: str    # '개별 드론'·'다중 에이전트'·'전역' 등
    role: str              # 한 줄 역할
    evidence: tuple[SafetyEvidence, ...]

    def __post_init__(self) -> None:
        if not self.layer_id or not self.layer_id.strip():
            raise ValueError("layer_id must be a non-empty string")
        if " " in self.layer_id:
            raise ValueError("layer_id must not contain internal spaces")
        for field_name in ("name", "abbrev", "decision_scope", "role"):
            value = getattr(self, field_name)
            if not value or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if self.rate_hz <= 0:
            raise ValueError(f"rate_hz must be positive, got {self.rate_hz}")
        if not self.evidence:
            raise ValueError(
                f"layer {self.layer_id!r} must cite at least one evidence artifact"
            )

    def existing_evidence(self, root: Path | None = None) -> tuple[SafetyEvidence, ...]:
        """디스크에 실재하는 근거만 인용 순서대로 반환한다."""
        return tuple(ev for ev in self.evidence if ev.exists(root))

    def missing_evidence(self, root: Path | None = None) -> tuple[SafetyEvidence, ...]:
        """디스크에 부재하는 근거만 인용 순서대로 반환한다."""
        return tuple(ev for ev in self.evidence if not ev.exists(root))

    def status(self, root: Path | None = None) -> str:
        """근거 실재 기준 입증 상태를 결정적으로 판정한다."""
        present = self.existing_evidence(root)
        if not present:
            return "UNSUBSTANTIATED"
        all_present = len(present) == len(self.evidence)
        has_executable = any(ev.is_executable for ev in present)
        if all_present and has_executable:
            return "SUBSTANTIATED"
        return "PARTIAL"


# 5계층 안전망 정의 (정본, 결정적 순서). RTM(Phase 306) 정의와 정합.
# 모든 인용 근거는 리포 실재 산출물(테스트가 디스크 실재 강제).
SAFETY_LAYERS: tuple[SafetyLayer, ...] = (
    SafetyLayer(
        "L1", "Artificial Potential Field", "APF", 10.0, "개별 드론",
        "가까운 장애물에 대한 즉시 척력 회피",
        (
            SafetyEvidence("simulation/apf_lyapunov.py", "module",
                           "APF 힘 F=-∇U 보존성 + Lyapunov 전역 수렴 형식화"),
            SafetyEvidence("docs/APF_CONVERGENCE_PROOF.md", "doc",
                           "APF 수렴성 수학 증명 (Phase 443)"),
        ),
    ),
    SafetyLayer(
        "L2", "Conflict-Based Search", "CBS", 0.1, "다중 에이전트",
        "사전 경로 충돌 해소 (MAPF)",
        (
            SafetyEvidence("simulation/cbs_optimality.py", "module",
                           "CBS 완전성·최적성 조건 독립 BFS 검증 (Phase 444)"),
            SafetyEvidence("docs/CBS_COMPLETENESS_OPTIMALITY.md", "doc",
                           "CBS 완전성·최적성 정리 문서"),
        ),
    ),
    SafetyLayer(
        "L3", "Closest Point of Approach", "CPA", 1.0, "쌍별 예측",
        "미래 충돌 시점 외삽 경보 + 4D 경로 충돌 감지",
        (
            SafetyEvidence("simulation/path_deconflict.py", "module",
                           "4D 경로 충돌 감지 코어 (Phase 448 속성 검증 대상)"),
            SafetyEvidence("docs/certification/RTM_5LAYER_COVERAGE.md", "doc",
                           "L3 CPA REQ→VER 추적성 (Phase 306)"),
        ),
    ),
    SafetyLayer(
        "L4", "Air Traffic Controller", "ATC", 1.0, "전역 관제",
        "명령·우선순위·관제권 핸드오프",
        (
            SafetyEvidence("simulation/handoff_model_checker.py", "module",
                           "핸드오프 FSM 교착 부재 + 단일 관제권 불변식 (Phase 442)"),
            SafetyEvidence("docs/certification/RTM_5LAYER_COVERAGE.md", "doc",
                           "L4 ATC REQ→VER 추적성 (Phase 306)"),
        ),
    ),
    SafetyLayer(
        "L5", "Unmanned Traffic Management", "UTM", 0.1, "전략적",
        "NFZ·회랑·Remote ID·UTM 적합성",
        (
            SafetyEvidence("simulation/icao_utm_conformance.py", "module",
                           "ICAO UTM Framework 적합성 자가 평가 (Phase 407)"),
            SafetyEvidence("simulation/remote_id.py", "module",
                           "ASTM F3411 Remote ID 실시간 식별·방송"),
        ),
    ),
)

# 시스템 전반(계층 횡단) 근거 — 어느 한 계층이 아닌 5계층 *결합* 의 안전을 입증.
CROSS_CUTTING_EVIDENCE: tuple[SafetyEvidence, ...] = (
    SafetyEvidence("simulation/safety_net_invariant.py", "module",
                   "계층 우선순위 단조성 불변식 유한 모델 검사 (Phase 441)"),
    SafetyEvidence("specs/SafetyNetPriority.tla", "spec",
                   "5계층 우선순위 TLA+ 형식 명세"),
    SafetyEvidence("docs/SAFETY_NET_TLA_SPEC.md", "doc",
                   "TLA+ 명세 해설"),
    SafetyEvidence("scripts/ablation_study.py", "script",
                   "계층 제거(ablation) 경험적 효과 측정 (Phase 286)"),
    SafetyEvidence("docs/certification/RTM_5LAYER_COVERAGE.md", "doc",
                   "5계층 요구사항 추적 매트릭스 (Phase 306)"),
)


# 로드 시점 무결성 게이트 — 계층 식별자 중복·순서를 임포트 시 즉시 차단.
_LAYER_IDS = [layer.layer_id for layer in SAFETY_LAYERS]
assert len(_LAYER_IDS) == len(set(_LAYER_IDS)), "duplicate layer_id in SAFETY_LAYERS"
assert sorted(_LAYER_IDS, key=lambda lid: int(lid[1:])) == _LAYER_IDS, (
    "SAFETY_LAYERS must be in numeric layer_id order"
)


@dataclass(frozen=True)
class WhitepaperReport:
    """5계층 안전 기준 백서의 입증 현황 요약(불변)."""

    total_layers: int
    substantiated: int
    partial: int
    unsubstantiated: int
    total_evidence: int
    existing_evidence: int
    cross_cutting_total: int
    cross_cutting_existing: int
    by_layer: Mapping[str, str]  # layer_id -> status, read-only

    def __post_init__(self) -> None:
        if not isinstance(self.by_layer, MappingProxyType):
            object.__setattr__(self, "by_layer", MappingProxyType(dict(self.by_layer)))
        counts = (
            self.total_layers, self.substantiated, self.partial, self.unsubstantiated,
            self.total_evidence, self.existing_evidence,
            self.cross_cutting_total, self.cross_cutting_existing,
        )
        if min(counts) < 0:
            raise ValueError("counts must be non-negative")
        if self.substantiated + self.partial + self.unsubstantiated != self.total_layers:
            raise ValueError(
                f"substantiated ({self.substantiated}) + partial ({self.partial}) + "
                f"unsubstantiated ({self.unsubstantiated}) != total_layers "
                f"({self.total_layers})"
            )
        if self.existing_evidence > self.total_evidence:
            raise ValueError("existing_evidence must not exceed total_evidence")
        if self.cross_cutting_existing > self.cross_cutting_total:
            raise ValueError("cross_cutting_existing must not exceed cross_cutting_total")
        if self.total_layers > 0 and len(self.by_layer) != self.total_layers:
            raise ValueError(
                f"by_layer size ({len(self.by_layer)}) != total_layers "
                f"({self.total_layers})"
            )
        # 정직성 결속: by_layer 값은 반드시 STATUSES 중 하나여야 한다 — 소비자가
        # 직접 보는 1순위 출력이므로 임의 문자열의 침투를 구조적으로 금지한다.
        for layer_id, status in self.by_layer.items():
            if status not in STATUSES:
                raise ValueError(
                    f"by_layer[{layer_id!r}] has invalid status {status!r}"
                )

    @property
    def coverage_pct(self) -> float:
        """가중 입증 커버리지 (%) — SUBSTANTIATED 1.0·PARTIAL 0.5."""
        if not self.total_layers:
            return 0.0
        score = (self.substantiated * _STATUS_WEIGHT["SUBSTANTIATED"]
                 + self.partial * _STATUS_WEIGHT["PARTIAL"])
        return 100.0 * score / self.total_layers

    @property
    def evidence_pct(self) -> float:
        """계층 근거 산출물 실재 비율 (%)."""
        if not self.total_evidence:
            return 0.0
        return 100.0 * self.existing_evidence / self.total_evidence

    @property
    def is_fully_substantiated(self) -> bool:
        """모든 계층이 완전 입증되고 횡단 근거도 전부 실재하는가."""
        return (
            self.substantiated == self.total_layers
            and self.cross_cutting_existing == self.cross_cutting_total
        )


def find_layer(layer_id: str) -> SafetyLayer:
    """식별자로 계층을 조회한다. 없으면 KeyError."""
    for layer in SAFETY_LAYERS:
        if layer.layer_id == layer_id:
            return layer
    raise KeyError(f"unknown safety layer: {layer_id!r}")


def layer_status(layer_id: str, root: Path | None = None) -> str:
    """식별자로 계층 입증 상태를 판정한다."""
    return find_layer(layer_id).status(root)


def missing_evidence(root: Path | None = None) -> tuple[SafetyEvidence, ...]:
    """계층·횡단 통틀어 디스크에 부재하는 모든 근거를 인용 순서로 반환한다.

    같은 파일이 여러 계층/횡단에서 인용되면 *인용 단위* 로 중복 반환한다 —
    "어느 계층이 근거를 잃는가" 를 보이려는 의도다(파일 단위 집합이 아님).
    """
    gaps: list[SafetyEvidence] = []
    for layer in SAFETY_LAYERS:
        gaps.extend(layer.missing_evidence(root))
    gaps.extend(ev for ev in CROSS_CUTTING_EVIDENCE if not ev.exists(root))
    return tuple(gaps)


def whitepaper_report(root: Path | None = None) -> WhitepaperReport:
    """백서 입증 현황을 집계한 결정적 리포트를 생성한다."""
    by_layer: dict[str, str] = {}
    total_evidence = 0
    existing_evidence = 0
    substantiated = partial = unsubstantiated = 0
    for layer in SAFETY_LAYERS:
        status = layer.status(root)
        by_layer[layer.layer_id] = status
        if status == "SUBSTANTIATED":
            substantiated += 1
        elif status == "PARTIAL":
            partial += 1
        else:
            unsubstantiated += 1
        total_evidence += len(layer.evidence)
        existing_evidence += len(layer.existing_evidence(root))
    cross_existing = sum(1 for ev in CROSS_CUTTING_EVIDENCE if ev.exists(root))
    return WhitepaperReport(
        total_layers=len(SAFETY_LAYERS),
        substantiated=substantiated,
        partial=partial,
        unsubstantiated=unsubstantiated,
        total_evidence=total_evidence,
        existing_evidence=existing_evidence,
        cross_cutting_total=len(CROSS_CUTTING_EVIDENCE),
        cross_cutting_existing=cross_existing,
        by_layer=MappingProxyType(by_layer),
    )


def case_study_matrix(root: Path | None = None) -> tuple[dict[str, object], ...]:
    """도구 간 교환용 사례 연구 매트릭스를 계층 순서 행으로 반환한다."""
    rows: list[dict[str, object]] = []
    for layer in SAFETY_LAYERS:
        rows.append({
            "layer_id": layer.layer_id,
            "abbrev": layer.abbrev,
            "name": layer.name,
            "rate_hz": layer.rate_hz,
            "decision_scope": layer.decision_scope,
            "status": layer.status(root),
            "evidence_present": len(layer.existing_evidence(root)),
            "evidence_total": len(layer.evidence),
        })
    return tuple(rows)


def _escape_md(text: str) -> str:
    """markdown 표 셀의 파이프를 이스케이프한다."""
    return text.replace("|", "\\|")


def markdown_table(root: Path | None = None) -> str:
    """사례 연구 매트릭스를 markdown 표 문자열로 반환한다."""
    lines = [
        "| 계층 | 약어 | 주기(Hz) | 결정 단위 | 입증 | 근거(실재/전체) |",
        "|---|---|:-:|---|:-:|:-:|",
    ]
    for row in case_study_matrix(root):
        lines.append(
            f"| {row['layer_id']} | {_escape_md(str(row['abbrev']))} | "
            f"{row['rate_hz']} | {_escape_md(str(row['decision_scope']))} | "
            f"{row['status']} | {row['evidence_present']}/{row['evidence_total']} |"
        )
    return "\n".join(lines)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ODYSSEY Phase 464 — 5계층 안전망 사례 연구 백서 골격",
    )
    parser.add_argument("--layers", action="store_true", help="5계층 정의·근거 출력")
    parser.add_argument("--report", action="store_true", help="백서 입증 현황 요약")
    parser.add_argument("--markdown", action="store_true", help="사례 연구 매트릭스(markdown)")
    parser.add_argument("--gaps", action="store_true", help="누락 근거(미실재) 목록")
    args = parser.parse_args(argv)

    if args.layers:
        for layer in SAFETY_LAYERS:
            print(f"{layer.layer_id} {layer.abbrev} ({layer.name}) "
                  f"@ {layer.rate_hz}Hz · {layer.decision_scope}")
            print(f"    역할: {layer.role}")
            for ev in layer.evidence:
                mark = "✓" if ev.exists() else "✗"
                print(f"    [{mark}] ({ev.kind}) {ev.path} — {ev.role}")
        return 0

    if args.markdown:
        print(markdown_table())
        return 0

    if args.gaps:
        gaps = missing_evidence()
        if not gaps:
            print("누락 근거 없음 — 모든 인용 산출물 실재.")
        for ev in gaps:
            print(f"[MISSING] ({ev.kind}) {ev.path} — {ev.role}")
        return 0

    # 기본: --report
    rep = whitepaper_report()
    print("ODYSSEY Phase 464 — 5계층 안전망 사례 연구 백서")
    print(f"  계층 입증: SUBSTANTIATED {rep.substantiated} · PARTIAL {rep.partial} · "
          f"UNSUBSTANTIATED {rep.unsubstantiated} / {rep.total_layers}")
    print(f"  가중 커버리지: {rep.coverage_pct:.1f}%")
    print(f"  계층 근거 실재: {rep.existing_evidence}/{rep.total_evidence} "
          f"({rep.evidence_pct:.1f}%)")
    print(f"  횡단 근거 실재: {rep.cross_cutting_existing}/{rep.cross_cutting_total}")
    print(f"  완전 입증: {'예' if rep.is_fully_substantiated else '아니오'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
