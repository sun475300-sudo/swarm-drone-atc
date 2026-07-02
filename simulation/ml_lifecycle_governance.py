"""ODYSSEY Phase 460 — EASA ML 수명주기 거버넌스(Lifecycle Governance) 적합성 게이트.

SDACS 의 ML 구성요소에 대한 *수명주기 전체* 거버넌스를 평가한다: 개발 환경과 데이터 출처
추적부터 형상 관리와 변경 통제를 거쳐 배포 인가(deployment authorization)와 배포 후
모니터링 거버넌스까지. Phase 458(`ml_verification_validation`)이 V&V *방법론* 을 다루고
Phase 459 가 안전 사례(safety case) 구조를 다룬다면, 본 모듈은 EASA 가 ML 주위에 요구하는
*조직·프로세스 거버넌스* 를 다룬다 — 누가 결정하는가, 변경은 어떻게 통제하는가, ML
구성요소는 어떻게 배포 인가를 받는가.

근거 (권위 있는 출처)
--------------------
- **EASA Concept Paper — "Guidance for Level 1 & 2 machine learning applications"**
  (Issue 02, 2024). 학습 프로세스 관리(Learning Process Management) 목표군으로 개발 환경
  재현성·데이터 거버넌스·형상 관리·배포 인가·배포 후 거버넌스를 요구한다.
- **EASA Artificial Intelligence Roadmap 2.0** (2023) — 학습 구성요소의 지속적 감항 보증
  (continuous airworthiness of the learning constituent) 개념을 배포 후 거버넌스의 근거로
  차용한다.
- **DO-178C / ED-12C** (소프트웨어 수명주기) — 소프트웨어 형상 관리·변경 통제·자격 심사
  프로세스를 ML 수명주기 거버넌스의 참조 프레임으로 둔다.
- **ARP4754A** (개발 보증) — 시스템 수준의 개발 보증 프로세스와 ML 구성요소 거버넌스의
  정합성을 위한 상위 참조.

정직 공시 (CLAUDE.md)
--------------------
1. 본 모듈은 *기능적 자가 평가* 이며 EASA 공식 적합성 인증이 아니다. 카테고리와
   ``anchor`` 토큰(``LG:*``)은 SDACS 의 해석이며 EASA 문서의 정확한 목표 번호를
   복제하지 않는다.
2. ``status`` 는 3값(``conformant``·``partial``·``gap``)이다. SDACS 의 ML 은 *연구 수준*
   이므로 대부분의 거버넌스 프로세스는 부분(partial)이거나 미충족(gap)이다 —
   낮은 가중 점수가 곧 정직함이다.
3. ``sdacs_module`` 은 목표를 *실제로* 떠받치는 리포 내 모듈/산출물 경로다. ``status`` 가
   ``gap`` 이면 반드시 ``None``, 그 외(``conformant``/``partial``)면 반드시 실재 경로를
   인용한다 — 근거 없는 충족 주장을 구조적으로 금지한다(테스트가 디스크 실재를 강제).
4. SDACS 의 *진짜 강점* 은 안전-결정 권한이 결정적 제어에 있다는 것이다: ML 은 자문
   전용(advisory-only)으로 배포되어 단독 안전-결정이 불가능하므로, ML 거버넌스 부담이
   구조적으로 제한된다. 반대로 실험 추적·데이터 버전 관리·배포 게이트·퇴역 정책 등
   정식 거버넌스 인프라는 솔직히 갭이다 — 이 비대칭이 본 매트릭스가 보고하려는
   핵심 사실이다.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/ml_lifecycle_governance.py --matrix          # 전체 적합성 매트릭스
    python simulation/ml_lifecycle_governance.py --report          # 적합성 요약
    python simulation/ml_lifecycle_governance.py --category configuration_management  # 카테고리별
    python simulation/ml_lifecycle_governance.py --gaps            # 미충족(갭) 목표
    python simulation/ml_lifecycle_governance.py --foundational    # 기반(필수) 목표
"""
from __future__ import annotations

