"""ODYSSEY Phase 405 — 국제 벤치마크 제출(BlueSky·U-TRAFMAN 비교).

Phase 465 가 큐레이션한 공개 표준 스위트 ``SDACS-SBS-10`` 의 10개 시나리오를,
공개 항공/UTM 시뮬레이터 **BlueSky** 와 **U-TRAFMAN** 의 모델링 역량에 결정적으로
대응시키는 *구조적* 비교 매트릭스다. "SDACS 의 표준 시나리오를 외부 도구로 교차
비교 제출하려면, 각 시나리오가 외부 도구에서 어떻게(또는 *어디까지만*) 표현되는가"
를 답한다.

정직 공시 (CLAUDE.md)
--------------------
- 본 모듈은 외부 도구의 **구조적 표현 가능성**(어떤 운용 차원을 모델링하는가)에
  대한 *기능적 요약* 이며, **성능 수치(벤치마크 결과)를 산출하거나 인용하지 않는다**.
  외부 도구 역량 평가는 각 도구의 **공개 문서/논문 기준**(``as_of`` 스냅샷)이다.
- ``status`` 는 3값 — ``direct``(해당 축을 외부 도구가 1차로 모델링), ``partial``
  (스크립팅/우회로 부분 표현), ``none``(해당 축을 표현하는 모델 부재).
  **정직성 결속**: ``status == 'none'`` ⟺ ``analog is None`` (없는 대응을 있다고
  주장 불가). 그 외(direct/partial)는 반드시 비공백 ``analog`` 를 보유.
- 비교 대상 식별자·통제 축은 Phase 465 ``standard_scenarios`` 가 **유일 출처(SSoT)**
  이며 본 모듈은 복제하지 않고 참조한다(``test_benchmark_ids_match_sbs10`` 가
  10종 식별자·축 일치를 강제).

근거 (공개 문서)
---------------
- **BlueSky** — Open Air Traffic Simulator, TU Delft CNS/ATM.
  Hoekstra & Ellerbroek, "BlueSky ATC Simulator Project: an Open Data and Open
  Source Approach", ICRAT 2016. github.com/TUDelft-CNS-ATM/bluesky. 전통 ATM·
  상태기반 충돌탐지/해소(MVP·SSD)·바람장·시나리오(.scn) 스크립팅을 1차 모델링.
  UTM 연합·보안 침입·군집 자율 편대는 모델 부재(연구 확장 별개).
- **U-TRAFMAN** — UAS Traffic Management 연구 시뮬레이터(에이전트 기반 UTM 운용·
  전략적 디컨플릭션·다중 운영자). UTM 운용 흐름을 1차 모델링하나 적대적 보안·
  군집 자율 편대는 평가 축 밖.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI (Phase 465 와 동일하게 패키지 모듈 형태로 실행):
    python -m simulation.benchmark_external_compare --matrix       # 전체 비교 매트릭스
    python -m simulation.benchmark_external_compare --report       # 도구별 비교 가능성 집계
    python -m simulation.benchmark_external_compare --tool bluesky # 도구별 대응 상세
    python -m simulation.benchmark_external_compare --gaps         # 표현 불가(none) 축
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TypedDict

from simulation.standard_scenarios import BENCHMARK_SET, get_scenario

# 비교 대상 외부 도구 — 결정적 정렬 순서.
TOOLS: tuple[str, str] = ("bluesky", "u_trafman")

# status 허용 집합 + 비교 가능성 가중치(direct 1.0·partial 0.5·none 0.0).
_STATUS_WEIGHT: Mapping[str, float] = MappingProxyType({
    "direct": 1.0,
    "partial": 0.5,
    "none": 0.0,
})

_BLUESKY_CITE = (
    "Hoekstra & Ellerbroek, BlueSky ATC Simulator Project, ICRAT 2016 "
    "(github.com/TUDelft-CNS-ATM/bluesky)"
)
_UTRAFMAN_CITE = "U-TRAFMAN, UAS Traffic Management 연구 시뮬레이터 (공개 문서 기준)"
# 외부 도구 역량 평가의 스냅샷 시점(도구는 갱신되므로 시점 명시 필수).
_AS_OF = "2026-06"
assert _AS_OF and _AS_OF.strip(), "_AS_OF 스냅샷 시점은 비공백이어야 한다"


@dataclass(frozen=True)
class ToolAnalog:
    """한 외부 도구에서의 대응 표현 (불변).

    Attributes:
        tool: 외부 도구 식별자(``TOOLS`` 중 하나).
        status: ``direct``·``partial``·``none``.
        analog: 외부 도구 내 대응 시나리오/역량 이름. ``status=='none'`` 이면
            반드시 ``None``, 그 외엔 반드시 비공백.
        note: 대응/한계에 대한 한 줄 근거.
        citation: 평가 근거가 된 외부 도구 공개 문서.
    """

    tool: str
    status: str
    analog: str | None
    note: str
    citation: str

    def __post_init__(self) -> None:
        if self.tool not in TOOLS:
            raise ValueError(f"알 수 없는 도구: {self.tool!r}")
        if self.status not in _STATUS_WEIGHT:
            raise ValueError(f"알 수 없는 status: {self.status!r}")
        # 정직성 결속 — 없는 대응을 있다고/있는 대응을 없다고 주장 불가.
        if self.status == "none":
            if self.analog is not None:
                raise ValueError("status 'none' 은 analog 가 None 이어야 한다")
        else:
            if not self.analog or not self.analog.strip():
                raise ValueError(f"status {self.status!r} 은 비공백 analog 필요")
        if not self.note.strip():
            raise ValueError("note 는 비공백이어야 한다")
        if not self.citation.strip():
            raise ValueError("citation 은 비공백이어야 한다")

    @property
    def weight(self) -> float:
        """비교 가능성 가중치(direct 1.0·partial 0.5·none 0.0)."""
        return _STATUS_WEIGHT[self.status]


@dataclass(frozen=True)
class ScenarioComparison:
    """SBS-10 한 시나리오의 외부 도구 대응 (불변).

    ``benchmark_id`` 는 Phase 465 SBS-10 의 실재 식별자여야 하며, ``analogs`` 는
    ``TOOLS`` 와 정확히 1:1(누락·중복·미지 도구 거부)이다.
    """

    benchmark_id: str
    analogs: tuple[ToolAnalog, ...]

    def __post_init__(self) -> None:
        # SSoT 결속 — SBS-10 에 없는 식별자 거부(존재 시 KeyError).
        get_scenario(self.benchmark_id)
        tools = [a.tool for a in self.analogs]
        if sorted(tools) != sorted(TOOLS):
            raise ValueError(
                f"{self.benchmark_id}: analogs 는 {TOOLS} 와 1:1 이어야 한다 (got {tools})"
            )

    def for_tool(self, tool: str) -> ToolAnalog:
        """도구별 대응을 조회한다.

        Raises:
            KeyError: 해당 도구 대응이 없을 때(형상상 발생 불가).
        """
        for analog in self.analogs:
            if analog.tool == tool:
                return analog
        raise KeyError(f"{self.benchmark_id}: 도구 대응 없음 {tool!r}")


def _a(tool: str, status: str, analog: str | None, note: str) -> ToolAnalog:
    cite = _BLUESKY_CITE if tool == "bluesky" else _UTRAFMAN_CITE
    return ToolAnalog(tool, status, analog, note, cite)


# 비교 매트릭스 — B01..B10 결정적 순서. 외부 도구가 표현 못 하는 축(보안·군집
# 자율)은 양 도구 모두 none 으로 정직 표면화(SDACS 스위트가 외부 도구 범위를 초과).
COMPARISONS: tuple[ScenarioComparison, ...] = (
    ScenarioComparison("B01", (
        _a("bluesky", "direct", "고밀도 교통 시나리오(.scn)",
           "다수 항적 동시 시뮬레이션이 BlueSky 1차 용도."),
        _a("u_trafman", "direct", "UTM 밀도/용량 시나리오",
           "UTM 운용 밀도·용량 연구가 핵심 대상."),
    )),
    ScenarioComparison("B02", (
        _a("bluesky", "partial", "스크립트 기반 항적 이상",
           "기체 상태 변경은 스크립팅 가능하나 전용 고장 모드 모델 부재."),
        _a("u_trafman", "partial", "비상(contingency) 이벤트",
           "운용 비상 처리 표현 가능하나 세부 고장 동역학은 범위 밖."),
    )),
    ScenarioComparison("B03", (
        _a("bluesky", "partial", "시각 분리 출발 스케줄",
           "시나리오 타이밍으로 이륙 서지 근사, 전용 vertiport 모델 부재."),
        _a("u_trafman", "partial", "운용 요청 서지",
           "다중 운용 요청 도착으로 서지 근사."),
    )),
    ScenarioComparison("B04", (
        _a("bluesky", "direct", "CD&R 충돌 시나리오(MVP/SSD)",
           "상태기반 충돌탐지/해소가 BlueSky 핵심 역량."),
        _a("u_trafman", "direct", "전략적 디컨플릭션 케이스",
           "전략적 디컨플릭션이 UTM 시뮬레이터 1차 기능."),
    )),
    ScenarioComparison("B05", (
        _a("bluesky", "none", None,
           "C2 두절 UTM 비상 절차 모델 부재(전통 ATC 관제 가정)."),
        _a("u_trafman", "partial", "C2 링크 두절 절차",
           "UTM 비상 절차로 lost-link 근사 가능."),
    )),
    ScenarioComparison("B06", (
        _a("bluesky", "direct", "바람장 시나리오",
           "바람장(wind field) 입력을 BlueSky 가 1차 지원."),
        _a("u_trafman", "partial", "기상 교란 효과",
           "기상 영향 표현 가능하나 바람장 충실도는 도구별."),
    )),
    ScenarioComparison("B07", (
        _a("bluesky", "none", None,
           "적대적 침입/보안은 교통 시뮬레이터 모델 범위 밖."),
        _a("u_trafman", "none", None,
           "적대적 침입/보안은 UTM 교통 시뮬레이터 평가 축 밖."),
    )),
    ScenarioComparison("B08", (
        _a("bluesky", "none", None,
           "단일 공역/관제 영역 가정 — 지역 간 연합 핸드오버 모델 부재."),
        _a("u_trafman", "partial", "다중 운영자 조율",
           "다중 운영자 조율로 연합 일부 근사, 지역 간 핸드오버는 제한적."),
    )),
    ScenarioComparison("B09", (
        _a("bluesky", "none", None,
           "고정익 ATM 중심 — 군집 자율 편대 모델 부재."),
        _a("u_trafman", "none", None,
           "UTM 교통 흐름 중심 — 군집 자율 편대는 평가 축 밖."),
    )),
    ScenarioComparison("B10", (
        _a("bluesky", "direct", "공칭 저밀도 교통 시나리오",
           "공칭 기준선은 양 도구에서 자명하게 표현 가능."),
        _a("u_trafman", "direct", "공칭 UTM 기준선",
           "공칭 저밀도 운용은 UTM 시뮬레이터 기본 케이스."),
    )),
)


def all_comparisons() -> tuple[ScenarioComparison, ...]:
    """결정적 순서의 10종 비교를 반환한다."""
    return COMPARISONS


def get_comparison(benchmark_id: str) -> ScenarioComparison:
    """벤치마크 식별자로 비교를 조회한다.

    Raises:
        KeyError: 알 수 없는 식별자.
    """
    for comp in COMPARISONS:
        if comp.benchmark_id == benchmark_id:
            return comp
    raise KeyError(f"알 수 없는 벤치마크 식별자: {benchmark_id!r}")


class ToolComparability(TypedDict):
    """도구별 비교 가능성 집계(JSON 직렬화 가능)."""

    tool: str
    direct: int
    partial: int
    none: int
    total: int
    score: float


def comparability_report(tool: str) -> ToolComparability:
    """한 외부 도구가 SBS-10 을 얼마나 표현 가능한지 결정적 집계한다.

    Args:
        tool: ``TOOLS`` 중 하나.

    Returns:
        direct/partial/none 카운트 + 가중 비교 가능성 점수(0~1, 소수 4자리).

    Raises:
        ValueError: 알 수 없는 도구.
    """
    if tool not in TOOLS:
        raise ValueError(f"알 수 없는 도구: {tool!r}")
    counts = {"direct": 0, "partial": 0, "none": 0}
    weight_sum = 0.0
    for comp in COMPARISONS:
        analog = comp.for_tool(tool)
        counts[analog.status] += 1
        weight_sum += analog.weight
    total = len(COMPARISONS)
    return {
        "tool": tool,
        "direct": counts["direct"],
        "partial": counts["partial"],
        "none": counts["none"],
        "total": total,
        "score": round(weight_sum / total, 4),
    }


def gaps(tool: str) -> tuple[str, ...]:
    """해당 도구가 표현 못 하는(``none``) 벤치마크 식별자를 결정적 순서로 반환."""
    if tool not in TOOLS:
        raise ValueError(f"알 수 없는 도구: {tool!r}")
    return tuple(
        comp.benchmark_id
        for comp in COMPARISONS
        if comp.for_tool(tool).status == "none"
    )


class MatrixRow(TypedDict):
    """도구 간 교환용 비교 매트릭스 행(JSON 직렬화 가능)."""

    benchmark_id: str
    axis: str
    bluesky_status: str
    bluesky_analog: str | None
    u_trafman_status: str
    u_trafman_analog: str | None


def comparison_matrix() -> tuple[Mapping[str, object], ...]:
    """도구 간 교환용 비교 매트릭스(읽기 전용 행)를 생성한다.

    각 행은 ``MappingProxyType`` 로 동결돼 하류 소비자가 공유 상태를 변조할 수
    없다(JSON 직렬화가 필요하면 호출측에서 ``dict(row)`` 로 복사 — `submission_manifest`
    참조). 매 호출마다 frozen ``COMPARISONS`` 로부터 새 행을 생성한다.
    """
    rows: list[Mapping[str, object]] = []
    for comp in COMPARISONS:
        axis = get_scenario(comp.benchmark_id).axis
        bs = comp.for_tool("bluesky")
        ut = comp.for_tool("u_trafman")
        row: MatrixRow = {
            "benchmark_id": comp.benchmark_id,
            "axis": axis,
            "bluesky_status": bs.status,
            "bluesky_analog": bs.analog,
            "u_trafman_status": ut.status,
            "u_trafman_analog": ut.analog,
        }
        rows.append(MappingProxyType(row))
    return tuple(rows)


def submission_manifest() -> dict[str, object]:
    """국제 벤치마크 제출용 공개 매니페스트(JSON 직렬화 가능)를 생성한다.

    SBS-10 식별자·축·도구별 대응 상태·도구별 비교 가능성 집계를 한 문서로 싣되,
    **성능 수치는 포함하지 않는다**(구조적 비교만).
    """
    # 매니페스트는 JSON 직렬화 스냅샷이라 읽기 전용 행을 plain dict 로 복사한다
    # (호출마다 새로 생성 — 공유 가변 상태 누출 없음).
    return {
        "suite_id": "SDACS-SBS-10",
        "tools": list(TOOLS),
        "as_of": _AS_OF,
        "comparability": {t: dict(comparability_report(t)) for t in TOOLS},
        "matrix": [dict(row) for row in comparison_matrix()],
        "disclaimer": (
            "구조적 표현 가능성 비교(외부 도구 공개 문서 기준). 성능 벤치마크 "
            "수치 아님."
        ),
    }


def _cmd_matrix() -> None:
    print(f"SDACS-SBS-10 × {' / '.join(TOOLS)} 비교 매트릭스 (as_of {_AS_OF})")
    print(f"{'ID':<5}{'AXIS':<22}{'BLUESKY':<10}U-TRAFMAN")
    for row in comparison_matrix():
        print(
            f"{row['benchmark_id']:<5}{row['axis']:<22}"
            f"{row['bluesky_status']:<10}{row['u_trafman_status']}"
        )


def _cmd_report() -> None:
    print(f"비교 가능성 집계 (direct 1.0·partial 0.5·none 0.0, as_of {_AS_OF})")
    for tool in TOOLS:
        rep = comparability_report(tool)
        print(
            f"  {tool:<11} direct {rep['direct']}·partial {rep['partial']}·"
            f"none {rep['none']} → {rep['score'] * 100:.1f}%"
        )


def _cmd_tool(tool: str) -> int:
    if tool not in TOOLS:
        print(f"알 수 없는 도구: {tool!r} (가능: {', '.join(TOOLS)})", file=sys.stderr)
        return 2
    print(f"[{tool}] SBS-10 대응 상세")
    for comp in COMPARISONS:
        analog = comp.for_tool(tool)
        label = analog.analog if analog.analog is not None else "(표현 불가)"
        print(f"  {comp.benchmark_id}  {analog.status:<8}{label}")
        print(f"        ↳ {analog.note}")
    return 0


def _cmd_gaps() -> None:
    print("외부 도구가 표현 못 하는(none) 축:")
    for tool in TOOLS:
        ids = gaps(tool)
        axes = ", ".join(f"{i}({get_scenario(i).axis})" for i in ids) or "없음"
        print(f"  {tool:<11} {axes}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ODYSSEY Phase 405 — BlueSky·U-TRAFMAN 벤치마크 구조 비교",
    )
    parser.add_argument("--matrix", action="store_true", help="전체 비교 매트릭스")
    parser.add_argument("--report", action="store_true", help="도구별 비교 가능성 집계")
    parser.add_argument("--tool", metavar="NAME", help="도구별 대응 상세(bluesky/u_trafman)")
    parser.add_argument("--gaps", action="store_true", help="표현 불가(none) 축")
    parser.add_argument("--manifest", action="store_true", help="제출 매니페스트(JSON)")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    if args.tool:
        return _cmd_tool(args.tool)
    if args.report:
        _cmd_report()
        return 0
    if args.gaps:
        _cmd_gaps()
        return 0
    if args.manifest:
        print(json.dumps(submission_manifest(), ensure_ascii=False, indent=2))
        return 0
    # --matrix 는 명시 플래그이자 무인자 기본 동작.
    _cmd_matrix()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
