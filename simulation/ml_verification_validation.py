"""ODYSSEY Phase 458 — EASA ML 검증·확인(V&V) 적합성 게이트 (W-shaped 학습 어슈어런스).

EASA 의 학습 어슈어런스 "W자형(W-shaped)" 프로세스 모델은 전통적 V-모델(요구→설계→구현→
검증)에 데이터/학습 특유의 왼쪽 추가 다리(데이터 관리→학습→학습 검증)를 덧붙인다. Phase
451(`easa_ai_conformance`)이 신뢰 가능 AI 6개 블록을 개괄하며 ``learning_process_verification``
을 핵심 갭으로 지목했으나, 그 한 행으로는 *검증·확인(V&V)* 실무의 세부 축 — 요구 추적성·
테스트셋 대표성·커버리지 지표·경계 조건 시험·회귀 시험 — 이 각각 어디에 있고 어디가 비어
있는지 보이지 않는다. 본 모듈은 형제 모듈 452(RL 일반화)·453(자문 경계)·456(설명가능성)·
457(운영 모니터링)과 **서로소** 인 *V&V 방법론* 축을 다룬다: SDACS 가 ML 정책을 "검증했다"고
말할 수 있으려면 무엇이 있어야 하며, 실제로 무엇이 있는가.

근거 (권위 있는 출처)
--------------------
- **EASA Concept Paper — "Guidance for Level 1 & 2 machine learning applications"**
  (Issue 02, 2024). 학습 어슈어런스 W자형 프로세스에서 ``Learning Process Management`` ·
  ``Learning Process Verification`` 목표군으로 데이터셋 대표성, 학습/검증/시험 데이터 분리,
  성능 지표·커버리지, 강건성(경계·OOD) 시험을 요구한다.
- **EASA Artificial Intelligence Roadmap 2.0** (2023) — "continuous airworthiness of the
  learning constituent" 하에 모델 변경 시 회귀 검증·재인증 트리거 개념을 제시한다.
- **SAE/EUROCAE ED-324 / AS6983** (W-shaped ML lifecycle 표준화 초안) — 요구사항 추적성과
  학습 데이터/모델 산출물 간 이력 관리(traceability)를 V&V 의 전제로 둔다. SDACS 는 이 표준의
  공식 준수를 주장하지 않으며, 본 매트릭스는 그 정신을 SDACS 리포에 대응시킨 자체 해석이다.

정직 공시 (CLAUDE.md)
--------------------
1. 본 모듈은 *기능적 자가 평가* 이며 EASA/SAE 공식 적합성 인증이 아니다. 카테고리와
   ``anchor`` 토큰(``VV:*``)은 SDACS 의 해석이며 원문 목표 번호를 복제하지 않는다.
2. ``status`` 는 3값(``conformant``·``partial``·``gap``)이다. SDACS 의 ML 은 *연구 수준*
   이므로 평가는 의도적으로 보수적이다 — "속성 기반 테스트가 존재한다"와 "EASA 기준의
   대표성·커버리지가 정량 검증됐다"는 다르다. 메커니즘만 있으면 ``partial``, 정량적 기준·
   임계값까지 결속돼야 ``conformant`` 다.
3. ``sdacs_module`` 은 목표를 *실제로* 떠받치는 리포 내 모듈/테스트 경로다. ``status`` 가
   ``gap`` 이면 반드시 ``None``, 그 외(``conformant``/``partial``)면 반드시 실재 경로를
   인용한다 — 근거 없는 충족 주장을 구조적으로 금지한다(테스트가 디스크 실재를 강제).
4. SDACS 의 *진짜 강점* 은 결정론적 불변식에 대한 속성 기반 시험(Hypothesis)에 있다 —
   `tests/test_property_deconflict.py`·`tests/test_scenario_fuzzer_property.py` 가 규칙
   기반 디컨플릭션·퍼저의 경계/불변식을 무작위 입력 공간에서 검증한다. 반면 *RL 정책 자체의*
   요구 추적성·테스트셋 대표성·회귀 게이트는 연구 수준이라 대부분 부분·갭이다 — 이 비대칭이
   본 매트릭스가 보고하려는 핵심 사실이다.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/ml_verification_validation.py --matrix          # 전체 적합성 매트릭스
    python simulation/ml_verification_validation.py --report          # 적합성 요약
    python simulation/ml_verification_validation.py --category boundary_testing  # 카테고리별
    python simulation/ml_verification_validation.py --gaps            # 미충족(갭) 목표
    python simulation/ml_verification_validation.py --foundational    # 기반(필수) 목표
"""
from __future__ import annotations

