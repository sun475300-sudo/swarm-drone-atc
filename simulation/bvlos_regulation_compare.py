"""ODYSSEY Phase 409 — 다국 BVLOS 규제 비교 (한·미·EU·일).

드론 BVLOS(Beyond Visual Line of Sight, 가시권 밖 비행) 운용을 허가하는
한국·미국·EU·일본 4개 관할의 규제 요건을 **동일한 비교 축(axis)** 으로 정렬해
객관적으로 대조하는 결정적 데이터 모듈이다. ODYSSEY 국제 확장에서 "SDACS 가
어느 관할의 BVLOS 요건을 어디까지 자가 평가/지원하는가" 를 답하기 위한 기준선이며,
Phase 402(FAA UTM)·403(EASA 카테고리)·407(ICAO) 자가 평가와 비경쟁(상호 보완)이다.

근거 (공개 규제 문서)
--------------------
- **한국(KR)**: 항공안전법 §129·시행규칙 §312의2 — BVLOS 는 *특별비행승인*
  (국토교통부, case-by-case). 포괄 BVLOS 규칙 부재, K-드론시스템(K-UTM) 실증.
- **미국(US)**: 14 CFR Part 107(§107.31 BVLOS) + Waiver, Remote ID 14 CFR Part 89.
  포괄 BVLOS 규칙 *Part 108* 은 NPRM(제안) 단계(본 스냅샷 시점 미발효).
- **EU**: Reg. (EU) 2019/947 — Open/Specific/Certified. BVLOS 는 통상 *Specific*
  카테고리(SORA 또는 STS-02 표준 시나리오/PDRA + 운영 허가). U-space 2021/664.
- **일본(JP)**: 改正航空法 — *Level 4*(제3자 상공 BVLOS) 2022-12 발효. 機体認証
  (1종) + 操縦ライセンス(1등 무인항공기조종사) + 운항허가 3중 요건.

정직 공시 (CLAUDE.md)
--------------------
- 본 모듈은 규제의 *기능적 요약* 이며 법률 자문이 아니다. 각 요건은 ``citation``
  으로 권위 있는 규제 문서를 명시하고, 관할별 ``as_of`` 스냅샷 시점을 보유한다
  (규제는 개정되므로 시점 명시 필수).
- ``sdacs_support`` 는 해당 관할 요건의 *자가 평가/지원* 에 실재로 쓰이는 리포
  모듈 경로다 — 대응 모듈이 없으면 ``None`` 으로 **갭** 을 정직 표면화한다
  (``test_cited_sdacs_modules_exist_on_disk`` 가 디스크 실재를 강제).

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/bvlos_regulation_compare.py --matrix          # 전체 비교 매트릭스
    python simulation/bvlos_regulation_compare.py --jurisdiction KR # 관할별 요건
    python simulation/bvlos_regulation_compare.py --dimension remote_id  # 축별 대조
    python simulation/bvlos_regulation_compare.py --support         # SDACS 지원 갭
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TypedDict

# 비교 축(axis) — 모든 관할에 동일하게 적용되는 BVLOS 요건 차원.
# (id, 한 줄 라벨) 순서가 매트릭스 행 정렬 순서를 결정한다.
DIMENSIONS: tuple[tuple[str, str], ...] = (
    ("bvlos_pathway", "BVLOS 법적 허가 경로"),
    ("risk_assessment", "운영 위험 평가 방식"),
    ("remote_id", "Remote ID(원격 식별) 요건"),
    ("pilot_competency", "조종 자격(라이선스) 요건"),
    ("aircraft_cert", "기체 인증 요건"),
    ("over_populated", "인구 밀집지/제3자 상공 BVLOS"),
)

_DIMENSION_IDS: tuple[str, ...] = tuple(d for d, _ in DIMENSIONS)

# 관할 코드 → 표시 명칭(정렬은 코드 사전식). 사전식 정렬 불변(매트릭스 열 순서 고정).
JURISDICTION_CODES: tuple[str, ...] = ("EU", "JP", "KR", "US")
assert list(JURISDICTION_CODES) == sorted(JURISDICTION_CODES), (
    "JURISDICTION_CODES must stay alphabetically sorted"
)


@dataclass(frozen=True)
class BvlosRequirement:
    """한 관할의 한 비교 축에 대한 BVLOS 요건."""

    dimension: str   # 비교 축 id (DIMENSIONS 중 하나)
    value: str       # 해당 관할의 요건 요약
    citation: str    # 권위 있는 규제 문서·조항

    def __post_init__(self) -> None:
        if self.dimension not in _DIMENSION_IDS:
            raise ValueError(
                f"dimension must be one of {_DIMENSION_IDS}, got {self.dimension!r}"
            )
        if not self.value or not self.value.strip():
            raise ValueError("value must be a non-empty string")
        if not self.citation or not self.citation.strip():
            raise ValueError("citation must be a non-empty string")


@dataclass(frozen=True)
class JurisdictionRegulation:
    """한 관할의 BVLOS 규제 프로파일."""

    code: str          # 'KR'·'US'·'EU'·'JP'
    name: str          # 관할 표시 명칭
    framework: str     # 1차 법적 프레임워크
    authority: str     # 규제 당국
    as_of: str         # 규제 스냅샷 시점 'YYYY-MM'
    requirements: tuple[BvlosRequirement, ...]
    sdacs_support: str | None  # 자가 평가/지원 리포 모듈 경로 (없으면 갭)

    def __post_init__(self) -> None:
        if self.code not in JURISDICTION_CODES:
            raise ValueError(
                f"code must be one of {JURISDICTION_CODES}, got {self.code!r}"
            )
        for field_name in ("name", "framework", "authority"):
            if not getattr(self, field_name) or not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        # as_of 는 'YYYY-MM' 형식 + 월 01-12 (규제 시점 명시 강제).
        parts = self.as_of.split("-")
        if (len(parts) != 2 or not (parts[0].isdigit() and parts[1].isdigit())
                or not (1 <= int(parts[1]) <= 12)):
            raise ValueError(
                f"as_of must be 'YYYY-MM' with month 01-12, got {self.as_of!r}"
            )
        # 모든 비교 축을 정확히 1회씩 보유해야 매트릭스가 정렬된다(빈칸·중복 금지).
        dims = [r.dimension for r in self.requirements]
        if sorted(dims) != sorted(_DIMENSION_IDS):
            raise ValueError(
                f"{self.code} requirements must cover each dimension exactly once; "
                f"got {sorted(dims)}"
            )
        if self.sdacs_support is not None and not self.sdacs_support.strip():
            raise ValueError("sdacs_support must be None or a non-empty path")

    @property
    def is_supported(self) -> bool:
        """SDACS 자가 평가/지원 모듈이 있으면 True (갭이 아니면 True)."""
        return self.sdacs_support is not None

    def requirement(self, dimension: str) -> BvlosRequirement:
        """비교 축으로 이 관할의 요건을 조회한다. 없으면 KeyError."""
        for req in self.requirements:
            if req.dimension == dimension:
                return req
        raise KeyError(f"{self.code} has no requirement for dimension {dimension!r}")


def _reqs(*items: tuple[str, str, str]) -> tuple[BvlosRequirement, ...]:
    """(dimension, value, citation) 튜플들을 요건 객체로 변환한다."""
    return tuple(BvlosRequirement(d, v, c) for d, v, c in items)


# 다국 BVLOS 규제 카탈로그 (정본). 요건은 공개 규제 문서 인용 기반.
REGULATIONS: tuple[JurisdictionRegulation, ...] = (
    JurisdictionRegulation(
        "KR", "대한민국", "항공안전법 + 특별비행승인",
        "국토교통부(MOLIT)", "2026-06",
        _reqs(
            ("bvlos_pathway",
             "포괄 규칙 부재 — 건별 특별비행승인 필요 (K-드론시스템 실증)",
             "항공안전법 §129, 시행규칙 §312의2"),
            ("risk_assessment",
             "특별비행승인 신청 시 안전성 검토(비행계획·안전관리)",
             "국토교통부 특별비행승인 운영지침"),
            ("remote_id",
             "기체 신고·식별 의무(원격 식별 단계적 도입)",
             "항공안전법 §122 드론 기체신고"),
            ("pilot_competency",
             "초경량비행장치 조종자 증명(자체중량 구간별)",
             "항공안전법 §125 조종자 증명"),
            ("aircraft_cert",
             "안전성 인증(최대이륙중량 25kg 초과 의무)",
             "항공안전법 §124 안전성 인증"),
            ("over_populated",
             "인구밀집지역 비행은 특별비행승인 + 야간/고밀도 추가 심사",
             "항공안전법 시행규칙 §310 비행승인"),
        ),
        "simulation/special_flight_approval.py",
    ),
    JurisdictionRegulation(
        "US", "미국", "14 CFR Part 107 + Waiver (Part 108 NPRM)",
        "FAA", "2026-06",
        _reqs(
            ("bvlos_pathway",
             "§107.31 BVLOS 금지 → §107.200 Waiver 로 면제 (Part 108 제안 단계)",
             "14 CFR §107.31, §107.205(b)"),
            ("risk_assessment",
             "Waiver 신청 시 안전 사례(safety case)·완화 수단 제출",
             "FAA Waiver Safety Explanation Guidelines"),
            ("remote_id",
             "Remote ID 의무 (Standard·Broadcast Module·FRIA)",
             "14 CFR Part 89"),
            ("pilot_competency",
             "Remote Pilot Certificate (Part 107 지식시험)",
             "14 CFR §107.61"),
            ("aircraft_cert",
             "통상 형식인증 면제(<55 lb), Part 108 BVLOS 시 기체 적격성 요구 제안",
             "14 CFR Part 107 / Part 108 NPRM"),
            ("over_populated",
             "Operations Over People 규칙 4 범주(Category 1-4)",
             "14 CFR §107.100-.140 (Subpart D)"),
        ),
        "simulation/flight_plan_filing.py",
    ),
    JurisdictionRegulation(
        "EU", "유럽연합", "Reg. (EU) 2019/947 (Open/Specific/Certified)",
        "EASA", "2026-06",
        _reqs(
            ("bvlos_pathway",
             "통상 Specific 카테고리 — SORA 또는 STS-02/PDRA + 운영 허가",
             "Reg. (EU) 2019/947 Art.5, Annex STS-02"),
            ("risk_assessment",
             "SORA(JARUS) 또는 사전정의 위험평가(PDRA) 의무",
             "JARUS SORA v2.0 / AMC1 Art.11"),
            ("remote_id",
             "Direct Remote ID + Network Identification(U-space)",
             "Reg. (EU) 2019/945 Part 6, 2021/664"),
            ("pilot_competency",
             "Specific 카테고리 원격조종사 이론·실기 역량 증명",
             "Reg. (EU) 2019/947 Art.8, UAS.SPEC.050"),
            ("aircraft_cert",
             "C-class 마킹(C0-C6) 또는 운영 허가 내 기체 적격성",
             "Reg. (EU) 2019/945 Part 1-6"),
            ("over_populated",
             "SORA 지상 위험 등급(iGRC)에 따른 인구밀도 구간 평가",
             "JARUS SORA Ground Risk Class"),
        ),
        "simulation/airspace_class.py",
    ),
    JurisdictionRegulation(
        "JP", "일본", "改正航空法 (Level 4 제도)",
        "国土交通省(MLIT)", "2026-06",
        _reqs(
            ("bvlos_pathway",
             "Level 4(제3자 상공 BVLOS) 2022-12 발효 — 기체인증+라이선스+운항허가",
             "航空法 §132の85 (Level 4)"),
            ("risk_assessment",
             "운항허가 신청 시 비행 매뉴얼·위험 완화 심사",
             "航空法 §132の86 운항 허가·승인"),
            ("remote_id",
             "리모트 ID 의무(기체 등록·발신)",
             "航空法 §131の2 무인항공기 등록"),
            ("pilot_competency",
             "1등 무인항공기조종사 라이선스(Level 4 필수)",
             "航空法 §132の40 기능증명"),
            ("aircraft_cert",
             "기체인증(1종) — Level 4 비행에 필수",
             "航空法 §132の13 기체 인증"),
            ("over_populated",
             "제3자 상공 비행은 1종 기체+1등 라이선스+운항허가 3중 요건",
             "航空法 §132の85 (Level 4 요건)"),
        ),
        None,
    ),
)


def jurisdictions() -> tuple[JurisdictionRegulation, ...]:
    """관할 규제를 코드 사전식 정렬로 반환한다."""
    return tuple(sorted(REGULATIONS, key=lambda j: j.code))


def find_jurisdiction(code: str) -> JurisdictionRegulation:
    """관할 코드로 규제를 조회한다. 없으면 KeyError."""
    for reg in REGULATIONS:
        if reg.code == code:
            return reg
    raise KeyError(f"unknown jurisdiction code: {code!r}")


def dimension_label(dimension: str) -> str:
    """비교 축 id 의 한 줄 라벨을 반환한다. 없으면 KeyError."""
    for dim, label in DIMENSIONS:
        if dim == dimension:
            return label
    raise KeyError(f"unknown dimension: {dimension!r}")


def compare_dimension(dimension: str) -> Mapping[str, BvlosRequirement]:
    """한 비교 축에 대해 {관할코드: 요건} 읽기 전용 매핑을 반환한다(전 관할 정렬)."""
    if dimension not in _DIMENSION_IDS:
        raise ValueError(f"unknown dimension: {dimension!r}")
    return MappingProxyType(
        {reg.code: reg.requirement(dimension) for reg in jurisdictions()}
    )


class MatrixCell(TypedDict):
    """한 관할의 한 축 셀 (요건 요약 + 인용)."""

    value: str
    citation: str


class MatrixRow(TypedDict):
    """비교 매트릭스 한 행 (한 축, 전 관할)."""

    dimension: str
    label: str
    jurisdictions: Mapping[str, MatrixCell]


def comparison_matrix() -> tuple[MatrixRow, ...]:
    """도구 간 교환용 비교 매트릭스를 (축 정렬) 행으로 반환한다.

    각 행은 한 비교 축에 대한 전 관할 요건/인용을 담는다. 반환 구조는
    읽기 전용(``MappingProxyType``)이라 하류 소비자가 공유 상태를 변조할 수 없다.
    """
    rows: list[MatrixRow] = []
    for dim in _DIMENSION_IDS:
        cells: dict[str, MatrixCell] = {}
        for reg in jurisdictions():
            req = reg.requirement(dim)
            cells[reg.code] = {"value": req.value, "citation": req.citation}
        rows.append({
            "dimension": dim,
            "label": dimension_label(dim),
            "jurisdictions": MappingProxyType(cells),
        })
    return tuple(rows)


@dataclass(frozen=True)
class SupportReport:
    """SDACS 자가 평가/지원 커버리지 요약."""

    total: int
    supported: int
    gaps: int

    def __post_init__(self) -> None:
        if min(self.total, self.supported, self.gaps) < 0:
            raise ValueError("counts must be non-negative")
        if self.supported + self.gaps != self.total:
            raise ValueError(
                f"supported ({self.supported}) + gaps ({self.gaps}) != total ({self.total})"
            )

    @property
    def support_pct(self) -> float:
        """SDACS 지원 관할 비율 (%)."""
        return 100.0 * self.supported / self.total if self.total else 0.0


def support_report() -> SupportReport:
    """관할별 SDACS 지원 현황을 집계한 결정적 리포트를 생성한다."""
    total = len(REGULATIONS)
    supported = sum(1 for r in REGULATIONS if r.is_supported)
    return SupportReport(total=total, supported=supported, gaps=total - supported)


def cited_sdacs_modules() -> tuple[str, ...]:
    """인용된 SDACS 지원 모듈 경로를 중복 제거·정렬로 반환한다(None 제외)."""
    return tuple(sorted({r.sdacs_support for r in REGULATIONS if r.sdacs_support}))


def _format_matrix() -> str:
    lines = ["다국 BVLOS 규제 비교 매트릭스 (한·미·EU·일)", ""]
    codes = [reg.code for reg in jurisdictions()]
    for row in comparison_matrix():
        lines.append(f"■ {row['label']} [{row['dimension']}]")
        cells = row["jurisdictions"]
        for code in codes:
            cell = cells[code]
            lines.append(f"   {code}: {cell['value']}")
            lines.append(f"       ↳ {cell['citation']}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _format_support() -> str:
    r = support_report()
    lines = [
        "SDACS BVLOS 자가 평가/지원 커버리지",
        "",
        f"지원 관할: {r.supported}/{r.total} ({r.support_pct:.0f}%)",
        "",
    ]
    for reg in jurisdictions():
        mark = "✓" if reg.is_supported else "✗(갭)"
        module = reg.sdacs_support or "—"
        lines.append(f"  {mark} {reg.code} {reg.name}: {module}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="다국 BVLOS 규제 비교 (ODYSSEY Phase 409)"
    )
    parser.add_argument("--matrix", action="store_true", help="전체 비교 매트릭스 출력")
    parser.add_argument(
        "--jurisdiction", choices=JURISDICTION_CODES, help="관할별 요건 출력"
    )
    parser.add_argument(
        "--dimension", choices=_DIMENSION_IDS, help="비교 축별 전 관할 대조 출력"
    )
    parser.add_argument("--support", action="store_true", help="SDACS 지원 갭 출력")
    args = parser.parse_args(argv)

    if args.matrix:
        print(_format_matrix())
    elif args.jurisdiction:
        reg = find_jurisdiction(args.jurisdiction)
        print(f"{reg.code} {reg.name} — {reg.framework} ({reg.authority}, {reg.as_of})")
        for dim in _DIMENSION_IDS:
            req = reg.requirement(dim)
            print(f"  [{dimension_label(dim)}] {req.value}")
            print(f"      ↳ {req.citation}")
    elif args.dimension:
        print(f"■ {dimension_label(args.dimension)} [{args.dimension}]")
        for code, req in compare_dimension(args.dimension).items():
            print(f"   {code}: {req.value}")
            print(f"       ↳ {req.citation}")
    elif args.support:
        print(_format_support())
    else:
        print(_format_support())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
