"""ODYSSEY Phase 461 — ASTM F38 기고 초안: 군집 관제 시험 방법(Test Method) 명세.

Standards & Policy 트랙(461-480)의 첫 칸. ASTM Committee F38 (*Unmanned Aircraft
Systems*) 에 기고할 **군집 공역 관제(swarm airspace control) 시험 방법** 을 결정적
명세로 인코딩한다. ASTM 표준 시험방법 문서(예: F3322 배터리·F3548 UTM)의 통상
구조 — Scope · Significance · Apparatus · Procedure · **Acceptance Criteria** ·
Report — 중 *기계적으로 검증 가능한* 부분(측정 지표 + 합격 판정)을 코드로 굳혀,
동일한 시뮬레이션 산출 KPI 에 같은 정의로 같은 판정을 내릴 수 있게 한다.

설계 원칙
--------
- **중복 없는 계층**: 시험 *절차/근거* 의 산문 정의는 동반 문서
  ``docs/standards/ASTM_F38_SWARM_TEST_METHOD.md`` 가 유일 출처다. 본 모듈은
  각 시험의 *측정 지표 키·단위·합격 임계·판정 방향* 만 보유해 문서를 가리킨다.
- **정직 공시**: 임계값은 **제안(draft)** 이며 ASTM 채택 전이다. 근거는 SDACS
  실측 기준선(충돌 해결률 공식 등)과 문헌이며, ``proposed=True`` 로 항상 표시.
- **판정의 결정성**: 측정값 → PASS/FAIL/INCONCLUSIVE 는 임계·방향만으로 정해지며
  무작위성 0. 측정값 부재(None)는 INCONCLUSIVE(거짓 합격 금지).

Phase 465(표준 벤치마크 스위트)가 *무엇을 돌릴지*(시나리오)를, Phase 466(텔레메트리
스키마)가 *어떻게 기록할지*(데이터 포맷)를 정한다면, 본 모듈은 *무엇을 합격으로
볼지*(시험 방법 + 합격 기준)를 정해 세 축을 완성한다.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python -m simulation.swarm_test_method --list       # 시험 방법 요약 표
    python -m simulation.swarm_test_method --validate    # 레지스트리 정합성
    python -m simulation.swarm_test_method --evaluate     # SDACS 실측 기준선 판정 데모
    python -m simulation.swarm_test_method --manifest     # 기고 매니페스트(JSON)
    python -m simulation.swarm_test_method --markdown     # 합격 기준표(Markdown)
"""
from __future__ import annotations

import json
import math
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

# 판정 방향 — 측정값이 임계 대비 어느 쪽이어야 합격인가.
DIRECTION_GE = "GE"  # measured >= threshold 이면 합격 (클수록 좋음)
DIRECTION_LE = "LE"  # measured <= threshold 이면 합격 (작을수록 좋음)
_DIRECTIONS = (DIRECTION_GE, DIRECTION_LE)

# 판정 결과(서로소).
PASS = "PASS"
FAIL = "FAIL"
INCONCLUSIVE = "INCONCLUSIVE"  # 측정값 부재 — 거짓 합격을 내지 않는다.


@dataclass(frozen=True)
class TestMethod:
    """군집 관제 시험 방법 한 건(불변).

    시험의 산문 정의(절차·근거)는 동반 문서가 유일 출처이며, 본 객체는 기계
    판정에 필요한 메타데이터만 보유한다.

    Attributes:
        method_id: 안정 식별자 (SM-TM-01..).
        title: 시험 방법 제목.
        metric_key: 측정 산출 KPI 키 (시뮬레이터 보고 지표명).
        units: 측정 단위 (예: ``ratio``, ``m``, ``count``, ``s``).
        threshold: 합격 임계값.
        direction: ``GE`` 또는 ``LE`` — 임계 대비 합격 방향.
        rationale: 임계 근거(요약). 상세는 동반 문서.
        proposed: ASTM 채택 전 제안임을 표시(항상 True — 정직 공시).
    """

    method_id: str
    title: str
    metric_key: str
    units: str
    threshold: float
    direction: str
    rationale: str
    proposed: bool = True

    def __post_init__(self) -> None:
        for field_name in ("method_id", "title", "metric_key", "units", "rationale"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} 는 비어 있을 수 없습니다: {value!r}")
        if self.direction not in _DIRECTIONS:
            raise ValueError(f"direction 은 {_DIRECTIONS} 중 하나여야 합니다: {self.direction!r}")
        if not isinstance(self.threshold, (int, float)) or not math.isfinite(self.threshold):
            raise ValueError(f"threshold 는 유한한 수여야 합니다: {self.threshold!r}")


