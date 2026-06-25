"""ODYSSEY Phase 455 — ML 데이터 관리(Data Management) 적합성 게이트.

EASA Concept Paper(*Guidance for Level 1&2 ML applications*, Issue 02 2024)의 신뢰
가능 AI 빌딩 블록 중 **러닝 어슈어런스(Learning Assurance) W-shape 좌측 팔** — 즉
*데이터 라이프사이클 관리*(Data Management) 목표를 SDACS 의 ML(RL) 자산이 어디까지
충족하는가를 **결정적**으로 평가하는 적합성 게이트.

자매 Phase 와의 경계 (서로소)
----------------------------
- Phase 451 `easa_ai_conformance` : 빌딩 블록 6종 *전체* 를 한 매트릭스로 자가 평가(상위).
- Phase 452 `rl_generalization_protocol` : 미학습 시나리오 *전이 평가 프로토콜* (W 우측 검증).
- Phase 453 `rl_advisory_boundary` : ML 이 안전 결정에 닿지 않는 *구조적 자문 경계*.
- Phase 454 `ml_application_classification` : ML 애플리케이션의 *EASA Level 분류*.
- **Phase 455(본 모듈)** : W *좌측* — 학습 데이터의 *요구·수집·전처리·검증* 라이프사이클이
  관리되는가. 451 이 가장 큰 갭으로 지목한 ``learning_process_verification`` 의 *입력측*
  근거를 데이터 차원에서 세분한다.

핵심 통찰 (정직 공시, CLAUDE.md)
-------------------------------
SDACS 의 RL 학습 데이터는 **시뮬레이션 생성** 이다 — 시나리오 코퍼스(YAML SSoT 10종)와
도메인 무작위화(`src/training/domain_rand.py`) 분포가 곧 데이터셋이고, 실 비행 로그는
수집되지 않았다(Track A 하드웨어 의존). 따라서 본 게이트는 *의도적으로 보수적* 이다:

- 데이터 *요구 명세*·*train/test 홀드아웃*·*결정적 파이프라인* 같은 **소프트웨어로
  통제 가능한** 목표는 충족(satisfied)으로 인용 가능하다.
- 그러나 **실세계 데이터 출처(provenance)** 는 갭(gap)이다 — 시뮬-실측 갭 보정
  (`src/training/sim_real_gap.py`)이 분포를 *근사* 할 뿐 실측을 *대체* 하지 못한다.
- 따라서 현 리포 판정은 **NOT_READY**: 데이터 관리의 SW 골격은 갖췄으나, 실세계
  대표성을 입증할 출처가 없는 한 인증용 데이터 관리는 미완이다(준비도 ≠ 완수).

이 게이트의 ``satisfied``/``partial`` 은 모두 *디스크 실재 산출물* 을 인용하며
(`audit_cited_artifacts` 라이브 강제), 인용 산출물이 사라지면 판정에서 *강등* 한다 —
정적 카탈로그와 실측의 불일치를 정직하게 표면화한다.

정직성 결속
-----------
1. ``status`` 는 3값(``satisfied``·``partial``·``gap``)이며 ``gap`` ⟺ ``evidence is None``.
   충족/부분은 반드시 실재 경로를 인용한다(테스트가 디스크 실재를 강제).
2. ``criticality`` 가 ``foundational`` 인 목표 하나라도 ``gap`` 이면 판정은
   ``DATA_NOT_READY`` — 가중 점수가 높아도 판정을 앞당기지 않는다. 기반 목표가
   ``partial`` 이면 ``DATA_AT_RISK``. 권장 목표의 미완은 점수에만 반영된다.
3. 본 게이트는 *자문* 이지 집행이 아니다. 무작위성 0 · 부수효과 0 · 결정적.
   기존 모듈 무수정 순수 추가.

CLI:
    python simulation/ml_data_management.py --objectives   # 전체 목표 매트릭스
    python simulation/ml_data_management.py --report       # 판정 요약
    python simulation/ml_data_management.py --audit        # 인용 산출물 디스크 감사
    python simulation/ml_data_management.py --gaps         # 갭(gap) 목표
    python simulation/ml_data_management.py --foundational  # 기반 목표만
    python simulation/ml_data_management.py --stage collection  # 라이프사이클 단계별
"""
from __future__ import annotations

import argparse
import pathlib
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

