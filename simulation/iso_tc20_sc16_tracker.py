"""ODYSSEY Phase 462 — ISO/TC 20/SC 16 (UAS) 표준 동향 추적 매트릭스.

ISO/TC 20/SC 16(*Unmanned aircraft systems*) 위원회가 발행·개발 중인 *외부* UAS
국제 표준의 현황을 결정적으로 추적하고, 각 표준에 대한 SDACS 정렬(alignment)
상태를 표면화한다. Standards & Policy 트랙(Phase 461-480)에서 "우리가 어떤 ISO
표준을 따라가야 하며 어디까지 정렬돼 있는가" 를 객관적으로 답하기 위한 기준 모듈이다.

자매 모듈과의 경계 (중복 없음)
------------------------------
- Phase 407(``icao_utm_conformance``) 은 *ICAO UTM Framework* 라는 단일 조화
  문서에 대한 SDACS *역량* 자가 평가다.
- Phase 470(``standardization_tracker``) 은 SDACS 가 *발신하는* 표준화 *기고*
  (우리 산출물)를 추적한다.
- 본 모듈(462)은 그 둘과 달리 *외부 ISO 표준 문서 자체* 의 발행 동향(어떤 부가
  언제 발행됐고 어떤 부가 개발 중인가)을 추적하고, 표준별 SDACS 정렬을 본다.

근거 (권위 있는 출처, 2026-06 기준 ISO 카탈로그)
----------------------------------------------
ISO/TC 20/SC 16 의 공개 발행/개발 현황을 인용한다(ISO 공식 카탈로그):
- **ISO 21384** 시리즈 — UAS 일반: Part 1(일반 사양, 개발 중)·Part 2(제품 시스템,
  개발 중)·Part 3:2023(운영 절차, 발행)·Part 4:2025(용어, 발행).
- **ISO 23629** 시리즈 — UTM(무인 교통 관리): Part 5:2023(기능 구조)·Part
  7:2021(공간 데이터 모델)·Part 8:2023(원격 식별)·Part 9:2023(USP–사용자
  인터페이스)·Part 12:2022(UTM 서비스 공급자 요건) — 모두 발행.

정직 공시 (CLAUDE.md)
--------------------
1. 본 모듈은 표준 *동향 추적* 이며 ISO 적합성 인증이 아니다. 표준 발행 상태는
   인용 시점(2026-06) ISO 카탈로그 스냅샷이며, 시리즈 일부만(검증된 항목만)
   추적한다 — 전수가 아님을 명시한다.
2. ``alignment`` 는 3값(``aligned``·``partial``·``none``)으로 SDACS 의 해당 표준
   주제 정렬도를 나타낸다. 이는 공식 적합성 주장이 아닌 *기능적 자가 평가* 다.
3. ``sdacs_module`` 은 해당 표준 주제를 *실제로* 다루는 리포 내 모듈 경로다.
   ``alignment`` 가 ``none`` 이면 반드시 ``None`` 이고, 그 외(``aligned``/
   ``partial``)면 반드시 실재 모듈을 인용한다 — 모듈 없는 정렬 주장을 구조적으로
   금지한다(테스트가 디스크 실재를 강제). 본 모듈의 가치는 정렬 주장보다 *미정렬
   표준의 가시화* 에 있다.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/iso_tc20_sc16_tracker.py --matrix        # 전체 추적 매트릭스
    python simulation/iso_tc20_sc16_tracker.py --report        # 동향·정렬 요약
    python simulation/iso_tc20_sc16_tracker.py --series 23629  # 시리즈별 표준
    python simulation/iso_tc20_sc16_tracker.py --published     # 발행된 표준만
    python simulation/iso_tc20_sc16_tracker.py --gaps          # 미정렬(none) 표준
"""
from __future__ import annotations

import argparse
import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

# ISO 표준 개발 단계 (추적 대상 3값). 카탈로그 스냅샷 기준.
STAGES: tuple[str, ...] = ("UNDER_DEVELOPMENT", "PUBLISHED", "WITHDRAWN")

