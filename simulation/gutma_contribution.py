"""ODYSSEY Phase 410 — GUTMA 회원 활동 시나리오(글로벌 UTM 커뮤니티 기고).

SDACS 기능을 GUTMA(Global UTM Association) 의 공개 기술 작업물(Flight Declaration
Protocol·USS 상호운용·GeoJSON 공역 표현 등)에 결정적으로 대응시켜, "SDACS 가
GUTMA 회원으로서 *어떤 작업 항목에 무엇으로 기여할 수 있는가*" 를 객관적으로
답하는 기고 적합성 매트릭스다. Phase 401(EASA U-space 매핑)·407(ICAO UTM 적합성)
의 자매편 — 같은 기능 자산을 GUTMA 산업 컨소시엄의 축으로 재평가한다.

근거 (권위 있는 공개 출처)
------------------------
- **GUTMA Flight Declaration Protocol** — USS 간 비행 선언(operation plan) 교환을
  위한 공개 사양(GitHub ``gutma/flight_declaration_protocol``).
- **GUTMA USS Interoperability / Discovery & Synchronization** — USS-to-USS 발견·
  동기화(ASTM F3548-21 DSS 개념 정렬).
- **GUTMA GeoJSON 기반 공역/UAS Volume 표현** — 공통 데이터 사전(Data Common
  Dictionary)과 GeoJSON 공역 직렬화.
- **Network Remote ID** — ASTM F3411 네트워크 원격 식별 연계.

정직 공시 (CLAUDE.md)
--------------------
``sdacs_module`` 은 해당 작업 항목에 *실제로* 참조 구현으로 기여 가능한 리포 내
모듈 경로다. 대응 모듈이 없는 항목(예: 호스팅형 DSS 발견 서비스 운영)은 ``None``
으로 **갭(gap)** 임을 정직히 표면화한다. 정직성 결속: ``status == "gap"`` ⟺
``sdacs_module is None`` 이며, ``ready``·``partial`` 은 반드시 디스크에 실재하는
모듈을 인용한다(``__post_init__`` 강제 + 테스트가 인용 경로 실재 강제). 본 매핑은
기능적 기여 가능성 평가이며 GUTMA 공식 채택이 아니다.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/gutma_contribution.py --matrix      # 전체 기고 매트릭스
    python simulation/gutma_contribution.py --report      # 기고 준비도 요약
    python simulation/gutma_contribution.py --group FDP   # 작업그룹별 항목
    python simulation/gutma_contribution.py --gaps        # 미대응(갭) 항목
    python simulation/gutma_contribution.py --groups      # 작업그룹 목록
"""
from __future__ import annotations

import argparse
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

# 리포 루트 — 인용 모듈 경로는 이 기준의 상대 경로다.
_REPO_ROOT = Path(__file__).resolve().parent.parent

# GUTMA 기술 작업그룹(working group) — 안정 코드 ↔ 설명.
WORKING_GROUPS: Mapping[str, str] = MappingProxyType(
    {
        "FDP": "Flight Declaration Protocol (비행 선언 교환)",
        "USSI": "USS Interoperability & Discovery (USS 상호운용·발견)",
        "DATA": "Data Common Dictionary & GeoJSON (공통 데이터·공역 표현)",
        "NRID": "Network Remote ID (네트워크 원격 식별)",
        "SURV": "Surveillance Data Exchange (감시 데이터 교환)",
    }
)

# 기고 준비도 상태(정직성 3값).
#   ready   — 참조 구현으로 즉시 기여 가능한 모듈 보유
#   partial — 관련 모듈은 있으나 사양 일부만 충족(추가 작업 필요)
#   gap     — 대응 모듈 없음(기여 불가, 정직 표면화)
CONTRIBUTION_STATUSES: tuple[str, ...] = ("ready", "partial", "gap")

# 상태별 가중치(준비도 점수 산정).
_STATUS_WEIGHT: Mapping[str, float] = MappingProxyType(
    {"ready": 1.0, "partial": 0.5, "gap": 0.0}
)