@dataclass(frozen=True)
class MethodOutcome:
    """한 시험 방법에 대한 측정값 판정 결과(불변)."""

    method_id: str
    verdict: str  # PASS / FAIL / INCONCLUSIVE
    measured: float | None
    threshold: float
    direction: str

    @property
    def is_pass(self) -> bool:
        return self.verdict == PASS


# --- 시험 방법 레지스트리 (ASTM F38 기고 초안) -------------------------------
#
# 임계값은 제안(draft)이다. 근거 요약은 rationale, 상세는 동반 문서 참조.
# 충돌 해결률 공식은 CLAUDE.md 규약 `1 - collisions/(conflicts + collisions)`.
_METHODS: tuple[TestMethod, ...] = (
    TestMethod(
        method_id="SM-TM-01",
        title="군집 충돌 해결률 (Conflict Resolution Rate)",
        metric_key="conflict_resolution_rate",
        units="ratio",
        threshold=0.95,
        direction=DIRECTION_GE,
        rationale="해결률 = 1 - collisions/(conflicts+collisions). 공역 통제 시스템의 "
        "1차 안전 지표. 제안 임계 0.95 는 SDACS 실측 고밀도 기준선 위.",
    ),
    TestMethod(
        method_id="SM-TM-02",
        title="공칭 밀도 무충돌 (Zero Collision under Nominal Density)",
        metric_key="collisions",
        units="count",
        threshold=0.0,
        direction=DIRECTION_LE,
        rationale="공칭(저밀도) 운용에서 실제 충돌은 0 이어야 한다 — 안전망의 "
        "절대 하한. 합격은 collisions == 0.",
    ),
    TestMethod(
        method_id="SM-TM-03",
        title="수평 분리 유지 (Horizontal Separation)",
        metric_key="min_horizontal_separation_m",
        units="m",
        threshold=5.0,
        direction=DIRECTION_GE,
        rationale="시험 전 구간 최근접 거리(NMD)가 수평 최소 분리 이상이어야 한다. "
        "제안 5 m 는 소형 멀티로터 군집의 보수적 분리 버블.",
    ),
    TestMethod(
        method_id="SM-TM-04",
        title="수직 분리 유지 (Vertical Separation)",
        metric_key="min_vertical_separation_m",
        units="m",
        threshold=2.0,
        direction=DIRECTION_GE,
        rationale="동일 수평 셀 내 고도층 간 최소 수직 분리. 제안 2 m 는 SDACS 9층 "
        "고도 레이어(0~240m) 운용과 정합.",
    ),
    TestMethod(
        method_id="SM-TM-05",
        title="저배터리 복귀 성공률 (RTB Success Rate)",
        metric_key="rtb_success_rate",
        units="ratio",
        threshold=0.99,
        direction=DIRECTION_GE,
        rationale="배터리 임계 진입 시 기지 복귀(RTB) 성공률. 제안 0.99 — 강하/회수 "
        "안전망 신뢰성 요건.",
    ),
    TestMethod(
        method_id="SM-TM-06",
        title="평균 해소 지연 (Mean Time To Deconflict)",
        metric_key="mean_time_to_deconflict_s",
        units="s",
        threshold=3.0,
        direction=DIRECTION_LE,
        rationale="충돌 위험 탐지~해소 명령 평균 지연. 작을수록 좋음. 제안 3 s 는 "
        "1Hz 컨트롤러 + 10Hz 드론 루프의 응답 예산.",
    ),
    TestMethod(
        method_id="SM-TM-07",
        title="결정적 재현성 (Deterministic Reproducibility)",
        metric_key="reproducible",
        units="bool",
        threshold=1.0,
        direction=DIRECTION_GE,
        rationale="동일 시드 → 동일 산출(1.0=재현됨, 0.0=불일치). 시험 결과 신뢰의 "
        "전제. 합격은 reproducible == 1.0.",
    ),
)

