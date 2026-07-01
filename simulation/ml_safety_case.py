"""ODYSSEY Phase 459 — EASA ML 안전 사례(Safety Case) 적합성 게이트.

SDACS 의 *학습 기반(ML)* 구성요소가 **수용 가능하게 안전(acceptably safe)**하다는 구조화된
논증(structured argument) — 즉 *안전 사례(safety case)* — 를 평가하는 적합성 매트릭스다.
Phase 451(`easa_ai_conformance`)이 신뢰 가능 AI 6개 블록을 개괄하며 안전 위험 완화를
한 행으로 조망했으나, 그 한 행으로는 안전 사례 구조의 세부 축 — 위험 식별·위험 분류·
안전 요구 할당·보증 수준 할당·잔여 위험 수용 — 이 각각 어디에 있고 어디가 비어 있는지
보이지 않는다. 본 모듈은 형제 모듈 452(RL 일반화)·453(자문 경계)·456(설명가능성)·
457(운영 모니터링)·458(V&V)과 **서로소** 인 *안전 사례 방법론* 축을 다룬다: SDACS 가
ML 구성요소 사용이 "수용 가능하게 안전하다"고 말할 수 있으려면 무엇이 있어야 하며,
실제로 무엇이 있는가.

근거 (권위 있는 출처)
--------------------
- **EASA Concept Paper — "Guidance for Level 1 & 2 machine learning applications"**
  (Issue 02, 2024). 학습 어슈어런스 목표 중 *AI safety risk mitigation* 으로 위험 식별,
  위험 분류, 안전 요구 할당, 보증 수준 할당, 잔여 위험 수용 논증을 제시한다.
- **EASA Artificial Intelligence Roadmap 2.0** (2023) — ML 구성요소의 안전 사례를
  기존 항공 안전 평가 프로세스(SAE ARP4754A/ARP4761)에 통합하는 개념을 제시한다.
- **SAE ARP4754A** (기능 위험 평가·안전 요구 할당) / **SAE ARP4761** (안전 평가 방법론:
  FHA, FMEA, FTA) — 전통적 항공 안전 평가 프로세스의 골격으로, ML 안전 사례가 이 위에
  구축돼야 한다. SDACS 는 이 표준의 공식 준수를 주장하지 않으며, 본 매트릭스는 그 정신을
  SDACS 리포에 대응시킨 자체 해석이다.

정직 공시 (CLAUDE.md)
--------------------
1. 본 모듈은 *기능적 자가 평가* 이며 EASA/SAE 공식 적합성 인증이 아니다. 카테고리와
   ``anchor`` 토큰(``SC:*``)은 SDACS 의 해석이며 원문 목표 번호를 복제하지 않는다.
2. ``status`` 는 3값(``conformant``·``partial``·``gap``)이다. SDACS 의 ML 은 *연구 수준*
   이므로 평가는 의도적으로 보수적이다 — "FMEA 가 존재한다"와 "EASA 기준의 ML 특화
   위험 식별이 체계적으로 완료됐다"는 다르다. 메커니즘만 있으면 ``partial``, 형식 문서·
   임계값까지 결속돼야 ``conformant`` 다.
3. ``sdacs_module`` 은 목표를 *실제로* 떠받치는 리포 내 모듈/산출물 경로다. ``status`` 가
   ``gap`` 이면 반드시 ``None``, 그 외(``conformant``/``partial``)면 반드시 실재 경로를
   인용한다 — 근거 없는 충족 주장을 구조적으로 금지한다(테스트가 디스크 실재를 강제).
4. SDACS 의 *진짜 강점* 은 **안전-결정적 판단을 ML 이 전혀 내리지 않는다**는 점이다:
   결정적 디컨플릭션 + 5계층 안전망이 안전-결정권을 보유하고, ML(RL 자문)은 [-1,1]
   클리핑·가중 블렌딩으로 한정된 자문 역할만 한다. 이 "ML 은 자문만, 안전은 결정적"
   아키텍처 선택이 안전 사례를 근본적으로 단순하게 만들며, 본 매트릭스의 ``conformant``
   항목들의 근거다. 반면 *형식 DAL 할당·잔여 위험 문서화* 등 인증 서류 측면은 연구
   수준이라 솔직히 갭이다 — 이 비대칭이 본 매트릭스가 보고하려는 핵심 사실이다.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/ml_safety_case.py --matrix          # 전체 적합성 매트릭스
    python simulation/ml_safety_case.py --report          # 적합성 요약
    python simulation/ml_safety_case.py --category residual_risk  # 카테고리별 목표
    python simulation/ml_safety_case.py --gaps            # 미충족(갭) 목표
    python simulation/ml_safety_case.py --foundational    # 기반(필수) 목표
"""
from __future__ import annotations