import argparse
import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

# EASA ML V&V 카테고리 (W자형 검증 다리의 세부 축, 프로세스 흐름 순서).
VV_CATEGORIES: tuple[str, ...] = (
    "requirement_verification",  # ML 요구사항의 추적성(요구→데이터→모델→시험)
    "test_set_adequacy",         # 대표적 학습/검증/시험 데이터셋 분리·적정성
    "coverage_metrics",          # ML 을 위한 시험 커버리지 지표
    "boundary_testing",          # 경계 조건·엣지 케이스 시험
    "regression_testing",        # 모델 변경 시 회귀 검증
)

_CATEGORY_NAMES: dict[str, str] = {
    "requirement_verification": "Requirement verification (ML 요구 추적성)",
    "test_set_adequacy": "Test-set adequacy (대표적 시험 데이터셋)",
    "coverage_metrics": "Coverage metrics (ML 시험 커버리지 지표)",
    "boundary_testing": "Boundary testing (경계·엣지 케이스 시험)",
    "regression_testing": "Regression testing (모델 변경 회귀 검증)",
}

# 적합성 상태 (3값). conformant=완전, partial=부분(메커니즘만), gap=미충족.
VV_STATUSES: tuple[str, ...] = ("conformant", "partial", "gap")

# 가중 점수: 완전 1.0, 부분 0.5, 미충족 0.0.
_STATUS_WEIGHT: dict[str, float] = {"conformant": 1.0, "partial": 0.5, "gap": 0.0}


