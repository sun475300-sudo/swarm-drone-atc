"""ODYSSEY Phase 405 — 국제 벤치마크 제출(BlueSky·U-TRAFMAN 비교 시나리오 공개).

SDACS 가 이미 공개한 벤치마크 스위트(``benchmarks/`` — P703, 10개 표준/스트레스
시나리오)를 국제적으로 널리 쓰이는 외부 공개 시뮬레이터(**BlueSky** 오픈 ATM
시뮬레이터·**U-TRAFMAN** UTM 트래픽 관리 시뮬레이터)의 *비교 가능 역량* 에
결정적으로 대응시켜, "SDACS 벤치마크 시나리오 중 어느 것이 외부 플랫폼으로
교차 검증 가능한가" 를 객관적으로 답하는 비교 매트릭스다. Phase 409(다국 규제
대조)의 자매편 — 거기서는 *관할* 을 비교 축으로, 여기서는 *시뮬레이터 플랫폼* 을
비교 축으로 같은 자산(공개 시나리오)을 재정렬한다.

근거 (권위 있는 공개 출처)
------------------------
- **BlueSky** — Open Air Traffic Simulator, TU Delft CNS/ATM (오픈소스
  ``github.com/TUDelft-CNS-ATM/bluesky``; Hoekstra & Ellerbroek, ICRAT 2016).
  고속(fast-time) 이산 시뮬레이션 + 충돌 탐지·해소(CD&R, ASAS) + 바람장.
- **U-TRAFMAN** — UAS Traffic Management 시뮬레이션 도구(공개 UTM 연구
  시뮬레이터). U-space 운영·UTM 트래픽 관리에 초점.
- **SDACS 벤치마크 스위트** — ``benchmarks/README.md`` (P703, CC-BY-4.0,
  10 시나리오 + 14 지표 + 4 baseline).

정직 공시 (CLAUDE.md)
--------------------
``comparable`` 은 해당 SDACS 시나리오와 *비교 가능한 역량* 이 외부 플랫폼에
존재한다는 **프로젝트 해석** 이다(외부 플랫폼 공식 채택·동등성 보증이 아님 —
공개 자료에 근거한 기능적 요약). ``comparable == ()`` 인 시나리오는 외부
교차 검증 기준선이 없는 **SDACS 고유(gap)** 시나리오로 정직히 표면화한다.
각 시나리오의 ``manifest`` 는 디스크에 실재하는 공개 매니페스트 경로이며
(``__post_init__`` 강제 + 테스트가 실재 강제) 모듈 없는 비교 주장을 구조적으로
금지한다.

무작위성 0 · 결정적. 기존 벤치마크·모듈 무수정 순수 추가.

CLI:
    python simulation/international_benchmark.py --matrix          # 전체 비교 매트릭스
    python simulation/international_benchmark.py --report          # 교차검증 커버리지 요약
    python simulation/international_benchmark.py --category CDR     # 범주별 시나리오
    python simulation/international_benchmark.py --platform bluesky # 플랫폼 비교 가능 시나리오
    python simulation/international_benchmark.py --unique           # SDACS 고유(외부 기준선 없음)
    python simulation/international_benchmark.py --platforms         # 외부 플랫폼 목록
"""
from __future__ import annotations

import argparse
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

# 리포 루트 — 인용 매니페스트 경로는 이 기준의 상대 경로다.
_REPO_ROOT = Path(__file__).resolve().parent.parent

# 외부 비교 대상 공개 시뮬레이터 — 안정 코드 ↔ 설명/인용.
PLATFORMS: Mapping[str, str] = MappingProxyType(
    {
        "bluesky": "BlueSky Open ATM Simulator (TU Delft CNS/ATM, ICRAT 2016)",
        "utrafman": "U-TRAFMAN UAS Traffic Management Simulator (공개 UTM 연구 도구)",
    }
)

# 벤치마크 범주(category) — 안정 코드 ↔ 설명.
BENCHMARK_CATEGORIES: Mapping[str, str] = MappingProxyType(
    {
        "CDR": "Conflict Detection & Resolution (충돌 탐지·해소)",
        "DENS": "Density / Capacity Stress (밀도·용량 스트레스)",
        "ENV": "Environmental Diversion (기상·바람 우회)",
        "REG": "Regulatory Constraint (규제 제약 — NFZ·Remote-ID)",
        "FAIL": "Failure / Contingency (장애·비상)",
        "ADV": "Adversarial / Security (적대·보안)",
    }
)

