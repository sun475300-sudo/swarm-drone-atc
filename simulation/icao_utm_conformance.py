"""ODYSSEY Phase 407 — ICAO UTM Framework Ed.4 적합성 자가 평가.

SDACS 기능 ↔ ICAO UTM Framework(Edition 4, 2023) 의 운영자 여정(operator journey)
단계별 UTM 기능을 결정적으로 대응시키는 적합성 자가 평가 매트릭스다. ODYSSEY 국제
확장(EASA U-space·FAA UTM·K-UTM 동시 호환)에서 "SDACS 가 ICAO 가 제시한 *전형적
UTM 시스템* 의 핵심 역량을 어디까지 충족하는가" 를 객관적으로 답하기 위한 기준 모듈이다.
Phase 401(EASA U-space 매핑)의 자매편으로, 같은 기능 자산을 ICAO 의 축으로 재평가한다.

근거 (권위 있는 출처)
--------------------
- **ICAO UTM Framework, Edition 4** — *"Unmanned Aircraft Systems Traffic
  Management (UTM): A Common Framework with Core Principles for Global
  Harmonization"* (2023). 본 프레임워크는 전형적 UTM 시스템의 핵심 역량을 운영자
  여정 10단계로 제시한다(ICAO 공개 자료): **manage·register·plan·coordinate·
  authorise·monitor·inform·adapt·report·investigate**. 본 모듈은 이 10단계를
  분류 축(journey phase)으로 삼는다.

정직 공시 (CLAUDE.md)
--------------------
1. 본 모듈은 *기능적 자가 평가* 이며 ICAO 공식 적합성 인증이 아니다. 역량 목록의
   세분화는 SDACS 의 해석이다(프레임워크의 정확한 절 번호를 복제하지 않는다).
2. ``status`` 는 3값(``conformant``·``partial``·``gap``)으로, Phase 401 의 이진
   충족보다 정직하게 *부분 충족* 과 *미충족* 을 구분한다.
3. ``sdacs_module`` 은 역량을 *실제로* 제공하는 리포 내 모듈 경로다. ``status`` 가
   ``gap`` 이면 반드시 ``None`` 이고, 그 외(``conformant``/``partial``)면 반드시
   실재 모듈을 인용한다 — 모듈 없는 충족 주장을 구조적으로 금지한다(테스트가 디스크
   실재를 강제). 본 모듈의 가치는 충족 주장보다 *미충족 항목의 가시화* 에 있다.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/icao_utm_conformance.py --matrix      # 전체 적합성 매트릭스
    python simulation/icao_utm_conformance.py --report      # 적합성 요약
    python simulation/icao_utm_conformance.py --phase plan  # 단계별 역량
    python simulation/icao_utm_conformance.py --gaps         # 미충족(갭) 역량
    python simulation/icao_utm_conformance.py --core         # 핵심 원칙 역량
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

# ICAO UTM Framework Ed.4 운영자 여정 단계 (분류 축, 프레임워크 제시 순서).
JOURNEY_PHASES: tuple[str, ...] = (
    "manage",
    "register",
    "plan",
    "coordinate",
    "authorise",
    "monitor",
    "inform",
    "adapt",
    "report",
    "investigate",
)

_PHASE_NAMES: dict[str, str] = {
    "manage": "Manage (공역 권한·책임·UTM 거버넌스)",
    "register": "Register (등록·식별)",
    "plan": "Plan (비행 계획·전략적 디컨플릭션)",
    "coordinate": "Coordinate (USS 간·ATM/ATC 조율)",
    "authorise": "Authorise (비행 승인)",
    "monitor": "Monitor (추적·감시·적합성·전술 회피)",
    "inform": "Inform (항공 정보·기상·지오 인지)",
    "adapt": "Adapt (동적 용량·우발 대응)",
    "report": "Report (비행 보고)",
    "investigate": "Investigate (사고·준사고 조사)",
}

# 적합성 상태 (3값). conformant=완전, partial=부분, gap=미충족.
CONFORMANCE_STATUSES: tuple[str, ...] = ("conformant", "partial", "gap")

# 가중 점수: 완전 1.0, 부분 0.5, 미충족 0.0.
_STATUS_WEIGHT: dict[str, float] = {"conformant": 1.0, "partial": 0.5, "gap": 0.0}


@dataclass(frozen=True)
class UTMCapability:
    """단일 ICAO UTM 역량과 SDACS 대응의 정의."""

    capability_id: str          # 안정 식별자 (예: 'remote_identification')
    name: str                   # 역량 명칭
    journey_phase: str          # 운영자 여정 단계
    core_principle: bool        # ICAO 핵심 역량(전형적 UTM 필수) 여부
    status: str                 # conformant·partial·gap
    sdacs_module: str | None    # 제공 모듈 경로 (gap 이면 None)
    summary: str                # 한 줄 설명

    def __post_init__(self) -> None:
        if not self.capability_id or self.capability_id != self.capability_id.strip():
            raise ValueError("capability_id must be non-empty and unpadded")
        if " " in self.capability_id:
            raise ValueError("capability_id must not contain internal spaces (snake_case)")
        if not self.name or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        if not self.summary or not self.summary.strip():
            raise ValueError("summary must be a non-empty string")
        if self.journey_phase not in JOURNEY_PHASES:
            raise ValueError(
                f"journey_phase must be one of {JOURNEY_PHASES}, got {self.journey_phase!r}"
            )
        if not isinstance(self.core_principle, bool):
            raise TypeError(
                f"core_principle must be bool, got {type(self.core_principle).__name__}"
            )
        if self.status not in CONFORMANCE_STATUSES:
            raise ValueError(
                f"status must be one of {CONFORMANCE_STATUSES}, got {self.status!r}"
            )
        # 정직성 결속: gap ⟺ 모듈 없음. 충족/부분은 반드시 실재 모듈 인용.
        if self.status == "gap":
            if self.sdacs_module is not None:
                raise ValueError("a gap capability must not cite an sdacs_module")
        else:
            if self.sdacs_module is None or not self.sdacs_module.strip():
                raise ValueError(
                    f"status {self.status!r} must cite a non-empty sdacs_module"
                )

    @property
    def is_gap(self) -> bool:
        """미충족(갭) 여부."""
        return self.status == "gap"

    @property
    def weight(self) -> float:
        """가중 점수 기여 (conformant 1.0·partial 0.5·gap 0.0)."""
        return _STATUS_WEIGHT[self.status]


# ICAO UTM 역량 카탈로그 ↔ SDACS 모듈 매핑 (정본).
# sdacs_module 경로는 리포에 실재하는 모듈 — 미대응(gap)은 None.
UTM_CAPABILITIES: tuple[UTMCapability, ...] = (
    # --- manage --------------------------------------------------------------
    UTMCapability(
        "airspace_management", "Airspace management authority", "manage", True,
        "conformant", "src/airspace_control/controller/airspace_controller.py",
        "공역 관제 권한·책임 — AirspaceController 1Hz 중앙 관제",
    ),
    UTMCapability(
        "uss_role_management", "USS role / federation management", "manage", False,
        "partial", "simulation/federation_discovery.py",
        "USS 역할·연합 관리 — 인스턴스 디스커버리(ASTM F3548 DSS 유사), 완전 거버넌스는 부분",
    ),
    # --- register ------------------------------------------------------------
    UTMCapability(
        "remote_identification", "Remote identification", "register", True,
        "conformant", "simulation/remote_id.py",
        "원격 식별(ASTM F3411 Remote ID) — 실시간 식별·위치 방송",
    ),
    UTMCapability(
        "e_registration", "Electronic registration", "register", True,
        "gap", None,
        "전자 등록 레지스트리 DB — 식별만 제공, 등록 원장 모듈 없음 (갭)",
    ),
    # --- plan ----------------------------------------------------------------
    UTMCapability(
        "flight_planning", "Flight planning (4D)", "plan", True,
        "conformant", "simulation/path_deconflict.py",
        "4D 비행 계획 — 시공간 경로 생성·CBS 다중 에이전트 계획",
    ),
    UTMCapability(
        "strategic_deconfliction", "Strategic deconfliction", "plan", True,
        "conformant", "simulation/path_deconflict.py",
        "전략적(사전) 충돌 해소 — 4D 경로 디컨플릭션",
    ),
    UTMCapability(
        "operational_intent_sharing", "Operational intent sharing", "plan", False,
        "conformant", "simulation/operational_intent.py",
        "운영 의도 4D 교환(ASTM F3548-21 정렬) — 연합 인스턴스 간 공유",
    ),
    # --- coordinate ----------------------------------------------------------
    UTMCapability(
        "inter_uss_coordination", "Inter-USS coordination", "coordinate", False,
        "partial", "simulation/federation_discovery.py",
        "USS 간 조율 — 디스커버리·핸드오버 모델, 운영 합의 일부",
    ),
    UTMCapability(
        "atm_atc_coordination", "ATM/ATC coordination", "coordinate", True,
        "partial", "simulation/kutm_protocol.py",
        "유인 ATM/ATC 조율 — K-UTM 프로토콜 연계, 완전 ATC 통합은 부분",
    ),
    # --- authorise -----------------------------------------------------------
    UTMCapability(
        "flight_authorisation", "Flight authorisation", "authorise", True,
        "conformant", "src/airspace_control/controller/airspace_controller.py",
        "비행 승인(clearance) 발급 — AirspaceController 관제",
    ),
    UTMCapability(
        "airspace_classification", "Airspace classification", "authorise", False,
        "conformant", "simulation/airspace_class.py",
        "ICAO 공역 클래스(A-G) 산정 — 고도 레이어 매핑",
    ),
    # --- monitor -------------------------------------------------------------
    UTMCapability(
        "tracking_surveillance", "Tracking and surveillance", "monitor", True,
        "conformant", "simulation/telemetry_recorder.py",
        "추적·감시 — 텔레메트리 기록·재생",
    ),
    UTMCapability(
        "cooperative_surveillance", "Cooperative surveillance (ADS-B)", "monitor", False,
        "conformant", "simulation/adsb_receiver.py",
        "협조 감시 — ADS-B 수신 데이터 통합",
    ),
    UTMCapability(
        "conformance_monitoring", "Conformance monitoring", "monitor", True,
        "conformant", "simulation/compliance_checker.py",
        "적합성 감시 — 계획 대비 이탈·규정 위반 탐지",
    ),
    UTMCapability(
        "tactical_deconfliction", "Tactical deconfliction (DAA)", "monitor", True,
        "conformant", "simulation/path_deconflict.py",
        "전술적(실시간) 충돌 회피 — APF + CPA 90초 예측",
    ),
    UTMCapability(
        "traffic_information", "Traffic information", "monitor", True,
        "conformant", "simulation/traffic_coordinator.py",
        "교통 정보 제공 — 인접 드론·항적 공유",
    ),
    # --- inform --------------------------------------------------------------
    UTMCapability(
        "aeronautical_information", "Aeronautical information management", "inform", True,
        "conformant", "simulation/notam_manager.py",
        "항공 정보(NOTAM) 관리 — 동적 NFZ 공지",
    ),
    UTMCapability(
        "weather_information", "Weather information", "inform", False,
        "conformant", "simulation/weather.py",
        "기상 정보 — 풍속장·APF 강풍 모드 연동",
    ),
    UTMCapability(
        "geo_awareness", "Geo-awareness", "inform", True,
        "conformant", "simulation/geofence_manager.py",
        "지오 인지 — 지오펜스·운용 제한구역(NFZ) 경계 인지",
    ),
    # --- adapt ---------------------------------------------------------------
    UTMCapability(
        "dynamic_capacity_management", "Dynamic capacity management", "adapt", False,
        "conformant", "simulation/airspace_capacity.py",
        "동적 용량 관리 — 공역 혼잡도 기반 수용량 산정",
    ),
    UTMCapability(
        "contingency_management", "Contingency management", "adapt", True,
        "conformant", "simulation/emergency_protocol.py",
        "우발 대응 — RTB·안전 강하·비상 프로토콜",
    ),
    # --- report --------------------------------------------------------------
    UTMCapability(
        "flight_reporting", "Flight reporting", "report", False,
        "partial", "simulation/flight_following.py",
        "비행 보고 — 추적 서비스 기록, 표준 보고 양식 자동화는 부분",
    ),
    # --- investigate ---------------------------------------------------------
    UTMCapability(
        "incident_investigation", "Incident investigation workflow", "investigate", False,
        "gap", None,
        "사고·준사고 조사 워크플로 런타임 모듈 — Phase 467 표준 양식은 문서 수준 (갭)",
    ),
)


# 로드 시점 무결성 게이트 — 중복 식별자를 임포트 시 즉시 차단(테스트보다 이른 단계).
_CATALOG_IDS = [c.capability_id for c in UTM_CAPABILITIES]
assert len(_CATALOG_IDS) == len(set(_CATALOG_IDS)), "duplicate capability_id in UTM_CAPABILITIES"


@dataclass(frozen=True)
class ConformanceReport:
    """ICAO UTM 적합성 자가 평가 요약."""

    total: int
    conformant: int
    partial: int
    gap: int
    core_total: int
    core_conformant: int
    by_phase: Mapping[str, tuple[int, int, int]]  # phase -> (conformant, partial, gap), read-only

    def __post_init__(self) -> None:
        # by_phase 를 항상 읽기 전용 뷰로 동결 — 직접 생성 시에도 내부 변형 차단.
        if not isinstance(self.by_phase, MappingProxyType):
            object.__setattr__(self, "by_phase", MappingProxyType(dict(self.by_phase)))
        if min(self.total, self.conformant, self.partial, self.gap,
               self.core_total, self.core_conformant) < 0:
            raise ValueError("counts must be non-negative")
        if self.conformant + self.partial + self.gap != self.total:
            raise ValueError(
                f"conformant ({self.conformant}) + partial ({self.partial}) + "
                f"gap ({self.gap}) != total ({self.total})"
            )
        if self.core_conformant > self.core_total:
            raise ValueError("core_conformant cannot exceed core_total")
        if self.core_total > self.total:
            raise ValueError("core_total cannot exceed total")
        # by_phase 가 주어졌으면 단계별 합이 집계 총계와 일치해야 한다.
        if self.by_phase:
            c = sum(v[0] for v in self.by_phase.values())
            p = sum(v[1] for v in self.by_phase.values())
            g = sum(v[2] for v in self.by_phase.values())
            if (c, p, g) != (self.conformant, self.partial, self.gap):
                raise ValueError(
                    f"by_phase sums ({c},{p},{g}) != "
                    f"({self.conformant},{self.partial},{self.gap})"
                )

    @property
    def weighted_score_pct(self) -> float:
        """가중 적합성 점수 (%) — conformant 1.0·partial 0.5·gap 0.0."""
        if not self.total:
            return 0.0
        score = self.conformant * 1.0 + self.partial * 0.5
        return 100.0 * score / self.total

    @property
    def core_conformant_pct(self) -> float:
        """핵심 역량 완전 충족 비율 (%)."""
        if not self.core_total:
            return 0.0
        return 100.0 * self.core_conformant / self.core_total

    @property
    def has_core_incomplete(self) -> bool:
        """핵심 역량 중 미완전(부분·미충족) 항목이 있으면 True.

        이름 그대로 *완전 충족이 아닌* 핵심 역량(부분·갭 모두)을 가리킨다 — 갭만이
        아니다. 핵심 ``partial`` 항목 1건만 있어도 True.
        """
        if not self.core_total:
            return False
        return self.core_conformant < self.core_total


def find_capability(capability_id: str) -> UTMCapability:
    """식별자로 역량을 조회한다. 없으면 KeyError."""
    for cap in UTM_CAPABILITIES:
        if cap.capability_id == capability_id:
            return cap
    raise KeyError(f"unknown UTM capability: {capability_id!r}")


def capabilities_by_phase(phase: str) -> tuple[UTMCapability, ...]:
    """운영자 여정 단계에 속한 역량을 식별자 정렬로 반환한다."""
    if phase not in JOURNEY_PHASES:
        raise ValueError(f"phase must be one of {JOURNEY_PHASES}, got {phase!r}")
    return tuple(
        sorted((c for c in UTM_CAPABILITIES if c.journey_phase == phase),
               key=lambda c: c.capability_id)
    )


def core_principles() -> tuple[UTMCapability, ...]:
    """ICAO 핵심 역량(core_principle=True)을 식별자 정렬로 반환한다."""
    return tuple(
        sorted((c for c in UTM_CAPABILITIES if c.core_principle),
               key=lambda c: c.capability_id)
    )


def gaps() -> tuple[UTMCapability, ...]:
    """미충족(gap) 역량을 식별자 정렬로 반환한다."""
    return tuple(
        sorted((c for c in UTM_CAPABILITIES if c.is_gap), key=lambda c: c.capability_id)
    )


def capabilities_by_status(status: str) -> tuple[UTMCapability, ...]:
    """적합성 상태별 역량을 식별자 정렬로 반환한다."""
    if status not in CONFORMANCE_STATUSES:
        raise ValueError(f"status must be one of {CONFORMANCE_STATUSES}, got {status!r}")
    return tuple(
        sorted((c for c in UTM_CAPABILITIES if c.status == status),
               key=lambda c: c.capability_id)
    )


def conformance_report() -> ConformanceReport:
    """전체 적합성 현황을 집계한 결정적 리포트를 생성한다."""
    total = len(UTM_CAPABILITIES)
    conformant = sum(1 for c in UTM_CAPABILITIES if c.status == "conformant")
    partial = sum(1 for c in UTM_CAPABILITIES if c.status == "partial")
    gap = sum(1 for c in UTM_CAPABILITIES if c.status == "gap")
    core = [c for c in UTM_CAPABILITIES if c.core_principle]
    core_conformant = sum(1 for c in core if c.status == "conformant")
    by_phase: dict[str, tuple[int, int, int]] = {}
    for phase in JOURNEY_PHASES:
        members = [c for c in UTM_CAPABILITIES if c.journey_phase == phase]
        by_phase[phase] = (
            sum(1 for c in members if c.status == "conformant"),
            sum(1 for c in members if c.status == "partial"),
            sum(1 for c in members if c.status == "gap"),
        )
    return ConformanceReport(
        total=total,
        conformant=conformant,
        partial=partial,
        gap=gap,
        core_total=len(core),
        core_conformant=core_conformant,
        by_phase=MappingProxyType(by_phase),
    )


def conformance_matrix() -> tuple[dict[str, object], ...]:
    """도구 간 교환용 적합성 매트릭스를 (단계, 식별자) 정렬 행으로 반환한다."""
    ordered = sorted(
        UTM_CAPABILITIES,
        key=lambda c: (JOURNEY_PHASES.index(c.journey_phase), c.capability_id),
    )
    return tuple(
        {
            "capability_id": c.capability_id,
            "name": c.name,
            "journey_phase": c.journey_phase,
            "core_principle": c.core_principle,
            "status": c.status,
            "sdacs_module": c.sdacs_module,
        }
        for c in ordered
    )


_STATUS_MARK: dict[str, str] = {"conformant": "✓", "partial": "◐", "gap": "✗(갭)"}


def _format_matrix() -> str:
    lines = ["ICAO UTM Framework Ed.4 적합성 매트릭스", ""]
    for row in conformance_matrix():
        mark = _STATUS_MARK[str(row["status"])]
        core = "핵심" if row["core_principle"] else "권장"
        module = row["sdacs_module"] or "—"
        lines.append(f"[{row['journey_phase']:11}] {mark:5} {core} {row['name']}")
        lines.append(f"      → {module}")
    return "\n".join(lines)


def _format_report() -> str:
    r = conformance_report()
    lines = [
        "ICAO UTM 적합성 자가 평가 요약",
        "",
        f"가중 점수   : {r.weighted_score_pct:.0f}% "
        f"(충족 {r.conformant} · 부분 {r.partial} · 갭 {r.gap} / 총 {r.total})",
        f"핵심 역량   : {r.core_conformant}/{r.core_total} 완전 충족 "
        f"({r.core_conformant_pct:.0f}%) "
        f"{'— 핵심 미완전 있음' if r.has_core_incomplete else '— 핵심 전부 충족'}",
        "",
        "여정 단계별 (충족/부분/갭):",
    ]
    for phase in JOURNEY_PHASES:
        c, p, g = r.by_phase[phase]
        lines.append(f"  {phase:11}: {c}/{p}/{g}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ICAO UTM Framework Ed.4 적합성 자가 평가 (ODYSSEY Phase 407)"
    )
    parser.add_argument("--matrix", action="store_true", help="전체 적합성 매트릭스 출력")
    parser.add_argument("--report", action="store_true", help="적합성 요약 출력")
    parser.add_argument("--phase", choices=JOURNEY_PHASES, help="여정 단계별 역량 출력")
    parser.add_argument("--gaps", action="store_true", help="미충족(갭) 역량 출력")
    parser.add_argument("--core", action="store_true", help="핵심 원칙 역량 출력")
    args = parser.parse_args(argv)

    if args.matrix:
        print(_format_matrix())
    elif args.report:
        print(_format_report())
    elif args.phase:
        for cap in capabilities_by_phase(args.phase):
            print(f"{cap.capability_id} [{cap.status}]: {cap.name} — {cap.summary}")
    elif args.gaps:
        for cap in gaps():
            print(f"[{cap.journey_phase}] {cap.name}: {cap.summary}")
    elif args.core:
        for cap in core_principles():
            print(f"{_STATUS_MARK[cap.status]} {cap.name} → {cap.sdacs_module or '—'}")
    else:
        print(_format_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