# SDACS 정렬 상태 (3값). aligned=정렬, partial=부분, none=미정렬.
ALIGNMENTS: tuple[str, ...] = ("aligned", "partial", "none")

# 가중 점수: 정렬 1.0, 부분 0.5, 미정렬 0.0.
_ALIGNMENT_WEIGHT: dict[str, float] = {"aligned": 1.0, "partial": 0.5, "none": 0.0}

# 발행 표준 지정명에 포함돼야 하는 발행 연도(:YYYY) 패턴.
# 정확히 4자리(5자리 연속 거부) — `\b` 대신 음수 lookahead 로 의도를 직접 표현.
_PUBLISHED_YEAR = re.compile(r":\d{4}(?!\d)")


@dataclass(frozen=True)
class IsoStandard:
    """ISO/TC 20/SC 16 표준 한 건의 추적 항목(불변)."""

    standard_id: str            # 안정 식별자 (예: 'ISO-23629-5')
    designation: str            # 공식 지정명 (예: 'ISO 23629-5:2023')
    title: str                  # 표준 제목
    series: str                 # 시리즈 번호 (예: '21384', '23629')
    stage: str                  # PUBLISHED·UNDER_DEVELOPMENT·WITHDRAWN
    alignment: str              # aligned·partial·none
    sdacs_module: str | None    # 정렬 모듈 경로 (none 이면 None)
    summary: str                # 한 줄 설명

    def __post_init__(self) -> None:
        if not self.standard_id or self.standard_id != self.standard_id.strip():
            raise ValueError("standard_id must be non-empty and unpadded")
        if " " in self.standard_id:
            raise ValueError("standard_id must not contain internal spaces")
        if not self.designation or not self.designation.strip():
            raise ValueError("designation must be a non-empty string")
        if not self.title or not self.title.strip():
            raise ValueError("title must be a non-empty string")
        if not self.summary or not self.summary.strip():
            raise ValueError("summary must be a non-empty string")
        if not self.series or not self.series.isdigit():
            raise ValueError(f"series must be digits, got {self.series!r}")
        if self.series not in self.designation:
            raise ValueError(
                f"designation {self.designation!r} must reference series {self.series!r}"
            )
        if self.stage not in STAGES:
            raise ValueError(f"stage must be one of {STAGES}, got {self.stage!r}")
        if self.alignment not in ALIGNMENTS:
            raise ValueError(
                f"alignment must be one of {ALIGNMENTS}, got {self.alignment!r}"
            )
        # 발행 표준은 지정명에 발행 연도(:YYYY)를 명시해야 한다.
        if self.stage == "PUBLISHED" and not _PUBLISHED_YEAR.search(self.designation):
            raise ValueError(
                f"PUBLISHED designation must carry a year (:YYYY): {self.designation!r}"
            )
        # 정직성 결속: none ⟺ 모듈 없음. 정렬/부분은 반드시 실재 모듈 인용.
        if self.alignment == "none":
            if self.sdacs_module is not None:
                raise ValueError("a 'none' alignment must not cite an sdacs_module")
        else:
            if self.sdacs_module is None or not self.sdacs_module.strip():
                raise ValueError(
                    f"alignment {self.alignment!r} must cite a non-empty sdacs_module"
                )

    @property
    def is_published(self) -> bool:
        """발행 완료 여부."""
        return self.stage == "PUBLISHED"

    @property
    def is_unaligned(self) -> bool:
        """SDACS 미정렬(none) 여부."""
        return self.alignment == "none"

    @property
    def weight(self) -> float:
        """가중 점수 기여 (aligned 1.0·partial 0.5·none 0.0)."""
        return _ALIGNMENT_WEIGHT[self.alignment]