# 보고 지표 코드 allowlist — benchmarks/metrics/README.md 의 14개 지표.
BENCHMARK_METRICS: frozenset[str] = frozenset(
    {
        "NMR", "MSD", "TTC", "PE", "MS", "FT", "AU", "VCU",
        "RID-CR", "LAANC", "geofence_violations", "RTF",
        "tick_latency", "memory_peak",
    }
)


@dataclass(frozen=True)
class BenchmarkScenario:
    """단일 공개 벤치마크 시나리오와 외부 플랫폼 비교 가능성의 정의(불변)."""

    scenario_id: str              # benchmarks/scenarios/ 디렉터리 ID (예: '01_corridor_crossing')
    name: str                     # 시나리오 명칭
    category: str                 # 범주 코드 (BENCHMARK_CATEGORIES)
    primary_metric: str           # 주 보고 지표 (BENCHMARK_METRICS)
    manifest: str                 # 실재하는 매니페스트 경로 (리포 상대)
    comparable: tuple[str, ...]   # 비교 가능 외부 플랫폼 코드 (빈 튜플이면 SDACS 고유)
    summary: str                  # 한 줄 설명

    def __post_init__(self) -> None:
        if not self.scenario_id or self.scenario_id != self.scenario_id.strip():
            raise ValueError("scenario_id must be non-empty and unpadded")
        if re.search(r"\s", self.scenario_id):
            raise ValueError(
                f"scenario_id must not contain whitespace: {self.scenario_id!r}"
            )
        if not self.name or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        if not self.summary or not self.summary.strip():
            raise ValueError("summary must be a non-empty string")
        if not self.manifest or not self.manifest.strip():
            raise ValueError("manifest must be a non-empty path")
        if self.category not in BENCHMARK_CATEGORIES:
            raise ValueError(
                f"category must be one of {tuple(BENCHMARK_CATEGORIES)}, "
                f"got {self.category!r}"
            )
        if self.primary_metric not in BENCHMARK_METRICS:
            raise ValueError(
                f"primary_metric must be a known benchmark metric, "
                f"got {self.primary_metric!r}"
            )
        # comparable 은 PLATFORMS 부분집합·중복 없음. 빈 튜플은 SDACS 고유(허용).
        seen: set[str] = set()
        for code in self.comparable:
            if code not in PLATFORMS:
                raise ValueError(
                    f"comparable platform must be one of {tuple(PLATFORMS)}, "
                    f"got {code!r}"
                )
            if code in seen:
                raise ValueError(f"duplicate comparable platform: {code!r}")
            seen.add(code)

    @property
    def is_cross_validatable(self) -> bool:
        """외부 플랫폼으로 교차 검증 가능하면 True (비교 대상 ≥1)."""
        return len(self.comparable) > 0

    @property
    def cross_platform_count(self) -> int:
        """비교 가능한 외부 플랫폼 수."""
        return len(self.comparable)


