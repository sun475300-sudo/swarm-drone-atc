"""ODYSSEY Phase 405 — 국제 벤치마크 비교 (SDACS · BlueSky · U-TRAFMAN).

SDACS 를 공개된 두 오픈소스 항공/무인 교통 시뮬레이터 — **BlueSky**(TU Delft 유인
ATM/ATC)·**U-TRAFMAN**(스페인 I3A-NavSys 무인 교통관리) — 와 **동일한 비교 축
(axis)** 으로 정렬해 객관적으로 대조하는 결정적 데이터 모듈이다. ODYSSEY 국제 확장
("국제 벤치마크 제출 — 비교 시나리오 공개")에서 SDACS 의 좌표를 학계·산업 도구
지형 위에 정직하게 자리매김하기 위한 기준선이며, Phase 465 가 큐레이션한 공개 표준
스위트 ``SDACS-SBS-10`` 을 제출 단위로 묶는다.

비교 대상 (공개 근거)
--------------------
- **SDACS**(본 프로젝트): 군집 드론 UTM·공역통제 자동화. 4계층 아키텍처(드론 10Hz
  → 제어 1Hz → 시뮬 → UI). 공개 리포 ``sun475300-sudo/swarm-drone-atc``.
- **BlueSky**(TU Delft CNS/ATM): 유인 항공교통 시뮬레이터, Python 3, GNU GPL v3.
  ASAS 플러그형 CD&R(상태기반). 근거: J.M. Hoekstra & J. Ellerbroek,
  *"BlueSky ATC Simulator Project: an Open Data and Open Source Approach"*,
  ICRAT 2016; ``github.com/TUDelft-CNS-ATM/bluesky``.
- **U-TRAFMAN**(Univ. Castilla-La Mancha, I3A-NavSys): 무인 교통관리(UTM)
  시뮬레이터, ROS+Gazebo+Matlab, GNU GPL v3. 근거: J. Jover, R. Casado,
  A. Bermúdez, *"U-TRAFMAN: Unmanned traffic management simulator"*,
  SoftwareX, 2025; ``github.com/I3A-NavSys/utrafman_sim``.

정직 공시 (CLAUDE.md)
--------------------
- 본 모듈은 세 도구의 *기능적 위치 설정* 이며 성능 우열 주장이 아니다. 각 축의
  값은 ``citation`` 으로 근거를 명시한다 — 외부 도구는 권위 있는 공개 문헌,
  SDACS 는 프로젝트 설계 문서(CLAUDE.md·docs/)를 가리킨다.
- SDACS 의 능력 주장은 ``evidence`` 로 **실재하는 리포 모듈/산출물 경로** 를
  가리켜 디스크 실재를 강제한다(``test_sdacs_evidence_exists_on_disk``). 외부
  도구(BlueSky·U-TRAFMAN)는 본 리포에서 검증 불가하므로 ``evidence`` 가 없다
  — 그 비대칭을 ``evidence`` 부재로 정직 표면화한다.
- 외부 도구의 능력은 공개 문헌이 기술하는 *설계 초점* 에 한정해 보수적으로
  요약한다(미검증 수치·우열 단정 금지).

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python -m simulation.benchmark_comparison --matrix       # 전체 비교 매트릭스
    python -m simulation.benchmark_comparison --tool sdacs   # 도구별 프로파일
    python -m simulation.benchmark_comparison --dimension conflict_method  # 축별 대조
    python -m simulation.benchmark_comparison --evidence     # SDACS 근거 커버리지
    python -m simulation.benchmark_comparison --submission   # 벤치마크 제출 매니페스트(JSON)
"""
from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TypedDict

from simulation import standard_scenarios

# 제출 식별자·버전 (International Benchmark Comparison)
SUBMISSION_ID = "SDACS-IBC-1"
SUBMISSION_VERSION = "1.0"

