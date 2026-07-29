"""ODYSSEY Phase 402 -- FAA UTM ConOps v2 USS 역할 요구사항 갭 분석.

FAA UTM(UAS Traffic Management) ConOps v2의 USS(UAS Service Supplier) 역할
요구사항을 SDACS 기능과 대조하여 충족·부분충족·갭을 결정적으로 분류한다.
ODYSSEY 국제 확장(EASA U-space·FAA UTM·K-UTM 동시 호환)에서 "SDACS가 FAA UTM
ConOps v2 USS 역할을 어디까지 수행할 수 있는가"를 객관적으로 답하기 위한 자가
평가 기준 모듈이다.

근거 (권위 있는 출처)
--------------------
- **FAA UTM ConOps v2** (2020): USS 역할 -- 등록, 비행 승인, 텔레메트리 보고,
  전략적 디컨플릭션, 적합성 감시, USS-USS 데이터 교환, 네트워크 참여.
- **ASTM F3548-21** (UAS Traffic Management -- UTM UAS Service Supplier
  Interoperability Specification): USS 상호운용 기술 요구사항.
- **14 CFR Part 107** / Part 89 (Remote ID): FAA 규정 프레임워크.

정직 공시 (CLAUDE.md)
--------------------
``sdacs_module`` 은 해당 요구사항을 *기능적으로* 대응하는 리포 내 모듈 경로다.
``compliance_level`` 이 "gap"인 항목은 대응 모듈이 없음을 정직히 표면화한다 --
본 모듈의 가치는 충족 주장보다 *미충족 항목의 가시화* 에 있다. 매핑은 기능적
대응이며 FAA 공식 인증이 아니다.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python -m simulation.faa_utm_gap --report       # 전체 갭 분석 리포트
    python -m simulation.faa_utm_gap --gaps         # 갭 항목만 출력
    python -m simulation.faa_utm_gap --json         # JSON 형식 출력
    python -m simulation.faa_utm_gap --category "Strategic Deconfliction"
"""
from __future__ import annotations

import argparse
import json
import types
from collections.abc import Mapping
from dataclasses import dataclass

# 유효한 compliance_level 값
COMPLIANCE_LEVELS: tuple[str, ...] = ("full", "partial", "gap", "not_applicable")

# USS 요구사항 카테고리
CATEGORIES: tuple[str, ...] = (
    "Registration",
    "Flight Authorization",
    "Telemetry",
    "Conflict Advisory",
    "Strategic Deconfliction",
    "Conformance Monitoring",
    "Data Exchange",
    "Network",
)


@dataclass(frozen=True)
class FAARequirement:
    """FAA UTM ConOps v2 USS 역할 개별 요구사항."""

    req_id: str
    category: str
    description: str
    conops_ref: str
    sdacs_module: str | None
    compliance_level: str
    notes: str

    def __post_init__(self) -> None:
        if not self.req_id or self.req_id != self.req_id.strip():
            raise ValueError("req_id must be non-empty and unpadded")
        if not self.category or not self.category.strip():
            raise ValueError("category must be a non-empty string")
        if not self.description or not self.description.strip():
            raise ValueError("description must be a non-empty string")
        if not self.conops_ref or not self.conops_ref.strip():
            raise ValueError("conops_ref must be a non-empty string")
        if self.compliance_level not in COMPLIANCE_LEVELS:
            raise ValueError(
                f"compliance_level must be one of {COMPLIANCE_LEVELS}, "
                f"got {self.compliance_level!r}"
            )
        if self.sdacs_module is not None and not self.sdacs_module.strip():
            raise ValueError("sdacs_module must be None or a non-empty path")
        if not self.notes or not self.notes.strip():
            raise ValueError("notes must be a non-empty string")


@dataclass(frozen=True)
class GapAnalysis:
    """FAA UTM USS 요구사항 갭 분석 집계."""

    total: int
    full: int
    partial: int
    gap: int
    not_applicable: int
    compliance_pct: float
    by_category: Mapping[str, dict[str, int]]

    def __post_init__(self) -> None:
        if self.full + self.partial + self.gap + self.not_applicable != self.total:
            raise ValueError(
                f"full ({self.full}) + partial ({self.partial}) + gap ({self.gap}) "
                f"+ not_applicable ({self.not_applicable}) != total ({self.total})"
            )
        if min(self.total, self.full, self.partial, self.gap, self.not_applicable) < 0:
            raise ValueError("counts must be non-negative")


