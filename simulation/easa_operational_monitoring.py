"""ODYSSEY Phase 457 — EASA AI 운영 단계 ODD 모니터링·드리프트 대응 적합성 게이트.

SDACS 의 *학습 기반(ML)* 구성요소가 **운용 중(in-operation)** 자신의 운용 설계 영역
(Operational Design Domain, ODD)을 벗어나는지 실시간으로 감시하고, 벗어났을 때 결정적
안전망으로 안전하게 폴백하는가를 결정적으로 평가하는 적합성 매트릭스다. ODYSSEY Track 🔬
Formal & Research Frontier(451-460, "RL 일반화 + 인증 가능 ML 조사")의 후속 모듈로,
Phase 451(`easa_ai_conformance`)이 *설계 시점(design-time)* 의 러닝 어슈어런스를 평가하는
자매편이라면, 본 모듈은 그 *운영 시점(operation-time)* 대응물 — **추론 모델이 배포 후
훈련 분포를 벗어날 때 무슨 일이 일어나는가** — 를 EASA 운영 모니터링 축으로 평가한다.

근거 (권위 있는 출처)
--------------------
- **EASA Concept Paper — "Guidance for Level 1 & 2 machine learning applications"**
  (Issue 02, 2024). 신뢰 가능 AI 빌딩 블록 중 *AI safety risk mitigation* 및 운영 단계
  요구로 **ODD 모니터링(operational monitoring of the ODD)**, **입력 데이터 적합성 감시**,
  **out-of-ODD 시 안전 상태로의 전이(safe fallback)**, **운영 데이터 기록** 을 제시한다.
- **EASA Artificial Intelligence Roadmap 2.0** (2023) — 학습 구성요소의 *지속적 적합성
  보증(continuous airworthiness of the learning constituent)* 개념을 운영 모니터링·드리프트
  대응의 근거로 차용한다.
- **EASA Concept Paper §"AI assurance — runtime monitoring"** — 추론 모델 출력을 결정적
  모니터로 경계(bounding)하는 *runtime assurance* 아키텍처를 권고한다. SDACS 의
  "ML 자문 + 결정적 권한" 구조가 정확히 이 권고에 대응한다.

정직 공시 (CLAUDE.md)
--------------------
1. 본 모듈은 *기능적 자가 평가* 이며 EASA 공식 적합성 인증이 아니다. 카테고리와 ``anchor``
   토큰(``OM:*``)은 SDACS 의 해석이며 EASA 문서의 정확한 목표 번호를 복제하지 않는다.
2. ``status`` 는 3값(``conformant``·``partial``·``gap``)이다. SDACS 의 ML 은 *연구 수준*
   이므로 본 평가는 의도적으로 보수적이다 — 충족 주장보다 *미충족(갭)의 가시화* 에 가치가
   있다. 낮은 가중 점수가 곧 정직함이다.
3. ``sdacs_module`` 은 목표를 *실제로* 떠받치는 리포 내 모듈/산출물 경로다. ``status`` 가
   ``gap`` 이면 반드시 ``None`` 이고, 그 외(``conformant``/``partial``)면 반드시 실재 경로를
   인용한다 — 근거 없는 충족 주장을 구조적으로 금지한다(테스트가 디스크 실재를 강제).
4. SDACS 의 *진짜 강점* 은 드리프트 *탐지* 가 아니라 **out-of-ODD 폴백** 에 있다:
   근접 위협이 ML 의 신뢰 영역을 벗어나면 `hybrid_collision_avoidance` 가 *결정적 APF*
   로 전환(safety_override)하고, 5계층 안전망이 안전-결정권을 보유한다. 즉 "ML 을 신뢰할
   수 없는 순간 ML 을 쓰지 않음" 으로써 위험을 완화한다 — 이 아키텍처 선택이 본 매트릭스의
   ``conformant`` 항목들의 근거다. 반대로 *온라인 드리프트/노벨티 탐지* 는 솔직히 갭이다.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/easa_operational_monitoring.py --matrix          # 전체 적합성 매트릭스
    python simulation/easa_operational_monitoring.py --report          # 적합성 요약
    python simulation/easa_operational_monitoring.py --category fallback  # 카테고리별 목표
    python simulation/easa_operational_monitoring.py --gaps            # 미충족(갭) 목표
    python simulation/easa_operational_monitoring.py --foundational    # 기반(필수) 목표
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

# EASA AI 운영 모니터링 카테고리 (분류 축, 운영 흐름 순서).
MONITORING_CATEGORIES: tuple[str, ...] = (
    "odd_monitoring",        # ODD 경계 정의·실시간 준수 감시
    "drift_detection",       # 입력/개념 드리프트 탐지
    "confidence_gating",     # 불확실성·신뢰도 기반 자문 한정
    "fallback",              # out-of-ODD 시 결정적 안전망으로 폴백
    "operational_recording", # 운영 데이터 기록·사후 분석
)

_CATEGORY_NAMES: dict[str, str] = {
    "odd_monitoring": "ODD monitoring (운용 설계 영역 경계·실시간 준수)",
    "drift_detection": "Drift detection (입력·개념 분포 이탈 탐지)",
    "confidence_gating": "Confidence gating (불확실성 기반 자문 한정)",
    "fallback": "Out-of-ODD fallback (결정적 안전망 전이)",
    "operational_recording": "Operational recording (운영 데이터 기록·사후 분석)",
}

# 적합성 상태 (3값). conformant=완전, partial=부분, gap=미충족.
CONFORMANCE_STATUSES: tuple[str, ...] = ("conformant", "partial", "gap")

# 가중 점수: 완전 1.0, 부분 0.5, 미충족 0.0.
_STATUS_WEIGHT: dict[str, float] = {"conformant": 1.0, "partial": 0.5, "gap": 0.0}


@dataclass(frozen=True)
class MonitoringObjective:
    """단일 EASA 운영 모니터링 목표와 SDACS 대응의 정의."""

    objective_id: str           # 안정 식별자 (예: 'odd_boundary_runtime_check')
    name: str                   # 목표 명칭
    category: str               # 모니터링 카테고리
    anchor: str                 # EASA 운영 모니터링 참조 토큰 (SDACS 해석, 예: 'OM:ODD-01')
    foundational: bool          # 운영 인증에 필수인 기반 목표 여부
    status: str                 # conformant·partial·gap
    sdacs_module: str | None    # 떠받치는 경로 (gap 이면 None)
    summary: str                # 한 줄 설명

    def __post_init__(self) -> None:
        if not self.objective_id or self.objective_id != self.objective_id.strip():
            raise ValueError("objective_id must be non-empty and unpadded")
        if " " in self.objective_id:
            raise ValueError("objective_id must not contain internal spaces (snake_case)")
        if not self.name or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        if not self.anchor or not self.anchor.strip():
            raise ValueError("anchor must be a non-empty string")
        if not self.summary or not self.summary.strip():
            raise ValueError("summary must be a non-empty string")
        if self.category not in MONITORING_CATEGORIES:
            raise ValueError(
                f"category must be one of {MONITORING_CATEGORIES}, got {self.category!r}"
            )
        if not isinstance(self.foundational, bool):
            raise TypeError(
                f"foundational must be bool, got {type(self.foundational).__name__}"
            )
        if self.status not in CONFORMANCE_STATUSES:
            raise ValueError(
                f"status must be one of {CONFORMANCE_STATUSES}, got {self.status!r}"
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


# EASA 운영 모니터링 목표 카탈로그 ↔ SDACS 자산 매핑 (정본).
# sdacs_module 경로는 리포에 실재하는 모듈/산출물 — 미대응(gap)은 None.
# SDACS 의 강점은 폴백(fallback)에, 갭은 온라인 드리프트/노벨티 탐지에 있다(정직성 > 점수).
MONITORING_OBJECTIVES: tuple[MonitoringObjective, ...] = (
    # --- odd_monitoring ------------------------------------------------------
    MonitoringObjective(
        "odd_envelope_definition", "Operational Design Domain envelope definition",
        "odd_monitoring", "OM:ODD-01", True,
        "partial", "config/default_simulation.yaml",
        "운용 envelope(드론 수·고도 밴드·풍속 한계) 시나리오 정의 존재 — 형식 ODD 명세는 부분",
    ),
    MonitoringObjective(
        "odd_boundary_runtime_check", "Runtime ODD boundary check",
        "odd_monitoring", "OM:ODD-02", True,
        "conformant", "src/autonomy/hybrid_collision_avoidance.py",
        "근접 위협이 안전 임계(safety_override_dist)를 넘으면 실시간으로 ML 신뢰 영역 이탈을 "
        "판정 — 결정적 경계 감시가 매 스텝 작동",
    ),
    MonitoringObjective(
        "wind_regime_monitoring", "Environmental regime monitoring (wind)",
        "odd_monitoring", "OM:ODD-03", False,
        "partial", "src/training/domain_rand.py",
        "도메인 무작위화가 풍속 영역을 학습에 반영 — 운영 중 풍속 ODD 이탈 실시간 판정은 부분",
    ),
    # --- drift_detection -----------------------------------------------------
    MonitoringObjective(
        "input_distribution_drift", "Online input distribution drift detection",
        "drift_detection", "OM:DR-01", True,
        "gap", None,
        "운영 중 입력 분포 이탈을 온라인으로 탐지하는 검출기 없음 — 인증 핵심 갭 (갭)",
    ),
    MonitoringObjective(
        "sim_real_distribution_gap", "Sim-to-real distribution gap quantification",
        "drift_detection", "OM:DR-02", True,
        "partial", "src/training/sim_real_gap.py",
        "학습(시뮬)↔배포(실측) 분포 격차를 정량화 — 오프라인 측정이며 런타임 드리프트 추적은 부분",
    ),
    MonitoringObjective(
        "ood_scenario_coverage", "Out-of-distribution scenario coverage (test-time)",
        "drift_detection", "OM:DR-03", False,
        "partial", "simulation/scenario_fuzzer.py",
        "시나리오 퍼저가 미학습(OOD) 상황을 생성해 강건성 시험 — 테스트 시점 커버리지, 운영 탐지 아님",
    ),
    MonitoringObjective(
        "concept_drift_alerting", "Concept drift operator alerting",
        "drift_detection", "OM:DR-04", False,
        "gap", None,
        "개념 드리프트 발생 시 운영자에게 경보하는 인터페이스 없음 (갭)",
    ),
    # --- confidence_gating ---------------------------------------------------
    MonitoringObjective(
        "uncertainty_quantification", "ML output uncertainty quantification",
        "confidence_gating", "OM:CG-01", True,
        "partial", "simulation/uncertainty.py",
        "예측 불확실성 정량화 모듈 존재 — RL 자문 출력과의 운영 결속(게이팅)은 부분",
    ),
    MonitoringObjective(
        "confidence_gated_advisory", "Confidence-bounded advisory blending",
        "confidence_gating", "OM:CG-02", True,
        "conformant", "src/autonomy/hybrid_collision_avoidance.py",
        "ML 힘은 항상 [-1,1] 클립·가중 블렌딩으로 한정 — 단독 권한 없이 결정적 APF 와 합성",
    ),
    MonitoringObjective(
        "collision_risk_prediction", "Predictive collision-risk monitoring",
        "confidence_gating", "OM:CG-03", False,
        "partial", "simulation/collision_predictor.py",
        "충돌 위험 예측이 자문 신뢰 맥락을 제공 — 신뢰도 기반 자동 게이팅 결속은 부분",
    ),
    # --- fallback (SDACS 의 진짜 강점) ---------------------------------------
    MonitoringObjective(
        "out_of_odd_fallback", "Out-of-ODD fallback to deterministic control",
        "fallback", "OM:FB-01", True,
        "conformant", "src/autonomy/hybrid_collision_avoidance.py",
        "안전 임계 이탈 시 safety_override 로 *순수 결정적 APF* 전환 — ML 미신뢰 구간을 회피",
    ),
    MonitoringObjective(
        "safety_invariant_monitoring", "Runtime safety invariant monitoring",
        "fallback", "OM:FB-02", True,
        "conformant", "simulation/safety_net_invariant.py",
        "분리거리·우선순위 안전 불변식을 런타임 감시 — ML 출력과 무관하게 위반을 차단",
    ),
    MonitoringObjective(
        "deterministic_authority_runtime", "Deterministic controller retains runtime authority",
        "fallback", "OM:FB-03", True,
        "conformant", "src/airspace_control/controller/airspace_controller.py",
        "결정적 관제기가 최종 안전-결정권 보유 — ML 은 운영 중에도 자문 역할로 한정",
    ),
    # --- operational_recording -----------------------------------------------
    MonitoringObjective(
        "operational_data_logging", "Operational data recording for assurance",
        "operational_recording", "OM:OR-01", True,
        "partial", "simulation/replay_analyzer.py",
        "리플레이 기록·분석으로 운영 데이터 보존 — 인증용 추적 메타데이터 표준화는 부분",
    ),
    MonitoringObjective(
        "performance_metrics_monitoring", "Operational performance metrics monitoring",
        "operational_recording", "OM:OR-02", False,
        "partial", "src/monitoring/metrics.py",
        "운영 지표 수집 인프라 존재 — ML 특화 적합성 지표(드리프트·신뢰도) 연계는 부분",
    ),
    MonitoringObjective(
        "post_ops_anomaly_review", "Post-operation anomaly review",
        "operational_recording", "OM:OR-03", False,
        "partial", "simulation/replay_analyzer.py",
        "리플레이 분석으로 사후 이상 검토 가능 — ML 노벨티 자동 라벨링은 부분",
    ),
    MonitoringObjective(
        "online_model_update_management", "Online model update / continuous learning control",
        "operational_recording", "OM:OR-04", True,
        "gap", None,
        "운영 중 모델 갱신·지속 학습의 형상 관리·검증 절차 없음 — 의도적 미채택 영역 (갭)",
    ),
)


# 로드 시점 무결성 게이트 — 중복 식별자를 임포트 시 즉시 차단(테스트보다 이른 단계).
_CATALOG_IDS = [o.objective_id for o in MONITORING_OBJECTIVES]
assert len(_CATALOG_IDS) == len(set(_CATALOG_IDS)), "duplicate objective_id in MONITORING_OBJECTIVES"


@dataclass(frozen=True)
class MonitoringReport:
    """EASA 운영 모니터링 적합성 자가 평가 요약."""

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
        if self.by_category:
            invalid = set(self.by_category.keys()) - set(MONITORING_CATEGORIES)
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
        """기반 목표 중 미완전(부분·미충족) 항목이 있으면 True.

        *완전 충족이 아닌* 기반 목표(부분·갭 모두)를 가리킨다. 기반 ``partial`` 1건만
        있어도 True. SDACS 의 ML 은 기반 목표 다수가 부분·갭이므로 통상 True 다.
        """
        if not self.foundational_total:
            return False
        return self.foundational_conformant < self.foundational_total


def find_objective(objective_id: str) -> MonitoringObjective:
    """식별자로 목표를 조회한다. 없으면 KeyError."""
    for obj in MONITORING_OBJECTIVES:
        if obj.objective_id == objective_id:
            return obj
    raise KeyError(f"unknown monitoring objective: {objective_id!r}")


def objectives_by_category(category: str) -> tuple[MonitoringObjective, ...]:
    """카테고리에 속한 목표를 식별자 정렬로 반환한다."""
    if category not in MONITORING_CATEGORIES:
        raise ValueError(
            f"category must be one of {MONITORING_CATEGORIES}, got {category!r}"
        )
    return tuple(
        sorted((o for o in MONITORING_OBJECTIVES if o.category == category),
               key=lambda o: o.objective_id)
    )


def foundational_objectives() -> tuple[MonitoringObjective, ...]:
    """기반(필수) 목표(foundational=True)를 식별자 정렬로 반환한다."""
    return tuple(
        sorted((o for o in MONITORING_OBJECTIVES if o.foundational),
               key=lambda o: o.objective_id)
    )


def gaps() -> tuple[MonitoringObjective, ...]:
    """미충족(gap) 목표를 식별자 정렬로 반환한다."""
    return tuple(
        sorted((o for o in MONITORING_OBJECTIVES if o.is_gap), key=lambda o: o.objective_id)
    )


def objectives_by_status(status: str) -> tuple[MonitoringObjective, ...]:
    """적합성 상태별 목표를 식별자 정렬로 반환한다."""
    if status not in CONFORMANCE_STATUSES:
        raise ValueError(f"status must be one of {CONFORMANCE_STATUSES}, got {status!r}")
    return tuple(
        sorted((o for o in MONITORING_OBJECTIVES if o.status == status),
               key=lambda o: o.objective_id)
    )


def monitoring_report() -> MonitoringReport:
    """전체 적합성 현황을 집계한 결정적 리포트를 생성한다."""
    total = len(MONITORING_OBJECTIVES)
    conformant = sum(1 for o in MONITORING_OBJECTIVES if o.status == "conformant")
    partial = sum(1 for o in MONITORING_OBJECTIVES if o.status == "partial")
    gap = sum(1 for o in MONITORING_OBJECTIVES if o.status == "gap")
    foundational = [o for o in MONITORING_OBJECTIVES if o.foundational]
    foundational_conformant = sum(1 for o in foundational if o.status == "conformant")
    by_category: dict[str, tuple[int, int, int]] = {}
    for category in MONITORING_CATEGORIES:
        members = [o for o in MONITORING_OBJECTIVES if o.category == category]
        by_category[category] = (
            sum(1 for o in members if o.status == "conformant"),
            sum(1 for o in members if o.status == "partial"),
            sum(1 for o in members if o.status == "gap"),
        )
    return MonitoringReport(
        total=total,
        conformant=conformant,
        partial=partial,
        gap=gap,
        foundational_total=len(foundational),
        foundational_conformant=foundational_conformant,
        by_category=MappingProxyType(by_category),
    )


def monitoring_matrix() -> tuple[Mapping[str, object], ...]:
    """도구 간 교환용 적합성 매트릭스를 (카테고리, 식별자) 정렬 행으로 반환한다."""
    ordered = sorted(
        MONITORING_OBJECTIVES,
        key=lambda o: (MONITORING_CATEGORIES.index(o.category), o.objective_id),
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
    lines = ["EASA AI 운영 모니터링·드리프트 대응 적합성 매트릭스", ""]
    for row in monitoring_matrix():
        mark = _STATUS_MARK[str(row["status"])]
        kind = "기반" if row["foundational"] else "권장"
        module = row["sdacs_module"] or "—"
        lines.append(
            f"[{str(row['category']):22}] {mark:5} {kind} {row['anchor']} {row['name']}"
        )
        lines.append(f"      → {module}")
    return "\n".join(lines)


def _format_report() -> str:
    r = monitoring_report()
    lines = [
        "EASA AI 운영 모니터링 적합성 자가 평가 요약",
        "",
        f"가중 점수   : {r.weighted_score_pct:.0f}% "
        f"(충족 {r.conformant} · 부분 {r.partial} · 갭 {r.gap} / 총 {r.total})",
        f"기반 목표   : {r.foundational_conformant}/{r.foundational_total} 완전 충족 "
        f"({r.foundational_conformant_pct:.0f}%) "
        f"{'— 기반 미완전 있음' if r.has_foundational_incomplete else '— 기반 전부 충족'}",
        "",
        "카테고리별 (충족/부분/갭):",
    ]
    for category in MONITORING_CATEGORIES:
        c, p, g = r.by_category[category]
        lines.append(f"  {_CATEGORY_NAMES[category]:46}: {c}/{p}/{g}")
    lines.append("")
    lines.append(
        "정직 공시: SDACS 의 강점은 드리프트 *탐지* 가 아니라 out-of-ODD *폴백* 이다. ML 신뢰"
    )
    lines.append(
        "  영역을 벗어나면 결정적 안전망이 권한을 회수하며, 온라인 드리프트 탐지는 솔직히 갭이다."
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "EASA AI 운영 모니터링·드리프트 대응 적합성 자가 평가 (ODYSSEY Phase 457)"
        )
    )
    parser.add_argument("--matrix", action="store_true", help="전체 적합성 매트릭스 출력")
    parser.add_argument("--report", action="store_true", help="적합성 요약 출력")
    parser.add_argument(
        "--category", choices=MONITORING_CATEGORIES, help="카테고리별 목표 출력"
    )
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
