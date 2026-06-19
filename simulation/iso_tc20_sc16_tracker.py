"""ODYSSEY Phase 462 — ISO/TC 20/SC 16 (UAS) 표준 동향 추적 매트릭스.

ISO 기술위원회 TC 20(Aircraft and space vehicles) 산하 소위원회 **SC 16
(Unmanned aircraft systems)** 이 개발·발행한 국제 표준을 SDACS 기능에 결정적으로
대응시켜, "SDACS 가 ISO UAS 표준 체계 어디에 정렬하고 어디가 갭인가" 를 추적하는
동향 매트릭스다. Phase 401(EASA U-space)·402(FAA UTM)·407(ICAO Framework) 가
*운영/규제* 체계 정렬을 다룬다면, 본 Phase 는 *국제 표준화(ISO)* 축을 별도로 추적한다
— 같은 SDACS 자산을 ISO 표준의 렌즈로 재평가하는 자매편이다.

근거 (권위 있는 출처)
--------------------
- **ISO/TC 20/SC 16** — UAS 국제 표준화 소위원회. 본 모듈이 추적하는 표준은 다음
  계열로 묶인다:
  - **ISO 21384 계열** — UAS 일반: Part 1(General specification)·Part 2(UA system
    components)·Part 3(Operational procedures)·Part 4(Vocabulary)
  - **ISO 21895** — 민간 UAS 분류 체계(Categorization and classification)
  - **ISO 23665** — UAS 운영 인력 훈련(Training for personnel)
  - **ISO 23629 계열** — UTM(UAS Traffic Management): Part 5(functional structure)·
    Part 7(data model for spatial data)

정직 공시 (CLAUDE.md)
--------------------
- ``status`` 와 표준 발행/개발 단계는 **프로젝트가 추적하는 스냅샷**(``AS_OF``)이며
  공식 권위는 ISO 카탈로그(iso.org)다. 정확한 판(edition)·발행 연도는 ISO 카탈로그로
  확인해야 한다. 본 매트릭스는 표준 *번호와 표제* 의 안정성에 의존할 뿐, 시기 주장에
  의존하지 않는다.
- ``sdacs_module`` 은 해당 표준의 범위를 *실제로* 다루는 리포 내 모듈 경로다. 대응
  모듈이 없으면 ``None`` 으로 **갭(gap)** 임을 정직히 표면화한다 — 본 모듈의 가치는
  정렬 주장보다 *미정렬 항목의 가시화* 에 있다. 매핑은 기능적 대응이며 ISO 적합성
  인증이 아니다.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/iso_tc20_sc16_tracker.py --matrix       # 전체 표준 매트릭스
    python simulation/iso_tc20_sc16_tracker.py --report       # 추적 요약
    python simulation/iso_tc20_sc16_tracker.py --category "UTM / Traffic Management"
    python simulation/iso_tc20_sc16_tracker.py --gaps         # SDACS 미정렬(갭) 표준
    python simulation/iso_tc20_sc16_tracker.py --published    # 발행 완료 표준
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

# 본 추적 스냅샷 기준 시점. status 는 이 시점의 프로젝트 추적값이며 권위는 ISO 카탈로그.
AS_OF: str = "2026-06"

# ISO/TC 20/SC 16 표준의 기능 범주 (추적 분류 축).
CATEGORIES: tuple[str, ...] = (
    "General & Vocabulary",
    "UAS Components",
    "Operational Procedures",
    "Categorization & Safety",
    "UTM / Traffic Management",
    "Training & Personnel",
)

# 표준 개발 단계 (프로젝트 추적 스냅샷). 권위는 ISO 카탈로그.
STATUSES: tuple[str, ...] = (
    "published",
    "under_development",
)


@dataclass(frozen=True)
class ISOStandard:
    """단일 ISO/TC 20/SC 16 표준과 SDACS 정렬의 정의."""

    standard_id: str          # 안정 식별자 겸 표준 번호 (예: 'ISO 21384-3')
    title: str                # 표준 표제
    series: str               # 계열 (예: 'ISO 21384', 'ISO 23629')
    category: str             # 기능 범주 (CATEGORIES 중 하나)
    status: str               # 개발 단계 (STATUSES 중 하나, AS_OF 스냅샷)
    sdacs_module: str | None  # 정렬 모듈 경로 (없으면 갭)
    summary: str              # 한 줄 설명

    def __post_init__(self) -> None:
        if not self.standard_id or self.standard_id != self.standard_id.strip():
            raise ValueError("standard_id must be non-empty and unpadded")
        if not self.title or not self.title.strip():
            raise ValueError("title must be a non-empty string")
        if not self.series or self.series != self.series.strip():
            raise ValueError("series must be non-empty and unpadded")
        # series 는 표준 번호의 *온전한* 접두여야 한다 — bare startswith 는
        # series='ISO 21' 가 standard_id='ISO 218' 을 오인하므로 구분자(-·공백)
        # 또는 문자열 끝이 뒤따라야 함을 강제한다.
        remainder = self.standard_id[len(self.series):]
        if not self.standard_id.startswith(self.series) or (
            remainder and remainder[0] not in ("-", " ")
        ):
            raise ValueError(
                f"standard_id {self.standard_id!r} must start with its series "
                f"{self.series!r} followed by a separator or end-of-string"
            )
        if not self.summary or not self.summary.strip():
            raise ValueError("summary must be a non-empty string")
        if self.category not in CATEGORIES:
            raise ValueError(
                f"category must be one of {CATEGORIES}, got {self.category!r}"
            )
        if self.status not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}, got {self.status!r}")
        if self.sdacs_module is not None and not self.sdacs_module.strip():
            raise ValueError("sdacs_module must be None or a non-empty path")

    @property
    def is_aligned(self) -> bool:
        """SDACS 정렬 모듈이 존재하면 True (갭이 아니면 True)."""
        return self.sdacs_module is not None

    @property
    def is_published(self) -> bool:
        """발행 완료 표준이면 True."""
        return self.status == "published"


# ISO/TC 20/SC 16 표준 카탈로그 ↔ SDACS 모듈 매핑 (정본).
# sdacs_module 경로는 리포에 실재하는 모듈 — 미정렬은 None(갭).
# status 는 AS_OF 스냅샷이며 권위는 ISO 카탈로그.
ISO_STANDARDS: tuple[ISOStandard, ...] = (
    ISOStandard(
        "ISO 21384-1", "Unmanned aircraft systems — Part 1: General specification",
        "ISO 21384", "General & Vocabulary", "under_development",
        None,
        "UAS 일반 사양 — 시스템 수준 요구사항. 현 시뮬은 하드웨어 사양 비모델 (갭)",
    ),
    ISOStandard(
        "ISO 21384-2", "Unmanned aircraft systems — Part 2: UAS components",
        "ISO 21384", "UAS Components", "under_development",
        None,
        "UAS 구성품 사양 — 기체·부품 수준. 시뮬은 물리 구성품 비모델 (갭)",
    ),
    ISOStandard(
        "ISO 21384-3", "Unmanned aircraft systems — Part 3: Operational procedures",
        "ISO 21384", "Operational Procedures", "published",
        "simulation/compliance_checker.py",
        "UAS 운영 절차 — 비행 전/중/후 절차·규정 준수. 적합성 검사기로 정렬",
    ),
    ISOStandard(
        "ISO 21384-4", "Unmanned aircraft systems — Part 4: Vocabulary",
        "ISO 21384", "General & Vocabulary", "published",
        None,
        "UAS 용어 정의 — 표준 어휘. 전용 용어집 모듈 부재 (갭)",
    ),
    ISOStandard(
        "ISO 21895", "Categorization and classification of civil unmanned aircraft systems",
        "ISO 21895", "Categorization & Safety", "published",
        "simulation/sora_category.py",
        "민간 UAS 분류 체계 — 위험 기반 범주화. SORA 카테고리 판정으로 정렬",
    ),
    ISOStandard(
        "ISO 23665", "Training for personnel involved in UAS operations",
        "ISO 23665", "Training & Personnel", "published",
        None,
        "UAS 운영 인력 훈련 요건 — 자격·역량. 훈련 관리 모듈 부재 (갭)",
    ),
    ISOStandard(
        "ISO 23629-5", "UAS traffic management (UTM) — Part 5: UTM functional structure",
        "ISO 23629", "UTM / Traffic Management", "published",
        "simulation/federation_discovery.py",
        "UTM 기능 구조 — 서비스·인터페이스 골격. 연합 디스커버리로 정렬",
    ),
    ISOStandard(
        "ISO 23629-7", "UAS traffic management (UTM) — Part 7: Data model for spatial data",
        "ISO 23629", "UTM / Traffic Management", "published",
        "simulation/operational_intent.py",
        "UTM 공간 데이터 모델 — 4D 볼륨 표현. 운영 의도 직렬화로 정렬",
    ),
)


# 적재 시점 중복 식별자 방어 (icao 자매편 규약) — 테스트 이전에 즉시 실패.
_CATALOG_IDS = [s.standard_id for s in ISO_STANDARDS]
assert len(_CATALOG_IDS) == len(set(_CATALOG_IDS)), "duplicate standard_id in ISO_STANDARDS"


@dataclass(frozen=True)
class TrackingReport:
    """ISO/TC 20/SC 16 표준 추적 현황 요약."""

    total: int
    published: int
    under_development: int
    aligned: int
    gaps: int
    by_category: Mapping[str, tuple[int, int]]  # category -> (aligned, total), read-only

    def __post_init__(self) -> None:
        # by_category 를 읽기 전용으로 강제 — 직접 생성 시에도 불변 보장 (icao 자매편 규약).
        if not isinstance(self.by_category, MappingProxyType):
            object.__setattr__(self, "by_category", MappingProxyType(dict(self.by_category)))
        if min(self.total, self.published, self.under_development,
               self.aligned, self.gaps) < 0:
            raise ValueError("counts must be non-negative")
        if self.published + self.under_development != self.total:
            raise ValueError(
                f"published ({self.published}) + under_development "
                f"({self.under_development}) != total ({self.total})"
            )
        if self.aligned + self.gaps != self.total:
            raise ValueError(
                f"aligned ({self.aligned}) + gaps ({self.gaps}) != total ({self.total})"
            )
        # by_category 가 제공되면 그 합이 상위 집계와 교차 일치해야 한다.
        if self.by_category:
            cat_total = sum(tot for _, tot in self.by_category.values())
            cat_aligned = sum(al for al, _ in self.by_category.values())
            if cat_total != self.total:
                raise ValueError(
                    f"by_category total sum ({cat_total}) != total ({self.total})"
                )
            if cat_aligned != self.aligned:
                raise ValueError(
                    f"by_category aligned sum ({cat_aligned}) != aligned ({self.aligned})"
                )

    @property
    def alignment_pct(self) -> float:
        """전체 표준 대비 SDACS 정렬 비율 (%)."""
        return 100.0 * self.aligned / self.total if self.total else 0.0


def find_standard(standard_id: str) -> ISOStandard:
    """표준 번호로 표준을 조회한다. 없으면 KeyError."""
    for std in ISO_STANDARDS:
        if std.standard_id == standard_id:
            return std
    raise KeyError(f"unknown ISO standard: {standard_id!r}")


def standards_by_category(category: str) -> tuple[ISOStandard, ...]:
    """범주에 속한 표준을 표준 번호 정렬로 반환한다."""
    if category not in CATEGORIES:
        raise ValueError(f"category must be one of {CATEGORIES}, got {category!r}")
    return tuple(
        sorted(
            (s for s in ISO_STANDARDS if s.category == category),
            key=lambda s: s.standard_id,
        )
    )


def standards_by_series(series: str) -> tuple[ISOStandard, ...]:
    """계열에 속한 표준을 표준 번호 정렬로 반환한다."""
    return tuple(
        sorted(
            (s for s in ISO_STANDARDS if s.series == series),
            key=lambda s: s.standard_id,
        )
    )


def gaps() -> tuple[ISOStandard, ...]:
    """SDACS 정렬 모듈이 없는(갭) 표준을 표준 번호 정렬로 반환한다."""
    return tuple(
        sorted((s for s in ISO_STANDARDS if not s.is_aligned), key=lambda s: s.standard_id)
    )


def aligned_standards() -> tuple[ISOStandard, ...]:
    """SDACS 정렬 모듈이 있는 표준을 표준 번호 정렬로 반환한다."""
    return tuple(
        sorted((s for s in ISO_STANDARDS if s.is_aligned), key=lambda s: s.standard_id)
    )


def published_standards() -> tuple[ISOStandard, ...]:
    """발행 완료(AS_OF 스냅샷) 표준을 표준 번호 정렬로 반환한다."""
    return tuple(
        sorted((s for s in ISO_STANDARDS if s.is_published), key=lambda s: s.standard_id)
    )


def tracking_report() -> TrackingReport:
    """전체 표준 추적 현황을 집계한 결정적 리포트를 생성한다."""
    total = len(ISO_STANDARDS)
    published = sum(1 for s in ISO_STANDARDS if s.is_published)
    aligned = sum(1 for s in ISO_STANDARDS if s.is_aligned)
    by_category: dict[str, tuple[int, int]] = {}
    for category in CATEGORIES:
        members = [s for s in ISO_STANDARDS if s.category == category]
        by_category[category] = (sum(1 for s in members if s.is_aligned), len(members))
    return TrackingReport(
        total=total,
        published=published,
        under_development=total - published,
        aligned=aligned,
        gaps=total - aligned,
        by_category=MappingProxyType(by_category),
    )


def tracking_matrix() -> tuple[Mapping[str, object], ...]:
    """도구 간 교환용 추적 매트릭스를 (범주, 표준 번호) 정렬 행으로 반환한다.

    각 행은 ``MappingProxyType`` 읽기 전용 — ``by_category`` 와 동일한 불변 보장.
    """
    ordered = sorted(
        ISO_STANDARDS,
        key=lambda s: (CATEGORIES.index(s.category), s.standard_id),
    )
    return tuple(
        MappingProxyType(
            {
                "standard_id": s.standard_id,
                "title": s.title,
                "series": s.series,
                "category": s.category,
                "status": s.status,
                "aligned": s.is_aligned,
                "sdacs_module": s.sdacs_module,
            }
        )
        for s in ordered
    )


def _format_matrix() -> str:
    lines = [f"ISO/TC 20/SC 16 (UAS) 표준 ↔ SDACS 정렬 매트릭스 (as of {AS_OF})", ""]
    for row in tracking_matrix():
        mark = "✓" if row["aligned"] else "✗(갭)"
        status = "발행" if row["status"] == "published" else "개발중"
        module = row["sdacs_module"] or "—"
        lines.append(f"[{row['category']}] {mark} ({status}) {row['standard_id']}: {row['title']}")
        lines.append(f"      → {module}")
    return "\n".join(lines)


def _format_report() -> str:
    r = tracking_report()
    lines = [
        f"ISO/TC 20/SC 16 (UAS) 표준 추적 요약 (as of {AS_OF})",
        "",
        f"전체 표준   : {r.total}",
        f"발행 완료   : {r.published}  /  개발 중: {r.under_development}",
        f"SDACS 정렬  : {r.aligned}/{r.total} ({r.alignment_pct:.0f}%)  /  갭: {r.gaps}",
        "",
        "범주별 정렬:",
    ]
    for category in CATEGORIES:
        aligned, tot = r.by_category[category]
        lines.append(f"  {category:28}: {aligned}/{tot}")
    lines.append("")
    lines.append("주: status 는 프로젝트 추적 스냅샷이며 권위는 ISO 카탈로그(iso.org).")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ISO/TC 20/SC 16 (UAS) 표준 동향 추적 (ODYSSEY Phase 462)"
    )
    parser.add_argument("--matrix", action="store_true", help="전체 표준 매트릭스 출력")
    parser.add_argument("--report", action="store_true", help="추적 요약 출력")
    parser.add_argument("--category", choices=CATEGORIES, help="범주별 표준 출력")
    parser.add_argument("--gaps", action="store_true", help="SDACS 미정렬(갭) 표준 출력")
    parser.add_argument("--published", action="store_true", help="발행 완료 표준 출력")
    args = parser.parse_args(argv)

    if args.matrix:
        print(_format_matrix())
    elif args.report:
        print(_format_report())
    elif args.category:
        for std in standards_by_category(args.category):
            print(f"{std.standard_id}: {std.title} — {std.summary}")
    elif args.gaps:
        for std in gaps():
            print(f"[{std.category}] {std.standard_id} {std.title}: {std.summary}")
    elif args.published:
        for std in published_standards():
            mark = "✓" if std.is_aligned else "✗"
            print(f"{mark} {std.standard_id}: {std.title} → {std.sdacs_module or '—'}")
    else:
        print(_format_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
