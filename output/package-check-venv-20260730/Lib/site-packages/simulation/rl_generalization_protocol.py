"""ODYSSEY Phase 452 — RL 일반화 평가 프로토콜 적합성 게이트.

Phase 451(`easa_ai_conformance`)이 SDACS 의 ML 자산을 EASA 축으로 평가하며 *핵심 연구
갭* 으로 지목한 항목이 ``learning_process_verification`` — "미학습 시나리오 전이(일반화)
검증 프로토콜 없음" 이었다. 본 모듈은 그 갭을 정면으로 다룬다: 강화학습 충돌 회피 정책
(`src/rl/ppo_collision.py`)에 대한 *신뢰할 수 있는 일반화 주장* 이 성립하려면 평가 프로토콜이
무엇을 갖춰야 하는가를 결정적 요건 카탈로그로 명문화하고, 각 요건이 리포 내 *실재 증거
산출물* 로 떠받쳐지는가를 감사하여 종합 판정(ESTABLISHED·PARTIAL·NOT_ESTABLISHED)을 내린다.

ODYSSEY Track 🔬 Formal & Research Frontier(451-460)의 두 번째 모듈이다. 451 이 *무엇이
빠졌는가* 를 6개 EASA 블록으로 폭넓게 진단했다면, 452 는 그중 가장 핵심인 *일반화 검증*
한 축을 깊게 파고들어 "어떤 증거가 있어야 일반화를 주장할 자격이 생기는가" 를 답한다.

근거 (학술 출처)
----------------
- **Cobbe et al., "Quantifying Generalization in Reinforcement Learning"** (ICML 2019) —
  학습/평가 환경 분리, 보류(held-out) 레벨 평가가 RL 일반화 측정의 전제임을 정립.
- **Kirk et al., "A Survey of Generalisation in Deep Reinforcement Learning"** (JAIR 2023) —
  분포 변화(distribution shift)·평가 프로토콜·통계적 엄밀성·베이스라인 기준화의
  분류 체계를 본 모듈의 *단계(stage)* 축에 차용한다.
- **Henderson et al., "Deep RL that Matters"** (AAAI 2018) — 다중 시드·유의성·음성 결과
  공시(reproducibility & reporting integrity)의 필요성을 본 모듈의 요건에 반영.

정직 공시 (CLAUDE.md)
--------------------
1. 본 모듈은 *프로토콜 준비도* 의 자가 감사이며 일반화 자체를 측정하지 않는다 — 실제
   일반화 수치는 GPU 학습·평가 실행(사용자 환경)에 의존한다. 본 게이트는 "그 실험을
   *신뢰할 수 있게* 돌릴 골격이 갖춰졌는가" 만 결정적으로 판정한다.
2. ``status`` 는 3값(``satisfied``·``partial``·``absent``)이다. SDACS 의 RL 은 연구
   수준이므로 본 평가는 보수적이다 — 충족 주장보다 *미충족(absent)의 가시화* 가 가치다.
3. 정직성 결속: ``status`` 가 ``absent`` 이면 ``evidence`` 는 반드시 ``None``, 그 외
   (``satisfied``/``partial``)면 반드시 디스크 실재 경로를 인용한다(테스트가 강제).
   근거 없는 충족 주장을 구조적으로 금지한다.
4. SDACS 의 *진짜 강점* 은 일반화 증명이 아니라 **일반화 실패의 무해화** 다: RL 은 항상
   자문이고 안전-결정권은 결정적 안전망이 보유하므로, RL 이 미학습 상황에서 틀려도
   안전 위반으로 이어지지 않는다. 이 불변식(``advisory_only_invariant``)이 본 카탈로그에서
   유일하게 ``satisfied`` 인 요건의 근거이며, 일반화 *증명* 의 부재(다수 ``absent``)와는
   독립적으로 시스템을 안전하게 만든다.

무작위성 0 · 결정적 · 부수효과 0. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/rl_generalization_protocol.py --matrix     # 전체 요건 매트릭스
    python simulation/rl_generalization_protocol.py --report     # 종합 판정 요약
    python simulation/rl_generalization_protocol.py --stage distribution_shift
    python simulation/rl_generalization_protocol.py --gaps       # 미충족(absent) 요건
    python simulation/rl_generalization_protocol.py --critical   # 임계(필수) 요건
"""
from __future__ import annotations