# 비교 축(axis) — 세 도구에 동일하게 적용되는 비교 차원.
# (id, 한 줄 라벨) 순서가 매트릭스 행 정렬 순서를 결정한다.
DIMENSIONS: tuple[tuple[str, str], ...] = (
    ("domain", "대상 도메인"),
    ("license", "라이선스·공개성"),
    ("conflict_method", "충돌 탐지·해결(CD&R) 방식"),
    ("traffic_model", "교통·기체 모델 입도"),
    ("swarm_support", "군집/다중에이전트 지원"),
    ("weather_model", "기상·바람 모델"),
    ("federation", "연합·다중 USS 운영"),
    ("reproducibility", "재현성·시나리오 정의"),
)

_DIMENSION_IDS: tuple[str, ...] = tuple(d for d, _ in DIMENSIONS)

# 도구 키 → 정렬은 사전식(매트릭스 열 순서 고정).
TOOL_KEYS: tuple[str, ...] = ("bluesky", "sdacs", "utrafman")
assert list(TOOL_KEYS) == sorted(TOOL_KEYS), "TOOL_KEYS must stay alphabetically sorted"


@dataclass(frozen=True)
class ComparisonAttribute:
    """한 도구의 한 비교 축에 대한 값 + 근거."""

    dimension: str          # 비교 축 id (DIMENSIONS 중 하나)
    value: str              # 해당 도구의 해당 축 요약
    citation: str           # 권위 있는 공개 문서·조항
    evidence: str | None = None  # 디스크 실재 리포 경로(SDACS 능력 주장 한정), 없으면 None

    def __post_init__(self) -> None:
        if self.dimension not in _DIMENSION_IDS:
            raise ValueError(
                f"dimension must be one of {_DIMENSION_IDS}, got {self.dimension!r}"
            )
        if not self.value or not self.value.strip():
            raise ValueError("value must be a non-empty string")
        if not self.citation or not self.citation.strip():
            raise ValueError("citation must be a non-empty string")
        if self.evidence is not None and not self.evidence.strip():
            raise ValueError("evidence must be None or a non-empty repo path")


@dataclass(frozen=True)
class SimulatorProfile:
    """비교 대상 시뮬레이터 한 종의 프로파일."""

    key: str            # 'sdacs'·'bluesky'·'utrafman'
    name: str           # 표시 명칭
    origin: str         # 개발 주체
    license: str        # 라이선스
    reference: str      # 1차 공개 근거(논문/리포)
    url: str            # 공개 URL
    attributes: tuple[ComparisonAttribute, ...]

    def __post_init__(self) -> None:
        if self.key not in TOOL_KEYS:
            raise ValueError(f"key must be one of {TOOL_KEYS}, got {self.key!r}")
        for field_name in ("name", "origin", "license", "reference", "url"):
            if not getattr(self, field_name) or not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        # 모든 비교 축을 정확히 1회씩 보유해야 매트릭스가 정렬된다(빈칸·중복 금지).
        dims = [a.dimension for a in self.attributes]
        if sorted(dims) != sorted(_DIMENSION_IDS):
            raise ValueError(
                f"{self.key} attributes must cover each dimension exactly once; "
                f"got {sorted(dims)}"
            )

    @property
    def is_subject(self) -> bool:
        """비교 주체(SDACS) 여부 — 근거(evidence) 검증 대상."""
        return self.key == "sdacs"

    def attribute(self, dimension: str) -> ComparisonAttribute:
        """비교 축으로 이 도구의 속성을 조회한다. 없으면 KeyError."""
        for attr in self.attributes:
            if attr.dimension == dimension:
                return attr
        raise KeyError(f"{self.key} has no attribute for dimension {dimension!r}")


def _attrs(*items: tuple[str, str, str] | tuple[str, str, str, str | None]
           ) -> tuple[ComparisonAttribute, ...]:
    """(dimension, value, citation[, evidence]) 튜플들을 속성 객체로 변환한다."""
    out: list[ComparisonAttribute] = []
    for item in items:
        if len(item) == 4:
            d, v, c, e = item
            out.append(ComparisonAttribute(d, v, c, e))
        else:
            d, v, c = item
            out.append(ComparisonAttribute(d, v, c))
    return tuple(out)