import argparse
import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

# EASA ML 안전 사례(Safety Case) 카테고리 (안전 평가 프로세스 순서).
SAFETY_CASE_CATEGORIES: tuple[str, ...] = (
    "hazard_identification",          # 위험 식별 (ML 관련 위험 체계적 식별)
    "risk_classification",            # 위험 분류 (ML 실패 모드의 심각도·빈도 분류)
    "safety_requirement_allocation",  # 안전 요구 할당 (ML 구성요소에 대한 안전 요구 배분)
    "assurance_level",                # 보증 수준 (ML 구성요소의 인증 보증 수준)
    "residual_risk",                  # 잔여 위험 (수용 가능한 잔여 위험의 논증·문서화)
)

_CATEGORY_NAMES: dict[str, str] = {
    "hazard_identification": "Hazard identification (ML 관련 위험 체계적 식별)",
    "risk_classification": "Risk classification (ML 실패 모드 심각도·빈도 분류)",
    "safety_requirement_allocation": "Safety requirement allocation (ML 안전 요구 배분)",
    "assurance_level": "Assurance level (ML 인증 보증 수준 할당)",
    "residual_risk": "Residual risk (수용 가능 잔여 위험 논증·문서화)",
}

# 적합성 상태 (3값). conformant=완전, partial=부분(메커니즘만), gap=미충족.
SC_STATUSES: tuple[str, ...] = ("conformant", "partial", "gap")

# 가중 점수: 완전 1.0, 부분 0.5, 미충족 0.0.
_STATUS_WEIGHT: dict[str, float] = {"conformant": 1.0, "partial": 0.5, "gap": 0.0}