import argparse
import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

# 일반화 평가 프로토콜의 단계 (분류 축, Kirk et al. 2023 분류 차용).
PROTOCOL_STAGES: tuple[str, ...] = (
    "split_protocol",
    "distribution_shift",
    "statistical_rigor",
    "baseline_grounding",
    "reporting_integrity",
)

_STAGE_NAMES: dict[str, str] = {
    "split_protocol": "Split protocol (학습/평가 분리·보류 시나리오)",
    "distribution_shift": "Distribution shift (OOD 조건 평가·리얼리티 갭)",
    "statistical_rigor": "Statistical rigor (다중 시드·유의성·신뢰구간)",
    "baseline_grounding": "Baseline grounding (결정적 베이스라인 대조·자문 불변식)",
    "reporting_integrity": "Reporting integrity (음성 결과 공시·일반화 지표 정의)",
}

# 요건 충족 상태 (3값). satisfied=완전, partial=부분, absent=미충족.
PROTOCOL_STATUSES: tuple[str, ...] = ("satisfied", "partial", "absent")

# 가중 점수: 완전 1.0, 부분 0.5, 미충족 0.0.
_STATUS_WEIGHT: Mapping[str, float] = MappingProxyType(
    {"satisfied": 1.0, "partial": 0.5, "absent": 0.0}
)

# 종합 판정값. 임계 요건 미충족이 하나라도 있으면 일반화 주장 자격 없음.
VERDICTS: tuple[str, ...] = ("ESTABLISHED", "PARTIAL", "NOT_ESTABLISHED")


@dataclass(frozen=True)
class ProtocolRequirement:
    """일반화 평가 프로토콜의 단일 요건과 SDACS 증거의 정의."""

    requirement_id: str          # 안정 식별자 (예: 'disjoint_train_eval_split')
    name: str                    # 요건 명칭
    stage: str                   # 프로토콜 단계
    anchor: str                  # 참조 토큰 (SDACS 해석, 예: 'SP:SPLIT')
    critical: bool               # 일반화 주장의 전제(필수) 요건 여부
    status: str                  # satisfied·partial·absent
    evidence: str | None         # 떠받치는 산출물 경로 (absent 이면 None)
    summary: str                 # 한 줄 설명

    def __post_init__(self) -> None:
        if not self.requirement_id or self.requirement_id != self.requirement_id.strip():
            raise ValueError("requirement_id must be non-empty and unpadded")
        if " " in self.requirement_id:
            raise ValueError("requirement_id must not contain internal spaces (snake_case)")
        # 엄격 snake_case 강제 — 탭·개행 등 내부 비-공백 공백문자도 차단(어드바이저 반영).
        if not re.fullmatch(r"[a-z][a-z0-9_]*", self.requirement_id):
            raise ValueError("requirement_id must be lowercase snake_case (a-z, 0-9, _)")
        if not self.name or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        if not self.anchor or not self.anchor.strip():
            raise ValueError("anchor must be a non-empty string")
        if not self.summary or not self.summary.strip():
            raise ValueError("summary must be a non-empty string")
        if self.stage not in PROTOCOL_STAGES:
            raise ValueError(
                f"stage must be one of {PROTOCOL_STAGES}, got {self.stage!r}"
            )
        if not isinstance(self.critical, bool):
            raise TypeError(
                f"critical must be bool, got {type(self.critical).__name__}"
            )
        if self.status not in PROTOCOL_STATUSES:
            raise ValueError(
                f"status must be one of {PROTOCOL_STATUSES}, got {self.status!r}"
            )
        # 정직성 결속: absent ⟺ 근거 경로 없음. 충족/부분은 반드시 실재 경로 인용.
        if self.status == "absent":
            if self.evidence is not None:
                raise ValueError("an absent requirement must not cite evidence")
        else:
            if self.evidence is None or not self.evidence.strip():
                raise ValueError(
                    f"status {self.status!r} must cite non-empty evidence"
                )

    @property
    def is_absent(self) -> bool:
        """미충족(absent) 여부."""
        return self.status == "absent"

    @property
    def weight(self) -> float:
        """가중 점수 기여 (satisfied 1.0·partial 0.5·absent 0.0)."""
        return _STATUS_WEIGHT[self.status]