class FAAUTMGapAnalyzer:
    """FAA UTM ConOps v2 USS 역할 요구사항 대 SDACS 갭 분석기."""

    REQUIREMENTS: tuple[FAARequirement, ...] = (
        # --- Registration (USS Registration & Discovery) ---
        FAARequirement(
            "USS-01", "Registration",
            "USS shall register with the FAA UTM ecosystem and maintain valid credentials",
            "ConOps v2 §3.1",
            "simulation/federation_discovery.py",
            "partial",
            "ASTM F3548 기반 서비스 디스커버리 구현 -- FAA 고유 등록 프로토콜 미대응",
        ),
        FAARequirement(
            "USS-02", "Registration",
            "USS shall support discovery by other USSs and FIMS",
            "ConOps v2 §3.1.2",
            "simulation/federation_discovery.py",
            "partial",
            "연합 디스커버리 메커니즘 존재 -- FIMS 인터페이스 미구현",
        ),
        FAARequirement(
            "USS-03", "Registration",
            "USS shall authenticate UAS operators and validate pilot credentials",
            "ConOps v2 §3.1.3",
            None,
            "gap",
            "UAS 운영자 인증 및 조종사 자격 검증 모듈 부재",
        ),
        # --- Flight Authorization ---
        FAARequirement(
            "USS-04", "Flight Authorization",
            "USS shall accept and process operational intent declarations from UAS operators",
            "ConOps v2 §4.1",
            "simulation/operational_intent.py",
            "full",
            "ASTM F3548 Operational Intent 선언 및 처리 완전 구현",
        ),
        FAARequirement(
            "USS-05", "Flight Authorization",
            "USS shall file flight plans and obtain necessary authorizations (LAANC)",
            "ConOps v2 §4.2",
            "simulation/flight_plan_filing.py",
            "partial",
            "비행 계획 제출 구현 -- LAANC 연동 미구현",
        ),
        FAARequirement(
            "USS-06", "Flight Authorization",
            "USS shall validate operational volumes against airspace constraints and TFRs",
            "ConOps v2 §4.2.3",
            "simulation/flight_plan_validator.py",
            "partial",
            "운용 공역 제약 검증 구현 -- TFR 실시간 수신 미구현",
        ),
        FAARequirement(
            "USS-07", "Flight Authorization",
            "USS shall enforce Part 107 waiver requirements for BVLOS and night operations",
            "ConOps v2 §4.3",
            "src/airspace_control/controller/airspace_controller.py",
            "partial",
            "비행 승인 및 관제 1Hz 존재 -- Part 107 waiver 기반 규정 검증 불완전",
        ),
        # --- Telemetry ---
        FAARequirement(
            "USS-08", "Telemetry",
            "USS shall receive and process real-time telemetry from UAS",
            "ConOps v2 §5.1",
            "simulation/ws_bridge.py",
            "full",
            "WebSocket 텔레메트리 브리지 -- 실시간 위치 및 상태 수신 완전 구현",
        ),
        FAARequirement(
            "USS-09", "Telemetry",
            "USS shall report UAS position to the UTM network at required intervals",
            "ConOps v2 §5.2",
            "simulation/telemetry_recorder.py",
            "full",
            "텔레메트리 레코더 -- 위치 보고 주기적 기록 및 전송 구현",
        ),
        FAARequirement(
            "USS-10", "Telemetry",
            "USS shall archive telemetry data for post-flight analysis and regulatory audit",
            "ConOps v2 §5.3",
            "src/storage/timescale.py",
            "full",
            "TimescaleDB 시계열 저장소 -- 감사 추적 및 사후 분석용 아카이브 구현",
        ),
        # --- Conflict Advisory ---
        FAARequirement(
            "USS-11", "Conflict Advisory",
            "USS shall detect potential conflicts between operations and issue advisories",
            "ConOps v2 §6.1",
            "simulation/federation_conflict_resolution.py",
            "full",
            "연합 충돌 해소 -- CPA 기반 잠재 충돌 탐지 및 경고 발행",
        ),
        FAARequirement(
            "USS-12", "Conflict Advisory",
            "USS shall provide real-time alerts to operators when proximity thresholds are breached",
            "ConOps v2 §6.2",
            "simulation/apf_engine/apf.py",
            "full",
            "APF 엔진 -- 실시간 근접 경고 및 회피 기동 생성",
        ),
        # --- Strategic Deconfliction ---
        FAARequirement(
            "USS-13", "Strategic Deconfliction",
            "USS shall perform strategic (pre-flight) deconfliction of operational intents",
            "ConOps v2 §6.3",
            "simulation/path_deconflict.py",
            "full",
            "4D 경로 디컨플릭션(CBS) -- 사전 비행 전략적 충돌 해소 구현",
        ),
        FAARequirement(
            "USS-14", "Strategic Deconfliction",
            "USS shall negotiate 4D volumes with other USSs to resolve intent conflicts",
            "ConOps v2 §6.3.2",
            "simulation/federation_conflict_resolution.py",
            "partial",
            "연합 충돌 해소 프로토콜 존재 -- 다자간 4D 볼륨 협상 절차 부분 구현",
        ),
        FAARequirement(
            "USS-15", "Strategic Deconfliction",
            "USS shall apply priority-based sequencing for operations in constrained airspace",
            "ConOps v2 §6.4",
            "src/airspace_control/controller/priority_queue.py",
            "full",
            "우선순위 큐 기반 혼잡 공역 순서 배정 구현",
        ),
        # --- Conformance Monitoring ---
        FAARequirement(
            "USS-16", "Conformance Monitoring",
            "USS shall monitor UAS conformance to approved operational volumes",
            "ConOps v2 §7.1",
            "simulation/compliance_checker.py",
            "full",
            "적합성 검사기 -- 승인 운용 공역 대비 실시간 적합성 감시",
        ),
        FAARequirement(
            "USS-17", "Conformance Monitoring",
            "USS shall initiate contingency procedures when non-conformance is detected",
            "ConOps v2 §7.2",
            "simulation/federation_handover.py",
            "partial",
            "연합 핸드오버 프로토콜 존재 -- 비적합 시 비상 절차 자동 트리거 부분 구현",
        ),
        # --- Data Exchange ---
        FAARequirement(
            "USS-18", "Data Exchange",
            "USS shall exchange operational intent and UAS position data with peer USSs",
            "ConOps v2 §8.1",
            "simulation/operational_intent.py",
            "partial",
            "Operational Intent 교환 구현 -- 피어 USS 간 위치 데이터 교환 프로토콜 불완전",
        ),
        FAARequirement(
            "USS-19", "Data Exchange",
            "USS shall publish and consume NOTAMs and airspace constraints",
            "ConOps v2 §8.2",
            "simulation/federation_notam.py",
            "partial",
            "연합 NOTAM 발행 및 수신 구현 -- FAA NOTAM 형식(FNS) 변환 미구현",
        ),
        # --- Network ---
        FAARequirement(
            "USS-20", "Network",
            "USS shall maintain persistent connectivity to the UTM network (FIMS interface)",
            "ConOps v2 §9.1",
            "simulation/federation_mesh.py",
            "partial",
            "연합 메시 네트워크 구현 -- FAA FIMS 인터페이스 프로토콜 미대응",
        ),
        FAARequirement(
            "USS-21", "Network",
            "USS shall comply with ASTM F3548 interoperability requirements for USS-USS communication",
            "ConOps v2 §9.2",
            "simulation/federation_mesh.py",
            "partial",
            "메시 기반 USS-USS 통신 존재 -- ASTM F3548 완전 적합성 시험 미완료",
        ),
    )

    def analyze(self) -> GapAnalysis:
        """갭 분석을 수행하고 집계 결과를 반환한다."""
        full = sum(1 for r in self.REQUIREMENTS if r.compliance_level == "full")
        partial = sum(1 for r in self.REQUIREMENTS if r.compliance_level == "partial")
        gap_count = sum(1 for r in self.REQUIREMENTS if r.compliance_level == "gap")
        na = sum(1 for r in self.REQUIREMENTS if r.compliance_level == "not_applicable")
        total = len(self.REQUIREMENTS)

        denominator = total - na
        compliance_pct = (
            (full + 0.5 * partial) / denominator * 100.0 if denominator > 0 else 0.0
        )

        by_cat: dict[str, dict[str, int]] = {}
        for req in self.REQUIREMENTS:
            bucket = by_cat.setdefault(req.category, {"full": 0, "partial": 0, "gap": 0})
            if req.compliance_level in ("full", "partial", "gap"):
                bucket[req.compliance_level] += 1

        return GapAnalysis(
            total=total,
            full=full,
            partial=partial,
            gap=gap_count,
            not_applicable=na,
            compliance_pct=round(compliance_pct, 2),
            by_category=types.MappingProxyType(
                {k: dict(v) for k, v in by_cat.items()}
            ),
        )

    def requirements_by_category(self, category: str) -> tuple[FAARequirement, ...]:
        """지정 카테고리의 요구사항을 req_id 정렬로 반환한다."""
        return tuple(
            sorted(
                (r for r in self.REQUIREMENTS if r.category == category),
                key=lambda r: r.req_id,
            )
        )

    def gaps(self) -> tuple[FAARequirement, ...]:
        """compliance_level == 'gap'인 요구사항만 req_id 정렬로 반환한다."""
        return tuple(
            sorted(
                (r for r in self.REQUIREMENTS if r.compliance_level == "gap"),
                key=lambda r: r.req_id,
            )
        )

    def gap_report(self) -> str:
        """FAA UTM USS 갭 분석 텍스트 리포트를 생성한다."""
        analysis = self.analyze()
        lines: list[str] = [
            "FAA UTM ConOps v2 -- USS 역할 요구사항 갭 분석",
            "=" * 52,
            "",
            f"총 요구사항     : {analysis.total}",
            f"완전 충족 (full): {analysis.full}",
            f"부분 충족 (partial): {analysis.partial}",
            f"갭 (gap)        : {analysis.gap}",
            f"비해당 (N/A)    : {analysis.not_applicable}",
            f"충족률          : {analysis.compliance_pct:.1f}%",
            "",
            "-" * 52,
            "카테고리별 현황",
            "-" * 52,
        ]

        for cat in CATEGORIES:
            counts = analysis.by_category.get(cat)
            if counts is None:
                continue
            lines.append(
                f"  {cat:28s}: full={counts['full']} partial={counts['partial']} gap={counts['gap']}"
            )

        lines.extend(["", "-" * 52, "요구사항 상세", "-" * 52])

        for req in self.REQUIREMENTS:
            mark = {"full": "[O]", "partial": "[~]", "gap": "[X]", "not_applicable": "[-]"}
            lines.append(
                f"{mark[req.compliance_level]} {req.req_id} [{req.category}] {req.description}"
            )
            module_str = req.sdacs_module or "(없음)"
            lines.append(f"    ConOps: {req.conops_ref} | 모듈: {module_str}")
            lines.append(f"    비고: {req.notes}")
            lines.append("")

        return "\n".join(lines)

    def to_json(self) -> list[dict[str, object]]:
        """JSON 직렬화 가능한 요구사항 목록을 반환한다."""
        return [
            {
                "req_id": r.req_id,
                "category": r.category,
                "description": r.description,
                "conops_ref": r.conops_ref,
                "sdacs_module": r.sdacs_module,
                "compliance_level": r.compliance_level,
                "notes": r.notes,
            }
            for r in self.REQUIREMENTS
        ]


