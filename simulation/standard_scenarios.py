"""ODYSSEY Phase 465 — 공역 통합 시뮬레이션 표준 시나리오 셋 (10종 공개).

`config/scenario_params/*.yaml` 에 흩어져 있던 실행형 시나리오를, 도구 간
교차 벤치마크가 가능한 **공개 표준 스위트** 로 큐레이션한다 — *SDACS Standard
Benchmark Suite v1* (식별자 ``SDACS-SBS-10``). Phase 405(BlueSky·U-TRAFMAN 비교)
와 Phase 410(GUTMA 기고)이 전제하는, "같은 10개 시나리오를 누구나 같은 정의로
돌려 비교한다" 는 공통 기준선을 제공하는 것이 목적이다.

설계 원칙
--------
- **중복 없는 큐레이션 계층**: 시나리오 *정의* 는 기존 YAML 이 유일 출처(SSoT)
  이며, 본 모듈은 정의를 복제하지 않는다. 각 벤치마크 항목은 하나의 통제 축
  (controlled axis)·범주·표제 KPI 메타데이터를 *덧붙여* YAML 을 가리킬 뿐이다.
- **스키마 적합 보장**: 10종 모두 `scenario_schema.validate_scenario` 계약을
  충족함을 `validate_suite()` 가 결정적으로 재검증한다(러너 호환 보증).
- **단일 통제 축**: 10개 항목은 서로 다른 운용 차원 하나씩을 통제한다 — 밀도·
  장애·이륙 서지·경로 충돌·통신 두절·기상·침입·다지역·자율 편대·공칭 기준선.
  B10 공칭 저밀도는 다른 9종 지표를 정규화하는 *대조(control)* 케이스다.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python -m simulation.standard_scenarios --list       # 10종 요약 표
    python -m simulation.standard_scenarios --validate   # 스키마 적합 재검증
    python -m simulation.standard_scenarios --manifest   # 공개 매니페스트(JSON)
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from simulation.scenario_schema import validate_scenario_file

# 공개 스위트 식별자·버전
SUITE_ID = "SDACS-SBS-10"
SUITE_VERSION = "1.0"

_SCENARIO_DIR = Path(__file__).resolve().parent.parent / "config" / "scenario_params"


@dataclass(frozen=True)
class BenchmarkScenario:
    """표준 벤치마크 스위트의 한 항목 (불변).

    시나리오 *정의* 는 ``source`` YAML 이 유일 출처이며, 본 객체는 벤치마크
    메타데이터(통제 축·범주·표제 KPI)만 보유한다.

    Attributes:
        benchmark_id: 스위트 내 안정 식별자 (B01..B10).
        axis: 이 시나리오가 통제하는 운용 차원(스위트 내 유일).
        category: 상위 분류.
        source: ``config/scenario_params`` 기준 상대 파일명.
        primary_kpi: 표제 평가 지표 이름(공개 스펙 — YAML 존재 여부와 무관).
    """

    benchmark_id: str
    axis: str
    category: str
    source: str
    primary_kpi: str

    def path(self) -> Path:
        """이 항목이 가리키는 시나리오 YAML 의 절대 경로."""
        return _SCENARIO_DIR / self.source


# 공개 표준 스위트 — 결정적 순서(B01..B10), 통제 축 상호 배타.
BENCHMARK_SET: tuple[BenchmarkScenario, ...] = (
    BenchmarkScenario(
        "B01", "traffic_density", "throughput",
        "high_density.yaml", "conflict_resolution_rate_min",
    ),
    BenchmarkScenario(
        "B02", "in_flight_failure", "safety",
        "emergency_failure.yaml", "emergency_response_p99_s",
    ),
    BenchmarkScenario(
        "B03", "launch_surge", "throughput",
        "mass_takeoff.yaml", "separation_violation_count",
    ),
    BenchmarkScenario(
        "B04", "deconfliction", "safety",
        "route_conflict.yaml", "conflict_resolution_rate_min",
    ),
    BenchmarkScenario(
        "B05", "lost_link", "resilience",
        "comms_loss.yaml", "lost_link_recovery_rate_min",
    ),
    BenchmarkScenario(
        "B06", "wind_robustness", "resilience",
        "weather_disturbance.yaml", "route_efficiency_max",
    ),
    BenchmarkScenario(
        "B07", "intrusion_security", "security",
        "adversarial_intrusion.yaml", "detection_rate_min",
    ),
    BenchmarkScenario(
        "B08", "multi_region", "federation",
        "multi_city.yaml", "handover_success_rate_min",
    ),
    BenchmarkScenario(
        "B09", "autonomous_formation", "autonomy",
        "swarm_autonomous_no_preplan.yaml", "conflict_resolution_rate_min",
    ),
    BenchmarkScenario(
        "B10", "nominal_baseline", "control",
        "nominal_baseline.yaml", "conflict_resolution_rate_min",
    ),
)


def all_scenarios() -> tuple[BenchmarkScenario, ...]:
    """결정적 순서의 표준 스위트 10종을 반환한다."""
    return BENCHMARK_SET


def get_scenario(benchmark_id: str) -> BenchmarkScenario:
    """벤치마크 식별자로 항목을 조회한다.

    Args:
        benchmark_id: B01..B10.

    Returns:
        해당 BenchmarkScenario.

    Raises:
        KeyError: 알 수 없는 식별자.
    """
    for entry in BENCHMARK_SET:
        if entry.benchmark_id == benchmark_id:
            return entry
    raise KeyError(f"알 수 없는 벤치마크 식별자: {benchmark_id!r}")


def load_config(entry: BenchmarkScenario) -> dict[str, Any]:
    """항목이 가리키는 시나리오 YAML 을 dict 로 로드한다.

    Raises:
        FileNotFoundError: 소스 파일이 없을 때.
    """
    import yaml

    path = entry.path()
    if not path.exists():
        raise FileNotFoundError(f"시나리오 소스 없음: {path}")
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as exc:
        # validate_scenario_file 과 오류 처리 대칭 — 파싱 실패를 명시적 예외로.
        raise ValueError(f"YAML 파싱 실패 ({path.name}): {exc}") from exc


def validate_suite() -> dict[str, bool]:
    """10종 모두 scenario_schema 계약을 충족하는지 재검증한다.

    Returns:
        ``benchmark_id -> is_valid`` 매핑 (결정적 순서).
    """
    return {
        entry.benchmark_id: validate_scenario_file(entry.path()).is_valid
        for entry in BENCHMARK_SET
    }


def benchmark_manifest() -> dict[str, Any]:
    """도구 간 교차 벤치마크용 공개 매니페스트(JSON 직렬화 가능)를 생성한다.

    각 항목에 통제 축·범주·표제 KPI·스키마 적합 여부와, 소스 YAML 의
    ``scenario`` 이름·``success_criteria`` (있으면)를 함께 싣는다. 표제 KPI 가
    소스 YAML 의 ``success_criteria`` 에 실제 키로 존재하는지는
    ``primary_kpi_in_criteria`` 플래그로 명시한다.
    """
    scenarios: list[dict[str, Any]] = []
    for entry in BENCHMARK_SET:
        config = load_config(entry)
        result = validate_scenario_file(entry.path())
        criteria = config.get("success_criteria") or None
        # 표제 KPI 는 *공개 스펙* 이름이라 일부 소스 YAML 의 success_criteria 에
        # 실제 키로 없을 수 있다(런너 파생 지표). 그 괴리를 기계 판독 가능한
        # 플래그로 명시해 자동화 소비자가 primary_kpi 를 success_criteria 키로
        # 가정해 오판하지 않게 한다.
        primary_kpi_in_criteria = bool(criteria) and entry.primary_kpi in criteria
        scenarios.append({
            "benchmark_id": entry.benchmark_id,
            "axis": entry.axis,
            "category": entry.category,
            "primary_kpi": entry.primary_kpi,
            "primary_kpi_in_criteria": primary_kpi_in_criteria,
            "scenario": config.get("scenario"),
            "source": entry.source,
            "schema_valid": result.is_valid,
            "success_criteria": criteria,
        })
    return {
        "suite_id": SUITE_ID,
        "version": SUITE_VERSION,
        "count": len(scenarios),
        "scenarios": scenarios,
    }


def _cmd_list() -> None:
    print(f"{SUITE_ID} v{SUITE_VERSION} — 표준 벤치마크 시나리오 {len(BENCHMARK_SET)}종")
    print(f"{'ID':<5}{'AXIS':<22}{'CATEGORY':<12}SOURCE")
    for entry in BENCHMARK_SET:
        print(f"{entry.benchmark_id:<5}{entry.axis:<22}{entry.category:<12}{entry.source}")


def _cmd_validate() -> int:
    results = validate_suite()
    for benchmark_id, ok in results.items():
        print(f"{benchmark_id}  {'VALID' if ok else 'INVALID'}")
    invalid = [bid for bid, ok in results.items() if not ok]
    if invalid:
        print(f"\nINVALID: {', '.join(invalid)}", file=sys.stderr)
        return 1
    print(f"\n전체 {len(results)}종 스키마 적합 ✅")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "--validate" in args:
        return _cmd_validate()
    if "--manifest" in args:
        print(json.dumps(benchmark_manifest(), ensure_ascii=False, indent=2))
        return 0
    _cmd_list()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
