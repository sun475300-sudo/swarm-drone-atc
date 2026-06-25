"""ODYSSEY Phase 456 — EASA 신뢰 가능 AI 설명가능성(Explainability) 적합성 심층 평가.

Phase 451(`easa_ai_conformance`)이 신뢰 가능 AI 6개 빌딩 블록을 한 행씩 *개괄* 했다면,
본 모듈은 그중 **설명가능성(explainability)** 블록 하나만을 *이해관계자(audience)별·
수명주기 단계별* 로 세분화해 결정적으로 재평가한다. 451 의 설명가능성 행 2건(개발용·
운영용)이 모두 ``gap`` 으로 뭉뚱그려졌으나, 실제 리포에는 설명가능성을 *부분적으로* 떠받치는
자산(post-hoc XAI 대리모델·해석 가능 규칙 관제·불변 감사 추적)이 실재한다 — 본 심층 평가는
이를 정직하게 가시화하되, EASA 기준의 *검증된* 설명가능성(의미 적절성·타당성·운영 적시성)은
여전히 갭임을 보수적으로 보고한다.

ODYSSEY Track 🔬 Formal & Research Frontier(451-460) 의 후속 칸으로, 형제 모듈
452(RL 일반화)·453(자문 경계)·454/455(ML 분류·데이터 관리)와 **서로소** 인 *설명가능성*
축을 다룬다.

근거 (권위 있는 출처)
--------------------
- **EASA Concept Paper — "Guidance for Level 1 & 2 machine learning applications"**
  (Issue 02, 2024). 설명가능성을 *개발 단계 설명가능성*(설계자·V&V·인증 근거용)과
  *운영 단계 설명가능성*(최종 사용자·관제사용, 적시·상황 인식)으로 구분하고, 설명 요구
  식별·의미 적절성·타당성 검증을 목표로 제시한다. 본 모듈은 이를 이해관계자 축
  (developer·end_user·regulator)으로 분류한다.
- **EASA Artificial Intelligence Roadmap 2.0** (2023) — 설명가능성을 러닝 어슈어런스·
  안전 위험 완화와 함께 신뢰 구축의 한 기둥으로 둔다.

정직 공시 (CLAUDE.md)
--------------------
1. 본 모듈은 *기능적 자가 평가* 이며 EASA 공식 인증이 아니다. ``anchor`` 토큰(EXP:xx)은
   SDACS 의 해석이며 EASA 문서의 정확한 목표 번호를 복제하지 않는다.
2. ``status`` 3값(``conformant``·``partial``·``gap``)은 보수적으로 매긴다. 대리모델·
   해석 규칙이 *존재* 함과 EASA 기준으로 *검증* 됨은 다르다 — 메커니즘만 있으면 ``partial``,
   EASA 의미 적절성·타당성까지 검증돼야 ``conformant`` 다.
3. ``sdacs_module`` 은 목표를 *실제로* 떠받치는 리포 경로다. ``gap`` 이면 반드시 ``None``,
   그 외엔 반드시 실재 경로를 인용한다(테스트가 디스크 실재를 강제 — 허위 충족 차단).
4. SDACS 의 *진짜* 설명가능성 강점은 ML 설명이 아니라 **안전-결정을 애초에 해석 가능한
   결정적 로직이 내린다** 는 데 있다: 안전-크리티컬 결정은 블랙박스 ML 이 아니라 IF-THEN
   규칙·결정적 디컨플릭션이 내리므로 본질적으로 설명 가능하고, 모든 결정은 불변 감사
   추적으로 사후 추적된다 — 이 두 항목이 본 매트릭스에서 유일한 ``conformant`` 다.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/explainability_conformance.py --matrix      # 전체 매트릭스
    python simulation/explainability_conformance.py --report      # 요약
    python simulation/explainability_conformance.py --audience end_user  # 이해관계자별
    python simulation/explainability_conformance.py --gaps        # 미충족(갭) 목표
    python simulation/explainability_conformance.py --foundational  # 기반(필수) 목표
"""
from __future__ import annotations

import argparse
import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

# 설명가능성 이해관계자 축 (수신자 — 개발자·최종 사용자·규제/인증).
AUDIENCES: tuple[str, ...] = ("developer", "end_user", "regulator")

_AUDIENCE_NAMES: dict[str, str] = {
    "developer": "Developer / V&V (개발·검증 단계 설명)",
    "end_user": "End user / operator (운영 단계 설명)",
    "regulator": "Regulator / certification (인증 근거 설명)",
}