# 비교 카탈로그 (정본). SDACS 속성은 evidence 로 리포 실재 경로를 결속.
PROFILES: tuple[SimulatorProfile, ...] = (
    SimulatorProfile(
        "sdacs", "SDACS", "본 프로젝트(swarm-drone-atc)",
        "공개 리포(학술 재현 산출물)",
        "SDACS 4계층 아키텍처 — SimPy 이산사건 + Dash 3D",
        "github.com/sun475300-sudo/swarm-drone-atc",
        _attrs(
            ("domain",
             "군집 드론 UTM·공역통제 자동화 — 저고도(0-240m) 다중 드론 분리·충돌해결",
             "CLAUDE.md §5·§7 4계층 아키텍처"),
            ("license",
             "공개 리포 + 인용 메타데이터(CITATION) — 학술 재현 가능",
             "리포 CITATION.cff", "CITATION.cff"),
            ("conflict_method",
             "APF(인공 퍼텐셜장)+CBS(충돌기반탐색) 하이브리드, 강풍 모드 자동전환",
             "docs/CBS_COMPLETENESS_OPTIMALITY.md",
             "src/autonomy/hybrid_collision_avoidance.py"),
            ("traffic_model",
             "10Hz SimPy 이산사건 드론 에이전트(개별 동역학·배터리)",
             "CLAUDE.md §7 Layer 1", "simulation/drone_agent.py"),
            ("swarm_support",
             "다수 드론 군집 동시 시뮬레이션 — 군무·자율 비계획 편대 시나리오",
             "CLAUDE.md §7 군집 다중 에이전트",
             "config/scenario_params/swarm_autonomous_no_preplan.yaml"),
            ("weather_model",
             "바람장·기상 외란 모델(풍속 >10 m/s 시 APF 강풍 모드 자동전환)",
             "CLAUDE.md §8 APF 강풍 모드", "simulation/weather.py"),
            ("federation",
             "다중 인스턴스 연합(inter-USS) — HLC 워터마크 인과-안정 배달",
             "docs/SIMULATOR_ODYSSEY_PLAN.md Track 🛰",
             "simulation/federation_causal_delivery.py"),
            ("reproducibility",
             "np.random.default_rng(seed) 결정적 시드 + YAML 시나리오 + Monte Carlo 스윕",
             "docs/REPRODUCIBILITY.md", "simulation/monte_carlo.py"),
        ),
    ),
    SimulatorProfile(
        "bluesky", "BlueSky", "TU Delft (CNS/ATM)",
        "GNU GPL v3",
        "Hoekstra & Ellerbroek, BlueSky ATC Simulator Project, ICRAT 2016",
        "github.com/TUDelft-CNS-ATM/bluesky",
        _attrs(
            ("domain",
             "유인 항공교통(ATM/ATC) — en-route·TMA 고정익 항공기(도시 드론 확장 연구)",
             "Hoekstra & Ellerbroek, ICRAT 2016"),
            ("license",
             "오픈소스 GNU GPL v3, Python 3(numpy·Qt/pygame)",
             "github.com/TUDelft-CNS-ATM/bluesky (LICENSE GPLv3)"),
            ("conflict_method",
             "ASAS — 플러그형 상태기반 CD&R(예: MVP·SSD), 분리보증 알고리즘 비교 평가",
             "BlueSky ASAS/CD&R 모듈 (Hoekstra et al.)"),
            ("traffic_model",
             "항공기 성능 모델(BADA/OpenAP) 기반 고정익 4D 궤적",
             "BlueSky aircraft performance (BADA/OpenAP)"),
            ("swarm_support",
             "대규모 항공기 다수 시뮬레이션 — 드론 군집 자율편대 전용 아님",
             "BlueSky scenario(.scn) 다중 항공기 모델"),
            ("weather_model",
             "바람(wind) 입력·필드 지원, 기상 외란은 시나리오 명령 의존",
             "BlueSky wind/scenario 명령"),
            ("federation",
             "단일 시뮬레이션 엔진 중심 — 다중 USS 연합은 설계 초점 아님",
             "BlueSky 아키텍처(단일 sim 엔진)"),
            ("reproducibility",
             "결정적 .scn 시나리오 스크립트로 재현",
             "BlueSky scenario(.scn) 파일 형식"),
        ),
    ),
    SimulatorProfile(
        "utrafman", "U-TRAFMAN", "Univ. Castilla-La Mancha (I3A-NavSys)",
        "GNU GPL v3",
        "Jover, Casado & Bermúdez, U-TRAFMAN, SoftwareX 2025",
        "github.com/I3A-NavSys/utrafman_sim",
        _attrs(
            ("domain",
             "무인 교통관리(UTM) — 드론 U-space 서비스 시뮬레이션",
             "Jover et al., U-TRAFMAN, SoftwareX 2025"),
            ("license",
             "오픈소스 GNU GPL v3, ROS+Gazebo+Matlab 통합",
             "github.com/I3A-NavSys/utrafman_sim (LICENSE GPLv3)"),
            ("conflict_method",
             "UTM 서비스 수준 전략적 디컨플릭션(궤적 사전 조정)",
             "U-TRAFMAN UTM 서비스 모델 (Jover et al.)"),
            ("traffic_model",
             "ROS+Gazebo 물리 엔진 기반 개별 드론 비행 시뮬레이션",
             "U-TRAFMAN ROS/Gazebo 통합 (SoftwareX 2025)"),
            ("swarm_support",
             "다수 드론 UTM 시나리오 — 확장 가능 기능셋",
             "U-TRAFMAN 확장형 아키텍처 (Jover et al.)"),
            ("weather_model",
             "Gazebo 물리 환경 — 기상 모델은 플러그인/확장 의존",
             "U-TRAFMAN Gazebo 시뮬레이션 환경"),
            ("federation",
             "UTM 중앙 서비스 모델 — 다중 USS 연합은 설계 초점 아님",
             "U-TRAFMAN UTM 시스템 모델"),
            ("reproducibility",
             "ROS/Matlab 설정 기반 재현, 공개 리포 제공",
             "github.com/I3A-NavSys/utrafman_sim 공개 리포"),
        ),
    ),
)


