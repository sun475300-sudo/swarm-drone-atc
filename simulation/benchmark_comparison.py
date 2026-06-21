"""ODYSSEY Phase 405 — 국제 벤치마크 비교 (BlueSky·U-TRAFMAN).

SDACS 를 공개 ATM/UTM 시뮬레이터 두 곳(BlueSky·U-TRAFMAN)과 **동일한 비교 축**으로
정렬해 대조하는 결정적 데이터 모듈이다. ODYSSEY 국제 확장에서 "SDACS 를 국제 벤치마크에
제출할 때, 확립된 공개 베이스라인 대비 어디가 같고 어디가 갭인가" 를 객관적으로 답한다.

비교 대상 (공개 출처)
--------------------
- **BlueSky** — TU Delft 오픈소스 항공교통 시뮬레이터(GPLv3). Hoekstra & Ellerbroek,
  *"BlueSky ATC Simulator Project: an Open Data and Open Source Approach"*, ICRAT 2016.
  유인 ATM 중심, 대규모(수천 기) 시간진행(time-step) 시뮬·강력한 CD&R.
- **U-TRAFMAN** — 학술 멀티에이전트 UTM 교통관리 연구 시뮬레이터. UAS 비행계획·UTM
  서비스 중심. 공개 연구 산출물.

정직 공시 (CLAUDE.md)
--------------------
1. ``sdacs_module`` 은 해당 비교 축을 *실제로* 제공하는 리포 내 모듈 경로다. 대응 모듈이
   없는 축(유인 항공 통합)은 ``None`` 으로 **갭(gap)** 임을 정직히 표면화한다 —
   ``sdacs_support == 'none'`` ⟺ ``sdacs_module is None`` 정직성 결속을
   ``__post_init__`` 가 강제하고, ``test_cited_modules_exist_on_disk`` 가 인용 경로의
   디스크 실재를 강제한다 (모듈 없는 충족 주장 구조적 금지).
2. BlueSky·U-TRAFMAN 의 지원 수준은 **공개 문서·논문 기술(description) 기반의 프로젝트
   평가**이며, 머리맞댄(head-to-head) 실측 벤치마크 실행 결과가 아니다. 우열 주장이 아니라
   기능 범위 정렬이 목적이다. 이 모듈은 BlueSky 가 더 강한 축(유인 통합·대규모 스케일)도
   정직히 드러낸다.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/benchmark_comparison.py --matrix       # 전체 비교 매트릭스
    python simulation/benchmark_comparison.py --report       # 시스템별 점수 요약
    python simulation/benchmark_comparison.py --system sdacs # 한 시스템 점수
    python simulation/benchmark_comparison.py --category conflict
    python simulation/benchmark_comparison.py --gaps         # SDACS 미충족(갭) 축
    python simulation/benchmark_comparison.py --systems      # 비교 대상 카탈로그
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from types import MappingProxyType

# 비교 대상 시스템 식별자 (정렬·표기 안정 순서).
BENCHMARK_SYSTEMS: tuple[str, ...] = ("sdacs", "bluesky", "u_trafman")

# 지원 수준 3값 및 가중치 (full=1.0·partial=0.5·none=0.0). 읽기 전용.
SUPPORT_LEVELS: tuple[str, ...] = ("full", "partial", "none")
SUPPORT_WEIGHT: MappingProxyType = MappingProxyType(
    {"full": 1.0, "partial": 0.5, "none": 0.0}
)


@dataclass(frozen=True)
class BenchmarkSystem:
    """비교 대상 시스템 메타데이터."""

    system_id: str
    name: str
    origin: str       # 출처/소속
    license: str      # 라이선스 또는 배포 형태
    citation: str     # 권위 있는 공개 출처

    def __post_init__(self) -> None:
        if self.system_id not in BENCHMARK_SYSTEMS:
            raise ValueError(
                f"system_id must be one of {BENCHMARK_SYSTEMS}, got {self.system_id!r}"
            )
        for field_name in ("name", "origin", "license", "citation"):
            value = getattr(self, field_name)
            if not value or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")


# 비교 대상 카탈로그 (정본).
BENCHMARK_SYSTEM_CATALOG: tuple[BenchmarkSystem, ...] = (
    BenchmarkSystem(
        "sdacs",
        "SDACS (Swarm Drone Airspace Control System)",
        "본 프로젝트 (SimPy 이산 이벤트 + Dash 3D)",
        "Apache-2.0 (오픈소스)",
        "본 리포 — 4계층 아키텍처·5계층 안전망 군집 드론 공역통제",
    ),
    BenchmarkSystem(
        "bluesky",
        "BlueSky ATC Simulator",
        "TU Delft (Control & Simulation)",
        "GPLv3 (오픈소스)",
        "Hoekstra & Ellerbroek, 'BlueSky ATC Simulator Project: an Open Data "
        "and Open Source Approach', ICRAT 2016",
    ),
    BenchmarkSystem(
        "u_trafman",
        "U-TRAFMAN (UTM Traffic Manager)",
        "학술 연구 (멀티에이전트 UTM)",
        "공개 연구 산출물",
        "U-TRAFMAN — 멀티에이전트 UAS 교통관리(UTM) 연구 시뮬레이터 (공개 문서 기반)",
    ),
)


@dataclass(frozen=True)
class BenchmarkDimension:
    """단일 비교 축과 세 시스템의 지원 수준 정의."""

    dim_id: str            # 안정 식별자 (예: 'pairwise_cdr')
    name: str              # 비교 축 명칭
    category: str          # 분류 (conflict·planning·environment 등)
    citation: str          # 비교 축을 정의하는 권위 있는 출처
    sdacs_support: str     # full/partial/none
    sdacs_module: str | None  # 제공 모듈 경로 (없으면 갭)
    bluesky_support: str   # full/partial/none (공개 기술 기반 프로젝트 평가)
    u_trafman_support: str  # full/partial/none (공개 기술 기반 프로젝트 평가)
    summary: str           # 한 줄 설명

    def __post_init__(self) -> None:
        if not self.dim_id or self.dim_id != self.dim_id.strip():
            raise ValueError("dim_id must be non-empty and unpadded")
        # 인간 가독 필드는 내부 공백 허용 — 식별자(dim_id)만 패딩 금지.
        for field_name in ("name", "category", "citation", "summary"):
            value = getattr(self, field_name)
            if not value or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        for field_name in ("sdacs_support", "bluesky_support", "u_trafman_support"):
            value = getattr(self, field_name)
            if value not in SUPPORT_LEVELS:
                raise ValueError(
                    f"{field_name} must be one of {SUPPORT_LEVELS}, got {value!r}"
                )
        # 정직성 결속: SDACS 미지원(none) ⟺ 인용 모듈 없음(None).
        if (self.sdacs_support == "none") != (self.sdacs_module is None):
            raise ValueError(
                "sdacs_support=='none' must hold iff sdacs_module is None "
                f"(got support={self.sdacs_support!r}, module={self.sdacs_module!r})"
            )
        if self.sdacs_module is not None and not self.sdacs_module.strip():
            raise ValueError("sdacs_module must be None or a non-empty path")

    def support_for(self, system: str) -> str:
        """주어진 시스템의 이 축 지원 수준을 반환한다."""
        if system == "sdacs":
            return self.sdacs_support
        if system == "bluesky":
            return self.bluesky_support
        if system == "u_trafman":
            return self.u_trafman_support
        raise ValueError(
            f"system must be one of {BENCHMARK_SYSTEMS}, got {system!r}"
        )


# 비교 매트릭스 카탈로그 (정본).
# BlueSky·U-TRAFMAN 수준은 공개 기술 기반 프로젝트 평가 (실측 실행 아님, docstring 참조).
BENCHMARK_DIMENSIONS: tuple[BenchmarkDimension, ...] = (
    BenchmarkDimension(
        "pairwise_cdr", "Pairwise conflict detection & resolution", "conflict",
        "ICAO Doc 4444 분리 기준 — 쌍별 충돌 탐지·회피(CD&R)는 ATM/UTM 벤치마크 핵심 축",
        "full", "simulation/path_deconflict.py",
        "full", "partial",
        "APF + CPA 90초 예측 기반 전술 충돌 회피. BlueSky 는 MVP/SSD CD&R 보유",
    ),
    BenchmarkDimension(
        "strategic_deconfliction", "Strategic 4D deconfliction", "planning",
        "ASTM F3548-21 strategic deconfliction — 사전 4D 경로 분리",
        "full", "simulation/path_deconflict.py",
        "partial", "full",
        "CBS 기반 사전 4D 디컨플릭션. U-TRAFMAN 은 UTM 비행계획 관리 중심으로 강함",
    ),
    BenchmarkDimension(
        "wind_field", "Wind / weather field model", "environment",
        "기상 위험 모델링 — 풍속장은 드론(소형 기체) 시뮬의 정확도 핵심",
        "full", "simulation/weather.py",
        "full", "none",
        "WindModel 풍속장 + APF 강풍 모드(>10 m/s) 자동 전환. BlueSky 는 METAR·실측 바람",
    ),
    BenchmarkDimension(
        "multi_agent_scale", "Multi-agent scalability", "scale",
        "대규모 교통 시뮬 — 동시 처리 기체 수는 시뮬레이터 성능 벤치마크 축",
        "partial", "simulation/simulator.py",
        "full", "partial",
        "SwarmSimulator 수십~수백 기. BlueSky 는 수천 기 대규모로 더 강함(정직 표면화)",
    ),
    BenchmarkDimension(
        "scenario_library", "Standard scenario library", "scenario",
        "재현 가능한 표준 시나리오 — 벤치마크 제출 시 공통 시험 입력",
        "full", "simulation/standard_scenarios.py",
        "full", "partial",
        "9종 시나리오 + config/scenario_params. BlueSky 는 .scn 시나리오 파일",
    ),
    BenchmarkDimension(
        "monte_carlo", "Monte Carlo statistical sweep", "analysis",
        "통계적 신뢰구간 — 무작위 시드 스윕은 안전성 정량화의 표준",
        "full", "simulation/monte_carlo.py",
        "partial", "partial",
        "내장 MC 스윕(시드·파라미터 격자). BlueSky 는 batch 가능하나 전용 스윕 프레임 약함",
    ),
    BenchmarkDimension(
        "separation_metrics", "Separation / loss-of-separation metrics", "analysis",
        "LOS·충돌 해소율 — 안전 성능의 공통 정량 지표",
        "full", "simulation/metrics.py",
        "full", "partial",
        "conflict_resolution_rate·collision_count 등 KPI. BlueSky 는 LOS·IPR 지표",
    ),
    BenchmarkDimension(
        "viz_3d", "3D visualization", "visualization",
        "3D 시각화 — 군집 고도 레이어 검증·시연용",
        "full", "visualization/simulator_3d.py",
        "partial", "partial",
        "Dash 3D 대시보드. BlueSky 는 2D 레이더 뷰 중심(3D 제한적)",
    ),
    BenchmarkDimension(
        "reproducibility", "Deterministic reproducibility", "reproducibility",
        "재현성 — seeded RNG·결정적 실행은 학술 벤치마크 제출의 전제",
        "full", "simulation/simulator.py",
        "partial", "partial",
        "np.random.default_rng(seed) 결정적 실행(docs/REPRODUCIBILITY.md)",
    ),
    BenchmarkDimension(
        "manned_integration", "Manned aviation / ATC integration", "integration",
        "유인 항공 통합 — 혼합 공역(유·무인) 벤치마크 축",
        "none", None,
        "full", "none",
        "현 시뮬 범위 밖 (갭). BlueSky 는 유인 ATM 시뮬레이터로 본질적으로 강함",
    ),
)


@dataclass(frozen=True)
class ComparisonReport:
    """한 시스템의 비교 축 지원 집계."""

    system: str
    total: int
    full: int
    partial: int
    none: int
    weighted_score: float

    def __post_init__(self) -> None:
        if self.system not in BENCHMARK_SYSTEMS:
            raise ValueError(
                f"system must be one of {BENCHMARK_SYSTEMS}, got {self.system!r}"
            )
        if min(self.total, self.full, self.partial, self.none) < 0:
            raise ValueError("counts must be non-negative")
        if self.full + self.partial + self.none != self.total:
            raise ValueError(
                f"full ({self.full}) + partial ({self.partial}) + none "
                f"({self.none}) != total ({self.total})"
            )
        # 상한은 total 이 아니라 가능한 최대 가중합(full*1.0 + partial*0.5) — none 은 0 기여.
        # total 을 상한으로 두면 counts 와 모순되는 weighted_score 가 통과한다.
        max_possible = float(self.full) * 1.0 + float(self.partial) * 0.5
        if not (0.0 <= self.weighted_score <= max_possible + 1e-9):
            raise ValueError(
                f"weighted_score ({self.weighted_score}) exceeds max possible "
                f"({max_possible}) for full={self.full}, partial={self.partial}"
            )

    @property
    def coverage_pct(self) -> float:
        """가중 지원 비율 (%). full=100%·partial=50%·none=0% 가중."""
        return 100.0 * self.weighted_score / self.total if self.total else 0.0


def find_system(system_id: str) -> BenchmarkSystem:
    """식별자로 비교 대상 시스템을 조회한다. 없으면 KeyError."""
    for sys in BENCHMARK_SYSTEM_CATALOG:
        if sys.system_id == system_id:
            return sys
    raise KeyError(f"unknown benchmark system: {system_id!r}")


def find_dimension(dim_id: str) -> BenchmarkDimension:
    """식별자로 비교 축을 조회한다. 없으면 KeyError."""
    for dim in BENCHMARK_DIMENSIONS:
        if dim.dim_id == dim_id:
            return dim
    raise KeyError(f"unknown benchmark dimension: {dim_id!r}")


def categories() -> tuple[str, ...]:
    """비교 축 분류를 정렬·중복 제거로 반환한다."""
    return tuple(sorted({d.category for d in BENCHMARK_DIMENSIONS}))


def dimensions_by_category(category: str) -> tuple[BenchmarkDimension, ...]:
    """분류에 속한 비교 축을 식별자 정렬로 반환한다."""
    members = tuple(
        sorted((d for d in BENCHMARK_DIMENSIONS if d.category == category),
               key=lambda d: d.dim_id)
    )
    if not members:
        raise ValueError(f"unknown category: {category!r}")
    return members


def gaps() -> tuple[BenchmarkDimension, ...]:
    """SDACS 가 미충족(none)인 비교 축을 식별자 정렬로 반환한다."""
    return tuple(
        sorted((d for d in BENCHMARK_DIMENSIONS if d.sdacs_support == "none"),
               key=lambda d: d.dim_id)
    )


def system_score(system: str) -> ComparisonReport:
    """한 시스템의 비교 축 지원 현황을 집계한 결정적 리포트를 생성한다."""
    if system not in BENCHMARK_SYSTEMS:
        raise ValueError(f"system must be one of {BENCHMARK_SYSTEMS}, got {system!r}")
    full = partial = none = 0
    weighted = 0.0
    for dim in BENCHMARK_DIMENSIONS:
        level = dim.support_for(system)
        weighted += SUPPORT_WEIGHT[level]
        if level == "full":
            full += 1
        elif level == "partial":
            partial += 1
        else:
            none += 1
    return ComparisonReport(
        system=system,
        total=len(BENCHMARK_DIMENSIONS),
        full=full,
        partial=partial,
        none=none,
        weighted_score=weighted,
    )


def comparison_matrix() -> tuple[MappingProxyType, ...]:
    """도구 간 교환용 비교 매트릭스를 (분류, 식별자) 정렬 읽기 전용 행으로 반환한다."""
    ordered = sorted(BENCHMARK_DIMENSIONS, key=lambda d: (d.category, d.dim_id))
    return tuple(
        MappingProxyType(
            {
                "dim_id": d.dim_id,
                "name": d.name,
                "category": d.category,
                "sdacs": d.sdacs_support,
                "sdacs_module": d.sdacs_module,
                "bluesky": d.bluesky_support,
                "u_trafman": d.u_trafman_support,
            }
        )
        for d in ordered
    )


def _format_matrix() -> str:
    mark = {"full": "●", "partial": "◐", "none": "○"}
    lines = ["국제 벤치마크 비교 매트릭스 (SDACS · BlueSky · U-TRAFMAN)", "",
             f"{'축':28} SDACS BlueSky U-TRAF", ""]
    for row in comparison_matrix():
        lines.append(
            f"[{row['category'][:10]:10}] {row['name'][:24]:24} "
            f"{mark[row['sdacs']]:^5} {mark[row['bluesky']]:^7} {mark[row['u_trafman']]:^6}"
        )
    lines.append("")
    lines.append("범례: ● full  ◐ partial  ○ none")
    return "\n".join(lines)


def _format_report() -> str:
    lines = ["벤치마크 점수 요약 (가중: full=1.0·partial=0.5·none=0.0)", ""]
    for system in BENCHMARK_SYSTEMS:
        r = system_score(system)
        lines.append(
            f"{system:10}: {r.weighted_score:4.1f}/{r.total} ({r.coverage_pct:.0f}%) "
            f"— full {r.full}·partial {r.partial}·none {r.none}"
        )
    lines.append("")
    lines.append("주: BlueSky·U-TRAFMAN 수준은 공개 기술 기반 프로젝트 평가 (실측 실행 아님)")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="국제 벤치마크 비교 BlueSky·U-TRAFMAN (ODYSSEY Phase 405)"
    )
    parser.add_argument("--matrix", action="store_true", help="전체 비교 매트릭스 출력")
    parser.add_argument("--report", action="store_true", help="시스템별 점수 요약 출력")
    parser.add_argument("--system", choices=BENCHMARK_SYSTEMS, help="한 시스템 점수 출력")
    parser.add_argument("--category", help="분류별 비교 축 출력")
    parser.add_argument("--gaps", action="store_true", help="SDACS 미충족(갭) 축 출력")
    parser.add_argument("--systems", action="store_true", help="비교 대상 카탈로그 출력")
    args = parser.parse_args(argv)

    if args.matrix:
        print(_format_matrix())
    elif args.report:
        print(_format_report())
    elif args.system:
        r = system_score(args.system)
        print(f"{args.system}: {r.weighted_score:.1f}/{r.total} ({r.coverage_pct:.0f}%)")
        print(f"  full {r.full} · partial {r.partial} · none {r.none}")
    elif args.category:
        for dim in dimensions_by_category(args.category):
            print(f"{dim.dim_id}: {dim.name} — SDACS={dim.sdacs_support}")
    elif args.gaps:
        for dim in gaps():
            print(f"[{dim.category}] {dim.name}: {dim.summary}")
    elif args.systems:
        for sys in BENCHMARK_SYSTEM_CATALOG:
            print(f"{sys.system_id}: {sys.name} ({sys.license})")
            print(f"      {sys.citation}")
    else:
        print(_format_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
