"""ODYSSEY Phase 451 — EASA 신뢰 가능 AI(Learning Assurance) 적합성 자가 평가.

SDACS 의 *학습 기반(ML)* 구성요소(강화학습 충돌 회피·도메인 무작위화·궤적 예측 등)가
EASA 가 제시한 신뢰 가능 AI 프레임워크의 목표를 어디까지 충족하는가를 결정적으로 평가하는
적합성 매트릭스다. ODYSSEY Track 🔬 Formal & Research Frontier(451-460, "RL 일반화 연구 +
인증 가능 ML 조사")의 착수 모듈로, "SDACS 의 ML 자산을 항공 인증 경로에 올리려면 *무엇이
빠져 있는가*" 를 객관적으로 답하기 위한 기준선이다. Phase 407(`icao_utm_conformance`)이
*시스템 운영* 역량을 ICAO 축으로 평가하는 자매편이라면, 본 모듈은 *학습 구성요소* 를 EASA
AI 축으로 평가한다.

근거 (권위 있는 출처)
--------------------
- **EASA Concept Paper — "Guidance for Level 1 & 2 machine learning applications"**
  (Issue 02, 2024). 신뢰 가능 AI 의 빌딩 블록(trustworthiness building blocks)으로
  *AI 신뢰성 분석·러닝 어슈어런스(W-shaped process)·AI 설명가능성·AI 안전 위험 완화·
  인적 요소(Level 2 human-AI teaming)·윤리 기반 평가* 를 제시한다. 본 모듈은 이 6개
  블록을 분류 축(building block)으로 삼는다.
- **EASA Artificial Intelligence Roadmap 2.0** (2023) — Learning Assurance 의
  W-shaped 개발·검증 단계(데이터 관리·학습 프로세스 관리·모델 훈련·학습 프로세스 검증·
  모델 구현·추론 모델 검증)를 본 모듈의 러닝 어슈어런스 목표 세분화에 차용한다.

정직 공시 (CLAUDE.md)
--------------------
1. 본 모듈은 *기능적 자가 평가* 이며 EASA 공식 적합성 인증이 아니다. 목표 세분화와
   ``anchor`` 토큰은 SDACS 의 해석이며 EASA 문서의 정확한 목표 번호를 복제하지 않는다.
2. ``status`` 는 3값(``conformant``·``partial``·``gap``)이다. SDACS 의 ML 은 *연구
   수준* 이므로 본 평가는 의도적으로 보수적이다 — 충족 주장보다 *미충족(갭)의 가시화* 에
   가치가 있다. 가중 점수가 낮은 것이 곧 정직함이다.
3. ``sdacs_module`` 은 목표를 *실제로* 떠받치는 리포 내 모듈/산출물 경로다. ``status``
   가 ``gap`` 이면 반드시 ``None`` 이고, 그 외(``conformant``/``partial``)면 반드시
   실재 경로를 인용한다 — 근거 없는 충족 주장을 구조적으로 금지한다(테스트가 디스크
   실재를 강제).
4. SDACS 의 *진짜 강점* 은 러닝 어슈어런스가 아니라 **AI 안전 위험 완화** 에 있다:
   ML(RL) 은 항상 *자문* 이고, 안전-결정권은 결정적 APF+CBS 5계층 안전망이 보유한다.
   즉 SDACS 는 "ML 을 안전-크리티컬 결정에 신뢰하지 않음" 으로써 위험을 완화한다 —
   이 아키텍처 선택이 본 매트릭스에서 유일하게 ``conformant`` 인 항목들의 근거다.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/easa_ai_conformance.py --matrix          # 전체 적합성 매트릭스
    python simulation/easa_ai_conformance.py --report          # 적합성 요약
    python simulation/easa_ai_conformance.py --block learning_assurance  # 블록별 목표
    python simulation/easa_ai_conformance.py --gaps            # 미충족(갭) 목표
    python simulation/easa_ai_conformance.py --foundational    # 기반(필수) 목표
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

# EASA 신뢰 가능 AI 빌딩 블록 (분류 축, Concept Paper 제시 순서).
BUILDING_BLOCKS: tuple[str, ...] = (
    "trustworthiness_analysis",
    "learning_assurance",
    "explainability",
    "human_factors",
    "safety_risk_mitigation",
    "ethics_assessment",
)

_BLOCK_NAMES: dict[str, str] = {
    "trustworthiness_analysis": "Trustworthiness analysis (AI 특성화·분류·ODD)",
    "learning_assurance": "Learning assurance (W-shaped 데이터·학습·검증)",
    "explainability": "AI explainability (설명가능성)",
    "human_factors": "Human factors (인적 요소·human-AI teaming)",
    "safety_risk_mitigation": "AI safety risk mitigation (안전 위험 완화)",
    "ethics_assessment": "Ethics-based assessment (윤리 기반 평가)",
}

# 적합성 상태 (3값). conformant=완전, partial=부분, gap=미충족.
CONFORMANCE_STATUSES: tuple[str, ...] = ("conformant", "partial", "gap")

# 가중 점수: 완전 1.0, 부분 0.5, 미충족 0.0.
_STATUS_WEIGHT: dict[str, float] = {"conformant": 1.0, "partial": 0.5, "gap": 0.0}


@dataclass(frozen=True)
class AIObjective:
    """단일 EASA 신뢰 가능 AI 목표와 SDACS 대응의 정의."""

    objective_id: str           # 안정 식별자 (예: 'data_management')
    name: str                   # 목표 명칭
    building_block: str         # 신뢰성 빌딩 블록
    anchor: str                 # EASA 목표 계열 참조 토큰 (SDACS 해석, 예: 'LA:DM')
    foundational: bool          # 어떤 ML 인증에도 필수인 기반 목표 여부
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
        if self.building_block not in BUILDING_BLOCKS:
            raise ValueError(
                f"building_block must be one of {BUILDING_BLOCKS}, got {self.building_block!r}"
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


# EASA 신뢰 가능 AI 목표 카탈로그 ↔ SDACS 자산 매핑 (정본).
# sdacs_module 경로는 리포에 실재하는 모듈/산출물 — 미대응(gap)은 None.
# SDACS 의 ML 은 연구 수준이므로 본 매핑은 의도적으로 보수적이다(정직성 > 점수).
AI_OBJECTIVES: tuple[AIObjective, ...] = (
    # --- trustworthiness_analysis -------------------------------------------
    AIObjective(
        "ai_characterisation", "AI/ML constituent characterisation",
        "trustworthiness_analysis", "TA:CO-01", True,
        "partial", "src/rl/ppo_collision.py",
        "ML 구성요소(PPO 충돌 회피) 실재 + 역할(자문) 정의 — 형식 특성화 문서는 부재(부분)",
    ),
    AIObjective(
        "ml_application_classification", "ML application Level classification (1/2/3)",
        "trustworthiness_analysis", "TA:CL-01", True,
        "gap", None,
        "EASA Level 1A/1B/2/3 분류 기록 없음 — 인증 경로 진입 전제 미충족 (갭)",
    ),
    AIObjective(
        "odd_definition", "Operational Design Domain (ODD) definition",
        "trustworthiness_analysis", "TA:CO-02", False,
        "partial", "config/default_simulation.yaml",
        "운용 envelope(드론 수·고도 밴드·풍속) 시나리오 정의 존재 — 형식 ODD 명세는 부분",
    ),
    # --- learning_assurance (W-shaped) --------------------------------------
    AIObjective(
        "learning_requirements", "Learning / data requirements capture",
        "learning_assurance", "LA:RQ-01", True,
        "gap", None,
        "데이터·학습 요구사항을 추적 가능 형식으로 포착한 산출물 없음 (갭)",
    ),
    AIObjective(
        "data_management", "Data management & representativeness",
        "learning_assurance", "LA:DM-01", True,
        "partial", "src/training/domain_rand.py",
        "도메인 무작위화로 학습 분포 다양화 — 형식 데이터 완전성·대표성 보증은 부분",
    ),
    AIObjective(
        "learning_process_management", "Learning process management",
        "learning_assurance", "LA:LM-01", False,
        "partial", "src/rl/ppo_collision.py",
        "PPO 학습 구성(하이퍼파라미터·Gym 래퍼) 정의 — 형식 학습 관리 계획은 부분",
    ),
    AIObjective(
        "model_training", "Model training",
        "learning_assurance", "LA:LM-02", False,
        "partial", "src/rl/ppo_collision.py",
        "SB3 PPO 훈련 파이프라인 존재(학습은 GPU) — 추적성·재현 보증은 부분",
    ),
    AIObjective(
        "learning_process_verification", "Learning process verification (generalisation)",
        "learning_assurance", "LA:LM-03", True,
        "gap", None,
        "미학습 시나리오 전이(일반화) 검증 프로토콜 없음 — 451-460 트랙의 핵심 연구 갭 (갭)",
    ),
    AIObjective(
        "model_implementation", "Model implementation on target",
        "learning_assurance", "LA:IM-01", True,
        "gap", None,
        "타깃(엣지) 추론 모델 구현·정량화 검증 없음, 연구 코드만 존재 (갭)",
    ),
    AIObjective(
        "inference_model_verification", "Inference model verification & integration",
        "learning_assurance", "LA:IM-02", True,
        "gap", None,
        "추론 모델의 시스템 통합·검증 산출물 없음 (갭)",
    ),
    # --- explainability ------------------------------------------------------
    AIObjective(
        "development_explainability", "Explainability for development",
        "explainability", "EX:DEV-01", False,
        "gap", None,
        "RL/GNN/Transformer 는 블랙박스 — 해석 가능 경로는 비-ML APF 가 담당 (갭)",
    ),
    AIObjective(
        "end_user_explainability", "Explainability for end users / operators",
        "explainability", "EX:USR-01", False,
        "gap", None,
        "ML 결정에 대한 운영자용 설명 인터페이스 없음 (갭)",
    ),
    # --- human_factors -------------------------------------------------------
    AIObjective(
        "human_ai_teaming", "Human-AI teaming (Level 2)",
        "human_factors", "HF:HT-01", False,
        "partial", "src/airspace_control/controller/airspace_controller.py",
        "결정적 관제기가 ML 자문을 경계·재정의 — 협업 구조 존재, 형식 HF 분석은 부분",
    ),
    AIObjective(
        "human_oversight", "Human/automation oversight of AI",
        "human_factors", "HF:OV-01", True,
        "partial", "src/airspace_control/controller/airspace_controller.py",
        "ML 출력을 결정적 관제기가 한정(최종 권한 비-ML) — 감독 구조 부분 충족",
    ),
    # --- safety_risk_mitigation (SDACS 의 진짜 강점) -------------------------
    AIObjective(
        "ai_safety_assessment", "AI-specific safety (risk) assessment",
        "safety_risk_mitigation", "SA:RA-01", True,
        "partial", "simulation/path_deconflict.py",
        "ML 출력을 결정적 디컨플릭션이 경계 — 형식 AI 안전 평가 문서는 부분",
    ),
    AIObjective(
        "runtime_safety_monitoring", "Runtime safety monitoring / assurance",
        "safety_risk_mitigation", "SA:RT-01", False,
        "conformant", "simulation/compliance_checker.py",
        "런타임 적합성 감시가 계획 대비 이탈·규정 위반을 탐지 — ML 자문을 결정적 검증",
    ),
    AIObjective(
        "classical_safety_net_authority", "Classical safety net retains authority over AI",
        "safety_risk_mitigation", "SA:SN-01", True,
        "conformant", "simulation/emergency_protocol.py",
        "5계층 안전망·비상 프로토콜이 안전-결정권 보유 — ML 은 안전-크리티컬 최종 권한 없음",
    ),
    # --- ethics_assessment ---------------------------------------------------
    AIObjective(
        "ethics_based_assessment", "Ethics-based trustworthiness assessment",
        "ethics_assessment", "ET:EA-01", False,
        "gap", None,
        "윤리 기반 신뢰성 평가(편향·책임·투명성) 산출물 없음 (갭)",
    ),
)


# 로드 시점 무결성 게이트 — 중복 식별자를 임포트 시 즉시 차단(테스트보다 이른 단계).
_CATALOG_IDS = [o.objective_id for o in AI_OBJECTIVES]
assert len(_CATALOG_IDS) == len(set(_CATALOG_IDS)), "duplicate objective_id in AI_OBJECTIVES"


@dataclass(frozen=True)
class ConformanceReport:
    """EASA 신뢰 가능 AI 적합성 자가 평가 요약."""

    total: int
    conformant: int
    partial: int
    gap: int
    foundational_total: int
    foundational_conformant: int
    by_block: Mapping[str, tuple[int, int, int]]  # block -> (conformant, partial, gap), read-only

    def __post_init__(self) -> None:
        # by_block 을 항상 읽기 전용 뷰로 동결 — 직접 생성 시에도 내부 변형 차단.
        if not isinstance(self.by_block, MappingProxyType):
            object.__setattr__(self, "by_block", MappingProxyType(dict(self.by_block)))
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
        if self.by_block:
            invalid = set(self.by_block.keys()) - set(BUILDING_BLOCKS)
            if invalid:
                raise ValueError(f"by_block contains unknown blocks: {sorted(invalid)}")
            c = sum(v[0] for v in self.by_block.values())
            p = sum(v[1] for v in self.by_block.values())
            g = sum(v[2] for v in self.by_block.values())
            if (c, p, g) != (self.conformant, self.partial, self.gap):
                raise ValueError(
                    f"by_block sums ({c},{p},{g}) != "
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
        있어도 True. SDACS 의 ML 은 기반 목표 다수가 갭이므로 통상 True 다.
        """
        if not self.foundational_total:
            return False
        return self.foundational_conformant < self.foundational_total