# 적합성 상태 (3값). conformant=완전, partial=부분(메커니즘만), gap=미충족.
EXPL_STATUSES: tuple[str, ...] = ("conformant", "partial", "gap")

# 가중 점수: 완전 1.0, 부분 0.5, 미충족 0.0.
_STATUS_WEIGHT: dict[str, float] = {"conformant": 1.0, "partial": 0.5, "gap": 0.0}


@dataclass(frozen=True)
class ExplObjective:
    """단일 설명가능성 목표와 SDACS 대응의 정의."""

    objective_id: str           # 안정 식별자 (예: 'feature_importance_attribution')
    name: str                   # 목표 명칭
    audience: str               # 설명 수신자 (developer·end_user·regulator)
    anchor: str                 # EASA 설명가능성 목표 참조 토큰 (SDACS 해석, 예: 'EXP:OP')
    foundational: bool          # 어떤 설명가능성 인증에도 필수인 기반 목표 여부
    status: str                 # conformant·partial·gap
    sdacs_module: str | None    # 떠받치는 경로 (gap 이면 None)
    summary: str                # 한 줄 설명

    def __post_init__(self) -> None:
        # snake_case 식별자 강제 — 공백뿐 아니라 탭·개행 등 모든 비정규 문자를 차단.
        if not re.fullmatch(r"[a-z][a-z0-9_]*", self.objective_id):
            raise ValueError(
                "objective_id must be non-empty snake_case "
                "(lowercase letter, then letters/digits/underscores)"
            )
        if not self.name or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        if not self.anchor or not self.anchor.strip():
            raise ValueError("anchor must be a non-empty string")
        if not self.summary or not self.summary.strip():
            raise ValueError("summary must be a non-empty string")
        if self.audience not in AUDIENCES:
            raise ValueError(
                f"audience must be one of {AUDIENCES}, got {self.audience!r}"
            )
        if not isinstance(self.foundational, bool):
            raise TypeError(
                f"foundational must be bool, got {type(self.foundational).__name__}"
            )
        if self.status not in EXPL_STATUSES:
            raise ValueError(
                f"status must be one of {EXPL_STATUSES}, got {self.status!r}"
            )
        # 정직성 결속: gap ⟺ 근거 경로 없음. 충족/부분은 반드시 실재 경로 인용.
        if self.status == "gap":
            if self.sdacs_module is not None:
                raise ValueError("a gap objective must not cite an sdacs_module")
        else:
            if self.sdacs_module is None or not self.sdacs_module.strip():
                raise ValueError(
                    f"status {self.status!r} must cite a non-empty sdacs_module"
                )

    @property
    def is_gap(self) -> bool:
        """미충족(갭) 여부."""
        return self.status == "gap"

    @property
    def weight(self) -> float:
        """가중 점수 기여 (conformant 1.0·partial 0.5·gap 0.0)."""
        return _STATUS_WEIGHT[self.status]