# 공개 벤치마크 시나리오 ↔ 외부 플랫폼 비교 매트릭스 (정본).
# manifest 경로는 benchmarks/scenarios/ 에 실재하는 매니페스트.
# comparable 빈 튜플 = SDACS 고유(외부 교차 검증 기준선 없음, 정직 gap).
BENCHMARK_SCENARIOS: tuple[BenchmarkScenario, ...] = (
    BenchmarkScenario(
        "01_corridor_crossing", "Corridor Crossing", "CDR", "MSD",
        "benchmarks/scenarios/01_corridor_crossing/manifest.yaml",
        ("bluesky", "utrafman"),
        "교차 회랑 정면 충돌 — 최소 분리거리 보존(양 플랫폼 CD&R 표준 케이스)",
    ),
    BenchmarkScenario(
        "02_dense_intersection", "Dense Intersection", "DENS", "NMR",
        "benchmarks/scenarios/02_dense_intersection/manifest.yaml",
        ("bluesky", "utrafman"),
        "고밀도 교차 — 근접 회피율(NMR) 비교(양 플랫폼 다중 충돌 부하 지원)",
    ),
    BenchmarkScenario(
        "03_emergency_landing", "Emergency Landing", "FAIL", "MS",
        "benchmarks/scenarios/03_emergency_landing/manifest.yaml",
        ("utrafman",),
        "비상 착륙 우선권 — 메이크스팬(UTM 비상 절차 대응은 U-TRAFMAN 측 비교 가능)",
    ),
    BenchmarkScenario(
        "04_no_fly_zone", "No-Fly Zone Avoidance", "REG", "geofence_violations",
        "benchmarks/scenarios/04_no_fly_zone/manifest.yaml",
        ("bluesky", "utrafman"),
        "비행 금지구역 회피 — 지오펜스 위반 0 목표(양 플랫폼 제한구역 모델 보유)",
    ),
    BenchmarkScenario(
        "05_weather_diversion", "Weather Diversion", "ENV", "PE",
        "benchmarks/scenarios/05_weather_diversion/manifest.yaml",
        ("bluesky",),
        "기상 우회 — 경로 효율(BlueSky 바람장 지원으로 환경 우회 교차 비교 가능)",
    ),
    BenchmarkScenario(
        "06_priority_aircraft", "Priority Aircraft", "CDR", "FT",
        "benchmarks/scenarios/06_priority_aircraft/manifest.yaml",
        ("bluesky", "utrafman"),
        "우선 항공기 양보 — 플로우타임(양 플랫폼 우선순위 디컨플릭션 비교 가능)",
    ),
    BenchmarkScenario(
        "07_communication_loss", "Communication Loss", "FAIL", "RID-CR",
        "benchmarks/scenarios/07_communication_loss/manifest.yaml",
        ("utrafman",),
        "통신 두절 비상 — Remote-ID 준수율(UTM 통신/네트워크 모델은 U-TRAFMAN 비교)",
    ),
    BenchmarkScenario(
        "08_stress_high_density", "High Density Stress", "DENS", "AU",
        "benchmarks/scenarios/08_stress_high_density/manifest.yaml",
        ("bluesky", "utrafman"),
        "초고밀도 스트레스 — 공역 활용도(양 플랫폼 대규모 트래픽 부하 비교 가능)",
    ),
    BenchmarkScenario(
        "09_stress_failure_cascade", "Failure Cascade Stress", "FAIL", "MSD",
        "benchmarks/scenarios/09_stress_failure_cascade/manifest.yaml",
        (),
        "연쇄 장애 주입 스트레스 — 외부 표준 기준선 부재(SDACS 고유, 정직 gap)",
    ),
    BenchmarkScenario(
        "10_stress_adversarial_swarm", "Adversarial Swarm Stress", "ADV", "NMR",
        "benchmarks/scenarios/10_stress_adversarial_swarm/manifest.yaml",
        (),
        "적대적 군집 스트레스 — 외부 표준 기준선 부재(SDACS 고유, 정직 gap)",
    ),
)