def simulators() -> tuple[SimulatorProfile, ...]:
    """비교 대상 도구를 키 사전식 정렬로 반환한다."""
    return tuple(sorted(PROFILES, key=lambda p: p.key))


def find_simulator(key: str) -> SimulatorProfile:
    """도구 키로 프로파일을 조회한다. 없으면 KeyError."""
    for prof in PROFILES:
        if prof.key == key:
            return prof
    raise KeyError(f"unknown simulator key: {key!r}")


def dimension_label(dimension: str) -> str:
    """비교 축 id 의 한 줄 라벨을 반환한다. 없으면 KeyError."""
    for dim, label in DIMENSIONS:
        if dim == dimension:
            return label
    raise KeyError(f"unknown dimension: {dimension!r}")


def compare_dimension(dimension: str) -> Mapping[str, ComparisonAttribute]:
    """한 비교 축에 대해 {도구키: 속성} 읽기 전용 매핑을 반환한다(전 도구 정렬)."""
    if dimension not in _DIMENSION_IDS:
        raise ValueError(f"unknown dimension: {dimension!r}")
    return MappingProxyType(
        {prof.key: prof.attribute(dimension) for prof in simulators()}
    )


class MatrixCell(TypedDict):
    """한 도구의 한 축 셀 (값 + 인용 + 근거)."""

    value: str
    citation: str
    evidence: str | None


class MatrixRow(TypedDict):
    """비교 매트릭스 한 행 (한 축, 전 도구)."""

    dimension: str
    label: str
    tools: Mapping[str, MatrixCell]