def main(argv: list[str] | None = None) -> int:
    """CLI 엔트리포인트."""
    parser = argparse.ArgumentParser(
        description="FAA UTM ConOps v2 USS 역할 갭 분석 (ODYSSEY Phase 402)"
    )
    parser.add_argument("--report", action="store_true", help="전체 갭 분석 리포트 출력")
    parser.add_argument("--gaps", action="store_true", help="갭 항목만 출력")
    parser.add_argument("--json", action="store_true", help="JSON 형식 출력")
    parser.add_argument("--category", type=str, help="카테고리별 요구사항 출력")
    args = parser.parse_args(argv)

    analyzer = FAAUTMGapAnalyzer()

    if args.report:
        print(analyzer.gap_report())
    elif args.gaps:
        for req in analyzer.gaps():
            print(f"[{req.category}] {req.req_id}: {req.description}")
            print(f"  비고: {req.notes}")
    elif args.json:
        print(json.dumps(analyzer.to_json(), ensure_ascii=False, indent=2))
    elif args.category:
        reqs = analyzer.requirements_by_category(args.category)
        if not reqs:
            print(f"카테고리 '{args.category}'에 해당하는 요구사항 없음")
        for req in reqs:
            mark = {"full": "O", "partial": "~", "gap": "X", "not_applicable": "-"}
            print(f"[{mark[req.compliance_level]}] {req.req_id}: {req.description}")
            print(f"    모듈: {req.sdacs_module or '(없음)'}")
    else:
        # 기본: 요약 출력
        analysis = analyzer.analyze()
        print(f"FAA UTM USS 갭 분석 -- 충족률 {analysis.compliance_pct:.1f}% "
              f"(full={analysis.full} partial={analysis.partial} gap={analysis.gap})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