@dataclass(frozen=True)
class BenchmarkComparisonReport:
    """벤치마크 교차 검증 커버리지 요약(불변)."""

    total: int
    cross_validatable: int                    # comparable 비어있지 않은 시나리오 수
    sdacs_unique: int                         # comparable == () (외부 기준선 없음)
    coverage: float                           # cross_validatable / total (0.0~1.0)
    by_platform: Mapping[str, int]            # platform -> 비교 가능 시나리오 수, read-only
    by_category: Mapping[str, tuple[int, int]]  # category -> (교차검증가능, 총), read-only

    def __post_init__(self) -> None:
        if min(self.total, self.cross_validatable, self.sdacs_unique) < 0:
            raise ValueError("counts must be non-negative")
        if self.cross_validatable + self.sdacs_unique != self.total:
            raise ValueError(
                f"cross_validatable ({self.cross_validatable}) + sdacs_unique "
                f"({self.sdacs_unique}) != total ({self.total})"
            )
        if not 0.0 <= self.coverage <= 1.0:
            raise ValueError(f"coverage must be in [0,1], got {self.coverage}")
        # 플랫폼별 비교 가능 수는 교차검증 가능 시나리오 수를 초과할 수 없다.
        for platform, count in self.by_platform.items():
            if platform not in PLATFORMS:
                raise ValueError(f"unknown platform in by_platform: {platform!r}")
            if not 0 <= count <= self.cross_validatable:
                raise ValueError(
                    f"by_platform[{platform!r}] ({count}) must be in "
                    f"[0, {self.cross_validatable}]"
                )
        # by_category 합이 총계와 일치해야 한다(교차검증).
        cat_total = sum(tot for _xv, tot in self.by_category.values())
        if cat_total != self.total:
            raise ValueError(
                f"by_category total ({cat_total}) != total ({self.total})"
            )
        for cat, (xv, tot) in self.by_category.items():
            if not 0 <= xv <= tot:
                raise ValueError(
                    f"by_category[{cat!r}] cross-validatable ({xv}) must be in [0, {tot}]"
                )
        # 각 시나리오는 정확히 한 범주에 속하므로 범주별 교차검증 수의 합은
        # 전체 교차검증 가능 수와 정확히 일치해야 한다(이중 교차검증).
        cat_xv = sum(xv for xv, _tot in self.by_category.values())
        if cat_xv != self.cross_validatable:
            raise ValueError(
                f"by_category cross-validatable sum ({cat_xv}) != "
                f"cross_validatable ({self.cross_validatable})"
            )

    @property
    def coverage_pct(self) -> float:
        """교차 검증 커버리지 백분율 (%)."""
        return 100.0 * self.coverage


def find_scenario(scenario_id: str) -> BenchmarkScenario:
    """식별자로 시나리오를 조회한다. 없으면 KeyError."""
    for scenario in BENCHMARK_SCENARIOS:
        if scenario.scenario_id == scenario_id:
            return scenario
    raise KeyError(f"unknown benchmark scenario: {scenario_id!r}")


def scenarios_by_category(category: str) -> tuple[BenchmarkScenario, ...]:
    """범주에 속한 시나리오를 식별자 정렬로 반환한다."""
    if category not in BENCHMARK_CATEGORIES:
        raise ValueError(
            f"category must be one of {tuple(BENCHMARK_CATEGORIES)}, got {category!r}"
        )
    return tuple(
        sorted(
            (s for s in BENCHMARK_SCENARIOS if s.category == category),
            key=lambda s: s.scenario_id,
        )
    )


def scenarios_for_platform(platform: str) -> tuple[BenchmarkScenario, ...]:
    """해당 외부 플랫폼으로 비교 가능한 시나리오를 식별자 정렬로 반환한다."""
    if platform not in PLATFORMS:
        raise ValueError(
            f"platform must be one of {tuple(PLATFORMS)}, got {platform!r}"
        )
    return tuple(
        sorted(
            (s for s in BENCHMARK_SCENARIOS if platform in s.comparable),
            key=lambda s: s.scenario_id,
        )
    )


def sdacs_unique_scenarios() -> tuple[BenchmarkScenario, ...]:
    """외부 교차 검증 기준선이 없는 SDACS 고유(gap) 시나리오를 정렬 반환한다."""
    return tuple(
        sorted(
            (s for s in BENCHMARK_SCENARIOS if not s.is_cross_validatable),
            key=lambda s: s.scenario_id,
        )
    )


def comparison_report() -> BenchmarkComparisonReport:
    """전체 교차 검증 커버리지를 집계한 결정적 리포트를 생성한다."""
    total = len(BENCHMARK_SCENARIOS)
    cross_validatable = sum(1 for s in BENCHMARK_SCENARIOS if s.is_cross_validatable)
    unique = total - cross_validatable
    coverage = (cross_validatable / total) if total else 0.0
    by_platform: dict[str, int] = {}
    for platform in PLATFORMS:
        by_platform[platform] = sum(
            1 for s in BENCHMARK_SCENARIOS if platform in s.comparable
        )
    by_category: dict[str, tuple[int, int]] = {}
    for category in BENCHMARK_CATEGORIES:
        members = [s for s in BENCHMARK_SCENARIOS if s.category == category]
        by_category[category] = (
            sum(1 for s in members if s.is_cross_validatable),
            len(members),
        )
    return BenchmarkComparisonReport(
        total=total,
        cross_validatable=cross_validatable,
        sdacs_unique=unique,
        coverage=coverage,
        by_platform=MappingProxyType(by_platform),
        by_category=MappingProxyType(by_category),
    )