# 데이터 라이프사이클 단계 (EASA DM W-shape 좌측). 정렬·표시 순서의 정본.
LIFECYCLE_STAGES: tuple[str, ...] = (
    "requirements",   # 데이터 요구·정의
    "collection",     # 수집·출처
    "preprocessing",  # 전처리·파이프라인
    "verification",   # 데이터 검증·분할
)

# 목표 상태 (3값). satisfied=충족, partial=부분, gap=미충족(근거 없음).
OBJECTIVE_STATUSES: tuple[str, ...] = ("satisfied", "partial", "gap")

# 가중 점수: 충족 1.0, 부분 0.5, 갭 0.0.
_STATUS_WEIGHT: Mapping[str, float] = MappingProxyType(
    {"satisfied": 1.0, "partial": 0.5, "gap": 0.0}
)

# 중요도 (2값). foundational=판정 게이트, recommended=점수에만 반영.
CRITICALITIES: tuple[str, ...] = ("foundational", "recommended")

# 판정 (verdict). 기반 목표 충족 상태로 결정.
VERDICT_NOT_READY = "DATA_NOT_READY"
VERDICT_AT_RISK = "DATA_AT_RISK"
VERDICT_MANAGED = "DATA_MANAGED"


@dataclass(frozen=True)
class DataObjective:
    """ML 데이터 관리 라이프사이클의 단일 목표."""

    objective_id: str        # 안정 식별자 (snake_case)
    name: str                # 목표 명칭
    stage: str               # requirements·collection·preprocessing·verification
    criticality: str         # foundational·recommended
    status: str              # satisfied·partial·gap
    evidence: str | None     # 떠받치는 리포 경로 (gap 이면 None)
    summary: str             # 한 줄 설명

    def __post_init__(self) -> None:
        if not self.objective_id or self.objective_id != self.objective_id.strip():
            raise ValueError("objective_id must be non-empty and unpadded")
        if any(ws in self.objective_id for ws in (" ", "\t", "\n")):
            raise ValueError("objective_id must be snake_case (no whitespace)")
        if self.objective_id != self.objective_id.lower():
            raise ValueError("objective_id must be lowercase snake_case")
        if not self.name or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        if not self.summary or not self.summary.strip():
            raise ValueError("summary must be a non-empty string")
        if self.stage not in LIFECYCLE_STAGES:
            raise ValueError(
                f"stage must be one of {LIFECYCLE_STAGES}, got {self.stage!r}"
            )
        if self.criticality not in CRITICALITIES:
            raise ValueError(
                f"criticality must be one of {CRITICALITIES}, got {self.criticality!r}"
            )
        if self.status not in OBJECTIVE_STATUSES:
            raise ValueError(
                f"status must be one of {OBJECTIVE_STATUSES}, got {self.status!r}"
            )
        # 정직성 결속: gap ⟺ 근거 없음. 충족/부분은 반드시 실재 경로 인용.
        if self.status == "gap":
            if self.evidence is not None:
                raise ValueError("a gap objective must not cite evidence")
        else:
            if self.evidence is None or not self.evidence.strip():
                raise ValueError(
                    f"status {self.status!r} must cite a non-empty evidence path"
                )

    @property
    def is_foundational(self) -> bool:
        """기반(필수) 목표 여부."""
        return self.criticality == "foundational"

    @property
    def is_gap(self) -> bool:
        """갭(미충족) 여부."""
        return self.status == "gap"

    @property
    def weight(self) -> float:
        """가중 점수 기여 (satisfied 1.0·partial 0.5·gap 0.0)."""
        return _STATUS_WEIGHT[self.status]


