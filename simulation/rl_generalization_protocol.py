"""ODYSSEY Phase 452 — RL 일반화(미학습 시나리오 전이) 평가 프로토콜 적합성 게이트.

🔬 Formal & Research Frontier 트랙(451-460)의 두 번째 모듈. Phase 451
(``easa_ai_conformance``)이 SDACS 의 ML 자산을 EASA 신뢰 가능 AI 축으로 평가하며
**핵심 갭**으로 지목한 ``LA:LM-03`` "미학습 시나리오 전이(일반화) 검증 프로토콜
부재" 를 정면으로 다룬다. 본 모듈은 그 갭을 *메우는* 것이 아니라(실 학습·전이
실험은 GPU·연구 일정 의존) — RL 정책이 "학습하지 않은 시나리오로 일반화된다" 는
**주장을 방어 가능하게** 하려면 어떤 평가 프로토콜 요건이 충족돼야 하는지를
결정적 게이트로 명문화하고, SDACS 의 현 자산을 그 요건에 *정직하게* 비춘다.

Phase 451 이 "*무엇이* 빠졌는가" 를 빌딩 블록 단위로 답했다면, 본 모듈은 그중 한
갭(일반화 검증)을 *어떻게 채워야 방어 가능한가* 를 요건 단위로 답한다 — 즉 451 은
진단, 452 는 그 진단 한 항목에 대한 *합격 기준 명세*다.

설계 원칙
--------
- **자문이지 집행 아님**: 본 모듈은 전이 주장 방어가능성을 *판정만* 하며 어떤
  파일도 변경하지 않고 어떤 모델도 학습·평가하지 않는다(부수효과 0).
- **요건의 근거는 권위 있는 출처**: 요건은 추측이 아니라 EASA Learning Assurance
  W-shaped 프로세스(독립 데이터 학습 검증)·강화학습 재현성 문헌(Henderson et al.,
  *Deep RL that Matters*, 2018)·도메인 무작위화/Sim-to-Real 전이 문헌(Tobin et al.
  2017; Peng et al. 2018)·공변량 변화 정량화에서 도출하고 명문 근거를 결속한다.
- **정직성 결속(증거 ⟺ 충족)**: ``MET``/``PARTIAL`` 요건은 반드시 리포에 실재하는
  증거 경로를 인용하고, ``UNMET``/``N/A`` 는 증거를 인용하지 못한다(근거 없는
  충족 주장을 구조적으로 금지 — 테스트가 디스크 실재를 강제).
- **정직한 자가 공시**: ``shipped_protocol`` 은 현 RL 자산을 *격상 없이* 판정한다.
  SDACS 의 RL 은 연구 수준이라 다수 필수 요건이 미충족이며, 현 판정은
  ``NOT_DEFENSIBLE`` 이다 — 낮은 점수는 결함이 아니라 인증 경로상 현 위치의 정직한
  보고이며, 안전은 RL 의 일반화가 아니라 결정적 안전망이 보장한다.

판정 우선순위(``assess``)
------------------------
1. CRITICAL 요건이 하나라도 UNMET → ``NOT_DEFENSIBLE``
2. CRITICAL 요건이 하나라도 PARTIAL → ``EVIDENCE_INSUFFICIENT``
3. (비-CRITICAL 포함) UNMET 또는 PARTIAL 이 남으면 → ``EVIDENCE_INSUFFICIENT``
4. 그 외(전부 MET 또는 N/A) → ``TRANSFER_CLAIM_DEFENSIBLE``

알 수 없는 상태 값은 sentinel 로 흡수하지 않고 ``ValueError`` 로 즉시 거부한다
(결정성·정직성 우선). 판정 결과는 위 3개 verdict 로 닫혀 있다.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python -m simulation.rl_generalization_protocol --requirements  # 요건 목록
    python -m simulation.rl_generalization_protocol --status        # 현 자산 판정
    python -m simulation.rl_generalization_protocol --gaps          # 미충족 요건
    python -m simulation.rl_generalization_protocol --policy        # 결정 매트릭스
    python -m simulation.rl_generalization_protocol --manifest      # 매니페스트(JSON)
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

# 리포 루트 — 증거 경로는 이 기준의 상대 경로로 보관한다.
_REPO_ROOT = Path(__file__).resolve().parent.parent

# --- 평가 차원(분류 축, 평가 흐름 순서) -----------------------------------
PROTOCOL_DIMENSIONS: tuple[str, ...] = (
    "data_partitioning",     # 학습/평가 시나리오 분리
    "distribution_coverage", # 미학습 분포 커버리지·변화 정량화
    "statistical_rigor",     # 시드·유의성·신뢰구간
    "baseline_ablation",     # 비-ML 기준·구성요소 제거 실험
    "reproducibility",       # 재현성(시드·설정·산출물)
    "safety_bounding",       # 전이 실패의 안전 한정
)

_DIMENSION_NAMES: Mapping[str, str] = MappingProxyType({
    "data_partitioning": "데이터 분할 (학습/미학습 시나리오 분리)",
    "distribution_coverage": "분포 커버리지 (미학습 ODD·공변량 변화 정량화)",
    "statistical_rigor": "통계적 엄밀성 (다중 시드·유의성·신뢰구간)",
    "baseline_ablation": "기준·제거 실험 (결정적 baseline 대비·ablation)",
    "reproducibility": "재현성 (시드·설정·산출물 추적)",
    "safety_bounding": "안전 한정 (전이 실패의 안전 영향 차단)",
})

# --- 요건 충족 상태(순서형) ------------------------------------------------
STATE_MET = "MET"                  # 요건을 완전히 충족
STATE_PARTIAL = "PARTIAL"          # 부분 충족(보강 필요)
STATE_UNMET = "UNMET"              # 미충족
STATE_NOT_APPLICABLE = "N/A"       # 본 평가에 비적용(게이트·분모에서 제외)

# 점수 가중치. N/A 는 분모에서 제외하므로 여기 없다.
_STATE_WEIGHT: Mapping[str, float] = MappingProxyType({
    STATE_MET: 1.0,
    STATE_PARTIAL: 0.5,
    STATE_UNMET: 0.0,
})
_KNOWN_STATES: frozenset[str] = frozenset(
    {STATE_MET, STATE_PARTIAL, STATE_UNMET, STATE_NOT_APPLICABLE}
)
# 증거를 인용할 수 있는(인용해야 하는) 상태 — MET·PARTIAL 만.
_EVIDENCE_STATES: frozenset[str] = frozenset({STATE_MET, STATE_PARTIAL})

# --- 게이트 판정 ----------------------------------------------------------
VERDICT_DEFENSIBLE = "TRANSFER_CLAIM_DEFENSIBLE"
VERDICT_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"
VERDICT_NOT_DEFENSIBLE = "NOT_DEFENSIBLE"


@dataclass(frozen=True)
class ProtocolRequirement:
    """일반화 평가 프로토콜 요건 한 건(불변).

    Attributes:
        requirement_id: 안정 식별자 (RG-01..).
        name: 요건 이름.
        dimension: 평가 차원(PROTOCOL_DIMENSIONS 중 하나).
        basis: 명문 근거(권위 있는 출처·원칙).
        critical: 미충족 시 전이 주장이 방어 불가가 되는 필수 요건 여부.
        description: 요건이 요구하는 바.
    """

    requirement_id: str
    name: str
    dimension: str
    basis: str
    critical: bool
    description: str

    def __post_init__(self) -> None:
        if not self.requirement_id or self.requirement_id != self.requirement_id.strip():
            raise ValueError("requirement_id must be non-empty and unpadded")
        if " " in self.requirement_id:
            raise ValueError("requirement_id must not contain internal spaces")
        if not self.name or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        if self.dimension not in PROTOCOL_DIMENSIONS:
            raise ValueError(
                f"dimension must be one of {PROTOCOL_DIMENSIONS}, got {self.dimension!r}"
            )
        if not self.basis or not self.basis.strip():
            raise ValueError("basis must be a non-empty string")
        if not isinstance(self.critical, bool):
            raise TypeError(f"critical must be bool, got {type(self.critical).__name__}")
        if not self.description or not self.description.strip():
            raise ValueError("description must be a non-empty string")


# 일반화 평가 프로토콜 요건 레지스트리 — 결정적 순서.
# EASA LA W-shaped 검증 · Henderson 2018(RL 재현성) · Tobin/Peng(Sim-to-Real DR) 근거.
REQUIREMENTS: tuple[ProtocolRequirement, ...] = (
    # --- data_partitioning --------------------------------------------------
    ProtocolRequirement(
        "RG-01", "미학습 시나리오 분리(held-out split)",
        "data_partitioning",
        "EASA Learning Assurance — 독립 데이터에 의한 학습 프로세스 검증(LA:LM-03)",
        True,
        "학습에 사용하지 않은 시나리오 집합을 사전에 분리하고, 전이 평가는 그 위에서만 수행.",
    ),
    ProtocolRequirement(
        "RG-02", "데이터 누수 차단(leakage control)",
        "data_partitioning",
        "ML 평가 일반 원칙 — 학습/평가 분포 오염 금지",
        True,
        "지형·풍속장·시드 등 학습 신호가 평가 시나리오에 새지 않음을 추적 가능하게 보증.",
    ),
    # --- distribution_coverage ---------------------------------------------
    ProtocolRequirement(
        "RG-03", "미학습 ODD 커버리지 정량화",
        "distribution_coverage",
        "EASA ODD 완전성 · Sim-to-Real 운용 영역 정의",
        True,
        "평가 시나리오가 운용 설계 영역(드론 수·고도·풍속) 중 어느 영역을 덮는지 정량 보고.",
    ),
    ProtocolRequirement(
        "RG-04", "공변량 변화(distribution shift) 측정",
        "distribution_coverage",
        "Quiñonero-Candela et al. — dataset shift 정량화",
        False,
        "학습 분포 대비 평가 분포의 변화량을 정량 지표로 측정해 전이 난이도를 표면화.",
    ),
    # --- statistical_rigor --------------------------------------------------
    ProtocolRequirement(
        "RG-05", "다중 시드 평가",
        "statistical_rigor",
        "Henderson et al. 2018, *Deep RL that Matters* — 시드 분산 보고",
        True,
        "단일 시드 결과를 일반화로 주장하지 않도록 독립 시드 다수로 전이 성능 분포를 평가.",
    ),
    ProtocolRequirement(
        "RG-06", "통계적 유의성 검정",
        "statistical_rigor",
        "Henderson et al. 2018 — baseline 대비 유의성",
        True,
        "전이 성능이 기준 대비 우연이 아님을 유의성 검정으로 확인.",
    ),
    ProtocolRequirement(
        "RG-07", "신뢰구간 보고",
        "statistical_rigor",
        "실험 보고 모범관행 — 점추정 단독 금지",
        False,
        "전이 성능 지표를 점추정이 아니라 신뢰구간과 함께 보고.",
    ),
    # --- baseline_ablation --------------------------------------------------
    ProtocolRequirement(
        "RG-08", "결정적 baseline 대비",
        "baseline_ablation",
        "비-ML 기준 대비 — RL 우월성 입증 책임",
        True,
        "RL 정책의 전이 성능을 결정적 APF+CBS baseline 과 동일 시나리오에서 직접 비교.",
    ),
    ProtocolRequirement(
        "RG-09", "구성요소 제거 실험(ablation)",
        "baseline_ablation",
        "ablation study — 일반화 기여 요인 분해",
        False,
        "도메인 무작위화 등 일반화 기여 구성요소를 제거해 각 기여를 분해.",
    ),
    # --- reproducibility ----------------------------------------------------
    ProtocolRequirement(
        "RG-10", "시드 통제(결정적 RNG)",
        "reproducibility",
        "재현성 — 시드 고정 RNG (CLAUDE.md: np.random.default_rng(seed))",
        True,
        "학습·평가 무작위성을 시드 고정 RNG 로 통제해 동일 시드 동일 결과를 보증.",
    ),
    ProtocolRequirement(
        "RG-11", "설정·산출물 캡처",
        "reproducibility",
        "ML 재현성 체크리스트 — 설정/산출물 버전 보존",
        False,
        "학습 하이퍼파라미터·환경 설정·평가 산출물을 추적 가능하게 보존.",
    ),
    # --- safety_bounding ----------------------------------------------------
    ProtocolRequirement(
        "RG-12", "자문 한정 권한(전이 실패 안전 차단)",
        "safety_bounding",
        "SDACS 아키텍처 — RL 자문, 결정적 안전망이 최종 권한",
        True,
        "전이 실패(미학습 분포에서의 오작동)가 안전-크리티컬 결정으로 이어지지 않도록 한정.",
    ),
    ProtocolRequirement(
        "RG-13", "런타임 영역 이탈 감시",
        "safety_bounding",
        "런타임 모니터링 — 분포 외(OOD) 입력 탐지",
        False,
        "운용 중 평가 영역을 벗어난 입력을 탐지해 자문 신뢰도를 동적으로 낮춤.",
    ),
)
_REQUIREMENT_INDEX = {r.requirement_id: r for r in REQUIREMENTS}
assert len(_REQUIREMENT_INDEX) == len(REQUIREMENTS), "duplicate requirement_id in REQUIREMENTS"


@dataclass(frozen=True)
class RequirementState:
    """현 자산의 요건 충족 상태와 증거(불변).

    정직성 결속: MET/PARTIAL 은 반드시 증거 경로를 인용하고, UNMET/N/A 는 증거를
    인용하지 못한다(근거 없는 충족 주장 구조적 금지).
    """

    requirement_id: str
    state: str
    evidence: str | None
    rationale: str

    def __post_init__(self) -> None:
        if self.requirement_id not in _REQUIREMENT_INDEX:
            raise KeyError(f"unknown requirement_id: {self.requirement_id!r}")
        if self.state not in _KNOWN_STATES:
            raise ValueError(
                f"{self.requirement_id}: unknown state {self.state!r} "
                f"(allowed: {', '.join(sorted(_KNOWN_STATES))})"
            )
        if not self.rationale or not self.rationale.strip():
            raise ValueError("rationale must be a non-empty string")
        if self.state in _EVIDENCE_STATES:
            if self.evidence is None or not self.evidence.strip():
                raise ValueError(
                    f"{self.requirement_id}: state {self.state} must cite a non-empty evidence path"
                )
        else:
            if self.evidence is not None:
                raise ValueError(
                    f"{self.requirement_id}: state {self.state} must not cite evidence"
                )


@dataclass(frozen=True)
class ProtocolAssessment:
    """일반화 평가 프로토콜 방어가능성 판정 결과(불변)."""

    verdict: str
    score: float
    state_by_requirement: Mapping[str, str]
    blocking: tuple[str, ...]   # verdict 를 유발한 요건 id
    notes: tuple[str, ...]

    def summary(self) -> str:
        """사람이 읽는 한 줄 요약."""
        pct = round(self.score * 100, 1)
        base = f"{self.verdict} ({pct}%)"
        if self.blocking:
            base += f" — 결격 {len(self.blocking)}건: {', '.join(self.blocking)}"
        return base


def all_requirements() -> tuple[ProtocolRequirement, ...]:
    """결정적 순서의 전체 요건 목록."""
    return REQUIREMENTS


def get_requirement(requirement_id: str) -> ProtocolRequirement:
    """식별자로 요건을 조회한다.

    Raises:
        KeyError: 알 수 없는 식별자.
    """
    try:
        return _REQUIREMENT_INDEX[requirement_id]
    except KeyError:
        raise KeyError(f"unknown requirement_id: {requirement_id!r}") from None


def requirements_by_dimension(dimension: str) -> tuple[ProtocolRequirement, ...]:
    """차원에 속한 요건을 식별자 정렬로 반환한다."""
    if dimension not in PROTOCOL_DIMENSIONS:
        raise ValueError(
            f"dimension must be one of {PROTOCOL_DIMENSIONS}, got {dimension!r}"
        )
    return tuple(
        sorted((r for r in REQUIREMENTS if r.dimension == dimension),
               key=lambda r: r.requirement_id)
    )


def _normalize(states: Mapping[str, str]) -> dict[str, str]:
    """요건 상태를 전체 요건에 대해 정규화한다(미지정 요건은 보수적으로 UNMET).

    Raises:
        KeyError: 레지스트리에 없는 요건 id.
        ValueError: 알 수 없는 상태 값.
    """
    for rid, state in states.items():
        if rid not in _REQUIREMENT_INDEX:
            raise KeyError(f"unknown requirement id: {rid!r}")
        if state not in _KNOWN_STATES:
            raise ValueError(
                f"{rid}: unknown state {state!r} "
                f"(allowed: {', '.join(sorted(_KNOWN_STATES))})"
            )
    return {r.requirement_id: states.get(r.requirement_id, STATE_UNMET) for r in REQUIREMENTS}


def assess(states: Mapping[str, str]) -> ProtocolAssessment:
    """요건 상태를 받아 전이 주장 방어가능성을 결정적으로 판정한다.

    판정 우선순위는 모듈 docstring 의 1-4 단계를 따른다.

    Args:
        states: 요건 id → 상태 매핑. 미지정 요건은 UNMET 으로 간주.
    """
    normalized = _normalize(states)

    # 점수: N/A 제외, 가중 평균. 전부 N/A 면 적용 요건이 전부 만족된 공허참 → 1.0.
    weighted = 0.0
    denom = 0
    for state in normalized.values():
        if state == STATE_NOT_APPLICABLE:
            continue
        denom += 1
        weighted += _STATE_WEIGHT[state]
    score = weighted / denom if denom else 1.0

    critical_unmet: list[str] = []
    critical_partial: list[str] = []
    other_incomplete: list[str] = []
    notes: list[str] = []

    for rid, state in normalized.items():
        req = _REQUIREMENT_INDEX[rid]
        if state == STATE_NOT_APPLICABLE:
            notes.append(f"{rid}: 비적용 — 게이트 제외")
            continue
        if state == STATE_MET:
            continue
        if req.critical and state == STATE_UNMET:
            critical_unmet.append(rid)
        elif req.critical and state == STATE_PARTIAL:
            critical_partial.append(rid)
        else:
            other_incomplete.append(rid)

    if critical_unmet:
        verdict = VERDICT_NOT_DEFENSIBLE
        blocking = tuple(critical_unmet)
    elif critical_partial:
        verdict = VERDICT_INSUFFICIENT
        blocking = tuple(critical_partial)
    elif other_incomplete:
        verdict = VERDICT_INSUFFICIENT
        blocking = tuple(other_incomplete)
    else:
        verdict = VERDICT_DEFENSIBLE
        blocking = ()

    return ProtocolAssessment(
        verdict=verdict,
        score=round(score, 4),
        state_by_requirement=MappingProxyType(dict(normalized)),
        blocking=blocking,
        notes=tuple(notes),
    )


# --- 결정 매트릭스(테스트가 assess 와 일치를 강제) -------------------------
# (worst_critical_state, has_other_incomplete) → verdict.
# worst_critical_state 는 CRITICAL 요건 중 최악(UNMET > PARTIAL > MET/N/A 순).
# CRITICAL 요건이 모두 N/A 인 경우 worst_critical_state 를 MET 와 동일하게 취급한다
# (N/A 는 게이트에서 제외되므로 별도 행 없이 (STATE_MET, ...) 행이 그 경우를 덮는다).
POLICY_MATRIX: tuple[tuple[str, bool, str], ...] = (
    (STATE_UNMET, True, VERDICT_NOT_DEFENSIBLE),
    (STATE_UNMET, False, VERDICT_NOT_DEFENSIBLE),
    (STATE_PARTIAL, True, VERDICT_INSUFFICIENT),
    (STATE_PARTIAL, False, VERDICT_INSUFFICIENT),
    (STATE_MET, True, VERDICT_INSUFFICIENT),
    (STATE_MET, False, VERDICT_DEFENSIBLE),
)


# --- 현 리포의 RL 일반화 자산(정직한 자가 공시) ---------------------------
# SDACS 의 RL 은 연구 수준이다. 격상 없이 현 자산 상태를 그대로 반영한다.
# MET/PARTIAL 은 실재 증거 경로를 인용(테스트가 디스크 실재 강제), UNMET 은 증거 없음.
SHIPPED: tuple[RequirementState, ...] = (
    RequirementState(
        "RG-01", STATE_PARTIAL, "config/scenario_params",
        "9개 시나리오 정의가 held-out 분리를 가능케 하나, 문서화된 학습/평가 분할 프로토콜 미수립.",
    ),
    RequirementState(
        "RG-02", STATE_UNMET, None,
        "학습/평가 분포 누수를 추적·차단하는 프로토콜 부재.",
    ),
    RequirementState(
        "RG-03", STATE_PARTIAL, "src/training/domain_rand.py",
        "도메인 무작위화가 학습 분포를 넓히나, 평가 ODD 커버리지의 정량 보고는 미수립.",
    ),
    RequirementState(
        "RG-04", STATE_PARTIAL, "src/training/sim_real_gap.py",
        "Sim-to-Real 격차 추정기가 분포 차이를 다루나, 학습-평가 공변량 변화 지표는 미형식화.",
    ),
    RequirementState(
        "RG-05", STATE_UNMET, None,
        "독립 다중 시드로 전이 성능 분포를 평가한 실험 부재.",
    ),
    RequirementState(
        "RG-06", STATE_UNMET, None,
        "전이 성능의 baseline 대비 통계적 유의성 검정 부재.",
    ),
    RequirementState(
        "RG-07", STATE_UNMET, None,
        "전이 지표의 신뢰구간 보고 부재.",
    ),
    RequirementState(
        "RG-08", STATE_PARTIAL, "simulation/path_deconflict.py",
        "결정적 APF+CBS baseline 이 실재해 대비 가능하나, 동일 시나리오 head-to-head 전이 비교 미실행.",
    ),
    RequirementState(
        "RG-09", STATE_UNMET, None,
        "일반화 기여 구성요소 제거 실험(ablation) 부재.",
    ),
    RequirementState(
        "RG-10", STATE_MET, "src/training/domain_rand.py",
        "시드 고정 RNG(np.random.default_rng) 가 프로젝트 전반에 강제되어 동일 시드 동일 결과 보증.",
    ),
    RequirementState(
        "RG-11", STATE_PARTIAL, "config/default_simulation.yaml",
        "환경 설정은 캡처되나, 학습 산출물·하이퍼파라미터의 per-run 버전 추적은 부재.",
    ),
    RequirementState(
        "RG-12", STATE_MET, "simulation/emergency_protocol.py",
        "5계층 안전망·비상 프로토콜이 안전-결정권 보유 — RL 전이 실패가 안전-크리티컬 결정으로 이어지지 않음.",
    ),
    RequirementState(
        "RG-13", STATE_PARTIAL, "simulation/compliance_checker.py",
        "런타임 적합성 감시가 계획 이탈을 탐지하나, RL 전용 분포 외(OOD) 탐지기는 부재.",
    ),
)
_SHIPPED_INDEX = {s.requirement_id: s for s in SHIPPED}
assert len(_SHIPPED_INDEX) == len(SHIPPED), "duplicate requirement_id in SHIPPED"
assert set(_SHIPPED_INDEX) == set(_REQUIREMENT_INDEX), "SHIPPED must cover every requirement exactly once"


def shipped_states() -> Mapping[str, str]:
    """현 자산의 요건별 상태 매핑(읽기 전용)."""
    return MappingProxyType({s.requirement_id: s.state for s in SHIPPED})


def shipped_protocol() -> ProtocolAssessment:
    """현 리포의 RL 일반화 자산 판정(정직한 자가 공시)."""
    return assess(shipped_states())


def gaps() -> tuple[RequirementState, ...]:
    """미충족(UNMET) 요건을 식별자 정렬로 반환한다."""
    return tuple(
        sorted((s for s in SHIPPED if s.state == STATE_UNMET),
               key=lambda s: s.requirement_id)
    )


def manifest() -> dict[str, Any]:
    """JSON 직렬화 가능한 매니페스트(요건 + 현 자산 판정)."""
    a = shipped_protocol()
    return {
        "schema": "sdacs-rl-generalization-protocol",
        "version": "1.0",
        "phase": 452,
        "requirements": [
            {
                "requirement_id": r.requirement_id,
                "name": r.name,
                "dimension": r.dimension,
                "basis": r.basis,
                "critical": r.critical,
                "description": r.description,
            }
            for r in REQUIREMENTS
        ],
        "shipped": {
            "verdict": a.verdict,
            "score": a.score,
            "state_by_requirement": dict(a.state_by_requirement),
            "evidence": {s.requirement_id: s.evidence for s in SHIPPED},
            "blocking": list(a.blocking),
            "notes": list(a.notes),
        },
    }


_STATE_MARK: Mapping[str, str] = MappingProxyType({
    STATE_MET: "✓", STATE_PARTIAL: "◐", STATE_UNMET: "✗", STATE_NOT_APPLICABLE: "–",
})


def _cmd_requirements() -> None:
    print(f"RL 일반화 평가 프로토콜 요건 — {len(REQUIREMENTS)}건")
    for dim in PROTOCOL_DIMENSIONS:
        print(f"\n[{_DIMENSION_NAMES[dim]}]")
        for r in requirements_by_dimension(dim):
            mark = "●" if r.critical else "○"
            print(f"  {mark} {r.requirement_id} {r.name}  ({r.basis})")


def _cmd_status() -> None:
    a = shipped_protocol()
    print("RL 일반화(미학습 시나리오 전이) 평가 프로토콜 — 현 자산 판정")
    for dim in PROTOCOL_DIMENSIONS:
        print(f"\n[{_DIMENSION_NAMES[dim]}]")
        for r in requirements_by_dimension(dim):
            s = _SHIPPED_INDEX[r.requirement_id]
            mark = "●" if r.critical else "○"
            module = s.evidence or "—"
            print(f"  {mark} {_STATE_MARK[s.state]} {r.requirement_id} {r.name:<26} → {module}")
    print(f"\n{a.summary()}")
    print("정직 공시: SDACS 의 RL 은 연구 수준이다. 낮은 점수는 결함이 아니라 인증 경로상")
    print("  현 위치의 정직한 보고이며, 안전은 RL 일반화가 아닌 결정적 안전망이 보장한다.")


def _cmd_gaps() -> None:
    g = gaps()
    print(f"미충족(UNMET) 요건 — {len(g)}건")
    for s in g:
        r = _REQUIREMENT_INDEX[s.requirement_id]
        crit = "필수" if r.critical else "권장"
        print(f"  ✗ {s.requirement_id} [{crit}] {r.name}: {s.rationale}")


def _cmd_policy() -> None:
    print("결정 매트릭스 (worst_critical_state, has_other_incomplete) → verdict")
    for worst, other, verdict in POLICY_MATRIX:
        print(f"  ({worst:<8}, other={str(other):<5}) → {verdict}")


_KNOWN_FLAGS: tuple[str, ...] = (
    "--requirements", "--status", "--gaps", "--policy", "--manifest",
)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    unknown = [a for a in args if a not in _KNOWN_FLAGS]
    if unknown:
        print(f"알 수 없는 인자: {' '.join(unknown)}", file=sys.stderr)
        print(f"사용법: {' | '.join(_KNOWN_FLAGS)}", file=sys.stderr)
        return 2
    if "--requirements" in args:
        _cmd_requirements()
        return 0
    if "--status" in args:
        _cmd_status()
        return 0
    if "--gaps" in args:
        _cmd_gaps()
        return 0
    if "--policy" in args:
        _cmd_policy()
        return 0
    if "--manifest" in args:
        print(json.dumps(manifest(), ensure_ascii=False, indent=2))
        return 0
    _cmd_status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
