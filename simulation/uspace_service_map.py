"""ODYSSEY Phase 401 — EASA U-space U1-U4 서비스 매핑.

SDACS 기능 ↔ EASA U-space 서비스를 결정적으로 대응시키는 정합성 매트릭스다.
ODYSSEY 국제 확장(EASA U-space·FAA UTM·K-UTM 동시 호환)에서 "SDACS 가 U-space
규제(EU 2021/664)와 CORUS ConOps U1-U4 서비스 레벨을 어디까지 충족하는가" 를
객관적으로 답하기 위한 자가 평가 기준 모듈이다.

근거 (권위 있는 출처)
--------------------
- **EU 2021/664** (U-space 규제 프레임워크) §Art.2·5: *mandatory* U-space 서비스
  4종 — network identification·geo-awareness·UAS flight authorisation·traffic
  information. weather·conformance monitoring 은 조건부.
- **CORUS U-space ConOps** 서비스 레벨 U1(foundation)·U2(initial)·U3(advanced)·
  U4(full). 각 서비스를 도입 레벨로 분류.

정직 공시 (CLAUDE.md)
--------------------
``sdacs_module`` 은 해당 서비스를 *실제로* 제공하는 리포 내 모듈 경로다. 대응
모듈이 없는 서비스(예: U4 유인 항공 통합)는 ``None`` 으로 **갭(gap)** 임을 정직히
표면화한다 — 본 모듈의 가치는 충족 주장보다 *미충족 항목의 가시화* 에 있다. 매핑은
기능적 대응이며 EASA 공식 인증이 아니다.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/uspace_service_map.py --matrix      # 전체 매핑 매트릭스
    python simulation/uspace_service_map.py --coverage    # 커버리지 요약
    python simulation/uspace_service_map.py --level U2     # 레벨별 서비스
    python simulation/uspace_service_map.py --gaps         # 미충족(갭) 서비스
    python simulation/uspace_service_map.py --mandatory    # EU 2021/664 의무 서비스
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

# CORUS ConOps 서비스 레벨 (도입 단계).
SERVICE_LEVELS: tuple[str, ...] = ("U1", "U2", "U3", "U4")

_LEVEL_NAMES: dict[str, str] = {
    "U1": "Foundation (e-registration·e-identification·geo-awareness)",
    "U2": "Initial (flight planning·approval·tracking·monitoring)",
    "U3": "Advanced (conflict resolution·dynamic capacity)",
    "U4": "Full (high automation·manned integration)",
}


@dataclass(frozen=True)
class USpaceService:
    """단일 U-space 서비스와 SDACS 대응의 정의."""

    service_id: str         # 안정 식별자 (예: 'network_identification')
    name: str               # 서비스 명칭
    level: str              # 도입 레벨 U1..U4
    mandatory: bool         # EU 2021/664 의무 서비스 여부
    sdacs_module: str | None  # 제공 모듈 경로 (없으면 갭)
    summary: str            # 한 줄 설명

    def __post_init__(self) -> None:
        if not self.service_id or self.service_id != self.service_id.strip():
            raise ValueError("service_id must be non-empty and unpadded")
        if not self.name or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        if not self.summary or not self.summary.strip():
            raise ValueError("summary must be a non-empty string")
        if self.level not in SERVICE_LEVELS:
            raise ValueError(
                f"level must be one of {SERVICE_LEVELS}, got {self.level!r}"
            )
        if not isinstance(self.mandatory, bool):
            raise TypeError(f"mandatory must be bool, got {type(self.mandatory).__name__}")
        if self.sdacs_module is not None and not self.sdacs_module.strip():
            raise ValueError("sdacs_module must be None or a non-empty path")

    @property
    def is_implemented(self) -> bool:
        """SDACS 대응 모듈이 존재하면 True (갭이 아니면 True)."""
        return self.sdacs_module is not None


# EASA U-space 서비스 카탈로그 ↔ SDACS 모듈 매핑 (정본).
# sdacs_module 경로는 리포에 실재하는 모듈 — 미대응은 None(갭).
USPACE_SERVICES: tuple[USpaceService, ...] = (
    USpaceService(
        "network_identification", "Network identification service", "U1", True,
        "simulation/remote_id.py",
        "Remote ID 송출(ASTM F3411) — 드론 실시간 식별·위치 방송",
    ),
    USpaceService(
        "geo_awareness", "Geo-awareness service", "U1", True,
        "simulation/geofence_manager.py",
        "지오펜스·운용 제한구역(NFZ) 인지 — 동적 경계 포함",
    ),
    USpaceService(
        "uas_flight_authorisation", "UAS flight authorisation service", "U2", True,
        "src/airspace_control/controller/airspace_controller.py",
        "비행 승인(clearance) 발급 — AirspaceController 1Hz 관제",
    ),
    USpaceService(
        "traffic_information", "Traffic information service", "U2", True,
        "simulation/traffic_coordinator.py",
        "주변 교통 정보 제공 — 인접 드론·항적 공유",
    ),
    USpaceService(
        "weather_information", "Weather information service", "U2", False,
        "simulation/weather.py",
        "풍속장·기상 위험 정보 — APF 강풍 모드 연동",
    ),
    USpaceService(
        "conformance_monitoring", "Conformance monitoring service", "U2", False,
        "simulation/compliance_checker.py",
        "비행 계획 대비 적합성 감시 — ICAO 분리·규정 위반 탐지",
    ),
    USpaceService(
        "tracking", "Tracking service", "U2", False,
        "simulation/telemetry_recorder.py",
        "비행 추적 — 텔레메트리 기록·재생",
    ),
    USpaceService(
        "drone_aeronautical_information", "Drone aeronautical information mgmt", "U2", False,
        "simulation/notam_manager.py",
        "항공 정보(NOTAM) 관리 — 동적 NFZ 공지",
    ),
    USpaceService(
        "emergency_management", "Emergency management service", "U2", False,
        "simulation/emergency_protocol.py",
        "비상 관리 — RTB·안전 강하·우발 대응",
    ),
    USpaceService(
        "strategic_conflict_resolution", "Strategic conflict resolution", "U3", False,
        "simulation/path_deconflict.py",
        "전략적(사전) 충돌 해소 — 4D 경로 디컨플릭션·CBS",
    ),
    USpaceService(
        # 전략·전술 충돌 해소 모두 path_deconflict.py 가 제공 — 의도된 모듈 공유.
        "tactical_conflict_resolution", "Tactical conflict resolution (DAA)", "U3", False,
        "simulation/path_deconflict.py",
        "전술적(실시간) 충돌 회피 — APF + CPA 90초 예측",
    ),
    USpaceService(
        "dynamic_capacity_management", "Dynamic capacity management", "U3", False,
        "simulation/airspace_capacity.py",
        "동적 용량 관리 — 공역 혼잡도 기반 수용량 산정",
    ),
    USpaceService(
        "collaborative_interface_atc", "Collaborative interface with ATC", "U3", False,
        "simulation/kutm_protocol.py",
        "유인 ATC 협조 인터페이스 — K-UTM 프로토콜 연계",
    ),
    USpaceService(
        "manned_aviation_integration", "Integration with manned aviation", "U4", False,
        None,
        "유인 항공과의 완전 통합 — 현 시뮬 범위 밖 (갭)",
    ),
)


@dataclass(frozen=True)
class CoverageReport:
    """U-space 서비스 충족 커버리지 요약."""

    total: int
    implemented: int
    gaps: int
    mandatory_total: int
    mandatory_implemented: int
    by_level: Mapping[str, tuple[int, int]]  # level -> (implemented, total), read-only

    def __post_init__(self) -> None:
        if min(self.total, self.implemented, self.gaps,
               self.mandatory_total, self.mandatory_implemented) < 0:
            raise ValueError("counts must be non-negative")
        if self.implemented + self.gaps != self.total:
            raise ValueError(
                f"implemented ({self.implemented}) + gaps ({self.gaps}) "
                f"!= total ({self.total})"
            )
        if self.mandatory_implemented > self.mandatory_total:
            raise ValueError("mandatory_implemented cannot exceed mandatory_total")
        if self.implemented > self.total:
            raise ValueError("implemented cannot exceed total")

    @property
    def coverage_pct(self) -> float:
        """전체 서비스 충족 비율 (%)."""
        return 100.0 * self.implemented / self.total if self.total else 0.0

    @property
    def mandatory_coverage_pct(self) -> float:
        """EU 2021/664 의무 서비스 충족 비율 (%)."""
        if not self.mandatory_total:
            return 0.0
        return 100.0 * self.mandatory_implemented / self.mandatory_total

    @property
    def is_mandatory_complete(self) -> bool:
        """의무 서비스 전부 충족 여부. 의무 서비스가 0건이면 False(공허참 방지)."""
        if not self.mandatory_total:
            return False
        return self.mandatory_implemented == self.mandatory_total


def find_service(service_id: str) -> USpaceService:
    """식별자로 서비스를 조회한다. 없으면 KeyError."""
    for svc in USPACE_SERVICES:
        if svc.service_id == service_id:
            return svc
    raise KeyError(f"unknown U-space service: {service_id!r}")


def services_by_level(level: str) -> tuple[USpaceService, ...]:
    """도입 레벨(U1..U4)에 속한 서비스를 식별자 정렬로 반환한다."""
    if level not in SERVICE_LEVELS:
        raise ValueError(f"level must be one of {SERVICE_LEVELS}, got {level!r}")
    return tuple(
        sorted((s for s in USPACE_SERVICES if s.level == level), key=lambda s: s.service_id)
    )


def mandatory_services() -> tuple[USpaceService, ...]:
    """EU 2021/664 의무 서비스를 식별자 정렬로 반환한다."""
    return tuple(sorted((s for s in USPACE_SERVICES if s.mandatory), key=lambda s: s.service_id))


def gaps() -> tuple[USpaceService, ...]:
    """SDACS 대응 모듈이 없는(미충족) 서비스를 식별자 정렬로 반환한다."""
    return tuple(
        sorted((s for s in USPACE_SERVICES if not s.is_implemented), key=lambda s: s.service_id)
    )


def implemented_services() -> tuple[USpaceService, ...]:
    """SDACS 대응 모듈이 있는 서비스를 식별자 정렬로 반환한다."""
    return tuple(
        sorted((s for s in USPACE_SERVICES if s.is_implemented), key=lambda s: s.service_id)
    )


def coverage_report() -> CoverageReport:
    """전체 서비스 충족 현황을 집계한 결정적 커버리지 리포트를 생성한다."""
    total = len(USPACE_SERVICES)
    implemented = sum(1 for s in USPACE_SERVICES if s.is_implemented)
    mandatory = [s for s in USPACE_SERVICES if s.mandatory]
    mandatory_impl = sum(1 for s in mandatory if s.is_implemented)
    by_level: dict[str, tuple[int, int]] = {}
    for level in SERVICE_LEVELS:
        members = [s for s in USPACE_SERVICES if s.level == level]
        by_level[level] = (sum(1 for s in members if s.is_implemented), len(members))
    return CoverageReport(
        total=total,
        implemented=implemented,
        gaps=total - implemented,
        mandatory_total=len(mandatory),
        mandatory_implemented=mandatory_impl,
        by_level=MappingProxyType(by_level),
    )


def service_matrix() -> tuple[dict[str, object], ...]:
    """도구 간 교환용 매핑 매트릭스를 (레벨, 식별자) 정렬 행으로 반환한다."""
    ordered = sorted(USPACE_SERVICES, key=lambda s: (SERVICE_LEVELS.index(s.level), s.service_id))
    return tuple(
        {
            "service_id": s.service_id,
            "name": s.name,
            "level": s.level,
            "mandatory": s.mandatory,
            "implemented": s.is_implemented,
            "sdacs_module": s.sdacs_module,
        }
        for s in ordered
    )


def _format_matrix() -> str:
    lines = ["U-space 서비스 ↔ SDACS 매핑 매트릭스", ""]
    for row in service_matrix():
        mark = "✓" if row["implemented"] else "✗(갭)"
        req = "필수" if row["mandatory"] else "조건부"
        module = row["sdacs_module"] or "—"
        lines.append(f"[{row['level']}] {mark} {req:4} {row['name']}")
        lines.append(f"      → {module}")
    return "\n".join(lines)


def _format_coverage() -> str:
    r = coverage_report()
    lines = [
        "U-space 커버리지 요약",
        "",
        f"전체 충족   : {r.implemented}/{r.total} ({r.coverage_pct:.0f}%)",
        f"의무(EU)    : {r.mandatory_implemented}/{r.mandatory_total} "
        f"({r.mandatory_coverage_pct:.0f}%) "
        f"{'— 완전 충족' if r.is_mandatory_complete else '— 미완'}",
        "",
        "레벨별:",
    ]
    for level in SERVICE_LEVELS:
        impl, tot = r.by_level[level]
        lines.append(f"  {level} {_LEVEL_NAMES[level].split(' (')[0]:9}: {impl}/{tot}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EASA U-space 서비스 매핑 (ODYSSEY Phase 401)")
    parser.add_argument("--matrix", action="store_true", help="전체 매핑 매트릭스 출력")
    parser.add_argument("--coverage", action="store_true", help="커버리지 요약 출력")
    parser.add_argument("--level", choices=SERVICE_LEVELS, help="레벨별 서비스 출력")
    parser.add_argument("--gaps", action="store_true", help="미충족(갭) 서비스 출력")
    parser.add_argument("--mandatory", action="store_true", help="EU 2021/664 의무 서비스 출력")
    args = parser.parse_args(argv)

    if args.matrix:
        print(_format_matrix())
    elif args.coverage:
        print(_format_coverage())
    elif args.level:
        for svc in services_by_level(args.level):
            print(f"{svc.service_id}: {svc.name} — {svc.summary}")
    elif args.gaps:
        for svc in gaps():
            print(f"[{svc.level}] {svc.name}: {svc.summary}")
    elif args.mandatory:
        for svc in mandatory_services():
            mark = "✓" if svc.is_implemented else "✗"
            print(f"{mark} {svc.name} → {svc.sdacs_module or '—'}")
    else:
        print(_format_coverage())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