@dataclass(frozen=True)
class SafetyCaseObjective:
    """단일 EASA ML 안전 사례 목표와 SDACS 대응의 정의."""

    objective_id: str           # 안정 식별자 (예: 'fmea_hazard_catalog')
    name: str                   # 목표 명칭
    category: str               # 안전 사례 카테고리
    anchor: str                 # EASA 안전 사례 참조 토큰 (SDACS 해석, 예: 'SC:HI-01')
    foundational: bool          # 안전 인증에 필수인 기반 목표 여부
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
        if self.category not in SAFETY_CASE_CATEGORIES:
            raise ValueError(
                f"category must be one of {SAFETY_CASE_CATEGORIES}, got {self.category!r}"
            )
        if not isinstance(self.foundational, bool):
            raise TypeError(
                f"foundational must be bool, got {type(self.foundational).__name__}"
            )
        if self.status not in SC_STATUSES:
            raise ValueError(
                f"status must be one of {SC_STATUSES}, got {self.status!r}"
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


# EASA ML 안전 사례 목표 카탈로그 ↔ SDACS 자산 매핑 (정본).
# sdacs_module 경로는 리포에 실재하는 모듈/산출물 — 미대응(gap)은 None.
# SDACS 의 강점은 "ML 은 자문만, 안전은 결정적" 아키텍처, 갭은 형식 DAL 할당·잔여 위험
# 문서화 등 인증 서류 측면이다(정직성 > 점수).
SAFETY_CASE_OBJECTIVES: tuple[SafetyCaseObjective, ...] = (
    # --- hazard_identification ---------------------------------------------------
    SafetyCaseObjective(
        "fmea_hazard_catalog",
        "FMEA-based hazard catalog for ML-related failures",
        "hazard_identification", "SC:HI-01", True,
        "partial", "simulation/hitl_report_generator.py",
        "FMEA 기반 고장 모드·영향 분석 존재 — ML 정책 특유 위험(자문 포화·OOD 입력 등)의 "
        "체계적 식별은 부분",
    ),
    SafetyCaseObjective(
        "ml_failure_mode_analysis",
        "ML-specific failure mode systematic analysis",
        "hazard_identification", "SC:HI-02", True,
        "gap", None,
        "ML(RL) 정책 특유 고장 모드(보상 해킹·분포 이탈·적대적 입력 등)의 체계적 분석 없음 (갭)",
    ),
    SafetyCaseObjective(
        "operational_hazard_monitoring",
        "Operational hazard monitoring via safety invariants",
        "hazard_identification", "SC:HI-03", False,
        "partial", "simulation/safety_net_invariant.py",
        "분리거리·우선순위 안전 불변식 감시가 운영 위험 모니터링에 기여 — ML 특화 위험 "
        "이벤트 분류·기록은 부분",
    ),
    # --- risk_classification -----------------------------------------------------
    SafetyCaseObjective(
        "ml_criticality_classification",
        "ML application criticality classification",
        "risk_classification", "SC:RC-01", True,
        "conformant", "simulation/ml_application_classification.py",
        "ML 응용의 임계성(criticality) 분류가 EASA Level 1/2 기준에 따라 수행됨 — "
        "자문 전용 구조로 Level 1(낮은 임계성) 분류 근거 명확",
    ),
    SafetyCaseObjective(
        "failure_severity_assessment",
        "Failure severity assessment via FMEA RPN scoring",
        "risk_classification", "SC:RC-02", False,
        "partial", "simulation/hitl_report_generator.py",
        "FMEA RPN(위험 우선순위 수) 점수 산정으로 고장 심각도·빈도·검출도 평가 — "
        "ML 특화 실패 모드의 심각도 기준 정의는 부분",
    ),
    SafetyCaseObjective(
        "ml_advisory_only_risk_bound",
        "ML advisory-only architecture as inherent risk bound",
        "risk_classification", "SC:RC-03", True,
        "conformant", "src/autonomy/hybrid_collision_avoidance.py",
        "ML 자문은 [-1,1] 클리핑·가중 블렌딩으로 한정되어 단독 제어 불가 — 아키텍처 "
        "자체가 ML 실패 위험을 구조적으로 경계(bounding)하므로 위험이 본질적으로 제한됨",
    ),
    # --- safety_requirement_allocation -------------------------------------------
    SafetyCaseObjective(
        "deterministic_safety_authority",
        "Deterministic controller retains safety-critical authority",
        "safety_requirement_allocation", "SC:SA-01", True,
        "conformant", "src/airspace_control/controller/airspace_controller.py",
        "결정적 관제기(AirspaceController)가 안전-결정권을 보유 — ML 출력과 무관하게 "
        "최종 분리·충돌회피 판단은 결정적 로직이 수행",
    ),
    SafetyCaseObjective(
        "ml_advisory_containment",
        "ML advisory output containment via clipping and weighted blending",
        "safety_requirement_allocation", "SC:SA-02", True,
        "conformant", "src/autonomy/hybrid_collision_avoidance.py",
        "ML 자문 출력은 [-1,1] 클리핑·가중 블렌딩으로 한정 — 결정적 APF 와 합성되어 "
        "ML 단독 제어가 구조적으로 불가능",
    ),
    SafetyCaseObjective(
        "safety_net_independence",
        "Safety net independence from ML constituent",
        "safety_requirement_allocation", "SC:SA-03", True,
        "conformant", "simulation/safety_net_invariant.py",
        "5계층 안전망(분리거리·우선순위·고도 밴드·긴급회피·지오펜스)은 ML 과 독립 작동 — "
        "ML 전면 실패 시에도 안전 보장 유지",
    ),
    # --- assurance_level ---------------------------------------------------------
    SafetyCaseObjective(
        "dal_assignment_documentation",
        "Design Assurance Level (DAL) assignment for ML constituent",
        "assurance_level", "SC:AL-01", True,
        "gap", None,
        "ML 구성요소에 대한 형식 DAL(설계 보증 수준) 할당 문서 없음 — ARP4754A 기준의 "
        "기능 위험 평가에서 ML 구성요소까지 공식 DAL 배정이 필요 (갭)",
    ),
    SafetyCaseObjective(
        "assurance_evidence_traceability",
        "Assurance evidence traceability for ML lifecycle artifacts",
        "assurance_level", "SC:AL-02", False,
        "partial", "simulation/rtm_generator.py",
        "요구사항 추적 매트릭스(RTM) 자동 생성 존재 — ML 학습·검증·배포 산출물까지의 "
        "보증 증거 추적은 부분",
    ),
    # --- residual_risk -----------------------------------------------------------
    SafetyCaseObjective(
        "residual_risk_documentation",
        "Formal residual risk acceptance argumentation",
        "residual_risk", "SC:RR-01", True,
        "gap", None,
        "수용 가능 잔여 위험의 형식 논증 문서(safety case argument) 없음 — 잔여 위험이 "
        "ALARP(합리적으로 달성 가능한 최저)임을 보이는 구조화된 논증이 필요 (갭)",
    ),
    SafetyCaseObjective(
        "safety_margin_quantification",
        "Safety margin quantification via collision prediction",
        "residual_risk", "SC:RR-02", False,
        "partial", "simulation/collision_predictor.py",
        "충돌 예측 모듈이 예측 충돌 시간·거리 기반 안전 여유(safety margin)를 정량화 — "
        "전체 잔여 위험 대비 안전 여유 충분성 논증은 부분",
    ),
    SafetyCaseObjective(
        "continuous_risk_monitoring",
        "Continuous operational risk monitoring metrics",
        "residual_risk", "SC:RR-03", False,
        "partial", "src/monitoring/metrics.py",
        "운영 지표 수집 인프라(충돌률·분리 위반·안전망 발동 등) 존재 — ML 위험 지표와의 "
        "체계적 연계 및 위험 추세 경보는 부분",
    ),
    SafetyCaseObjective(
        "worst_case_performance_bound",
        "Worst-case performance bounding via Monte Carlo simulation",
        "residual_risk", "SC:RR-04", False,
        "partial", "simulation/monte_carlo.py",
        "Monte Carlo 시뮬레이션으로 다양한 시나리오의 최악 성능 경계를 추정 — 형식 "
        "최악 사례 분석(WCPA) 수준의 잔여 위험 경계 논증은 부분",
    ),
)


# 로드 시점 무결성 게이트 — 중복 식별자를 임포트 시 즉시 차단(테스트보다 이른 단계).
_CATALOG_IDS = [o.objective_id for o in SAFETY_CASE_OBJECTIVES]
assert len(_CATALOG_IDS) == len(set(_CATALOG_IDS)), "duplicate objective_id in SAFETY_CASE_OBJECTIVES"


@dataclass(frozen=True)
class SafetyCaseReport:
    """EASA ML 안전 사례 적합성 자가 평가 요약."""

    total: int
    conformant: int
    partial: int
    gap: int
    foundational_total: int
    foundational_conformant: int
    by_category: Mapping[str, tuple[int, int, int]]  # cat -> (conformant, partial, gap), read-only

    def __post_init__(self) -> None:
        # by_category 를 항상 읽기 전용 뷰로 동결 — 직접 생성 시에도 내부 변형 차단.
        if not isinstance(self.by_category, MappingProxyType):
            object.__setattr__(self, "by_category", MappingProxyType(dict(self.by_category)))
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
        # total>0 이면 by_category 분해가 반드시 존재·전수·합 일치해야 한다.
        # (빈 dict 로 교차검증을 우회해 위조 총계를 통과시키는 구멍을 막는다.)
        if self.total > 0:
            missing = set(SAFETY_CASE_CATEGORIES) - set(self.by_category.keys())
            if missing:
                raise ValueError(f"by_category missing required categories: {sorted(missing)}")
            invalid = set(self.by_category.keys()) - set(SAFETY_CASE_CATEGORIES)
            if invalid:
                raise ValueError(f"by_category contains unknown categories: {sorted(invalid)}")
            c = sum(v[0] for v in self.by_category.values())
            p = sum(v[1] for v in self.by_category.values())
            g = sum(v[2] for v in self.by_category.values())
            if (c, p, g) != (self.conformant, self.partial, self.gap):
                raise ValueError(
                    f"by_category sums ({c},{p},{g}) != "
                    f"({self.conformant},{self.partial},{self.gap})"
                )
        elif self.by_category:
            raise ValueError("by_category must be empty when total is 0")

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


def find_objective(objective_id: str) -> SafetyCaseObjective:
    """식별자로 목표를 조회한다. 없으면 KeyError."""
    for obj in SAFETY_CASE_OBJECTIVES:
        if obj.objective_id == objective_id:
            return obj
    raise KeyError(f"unknown safety case objective: {objective_id!r}")


def objectives_by_category(category: str) -> tuple[SafetyCaseObjective, ...]:
    """카테고리에 속한 목표를 식별자 정렬로 반환한다."""
    if category not in SAFETY_CASE_CATEGORIES:
        raise ValueError(f"category must be one of {SAFETY_CASE_CATEGORIES}, got {category!r}")
    return tuple(
        sorted((o for o in SAFETY_CASE_OBJECTIVES if o.category == category),
               key=lambda o: o.objective_id)
    )


def foundational_objectives() -> tuple[SafetyCaseObjective, ...]:
    """기반(필수) 목표(foundational=True)를 식별자 정렬로 반환한다."""
    return tuple(
        sorted((o for o in SAFETY_CASE_OBJECTIVES if o.foundational), key=lambda o: o.objective_id)
    )


def gaps() -> tuple[SafetyCaseObjective, ...]:
    """미충족(gap) 목표를 식별자 정렬로 반환한다."""
    return tuple(
        sorted((o for o in SAFETY_CASE_OBJECTIVES if o.is_gap), key=lambda o: o.objective_id)
    )


def objectives_by_status(status: str) -> tuple[SafetyCaseObjective, ...]:
    """적합성 상태별 목표를 식별자 정렬로 반환한다."""
    if status not in SC_STATUSES:
        raise ValueError(f"status must be one of {SC_STATUSES}, got {status!r}")
    return tuple(
        sorted((o for o in SAFETY_CASE_OBJECTIVES if o.status == status),
               key=lambda o: o.objective_id)
    )


def safety_case_report() -> SafetyCaseReport:
    """전체 적합성 현황을 집계한 결정적 리포트를 생성한다."""
    total = len(SAFETY_CASE_OBJECTIVES)
    conformant = sum(1 for o in SAFETY_CASE_OBJECTIVES if o.status == "conformant")
    partial = sum(1 for o in SAFETY_CASE_OBJECTIVES if o.status == "partial")
    gap = sum(1 for o in SAFETY_CASE_OBJECTIVES if o.status == "gap")
    foundational = [o for o in SAFETY_CASE_OBJECTIVES if o.foundational]
    foundational_conformant = sum(1 for o in foundational if o.status == "conformant")
    by_category: dict[str, tuple[int, int, int]] = {}
    for category in SAFETY_CASE_CATEGORIES:
        members = [o for o in SAFETY_CASE_OBJECTIVES if o.category == category]
        by_category[category] = (
            sum(1 for o in members if o.status == "conformant"),
            sum(1 for o in members if o.status == "partial"),
            sum(1 for o in members if o.status == "gap"),
        )
    return SafetyCaseReport(
        total=total,
        conformant=conformant,
        partial=partial,
        gap=gap,
        foundational_total=len(foundational),
        foundational_conformant=foundational_conformant,
        by_category=MappingProxyType(by_category),
    )


def safety_case_matrix() -> tuple[Mapping[str, object], ...]:
    """도구 간 교환용 적합성 매트릭스를 (카테고리, 식별자) 정렬 행으로 반환한다."""
    ordered = sorted(
        SAFETY_CASE_OBJECTIVES,
        key=lambda o: (SAFETY_CASE_CATEGORIES.index(o.category), o.objective_id),
    )
    return tuple(
        MappingProxyType({
            "objective_id": o.objective_id,
            "name": o.name,
            "category": o.category,
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
    lines = ["EASA ML 안전 사례(Safety Case) 적합성 매트릭스", ""]
    for row in safety_case_matrix():
        mark = _STATUS_MARK[str(row["status"])]
        kind = "기반" if row["foundational"] else "권장"
        module = row["sdacs_module"] or "—"
        lines.append(
            f"[{str(row['category']):30}] {mark:5} {kind} {row['anchor']} {row['name']}"
        )
        lines.append(f"      → {module}")
    return "\n".join(lines)


def _format_report() -> str:
    r = safety_case_report()
    lines = [
        "EASA ML 안전 사례(Safety Case) 적합성 자가 평가 요약",
        "",
        f"가중 점수   : {r.weighted_score_pct:.0f}% "
        f"(충족 {r.conformant} · 부분 {r.partial} · 갭 {r.gap} / 총 {r.total})",
        f"기반 목표   : {r.foundational_conformant}/{r.foundational_total} 완전 충족 "
        f"({r.foundational_conformant_pct:.0f}%) "
        f"{'— 기반 미완전 있음' if r.has_foundational_incomplete else '— 기반 전부 충족'}",
        "",
        "카테고리별 (충족/부분/갭):",
    ]
    for category in SAFETY_CASE_CATEGORIES:
        c, p, g = r.by_category[category]
        lines.append(f"  {_CATEGORY_NAMES[category]:50}: {c}/{p}/{g}")
    lines.append("")
    lines.append(
        "정직 공시: SDACS 의 강점은 안전-결정적 판단을 ML 이 전혀 내리지 않는 아키텍처다."
    )
    lines.append(
        "  결정적 디컨플릭션 + 5계층 안전망이 안전-결정권을 보유하고, ML 은 자문만 한다."
    )
    lines.append(
        "  형식 DAL 할당·잔여 위험 문서화 등 인증 서류 측면은 연구 수준이라 솔직히 갭이다."
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="EASA ML 안전 사례(Safety Case) 적합성 자가 평가 (ODYSSEY Phase 459)"
    )
    parser.add_argument("--matrix", action="store_true", help="전체 적합성 매트릭스 출력")
    parser.add_argument("--report", action="store_true", help="적합성 요약 출력")
    parser.add_argument("--category", choices=SAFETY_CASE_CATEGORIES, help="카테고리별 목표 출력")
    parser.add_argument("--gaps", action="store_true", help="미충족(갭) 목표 출력")
    parser.add_argument("--foundational", action="store_true", help="기반(필수) 목표 출력")
    args = parser.parse_args(argv)

    if args.matrix:
        print(_format_matrix())
    elif args.report:
        print(_format_report())
    elif args.category:
        for obj in objectives_by_category(args.category):
            print(f"{obj.objective_id} [{obj.status}]: {obj.name} — {obj.summary}")
    elif args.gaps:
        for obj in gaps():
            print(f"[{obj.category}] {obj.anchor} {obj.name}: {obj.summary}")
    elif args.foundational:
        for obj in foundational_objectives():
            print(f"{_STATUS_MARK[obj.status]} {obj.anchor} {obj.name} → {obj.sdacs_module or '—'}")
    else:
        print(_format_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
