"""ODYSSEY Phase 452 — RL 일반화 평가 프로토콜 적합성 게이트.

SDACS 의 강화학습(RL) 구성요소가 *미학습 시나리오로의 일반화* 를 검증하는 데 필요한
평가 프로토콜 요소를 어디까지 갖췄는가를 결정적으로 판정하는 자문 게이트다. ODYSSEY
Track 🔬 Formal & Research Frontier(451-460)의 두 번째 모듈로, 자매 Phase 451
(`easa_ai_conformance`)이 *EASA 신뢰 가능 AI* 축에서 표면화한 핵심 연구 갭 —
``learning_process_verification`` ("미학습 시나리오 전이(일반화) 검증 프로토콜 없음 —
451-460 트랙의 핵심 연구 갭") — 을 *그 갭이 무엇으로 구성되는가* 의 차원으로 분해해
정직하게 추적한다. 451 이 "무엇이 빠졌는가" 를 한 줄로 선언했다면, 본 모듈은 "그 빠진
프로토콜이 정확히 어떤 요소로 이루어지며 각 요소가 현 리포에 있는가" 를 판정한다.

근거 (권위 있는 출처)
--------------------
- **Cobbe et al., "Quantifying Generalization in Reinforcement Learning"** (ICML 2019).
  학습/평가 환경을 *분리된 집합* 으로 나누고(절차적 생성 레벨의 train/test split) 미학습
  레벨에서 성능을 측정해 *일반화 갭* 을 정량화하는 방법론을 본 모듈의 ``evaluation_design``·
  ``generalization_analysis`` 단계 요소로 차용한다.
- **EASA Learning Assurance — 목표 LA:LM-03 (Learning process verification /
  generalisation)**. 자매 451 이 ``gap`` 으로 공시한 바로 그 목표이며, 본 게이트의
  최상위 추적 대상이다(``parent_gap_traceability`` 요소가 451 카탈로그로 역참조).
- 일반화 주장의 통계적 엄밀성(다중 시드·신뢰구간·표본수 검정력)과 비-ML 결정적
  기준선(APF/CBS) 대비 비교는 ML 평가 보고의 통상 기준을 따른다.

정직 공시 (CLAUDE.md)
--------------------
1. 본 모듈은 *프로토콜 준비도* 의 자가 평가이며, RL 정책이 실제로 일반화함을 *증명* 하지
   않는다. 게이트가 ``PROTOCOL_READY`` 라도 그것은 "평가할 도구가 갖춰졌다" 일 뿐
   "정책이 일반화한다" 가 아니다 — 준비도와 결과는 독립이다.
2. ``status`` 는 3값(``established``·``partial``·``absent``)이다. SDACS 의 RL 은
   *연구 수준* 이고 일반화 평가 프로토콜은 트랙의 *미해결 프런티어* 이므로, 본 평가는
   의도적으로 보수적이다 — 충족 주장보다 *부재(absent)의 가시화* 에 가치가 있다.
3. ``evidence`` 는 요소를 *실제로* 떠받치는 리포 내 모듈/산출물 경로다. ``status`` 가
   ``absent`` 이면 반드시 ``None`` 이고, 그 외(``established``/``partial``)면 반드시
   실재 경로를 인용한다 — 근거 없는 충족 주장을 구조적으로 금지한다(테스트가 디스크
   실재를 강제).
4. **정직성 결속(핵심):** 유일하게 ``established`` 인 요소는 *갭 추적성 자체*
   (``parent_gap_traceability``)다. 즉 SDACS 가 지금 한 일은 *프로토콜을 갖춘 것* 이
   아니라 *프로토콜이 없음을 정직하게 목록화한 것* 뿐이다. 따라서 종합 판정
   (``protocol_readiness``)은 **기반(필수) 요소가 하나도 established 가 아니면**
   추적성이 established 여도 ``NO_PROTOCOL`` 로 고정한다 — 갭을 카탈로그한 것이 갭을
   메운 것으로 둔갑하지 못하게 막는다.

무작위성 0 · 결정적 · 부수효과 0. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/rl_generalization_protocol.py --matrix       # 전체 프로토콜 매트릭스
    python simulation/rl_generalization_protocol.py --report       # 준비도 요약
    python simulation/rl_generalization_protocol.py --stage evaluation_design  # 단계별
    python simulation/rl_generalization_protocol.py --absent       # 부재(absent) 요소
    python simulation/rl_generalization_protocol.py --foundational # 기반(필수) 요소
    python simulation/rl_generalization_protocol.py --verdict      # 종합 준비도 판정
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

# 일반화 평가 프로토콜의 단계(분류 축, 평가 흐름 순서).
PROTOCOL_STAGES: tuple[str, ...] = (
    "evaluation_design",
    "distribution_shift",
    "statistical_rigor",
    "baseline_grounding",
    "generalization_analysis",
)

_STAGE_NAMES: dict[str, str] = {
    "evaluation_design": "Evaluation design (train/test 분리·held-out 시나리오)",
    "distribution_shift": "Distribution shift (분포 이동 스트레스·sim2real)",
    "statistical_rigor": "Statistical rigor (다중 시드·신뢰구간·검정력)",
    "baseline_grounding": "Baseline grounding (결정적 기준선 대비·ablation)",
    "generalization_analysis": "Generalization analysis (일반화 갭·최악·OOD)",
}

# 프로토콜 요소 상태 (3값). established=구비, partial=부분, absent=부재.
PROTOCOL_STATUSES: tuple[str, ...] = ("established", "partial", "absent")

# 가중 점수: 구비 1.0, 부분 0.5, 부재 0.0.
_STATUS_WEIGHT: dict[str, float] = {"established": 1.0, "partial": 0.5, "absent": 0.0}

# 종합 준비도 판정 (서로소).
PROTOCOL_READY = "PROTOCOL_READY"          # 기반 요소 전부 established
PARTIAL_PROTOCOL = "PARTIAL_PROTOCOL"      # 기반 일부 established
NO_PROTOCOL = "NO_PROTOCOL"                # 기반 0개 established (추적성만으론 불가)
READINESS_VERDICTS: tuple[str, ...] = (PROTOCOL_READY, PARTIAL_PROTOCOL, NO_PROTOCOL)


@dataclass(frozen=True)
class ProtocolRequirement:
    """단일 RL 일반화 평가 프로토콜 요소와 SDACS 대응의 정의."""

    requirement_id: str         # 안정 식별자 (예: 'train_test_scenario_split')
    name: str                   # 요소 명칭
    stage: str                  # 프로토콜 단계
    anchor: str                 # 방법론 계열 참조 토큰 (SDACS 해석, 예: 'ED:TT-01')
    foundational: bool          # 신뢰할 만한 일반화 주장에 필수인 요소 여부
    status: str                 # established·partial·absent
    evidence: str | None        # 떠받치는 경로 (absent 이면 None)
    summary: str                # 한 줄 설명

    def __post_init__(self) -> None:
        if not self.requirement_id or self.requirement_id != self.requirement_id.strip():
            raise ValueError("requirement_id must be non-empty and unpadded")
        if " " in self.requirement_id:
            raise ValueError("requirement_id must not contain internal spaces (snake_case)")
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
        if not isinstance(self.foundational, bool):
            raise TypeError(
                f"foundational must be bool, got {type(self.foundational).__name__}"
            )
        if self.status not in PROTOCOL_STATUSES:
            raise ValueError(
                f"status must be one of {PROTOCOL_STATUSES}, got {self.status!r}"
            )
        # 정직성 결속: absent ⟺ 근거 경로 없음. 구비/부분은 반드시 실재 경로 인용.
        if self.status == "absent":
            if self.evidence is not None:
                raise ValueError("an absent requirement must not cite evidence")
        else:
            if self.evidence is None or not self.evidence.strip():
                raise ValueError(
                    f"status {self.status!r} must cite a non-empty evidence path"
                )

    @property
    def is_absent(self) -> bool:
        """부재(absent) 여부."""
        return self.status == "absent"

    @property
    def weight(self) -> float:
        """가중 점수 기여 (established 1.0·partial 0.5·absent 0.0)."""
        return _STATUS_WEIGHT[self.status]


# RL 일반화 평가 프로토콜 요소 카탈로그 ↔ SDACS 자산 매핑 (정본).
# evidence 경로는 리포에 실재하는 모듈/산출물 — 부재(absent)는 None.
# 일반화 평가 프로토콜은 트랙의 미해결 프런티어이므로 본 매핑은 의도적으로 보수적이다.
PROTOCOL_REQUIREMENTS: tuple[ProtocolRequirement, ...] = (
    # --- evaluation_design ---------------------------------------------------
    ProtocolRequirement(
        "train_test_scenario_split", "Train/test scenario split (held-out 분리)",
        "evaluation_design", "ED:TT-01", True,
        "absent", None,
        "학습 분포와 분리된 *지정* held-out 평가 시나리오 집합 없음 — 일반화 측정 전제 미충족 (부재)",
    ),
    ProtocolRequirement(
        "held_out_scenario_suite", "Held-out 후보 표준 시나리오 스위트",
        "evaluation_design", "ED:HO-01", False,
        "partial", "simulation/standard_scenarios.py",
        "SDACS-SBS-10 표준 스위트가 held-out 후보로 존재 — 단 RL train/test 분할로 *지정* 되진 않음 (부분)",
    ),
    ProtocolRequirement(
        "evaluation_protocol_spec", "기록된 일반화 평가 프로토콜 명세",
        "evaluation_design", "ED:SP-01", True,
        "absent", None,
        "평가 절차(분할 기준·지표·합격선)를 추적 가능 형식으로 명문화한 산출물 없음 (부재)",
    ),
    # --- distribution_shift --------------------------------------------------
    ProtocolRequirement(
        "domain_randomization_coverage", "Domain randomization 학습 분포 다양화",
        "distribution_shift", "DS:DR-01", False,
        "partial", "src/training/domain_rand.py",
        "DR+ADR 로 학습 분포 다양화 — 단 평가 분포 대비 *커버리지 측정* 은 미구비 (부분)",
    ),
    ProtocolRequirement(
        "sim_to_real_gap_model", "Sim-to-real 갭 모델·보정",
        "distribution_shift", "DS:SR-01", False,
        "partial", "src/training/sim_real_gap.py",
        "시뮬-실측 갭 파라미터 자동 보정 존재 — 단 실 비행 데이터로 *검증* 되진 않음 (부분)",
    ),
    ProtocolRequirement(
        "covariate_shift_stress", "Covariate shift 스트레스 평가 (풍속·밀도)",
        "distribution_shift", "DS:CS-01", True,
        "absent", None,
        "RL 정책을 미학습 풍속/밀도 분포에서 체계적으로 스트레스하는 평가 프로토콜 없음 (부재)",
    ),
    # --- statistical_rigor ---------------------------------------------------
    ProtocolRequirement(
        "multi_seed_evaluation", "다중 시드 평가",
        "statistical_rigor", "SR:MS-01", True,
        "absent", None,
        "여러 시드에 걸친 RL 일반화 성능 평가 기록 없음 — 분산 추정 전제 미충족 (부재)",
    ),
    ProtocolRequirement(
        "confidence_interval_reporting", "신뢰구간 보고 인프라",
        "statistical_rigor", "SR:CI-01", False,
        "partial", "simulation/uncertainty.py",
        "Monte Carlo 신뢰구간 자동 리포트 인프라 존재 — 단 RL 일반화 평가에 *결선* 되진 않음 (부분)",
    ),
    ProtocolRequirement(
        "sample_size_power", "표본수·검정력 산출",
        "statistical_rigor", "SR:PW-01", False,
        "partial", "simulation/power_analysis.py",
        "충돌 해결률 검정력·표본수 산출 인프라 존재 — RL 일반화 비교에 *적용* 은 미구비 (부분)",
    ),
    # --- baseline_grounding --------------------------------------------------
    ProtocolRequirement(
        "deterministic_baseline_comparison", "결정적 기준선(APF) 대비 비교",
        "baseline_grounding", "BG:DB-01", False,
        "partial", "simulation/apf_lyapunov.py",
        "결정적 APF 기준선이 형식적으로 특성화됨 — 단 held-out 평가에서 RL 대 APF *직접 비교* 프로토콜은 미구비 (부분)",
    ),
    ProtocolRequirement(
        "ablation_protocol", "RL 기여 ablation 프로토콜",
        "baseline_grounding", "BG:AB-01", True,
        "absent", None,
        "RL 자문 제거 시 성능 변화를 분리 측정하는 ablation 평가 프로토콜 없음 (부재)",
    ),
    # --- generalization_analysis ---------------------------------------------
    ProtocolRequirement(
        "generalization_gap_quantification", "일반화 갭 정량화 (train−test)",
        "generalization_analysis", "GA:GG-01", True,
        "absent", None,
        "학습-평가 성능 차(일반화 갭)를 측정·보고한 산출물 없음 — LA:LM-03 직접 갭 (부재)",
    ),
    ProtocolRequirement(
        "worst_case_robustness", "최악 케이스 강건성 평가",
        "generalization_analysis", "GA:WC-01", False,
        "absent", None,
        "RL 정책의 최악 시나리오(적대적 분포) 강건성을 측정하는 평가 프로토콜 없음 (부재)",
    ),
    ProtocolRequirement(
        "ood_detection", "Out-of-distribution 입력 탐지",
        "generalization_analysis", "GA:OD-01", False,
        "absent", None,
        "RL 입력이 학습 분포 밖임을 런타임에 탐지하는 OOD 게이트 없음 (부재)",
    ),
    ProtocolRequirement(
        "parent_gap_traceability", "상위 EASA 갭(LA:LM-03) 추적성",
        "generalization_analysis", "GA:TR-01", False,
        "established", "simulation/easa_ai_conformance.py",
        "본 프로토콜이 추적하는 상위 갭이 451 카탈로그에 정직히 공시됨 — *갭의 목록화* 자체는 구비(단 프로토콜 구비 아님)",
    ),
)


# 로드 시점 무결성 게이트 — 중복 식별자를 임포트 시 즉시 차단(테스트보다 이른 단계).
_CATALOG_IDS = [r.requirement_id for r in PROTOCOL_REQUIREMENTS]
assert len(_CATALOG_IDS) == len(set(_CATALOG_IDS)), \
    "duplicate requirement_id in PROTOCOL_REQUIREMENTS"


@dataclass(frozen=True)
class ProtocolReport:
    """RL 일반화 평가 프로토콜 준비도 요약."""

    total: int
    established: int
    partial: int
    absent: int
    foundational_total: int
    foundational_established: int
    by_stage: Mapping[str, tuple[int, int, int]]  # stage -> (established, partial, absent)

    def __post_init__(self) -> None:
        # by_stage 를 항상 읽기 전용 뷰로 동결 — 직접 생성 시에도 내부 변형 차단.
        if not isinstance(self.by_stage, MappingProxyType):
            object.__setattr__(self, "by_stage", MappingProxyType(dict(self.by_stage)))
        if min(self.total, self.established, self.partial, self.absent,
               self.foundational_total, self.foundational_established) < 0:
            raise ValueError("counts must be non-negative")
        if self.established + self.partial + self.absent != self.total:
            raise ValueError(
                f"established ({self.established}) + partial ({self.partial}) + "
                f"absent ({self.absent}) != total ({self.total})"
            )
        if self.foundational_established > self.foundational_total:
            raise ValueError("foundational_established cannot exceed foundational_total")
        if self.foundational_total > self.total:
            raise ValueError("foundational_total cannot exceed total")
        # by_stage 합산 검증은 *항상* 실행 — 빈 dict 우회를 차단(어드바이저 MEDIUM).
        # total=0·by_stage={} 정상 케이스는 (0,0,0)==(0,0,0) 으로 자연 통과한다.
        invalid = set(self.by_stage.keys()) - set(PROTOCOL_STAGES)
        if invalid:
            raise ValueError(f"by_stage contains unknown stages: {sorted(invalid)}")
        e = sum(v[0] for v in self.by_stage.values())
        p = sum(v[1] for v in self.by_stage.values())
        a = sum(v[2] for v in self.by_stage.values())
        if (e, p, a) != (self.established, self.partial, self.absent):
            raise ValueError(
                f"by_stage sums ({e},{p},{a}) != "
                f"({self.established},{self.partial},{self.absent})"
            )

    @property
    def weighted_score_pct(self) -> float:
        """가중 준비도 점수 (%) — established 1.0·partial 0.5·absent 0.0."""
        if not self.total:
            return 0.0
        score = self.established * 1.0 + self.partial * 0.5
        return 100.0 * score / self.total

    @property
    def foundational_established_pct(self) -> float:
        """기반(필수) 요소 구비 비율 (%)."""
        if not self.foundational_total:
            return 0.0
        return 100.0 * self.foundational_established / self.foundational_total


@dataclass(frozen=True)
class ReadinessVerdict:
    """종합 일반화 프로토콜 준비도 판정 (정직성 결속 적용)."""

    verdict: str                    # READINESS_VERDICTS 중 하나
    foundational_established: int
    foundational_total: int
    weighted_score_pct: float
    rationale: str

    def __post_init__(self) -> None:
        if self.verdict not in READINESS_VERDICTS:
            raise ValueError(
                f"verdict must be one of {READINESS_VERDICTS}, got {self.verdict!r}"
            )
        if not self.rationale or not self.rationale.strip():
            raise ValueError("rationale must be a non-empty string")
        if self.foundational_established < 0 or self.foundational_total < 0:
            raise ValueError("counts must be non-negative")
        if self.foundational_established > self.foundational_total:
            raise ValueError("foundational_established cannot exceed foundational_total")
        # 어드바이저 MEDIUM: 점수는 의미상 [0, 100] 범위여야 한다(직접 생성 방어).
        if not (0.0 <= self.weighted_score_pct <= 100.0):
            raise ValueError(
                f"weighted_score_pct must be in [0, 100], got {self.weighted_score_pct}"
            )

    @property
    def is_ready(self) -> bool:
        """프로토콜이 평가 가능 수준으로 구비됐는지(PROTOCOL_READY)."""
        return self.verdict == PROTOCOL_READY


def find_requirement(requirement_id: str) -> ProtocolRequirement:
    """식별자로 요소를 조회한다. 없으면 KeyError."""
    for req in PROTOCOL_REQUIREMENTS:
        if req.requirement_id == requirement_id:
            return req
    raise KeyError(f"unknown protocol requirement: {requirement_id!r}")


def requirements_by_stage(stage: str) -> tuple[ProtocolRequirement, ...]:
    """프로토콜 단계에 속한 요소를 식별자 정렬로 반환한다."""
    if stage not in PROTOCOL_STAGES:
        raise ValueError(f"stage must be one of {PROTOCOL_STAGES}, got {stage!r}")
    return tuple(
        sorted((r for r in PROTOCOL_REQUIREMENTS if r.stage == stage),
               key=lambda r: r.requirement_id)
    )


def foundational_requirements() -> tuple[ProtocolRequirement, ...]:
    """기반(필수) 요소(foundational=True)를 식별자 정렬로 반환한다."""
    return tuple(
        sorted((r for r in PROTOCOL_REQUIREMENTS if r.foundational),
               key=lambda r: r.requirement_id)
    )


def absent_requirements() -> tuple[ProtocolRequirement, ...]:
    """부재(absent) 요소를 식별자 정렬로 반환한다."""
    return tuple(
        sorted((r for r in PROTOCOL_REQUIREMENTS if r.is_absent),
               key=lambda r: r.requirement_id)
    )


def requirements_by_status(status: str) -> tuple[ProtocolRequirement, ...]:
    """프로토콜 상태별 요소를 식별자 정렬로 반환한다."""
    if status not in PROTOCOL_STATUSES:
        raise ValueError(f"status must be one of {PROTOCOL_STATUSES}, got {status!r}")
    return tuple(
        sorted((r for r in PROTOCOL_REQUIREMENTS if r.status == status),
               key=lambda r: r.requirement_id)
    )


def protocol_report() -> ProtocolReport:
    """전체 프로토콜 준비도 현황을 집계한 결정적 리포트를 생성한다."""
    total = len(PROTOCOL_REQUIREMENTS)
    established = sum(1 for r in PROTOCOL_REQUIREMENTS if r.status == "established")
    partial = sum(1 for r in PROTOCOL_REQUIREMENTS if r.status == "partial")
    absent = sum(1 for r in PROTOCOL_REQUIREMENTS if r.status == "absent")
    foundational = [r for r in PROTOCOL_REQUIREMENTS if r.foundational]
    foundational_established = sum(1 for r in foundational if r.status == "established")
    by_stage: dict[str, tuple[int, int, int]] = {}
    for stage in PROTOCOL_STAGES:
        members = [r for r in PROTOCOL_REQUIREMENTS if r.stage == stage]
        by_stage[stage] = (
            sum(1 for r in members if r.status == "established"),
            sum(1 for r in members if r.status == "partial"),
            sum(1 for r in members if r.status == "absent"),
        )
    return ProtocolReport(
        total=total,
        established=established,
        partial=partial,
        absent=absent,
        foundational_total=len(foundational),
        foundational_established=foundational_established,
        by_stage=MappingProxyType(by_stage),
    )


def protocol_readiness() -> ReadinessVerdict:
    """종합 일반화 프로토콜 준비도를 정직성 결속 우선순위로 판정한다.

    정직성 결속(핵심): 기반(필수) 요소가 하나도 ``established`` 가 아니면 — 추적성 등
    비-기반 요소가 established 여도 — ``NO_PROTOCOL`` 로 고정한다. 갭을 *카탈로그* 한 것이
    갭을 *메운* 것으로 둔갑하지 못하게 막는다.
    """
    r = protocol_report()
    fe, ft = r.foundational_established, r.foundational_total
    if ft > 0 and fe == ft:
        verdict = PROTOCOL_READY
        rationale = (
            f"기반 요소 {fe}/{ft} 전부 구비 — 일반화 평가를 실행할 프로토콜이 갖춰짐 "
            "(정책의 실제 일반화 여부는 별개)"
        )
    elif fe > 0:
        verdict = PARTIAL_PROTOCOL
        rationale = (
            f"기반 요소 {fe}/{ft} 구비 — 평가 프로토콜이 부분적으로만 갖춰짐"
        )
    elif ft == 0:
        # 기반 요소가 정의되지 않은 가상 카탈로그 — 추적성 문구를 단정하지 않는다
        # (어드바이저 MEDIUM: rationale 이 실제 상태와 어긋나지 않도록).
        verdict = NO_PROTOCOL
        rationale = "기반(필수) 요소가 정의되지 않음 — 일반화 프로토콜 준비도 판정 불가"
    else:
        verdict = NO_PROTOCOL
        rationale = (
            f"기반 요소 {fe}/{ft} 구비 — 일반화 평가 프로토콜 부재. 현 established 항목은 "
            "갭 추적성뿐이며, 갭의 목록화는 갭의 해소가 아님(정직 공시)"
        )
    return ReadinessVerdict(
        verdict=verdict,
        foundational_established=fe,
        foundational_total=ft,
        weighted_score_pct=r.weighted_score_pct,
        rationale=rationale,
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
            "foundational": r.foundational,
            "status": r.status,
            "evidence": r.evidence,
            "summary": r.summary,
        })
        for r in ordered
    )


_STATUS_MARK: dict[str, str] = {"established": "✓", "partial": "◐", "absent": "✗(부재)"}


def _format_matrix() -> str:
    lines = ["RL 일반화 평가 프로토콜 적합성 매트릭스", ""]
    for row in protocol_matrix():
        mark = _STATUS_MARK[str(row["status"])]
        kind = "기반" if row["foundational"] else "권장"
        evidence = row["evidence"] or "—"
        lines.append(
            f"[{row['stage']:24}] {mark:7} {kind} {row['anchor']} {row['name']}"
        )
        lines.append(f"      → {evidence}")
    return "\n".join(lines)


def _format_report() -> str:
    r = protocol_report()
    v = protocol_readiness()
    lines = [
        "RL 일반화 평가 프로토콜 준비도 요약",
        "",
        f"종합 판정   : {v.verdict} — {v.rationale}",
        f"가중 점수   : {r.weighted_score_pct:.0f}% "
        f"(구비 {r.established} · 부분 {r.partial} · 부재 {r.absent} / 총 {r.total})",
        f"기반 요소   : {r.foundational_established}/{r.foundational_total} 구비 "
        f"({r.foundational_established_pct:.0f}%)",
        "",
        "프로토콜 단계별 (구비/부분/부재):",
    ]
    for stage in PROTOCOL_STAGES:
        e, p, a = r.by_stage[stage]
        lines.append(f"  {_STAGE_NAMES[stage]:46}: {e}/{p}/{a}")
    lines.append("")
    lines.append(
        "정직 공시: 일반화 평가 프로토콜은 451-460 트랙의 미해결 프런티어다. 낮은 점수는"
    )
    lines.append(
        "  결함이 아니라 인증 가능 ML 경로의 현 위치를 정직하게 보고하는 것이다."
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="RL 일반화 평가 프로토콜 적합성 게이트 (ODYSSEY Phase 452)"
    )
    parser.add_argument("--matrix", action="store_true", help="전체 프로토콜 매트릭스 출력")
    parser.add_argument("--report", action="store_true", help="준비도 요약 출력")
    parser.add_argument("--stage", choices=PROTOCOL_STAGES, help="단계별 요소 출력")
    parser.add_argument("--absent", action="store_true", help="부재(absent) 요소 출력")
    parser.add_argument("--foundational", action="store_true", help="기반(필수) 요소 출력")
    parser.add_argument("--verdict", action="store_true", help="종합 준비도 판정 출력")
    args = parser.parse_args(argv)

    if args.matrix:
        print(_format_matrix())
    elif args.report:
        print(_format_report())
    elif args.stage:
        for req in requirements_by_stage(args.stage):
            print(f"{req.requirement_id} [{req.status}]: {req.name} — {req.summary}")
    elif args.absent:
        for req in absent_requirements():
            print(f"[{req.stage}] {req.anchor} {req.name}: {req.summary}")
    elif args.foundational:
        for req in foundational_requirements():
            print(f"{_STATUS_MARK[req.status]} {req.anchor} {req.name} → {req.evidence or '—'}")
    elif args.verdict:
        v = protocol_readiness()
        print(f"{v.verdict} ({v.foundational_established}/{v.foundational_total} 기반 구비)")
        print(f"  {v.rationale}")
    else:
        print(_format_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