# ML 데이터 관리 목표 카탈로그 (정본).
# evidence 경로는 리포에 실재하는 모듈/산출물 — 갭(gap)은 None.
# 현 리포는 학습 데이터가 *시뮬 생성* 이라 실세계 출처가 갭(정직한 한계).
DATA_OBJECTIVES: tuple[DataObjective, ...] = (
    # --- requirements ---
    DataObjective(
        "data_requirements_specified",
        "학습 데이터 요구사항이 스키마로 명세됨",
        "requirements", "foundational", "satisfied",
        "simulation/scenario_schema.py",
        "시나리오 데이터 계약(필드·타입·범위)이 `scenario_schema` 로 명세·강제됨",
    ),
    DataObjective(
        "ml_dataset_definition",
        "ML 데이터셋(시나리오 코퍼스 + DR 분포)이 정의됨",
        "requirements", "foundational", "satisfied",
        "src/training/domain_rand.py",
        "RL 학습 데이터 = 시나리오 코퍼스 + 도메인 무작위화 분포로 명시적 정의",
    ),
    # --- collection ---
    DataObjective(
        "scenario_corpus_curated",
        "표준 시나리오 코퍼스가 큐레이션·공개됨",
        "collection", "recommended", "satisfied",
        "docs/standards/SDACS_BENCHMARK_SUITE.md",
        "SDACS-SBS-10 표준 스위트 10종이 통제 축으로 큐레이션(Phase 465)",
    ),
    DataObjective(
        "representative_data_distribution",
        "데이터 분포가 운영 포락선을 대표함",
        "collection", "foundational", "partial",
        "src/training/domain_rand.py",
        "도메인 무작위화가 풍속·밀도·고장 포락선을 스팬 — 시뮬 범위 내 대표성(부분)",
    ),
    DataObjective(
        "real_world_data_provenance",
        "실세계(실 비행) 데이터 출처·이력 확보",
        "collection", "foundational", "gap",
        None,
        "실 비행 로그 미수집(Track A HW 의존) — 시뮬 생성 데이터만 존재, 실측 출처 갭",
    ),
    # --- preprocessing ---
    DataObjective(
        "deterministic_data_pipeline",
        "데이터 생성·전처리가 결정적(시드 RNG)",
        "preprocessing", "recommended", "satisfied",
        "src/utils/rng.py",
        "시드 RNG 규약(np.random.default_rng)으로 시나리오 생성·전처리 재현성 확보",
    ),
    DataObjective(
        "sim_real_gap_calibration",
        "시뮬-실측 갭 보정이 분포를 근사",
        "preprocessing", "recommended", "partial",
        "src/training/sim_real_gap.py",
        "도메인 무작위화 파라미터 자동 보정 — 실측 부재로 근사일 뿐(부분)",
    ),
    DataObjective(
        "dataset_provenance_pinned",
        "데이터 의존성·버전이 핀 고정됨",
        "preprocessing", "recommended", "partial",
        "requirements.lock.txt",
        "의존성 락·재현 컨테이너로 데이터 생성 환경 핀 — 데이터셋 자체 버저닝은 부분",
    ),
    # --- verification ---
    DataObjective(
        "train_test_holdout",
        "미학습 시나리오 train/test 홀드아웃 분리",
        "verification", "foundational", "satisfied",
        "simulation/rl_generalization_protocol.py",
        "Phase 452 일반화 프로토콜이 미학습 시나리오 홀드아웃을 결정적으로 분리",
    ),
    DataObjective(
        "independent_test_set",
        "독립 평가용 표준 테스트 셋 보유",
        "verification", "recommended", "satisfied",
        "simulation/standard_scenarios.py",
        "SBS-10 표준 시나리오가 도구 간 교차 벤치마크용 독립 평가 셋 제공",
    ),
    DataObjective(
        "data_completeness_audit",
        "데이터 완전성·스키마 적합 감사",
        "verification", "recommended", "satisfied",
        "config/scenario_params/nominal_baseline.yaml",
        "전 시나리오 YAML 이 `scenario_schema` 적합 — 결측·범위 위반을 결정적 거부",
    ),
    DataObjective(
        "fairness_bias_assessment",
        "데이터 편향·공정성 평가",
        "verification", "recommended", "gap",
        None,
        "군집 시나리오의 표집 편향(밀도·지형 치우침) 정량 평가 미수행 — 갭",
    ),
)


# 로드 시점 무결성 게이트 — 중복 식별자를 임포트 시 즉시 차단.
# `assert` 는 `python -O` 에서 비활성화되므로 명시적 raise 로 집행한다.
_CATALOG_IDS = [obj.objective_id for obj in DATA_OBJECTIVES]
if len(_CATALOG_IDS) != len(set(_CATALOG_IDS)):
    raise RuntimeError("duplicate objective_id in catalog")