# ISO/TC 20/SC 16 표준 추적 레지스트리 (정본, 결정적 순서).
# 발행 상태는 2026-06 ISO 카탈로그 스냅샷. sdacs_module 은 리포 실재 모듈(none=None).
ISO_STANDARDS: tuple[IsoStandard, ...] = (
    # --- ISO 21384 시리즈 (UAS 일반) -----------------------------------------
    IsoStandard(
        "ISO-21384-1", "ISO/DIS 21384-1", "Unmanned aircraft systems — Part 1: General specification",
        "21384", "UNDER_DEVELOPMENT", "none", None,
        "UAS 일반 사양 — 개발 중(DIS). 기체 일반 사양은 SDACS(관제 계층) 범위 밖 (미정렬)",
    ),
    IsoStandard(
        "ISO-21384-2", "ISO/CD 21384-2", "Unmanned aircraft systems — Part 2: Product systems",
        "21384", "UNDER_DEVELOPMENT", "none", None,
        "UAS 제품 시스템(기체 구성품) — 개발 중. 에어프레임 제품 표준은 SDACS 범위 밖 (미정렬)",
    ),
    IsoStandard(
        "ISO-21384-3", "ISO 21384-3:2023", "Unmanned aircraft systems — Part 3: Operational procedures",
        "21384", "PUBLISHED", "partial", "simulation/sora_category.py",
        "운영 절차(안전 운용 요건) — SORA 운영 위험 분류 모듈과 부분 정렬, 전 절차 자동화는 부분",
    ),
    IsoStandard(
        "ISO-21384-4", "ISO 21384-4:2025", "Uncrewed aircraft systems — Part 4: Vocabulary",
        "21384", "PUBLISHED", "none", None,
        "용어·정의 — SDACS 전용 용어 사전 모듈 없음 (미정렬, 갭)",
    ),
    # --- ISO 23629 시리즈 (UTM) ----------------------------------------------
    IsoStandard(
        "ISO-23629-5", "ISO 23629-5:2023", "UAS traffic management (UTM) — Part 5: UTM functional structure",
        "23629", "PUBLISHED", "aligned", "simulation/uspace_service_map.py",
        "UTM 기능 구조 — U-space 서비스 매핑이 기능 분해를 SDACS 모듈에 정렬",
    ),
    IsoStandard(
        "ISO-23629-7", "ISO 23629-7:2021", "UAS traffic management (UTM) — Part 7: Data model for spatial data",
        "23629", "PUBLISHED", "partial", "simulation/geo_zones.py",
        "공간 데이터 모델 — UTM zone·좌표계 결정적 변환 모듈과 부분 정렬",
    ),
    IsoStandard(
        "ISO-23629-8", "ISO 23629-8:2023", "UAS traffic management (UTM) — Part 8: Remote identification",
        "23629", "PUBLISHED", "aligned", "simulation/remote_id.py",
        "원격 식별 — Remote ID 실시간 식별·방송 모듈에 정렬",
    ),
    IsoStandard(
        "ISO-23629-9", "ISO 23629-9:2023",
        "UAS traffic management (UTM) — Part 9: Interface between UTM service providers and users",
        "23629", "PUBLISHED", "partial", "simulation/operational_intent.py",
        "USP–사용자 인터페이스 — 운영 의도 4D 교환 모듈과 부분 정렬, 전 인터페이스 규약은 부분",
    ),
    IsoStandard(
        "ISO-23629-12", "ISO 23629-12:2022",
        "UAS traffic management (UTM) — Part 12: Requirements for UTM service providers",
        "23629", "PUBLISHED", "partial", "simulation/icao_utm_conformance.py",
        "UTM 서비스 공급자 요건 — UTM 역량 자가 평가 매트릭스와 부분 정렬",
    ),
)


# 로드 시점 무결성 게이트 — 중복 식별자를 임포트 시 즉시 차단(테스트보다 이른 단계).
_REGISTRY_IDS = [s.standard_id for s in ISO_STANDARDS]
assert len(_REGISTRY_IDS) == len(set(_REGISTRY_IDS)), "duplicate standard_id in ISO_STANDARDS"

# 레지스트리에 실재하는 시리즈 번호 (정렬). 조회 검증의 정본 집합.
SERIES: tuple[str, ...] = tuple(sorted({s.series for s in ISO_STANDARDS}))