# 설명가능성 목표 카탈로그 ↔ SDACS 자산 매핑 (정본).
# sdacs_module 경로는 리포에 실재하는 모듈/산출물 — 미대응(gap)은 None.
# 메커니즘 존재만으로는 partial, EASA 의미 적절성·타당성 검증까지여야 conformant.
EXPL_OBJECTIVES: tuple[ExplObjective, ...] = (
    # --- 설명 요구 식별 (수명주기 진입) -------------------------------------
    ExplObjective(
        "explainability_needs_identification",
        "Explainability needs identification per stakeholder",
        "regulator", "EXP:ND-01", True,
        "gap", None,
        "이해관계자별 설명 요구(무엇을·언제·왜)를 식별한 형식 분석 산출물 없음 (갭)",
    ),
    ExplObjective(
        "stakeholder_audience_mapping",
        "Stakeholder / audience mapping for explanations",
        "regulator", "EXP:ND-02", False,
        "gap", None,
        "설명 수신자별 적정 설명 형식·상세도 매핑 부재 (갭)",
    ),
    # --- 개발 단계 설명가능성 (개발자·V&V) ----------------------------------
    ExplObjective(
        "ml_blackbox_characterization",
        "Black-box ML constituent characterisation",
        "developer", "EXP:DEV-01", False,
        "partial", "src/rl/ppo_collision.py",
        "RL/GNN/Transformer 가 블랙박스임을 특성화 — 대리 설명은 있으나 모델 내재 해석은 부분",
    ),
    ExplObjective(
        "feature_importance_attribution",
        "Feature importance attribution (SHAP-like)",
        "developer", "EXP:DEV-02", False,
        "partial", "simulation/explainable_ai.py",
        "SHAP 류 특성 중요도 메커니즘 존재 — EASA 의미 적절성 검증은 미수행이라 부분",
    ),
    ExplObjective(
        "local_surrogate_explanation",
        "Local surrogate explanation (LIME-like)",
        "developer", "EXP:DEV-03", False,
        "partial", "simulation/explainable_ai.py",
        "LIME 류 로컬 대리모델 설명 존재 — 충실도(fidelity) 정량 검증 미수행이라 부분",
    ),
    ExplObjective(
        "counterfactual_explanation",
        "Counterfactual / what-if explanation",
        "developer", "EXP:DEV-04", False,
        "partial", "simulation/explainable_ai.py",
        "반사실 설명 메커니즘 존재 — 운영 파이프라인 통합·검증 미수행이라 부분",
    ),
    # --- 본질적 해석가능성 (SDACS 의 진짜 강점) -----------------------------
    ExplObjective(
        "interpretable_decision_logic",
        "Inherently interpretable safety decision logic",
        "developer", "EXP:IN-01", True,
        "conformant", "simulation/decision_tree_atc.py",
        "안전-크리티컬 결정을 블랙박스 ML 이 아닌 IF-THEN 규칙·결정적 디컨플릭션이 내림 — 본질적 설명 가능",
    ),
    ExplObjective(
        "deterministic_resolution_traceability",
        "Deterministic conflict-resolution traceability",
        "developer", "EXP:IN-02", False,
        "partial", "simulation/path_deconflict.py",
        "결정적 디컨플릭션의 해결 근거가 코드 추적 가능 — 사용자용 근거 직렬화는 부분",
    ),
    # --- 운영 단계 설명가능성 (관제사·최종 사용자) --------------------------
    ExplObjective(
        "operational_explanation_interface",
        "Operational explanation interface for operators",
        "end_user", "EXP:OP-01", True,
        "gap", None,
        "관제사에게 실시간 결정 근거를 제시하는 운영용 설명 인터페이스 미통합 (갭)",
    ),
    ExplObjective(
        "explanation_timeliness",
        "Timely / situation-aware explanation delivery",
        "end_user", "EXP:OP-02", False,
        "gap", None,
        "결정 시점에 맞춘 적시·상황 인식 설명 전달 메커니즘 없음 (갭)",
    ),
    # --- 인증 근거·검증 (규제) ----------------------------------------------
    ExplObjective(
        "decision_traceability_audit",
        "Immutable decision traceability for audit",
        "regulator", "EXP:CE-01", True,
        "conformant", "simulation/audit_trail.py",
        "모든 결정이 불변 해시 체인 감사 추적으로 사후 추적·재구성 가능 — 인증 근거 충족",
    ),
    ExplObjective(
        "semantic_relevance_validation",
        "Semantic relevance validation of explanations",
        "regulator", "EXP:CE-02", True,
        "gap", None,
        "설명이 의미적으로 적절·정확한지 검증한 산출물 없음 (갭)",
    ),
    ExplObjective(
        "explanation_validity_verification",
        "Explanation validity / fidelity verification",
        "regulator", "EXP:CE-03", False,
        "gap", None,
        "대리 설명의 모델 충실도를 정량 검증한 절차 없음 (갭)",
    ),
)


# 로드 시점 무결성 게이트 — 중복 식별자를 임포트 시 즉시 차단(테스트보다 이른 단계).
_CATALOG_IDS = [o.objective_id for o in EXPL_OBJECTIVES]
assert len(_CATALOG_IDS) == len(set(_CATALOG_IDS)), "duplicate objective_id in EXPL_OBJECTIVES"