REGISTRY: Mapping[str, TestMethod] = MappingProxyType(
    {m.method_id: m for m in _METHODS}
)


def methods() -> tuple[TestMethod, ...]:
    """등록된 시험 방법 전체(정의 순서)."""
    return _METHODS


def get_method(method_id: str) -> TestMethod:
    """식별자로 시험 방법 조회. 미등록이면 KeyError."""
    return REGISTRY[method_id]


def evaluate_method(method: TestMethod, measured: float | None) -> MethodOutcome:
    """단일 시험 방법에 측정값을 적용해 판정한다.

    측정값이 None 이면 INCONCLUSIVE — 측정 부재를 합격으로 처리하지 않는다.
    """
    if measured is None:
        verdict = INCONCLUSIVE
    elif method.direction == DIRECTION_GE:
        verdict = PASS if measured >= method.threshold else FAIL
    else:  # DIRECTION_LE
        verdict = PASS if measured <= method.threshold else FAIL
    return MethodOutcome(
        method_id=method.method_id,
        verdict=verdict,
        measured=measured,
        threshold=method.threshold,
        direction=method.direction,
    )


@dataclass(frozen=True)
class SuiteResult:
    """전체 시험 스위트 판정 요약(불변)."""

    outcomes: tuple[MethodOutcome, ...]
    passed: int
    failed: int
    inconclusive: int

    def __post_init__(self) -> None:
        # 집계 카운트가 outcomes 와 일치함을 강제 — 외부 구성 시 불일치 차단.
        expected = {
            "passed": sum(1 for o in self.outcomes if o.verdict == PASS),
            "failed": sum(1 for o in self.outcomes if o.verdict == FAIL),
            "inconclusive": sum(1 for o in self.outcomes if o.verdict == INCONCLUSIVE),
        }
        for name, value in expected.items():
            if getattr(self, name) != value:
                raise ValueError(
                    f"{name} 집계가 outcomes 와 불일치: {getattr(self, name)} != {value}"
                )

    @property
    def is_conformant(self) -> bool:
        """단 하나의 FAIL/INCONCLUSIVE 도 없어야 적합(all-or-nothing)."""
        return self.failed == 0 and self.inconclusive == 0 and self.passed > 0

    def summary(self) -> str:
        verdict = "CONFORMANT" if self.is_conformant else "NON_CONFORMANT"
        return (
            f"{verdict} — {self.passed} pass / {self.failed} fail / "
            f"{self.inconclusive} inconclusive (총 {len(self.outcomes)})"
        )


def evaluate_suite(measurements: Mapping[str, float | None]) -> SuiteResult:
    """측정 KPI 묶음을 전체 시험 방법에 적용해 적합성을 판정한다.

    Args:
        measurements: ``metric_key -> 측정값`` 사상. 누락 키는 None(INCONCLUSIVE).
    """
    outcomes = tuple(
        evaluate_method(m, measurements.get(m.metric_key)) for m in _METHODS
    )
    passed = sum(1 for o in outcomes if o.verdict == PASS)
    failed = sum(1 for o in outcomes if o.verdict == FAIL)
    inconclusive = sum(1 for o in outcomes if o.verdict == INCONCLUSIVE)
    return SuiteResult(
        outcomes=outcomes,
        passed=passed,
        failed=failed,
        inconclusive=inconclusive,
    )


@dataclass(frozen=True)
class ValidationResult:
    """레지스트리 정합성 검사 결과 (scenario_schema 규약과 동일 형태)."""

    is_valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