@dataclass(frozen=True)
class TrackerReport:
    """ISO/TC 20/SC 16 표준 동향·정렬 요약."""

    total: int
    published: int
    under_development: int
    withdrawn: int
    aligned: int
    partial: int
    none: int
    by_series: Mapping[str, int]  # series -> count, read-only

    def __post_init__(self) -> None:
        # by_series 를 항상 읽기 전용 뷰로 동결 — 직접 생성 시에도 내부 변형 차단.
        if not isinstance(self.by_series, MappingProxyType):
            object.__setattr__(self, "by_series", MappingProxyType(dict(self.by_series)))
        counts = (self.total, self.published, self.under_development, self.withdrawn,
                  self.aligned, self.partial, self.none)
        if min(counts) < 0:
            raise ValueError("counts must be non-negative")
        if self.published + self.under_development + self.withdrawn != self.total:
            raise ValueError(
                f"published ({self.published}) + under_development "
                f"({self.under_development}) + withdrawn ({self.withdrawn}) "
                f"!= total ({self.total})"
            )
        if self.aligned + self.partial + self.none != self.total:
            raise ValueError(
                f"aligned ({self.aligned}) + partial ({self.partial}) + "
                f"none ({self.none}) != total ({self.total})"
            )
        # total>0 이면 by_series 는 반드시 합이 total 과 일치하는 완전한 투영이어야
        # 한다 — 빈 dict 도 거부(total==0 인 빈 리포트만 면제).
        if self.total > 0 and sum(self.by_series.values()) != self.total:
            raise ValueError(
                f"by_series sum ({sum(self.by_series.values())}) != total ({self.total})"
            )

    @property
    def alignment_score_pct(self) -> float:
        """가중 정렬 점수 (%) — aligned 1.0·partial 0.5·none 0.0."""
        if not self.total:
            return 0.0
        score = self.aligned * 1.0 + self.partial * 0.5
        return 100.0 * score / self.total

    @property
    def published_pct(self) -> float:
        """발행 완료 비율 (%)."""
        if not self.total:
            return 0.0
        return 100.0 * self.published / self.total


def find_standard(standard_id: str) -> IsoStandard:
    """식별자로 표준을 조회한다. 없으면 KeyError."""
    for std in ISO_STANDARDS:
        if std.standard_id == standard_id:
            return std
    raise KeyError(f"unknown ISO standard: {standard_id!r}")


def standards_by_series(series: str) -> tuple[IsoStandard, ...]:
    """시리즈 번호에 속한 표준을 식별자 정렬로 반환한다.

    오타로 인한 위양성 빈 결과를 막기 위해, 알 수 없는 시리즈는 조용히 빈
    튜플을 반환하지 않고 ValueError 를 던진다(``standards_by_stage`` 와 대칭).
    """
    if series not in SERIES:
        raise ValueError(f"series must be one of {SERIES}, got {series!r}")
    return tuple(
        sorted((s for s in ISO_STANDARDS if s.series == series),
               key=lambda s: s.standard_id)
    )


def standards_by_stage(stage: str) -> tuple[IsoStandard, ...]:
    """개발 단계별 표준을 식별자 정렬로 반환한다."""
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}, got {stage!r}")
    return tuple(
        sorted((s for s in ISO_STANDARDS if s.stage == stage),
               key=lambda s: s.standard_id)
    )


def published_standards() -> tuple[IsoStandard, ...]:
    """발행 완료(PUBLISHED) 표준을 식별자 정렬로 반환한다."""
    return standards_by_stage("PUBLISHED")


def gaps() -> tuple[IsoStandard, ...]:
    """SDACS 미정렬(none) 표준을 식별자 정렬로 반환한다."""
    return tuple(
        sorted((s for s in ISO_STANDARDS if s.is_unaligned), key=lambda s: s.standard_id)
    )