# RL 일반화 평가 프로토콜 요건 카탈로그 ↔ SDACS 자산 매핑 (정본).
# evidence 경로는 리포에 실재하는 모듈/산출물 — 미충족(absent)은 None.
# SDACS 의 RL 은 연구 수준이므로 본 매핑은 의도적으로 보수적이다(정직성 > 점수).
PROTOCOL_REQUIREMENTS: tuple[ProtocolRequirement, ...] = (
    # --- split_protocol ------------------------------------------------------
    ProtocolRequirement(
        "disjoint_train_eval_split", "Disjoint train/eval scenario split (no leakage)",
        "split_protocol", "SP:SPLIT", True,
        "absent", None,
        "학습/평가 시나리오의 서로소 분할 기록 없음 — 일반화 측정의 1차 전제 미충족 (갭)",
    ),
    ProtocolRequirement(
        "held_out_scenario_registry", "Held-out scenario registry",
        "split_protocol", "SP:HOLDOUT", True,
        "partial", "simulation/standard_scenarios.py",
        "표준 시나리오 스위트(SDACS-SBS-10) 존재 — RL 학습 미노출 보류셋으로 *지정* 은 부분",
    ),
    # --- distribution_shift --------------------------------------------------
    ProtocolRequirement(
        "ood_condition_coverage", "Out-of-distribution condition coverage",
        "distribution_shift", "DS:OOD", True,
        "partial", "src/training/domain_rand.py",
        "도메인 무작위화로 학습 분포 확장(ADR 곡선) — DR 외피 *바깥* OOD 평가 기록은 부분",
    ),
    ProtocolRequirement(
        "reality_gap_quantification", "Sim-to-real reality gap quantification",
        "distribution_shift", "DS:GAP", False,
        "absent", None,
        "시뮬↔실기 리얼리티 갭 측정 산출물 없음(엣지 추론·실 비행 의존) (갭)",
    ),
    # --- statistical_rigor ---------------------------------------------------
    ProtocolRequirement(
        "multi_seed_evaluation", "Multi-seed independent evaluation",
        "statistical_rigor", "SR:SEED", True,
        "partial", "simulation/uncertainty.py",
        "Monte Carlo 신뢰구간 하니스 존재(시드 재현) — RL 정책 평가에 *적용* 은 부분",
    ),
    ProtocolRequirement(
        "significance_testing", "Statistical significance / power analysis",
        "statistical_rigor", "SR:SIG", False,
        "partial", "simulation/power_analysis.py",
        "충돌 해결률 차이 검정력 분석 도구 존재 — RL vs 베이스라인 비교에 적용은 부분",
    ),
    ProtocolRequirement(
        "confidence_interval_reporting", "Confidence interval reporting",
        "statistical_rigor", "SR:CI", False,
        "partial", "simulation/uncertainty.py",
        "MC 신뢰구간 자동 리포트 존재 — 일반화 지표의 CI 보고 결속은 부분",
    ),
    # --- baseline_grounding --------------------------------------------------
    ProtocolRequirement(
        "deterministic_baseline_comparison", "Head-to-head vs deterministic baseline",
        "baseline_grounding", "BG:BASE", True,
        "partial", "simulation/path_deconflict.py",
        "결정적 APF+CBS 베이스라인이 정본 운영계로 실재 — 동일 시나리오 정면 대조 기록은 부분",
    ),
    ProtocolRequirement(
        "advisory_only_invariant", "RL is advisory; safety net retains authority",
        "baseline_grounding", "BG:ADV", True,
        "satisfied", "simulation/emergency_protocol.py",
        "5계층 안전망이 안전-결정권 보유 — RL 일반화 실패가 안전 위반으로 전이 불가 (강점)",
    ),
    # --- reporting_integrity -------------------------------------------------
    ProtocolRequirement(
        "generalization_metric_definition", "Defined deterministic generalization metric",
        "reporting_integrity", "RI:METRIC", True,
        "absent", None,
        "보류셋 대비 성능 유지율 등 일반화 지표의 결정적 정의 없음 — 측정 대상 미정의 (갭)",
    ),
    ProtocolRequirement(
        "negative_result_disclosure", "Negative-result disclosure protocol",
        "reporting_integrity", "RI:NEG", False,
        "absent", None,
        "RL 이 베이스라인에 미달할 때의 음성 결과 공시 기록 없음(평가 미실행) (갭)",
    ),
)