@dataclass(frozen=True)
class ExplainabilityReport:
    """설명가능성 적합성 자가 평가 요약."""

    total: int
    conformant: int
    partial: int
    gap: int
    foundational_total: int
    foundational_conformant: int
    by_audience: Mapping[str, tuple[int, int, int]]  # audience -> (c, p, g), read-only

    def __post_init__(self) -> None:
        # by_audience 를 항상 읽기 전용 뷰로 동결 — 직접 생성 시에도 내부 변형 차단.
        if not isinstance(self.by_audience, MappingProxyType):
            object.__setattr__(self, "by_audience", MappingProxyType(dict(self.by_audience)))
        if min(self.total, self.conformant, self.partial, self.gap,
               self.foundational_total, self.foundational_conformant) < 0:
            raise ValueError("counts must be non-negative")
        if self.conformant + self.partial + self.gap != self.total:
            raise ValueError(
                f"conformant ({self.conformant}) + partial ({self.partial}) + "
                f"gap ({self.gap}) != total ({self.total})"
            )
        if self.foundational_conformant > self.foundational_total:
            raise ValueError("foundational_conformant cannot exceed foundational_total")
        if self.foundational_total > self.total:
            raise ValueError("foundational_total cannot exceed total")
        # total>0 이면 by_audience 분해가 반드시 존재·전수·합 일치해야 한다.
        # (빈 dict 로 교차검증을 우회해 위조 총계를 통과시키는 구멍을 막는다.)
        if self.total > 0:
            missing = set(AUDIENCES) - set(self.by_audience.keys())
            if missing:
                raise ValueError(f"by_audience missing required audiences: {sorted(missing)}")
            invalid = set(self.by_audience.keys()) - set(AUDIENCES)
            if invalid:
                raise ValueError(f"by_audience contains unknown audiences: {sorted(invalid)}")
            c = sum(v[0] for v in self.by_audience.values())
            p = sum(v[1] for v in self.by_audience.values())
            g = sum(v[2] for v in self.by_audience.values())
            if (c, p, g) != (self.conformant, self.partial, self.gap):
                raise ValueError(
                    f"by_audience sums ({c},{p},{g}) != "
                    f"({self.conformant},{self.partial},{self.gap})"
                )
        elif self.by_audience:
            raise ValueError("by_audience must be empty when total is 0")

    @property
    def weighted_score_pct(self) -> float:
        """가중 적합성 점수 (%) — conformant 1.0·partial 0.5·gap 0.0."""
        if not self.total:
            return 0.0
        score = self.conformant * 1.0 + self.partial * 0.5
        return 100.0 * score / self.total

    @property
    def foundational_conformant_pct(self) -> float:
        """기반(필수) 목표 완전 충족 비율 (%)."""
        if not self.foundational_total:
            return 0.0
        return 100.0 * self.foundational_conformant / self.foundational_total

    @property
    def has_foundational_incomplete(self) -> bool:
        """기반 목표 중 미완전(부분·갭) 항목이 있으면 True."""
        if not self.foundational_total:
            return False
        return self.foundational_conformant < self.foundational_total


def find_objective(objective_id: str) -> ExplObjective:
    """식별자로 목표를 조회한다. 없으면 KeyError."""
    for obj in EXPL_OBJECTIVES:
        if obj.objective_id == objective_id:
            return obj
    raise KeyError(f"unknown explainability objective: {objective_id!r}")


def objectives_by_audience(audience: str) -> tuple[ExplObjective, ...]:
    """이해관계자에 속한 목표를 식별자 정렬로 반환한다."""
    if audience not in AUDIENCES:
        raise ValueError(f"audience must be one of {AUDIENCES}, got {audience!r}")
    return tuple(
        sorted((o for o in EXPL_OBJECTIVES if o.audience == audience),
               key=lambda o: o.objective_id)
    )


def foundational_objectives() -> tuple[ExplObjective, ...]:
    """기반(필수) 목표(foundational=True)를 식별자 정렬로 반환한다."""
    return tuple(
        sorted((o for o in EXPL_OBJECTIVES if o.foundational),
               key=lambda o: o.objective_id)
    )


def gaps() -> tuple[ExplObjective, ...]:
    """미충족(gap) 목표를 식별자 정렬로 반환한다."""
    return tuple(
        sorted((o for o in EXPL_OBJECTIVES if o.is_gap), key=lambda o: o.objective_id)
    )


def explainability_report() -> ExplainabilityReport:
    """전체 설명가능성 적합성 현황을 집계한 결정적 리포트를 생성한다."""
    total = len(EXPL_OBJECTIVES)
    conformant = sum(1 for o in EXPL_OBJECTIVES if o.status == "conformant")
    partial = sum(1 for o in EXPL_OBJECTIVES if o.status == "partial")
    gap = sum(1 for o in EXPL_OBJECTIVES if o.status == "gap")
    foundational = [o for o in EXPL_OBJECTIVES if o.foundational]
    foundational_conformant = sum(1 for o in foundational if o.status == "conformant")
    by_audience: dict[str, tuple[int, int, int]] = {}
    for audience in AUDIENCES:
        members = [o for o in EXPL_OBJECTIVES if o.audience == audience]
        by_audience[audience] = (
            sum(1 for o in members if o.status == "conformant"),
            sum(1 for o in members if o.status == "partial"),
            sum(1 for o in members if o.status == "gap"),
        )
    return ExplainabilityReport(
        total=total,
        conformant=conformant,
        partial=partial,
        gap=gap,
        foundational_total=len(foundational),
        foundational_conformant=foundational_conformant,
        by_audience=MappingProxyType(by_audience),
    )


