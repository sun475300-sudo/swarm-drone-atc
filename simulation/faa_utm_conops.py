"""ODYSSEY Phase 402 — FAA UTM ConOps v2.0 정렬 · USS 역할 요건 갭 분석.

SDACS 기능 ↔ FAA UTM(무인기 교통 관리) Concept of Operations v2.0 의 USS(UAS
Service Supplier) 역할 요건을 결정적으로 대응시키는 적합성 매트릭스다. Phase 401
(EASA U-space 매핑)의 자매 모듈로, ODYSSEY 국제 확장(EASA U-space·FAA UTM·K-UTM
3대 체계 동시 호환)에서 "SDACS 가 FAA UTM USS 요건을 어디까지 충족하는가" 를
객관적으로 답하기 위한 자가 평가 기준이다.

근거 (권위 있는 출처)
--------------------
- **FAA UTM ConOps v2.0** (2020-03): UTM 아키텍처 원칙과 USS/FIMS/SDSP/Operator
  역할 분담. 핵심 USS 능력군 — Operation Intent 공유·Strategic Deconfliction·
  Conformance Monitoring·Remote ID & Tracking·Constraint(UVR) 관리·
  Discovery & Synchronization(USS↔USS)·Authentication & Authorization.
- **14 CFR Part 89** (Remote ID 규칙): networked/broadcast 원격 식별 의무.
- **LAANC** (Low Altitude Authorization and Notification Capability): 관제권 내
  비행 승인.

정직 공시 (CLAUDE.md)
--------------------
``sdacs_module`` 은 해당 능력을 *실제로* 제공하는 리포 내 모듈 경로다. 대응 모듈이
없는 요건(예: FAA 정부 FIMS 게이트웨이 연동)은 ``None`` 으로 **갭(gap)** 임을 정직히
표면화한다 — 본 모듈의 가치는 충족 주장보다 *미충족 요건의 가시화* 에 있다. 매핑은
기능적 대응이며 FAA 공식 인증·USS 승인이 아니다.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/faa_utm_conops.py --matrix       # 전체 매핑 매트릭스
    python simulation/faa_utm_conops.py --conformance  # 적합성 요약
    python simulation/faa_utm_conops.py --role USS     # 역할별 능력
    python simulation/faa_utm_conops.py --gaps          # 미충족(갭) 요건
    python simulation/faa_utm_conops.py --required      # FAA UTM 핵심 요건
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

# FAA UTM ConOps v2.0 아키텍처 역할 (능력 책임 주체).
UTM_ROLES: tuple[str, ...] = ("USS", "FIMS", "SDSP", "OPERATOR")

_ROLE_NAMES: dict[str, str] = {
    "USS": "UAS Service Supplier (운영 지원·전략 디컨플릭션·식별)",
    "FIMS": "Flight Information Management System (FAA 게이트웨이)",
    "SDSP": "Supplemental Data Service Provider (기상·지형 보조 데이터)",
    "OPERATOR": "Operator (운영자·기체 등록·계획 제출)",
}


@dataclass(frozen=True)
class FaaUtmCapability:
    """단일 FAA UTM USS 역할 요건과 SDACS 대응의 정의."""

    capability_id: str        # 안정 식별자 (예: 'strategic_deconfliction')
    name: str                 # 능력 명칭
    role: str                 # 책임 역할 USS/FIMS/SDSP/OPERATOR
    required: bool            # FAA UTM 핵심(필수) 요건 여부
    sdacs_module: str | None  # 제공 모듈 경로 (없으면 갭)
    conops_area: str          # ConOps v2.0 능력군 명칭
    summary: str              # 한 줄 설명

    def __post_init__(self) -> None:
        if not self.capability_id or self.capability_id != self.capability_id.strip():
            raise ValueError("capability_id must be non-empty and unpadded")
        if not self.name or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        if not self.conops_area or not self.conops_area.strip():
            raise ValueError("conops_area must be a non-empty string")
        if not self.summary or not self.summary.strip():
            raise ValueError("summary must be a non-empty string")
        if self.role not in UTM_ROLES:
            raise ValueError(f"role must be one of {UTM_ROLES}, got {self.role!r}")
        if not isinstance(self.required, bool):
            raise TypeError(f"required must be bool, got {type(self.required).__name__}")
        if self.sdacs_module is not None and not self.sdacs_module.strip():
            raise ValueError("sdacs_module must be None or a non-empty path")

    @property
    def is_implemented(self) -> bool:
        """SDACS 대응 모듈이 존재하면 True (갭이 아니면 True)."""
        return self.sdacs_module is not None


# FAA UTM ConOps v2.0 USS 역할 요건 카탈로그 ↔ SDACS 모듈 매핑 (정본).
# sdacs_module 경로는 리포에 실재하는 모듈 — 미대응은 None(갭).
FAA_UTM_CAPABILITIES: tuple[FaaUtmCapability, ...] = (
    FaaUtmCapability(
        "operation_intent_sharing", "Operation intent sharing", "USS", True,
        "simulation/operational_intent.py", "Operation Planning",
        "운영 의도(4D 볼륨) 공유 — 사전 비행 계획 제출·교환",
    ),
    FaaUtmCapability(
        "strategic_deconfliction", "Strategic deconfliction", "USS", True,
        "simulation/path_deconflict.py", "Strategic Deconfliction",
        "전략적(사전) 충돌 해소 — 4D 경로 디컨플릭션·CBS",
    ),
    FaaUtmCapability(
        "conformance_monitoring", "Conformance monitoring", "USS", True,
        "simulation/compliance_checker.py", "Conformance Monitoring",
        "운영 의도 볼륨 대비 적합성 감시 — 이탈 탐지",
    ),
    FaaUtmCapability(
        "remote_identification", "Remote identification", "USS", True,
        "simulation/remote_id.py", "Remote ID & Tracking",
        "원격 식별(14 CFR Part 89·ASTM F3411) — networked/broadcast",
    ),
    FaaUtmCapability(
        "position_reporting", "Position reporting & tracking", "USS", False,
        "simulation/telemetry_recorder.py", "Remote ID & Tracking",
        "위치 보고·항적 추적 — 텔레메트리 기록·공유",
    ),
    FaaUtmCapability(
        "conflict_advisory_alert", "Conflict advisory & alert", "USS", False,
        "simulation/path_deconflict.py", "Tactical Advisory",
        "전술 충돌 권고·경보 — APF + CPA 90초 예측 advisory",
    ),
    FaaUtmCapability(
        "constraint_dissemination", "Constraint (UVR) dissemination", "USS", True,
        "simulation/notam_manager.py", "Constraint Management",
        "UAS 볼륨 예약(UVR)·동적 제한구역 전파 — NOTAM 공지",
    ),
    FaaUtmCapability(
        "airspace_authorization", "Airspace authorization (LAANC)", "USS", True,
        "simulation/faa_laanc.py", "Authentication & Authorization",
        "관제권 내 비행 승인 — LAANC 자동 인가",
    ),
    FaaUtmCapability(
        "uss_discovery_sync", "USS discovery & synchronization", "USS", True,
        "simulation/federation_discovery.py", "Discovery & Synchronization",
        "USS↔USS 발견·데이터 동기화 — 인접 공역 연합 (Phase 421-440 심화)",
    ),
    FaaUtmCapability(
        "inter_uss_negotiation", "Inter-USS negotiation & replanning", "USS", False,
        "simulation/autonomous_negotiation.py", "Strategic Deconfliction",
        "USS 간 협상·재계획 — 충돌 시 자율 우선순위 협상",
    ),
    FaaUtmCapability(
        "emergency_management", "Off-nominal & emergency management", "USS", False,
        "simulation/emergency_protocol.py", "Contingency Management",
        "비정상·비상 관리 — RTB·안전 강하·우발 대응",
    ),
    FaaUtmCapability(
        "operator_uas_registration", "Operator & UAS registration", "OPERATOR", True,
        "simulation/drone_registry.py", "Registration",
        "운영자·기체 등록 — 식별자 발급·등록 대장",
    ),
    FaaUtmCapability(
        "fims_data_exchange", "FIMS data exchange", "FIMS", True,
        None, "Authentication & Authorization",
        "FAA 정부 게이트웨이(FIMS) 연동 — 현 시뮬 범위 밖 (갭)",
    ),
    FaaUtmCapability(
        "weather_data_supplement", "Supplemental weather data", "SDSP", False,
        "simulation/weather.py", "Supplemental Data",
        "보조 기상 데이터 — 풍속장·APF 강풍 모드 연동",
    ),
    FaaUtmCapability(
        "terrain_obstacle_supplement", "Supplemental terrain/obstacle data", "SDSP", False,
        "simulation/terrain_awareness_system.py", "Supplemental Data",
        "보조 지형·장애물 데이터 — 지형 인지·회피",
    ),
)


@dataclass(frozen=True)
class ConformanceReport:
    """FAA UTM USS 요건 충족 적합성 요약."""

    total: int
    implemented: int
    gaps: int
    required_total: int
    required_implemented: int
    by_role: Mapping[str, tuple[int, int]]  # role -> (implemented, total), read-only

    def __post_init__(self) -> None:
        if min(self.total, self.implemented, self.gaps,
               self.required_total, self.required_implemented) < 0:
            raise ValueError("counts must be non-negative")
        if self.implemented + self.gaps != self.total:
            raise ValueError(
                f"implemented ({self.implemented}) + gaps ({self.gaps}) "
                f"!= total ({self.total})"
            )
        if self.required_implemented > self.required_total:
            raise ValueError("required_implemented cannot exceed required_total")
        if self.implemented > self.total:
            raise ValueError("implemented cannot exceed total")
        # 직접 생성 시에도 by_role 불변(읽기 전용)을 강제 — 평범한 dict 가
        # Mapping 을 만족해 가변 상태로 남는 것을 방지한다.
        if not isinstance(self.by_role, MappingProxyType):
            object.__setattr__(self, "by_role", MappingProxyType(dict(self.by_role)))

    @property
    def coverage_pct(self) -> float:
        """전체 요건 충족 비율 (%)."""
        return 100.0 * self.implemented / self.total if self.total else 0.0

    @property
    def required_coverage_pct(self) -> float:
        """FAA UTM 핵심(필수) 요건 충족 비율 (%)."""
        if not self.required_total:
            return 0.0
        return 100.0 * self.required_implemented / self.required_total

    @property
    def is_required_complete(self) -> bool:
        """핵심 요건 전부 충족 여부. 핵심 요건이 0건이면 False(공허참 방지)."""
        if not self.required_total:
            return False
        return self.required_implemented == self.required_total


def find_capability(capability_id: str) -> FaaUtmCapability:
    """식별자로 능력을 조회한다. 없으면 KeyError."""
    for cap in FAA_UTM_CAPABILITIES:
        if cap.capability_id == capability_id:
            return cap
    raise KeyError(f"unknown FAA UTM capability: {capability_id!r}")


def capabilities_by_role(role: str) -> tuple[FaaUtmCapability, ...]:
    """역할(USS/FIMS/SDSP/OPERATOR)에 속한 능력을 식별자 정렬로 반환한다."""
    if role not in UTM_ROLES:
        raise ValueError(f"role must be one of {UTM_ROLES}, got {role!r}")
    return tuple(
        sorted((c for c in FAA_UTM_CAPABILITIES if c.role == role), key=lambda c: c.capability_id)
    )


def required_capabilities() -> tuple[FaaUtmCapability, ...]:
    """FAA UTM 핵심(필수) 요건을 식별자 정렬로 반환한다."""
    return tuple(
        sorted((c for c in FAA_UTM_CAPABILITIES if c.required), key=lambda c: c.capability_id)
    )


def gaps() -> tuple[FaaUtmCapability, ...]:
    """SDACS 대응 모듈이 없는(미충족) 요건을 식별자 정렬로 반환한다."""
    return tuple(
        sorted((c for c in FAA_UTM_CAPABILITIES if not c.is_implemented), key=lambda c: c.capability_id)
    )


def implemented_capabilities() -> tuple[FaaUtmCapability, ...]:
    """SDACS 대응 모듈이 있는 요건을 식별자 정렬로 반환한다."""
    return tuple(
        sorted((c for c in FAA_UTM_CAPABILITIES if c.is_implemented), key=lambda c: c.capability_id)
    )


def conformance_report() -> ConformanceReport:
    """전체 요건 충족 현황을 집계한 결정적 적합성 리포트를 생성한다."""
    total = len(FAA_UTM_CAPABILITIES)
    implemented = sum(1 for c in FAA_UTM_CAPABILITIES if c.is_implemented)
    required = [c for c in FAA_UTM_CAPABILITIES if c.required]
    required_impl = sum(1 for c in required if c.is_implemented)
    by_role: dict[str, tuple[int, int]] = {}
    for role in UTM_ROLES:
        members = [c for c in FAA_UTM_CAPABILITIES if c.role == role]
        by_role[role] = (sum(1 for c in members if c.is_implemented), len(members))
    return ConformanceReport(
        total=total,
        implemented=implemented,
        gaps=total - implemented,
        required_total=len(required),
        required_implemented=required_impl,
        by_role=MappingProxyType(by_role),
    )


def capability_matrix() -> tuple[dict[str, object], ...]:
    """도구 간 교환용 매핑 매트릭스를 (역할, 식별자) 정렬 행으로 반환한다."""
    ordered = sorted(
        FAA_UTM_CAPABILITIES, key=lambda c: (UTM_ROLES.index(c.role), c.capability_id)
    )
    return tuple(
        {
            "capability_id": c.capability_id,
            "name": c.name,
            "role": c.role,
            "required": c.required,
            "implemented": c.is_implemented,
            "conops_area": c.conops_area,
            "sdacs_module": c.sdacs_module,
        }
        for c in ordered
    )


def _format_matrix() -> str:
    lines = ["FAA UTM ConOps v2.0 USS 요건 ↔ SDACS 매핑 매트릭스", ""]
    for row in capability_matrix():
        mark = "✓" if row["implemented"] else "✗(갭)"
        req = "필수" if row["required"] else "보조"
        module = row["sdacs_module"] or "—"
        lines.append(f"[{row['role']:8}] {mark} {req} {row['name']}")
        lines.append(f"           ({row['conops_area']}) → {module}")
    return "\n".join(lines)


def _format_conformance() -> str:
    r = conformance_report()
    lines = [
        "FAA UTM ConOps v2.0 적합성 요약",
        "",
        f"전체 충족   : {r.implemented}/{r.total} ({r.coverage_pct:.0f}%)",
        f"핵심(필수)  : {r.required_implemented}/{r.required_total} "
        f"({r.required_coverage_pct:.0f}%) "
        f"{'— 완전 충족' if r.is_required_complete else '— 미완(갭 존재)'}",
        "",
        "역할별:",
    ]
    for role in UTM_ROLES:
        impl, tot = r.by_role[role]
        lines.append(f"  {role:8}: {impl}/{tot}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FAA UTM ConOps v2.0 정렬 (ODYSSEY Phase 402)")
    parser.add_argument("--matrix", action="store_true", help="전체 매핑 매트릭스 출력")
    parser.add_argument("--conformance", action="store_true", help="적합성 요약 출력")
    parser.add_argument("--role", choices=UTM_ROLES, help="역할별 능력 출력")
    parser.add_argument("--gaps", action="store_true", help="미충족(갭) 요건 출력")
    parser.add_argument("--required", action="store_true", help="FAA UTM 핵심 요건 출력")
    args = parser.parse_args(argv)

    if args.matrix:
        print(_format_matrix())
    elif args.conformance:
        print(_format_conformance())
    elif args.role:
        for cap in capabilities_by_role(args.role):
            print(f"{cap.capability_id}: {cap.name} — {cap.summary}")
    elif args.gaps:
        for cap in gaps():
            print(f"[{cap.role}] {cap.name}: {cap.summary}")
    elif args.required:
        for cap in required_capabilities():
            mark = "✓" if cap.is_implemented else "✗"
            print(f"{mark} {cap.name} → {cap.sdacs_module or '—'}")
    else:
        print(_format_conformance())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