@dataclass(frozen=True)
class GutmaWorkItem:
    """단일 GUTMA 작업 항목과 SDACS 기고 가능성의 정의(불변)."""

    item_id: str          # 안정 식별자 (예: 'flight_declaration')
    name: str             # 작업 항목 명칭
    group: str            # 작업그룹 코드 (WORKING_GROUPS 키)
    status: str           # 기고 준비도 (CONTRIBUTION_STATUSES)
    spec_ref: str         # 권위 있는 GUTMA 사양/문서 인용
    sdacs_module: str | None  # 참조 구현 모듈 경로 (gap 이면 None)
    summary: str          # 한 줄 설명

    def __post_init__(self) -> None:
        if not self.item_id or self.item_id != self.item_id.strip():
            raise ValueError("item_id must be non-empty and unpadded")
        # 내부 탭·개행 등 모든 공백 문자를 거부(strip 은 양끝만, ' ' 검사는 ASCII 만).
        if re.search(r"\s", self.item_id):
            raise ValueError(f"item_id must not contain whitespace: {self.item_id!r}")
        if not self.name or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        if not self.summary or not self.summary.strip():
            raise ValueError("summary must be a non-empty string")
        if not self.spec_ref or not self.spec_ref.strip():
            raise ValueError("spec_ref must be a non-empty citation")
        if self.group not in WORKING_GROUPS:
            raise ValueError(
                f"group must be one of {tuple(WORKING_GROUPS)}, got {self.group!r}"
            )
        if self.status not in CONTRIBUTION_STATUSES:
            raise ValueError(
                f"status must be one of {CONTRIBUTION_STATUSES}, got {self.status!r}"
            )
        # 정직성 결속: gap ⟺ 모듈 없음. ready/partial 은 모듈 인용 필수.
        if self.status == "gap":
            if self.sdacs_module is not None:
                raise ValueError("gap status must have sdacs_module=None")
        else:
            if self.sdacs_module is None or not self.sdacs_module.strip():
                raise ValueError(
                    f"status {self.status!r} must cite a non-empty sdacs_module"
                )

    @property
    def can_contribute(self) -> bool:
        """SDACS 가 (전부 또는 일부) 기여 가능하면 True (갭이 아니면 True)."""
        return self.status != "gap"

    @property
    def weight(self) -> float:
        """기고 준비도 가중치 (ready 1.0·partial 0.5·gap 0.0)."""
        return _STATUS_WEIGHT[self.status]


# GUTMA 작업 항목 카탈로그 ↔ SDACS 기고 매핑 (정본).
# sdacs_module 경로는 리포에 실재하는 모듈 — 미대응은 None(갭, status='gap').
GUTMA_WORK_ITEMS: tuple[GutmaWorkItem, ...] = (
    GutmaWorkItem(
        "flight_declaration", "Flight Declaration Protocol", "FDP", "ready",
        "GUTMA Flight Declaration Protocol (gutma/flight_declaration_protocol)",
        "simulation/flight_plan_filing.py",
        "비행 선언(operation plan) 제출·교환 — 4D 경로·시간창 직렬화",
    ),
    GutmaWorkItem(
        "operation_plan_share", "Operation Plan Sharing", "FDP", "ready",
        "GUTMA FDP §operation_plan + ASTM F3548-21 운영 의도",
        "simulation/operational_intent.py",
        "운영 의도(operational intent) 4D 볼륨 공유 — 전략적 디컨플릭션 근거",
    ),
    GutmaWorkItem(
        "uss_interoperability", "USS-to-USS Interoperability", "USSI", "partial",
        "GUTMA USS Interoperability (ASTM F3548-21 DSS 개념 정렬)",
        "simulation/federation_conflict_resolution.py",
        "USS 간 충돌 해소 협조 — 인접 공역 연합 운영(호스팅 DSS 미운영, 일부)",
    ),
    GutmaWorkItem(
        "discovery_synchronization", "Discovery & Synchronization Service", "USSI", "gap",
        "GUTMA Discovery & Synchronization Service (호스팅형 DSS)",
        None,
        "호스팅형 DSS 발견·동기화 서비스 운영 — 단일 인스턴스 범위 밖 (갭)",
    ),
    GutmaWorkItem(
        "geojson_airspace", "GeoJSON Airspace Representation", "DATA", "ready",
        "GUTMA Data Common Dictionary + GeoJSON 공역/UAS Volume",
        "simulation/geo_zones.py",
        "공역·제한구역 GeoJSON 직렬화 — 운용 볼륨 경계 표현",
    ),
    GutmaWorkItem(
        "geofence_data", "Geo-awareness Data Exchange", "DATA", "ready",
        "GUTMA geo-awareness 데이터(ED-269 정렬)",
        "simulation/geofence_manager.py",
        "지오펜스·동적 NFZ 데이터 — 경계 인지 정보 교환",
    ),
    GutmaWorkItem(
        "network_remote_id", "Network Remote ID", "NRID", "ready",
        "GUTMA Network Remote ID (ASTM F3411 연계)",
        "simulation/remote_id.py",
        "네트워크 원격 식별 — 드론 실시간 식별·위치 방송",
    ),
    GutmaWorkItem(
        "surveillance_exchange", "Surveillance Data Exchange", "SURV", "partial",
        "GUTMA Surveillance Data Exchange (텔레메트리 스키마)",
        "simulation/telemetry_validator.py",
        "감시(텔레메트리) 데이터 검증·교환 — 표준 스키마 일부 충족",
    ),
    GutmaWorkItem(
        # 런타임 적합성 감시 — 계획 단계 디컨플릭션(path_deconflict)이 아니라
        # 비행 중 운영 볼륨 대비 적합성을 검사하는 compliance_checker 가 정확한 대응.
        "conformance_monitoring", "Conformance Monitoring Feedback", "SURV", "ready",
        "GUTMA conformance monitoring (운영 의도 대비 적합성)",
        "simulation/compliance_checker.py",
        "비행 중 운영 볼륨 대비 적합성 감시 — 분리 위반·이탈 탐지 피드백",
    ),
)


