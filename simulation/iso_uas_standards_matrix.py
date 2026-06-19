"""ODYSSEY Phase 462 — ISO/TC 20/SC 16 (UAS) 표준 동향 추적 매트릭스.

ISO/TC 20/SC 16(무인항공기시스템 분과위원회)이 발간·개발 중인 핵심 표준을
SDACS 모듈에 결정적으로 대응시키는 추적 매트릭스다. Standards & Policy
트랙(ODYSSEY 461-480)이 "SDACS 가 국제 UAS 표준의 어느 항목을 기능적으로
구현하고, 어디가 갭인가" 를 객관적으로 답하기 위한 자가 평가 기준 모듈이며,
Phase 401(EASA U-space 매핑)의 자매 매트릭스다.

근거 (ISO/TC 20/SC 16 발간물)
---------------------------
- **ISO 21384 시리즈** — UAS 일반: Part 1(일반 명세)·Part 2(구성품)·
  Part 3(운영 절차).
- **ISO 21895** — 민수 UAS 분류·범주화.
- **ISO 23665** — UAS 운용 인력 훈련.
- **ISO 23629 시리즈** — UTM(UAS Traffic Management): Part 5(기능 구조·정보
  흐름)·Part 7(공간 데이터 모델)·Part 8(원격 식별, 개발 중)·Part 12(UTM
  서비스 제공자 요건).

정직 공시 (CLAUDE.md)
--------------------
- ``sdacs_module`` 은 해당 표준이 다루는 기능을 *실제로* 제공하는 리포 내 모듈
  경로다. 대응 모듈이 없는 표준(예: 인력 훈련·물리 구성품 적합성)은 ``None`` 으로
  **갭(gap)** 임을 정직히 표면화한다 — 본 모듈의 가치는 충족 주장보다 *미충족
  항목의 가시화* 에 있다.
- 매핑은 *기능적 대응* 이며 ISO 공식 인증·적합성 선언이 아니다.
- 표준의 **판(edition) 연도는 의도적으로 보유하지 않는다** — 현행 판은 ISO
  카탈로그가 유일 출처(SSoT)이며 본 모듈에 박제하면 표류한다. 발간 상태
  (``PUBLISHED`` / ``UNDER_DEVELOPMENT``)만 추적한다.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/iso_uas_standards_matrix.py --matrix      # 전체 매트릭스
    python simulation/iso_uas_standards_matrix.py --coverage    # 커버리지 요약
    python simulation/iso_uas_standards_matrix.py --category UTM # 범주별 표준
    python simulation/iso_uas_standards_matrix.py --gaps         # 미충족(갭) 표준
    python simulation/iso_uas_standards_matrix.py --published    # 발간 완료 표준
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

# ISO/TC 20/SC 16 표준 범주 (추적용 분류 축).
CATEGORIES: tuple[str, ...] = (
    "General",
    "Operations",
    "Classification",
    "Personnel",
    "UTM",
)

# 발간 상태 — 현행 판 연도가 아닌 발간 진행 단계만 추적한다.
STATUSES: tuple[str, ...] = ("PUBLISHED", "UNDER_DEVELOPMENT")

_CATEGORY_NAMES: dict[str, str] = {
    "General": "UAS 일반 명세·구성품",
    "Operations": "운영 절차·관제",
    "Classification": "분류·범주화",
    "Personnel": "운용 인력·훈련",
    "UTM": "UAS 교통 관리(UTM)",
}


@dataclass(frozen=True)
class IsoStandard:
    """단일 ISO/TC 20/SC 16 표준과 SDACS 대응의 정의."""

    standard_id: str          # 표준 번호 (예: 'ISO 21384-3')
    title: str                # 표준 표제
    category: str             # 추적 범주 (CATEGORIES 중 하나)
    status: str               # 발간 상태 (STATUSES 중 하나)
    sdacs_module: str | None  # 기능 제공 모듈 경로 (없으면 갭)
    relevance: str            # SDACS 와의 관련성 한 줄 설명

    def __post_init__(self) -> None:
        if not self.standard_id or self.standard_id != self.standard_id.strip():
            raise ValueError("standard_id must be non-empty and unpadded")
        if not self.title or not self.title.strip():
            raise ValueError("title must be a non-empty string")
        if not self.relevance or not self.relevance.strip():
            raise ValueError("relevance must be a non-empty string")
        if self.category not in CATEGORIES:
            raise ValueError(
                f"category must be one of {CATEGORIES}, got {self.category!r}"
            )
        if self.status not in STATUSES:
            raise ValueError(
                f"status must be one of {STATUSES}, got {self.status!r}"
            )
        if self.sdacs_module is not None and not self.sdacs_module.strip():
            raise ValueError("sdacs_module must be None or a non-empty path")

    @property
    def is_covered(self) -> bool:
        """SDACS 대응 모듈이 존재하면 True (갭이 아니면 True)."""
        return self.sdacs_module is not None

    @property
    def is_published(self) -> bool:
        """ISO 발간이 완료된 표준이면 True."""
        return self.status == "PUBLISHED"


# ISO/TC 20/SC 16 표준 카탈로그 ↔ SDACS 모듈 매핑 (정본).
# sdacs_module 경로는 리포에 실재하는 모듈 — 미대응은 None(갭).
ISO_STANDARDS: tuple[IsoStandard, ...] = (
    IsoStandard(
        "ISO 21384-1", "UAS — Part 1: General specification",
        "General", "PUBLISHED",
        "simulation/drone_agent.py",
        "UAS 플랫폼 일반 명세 — DroneAgent 비행체 모델(10Hz SimPy)",
    ),
    IsoStandard(
        "ISO 21384-2", "UAS — Part 2: UAS components",
        "General", "PUBLISHED",
        None,
        "물리 구성품 적합성 — SDACS 는 비행 거동 모델이며 부품 인증 범위 밖 (갭)",
    ),
    IsoStandard(
        "ISO 21384-3", "UAS — Part 3: Operational procedures",
        "Operations", "PUBLISHED",
        "src/airspace_control/controller/airspace_controller.py",
        "운영 절차·관제 — AirspaceController 1Hz 비행 승인·분리 유지",
    ),
    IsoStandard(
        "ISO 21895", "Categorization and classification of civil UAS",
        "Classification", "PUBLISHED",
        "simulation/sora_category.py",
        "민수 UAS 분류 — EU 2019/947 운영 카테고리(Open/Specific/Certified) 판정",
    ),
    IsoStandard(
        "ISO 23665", "Training for personnel involved in UAS operations",
        "Personnel", "PUBLISHED",
        None,
        "운용 인력 훈련 — 인적 훈련 체계는 시뮬 범위 밖 (갭)",
    ),
    IsoStandard(
        "ISO 23629-5", "UTM — Part 5: UTM functional structure and information flows",
        "UTM", "PUBLISHED",
        "simulation/kutm_protocol.py",
        "UTM 기능 구조·정보 흐름 — K-UTM 표준 프로토콜 준수 시뮬레이션",
    ),
    IsoStandard(
        "ISO 23629-7", "UTM — Part 7: Data model for spatial data",
        "UTM", "PUBLISHED",
        "simulation/telemetry_validator.py",
        "공간 데이터 모델 — 텔레메트리 표준 스키마 검증기(JSON Schema 계약)",
    ),
    IsoStandard(
        "ISO 23629-8", "UTM — Part 8: Remote identification",
        "UTM", "UNDER_DEVELOPMENT",
        "simulation/remote_id.py",
        "원격 식별 — Remote ID 송출(ASTM F3411 호환) 시뮬레이션",
    ),
    IsoStandard(
        "ISO 23629-12", "UTM — Part 12: Requirements for UTM service providers",
        "UTM", "PUBLISHED",
        # UTM 기능 구조와 서비스 제공자 요건 모두 kutm_protocol.py 가 제공 — 의도된 모듈 공유.
        "simulation/kutm_protocol.py",
        "UTM 서비스 제공자 요건 — K-UTM 프로토콜 준수·인터페이스 계약",
    ),
)


@dataclass(frozen=True)
class CoverageReport:
    """ISO/TC 20/SC 16 표준 충족 커버리지 요약."""

    total: int
    covered: int
    gaps: int
    published_total: int
    published_covered: int
    by_category: Mapping[str, tuple[int, int]]  # category -> (covered, total), read-only

    def __post_init__(self) -> None:
        if min(self.total, self.covered, self.gaps,
               self.published_total, self.published_covered) < 0:
            raise ValueError("counts must be non-negative")
        if self.covered + self.gaps != self.total:
            raise ValueError(
                f"covered ({self.covered}) + gaps ({self.gaps}) != total ({self.total})"
            )
        if self.covered > self.total:
            raise ValueError("covered cannot exceed total")
        if self.published_covered > self.published_total:
            raise ValueError("published_covered cannot exceed published_total")
        if self.published_total > self.total:
            raise ValueError("published_total cannot exceed total")

    @property
    def coverage_pct(self) -> float:
        """전체 표준 기능 충족 비율 (%)."""
        return 100.0 * self.covered / self.total if self.total else 0.0

    @property
    def published_coverage_pct(self) -> float:
        """발간 완료 표준 중 기능 충족 비율 (%)."""
        if not self.published_total:
            return 0.0
        return 100.0 * self.published_covered / self.published_total


def find_standard(standard_id: str) -> IsoStandard:
    """표준 번호로 표준을 조회한다. 없으면 KeyError."""
    for std in ISO_STANDARDS:
        if std.standard_id == standard_id:
            return std
    raise KeyError(f"unknown ISO standard: {standard_id!r}")


def standards_by_category(category: str) -> tuple[IsoStandard, ...]:
    """범주에 속한 표준을 표준 번호 정렬로 반환한다."""
    if category not in CATEGORIES:
        raise ValueError(f"category must be one of {CATEGORIES}, got {category!r}")
    return tuple(
        sorted((s for s in ISO_STANDARDS if s.category == category),
               key=lambda s: s.standard_id)
    )


def standards_by_status(status: str) -> tuple[IsoStandard, ...]:
    """발간 상태별 표준을 표준 번호 정렬로 반환한다."""
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}, got {status!r}")
    return tuple(
        sorted((s for s in ISO_STANDARDS if s.status == status),
               key=lambda s: s.standard_id)
    )


def gaps() -> tuple[IsoStandard, ...]:
    """SDACS 대응 모듈이 없는(미충족) 표준을 표준 번호 정렬로 반환한다."""
    return tuple(
        sorted((s for s in ISO_STANDARDS if not s.is_covered), key=lambda s: s.standard_id)
    )


def covered_standards() -> tuple[IsoStandard, ...]:
    """SDACS 대응 모듈이 있는 표준을 표준 번호 정렬로 반환한다."""
    return tuple(
        sorted((s for s in ISO_STANDARDS if s.is_covered), key=lambda s: s.standard_id)
    )


def coverage_report() -> CoverageReport:
    """전체 표준 기능 충족 현황을 집계한 결정적 커버리지 리포트를 생성한다."""
    total = len(ISO_STANDARDS)
    covered = sum(1 for s in ISO_STANDARDS if s.is_covered)
    published = [s for s in ISO_STANDARDS if s.is_published]
    published_covered = sum(1 for s in published if s.is_covered)
    by_category: dict[str, tuple[int, int]] = {}
    for category in CATEGORIES:
        members = [s for s in ISO_STANDARDS if s.category == category]
        by_category[category] = (sum(1 for s in members if s.is_covered), len(members))
    return CoverageReport(
        total=total,
        covered=covered,
        gaps=total - covered,
        published_total=len(published),
        published_covered=published_covered,
        by_category=MappingProxyType(by_category),
    )


def standards_matrix() -> tuple[dict[str, object], ...]:
    """도구 간 교환용 표준 매트릭스를 (범주, 표준 번호) 정렬 행으로 반환한다."""
    ordered = sorted(
        ISO_STANDARDS, key=lambda s: (CATEGORIES.index(s.category), s.standard_id)
    )
    return tuple(
        {
            "standard_id": s.standard_id,
            "title": s.title,
            "category": s.category,
            "status": s.status,
            "covered": s.is_covered,
            "sdacs_module": s.sdacs_module,
        }
        for s in ordered
    )


def _format_matrix() -> str:
    lines = ["ISO/TC 20/SC 16 (UAS) 표준 ↔ SDACS 매트릭스", ""]
    for row in standards_matrix():
        mark = "✓" if row["covered"] else "✗(갭)"
        stat = "발간" if row["status"] == "PUBLISHED" else "개발중"
        module = row["sdacs_module"] or "—"
        lines.append(f"[{row['category']:11}] {mark} {stat:3} {row['standard_id']} — {row['title']}")
        lines.append(f"      → {module}")
    return "\n".join(lines)


def _format_coverage() -> str:
    r = coverage_report()
    lines = [
        "ISO/TC 20/SC 16 커버리지 요약",
        "",
        f"전체 기능 충족 : {r.covered}/{r.total} ({r.coverage_pct:.0f}%)",
        f"발간 표준 중   : {r.published_covered}/{r.published_total} "
        f"({r.published_coverage_pct:.0f}%)",
        "",
        "범주별:",
    ]
    for category in CATEGORIES:
        cov, tot = r.by_category[category]
        lines.append(f"  {category:12} ({_CATEGORY_NAMES[category]}): {cov}/{tot}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ISO/TC 20/SC 16 (UAS) 표준 추적 매트릭스 (ODYSSEY Phase 462)"
    )
    parser.add_argument("--matrix", action="store_true", help="전체 매트릭스 출력")
    parser.add_argument("--coverage", action="store_true", help="커버리지 요약 출력")
    parser.add_argument("--category", choices=CATEGORIES, help="범주별 표준 출력")
    parser.add_argument("--gaps", action="store_true", help="미충족(갭) 표준 출력")
    parser.add_argument("--published", action="store_true", help="발간 완료 표준 출력")
    args = parser.parse_args(argv)

    if args.matrix:
        print(_format_matrix())
    elif args.coverage:
        print(_format_coverage())
    elif args.category:
        for std in standards_by_category(args.category):
            print(f"{std.standard_id}: {std.title} — {std.relevance}")
    elif args.gaps:
        for std in gaps():
            print(f"[{std.category}] {std.standard_id} {std.title}: {std.relevance}")
    elif args.published:
        for std in standards_by_status("PUBLISHED"):
            mark = "✓" if std.is_covered else "✗"
            print(f"{mark} {std.standard_id} {std.title} → {std.sdacs_module or '—'}")
    else:
        print(_format_coverage())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