import argparse
import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

# EASA ML 수명주기 거버넌스 카테고리 (수명주기 흐름 순서).
LIFECYCLE_CATEGORIES: tuple[str, ...] = (
    "development_environment",     # 개발 환경 관리 (ML 학습/추론 환경 재현성·도구 관리)
    "data_governance",             # 데이터 거버넌스 (학습 데이터 출처·품질·형상 관리)
    "configuration_management",    # 형상 관리 (모델·코드·데이터 버전 관리·변경 통제)
    "deployment_authorization",    # 배포 인가 (ML 모델 배포 승인·게이트)
    "post_deployment_governance",  # 배포 후 거버넌스 (운영 중 ML 성능·안전 감시 거버넌스)
)

_CATEGORY_NAMES: dict[str, str] = {
    "development_environment": "Development environment (개발 환경 재현성·도구 관리)",
    "data_governance": "Data governance (학습 데이터 출처·품질·형상 관리)",
    "configuration_management": "Configuration management (모델·코드·데이터 버전·변경 통제)",
    "deployment_authorization": "Deployment authorization (ML 모델 배포 승인·게이트)",
    "post_deployment_governance": "Post-deployment governance (운영 중 ML 성능·안전 감시)",
}

# 적합성 상태 (3값). conformant=완전, partial=부분, gap=미충족.
LIFECYCLE_STATUSES: tuple[str, ...] = ("conformant", "partial", "gap")

# 가중 점수: 완전 1.0, 부분 0.5, 미충족 0.0.
_STATUS_WEIGHT: dict[str, float] = {"conformant": 1.0, "partial": 0.5, "gap": 0.0}