def tracker_report() -> TrackerReport:
    """전체 동향·정렬 현황을 집계한 결정적 리포트를 생성한다."""
    by_series: dict[str, int] = {}
    for std in ISO_STANDARDS:
        by_series[std.series] = by_series.get(std.series, 0) + 1
    return TrackerReport(
        total=len(ISO_STANDARDS),
        published=sum(1 for s in ISO_STANDARDS if s.stage == "PUBLISHED"),
        under_development=sum(1 for s in ISO_STANDARDS if s.stage == "UNDER_DEVELOPMENT"),
        withdrawn=sum(1 for s in ISO_STANDARDS if s.stage == "WITHDRAWN"),
        aligned=sum(1 for s in ISO_STANDARDS if s.alignment == "aligned"),
        partial=sum(1 for s in ISO_STANDARDS if s.alignment == "partial"),
        none=sum(1 for s in ISO_STANDARDS if s.alignment == "none"),
        by_series=MappingProxyType(by_series),
    )


def tracking_matrix() -> tuple[dict[str, object], ...]:
    """도구 간 교환용 추적 매트릭스를 (시리즈, 식별자) 정렬 행으로 반환한다."""
    ordered = sorted(ISO_STANDARDS, key=lambda s: (s.series, s.standard_id))
    return tuple(
        {
            "standard_id": s.standard_id,
            "designation": s.designation,
            "title": s.title,
            "series": s.series,
            "stage": s.stage,
            "alignment": s.alignment,
            "sdacs_module": s.sdacs_module,
        }
        for s in ordered
    )


_STAGE_MARK: dict[str, str] = {
    "PUBLISHED": "발행",
    "UNDER_DEVELOPMENT": "개발중",
    "WITHDRAWN": "폐기",
}
_ALIGN_MARK: dict[str, str] = {"aligned": "✓", "partial": "◐", "none": "✗(갭)"}


def _format_matrix() -> str:
    lines = ["ISO/TC 20/SC 16 (UAS) 표준 추적 매트릭스", ""]
    for row in tracking_matrix():
        stage = _STAGE_MARK[str(row["stage"])]
        align = _ALIGN_MARK[str(row["alignment"])]
        module = row["sdacs_module"] or "—"
        lines.append(f"[{stage:6}] {align:5} {row['designation']}")
        lines.append(f"      {row['title']}")
        lines.append(f"      → {module}")
    return "\n".join(lines)


def _format_report() -> str:
    r = tracker_report()
    lines = [
        "ISO/TC 20/SC 16 표준 동향·정렬 요약",
        "",
        f"발행 현황   : 발행 {r.published} · 개발중 {r.under_development} · "
        f"폐기 {r.withdrawn} / 총 {r.total} ({r.published_pct:.0f}% 발행)",
        f"정렬 점수   : {r.alignment_score_pct:.0f}% "
        f"(정렬 {r.aligned} · 부분 {r.partial} · 미정렬 {r.none})",
        "",
        "시리즈별 표준 수:",
    ]
    for series in sorted(r.by_series):
        lines.append(f"  ISO {series}: {r.by_series[series]}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ISO/TC 20/SC 16 (UAS) 표준 동향 추적 매트릭스 (ODYSSEY Phase 462)"
    )
    parser.add_argument("--matrix", action="store_true", help="전체 추적 매트릭스 출력")
    parser.add_argument("--report", action="store_true", help="동향·정렬 요약 출력")
    parser.add_argument("--series", choices=SERIES, help="시리즈별 표준 출력 (예: 23629)")
    parser.add_argument("--published", action="store_true", help="발행된 표준만 출력")
    parser.add_argument("--gaps", action="store_true", help="미정렬(none) 표준 출력")
    args = parser.parse_args(argv)

    if args.matrix:
        print(_format_matrix())
    elif args.report:
        print(_format_report())
    elif args.series:
        for std in standards_by_series(args.series):
            print(f"{std.designation} [{std.stage}/{std.alignment}]: {std.title}")
    elif args.published:
        for std in published_standards():
            print(f"{std.designation}: {std.title} → {std.sdacs_module or '—'}")
    elif args.gaps:
        for std in gaps():
            print(f"{std.designation}: {std.summary}")
    else:
        print(_format_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