def find_objective(objective_id: str) -> AIObjective:
    """식별자로 목표를 조회한다. 없으면 KeyError."""
    for obj in AI_OBJECTIVES:
        if obj.objective_id == objective_id:
            return obj
    raise KeyError(f"unknown AI objective: {objective_id!r}")


def objectives_by_block(block: str) -> tuple[AIObjective, ...]:
    """빌딩 블록에 속한 목표를 식별자 정렬로 반환한다."""
    if block not in BUILDING_BLOCKS:
        raise ValueError(f"block must be one of {BUILDING_BLOCKS}, got {block!r}")
    return tuple(
        sorted((o for o in AI_OBJECTIVES if o.building_block == block),
               key=lambda o: o.objective_id)
    )


def foundational_objectives() -> tuple[AIObjective, ...]:
    """기반(필수) 목표(foundational=True)를 식별자 정렬로 반환한다."""
    return tuple(
        sorted((o for o in AI_OBJECTIVES if o.foundational),
               key=lambda o: o.objective_id)
    )


def gaps() -> tuple[AIObjective, ...]:
    """미충족(gap) 목표를 식별자 정렬로 반환한다."""
    return tuple(
        sorted((o for o in AI_OBJECTIVES if o.is_gap), key=lambda o: o.objective_id)
    )