def audit_cited_artifacts() -> tuple[str, ...]:
    """인용된 증거 경로 중 디스크에 실재하지 않는 것을 정렬로 반환한다.

    ``satisfied``/``partial`` 목표는 실재 산출물을 인용해야 한다 — 이 라이브 감사가
    인용 경로의 디스크 실재를 강제한다. 누군가 인용 산출물을 삭제하면 이 감사(와
    회귀 테스트)가 즉시 위반을 표면화한다. 위반이 없으면 빈 튜플.
    """
    missing: list[str] = []
    for obj in DATA_OBJECTIVES:
        if obj.evidence is None:
            continue
        if not (_REPO_ROOT / obj.evidence).exists():
            missing.append(obj.evidence)
    return tuple(sorted(set(missing)))


def artifacts_intact() -> bool:
    """인용 산출물이 전부 디스크에 실재하면 True."""
    return not audit_cited_artifacts()


@dataclass(frozen=True)
class DataManagementReport:
    """ML 데이터 관리 적합성 게이트 판정 요약."""

    verdict: str
    total: int
    satisfied: int
    partial: int
    gap: int
    foundational_total: int
    foundational_satisfied: int
    by_stage: Mapping[str, tuple[int, int, int]]  # stage -> (satisfied, partial, gap)

    def __post_init__(self) -> None:
        if not isinstance(self.by_stage, MappingProxyType):
            object.__setattr__(self, "by_stage", MappingProxyType(dict(self.by_stage)))
        counts = (
            self.total, self.satisfied, self.partial, self.gap,
            self.foundational_total, self.foundational_satisfied,
        )
        if min(counts) < 0:
            raise ValueError("counts must be non-negative")
        if self.satisfied + self.partial + self.gap != self.total:
            raise ValueError(
                f"satisfied ({self.satisfied}) + partial ({self.partial}) + "
                f"gap ({self.gap}) != total ({self.total})"
            )
        if self.foundational_total > self.total:
            raise ValueError("foundational_total cannot exceed total")
        if self.foundational_satisfied > self.foundational_total:
            raise ValueError("foundational_satisfied cannot exceed foundational_total")
        if self.verdict not in (VERDICT_NOT_READY, VERDICT_AT_RISK, VERDICT_MANAGED):
            raise ValueError(f"invalid verdict: {self.verdict!r}")
        # 빈 by_stage 도 교차검증한다 — 미지 단계 키 거부 + 합 일치 강제.
        invalid = set(self.by_stage.keys()) - set(LIFECYCLE_STAGES)
        if invalid:
            raise ValueError(f"by_stage has unknown keys: {sorted(invalid)}")
        # 비-빈 리포트는 모든 단계 키가 있어야 한다 — 누락 단계는 `_format_report` 의
        # `by_stage[stage]` 에서 KeyError 를 유발하므로 생성 시점에 차단한다. 빈 리포트
        # (total=0)는 의도적으로 빈 맵을 허용한다.
        missing_stages = set(LIFECYCLE_STAGES) - set(self.by_stage.keys())
        if missing_stages and self.total > 0:
            raise ValueError(f"by_stage is missing stages: {sorted(missing_stages)}")
        s = sum(v[0] for v in self.by_stage.values())
        p = sum(v[1] for v in self.by_stage.values())
        g = sum(v[2] for v in self.by_stage.values())
        if (s, p, g) != (self.satisfied, self.partial, self.gap):
            raise ValueError(
                f"by_stage sums ({s},{p},{g}) != "
                f"({self.satisfied},{self.partial},{self.gap})"
            )

    @property
    def weighted_score_pct(self) -> float:
        """가중 적합 점수 (%) — satisfied 1.0·partial 0.5·gap 0.0."""
        if not self.total:
            return 0.0
        score = self.satisfied * 1.0 + self.partial * 0.5
        return 100.0 * score / self.total

    @property
    def is_managed(self) -> bool:
        """판정이 DATA_MANAGED 인지 여부."""
        return self.verdict == VERDICT_MANAGED


def _verdict_for(objectives: tuple[DataObjective, ...]) -> str:
    """기반 목표 상태로 판정을 결정한다.

    우선순위(서로소): 기반 갭 → NOT_READY > 기반 부분 → AT_RISK >
    기반 전부 충족 → MANAGED. 권장 목표는 판정을 게이트하지 않는다.
    기반 목표가 하나도 없으면 공허한 MANAGED 가 아니라 NOT_READY.
    """
    foundational = [obj for obj in objectives if obj.is_foundational]
    if not foundational:
        return VERDICT_NOT_READY
    if any(obj.status == "gap" for obj in foundational):
        return VERDICT_NOT_READY
    if any(obj.status == "partial" for obj in foundational):
        return VERDICT_AT_RISK
    return VERDICT_MANAGED