# 로드 시점 무결성 게이트 — 중복 식별자를 임포트 시 즉시 차단(테스트보다 이른 단계).
_CATALOG_IDS = [r.requirement_id for r in PROTOCOL_REQUIREMENTS]
# `assert` 는 `python -O` 에서 비활성화되므로 명시적 raise 로 집행한다.
if len(_CATALOG_IDS) != len(set(_CATALOG_IDS)):
    raise RuntimeError("duplicate requirement_id in PROTOCOL_REQUIREMENTS")


@dataclass(frozen=True)
class ProtocolReport:
    """RL 일반화 평가 프로토콜 적합성 종합 리포트."""

    total: int
    satisfied: int
    partial: int
    absent: int
    critical_total: int
    critical_satisfied: int
    critical_unmet: int  # 임계 요건 중 absent 개수 (일반화 주장 자격 차단 사유)
    by_stage: Mapping[str, tuple[int, int, int]]  # stage -> (satisfied, partial, absent)

    def __post_init__(self) -> None:
        if not isinstance(self.by_stage, MappingProxyType):
            object.__setattr__(self, "by_stage", MappingProxyType(dict(self.by_stage)))
        if min(self.total, self.satisfied, self.partial, self.absent,
               self.critical_total, self.critical_satisfied, self.critical_unmet) < 0:
            raise ValueError("counts must be non-negative")
        if self.satisfied + self.partial + self.absent != self.total:
            raise ValueError(
                f"satisfied ({self.satisfied}) + partial ({self.partial}) + "
                f"absent ({self.absent}) != total ({self.total})"
            )
        if self.critical_satisfied > self.critical_total:
            raise ValueError("critical_satisfied cannot exceed critical_total")
        if self.critical_unmet > self.critical_total:
            raise ValueError("critical_unmet cannot exceed critical_total")
        # 임계 회계 일관성 — 완전 충족 + 미충족이 임계 총계를 넘을 수 없다(어드바이저 HIGH 반영).
        if self.critical_satisfied + self.critical_unmet > self.critical_total:
            raise ValueError(
                "critical_satisfied + critical_unmet cannot exceed critical_total"
            )
        if self.critical_total > self.total:
            raise ValueError("critical_total cannot exceed total")
        if self.by_stage:
            invalid = set(self.by_stage.keys()) - set(PROTOCOL_STAGES)
            if invalid:
                raise ValueError(f"by_stage contains unknown stages: {sorted(invalid)}")
            s = sum(v[0] for v in self.by_stage.values())
            p = sum(v[1] for v in self.by_stage.values())
            a = sum(v[2] for v in self.by_stage.values())
            if (s, p, a) != (self.satisfied, self.partial, self.absent):
                raise ValueError(
                    f"by_stage sums ({s},{p},{a}) != "
                    f"({self.satisfied},{self.partial},{self.absent})"
                )

    @property
    def weighted_score_pct(self) -> float:
        """가중 적합성 점수 (%) — satisfied 1.0·partial 0.5·absent 0.0."""
        if not self.total:
            return 0.0
        score = self.satisfied * 1.0 + self.partial * 0.5
        return 100.0 * score / self.total

    @property
    def verdict(self) -> str:
        """종합 판정.

        임계 요건이 하나라도 미충족(absent)이면 ``NOT_ESTABLISHED`` — 일반화를 주장할
        자격이 없다(전제 미성립). 모든 요건이 완전 충족이면 ``ESTABLISHED``. 그 외(임계는
        전부 충족됐으나 부분/비임계 미충족이 남음)는 ``PARTIAL``.

        가중 점수가 높아도 임계 미충족이면 NOT_ESTABLISHED — 점수가 판정을 앞당기지 않는다.
        """
        if self.critical_unmet > 0:
            return "NOT_ESTABLISHED"
        if self.satisfied == self.total:
            return "ESTABLISHED"
        return "PARTIAL"


