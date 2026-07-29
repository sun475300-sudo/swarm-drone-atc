"""GENESIS Phase 306 -- 요구사항 추적 행렬(RTM) 자동 생성기.

5계층 안전망(Safety Net) 아키텍처의 요구사항을 시뮬레이션 모듈 및
테스트 파일에 매핑하여 커버리지를 정량적으로 산정합니다.

5계층 안전망:
  L1 APF    — 충돌 회피 (Artificial Potential Field)
  L2 CPA    — 충돌 예측 (Closest Point of Approach)
  L3 Fence  — 지오펜스 (Geofence Boundary Enforcement)
  L4 ATC    — 공역 통제 (Airspace Traffic Controller)
  L5 UTM    — 교통 관리 (UAS Traffic Management)

Honesty binding:
  COVERED   — 모듈 파일 + 테스트 파일 모두 존재
  PARTIAL   — 모듈 파일은 있으나 테스트 파일 없음
  UNCOVERED — 모듈 파일 자체가 디스크에 없음

CLI:
    python simulation/rtm_generator.py --report
    python simulation/rtm_generator.py --layer 1
    python simulation/rtm_generator.py --gaps
    python simulation/rtm_generator.py --json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------------
COVERED = "COVERED"
PARTIAL = "PARTIAL"
UNCOVERED = "UNCOVERED"

STATUS_LABELS: MappingProxyType[str, str] = MappingProxyType({
    COVERED: "COVERED",
    PARTIAL: "PARTIAL",
    UNCOVERED: "UNCOVERED",
})

# ---------------------------------------------------------------------------
# Layer constants
# ---------------------------------------------------------------------------
LAYER_NAMES: MappingProxyType[int, str] = MappingProxyType({
    1: "APF (Collision Avoidance)",
    2: "CPA (Collision Prediction)",
    3: "Geofence (Boundary Enforcement)",
    4: "ATC (Airspace Controller)",
    5: "UTM (Traffic Management)",
})

# ---------------------------------------------------------------------------
# Frozen dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Requirement:
    id: str
    description: str
    layer: int
    priority: str
    source: str
    verification_method: str

    def __post_init__(self) -> None:
        if self.layer not in LAYER_NAMES:
            raise ValueError(f"layer must be 1-5, got {self.layer}")
        if self.priority not in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            raise ValueError(f"invalid priority: {self.priority}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "layer": self.layer,
            "priority": self.priority,
            "source": self.source,
            "verification_method": self.verification_method,
        }


@dataclass(frozen=True)
class TraceabilityLink:
    req_id: str
    module_path: str
    test_path: str
    status: str

    def __post_init__(self) -> None:
        if self.status not in (COVERED, PARTIAL, UNCOVERED):
            raise ValueError(f"invalid status: {self.status}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "req_id": self.req_id,
            "module_path": self.module_path,
            "test_path": self.test_path,
            "status": self.status,
        }


@dataclass(frozen=True)
class LayerCoverage:
    layer: int
    name: str
    total: int
    covered: int
    partial: int
    uncovered: int

    @property
    def coverage_pct(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.covered / self.total) * 100.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "layer": self.layer,
            "name": self.name,
            "total": self.total,
            "covered": self.covered,
            "partial": self.partial,
            "uncovered": self.uncovered,
            "coverage_pct": round(self.coverage_pct, 1),
        }


@dataclass(frozen=True)
class RTMReport:
    requirements: tuple[Requirement, ...]
    links: tuple[TraceabilityLink, ...]
    layer_coverage: tuple[LayerCoverage, ...]
    total_requirements: int
    total_covered: int
    total_partial: int
    total_uncovered: int

    @property
    def overall_coverage_pct(self) -> float:
        if self.total_requirements == 0:
            return 0.0
        return (self.total_covered / self.total_requirements) * 100.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_requirements": self.total_requirements,
            "total_covered": self.total_covered,
            "total_partial": self.total_partial,
            "total_uncovered": self.total_uncovered,
            "overall_coverage_pct": round(self.overall_coverage_pct, 1),
            "layer_coverage": tuple(lc.as_dict() for lc in self.layer_coverage),
            "requirements": tuple(r.as_dict() for r in self.requirements),
            "links": tuple(ln.as_dict() for ln in self.links),
        }


# ---------------------------------------------------------------------------
# Requirements registry — 5계층 안전망 요구사항
# ---------------------------------------------------------------------------

_REQUIREMENTS_RAW: tuple[tuple[str, str, int, str, str, str], ...] = (
    # L1 APF
    ("REQ-L1-001", "APF 기반 실시간 충돌 회피 연산", 1,
     "CRITICAL", "SRS-4.1", "unit_test"),
    ("REQ-L1-002", "APF 척력/인력 파라미터 동적 조정", 1,
     "HIGH", "SRS-4.1.1", "unit_test"),
    ("REQ-L1-003", "강풍 모드(>10m/s) APF 파라미터 자동 전환", 1,
     "CRITICAL", "SRS-4.1.2", "unit_test"),
    ("REQ-L1-004", "APF Lyapunov 안정성 검증", 1,
     "HIGH", "SRS-4.1.3", "analysis"),
    ("REQ-L1-005", "APF GPU 가속 연산 지원", 1,
     "MEDIUM", "SRS-4.1.4", "unit_test"),
    # L2 CPA
    ("REQ-L2-001", "CPA 기반 충돌 사전 예측", 2,
     "CRITICAL", "SRS-4.2", "unit_test"),
    ("REQ-L2-002", "충돌 예측 시스템 다중 드론 추적", 2,
     "HIGH", "SRS-4.2.1", "unit_test"),
    ("REQ-L2-003", "충돌 포렌식 기록 생성", 2,
     "MEDIUM", "SRS-4.2.2", "unit_test"),
    ("REQ-L2-004", "하이브리드 충돌 회피 전략", 2,
     "HIGH", "SRS-4.2.3", "integration_test"),
    # L3 Geofence
    ("REQ-L3-001", "지오펜스 경계 침입 탐지", 3,
     "CRITICAL", "SRS-4.3", "unit_test"),
    ("REQ-L3-002", "지오펜스 위반 시 페일세이프 에스컬레이션", 3,
     "CRITICAL", "SRS-4.3.1", "unit_test"),
    ("REQ-L3-003", "동적 지오펜스 업데이트", 3,
     "HIGH", "SRS-4.3.2", "unit_test"),
    ("REQ-L3-004", "안전망 불변 조건 형식 검증", 3,
     "CRITICAL", "SRS-4.3.3", "analysis"),
    # L4 ATC
    ("REQ-L4-001", "공역 통제 명령 생성 및 전파", 4,
     "CRITICAL", "SRS-4.4", "unit_test"),
    ("REQ-L4-002", "우선순위 큐 기반 드론 스케줄링", 4,
     "HIGH", "SRS-4.4.1", "unit_test"),
    ("REQ-L4-003", "공역 등급 분류 및 제한 적용", 4,
     "HIGH", "SRS-4.4.2", "unit_test"),
    ("REQ-L4-004", "페일세이프 단계별 에스컬레이션", 4,
     "CRITICAL", "SRS-4.4.3", "unit_test"),
    ("REQ-L4-005", "스웜 안전 표준 적합성", 4,
     "MEDIUM", "SRS-4.4.4", "integration_test"),
    # L5 UTM
    ("REQ-L5-001", "FAA UTM 규격 갭 분석", 5,
     "HIGH", "SRS-4.5", "analysis"),
    ("REQ-L5-002", "ICAO UTM 적합성 검증", 5,
     "HIGH", "SRS-4.5.1", "analysis"),
    ("REQ-L5-003", "UTM 교통 흐름 관리", 5,
     "MEDIUM", "SRS-4.5.2", "integration_test"),
    ("REQ-L5-004", "BVLOS 규제 비교 분석", 5,
     "MEDIUM", "SRS-4.5.3", "analysis"),
    ("REQ-L5-005", "규제 적합성 종합 점검", 5,
     "HIGH", "SRS-4.5.4", "unit_test"),
)

REQUIREMENTS: tuple[Requirement, ...] = tuple(
    Requirement(rid, desc, layer, pri, src, vm)
    for rid, desc, layer, pri, src, vm in _REQUIREMENTS_RAW
)

# ---------------------------------------------------------------------------
# Module-to-file mapping — 요구사항 ID → (모듈 경로, 테스트 경로)
# ---------------------------------------------------------------------------

_MODULE_MAP_RAW: dict[str, tuple[str, str]] = {
    # L1 APF
    "REQ-L1-001": ("simulation/apf_engine/apf.py", "tests/test_apf.py"),
    "REQ-L1-002": ("simulation/apf_engine/apf.py", "tests/test_apf.py"),
    "REQ-L1-003": ("simulation/apf_engine/apf.py", "tests/test_apf.py"),
    "REQ-L1-004": ("simulation/apf_lyapunov.py", "tests/test_apf_lyapunov.py"),
    "REQ-L1-005": ("simulation/apf_engine/apf_gpu.py",
                    "tests/test_apf_engine_fallback.py"),
    # L2 CPA
    "REQ-L2-001": ("simulation/collision_predictor.py",
                    "tests/test_collision_predictor.py"),
    "REQ-L2-002": ("simulation/collision_prediction_system.py",
                    "tests/test_collision_prediction_system.py"),
    "REQ-L2-003": ("simulation/collision_forensics.py",
                    "tests/test_collision_forensics.py"),
    "REQ-L2-004": ("simulation/hybrid_collision_avoidance.py",
                    "tests/test_hybrid_collision_avoidance.py"),
    # L3 Geofence
    "REQ-L3-001": ("simulation/geofence_manager.py",
                    "tests/test_geofence_manager.py"),
    "REQ-L3-002": ("simulation/failsafe_manager.py",
                    "tests/test_failsafe_manager.py"),
    "REQ-L3-003": ("simulation/geofence_manager.py",
                    "tests/test_geofence_manager.py"),
    "REQ-L3-004": ("simulation/safety_net_invariant.py",
                    "tests/test_safety_net_invariant.py"),
    # L4 ATC
    "REQ-L4-001": ("src/airspace_control/controller/airspace_controller.py",
                    "tests/test_airspace_controller.py"),
    "REQ-L4-002": ("src/airspace_control/controller/priority_queue.py",
                    "tests/test_airspace_controller.py"),
    "REQ-L4-003": ("simulation/airspace_class.py",
                    "tests/test_airspace_class.py"),
    "REQ-L4-004": ("simulation/failsafe_manager.py",
                    "tests/test_failsafe_manager.py"),
    "REQ-L4-005": ("simulation/swarm_safety_standard.py",
                    "tests/test_swarm_safety_standard.py"),
    # L5 UTM
    "REQ-L5-001": ("simulation/faa_utm_gap.py",
                    "tests/test_faa_utm_gap.py"),
    "REQ-L5-002": ("simulation/icao_utm_conformance.py",
                    "tests/test_icao_utm_conformance.py"),
    "REQ-L5-003": ("simulation/faa_utm_gap.py",
                    "tests/test_faa_utm_gap.py"),
    "REQ-L5-004": ("simulation/bvlos_regulation_compare.py",
                    "tests/test_bvlos_regulation_compare.py"),
    "REQ-L5-005": ("simulation/compliance_checker.py",
                    "tests/test_compliance_checker.py"),
}

MODULE_MAP: MappingProxyType[str, tuple[str, str]] = MappingProxyType(
    _MODULE_MAP_RAW
)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def _resolve_status(
    module_path: str,
    test_path: str,
    repo_root: pathlib.Path,
) -> str:
    """파일 존재 여부로 커버리지 상태 결정 (honesty binding)."""
    module_exists = (repo_root / module_path).is_file()
    if not module_exists:
        return UNCOVERED
    test_exists = (repo_root / test_path).is_file()
    return COVERED if test_exists else PARTIAL


def _build_links(
    requirements: tuple[Requirement, ...],
    module_map: MappingProxyType[str, tuple[str, str]],
    repo_root: pathlib.Path,
) -> tuple[TraceabilityLink, ...]:
    """요구사항별 추적 링크 생성."""
    links: list[TraceabilityLink] = []
    for req in requirements:
        mod_path, test_path = module_map.get(req.id, ("", ""))
        status = (
            UNCOVERED
            if not mod_path
            else _resolve_status(mod_path, test_path, repo_root)
        )
        links.append(TraceabilityLink(
            req_id=req.id,
            module_path=mod_path,
            test_path=test_path,
            status=status,
        ))
    return tuple(links)


def _compute_layer_coverage(
    requirements: tuple[Requirement, ...],
    links: tuple[TraceabilityLink, ...],
) -> tuple[LayerCoverage, ...]:
    """계층별 커버리지 통계 산출."""
    link_by_id: dict[str, TraceabilityLink] = {
        ln.req_id: ln for ln in links
    }
    result: list[LayerCoverage] = []
    for layer_num in sorted(LAYER_NAMES):
        layer_reqs = tuple(r for r in requirements if r.layer == layer_num)
        covered = sum(
            1 for r in layer_reqs
            if link_by_id.get(r.id) is not None
            and link_by_id[r.id].status == COVERED
        )
        partial = sum(
            1 for r in layer_reqs
            if link_by_id.get(r.id) is not None
            and link_by_id[r.id].status == PARTIAL
        )
        uncovered = len(layer_reqs) - covered - partial
        result.append(LayerCoverage(
            layer=layer_num,
            name=LAYER_NAMES[layer_num],
            total=len(layer_reqs),
            covered=covered,
            partial=partial,
            uncovered=uncovered,
        ))
    return tuple(result)


def generate_rtm(
    repo_root: pathlib.Path | None = None,
) -> RTMReport:
    """5계층 안전망 RTM 보고서 생성."""
    root = repo_root or _REPO_ROOT
    links = _build_links(REQUIREMENTS, MODULE_MAP, root)
    layer_cov = _compute_layer_coverage(REQUIREMENTS, links)

    total_covered = sum(1 for ln in links if ln.status == COVERED)
    total_partial = sum(1 for ln in links if ln.status == PARTIAL)
    total_uncovered = len(links) - total_covered - total_partial

    return RTMReport(
        requirements=REQUIREMENTS,
        links=links,
        layer_coverage=layer_cov,
        total_requirements=len(REQUIREMENTS),
        total_covered=total_covered,
        total_partial=total_partial,
        total_uncovered=total_uncovered,
    )


def get_gaps(report: RTMReport) -> tuple[TraceabilityLink, ...]:
    """UNCOVERED 또는 PARTIAL 상태 링크만 반환."""
    return tuple(ln for ln in report.links if ln.status != COVERED)


def filter_by_layer(
    report: RTMReport, layer: int,
) -> tuple[TraceabilityLink, ...]:
    """특정 계층 링크만 반환."""
    req_ids = frozenset(r.id for r in report.requirements if r.layer == layer)
    return tuple(ln for ln in report.links if ln.req_id in req_ids)


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------


def _bar(pct: float) -> str:
    filled = int(pct / 10)
    return "█" * filled + "░" * (10 - filled)


def _print_report(report: RTMReport, as_json: bool) -> None:
    if as_json:
        print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False))
        return
    print("=" * 60)
    print("  RTM 5계층 안전망 커버리지 보고서")
    print("=" * 60)
    for lc in report.layer_coverage:
        print(f"\n  L{lc.layer} {lc.name}")
        print(f"    {_bar(lc.coverage_pct)} {lc.coverage_pct:.1f}%")
        print(f"    총 {lc.total} | "
              f"충족 {lc.covered} | "
              f"부분 {lc.partial} | "
              f"미충족 {lc.uncovered}")
    print(f"\n{'─' * 60}")
    print(f"  전체: {report.overall_coverage_pct:.1f}% "
          f"({report.total_covered}/{report.total_requirements})")
    print("=" * 60)


def _print_layer(report: RTMReport, layer: int, as_json: bool) -> None:
    links = filter_by_layer(report, layer)
    if as_json:
        print(json.dumps(
            [ln.as_dict() for ln in links],
            indent=2, ensure_ascii=False,
        ))
        return
    name = LAYER_NAMES.get(layer, f"Layer {layer}")
    print(f"\n  L{layer} {name} 요구사항 추적")
    print("─" * 60)
    for ln in links:
        icon = {"COVERED": "✓", "PARTIAL": "△", "UNCOVERED": "✗"}[ln.status]
        print(f"  [{icon}] {ln.req_id}  {ln.status:<10} {ln.module_path}")


def _print_gaps(report: RTMReport, as_json: bool) -> None:
    gaps = get_gaps(report)
    if as_json:
        print(json.dumps(
            [ln.as_dict() for ln in gaps],
            indent=2, ensure_ascii=False,
        ))
        return
    if not gaps:
        print("  모든 요구사항이 충족됨 — 갭 없음")
        return
    print(f"\n  미충족/부분 충족 요구사항: {len(gaps)}건")
    print("─" * 60)
    for ln in gaps:
        icon = "△" if ln.status == PARTIAL else "✗"
        print(f"  [{icon}] {ln.req_id}  {ln.status:<10} {ln.module_path}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="RTM 5계층 안전망 요구사항 추적 행렬 생성",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--report", action="store_true",
                       help="전체 RTM 보고서 출력")
    group.add_argument("--layer", type=int, choices=[1, 2, 3, 4, 5],
                       help="특정 계층 상세 조회")
    group.add_argument("--gaps", action="store_true",
                       help="미충족 요구사항만 조회")
    parser.add_argument("--json", action="store_true",
                        help="JSON 형식 출력")
    args = parser.parse_args()

    report = generate_rtm()

    if args.report:
        _print_report(report, args.json)
    elif args.layer is not None:
        _print_layer(report, args.layer, args.json)
    elif args.gaps:
        _print_gaps(report, args.json)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    _main()