def assess_data_management() -> DataManagementReport:
    """ML 데이터 관리 적합성을 집계한 결정적 게이트 판정을 생성한다.

    인용 산출물이 디스크에서 사라지면(라이브 감사 위반) 해당 목표의 정적
    ``satisfied``/``partial`` 선언은 신뢰할 수 없으므로 ``gap`` 으로 *강등* 한다 —
    정적 카탈로그와 실측 사이의 불일치를 정직하게 표면화한다. 강등 시 근거를
    제거(None)해 정직성 결속(gap ⟺ evidence None)을 유지한다.
    """
    missing = set(audit_cited_artifacts())
    effective: list[DataObjective] = []
    for obj in DATA_OBJECTIVES:
        if obj.evidence is not None and obj.evidence in missing:
            # gap 으로 완전 강등(부분 아님): 부재 산출물은 근거 0 이므로 주장이 *완전히*
            # 무근거가 된다 — 한 모듈 실패가 주장을 약화만 하는 Phase 453 격리 강등과 달리,
            # 본 게이트의 감사는 *목표별* 이라 부재 = 해당 주장 완전 미입증.
            effective.append(
                DataObjective(
                    obj.objective_id, obj.name, obj.stage, obj.criticality,
                    "gap", None,
                    obj.summary + " [인용 산출물 부재 — 정적 선언 강등됨]",
                )
            )
        else:
            effective.append(obj)
    objectives = tuple(effective)

    total = len(objectives)
    satisfied = sum(1 for obj in objectives if obj.status == "satisfied")
    partial = sum(1 for obj in objectives if obj.status == "partial")
    gap = sum(1 for obj in objectives if obj.status == "gap")
    foundational = [obj for obj in objectives if obj.is_foundational]
    foundational_satisfied = sum(1 for obj in foundational if obj.status == "satisfied")
    by_stage: dict[str, tuple[int, int, int]] = {}
    for stage in LIFECYCLE_STAGES:
        members = [obj for obj in objectives if obj.stage == stage]
        by_stage[stage] = (
            sum(1 for obj in members if obj.status == "satisfied"),
            sum(1 for obj in members if obj.status == "partial"),
            sum(1 for obj in members if obj.status == "gap"),
        )
    return DataManagementReport(
        verdict=_verdict_for(objectives),
        total=total,
        satisfied=satisfied,
        partial=partial,
        gap=gap,
        foundational_total=len(foundational),
        foundational_satisfied=foundational_satisfied,
        by_stage=MappingProxyType(by_stage),
    )


def find_objective(objective_id: str) -> DataObjective:
    """식별자로 목표를 조회한다. 없으면 KeyError."""
    for obj in DATA_OBJECTIVES:
        if obj.objective_id == objective_id:
            return obj
    raise KeyError(f"unknown data objective: {objective_id!r}")


def objectives_by_stage(stage: str) -> tuple[DataObjective, ...]:
    """라이프사이클 단계별 목표를 식별자 정렬로 반환한다."""
    if stage not in LIFECYCLE_STAGES:
        raise ValueError(f"stage must be one of {LIFECYCLE_STAGES}, got {stage!r}")
    return tuple(
        sorted((obj for obj in DATA_OBJECTIVES if obj.stage == stage),
               key=lambda obj: obj.objective_id)
    )


def foundational_objectives() -> tuple[DataObjective, ...]:
    """기반(필수) 목표를 식별자 정렬로 반환한다."""
    return tuple(
        sorted((obj for obj in DATA_OBJECTIVES if obj.is_foundational),
               key=lambda obj: obj.objective_id)
    )


def gaps() -> tuple[DataObjective, ...]:
    """갭(gap) 목표를 식별자 정렬로 반환한다."""
    return tuple(
        sorted((obj for obj in DATA_OBJECTIVES if obj.is_gap),
               key=lambda obj: obj.objective_id)
    )