def find_requirement(requirement_id: str) -> ProtocolRequirement:
    """식별자로 요건을 조회한다. 없으면 KeyError."""
    for req in PROTOCOL_REQUIREMENTS:
        if req.requirement_id == requirement_id:
            return req
    raise KeyError(f"unknown protocol requirement: {requirement_id!r}")


def requirements_by_stage(stage: str) -> tuple[ProtocolRequirement, ...]:
    """프로토콜 단계에 속한 요건을 식별자 정렬로 반환한다."""
    if stage not in PROTOCOL_STAGES:
        raise ValueError(f"stage must be one of {PROTOCOL_STAGES}, got {stage!r}")
    return tuple(
        sorted((r for r in PROTOCOL_REQUIREMENTS if r.stage == stage),
               key=lambda r: r.requirement_id)
    )


def critical_requirements() -> tuple[ProtocolRequirement, ...]:
    """임계(필수) 요건(critical=True)을 식별자 정렬로 반환한다."""
    return tuple(
        sorted((r for r in PROTOCOL_REQUIREMENTS if r.critical),
               key=lambda r: r.requirement_id)
    )


def gaps() -> tuple[ProtocolRequirement, ...]:
    """미충족(absent) 요건을 식별자 정렬로 반환한다."""
    return tuple(
        sorted((r for r in PROTOCOL_REQUIREMENTS if r.is_absent),
               key=lambda r: r.requirement_id)
    )


def requirements_by_status(status: str) -> tuple[ProtocolRequirement, ...]:
    """충족 상태별 요건을 식별자 정렬로 반환한다."""
    if status not in PROTOCOL_STATUSES:
        raise ValueError(f"status must be one of {PROTOCOL_STATUSES}, got {status!r}")
    return tuple(
        sorted((r for r in PROTOCOL_REQUIREMENTS if r.status == status),
               key=lambda r: r.requirement_id)
    )


def protocol_report() -> ProtocolReport:
    """전체 프로토콜 적합성 현황을 집계한 결정적 리포트를 생성한다."""
    total = len(PROTOCOL_REQUIREMENTS)
    satisfied = sum(1 for r in PROTOCOL_REQUIREMENTS if r.status == "satisfied")
    partial = sum(1 for r in PROTOCOL_REQUIREMENTS if r.status == "partial")
    absent = sum(1 for r in PROTOCOL_REQUIREMENTS if r.status == "absent")
    critical = [r for r in PROTOCOL_REQUIREMENTS if r.critical]
    critical_satisfied = sum(1 for r in critical if r.status == "satisfied")
    critical_unmet = sum(1 for r in critical if r.status == "absent")
    by_stage: dict[str, tuple[int, int, int]] = {}
    for stage in PROTOCOL_STAGES:
        members = [r for r in PROTOCOL_REQUIREMENTS if r.stage == stage]
        by_stage[stage] = (
            sum(1 for r in members if r.status == "satisfied"),
            sum(1 for r in members if r.status == "partial"),
            sum(1 for r in members if r.status == "absent"),
        )
    return ProtocolReport(
        total=total,
        satisfied=satisfied,
        partial=partial,
        absent=absent,
        critical_total=len(critical),
        critical_satisfied=critical_satisfied,
        critical_unmet=critical_unmet,
        by_stage=MappingProxyType(by_stage),
    )