def validate_registry() -> ValidationResult:
    """시험 방법 레지스트리의 결정적 정합성 불변식을 검사한다.

    - 식별자 유일·비공백
    - direction 은 GE/LE
    - metric_key 유일(한 지표=한 시험)
    - 모든 항목 proposed=True (채택 전 정직 공시)
    """
    errors: list[str] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()
    seen_metrics: set[str] = set()
    for m in _METHODS:
        if m.method_id in seen_ids:
            errors.append(f"중복 method_id: {m.method_id}")
        seen_ids.add(m.method_id)
        if m.metric_key in seen_metrics:
            errors.append(f"중복 metric_key: {m.metric_key} ({m.method_id})")
        seen_metrics.add(m.metric_key)
        if m.direction not in _DIRECTIONS:
            errors.append(f"잘못된 direction: {m.method_id} -> {m.direction}")
        if not m.proposed:
            errors.append(
                f"{m.method_id} proposed=False — ASTM 채택 증거 없이 채택 표기"
            )
    return ValidationResult(
        is_valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# SDACS 실측 기준선 — 정직 공시용 데모 측정값(2026-06 회귀 기준선 근사).
# 절대 검증이 아니라 *시험 방법이 어떻게 판정하는가* 를 보이기 위한 예시.
SDACS_BASELINE: Mapping[str, float] = MappingProxyType(
    {
        "conflict_resolution_rate": 0.97,
        "collisions": 0.0,
        "min_horizontal_separation_m": 6.2,
        "min_vertical_separation_m": 3.0,
        "rtb_success_rate": 0.995,
        "mean_time_to_deconflict_s": 2.1,
        "reproducible": 1.0,
    }
)


def manifest() -> dict[str, Any]:
    """도구 간 교환용 기고 매니페스트(JSON 직렬화 가능)."""
    return {
        "contribution": "ASTM F38 — Swarm Airspace Control Test Methods (draft)",
        "phase": "ODYSSEY-461",
        "proposed": True,
        "method_count": len(_METHODS),
        "methods": [
            {
                "method_id": m.method_id,
                "title": m.title,
                "metric_key": m.metric_key,
                "units": m.units,
                "threshold": m.threshold,
                "direction": m.direction,
                "proposed": m.proposed,
            }
            for m in _METHODS
        ],
    }


def _escape_md(text: str) -> str:
    return text.replace("|", "\\|")


def markdown_table() -> str:
    """합격 기준표(Markdown)."""
    lines = [
        "| ID | 시험 방법 | 지표 | 단위 | 합격 기준 |",
        "|---|---|---|---|---|",
    ]
    for m in _METHODS:
        op = "≥" if m.direction == DIRECTION_GE else "≤"
        crit = f"{op} {m.threshold:g} {m.units}"
        lines.append(
            f"| {m.method_id} | {_escape_md(m.title)} | `{m.metric_key}` | "
            f"{m.units} | {crit} |"
        )
    return "\n".join(lines)


def _cli(argv: list[str]) -> int:
    if "--validate" in argv:
        result = validate_registry()
        print(f"valid={result.is_valid} errors={len(result.errors)} "
              f"warnings={len(result.warnings)}")
        for e in result.errors:
            print(f"  ERROR: {e}")
        for w in result.warnings:
            print(f"  WARN: {w}")
        return 0 if result.is_valid else 1
    if "--manifest" in argv:
        print(json.dumps(manifest(), ensure_ascii=False, indent=2))
        return 0
    if "--markdown" in argv:
        print(markdown_table())
        return 0
    if "--evaluate" in argv:
        result = evaluate_suite(SDACS_BASELINE)
        print(f"SDACS 실측 기준선 판정: {result.summary()}")
        for o in result.outcomes:
            print(f"  {o.method_id}: {o.verdict} "
                  f"(measured={o.measured} {o.direction} {o.threshold})")
        return 0
    # 기본: --list
    for m in _METHODS:
        op = "≥" if m.direction == DIRECTION_GE else "≤"
        print(f"{m.method_id}  {m.title}")
        print(f"    {m.metric_key} {op} {m.threshold:g} {m.units}  (proposed)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_cli(sys.argv[1:]))