@dataclass(frozen=True)
class LifecycleObjective:
    """단일 EASA ML 수명주기 거버넌스 목표와 SDACS 대응의 정의."""

    objective_id: str           # 안정 식별자 (예: 'training_environment_reproducibility')
    name: str                   # 목표 명칭
    category: str               # 수명주기 거버넌스 카테고리
    anchor: str                 # EASA ML 거버넌스 참조 토큰 (SDACS 해석, 예: 'LG:DE-01')
    foundational: bool          # 수명주기 인증에 필수인 기반 목표 여부
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
        if self.category not in LIFECYCLE_CATEGORIES:
            raise ValueError(
                f"category must be one of {LIFECYCLE_CATEGORIES}, got {self.category!r}"
            )
        if not isinstance(self.foundational, bool):
            raise TypeError(
                f"foundational must be bool, got {type(self.foundational).__name__}"
            )
        if self.status not in LIFECYCLE_STATUSES:
            raise ValueError(
                f"status must be one of {LIFECYCLE_STATUSES}, got {self.status!r}"
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


# EASA ML 수명주기 거버넌스 목표 카탈로그 ↔ SDACS 자산 매핑 (정본).
# sdacs_module 경로는 리포에 실재하는 모듈/산출물 — 미대응(gap)은 None.
# SDACS 의 강점은 ML 자문 전용 배포(advisory-only deployment)로 거버넌스 부담 제한,
# 갭은 정식 거버넌스 인프라(실험 추적·데이터 버전·배포 게이트·퇴역 정책)에 있다
# (정직성 > 점수).
LIFECYCLE_OBJECTIVES: tuple[LifecycleObjective, ...] = (
    # --- development_environment -------------------------------------------------
    LifecycleObjective(
        "training_environment_reproducibility",
        "Training environment reproducibility",
        "development_environment", "LG:DE-01", True,
        "partial", "config/default_simulation.yaml",
        "시뮬레이션 환경은 seed 기반 재현 가능 — ML 학습 환경(GPU·CUDA·라이브러리 버전) "
        "정식 고정은 부분",
    ),
    LifecycleObjective(
        "tool_qualification",
        "ML tool qualification (training frameworks)",
        "development_environment", "LG:DE-02", True,
        "gap", None,
        "ML 학습에 사용된 도구(SB3/PyTorch)의 형식 자격 심사(tool qualification) 없음 (갭)",
    ),
    LifecycleObjective(
        "compute_environment_documentation",
        "Compute environment documentation",
        "development_environment", "LG:DE-03", False,
        "partial", "Dockerfile",
        "Docker 기반 재현성 패키지 존재 — GPU 학습 환경·하드웨어 사양 문서화는 부분",
    ),
    # --- data_governance ----------------------------------------------------------
    LifecycleObjective(
        "training_data_provenance",
        "Training data provenance tracking",
        "data_governance", "LG:DG-01", True,
        "gap", None,
        "RL 학습 데이터(시뮬 경험)의 형식 출처 추적·품질 관리 없음 (갭)",
    ),
    LifecycleObjective(
        "data_versioning",
        "Training data and experience buffer versioning",
        "data_governance", "LG:DG-02", True,
        "gap", None,
        "학습 데이터·경험 버퍼의 형식 버전 관리 없음 (갭)",
    ),
    LifecycleObjective(
        "domain_randomization_governance",
        "Domain randomization parameter governance",
        "data_governance", "LG:DG-03", False,
        "partial", "src/training/domain_rand.py",
        "도메인 무작위화 파라미터 정의 존재 — 변경 통제·승인 절차는 부분",
    ),
    # --- configuration_management ------------------------------------------------
    LifecycleObjective(
        "model_version_control",
        "ML model source code version control",
        "configuration_management", "LG:CM-01", True,
        "partial", "src/rl/ppo_collision.py",
        "모델 코드는 git 관리 — 학습된 가중치·체크포인트의 형식 형상 관리는 부분",
    ),
    LifecycleObjective(
        "experiment_tracking",
        "ML experiment tracking infrastructure",
        "configuration_management", "LG:CM-02", True,
        "gap", None,
        "실험 추적 인프라(MLflow/W&B 등) 없음 — 학습 실행 간 비교·재현 불가 (갭)",
    ),
    LifecycleObjective(
        "change_impact_analysis",
        "Change impact analysis via traceability",
        "configuration_management", "LG:CM-03", False,
        "partial", "simulation/rtm_generator.py",
        "RTM 자동 생성으로 변경 영향 추적 부분 — ML 구성요소 특화 영향 분석은 부분",
    ),
    # --- deployment_authorization ------------------------------------------------
    LifecycleObjective(
        "deployment_gate_process",
        "Formal ML model deployment gate process",
        "deployment_authorization", "LG:DA-01", True,
        "gap", None,
        "ML 모델 배포 전 형식 승인·게이트 프로세스 없음 (갭)",
    ),
    LifecycleObjective(
        "pre_deployment_validation_checklist",
        "Pre-deployment validation checklist",
        "deployment_authorization", "LG:DA-02", False,
        "partial", "tests/test_property_deconflict.py",
        "전체 테스트 스위트(2,823+)가 배포 전 검증 역할 수행 — ML 특화 배포 체크리스트는 부분",
    ),
    LifecycleObjective(
        "advisory_only_deployment_constraint",
        "Advisory-only deployment constraint for ML",
        "deployment_authorization", "LG:DA-03", True,
        "conformant", "src/autonomy/hybrid_collision_avoidance.py",
        "ML 은 자문 전용(advisory-only)으로 배포 — 단독 안전-결정 불가로 배포 위험을 "
        "구조적으로 제한",
    ),
    # --- post_deployment_governance -----------------------------------------------
    LifecycleObjective(
        "operational_performance_baseline",
        "Operational ML performance baseline management",
        "post_deployment_governance", "LG:PD-01", True,
        "partial", "src/monitoring/metrics.py",
        "운영 지표 수집 인프라 존재 — ML 성능 기준선(baseline) 정식 관리는 부분",
    ),
    LifecycleObjective(
        "incident_response_procedure",
        "ML-related incident response procedure",
        "post_deployment_governance", "LG:PD-02", True,
        "gap", None,
        "ML 관련 운영 사고 대응 절차(incident response procedure) 없음 (갭)",
    ),
    LifecycleObjective(
        "model_retirement_policy",
        "ML model retirement and replacement policy",
        "post_deployment_governance", "LG:PD-03", False,
        "gap", None,
        "ML 모델 퇴역·교체 정책(retirement policy) 없음 (갭)",
    ),
    LifecycleObjective(
        "continuous_airworthiness_governance",
        "Continuous airworthiness governance process",
        "post_deployment_governance", "LG:PD-04", True,
        "gap", None,
        "지속적 감항 보증(continuous airworthiness) 거버넌스 프로세스 없음 (갭)",
    ),
)


# 로드 시점 무결성 게이트 — 중복 식별자를 임포트 시 즉시 차단(테스트보다 이른 단계).
_CATALOG_IDS = [o.objective_id for o in LIFECYCLE_OBJECTIVES]
assert len(_CATALOG_IDS) == len(set(_CATALOG_IDS)), "duplicate objective_id in LIFECYCLE_OBJECTIVES"


@dataclass(frozen=True)
class LifecycleReport:
    """EASA ML 수명주기 거버넌스 적합성 자가 평가 요약."""

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
        if self.total > 0:
            missing = set(LIFECYCLE_CATEGORIES) - set(self.by_category.keys())
            if missing:
                raise ValueError(f"by_category missing required categories: {sorted(missing)}")
            invalid = set(self.by_category.keys()) - set(LIFECYCLE_CATEGORIES)
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


def find_objective(objective_id: str) -> LifecycleObjective:
    """식별자로 목표를 조회한다. 없으면 KeyError."""
    for obj in LIFECYCLE_OBJECTIVES:
        if obj.objective_id == objective_id:
            return obj
    raise KeyError(f"unknown lifecycle governance objective: {objective_id!r}")


def objectives_by_category(category: str) -> tuple[LifecycleObjective, ...]:
    """카테고리에 속한 목표를 식별자 정렬로 반환한다."""
    if category not in LIFECYCLE_CATEGORIES:
        raise ValueError(f"category must be one of {LIFECYCLE_CATEGORIES}, got {category!r}")
    return tuple(
        sorted((o for o in LIFECYCLE_OBJECTIVES if o.category == category),
               key=lambda o: o.objective_id)
    )


def foundational_objectives() -> tuple[LifecycleObjective, ...]:
    """기반(필수) 목표(foundational=True)를 식별자 정렬로 반환한다."""
    return tuple(
        sorted((o for o in LIFECYCLE_OBJECTIVES if o.foundational),
               key=lambda o: o.objective_id)
    )


def gaps() -> tuple[LifecycleObjective, ...]:
    """미충족(gap) 목표를 식별자 정렬로 반환한다."""
    return tuple(
        sorted((o for o in LIFECYCLE_OBJECTIVES if o.is_gap), key=lambda o: o.objective_id)
    )


def objectives_by_status(status: str) -> tuple[LifecycleObjective, ...]:
    """적합성 상태별 목표를 식별자 정렬로 반환한다."""
    if status not in LIFECYCLE_STATUSES:
        raise ValueError(f"status must be one of {LIFECYCLE_STATUSES}, got {status!r}")
    return tuple(
        sorted((o for o in LIFECYCLE_OBJECTIVES if o.status == status),
               key=lambda o: o.objective_id)
    )


def lifecycle_report() -> LifecycleReport:
    """전체 적합성 현황을 집계한 결정적 리포트를 생성한다."""
    total = len(LIFECYCLE_OBJECTIVES)
    conformant = sum(1 for o in LIFECYCLE_OBJECTIVES if o.status == "conformant")
    partial = sum(1 for o in LIFECYCLE_OBJECTIVES if o.status == "partial")
    gap = sum(1 for o in LIFECYCLE_OBJECTIVES if o.status == "gap")
    foundational = [o for o in LIFECYCLE_OBJECTIVES if o.foundational]
    foundational_conformant = sum(1 for o in foundational if o.status == "conformant")
    by_category: dict[str, tuple[int, int, int]] = {}
    for category in LIFECYCLE_CATEGORIES:
        members = [o for o in LIFECYCLE_OBJECTIVES if o.category == category]
        by_category[category] = (
            sum(1 for o in members if o.status == "conformant"),
            sum(1 for o in members if o.status == "partial"),
            sum(1 for o in members if o.status == "gap"),
        )
    return LifecycleReport(
        total=total,
        conformant=conformant,
        partial=partial,
        gap=gap,
        foundational_total=len(foundational),
        foundational_conformant=foundational_conformant,
        by_category=MappingProxyType(by_category),
    )


def lifecycle_matrix() -> tuple[Mapping[str, object], ...]:
    """도구 간 교환용 적합성 매트릭스를 (카테고리, 식별자) 정렬 행으로 반환한다."""
    ordered = sorted(
        LIFECYCLE_OBJECTIVES,
        key=lambda o: (LIFECYCLE_CATEGORIES.index(o.category), o.objective_id),
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
    lines = ["EASA ML 수명주기 거버넌스(Lifecycle Governance) 적합성 매트릭스", ""]
    for row in lifecycle_matrix():
        mark = _STATUS_MARK[str(row["status"])]
        kind = "기반" if row["foundational"] else "권장"
        module = row["sdacs_module"] or "—"
        lines.append(
            f"[{str(row['category']):28}] {mark:5} {kind} {row['anchor']} {row['name']}"
        )
        lines.append(f"      → {module}")
    return "\n".join(lines)


def _format_report() -> str:
    r = lifecycle_report()
    lines = [
        "EASA ML 수명주기 거버넌스 적합성 자가 평가 요약",
        "",
        f"가중 점수   : {r.weighted_score_pct:.0f}% "
        f"(충족 {r.conformant} · 부분 {r.partial} · 갭 {r.gap} / 총 {r.total})",
        f"기반 목표   : {r.foundational_conformant}/{r.foundational_total} 완전 충족 "
        f"({r.foundational_conformant_pct:.0f}%) "
        f"{'— 기반 미완전 있음' if r.has_foundational_incomplete else '— 기반 전부 충족'}",
        "",
        "카테고리별 (충족/부분/갭):",
    ]
    for category in LIFECYCLE_CATEGORIES:
        c, p, g = r.by_category[category]
        lines.append(f"  {_CATEGORY_NAMES[category]:50}: {c}/{p}/{g}")
    lines.append("")
    lines.append(
        "정직 공시: SDACS 의 강점은 ML 자문 전용(advisory-only) 배포로 거버넌스 부담을"
    )
    lines.append(
        "  구조적으로 제한하는 데 있다. 정식 거버넌스 인프라(실험 추적·데이터 버전 관리·"
    )
    lines.append(
        "  배포 게이트·퇴역 정책)는 솔직히 갭이다 — 이 비대칭을 가시화하는 것이 본"
    )
    lines.append(
        "  매트릭스의 목적이다."
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="EASA ML 수명주기 거버넌스 적합성 자가 평가 (ODYSSEY Phase 460)"
    )
    parser.add_argument("--matrix", action="store_true", help="전체 적합성 매트릭스 출력")
    parser.add_argument("--report", action="store_true", help="적합성 요약 출력")
    parser.add_argument("--category", choices=LIFECYCLE_CATEGORIES, help="카테고리별 목표 출력")
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