def protocol_matrix() -> tuple[Mapping[str, object], ...]:
    """도구 간 교환용 프로토콜 매트릭스를 (단계, 식별자) 정렬 행으로 반환한다."""
    ordered = sorted(
        PROTOCOL_REQUIREMENTS,
        key=lambda r: (PROTOCOL_STAGES.index(r.stage), r.requirement_id),
    )
    return tuple(
        MappingProxyType({
            "requirement_id": r.requirement_id,
            "name": r.name,
            "stage": r.stage,
            "anchor": r.anchor,
            "critical": r.critical,
            "status": r.status,
            "evidence": r.evidence,
            "summary": r.summary,
        })
        for r in ordered
    )


_STATUS_MARK: dict[str, str] = {"satisfied": "✓", "partial": "◐", "absent": "✗(갭)"}


def _format_matrix() -> str:
    lines = ["RL 일반화 평가 프로토콜 적합성 매트릭스", ""]
    for row in protocol_matrix():
        mark = _STATUS_MARK[str(row["status"])]
        kind = "임계" if row["critical"] else "권장"
        evidence = row["evidence"] or "—"
        lines.append(
            f"[{row['stage']:20}] {mark:5} {kind} {row['anchor']} {row['name']}"
        )
        lines.append(f"      → {evidence}")
    return "\n".join(lines)


def _format_report() -> str:
    r = protocol_report()
    lines = [
        "RL 일반화 평가 프로토콜 적합성 종합 판정",
        "",
        f"판정       : {r.verdict}",
        f"가중 점수   : {r.weighted_score_pct:.0f}% "
        f"(충족 {r.satisfied} · 부분 {r.partial} · 갭 {r.absent} / 총 {r.total})",
        f"임계 요건   : {r.critical_satisfied}/{r.critical_total} 완전 충족 · "
        f"미충족 {r.critical_unmet}건"
        f"{' (일반화 주장 자격 없음)' if r.critical_unmet else ''}",
        "",
        "단계별 (충족/부분/갭):",
    ]
    for stage in PROTOCOL_STAGES:
        s, p, a = r.by_stage[stage]
        lines.append(f"  {_STAGE_NAMES[stage]:44}: {s}/{p}/{a}")
    lines.append("")
    lines.append(
        "정직 공시: 본 게이트는 *일반화 실험을 신뢰성 있게 돌릴 골격* 의 준비도만 판정하며"
    )
    lines.append(
        "  일반화 자체를 측정하지 않는다. 임계 미충족이 남아 있어도 안전은 RL 이 아닌"
    )
    lines.append(
        "  결정적 안전망이 보장한다(RL 자문 불변식) — 일반화 실패는 무해하다."
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="RL 일반화 평가 프로토콜 적합성 게이트 (ODYSSEY Phase 452)"
    )
    parser.add_argument("--matrix", action="store_true", help="전체 요건 매트릭스 출력")
    parser.add_argument("--report", action="store_true", help="종합 판정 요약 출력")
    parser.add_argument("--stage", choices=PROTOCOL_STAGES, help="단계별 요건 출력")
    parser.add_argument("--gaps", action="store_true", help="미충족(갭) 요건 출력")
    parser.add_argument("--critical", action="store_true", help="임계(필수) 요건 출력")
    args = parser.parse_args(argv)

    if args.matrix:
        print(_format_matrix())
    elif args.report:
        print(_format_report())
    elif args.stage:
        for req in requirements_by_stage(args.stage):
            print(f"{req.requirement_id} [{req.status}]: {req.name} — {req.summary}")
    elif args.gaps:
        for req in gaps():
            print(f"[{req.stage}] {req.anchor} {req.name}: {req.summary}")
    elif args.critical:
        for req in critical_requirements():
            print(f"{_STATUS_MARK[req.status]} {req.anchor} {req.name} → {req.evidence or '—'}")
    else:
        print(_format_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