def data_matrix() -> tuple[Mapping[str, object], ...]:
    """도구 간 교환용 데이터 관리 매트릭스를 (단계, 식별자) 정렬 행으로 반환한다."""
    ordered = sorted(
        DATA_OBJECTIVES,
        key=lambda obj: (LIFECYCLE_STAGES.index(obj.stage), obj.objective_id),
    )
    return tuple(
        MappingProxyType({
            "objective_id": obj.objective_id,
            "name": obj.name,
            "stage": obj.stage,
            "criticality": obj.criticality,
            "status": obj.status,
            "evidence": obj.evidence,
            "summary": obj.summary,
        })
        for obj in ordered
    )


_STATUS_MARK: dict[str, str] = {"satisfied": "✓", "partial": "◐", "gap": "✗(갭)"}
_STAGE_NAMES: dict[str, str] = {
    "requirements": "요구",
    "collection": "수집",
    "preprocessing": "전처리",
    "verification": "검증",
}


def _format_matrix() -> str:
    lines = ["ML 데이터 관리 목표 매트릭스 (EASA Learning Assurance — Data Management)", ""]
    for row in data_matrix():
        mark = _STATUS_MARK[str(row["status"])]
        kind = "기반" if row["criticality"] == "foundational" else "권장"
        stage = _STAGE_NAMES[str(row["stage"])]
        evidence = row["evidence"] or "—"
        lines.append(f"[{stage}·{kind}] {mark} {row['objective_id']}: {row['name']}")
        lines.append(f"      → {evidence}")
    return "\n".join(lines)


def _format_report() -> str:
    r = assess_data_management()
    audit = audit_cited_artifacts()
    lines = [
        "ML 데이터 관리 적합성 게이트 판정 (ODYSSEY Phase 455)",
        "",
        f"판정       : {r.verdict}",
        f"가중 점수   : {r.weighted_score_pct:.0f}% "
        f"(충족 {r.satisfied} · 부분 {r.partial} · 갭 {r.gap} / 총 {r.total})",
        f"기반 목표   : {r.foundational_satisfied}/{r.foundational_total} 충족",
        f"산출물 감사 : {'전부 실재' if not audit else f'부재 {len(audit)}건'}",
        "",
        "단계별 (충족/부분/갭):",
    ]
    for stage in LIFECYCLE_STAGES:
        s, p, g = r.by_stage[stage]
        lines.append(f"  {_STAGE_NAMES[stage]}: {s}/{p}/{g}")
    lines.append("")
    lines.append(
        "정직 공시: 학습 데이터가 시뮬 생성이라 실세계 출처가 갭 — DATA_NOT_READY 는"
    )
    lines.append(
        "  데이터 관리 SW 골격은 갖췄으나 실측 대표성 입증 전까지 인증 미완임을 뜻한다."
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ML 데이터 관리(Data Management) 적합성 게이트 (ODYSSEY Phase 455)"
    )
    parser.add_argument("--objectives", action="store_true", help="전체 목표 매트릭스 출력")
    parser.add_argument("--report", action="store_true", help="판정 요약 출력")
    parser.add_argument("--audit", action="store_true", help="인용 산출물 디스크 감사 출력")
    parser.add_argument("--gaps", action="store_true", help="갭(gap) 목표 출력")
    parser.add_argument("--foundational", action="store_true", help="기반 목표만 출력")
    parser.add_argument("--stage", choices=LIFECYCLE_STAGES, help="라이프사이클 단계별 출력")
    args = parser.parse_args(argv)

    if args.objectives:
        print(_format_matrix())
    elif args.report:
        print(_format_report())
    elif args.audit:
        missing = audit_cited_artifacts()
        if not missing:
            print("인용 산출물 감사: 전부 디스크에 실재 — 데이터 근거 무결.")
        else:
            print("인용 산출물 감사: 부재 산출물 발견 —")
            for path in missing:
                print(f"  {path}")
    elif args.gaps:
        for obj in gaps():
            print(f"[{obj.stage}] {obj.objective_id}: {obj.summary}")
    elif args.foundational:
        for obj in foundational_objectives():
            print(f"{_STATUS_MARK[obj.status]} {obj.objective_id} → {obj.evidence or '—'}")
    elif args.stage:
        for obj in objectives_by_stage(args.stage):
            print(f"{_STATUS_MARK[obj.status]} {obj.objective_id}: {obj.name}")
    else:
        print(_format_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