def explainability_matrix() -> tuple[Mapping[str, object], ...]:
    """도구 간 교환용 매트릭스를 (audience, 식별자) 정렬 행으로 반환한다."""
    ordered = sorted(
        EXPL_OBJECTIVES,
        key=lambda o: (AUDIENCES.index(o.audience), o.objective_id),
    )
    return tuple(
        MappingProxyType({
            "objective_id": o.objective_id,
            "name": o.name,
            "audience": o.audience,
            "anchor": o.anchor,
            "foundational": o.foundational,
            "status": o.status,
            "sdacs_module": o.sdacs_module,
            "summary": o.summary,
        })
        for o in ordered
    )


_STATUS_MARK: dict[str, str] = {"conformant": "✓", "partial": "◐", "gap": "✗(갭)"}


def _format_matrix() -> str:
    lines = ["EASA AI 설명가능성(Explainability) 적합성 매트릭스", ""]
    for row in explainability_matrix():
        mark = _STATUS_MARK[str(row["status"])]
        kind = "기반" if row["foundational"] else "권장"
        module = row["sdacs_module"] or "—"
        lines.append(
            f"[{str(row['audience']):10}] {mark:5} {kind} {row['anchor']} {row['name']}"
        )
        lines.append(f"      → {module}")
    return "\n".join(lines)


def _format_report() -> str:
    r = explainability_report()
    lines = [
        "EASA AI 설명가능성 적합성 자가 평가 요약 (Phase 451 설명가능성 블록 심층)",
        "",
        f"가중 점수   : {r.weighted_score_pct:.0f}% "
        f"(충족 {r.conformant} · 부분 {r.partial} · 갭 {r.gap} / 총 {r.total})",
        f"기반 목표   : {r.foundational_conformant}/{r.foundational_total} 완전 충족 "
        f"({r.foundational_conformant_pct:.0f}%) "
        f"{'— 기반 미완전 있음' if r.has_foundational_incomplete else '— 기반 전부 충족'}",
        "",
        "이해관계자별 (충족/부분/갭):",
    ]
    for audience in AUDIENCES:
        c, p, g = r.by_audience[audience]
        lines.append(f"  {_AUDIENCE_NAMES[audience]:42}: {c}/{p}/{g}")
    lines.append("")
    lines.append(
        "정직 공시: SDACS 의 ML 설명은 연구 수준(대리모델 존재·검증 미완)이다. 그러나"
    )
    lines.append(
        "  안전-결정은 해석 가능한 결정적 로직이 내리고 모든 결정은 감사 추적되므로,"
    )
    lines.append(
        "  설명가능성의 핵심(안전-크리티컬 결정의 추적·해석)은 ML 이 아닌 곳에서 충족된다."
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="EASA AI 설명가능성 적합성 자가 평가 (ODYSSEY Phase 456)"
    )
    parser.add_argument("--matrix", action="store_true", help="전체 적합성 매트릭스 출력")
    parser.add_argument("--report", action="store_true", help="적합성 요약 출력")
    parser.add_argument("--audience", choices=AUDIENCES, help="이해관계자별 목표 출력")
    parser.add_argument("--gaps", action="store_true", help="미충족(갭) 목표 출력")
    parser.add_argument("--foundational", action="store_true", help="기반(필수) 목표 출력")
    args = parser.parse_args(argv)

    if args.matrix:
        print(_format_matrix())
    elif args.report:
        print(_format_report())
    elif args.audience:
        for obj in objectives_by_audience(args.audience):
            print(f"{obj.objective_id} [{obj.status}]: {obj.name} — {obj.summary}")
    elif args.gaps:
        for obj in gaps():
            print(f"[{obj.audience}] {obj.anchor} {obj.name}: {obj.summary}")
    elif args.foundational:
        for obj in foundational_objectives():
            print(f"{_STATUS_MARK[obj.status]} {obj.anchor} {obj.name} → {obj.sdacs_module or '—'}")
    else:
        print(_format_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