@dataclass(frozen=True)
class VVObjective:
    """단일 EASA ML V&V 목표와 SDACS 대응의 정의."""

    objective_id: str           # 안정 식별자 (예: 'ml_requirement_traceability')
    name: str                   # 목표 명칭
    category: str               # V&V 카테고리
    anchor: str                 # EASA ML V&V 참조 토큰 (SDACS 해석, 예: 'VV:RQ-01')
    foundational: bool          # 학습 어슈어런스 인증에 필수인 기반 목표 여부
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
        if self.category not in VV_CATEGORIES:
            raise ValueError(
                f"category must be one of {VV_CATEGORIES}, got {self.category!r}"
            )
        if not isinstance(self.foundational, bool):
            raise TypeError(
                f"foundational must be bool, got {type(self.foundational).__name__}"
            )
        if self.status not in VV_STATUSES:
            raise ValueError(
                f"status must be one of {VV_STATUSES}, got {self.status!r}"
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


# EASA ML V&V 목표 카탈로그 ↔ SDACS 자산 매핑 (정본).
# sdacs_module 경로는 리포에 실재하는 모듈/테스트 — 미대응(gap)은 None.
# SDACS 의 강점은 결정론적 불변식의 속성 기반 시험, 갭은 RL 정책 자체의 요구 추적성·
# 대표성 검증·회귀 게이트다(정직성 > 점수).
VV_OBJECTIVES: tuple[VVObjective, ...] = (
    # --- requirement_verification ---------------------------------------------
    VVObjective(
        "ml_requirement_traceability",
        "ML requirement to design/data/test traceability",
        "requirement_verification", "VV:RQ-01", True,
        "gap", None,
        "ML(RL) 요구사항이 데이터·모델·시험 산출물까지 형식 추적되는 매트릭스 없음 (갭)",
    ),
    VVObjective(
        "safety_requirement_to_deterministic_logic",
        "Safety requirement traceability for deterministic core",
        "requirement_verification", "VV:RQ-02", False,
        "partial", "simulation/path_deconflict.py",
        "결정적 디컨플릭션 코어의 분리거리 요구는 코드에 직접 구현·주석 추적 가능 — 형식 "
        "요구관리 도구(RTM) 결속은 부분",
    ),
    VVObjective(
        "training_reference_documentation",
        "Training/inference reference documentation",
        "requirement_verification", "VV:RQ-03", False,
        "partial", "src/rl/ppo_collision.py",
        "PPO 학습·평가 절차가 모듈 docstring 에 문서화 — 독립 V&V 팀용 정식 사양서는 부분",
    ),
    # --- test_set_adequacy -----------------------------------------------------
    VVObjective(
        "train_val_test_split_discipline",
        "Disciplined train/validation/test split",
        "test_set_adequacy", "VV:TS-01", True,
        "gap", None,
        "RL 정책 학습에 형식적 학습/검증/시험 데이터셋 분리·오염 방지 절차 없음 (갭)",
    ),
    VVObjective(
        "domain_randomization_representativeness",
        "Domain randomization for representative training distribution",
        "test_set_adequacy", "VV:TS-02", True,
        "partial", "src/training/domain_rand.py",
        "풍속·센서 노이즈·배터리·통신지연을 무작위화해 대표성 확장 — EASA 기준 대표성 정량 "
        "검증(커버리지 비율 등)은 부분",
    ),
    VVObjective(
        "sim_to_real_gap_bounding",
        "Simulation-to-real distribution gap bounding for test adequacy",
        "test_set_adequacy", "VV:TS-03", False,
        "partial", "src/training/sim_real_gap.py",
        "시뮬↔실측 분포 격차를 정량화해 시험셋 대표성 근거를 제공 — 실측 데이터 기반 폐루프 "
        "검증은 부분",
    ),
    # --- coverage_metrics --------------------------------------------------------
    VVObjective(
        "ml_specific_test_coverage_metric",
        "ML-specific test coverage metric (input-space / scenario coverage)",
        "coverage_metrics", "VV:CV-01", True,
        "partial", "simulation/scenario_fuzzer.py",
        "시나리오 퍼저가 입력 공간을 체계적으로 확장·기록 — EASA 기준 정량 커버리지 목표치 "
        "(%) 결속은 부분",
    ),
    VVObjective(
        "generalization_test_protocol",
        "Held-out generalization test protocol for RL policy",
        "coverage_metrics", "VV:CV-02", True,
        "partial", "simulation/rl_generalization_protocol.py",
        "미학습 시나리오 전이(일반화) 평가 프로토콜 존재 — 인증 기준 통과/실패 임계값 결속은 부분",
    ),
    VVObjective(
        "code_coverage_conventional_tests",
        "Conventional code coverage for deterministic modules",
        "coverage_metrics", "VV:CV-03", False,
        "partial", "tests/test_property_deconflict.py",
        "pytest 스위트(2,823+)가 결정적 모듈 코드 커버리지를 제공 — ML 추론 경로 자체의 "
        "커버리지 집계는 부분",
    ),
    # --- boundary_testing --------------------------------------------------------
    VVObjective(
        "deterministic_invariant_property_testing",
        "Property-based boundary/invariant testing (Hypothesis)",
        "boundary_testing", "VV:BT-01", True,
        "conformant", "tests/test_property_deconflict.py",
        "Hypothesis 기반 속성 시험이 디컨플릭션 코어의 분리 불변식·보간 경계를 무작위 입력 "
        "전역에서 결정적으로 검증 — 예제 기반 시험이 놓치는 경계 조건 포착",
    ),
    VVObjective(
        "adversarial_scenario_boundary_testing",
        "Adversarial fuzzed scenario boundary testing",
        "boundary_testing", "VV:BT-02", True,
        "conformant", "tests/test_scenario_fuzzer_property.py",
        "속성 기반 퍼저 시험이 시나리오 변이의 스키마 유효성·분포 재정규화·거리 순서 불변식을 "
        "근방 시나리오 공간 전역에서 검증 — 결정론적 재현성 포함",
    ),
    VVObjective(
        "advisory_boundary_saturation_testing",
        "RL advisory output boundary/saturation testing",
        "boundary_testing", "VV:BT-03", False,
        "partial", "simulation/rl_advisory_boundary.py",
        "RL 자문 출력의 클리핑·포화 경계 정합성 게이트 존재 — 정책 자체의 극단 입력 시험 "
        "커버리지는 부분",
    ),
    VVObjective(
        "onboard_inference_resource_boundary",
        "Onboard inference resource boundary estimation",
        "boundary_testing", "VV:BT-04", False,
        "partial", "simulation/onboard_rl_bench.py",
        "엣지 배포 시 지연시간·메모리·전력의 분석적 경계 추정 존재 — 실측 벤치마크 검증은 부분",
    ),
    # --- regression_testing --------------------------------------------------------
    VVObjective(
        "full_suite_regression_gate",
        "Full deterministic-core regression suite as change gate",
        "regression_testing", "VV:RG-01", True,
        "conformant", "tests/test_property_deconflict.py",
        "PR 전 전체 pytest 스위트(2,823+) 실행이 결정적 코어 변경의 회귀 게이트로 관행화 — "
        "CLAUDE.md 컨벤션으로 강제",
    ),
    VVObjective(
        "ml_model_version_regression_baseline",
        "ML model version-to-version regression baseline comparison",
        "regression_testing", "VV:RG-02", True,
        "gap", None,
        "RL 정책 재학습/버전 갱신 시 이전 버전 대비 안전성·성능 회귀를 정량 비교하는 절차 "
        "없음 (갭)",
    ),
    VVObjective(
        "safety_invariant_regression_monitoring",
        "Safety-invariant regression monitoring across code changes",
        "regression_testing", "VV:RG-03", False,
        "partial", "simulation/safety_net_invariant.py",
        "분리거리·우선순위 안전 불변식의 런타임 감시가 회귀 방지에 기여 — 형식 회귀 리포트 "
        "산출물화는 부분",
    ),
)


# 로드 시점 무결성 게이트 — 중복 식별자를 임포트 시 즉시 차단(테스트보다 이른 단계).
_CATALOG_IDS = [o.objective_id for o in VV_OBJECTIVES]
assert len(_CATALOG_IDS) == len(set(_CATALOG_IDS)), "duplicate objective_id in VV_OBJECTIVES"


@dataclass(frozen=True)
class VVReport:
    """EASA ML V&V 적합성 자가 평가 요약."""

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
            missing = set(VV_CATEGORIES) - set(self.by_category.keys())
            if missing:
                raise ValueError(f"by_category missing required categories: {sorted(missing)}")
            invalid = set(self.by_category.keys()) - set(VV_CATEGORIES)
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


def find_objective(objective_id: str) -> VVObjective:
    """식별자로 목표를 조회한다. 없으면 KeyError."""
    for obj in VV_OBJECTIVES:
        if obj.objective_id == objective_id:
            return obj
    raise KeyError(f"unknown V&V objective: {objective_id!r}")


def objectives_by_category(category: str) -> tuple[VVObjective, ...]:
    """카테고리에 속한 목표를 식별자 정렬로 반환한다."""
    if category not in VV_CATEGORIES:
        raise ValueError(f"category must be one of {VV_CATEGORIES}, got {category!r}")
    return tuple(
        sorted((o for o in VV_OBJECTIVES if o.category == category),
               key=lambda o: o.objective_id)
    )


def foundational_objectives() -> tuple[VVObjective, ...]:
    """기반(필수) 목표(foundational=True)를 식별자 정렬로 반환한다."""
    return tuple(
        sorted((o for o in VV_OBJECTIVES if o.foundational), key=lambda o: o.objective_id)
    )


def gaps() -> tuple[VVObjective, ...]:
    """미충족(gap) 목표를 식별자 정렬로 반환한다."""
    return tuple(
        sorted((o for o in VV_OBJECTIVES if o.is_gap), key=lambda o: o.objective_id)
    )


def objectives_by_status(status: str) -> tuple[VVObjective, ...]:
    """적합성 상태별 목표를 식별자 정렬로 반환한다."""
    if status not in VV_STATUSES:
        raise ValueError(f"status must be one of {VV_STATUSES}, got {status!r}")
    return tuple(
        sorted((o for o in VV_OBJECTIVES if o.status == status), key=lambda o: o.objective_id)
    )


def vv_report() -> VVReport:
    """전체 적합성 현황을 집계한 결정적 리포트를 생성한다."""
    total = len(VV_OBJECTIVES)
    conformant = sum(1 for o in VV_OBJECTIVES if o.status == "conformant")
    partial = sum(1 for o in VV_OBJECTIVES if o.status == "partial")
    gap = sum(1 for o in VV_OBJECTIVES if o.status == "gap")
    foundational = [o for o in VV_OBJECTIVES if o.foundational]
    foundational_conformant = sum(1 for o in foundational if o.status == "conformant")
    by_category: dict[str, tuple[int, int, int]] = {}
    for category in VV_CATEGORIES:
        members = [o for o in VV_OBJECTIVES if o.category == category]
        by_category[category] = (
            sum(1 for o in members if o.status == "conformant"),
            sum(1 for o in members if o.status == "partial"),
            sum(1 for o in members if o.status == "gap"),
        )
    return VVReport(
        total=total,
        conformant=conformant,
        partial=partial,
        gap=gap,
        foundational_total=len(foundational),
        foundational_conformant=foundational_conformant,
        by_category=MappingProxyType(by_category),
    )


def vv_matrix() -> tuple[Mapping[str, object], ...]:
    """도구 간 교환용 적합성 매트릭스를 (카테고리, 식별자) 정렬 행으로 반환한다."""
    ordered = sorted(
        VV_OBJECTIVES,
        key=lambda o: (VV_CATEGORIES.index(o.category), o.objective_id),
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
    lines = ["EASA ML 검증·확인(V&V) 적합성 매트릭스 (W-shaped 학습 어슈어런스)", ""]
    for row in vv_matrix():
        mark = _STATUS_MARK[str(row["status"])]
        kind = "기반" if row["foundational"] else "권장"
        module = row["sdacs_module"] or "—"
        lines.append(
            f"[{str(row['category']):26}] {mark:5} {kind} {row['anchor']} {row['name']}"
        )
        lines.append(f"      → {module}")
    return "\n".join(lines)


def _format_report() -> str:
    r = vv_report()
    lines = [
        "EASA ML 검증·확인(V&V) 적합성 자가 평가 요약",
        "",
        f"가중 점수   : {r.weighted_score_pct:.0f}% "
        f"(충족 {r.conformant} · 부분 {r.partial} · 갭 {r.gap} / 총 {r.total})",
        f"기반 목표   : {r.foundational_conformant}/{r.foundational_total} 완전 충족 "
        f"({r.foundational_conformant_pct:.0f}%) "
        f"{'— 기반 미완전 있음' if r.has_foundational_incomplete else '— 기반 전부 충족'}",
        "",
        "카테고리별 (충족/부분/갭):",
    ]
    for category in VV_CATEGORIES:
        c, p, g = r.by_category[category]
        lines.append(f"  {_CATEGORY_NAMES[category]:42}: {c}/{p}/{g}")
    lines.append("")
    lines.append(
        "정직 공시: SDACS 의 강점은 결정론적 불변식에 대한 속성 기반 시험(Hypothesis)이다."
    )
    lines.append(
        "  RL 정책 자체의 요구 추적성·대표적 데이터셋 분리·버전 간 회귀 게이트는 연구 수준이라"
    )
    lines.append(
        "  대부분 부분·갭이다 — 이 비대칭을 가시화하는 것이 본 매트릭스의 목적이다."
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="EASA ML 검증·확인(V&V) 적합성 자가 평가 (ODYSSEY Phase 458)"
    )
    parser.add_argument("--matrix", action="store_true", help="전체 적합성 매트릭스 출력")
    parser.add_argument("--report", action="store_true", help="적합성 요약 출력")
    parser.add_argument("--category", choices=VV_CATEGORIES, help="카테고리별 목표 출력")
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
