"""ODYSSEY Phase 402 — FAA UTM ConOps v2.0 정렬 (USS 역할 요건 갭 분석).

SDACS 기능 ↔ FAA UTM USS(UAS Service Supplier) 역할 요건을 결정적으로 대응시키는
적합성 매트릭스다. ODYSSEY 국제 확장(EASA U-space·FAA UTM·K-UTM 동시 호환)에서
Phase 401(EASA U-space)의 *미국* 대응물 — "SDACS 가 FAA UTM ConOps v2.0 이
요구하는 USS 역할(operation intent 교환·strategic deconfliction·DSS 동기화 등)을
어디까지 충족하는가" 를 객관적으로 답하기 위한 자가 평가 기준 모듈이다.

근거 (권위 있는 출처)
--------------------
- **FAA UTM ConOps v2.0** (FAA, 2020) §3-§4: USS 가 UAS 운영자에게 제공하는 서비스와
  USS Network 내 USS-to-USS 협조 역할. 운영 의도(operation intent) 공유·전략적
  분리(strategic deconfliction)·적합성 감시(conformance monitoring)·제약 전파
  (UVR/constraint)·네트워크 Remote ID 가 핵심.
- **Discovery and Synchronization Service (DSS)** — USS 간 운영 발견·동기화 인터페이스
  (ASTM F3548-21 정렬). FAA UTM 의 USS Network 골격.

핵심(core) 요건의 정의 — *프로젝트 해석*
--------------------
``core=True`` 는 USS Network 참여에 기반이 되는 역할(운영 의도 관리·전략적 분리·
적합성 감시·네트워크 Remote ID·제약 전파·USS 간 통신·DSS 동기화)이다. 나머지
(LAANC 승인·기상·용량 등)는 역할별 보강(supplemental) 서비스로 분류한다. 이
core/보강 구분은 ConOps 의 강조점을 따른 **본 프로젝트의 해석**이며 FAA 가 명시한
필수/선택 목록이 아니다 — 특히 적합성 감시(conformance monitoring)는 ConOps 가
USS 가 *자기 운영자에게* 제공하는 서비스로 기술하나, 안전 핵심성을 고려해 core 로
분류했다.

정직 공시 (CLAUDE.md)
--------------------
``sdacs_module`` 은 해당 역할을 *실제로* 제공하는 리포 내 모듈 경로다. 대응 모듈이
없는 역할(운영자 자격 검증·공공안전 데이터 접근)은 ``None`` 으로 **갭(gap)** 임을
정직히 표면화한다 — 본 모듈의 가치는 충족 주장보다 *미충족 항목의 가시화* 에 있다.
매핑은 기능적 대응이며 FAA 의 USS 공식 승인이 아니다.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/faa_uss_roles.py --matrix            # 전체 역할 매트릭스
    python simulation/faa_uss_roles.py --conformance       # 적합성 요약
    python simulation/faa_uss_roles.py --category "Inter-USS / Network"
    python simulation/faa_uss_roles.py --gaps              # 미충족(갭) 역할
    python simulation/faa_uss_roles.py --core              # 핵심 USS Network 역할
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

# FAA UTM ConOps v2.0 USS 역할 범주 (기능 영역).
CATEGORIES: tuple[str, ...] = (
    "Operation Management",
    "Airspace & Constraints",
    "Identification & Surveillance",
    "Information Services",
    "Inter-USS / Network",
    "Safety & Contingency",
)


@dataclass(frozen=True)
class USSRequirement:
    """단일 USS 역할 요건과 SDACS 대응의 정의."""

    requirement_id: str       # 안정 식별자 (예: 'strategic_deconfliction')
    name: str                 # 역할 명칭
    category: str             # 기능 범주 (CATEGORIES 중 하나)
    core: bool                # USS Network 참여 필수 역할 여부
    sdacs_module: str | None  # 제공 모듈 경로 (없으면 갭)
    summary: str              # 한 줄 설명

    def __post_init__(self) -> None:
        if not self.requirement_id or self.requirement_id != self.requirement_id.strip():
            raise ValueError("requirement_id must be non-empty and unpadded")
        if not self.name or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        if not self.summary or not self.summary.strip():
            raise ValueError("summary must be a non-empty string")
        if self.category not in CATEGORIES:
            raise ValueError(
                f"category must be one of {CATEGORIES}, got {self.category!r}"
            )
        if not isinstance(self.core, bool):
            raise TypeError(f"core must be bool, got {type(self.core).__name__}")
        if self.sdacs_module is not None and not self.sdacs_module.strip():
            raise ValueError("sdacs_module must be None or a non-empty path")

    @property
    def is_implemented(self) -> bool:
        """SDACS 대응 모듈이 존재하면 True (갭이 아니면 True)."""
        return self.sdacs_module is not None


# FAA UTM ConOps v2.0 USS 역할 카탈로그 ↔ SDACS 모듈 매핑 (정본).
# sdacs_module 경로는 리포에 실재하는 모듈 — 미대응은 None(갭).
USS_REQUIREMENTS: tuple[USSRequirement, ...] = (
    USSRequirement(
        "operation_planning", "Operation intent planning & management",
        "Operation Management", True,
        "simulation/operational_intent.py",
        "운영 의도(4D 볼륨) 계획·제출·관리 — ASTM F3548-21 정렬 직렬화",
    ),
    USSRequirement(
        "strategic_deconfliction", "Strategic deconfliction",
        "Operation Management", True,
        "simulation/path_deconflict.py",
        "사전 운영 의도 충돌 해소 — 4D 경로 디컨플릭션·CBS",
    ),
    USSRequirement(
        "conformance_monitoring", "Conformance monitoring",
        "Operation Management", True,
        "simulation/compliance_checker.py",
        "운영 계획 대비 적합성 감시 — 분리·규정 위반 탐지",
    ),
    USSRequirement(
        "operator_credentialing", "Operator credential verification",
        "Operation Management", False,
        None,
        "운영자·조종자 자격 검증·airman 데이터 연계 — 현 시뮬 범위 밖 (갭)",
    ),
    USSRequirement(
        "constraint_dissemination", "Constraint (UVR) dissemination",
        "Airspace & Constraints", True,
        "simulation/notam_manager.py",
        "UAS Volume Reservation·동적 제약 전파 — NOTAM·동적 NFZ 공지",
    ),
    USSRequirement(
        "airspace_authorization", "Airspace authorization (LAANC)",
        "Airspace & Constraints", False,
        "simulation/faa_laanc.py",
        "통제 공역 비행 승인(LAANC) — UASFM 격자 기반 자동 승인",
    ),
    USSRequirement(
        "geo_awareness", "Geo-awareness / geo-fencing",
        "Airspace & Constraints", False,
        "simulation/geofence_manager.py",
        "지오펜스·운용 제한구역 인지 — 동적 경계 포함",
    ),
    USSRequirement(
        "network_remote_id", "Network Remote ID",
        "Identification & Surveillance", True,
        "simulation/remote_id.py",
        "네트워크 Remote ID 송출(ASTM F3411) — 실시간 식별·위치 방송",
    ),
    USSRequirement(
        "position_reporting", "Position reporting & tracking",
        "Identification & Surveillance", False,
        "simulation/telemetry_recorder.py",
        "위치·항적 보고 — 텔레메트리 기록·재생",
    ),
    USSRequirement(
        "weather_integration", "Weather data integration",
        "Information Services", False,
        "simulation/weather.py",
        "기상 정보 통합 — 풍속장·APF 강풍 모드 연동",
    ),
    USSRequirement(
        "capacity_management", "Dynamic capacity management",
        "Information Services", False,
        "simulation/airspace_capacity.py",
        "동적 용량 관리 — 공역 혼잡도 기반 수용량 산정",
    ),
    USSRequirement(
        "public_safety_access", "Public safety / LEA data access",
        "Information Services", False,
        None,
        "공공안전·법집행기관 데이터 접근 포털 — 현 시뮬 범위 밖 (갭)",
    ),
    USSRequirement(
        # operation_planning 과 동일 모듈 공유 — operational_intent.py 가 4D 볼륨
        # *관리* 와 USS 간 *교환 직렬화* 둘 다 제공(의도된 모듈 공유).
        "inter_uss_communication", "Inter-USS communication",
        "Inter-USS / Network", True,
        "simulation/operational_intent.py",
        "USS 간 운영 의도 교환 — 라운드트립 직렬화·보수적 4D 교차",
    ),
    USSRequirement(
        "discovery_synchronization", "Discovery & Synchronization (DSS)",
        "Inter-USS / Network", True,
        "simulation/federation_discovery.py",
        "USS 간 운영 발견·동기화 — ASTM F3548 DSS 유사 결정적 모델",
    ),
    USSRequirement(
        # ConOps v2.0 는 데이터 보존을 일반 USS 의무로 규정 — 본 매핑은 *인스턴스 경계를
        # 넘는* 변조 탐지 원장(federation_audit.py)이 제공하므로 Inter-USS / Network 로 분류.
        "data_archiving", "Operations data archiving",
        "Inter-USS / Network", False,
        "simulation/federation_audit.py",
        "운영 데이터 보존 — 변조 탐지 SHA-256 해시 체인 원장",
    ),
    USSRequirement(
        "conflict_advisory", "Conflict advisory & alerting",
        "Safety & Contingency", False,
        "simulation/traffic_coordinator.py",
        "충돌 권고·경보 — 인접 드론·항적 정보 제공",
    ),
    USSRequirement(
        "contingency_management", "Off-nominal / contingency management",
        "Safety & Contingency", False,
        "simulation/emergency_protocol.py",
        "비정상·우발 상황 관리 — RTB·안전 강하·비상 대응",
    ),
)


@dataclass(frozen=True)
class ConformanceReport:
    """USS 역할 충족 적합성 요약."""

    total: int
    implemented: int
    gaps: int
    core_total: int
    core_implemented: int
    by_category: Mapping[str, tuple[int, int]]  # category -> (implemented, total), read-only

    def __post_init__(self) -> None:
        if min(self.total, self.implemented, self.gaps,
               self.core_total, self.core_implemented) < 0:
            raise ValueError("counts must be non-negative")
        if self.implemented + self.gaps != self.total:
            raise ValueError(
                f"implemented ({self.implemented}) + gaps ({self.gaps}) "
                f"!= total ({self.total})"
            )
        if self.core_implemented > self.core_total:
            raise ValueError("core_implemented cannot exceed core_total")
        if self.implemented > self.total:
            raise ValueError("implemented cannot exceed total")
        # 핵심 역할은 전체 역할의 부분집합이므로 충족 핵심 수가 충족 전체 수를 넘을 수 없다.
        if self.core_implemented > self.implemented:
            raise ValueError("core_implemented cannot exceed implemented")

    @property
    def coverage_pct(self) -> float:
        """전체 역할 충족 비율 (%)."""
        return 100.0 * self.implemented / self.total if self.total else 0.0

    @property
    def core_coverage_pct(self) -> float:
        """핵심 USS Network 역할 충족 비율 (%)."""
        if not self.core_total:
            return 0.0
        return 100.0 * self.core_implemented / self.core_total

    @property
    def is_core_complete(self) -> bool:
        """핵심 역할 전부 충족 여부. 핵심 역할이 0건이면 False(공허참 방지)."""
        if not self.core_total:
            return False
        return self.core_implemented == self.core_total


def find_requirement(requirement_id: str) -> USSRequirement:
    """식별자로 USS 역할 요건을 조회한다. 없으면 KeyError."""
    for req in USS_REQUIREMENTS:
        if req.requirement_id == requirement_id:
            return req
    raise KeyError(f"unknown USS requirement: {requirement_id!r}")


def requirements_by_category(category: str) -> tuple[USSRequirement, ...]:
    """범주에 속한 역할 요건을 식별자 정렬로 반환한다."""
    if category not in CATEGORIES:
        raise ValueError(f"category must be one of {CATEGORIES}, got {category!r}")
    return tuple(
        sorted(
            (r for r in USS_REQUIREMENTS if r.category == category),
            key=lambda r: r.requirement_id,
        )
    )


def core_requirements() -> tuple[USSRequirement, ...]:
    """USS Network 참여 필수(core) 역할을 식별자 정렬로 반환한다."""
    return tuple(
        sorted((r for r in USS_REQUIREMENTS if r.core), key=lambda r: r.requirement_id)
    )


def gaps() -> tuple[USSRequirement, ...]:
    """SDACS 대응 모듈이 없는(미충족) 역할을 식별자 정렬로 반환한다."""
    return tuple(
        sorted(
            (r for r in USS_REQUIREMENTS if not r.is_implemented),
            key=lambda r: r.requirement_id,
        )
    )


def implemented_requirements() -> tuple[USSRequirement, ...]:
    """SDACS 대응 모듈이 있는 역할을 식별자 정렬로 반환한다."""
    return tuple(
        sorted(
            (r for r in USS_REQUIREMENTS if r.is_implemented),
            key=lambda r: r.requirement_id,
        )
    )


def conformance_report() -> ConformanceReport:
    """전체 역할 충족 현황을 집계한 결정적 적합성 리포트를 생성한다."""
    total = len(USS_REQUIREMENTS)
    implemented = sum(1 for r in USS_REQUIREMENTS if r.is_implemented)
    core = [r for r in USS_REQUIREMENTS if r.core]
    core_impl = sum(1 for r in core if r.is_implemented)
    by_category: dict[str, tuple[int, int]] = {}
    for category in CATEGORIES:
        members = [r for r in USS_REQUIREMENTS if r.category == category]
        by_category[category] = (sum(1 for r in members if r.is_implemented), len(members))
    return ConformanceReport(
        total=total,
        implemented=implemented,
        gaps=total - implemented,
        core_total=len(core),
        core_implemented=core_impl,
        by_category=MappingProxyType(by_category),
    )


def role_matrix() -> tuple[Mapping[str, object], ...]:
    """도구 간 교환용 역할 매트릭스를 (범주, 식별자) 정렬 행으로 반환한다.

    각 행은 ``MappingProxyType`` 읽기 전용 — ``by_category`` 와 동일한 불변 보장.
    """
    ordered = sorted(
        USS_REQUIREMENTS,
        key=lambda r: (CATEGORIES.index(r.category), r.requirement_id),
    )
    return tuple(
        MappingProxyType(
            {
                "requirement_id": r.requirement_id,
                "name": r.name,
                "category": r.category,
                "core": r.core,
                "implemented": r.is_implemented,
                "sdacs_module": r.sdacs_module,
            }
        )
        for r in ordered
    )


def _format_matrix() -> str:
    lines = ["FAA UTM USS 역할 ↔ SDACS 매핑 매트릭스", ""]
    for row in role_matrix():
        mark = "✓" if row["implemented"] else "✗(갭)"
        kind = "핵심" if row["core"] else "보강"
        module = row["sdacs_module"] or "—"
        lines.append(f"[{row['category']}] {mark} {kind} {row['name']}")
        lines.append(f"      → {module}")
    return "\n".join(lines)


def _format_conformance() -> str:
    r = conformance_report()
    lines = [
        "FAA UTM USS 적합성 요약",
        "",
        f"전체 충족   : {r.implemented}/{r.total} ({r.coverage_pct:.0f}%)",
        f"핵심(Network): {r.core_implemented}/{r.core_total} "
        f"({r.core_coverage_pct:.0f}%) "
        f"{'— 완전 충족' if r.is_core_complete else '— 미완'}",
        "",
        "범주별:",
    ]
    for category in CATEGORIES:
        impl, tot = r.by_category[category]
        lines.append(f"  {category:30}: {impl}/{tot}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="FAA UTM ConOps v2.0 USS 역할 매핑 (ODYSSEY Phase 402)"
    )
    parser.add_argument("--matrix", action="store_true", help="전체 역할 매트릭스 출력")
    parser.add_argument("--conformance", action="store_true", help="적합성 요약 출력")
    parser.add_argument("--category", choices=CATEGORIES, help="범주별 역할 출력")
    parser.add_argument("--gaps", action="store_true", help="미충족(갭) 역할 출력")
    parser.add_argument("--core", action="store_true", help="핵심 USS Network 역할 출력")
    args = parser.parse_args(argv)

    if args.matrix:
        print(_format_matrix())
    elif args.conformance:
        print(_format_conformance())
    elif args.category:
        for req in requirements_by_category(args.category):
            print(f"{req.requirement_id}: {req.name} — {req.summary}")
    elif args.gaps:
        for req in gaps():
            print(f"[{req.category}] {req.name}: {req.summary}")
    elif args.core:
        for req in core_requirements():
            mark = "✓" if req.is_implemented else "✗"
            print(f"{mark} {req.name} → {req.sdacs_module or '—'}")
    else:
        print(_format_conformance())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