def objectives_by_status(status: str) -> tuple[AIObjective, ...]:
    """적합성 상태별 목표를 식별자 정렬로 반환한다."""
    if status not in CONFORMANCE_STATUSES:
        raise ValueError(f"status must be one of {CONFORMANCE_STATUSES}, got {status!r}")
    return tuple(
        sorted((o for o in AI_OBJECTIVES if o.status == status),
               key=lambda o: o.objective_id)
    )


def conformance_report() -> ConformanceReport:
    """전체 적합성 현황을 집계한 결정적 리포트를 생성한다."""
    total = len(AI_OBJECTIVES)
    conformant = sum(1 for o in AI_OBJECTIVES if o.status == "conformant")
    partial = sum(1 for o in AI_OBJECTIVES if o.status == "partial")
    gap = sum(1 for o in AI_OBJECTIVES if o.status == "gap")
    foundational = [o for o in AI_OBJECTIVES if o.foundational]
    foundational_conformant = sum(1 for o in foundational if o.status == "conformant")
    by_block: dict[str, tuple[int, int, int]] = {}
    for block in BUILDING_BLOCKS:
        members = [o for o in AI_OBJECTIVES if o.building_block == block]
        by_block[block] = (
            sum(1 for o in members if o.status == "conformant"),
            sum(1 for o in members if o.status == "partial"),
            sum(1 for o in members if o.status == "gap"),
        )
    return ConformanceReport(
        total=total,
        conformant=conformant,
        partial=partial,
        gap=gap,
        foundational_total=len(foundational),
        foundational_conformant=foundational_conformant,
        by_block=MappingProxyType(by_block),
    )