def comparison_matrix() -> tuple[MatrixRow, ...]:
    """도구 간 교환용 비교 매트릭스를 (축 정렬) 행으로 반환한다.

    각 행은 한 비교 축에 대한 전 도구 값/인용/근거를 담는다. 각 행의 ``tools``
    매핑은 읽기 전용(``MappingProxyType``)이라 하류 소비자가 도구 셀을 변조할 수
    없다(행 dict 자체는 sibling Phase 409 와 동일하게 가변 컨테이너).
    """
    rows: list[MatrixRow] = []
    for dim in _DIMENSION_IDS:
        cells: dict[str, MatrixCell] = {}
        for prof in simulators():
            attr = prof.attribute(dim)
            cells[prof.key] = {
                "value": attr.value,
                "citation": attr.citation,
                "evidence": attr.evidence,
            }
        rows.append({
            "dimension": dim,
            "label": dimension_label(dim),
            "tools": MappingProxyType(cells),
        })
    return tuple(rows)


def sdacs_evidence() -> Mapping[str, str | None]:
    """SDACS 의 축별 근거(디스크 실재 경로)를 읽기 전용 매핑으로 반환한다.

    근거가 단일 모듈로 환원되지 않는 축(도메인 정의 등)은 ``None`` 으로 정직
    표면화한다.
    """
    sdacs = find_simulator("sdacs")
    return MappingProxyType(
        {dim: sdacs.attribute(dim).evidence for dim in _DIMENSION_IDS}
    )


def cited_evidence_paths() -> tuple[str, ...]:
    """SDACS 가 인용한 근거 경로를 중복 제거·정렬로 반환한다(None 제외)."""
    sdacs = find_simulator("sdacs")
    return tuple(sorted({
        a.evidence for a in sdacs.attributes if a.evidence is not None
    }))


@dataclass(frozen=True)
class EvidenceReport:
    """SDACS 능력 주장의 디스크 근거 커버리지 요약."""

    total_dimensions: int
    with_evidence: int
    without_evidence: int

    def __post_init__(self) -> None:
        if min(self.total_dimensions, self.with_evidence, self.without_evidence) < 0:
            raise ValueError("counts must be non-negative")
        if self.with_evidence + self.without_evidence != self.total_dimensions:
            raise ValueError(
                f"with_evidence ({self.with_evidence}) + without_evidence "
                f"({self.without_evidence}) != total ({self.total_dimensions})"
            )

    @property
    def evidence_pct(self) -> float:
        """디스크 근거를 가진 축 비율 (%)."""
        if self.total_dimensions == 0:
            return 0.0
        return 100.0 * self.with_evidence / self.total_dimensions


def evidence_report() -> EvidenceReport:
    """SDACS 의 축별 근거 보유 현황을 집계한 결정적 리포트를 생성한다."""
    ev = sdacs_evidence()
    with_ev = sum(1 for v in ev.values() if v is not None)
    total = len(ev)
    return EvidenceReport(
        total_dimensions=total,
        with_evidence=with_ev,
        without_evidence=total - with_ev,
    )


def submission_manifest() -> dict:
    """국제 벤치마크 제출용 매니페스트(JSON 직렬화 가능)를 생성한다.

    SDACS 가 제출하는 공개 표준 스위트(``SDACS-SBS-10``, Phase 465)와 본
    비교 매트릭스를 하나의 제출 단위로 묶는다. 외부 도구의 결과 수치는 담지
    않는다(미검증 우열 단정 금지) — 제출하는 것은 *스위트 정의* 와 *기능적
    위치 설정* 이다. ``comparators`` 는 비교 *대상* 만 담고 비교 주체(SDACS)는
    ``subject`` 로 분리한다.

    주의: ``standard_scenarios.benchmark_manifest()`` 를 통해 10개 시나리오
    YAML 을 읽으므로 디스크 I/O 가 발생한다(소스 부재 시 ``FileNotFoundError``).
    """
    matrix = [
        {
            "dimension": row["dimension"],
            "label": row["label"],
            "tools": {k: dict(v) for k, v in row["tools"].items()},
        }
        for row in comparison_matrix()
    ]
    suite = standard_scenarios.benchmark_manifest()
    report = evidence_report()
    return {
        "submission_id": SUBMISSION_ID,
        "version": SUBMISSION_VERSION,
        "subject": "sdacs",
        "comparators": [
            {
                "key": p.key,
                "name": p.name,
                "origin": p.origin,
                "license": p.license,
                "reference": p.reference,
                "url": p.url,
            }
            for p in simulators()
            if not p.is_subject
        ],
        "dimensions": [{"id": d, "label": label} for d, label in DIMENSIONS],
        "comparison_matrix": matrix,
        "benchmark_suite": {
            "suite_id": suite["suite_id"],
            "version": suite["version"],
            "count": suite["count"],
        },
        "sdacs_evidence_coverage": {
            "with_evidence": report.with_evidence,
            "total_dimensions": report.total_dimensions,
            "evidence_pct": round(report.evidence_pct, 1),
        },
    }