@dataclass(frozen=True)
class ContributionReport:
    """GUTMA 기고 준비도 요약(불변)."""

    total: int
    ready: int
    partial: int
    gaps: int
    score: float                              # 가중 준비도 (0.0~1.0)
    by_group: Mapping[str, tuple[int, int]]   # group -> (기여가능, 총), read-only

    def __post_init__(self) -> None:
        if min(self.total, self.ready, self.partial, self.gaps) < 0:
            raise ValueError("counts must be non-negative")
        if self.ready + self.partial + self.gaps != self.total:
            raise ValueError(
                f"ready ({self.ready}) + partial ({self.partial}) + gaps "
                f"({self.gaps}) != total ({self.total})"
            )
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0,1], got {self.score}")
        # by_group 합이 총계와 일치해야 한다(교차검증).
        group_total = sum(tot for _impl, tot in self.by_group.values())
        if group_total != self.total:
            raise ValueError(
                f"by_group total ({group_total}) != total ({self.total})"
            )
        # 그룹별 기여가능 수는 그룹 총계를 초과할 수 없다(0 ≤ impl ≤ tot).
        for group, (impl, tot) in self.by_group.items():
            if not 0 <= impl <= tot:
                raise ValueError(
                    f"by_group[{group!r}] contributable ({impl}) must be in [0, {tot}]"
                )

    @property
    def score_pct(self) -> float:
        """가중 준비도 백분율 (%)."""
        return 100.0 * self.score

    @property
    def contributable(self) -> int:
        """기여 가능(갭 아님) 항목 수 = ready + partial."""
        return self.ready + self.partial


def find_work_item(item_id: str) -> GutmaWorkItem:
    """식별자로 작업 항목을 조회한다. 없으면 KeyError."""
    for item in GUTMA_WORK_ITEMS:
        if item.item_id == item_id:
            return item
    raise KeyError(f"unknown GUTMA work item: {item_id!r}")


def items_by_group(group: str) -> tuple[GutmaWorkItem, ...]:
    """작업그룹에 속한 항목을 식별자 정렬로 반환한다."""
    if group not in WORKING_GROUPS:
        raise ValueError(
            f"group must be one of {tuple(WORKING_GROUPS)}, got {group!r}"
        )
    return tuple(
        sorted((i for i in GUTMA_WORK_ITEMS if i.group == group), key=lambda i: i.item_id)
    )


def items_by_status(status: str) -> tuple[GutmaWorkItem, ...]:
    """상태별 항목을 식별자 정렬로 반환한다."""
    if status not in CONTRIBUTION_STATUSES:
        raise ValueError(
            f"status must be one of {CONTRIBUTION_STATUSES}, got {status!r}"
        )
    return tuple(
        sorted((i for i in GUTMA_WORK_ITEMS if i.status == status), key=lambda i: i.item_id)
    )