def conformance_matrix() -> tuple[dict[str, object], ...]:
    """도구 간 교환용 적합성 매트릭스를 (블록, 식별자) 정렬 행으로 반환한다."""
    ordered = sorted(
        AI_OBJECTIVES,
        key=lambda o: (BUILDING_BLOCKS.index(o.building_block), o.objective_id),
    )
    return tuple(
        MappingProxyType({
            "objective_id": o.objective_id,
            "name": o.name,
            "building_block": o.building_block,
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
    lines = ["EASA 신뢰 가능 AI(Learning Assurance) 적합성 매트릭스", ""]
    for row in conformance_matrix():
        mark = _STATUS_MARK[str(row["status"])]
        kind = "기반" if row["foundational"] else "권장"
        module = row["sdacs_module"] or "—"
        lines.append(
            f"[{row['building_block']:24}] {mark:5} {kind} {row['anchor']} {row['name']}"
        )
        lines.append(f"      → {module}")
    return "\n".join(lines)


def _format_report() -> str:
    r = conformance_report()
    lines = [
        "EASA 신뢰 가능 AI 적합성 자가 평가 요약",
        "",
        f"가중 점수   : {r.weighted_score_pct:.0f}% "
        f"(충족 {r.conformant} · 부분 {r.partial} · 갭 {r.gap} / 총 {r.total})",
        f"기반 목표   : {r.foundational_conformant}/{r.foundational_total} 완전 충족 "
        f"({r.foundational_conformant_pct:.0f}%) "
        f"{'— 기반 미완전 있음' if r.has_foundational_incomplete else '— 기반 전부 충족'}",
        "",
        "빌딩 블록별 (충족/부분/갭):",
    ]
    for block in BUILDING_BLOCKS:
        c, p, g = r.by_block[block]
        lines.append(f"  {_BLOCK_NAMES[block]:42}: {c}/{p}/{g}")
    lines.append("")
    lines.append(
        "정직 공시: SDACS 의 ML 은 연구 수준이다. 낮은 점수는 결함이 아니라 인증 경로의"
    )
    lines.append(
        "  현 위치를 정직하게 보고하는 것이며, 안전은 ML 이 아닌 결정적 안전망이 보장한다."
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="EASA 신뢰 가능 AI(Learning Assurance) 적합성 자가 평가 (ODYSSEY Phase 451)"
    )
    parser.add_argument("--matrix", action="store_true", help="전체 적합성 매트릭스 출력")
    parser.add_argument("--report", action="store_true", help="적합성 요약 출력")
    parser.add_argument("--block", choices=BUILDING_BLOCKS, help="빌딩 블록별 목표 출력")
    parser.add_argument("--gaps", action="store_true", help="미충족(갭) 목표 출력")
    parser.add_argument("--foundational", action="store_true", help="기반(필수) 목표 출력")
    args = parser.parse_args(argv)

    if args.matrix:
        print(_format_matrix())
    elif args.report:
        print(_format_report())
    elif args.block:
        for obj in objectives_by_block(args.block):
            print(f"{obj.objective_id} [{obj.status}]: {obj.name} — {obj.summary}")
    elif args.gaps:
        for obj in gaps():
            print(f"[{obj.building_block}] {obj.anchor} {obj.name}: {obj.summary}")
    elif args.foundational:
        for obj in foundational_objectives():
            print(f"{_STATUS_MARK[obj.status]} {obj.anchor} {obj.name} → {obj.sdacs_module or '—'}")
    else:
        print(_format_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