def comparison_matrix() -> tuple[Mapping[str, object], ...]:
    """도구 간 교환용 비교 매트릭스를 식별자 정렬 행으로 반환한다.

    각 행은 ``MappingProxyType`` 읽기 전용 매핑이다(모듈 전반의 불변 규율과 일치).
    """
    ordered = sorted(BENCHMARK_SCENARIOS, key=lambda s: s.scenario_id)
    return tuple(
        MappingProxyType(
            {
                "scenario_id": s.scenario_id,
                "name": s.name,
                "category": s.category,
                "primary_metric": s.primary_metric,
                "comparable": s.comparable,
                "cross_validatable": s.is_cross_validatable,
                "manifest": s.manifest,
            }
        )
        for s in ordered
    )


def _format_matrix() -> str:
    lines = ["SDACS 공개 벤치마크 ↔ 외부 플랫폼(BlueSky·U-TRAFMAN) 비교 매트릭스", ""]
    for row in comparison_matrix():
        comparable = row["comparable"] or ()
        mark = "✓" if comparable else "✗"  # ✗ = SDACS 고유(외부 기준선 없음)
        platforms = ", ".join(comparable) if comparable else "—(SDACS 고유)"
        lines.append(
            f"[{row['category']:4}] {mark} {row['name']} "
            f"(지표 {row['primary_metric']})"
        )
        lines.append(f"        ↔ {platforms}")
    return "\n".join(lines)


def _format_report() -> str:
    r = comparison_report()
    lines = [
        "국제 벤치마크 교차 검증 커버리지 요약",
        "",
        f"전체 시나리오       : {r.total}",
        f"교차 검증 가능       : {r.cross_validatable}",
        f"SDACS 고유(기준선 없음): {r.sdacs_unique}",
        f"커버리지            : {r.coverage_pct:.0f}%",
        "",
        "외부 플랫폼별 비교 가능 시나리오 수:",
    ]
    for platform, label in PLATFORMS.items():
        short = label.split(" (")[0][:40]
        lines.append(f"  {platform:9} {short:40}: {r.by_platform[platform]}")
    lines.append("")
    lines.append("범주별 (교차검증가능/총):")
    for category, label in BENCHMARK_CATEGORIES.items():
        xv, tot = r.by_category[category]
        short = label.split(" (")[0][:32]
        lines.append(f"  {category:5} {short:32}: {xv}/{tot}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="국제 벤치마크 비교 매트릭스 (ODYSSEY Phase 405)"
    )
    parser.add_argument("--matrix", action="store_true", help="전체 비교 매트릭스 출력")
    parser.add_argument("--report", action="store_true", help="교차검증 커버리지 요약 출력")
    parser.add_argument(
        "--category", choices=tuple(BENCHMARK_CATEGORIES), help="범주별 시나리오 출력"
    )
    parser.add_argument(
        "--platform", choices=tuple(PLATFORMS), help="플랫폼 비교 가능 시나리오 출력"
    )
    parser.add_argument(
        "--unique", action="store_true", help="SDACS 고유(외부 기준선 없음) 시나리오 출력"
    )
    parser.add_argument("--platforms", action="store_true", help="외부 플랫폼 목록 출력")
    args = parser.parse_args(argv)

    if args.matrix:
        print(_format_matrix())
    elif args.report:
        print(_format_report())
    elif args.category:
        for s in scenarios_by_category(args.category):
            print(f"{s.scenario_id}: {s.name} [{s.primary_metric}] — {s.summary}")
    elif args.platform:
        for s in scenarios_for_platform(args.platform):
            print(f"{s.scenario_id}: {s.name} — {s.summary}")
    elif args.unique:
        for s in sdacs_unique_scenarios():
            print(f"[{s.category}] {s.name}: {s.summary}")
    elif args.platforms:
        for platform, label in PLATFORMS.items():
            print(f"{platform}: {label}")
    else:
        print(_format_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