def _format_matrix() -> str:
    lines = ["국제 벤치마크 비교 매트릭스 (SDACS · BlueSky · U-TRAFMAN)", ""]
    keys = [p.key for p in simulators()]
    for row in comparison_matrix():
        lines.append(f"■ {row['label']} [{row['dimension']}]")
        cells = row["tools"]
        for key in keys:
            cell = cells[key]
            lines.append(f"   {key}: {cell['value']}")
            lines.append(f"       ↳ {cell['citation']}")
            if cell["evidence"]:
                lines.append(f"       ✓ 근거: {cell['evidence']}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _format_tool(prof: SimulatorProfile) -> str:
    lines = [
        f"{prof.name} [{prof.key}] — {prof.origin}",
        f"  라이선스: {prof.license}",
        f"  근거: {prof.reference}",
        f"  URL: {prof.url}",
        "",
    ]
    for dim in _DIMENSION_IDS:
        attr = prof.attribute(dim)
        lines.append(f"  [{dimension_label(dim)}] {attr.value}")
        lines.append(f"      ↳ {attr.citation}")
        if attr.evidence:
            lines.append(f"      ✓ 근거: {attr.evidence}")
    return "\n".join(lines)


def _format_evidence() -> str:
    r = evidence_report()
    lines = [
        "SDACS 능력 주장 디스크 근거 커버리지",
        "",
        f"근거 보유 축: {r.with_evidence}/{r.total_dimensions} ({r.evidence_pct:.0f}%)",
        "",
    ]
    for dim, label in DIMENSIONS:
        path = sdacs_evidence()[dim]
        mark = "✓" if path else "—(축 정의·단일 모듈 환원 불가)"
        lines.append(f"  {mark} [{label}] {path or ''}".rstrip())
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="국제 벤치마크 비교 (ODYSSEY Phase 405)"
    )
    parser.add_argument("--matrix", action="store_true", help="전체 비교 매트릭스 출력")
    parser.add_argument("--tool", choices=TOOL_KEYS, help="도구별 프로파일 출력")
    parser.add_argument(
        "--dimension", choices=_DIMENSION_IDS, help="비교 축별 전 도구 대조 출력"
    )
    parser.add_argument("--evidence", action="store_true", help="SDACS 근거 커버리지 출력")
    parser.add_argument(
        "--submission", action="store_true", help="벤치마크 제출 매니페스트(JSON) 출력"
    )
    args = parser.parse_args(argv)

    if args.matrix:
        print(_format_matrix())
    elif args.tool:
        print(_format_tool(find_simulator(args.tool)))
    elif args.dimension:
        print(f"■ {dimension_label(args.dimension)} [{args.dimension}]")
        for key, attr in compare_dimension(args.dimension).items():
            print(f"   {key}: {attr.value}")
            print(f"       ↳ {attr.citation}")
            if attr.evidence:
                print(f"       ✓ 근거: {attr.evidence}")
    elif args.evidence:
        print(_format_evidence())
    elif args.submission:
        print(json.dumps(submission_manifest(), ensure_ascii=False, indent=2))
    else:
        print(_format_matrix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