def gaps() -> tuple[GutmaWorkItem, ...]:
    """SDACS 대응 모듈이 없는(미대응) 항목을 식별자 정렬로 반환한다."""
    return items_by_status("gap")


def contribution_report() -> ContributionReport:
    """전체 기고 준비도를 집계한 결정적 리포트를 생성한다."""
    total = len(GUTMA_WORK_ITEMS)
    ready = sum(1 for i in GUTMA_WORK_ITEMS if i.status == "ready")
    partial = sum(1 for i in GUTMA_WORK_ITEMS if i.status == "partial")
    gap_count = sum(1 for i in GUTMA_WORK_ITEMS if i.status == "gap")
    score = (sum(i.weight for i in GUTMA_WORK_ITEMS) / total) if total else 0.0
    by_group: dict[str, tuple[int, int]] = {}
    for group in WORKING_GROUPS:
        members = [i for i in GUTMA_WORK_ITEMS if i.group == group]
        by_group[group] = (sum(1 for i in members if i.can_contribute), len(members))
    return ContributionReport(
        total=total,
        ready=ready,
        partial=partial,
        gaps=gap_count,
        score=score,
        by_group=MappingProxyType(by_group),
    )


def contribution_matrix() -> tuple[Mapping[str, object], ...]:
    """도구 간 교환용 기고 매트릭스를 (그룹, 식별자) 정렬 행으로 반환한다.

    각 행은 ``MappingProxyType`` 읽기 전용 매핑이다(모듈 전반의 불변 규율과 일치).
    """
    group_order = list(WORKING_GROUPS)
    ordered = sorted(
        GUTMA_WORK_ITEMS, key=lambda i: (group_order.index(i.group), i.item_id)
    )
    return tuple(
        MappingProxyType(
            {
                "item_id": i.item_id,
                "name": i.name,
                "group": i.group,
                "status": i.status,
                "can_contribute": i.can_contribute,
                "spec_ref": i.spec_ref,
                "sdacs_module": i.sdacs_module,
            }
        )
        for i in ordered
    )


def _format_matrix() -> str:
    marks = {"ready": "✓", "partial": "~", "gap": "✗"}
    lines = ["GUTMA 작업 항목 ↔ SDACS 기고 매트릭스", ""]
    for row in contribution_matrix():
        mark = marks[str(row["status"])]
        module = row["sdacs_module"] or "—"
        lines.append(f"[{row['group']:4}] {mark} {row['name']} ({row['status']})")
        lines.append(f"        → {module}")
    return "\n".join(lines)


def _format_report() -> str:
    r = contribution_report()
    lines = [
        "GUTMA 기고 준비도 요약",
        "",
        f"전체 항목     : {r.total}",
        f"즉시 기여(ready): {r.ready}",
        f"부분(partial)  : {r.partial}",
        f"갭(gap)        : {r.gaps}",
        f"가중 준비도    : {r.score_pct:.0f}%",
        "",
        "작업그룹별 (기여가능/총):",
    ]
    for group, label in WORKING_GROUPS.items():
        impl, tot = r.by_group[group]
        # 라벨 앞부분만 표기 — 괄호 부재 시에도 안전하도록 길이 슬라이스.
        short = label.split(" (")[0][:38]
        lines.append(f"  {group:5} {short:38}: {impl}/{tot}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="GUTMA 회원 기고 적합성 매트릭스 (ODYSSEY Phase 410)"
    )
    parser.add_argument("--matrix", action="store_true", help="전체 기고 매트릭스 출력")
    parser.add_argument("--report", action="store_true", help="기고 준비도 요약 출력")
    parser.add_argument("--group", choices=tuple(WORKING_GROUPS), help="작업그룹별 항목 출력")
    parser.add_argument("--gaps", action="store_true", help="미대응(갭) 항목 출력")
    parser.add_argument("--groups", action="store_true", help="작업그룹 목록 출력")
    args = parser.parse_args(argv)

    if args.matrix:
        print(_format_matrix())
    elif args.report:
        print(_format_report())
    elif args.group:
        for item in items_by_group(args.group):
            print(f"{item.item_id}: {item.name} [{item.status}] — {item.summary}")
    elif args.gaps:
        for item in gaps():
            print(f"[{item.group}] {item.name}: {item.summary}")
    elif args.groups:
        for group, label in WORKING_GROUPS.items():
            print(f"{group}: {label}")
    else:
        print(_format_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
