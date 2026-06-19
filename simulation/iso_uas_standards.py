"""ODYSSEY Phase 462 — ISO/TC 20/SC 16 (UAS) 표준 동향 추적 매트릭스.

국제표준화기구(ISO) 항공우주기술위원회(TC 20) 산하 무인항공기시스템 분과위원회
(SC 16, *Unmanned aircraft systems*)가 발행하는 UAS 표준군을 추적하고, 각 표준의
*주제* 를 SDACS 의 어느 모듈이 다루는지 결정적으로 대응시키는 커버리지 매트릭스다.

Phase 470(표준화 기고 추적 대시보드)이 SDACS 가 *내보내는* 자체 기고를 추적한다면,
본 모듈은 그 반대 방향 — SDACS 가 *마주하는* 외부 ISO 표준 지형을 추적하고, 그
지형 대비 현재 시스템의 주제 커버리지를 정직하게 표면화한다. Phase 407(ICAO UTM
Framework 적합성)이 단일 SDO 의 운영자 여정 축을 평가했다면, 본 모듈은 ISO SC 16
이라는 *다른 SDO* 의 표준 문서 축으로 같은 자산을 재조명한다.

정직 공시 (CLAUDE.md)
--------------------
1. 본 모듈은 *주제 정렬(thematic alignment)* 추적이며 ISO 공식 적합성 인증이 아니다.
   ``coverage`` 는 "이 표준의 주제를 SDACS 의 어느 모듈이 다루는가" 일 뿐, 표준의
   세부 요구사항을 인증 수준으로 충족한다는 주장이 아니다.
2. 표준 지정번호·발행 성숙도는 지식 기준일(:data:`AS_OF`) 시점 스냅샷이다. ISO
   카탈로그는 갱신되므로(개정·발행·폐지) 인용 전 공식 카탈로그로 검증해야 한다.
   본 모듈의 가치는 정확한 발행 연도보다 *어떤 표준 주제가 미커버(gap)인지* 의
   가시화에 있다.
3. ``sdacs_module`` 은 그 주제를 *실제로* 다루는 리포 내 모듈 경로다. ``coverage``
   가 ``none`` 이면 반드시 ``None`` 이고, 그 외(``full``/``partial``)면 반드시 실재
   모듈을 인용한다 — 모듈 없는 커버리지 주장을 구조적으로 금지한다(``validate``
   가 디스크 실재를 강제).

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python -m simulation.iso_uas_standards --matrix     # 전체 추적 매트릭스
    python -m simulation.iso_uas_standards --report     # 커버리지 요약
    python -m simulation.iso_uas_standards --gaps        # 미커버(gap) 표준
    python -m simulation.iso_uas_standards --category utm  # 범주별 표준
    python -m simulation.iso_uas_standards --validate    # 레지스트리 정합성
    python -m simulation.iso_uas_standards --manifest    # 매니페스트(JSON)
    python -m simulation.iso_uas_standards --markdown    # 대시보드(Markdown)
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# 리포 루트 — sdacs_module 경로는 이 기준의 상대 경로로 보관한다.
_REPO_ROOT = Path(__file__).resolve().parent.parent

# 지정번호·성숙도 스냅샷의 기준일. 이후 ISO 카탈로그 갱신은 본 값으로 정직 공시한다.
AS_OF = "2026-06-19"

# ISO/TC 20/SC 16 표준 주제 범주 (분류 축).
CATEGORIES: tuple[str, ...] = (
    "general",      # 일반 시스템 사양
    "product",      # 제품(기체·구성품) 요구사항
    "operations",   # 운영 절차
    "terminology",  # 용어
    "utm",          # UTM(무인기 교통관리)
)

_CATEGORY_NAMES: dict[str, str] = {
    "general": "General (일반 시스템 사양)",
    "product": "Product (기체·구성품 요구사항)",
    "operations": "Operations (운영 절차)",
    "terminology": "Terminology (용어)",
    "utm": "UTM (무인기 교통관리)",
}

# 발행 성숙도 (스냅샷). published=발행, under_development=개발 중.
MATURITIES: tuple[str, ...] = ("published", "under_development")

# 커버리지 상태 (3값). full=완전, partial=부분, none=미커버.
COVERAGE_STATUSES: tuple[str, ...] = ("full", "partial", "none")

# 가중 점수: 완전 1.0, 부분 0.5, 미커버 0.0.
_COVERAGE_WEIGHT: dict[str, float] = {"full": 1.0, "partial": 0.5, "none": 0.0}


@dataclass(frozen=True)
class ISOStandard:
    """단일 ISO/TC 20/SC 16 표준과 SDACS 주제 커버리지의 정의(불변).

    Attributes:
        standard_id: 안정 식별자 (예: ``ISO-21384-3``). 내부 공백 금지.
        designation: ISO 지정번호 표기 (예: ``ISO 21384-3:2023``).
        title: 표준 제목.
        category: CATEGORIES 중 하나.
        maturity: MATURITIES 중 하나 (스냅샷).
        coverage: full·partial·none.
        sdacs_module: 주제를 다루는 리포 내 모듈 경로 (none 이면 None).
        summary: 한 줄 설명.
    """

    standard_id: str
    designation: str
    title: str
    category: str
    maturity: str
    coverage: str
    sdacs_module: str | None
    summary: str

    def __post_init__(self) -> None:
        if not self.standard_id or self.standard_id != self.standard_id.strip():
            raise ValueError("standard_id must be non-empty and unpadded")
        if " " in self.standard_id:
            raise ValueError("standard_id must not contain internal spaces")
        for field_name in ("designation", "title", "summary"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if self.category not in CATEGORIES:
            raise ValueError(f"category must be one of {CATEGORIES}, got {self.category!r}")
        if self.maturity not in MATURITIES:
            raise ValueError(f"maturity must be one of {MATURITIES}, got {self.maturity!r}")
        if self.coverage not in COVERAGE_STATUSES:
            raise ValueError(f"coverage must be one of {COVERAGE_STATUSES}, got {self.coverage!r}")
        # 정직성 결속: none ⟺ 모듈 없음. full/partial 은 반드시 실재 모듈 인용.
        if self.coverage == "none":
            if self.sdacs_module is not None:
                raise ValueError("a 'none' coverage standard must not cite an sdacs_module")
        else:
            if self.sdacs_module is None or not self.sdacs_module.strip():
                raise ValueError(
                    f"coverage {self.coverage!r} must cite a non-empty sdacs_module"
                )

    @property
    def is_gap(self) -> bool:
        """미커버(gap) 여부."""
        return self.coverage == "none"

    @property
    def is_published(self) -> bool:
        """발행된 표준 여부 (개발 중이면 False)."""
        return self.maturity == "published"

    @property
    def weight(self) -> float:
        """가중 점수 기여 (full 1.0·partial 0.5·none 0.0)."""
        return _COVERAGE_WEIGHT[self.coverage]

    def module_path(self) -> Path | None:
        """SDACS 모듈의 절대 경로(없으면 None)."""
        return _REPO_ROOT / self.sdacs_module if self.sdacs_module else None

    def module_exists(self) -> bool:
        """인용한 모듈 파일이 실재하는지 여부(경로 미지정이면 False)."""
        path = self.module_path()
        return path is not None and path.is_file()


# ISO/TC 20/SC 16 표준 ↔ SDACS 주제 커버리지 카탈로그 (정본).
# 지정번호·성숙도는 AS_OF 스냅샷. sdacs_module 은 리포 실재 모듈(none 은 None).
REGISTRY: tuple[ISOStandard, ...] = (
    # --- 21384 시리즈: UAS 일반 ------------------------------------------------
    ISOStandard(
        "ISO-21384-1", "ISO 21384-1", "UAS — Part 1: General specification",
        "general", "published", "none", None,
        "UAS 일반 시스템 사양 — SDACS 는 관제·시뮬레이션 소프트웨어로 기체 전반 "
        "제품 사양을 정의하지 않음 (gap)",
    ),
    ISOStandard(
        "ISO-21384-2", "ISO 21384-2", "UAS — Part 2: UA systems requirements",
        "product", "published", "none", None,
        "기체·구성품 제품 요구사항 — 하드웨어 제품 영역, SDACS 범위 밖 (gap)",
    ),
    ISOStandard(
        "ISO-21384-3", "ISO 21384-3:2023", "UAS — Part 3: Operational procedures",
        "operations", "published", "full",
        "src/airspace_control/controller/airspace_controller.py",
        "운영 절차 — 공역 관제·승인·분리 운영을 AirspaceController 1Hz 로 구현 (핵심 도메인)",
    ),
    ISOStandard(
        "ISO-21384-4", "ISO 21384-4", "UAS — Part 4: Vocabulary",
        "terminology", "published", "none", None,
        "용어 표준 — SDACS 는 ISO 정렬 통제 어휘집을 별도 발행하지 않음 (gap)",
    ),
    # --- 23629 시리즈: UTM -----------------------------------------------------
    ISOStandard(
        "ISO-23629-5", "ISO 23629-5", "UTM — Part 5: UAS Service Provider (USP) functional structure",
        "utm", "published", "partial", "simulation/faa_uss_roles.py",
        "USP 기능 구조 — USS 역할↔SDACS 모듈 적합성 매트릭스로 부분 대응(완전 USP 거버넌스는 부분)",
    ),
    ISOStandard(
        "ISO-23629-7", "ISO 23629-7:2021", "UTM — Part 7: Data model for spatial data",
        "utm", "published", "partial", "simulation/geo_zones.py",
        "공간 데이터 모델 — 좌표계·UTM 그리드 존 결정적 판정으로 부분 대응(완전 데이터 모델은 부분)",
    ),
    ISOStandard(
        "ISO-23629-12", "ISO 23629-12", "UTM — Part 12: Requirements for UTM service providers",
        "utm", "under_development", "partial", "simulation/icao_utm_conformance.py",
        "UTM 서비스 제공자 요구사항 — ICAO UTM 적합성 자가 평가로 부분 대응(ISO 요구 매핑은 부분)",
    ),
)


# 로드 시점 무결성 게이트 — 중복 식별자를 임포트 시 즉시 차단.
_REGISTRY_IDS = [s.standard_id for s in REGISTRY]
assert len(_REGISTRY_IDS) == len(set(_REGISTRY_IDS)), "duplicate standard_id in REGISTRY"


@dataclass(frozen=True)
class ValidationResult:
    """레지스트리 검증 결과. errors 가 비면 정합하다.

    Phase 465/466/470 의 ``ValidationResult`` 와 동일한 계약
    (is_valid·errors·warnings 튜플)을 따른다.
    """

    is_valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    def summary(self) -> str:
        """사람이 읽는 한 줄 요약을 반환한다."""
        if self.is_valid:
            base = "VALID"
        else:
            n = len(self.errors)
            base = f"INVALID ({n} {'error' if n == 1 else 'errors'})"
        if self.warnings:
            n = len(self.warnings)
            base += f" / {n} {'warning' if n == 1 else 'warnings'}"
        return base


def all_standards() -> tuple[ISOStandard, ...]:
    """결정적 순서의 전체 레지스트리를 반환한다."""
    return REGISTRY


def find_standard(standard_id: str) -> ISOStandard:
    """식별자로 표준을 조회한다.

    Raises:
        KeyError: 알 수 없는 식별자.
    """
    for entry in REGISTRY:
        if entry.standard_id == standard_id:
            return entry
    raise KeyError(f"unknown ISO standard: {standard_id!r}")


def standards_by_category(category: str) -> tuple[ISOStandard, ...]:
    """범주에 속한 표준을 식별자 정렬로 반환한다."""
    if category not in CATEGORIES:
        raise ValueError(f"category must be one of {CATEGORIES}, got {category!r}")
    return tuple(
        sorted((s for s in REGISTRY if s.category == category), key=lambda s: s.standard_id)
    )


def standards_by_coverage(coverage: str) -> tuple[ISOStandard, ...]:
    """커버리지 상태별 표준을 식별자 정렬로 반환한다."""
    if coverage not in COVERAGE_STATUSES:
        raise ValueError(f"coverage must be one of {COVERAGE_STATUSES}, got {coverage!r}")
    return tuple(
        sorted((s for s in REGISTRY if s.coverage == coverage), key=lambda s: s.standard_id)
    )


def gaps() -> tuple[ISOStandard, ...]:
    """미커버(none) 표준을 식별자 정렬로 반환한다."""
    return standards_by_coverage("none")


def validate(registry: tuple[ISOStandard, ...] = REGISTRY) -> ValidationResult:
    """레지스트리의 내부 정합성을 결정적으로 검증한다.

    검사 규칙:
        - 식별자 유일 (위반 → error).
        - full/partial 커버리지는 인용 모듈 파일이 실재 (위반 → error).
        - none 커버리지는 모듈 미인용 (dataclass 가 강제하나 이중 확인).
        - 발행(published) 표준이 하나도 없으면 (위반 → warning).
    """
    errors: list[str] = []
    warnings: list[str] = []

    seen: set[str] = set()
    for entry in registry:
        sid = entry.standard_id
        if sid in seen:
            errors.append(f"{sid}: 중복 식별자")
        seen.add(sid)

        if not entry.is_gap and not entry.module_exists():
            errors.append(f"{sid}: 인용 모듈 없음 → {entry.sdacs_module}")
        if entry.is_gap and entry.sdacs_module is not None:
            errors.append(f"{sid}: none 커버리지인데 모듈을 인용함")

    if registry and not any(s.is_published for s in registry):
        warnings.append("발행(published) 표준이 레지스트리에 없음")

    return ValidationResult(
        is_valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def category_rollup(registry: tuple[ISOStandard, ...] = REGISTRY) -> dict[str, int]:
    """범주별 표준 수를 CATEGORIES 순으로 집계한다(0 포함)."""
    counts = {category: 0 for category in CATEGORIES}
    for entry in registry:
        if entry.category in counts:
            counts[entry.category] += 1
    return counts


def coverage_rollup(registry: tuple[ISOStandard, ...] = REGISTRY) -> dict[str, int]:
    """커버리지 상태별 표준 수를 COVERAGE_STATUSES 순으로 집계한다(0 포함)."""
    counts = {status: 0 for status in COVERAGE_STATUSES}
    for entry in registry:
        if entry.coverage in counts:
            counts[entry.coverage] += 1
    return counts


def coverage_score(registry: tuple[ISOStandard, ...] = REGISTRY) -> float:
    """전체 주제 커버리지 점수 [0,1] — 가중 평균(full 1.0·partial 0.5·none 0.0).

    빈 레지스트리는 0.0.
    """
    if not registry:
        return 0.0
    return sum(s.weight for s in registry) / len(registry)


def manifest(registry: tuple[ISOStandard, ...] = REGISTRY) -> dict[str, Any]:
    """JSON 직렬화 가능한 추적 매니페스트를 생성한다."""
    result = validate(registry)
    return {
        "schema": "sdacs-iso-uas-standards-tracker",
        "version": "1.0",
        "as_of": AS_OF,
        "count": len(registry),
        "coverage_score": round(coverage_score(registry), 4),
        "is_valid": result.is_valid,
        "category_rollup": category_rollup(registry),
        "coverage_rollup": coverage_rollup(registry),
        "standards": [
            {
                "standard_id": entry.standard_id,
                "designation": entry.designation,
                "title": entry.title,
                "category": entry.category,
                "maturity": entry.maturity,
                "coverage": entry.coverage,
                "sdacs_module": entry.sdacs_module,
                "module_exists": entry.module_exists(),
            }
            for entry in registry
        ],
    }


def _escape_md(value: str) -> str:
    """Markdown 표 셀에서 파이프를 이스케이프해 표 깨짐을 막는다."""
    return value.replace("|", "\\|")


def markdown_table(registry: tuple[ISOStandard, ...] = REGISTRY) -> str:
    """대시보드용 Markdown 표를 생성한다(결정적)."""
    lines = [
        "| 지정번호 | 제목 | 범주 | 성숙도 | 커버리지 | SDACS 모듈 |",
        "|---|---|---|---|:-:|---|",
    ]
    for entry in registry:
        module = _escape_md(entry.sdacs_module) if entry.sdacs_module else "—"
        lines.append(
            f"| {_escape_md(entry.designation)} | {_escape_md(entry.title)} "
            f"| {entry.category} | {entry.maturity} | {entry.coverage} | {module} |"
        )
    pct = round(coverage_score(registry) * 100, 1)
    lines.append("")
    lines.append(f"**주제 커버리지 점수**: {pct}% ({len(registry)}건, as of {AS_OF})")
    return "\n".join(lines)


_COVERAGE_MARK: dict[str, str] = {"full": "✓", "partial": "◐", "none": "✗(gap)"}


def _format_matrix() -> str:
    lines = [f"ISO/TC 20/SC 16 (UAS) 표준 추적 매트릭스 (as of {AS_OF})", ""]
    for entry in REGISTRY:
        mark = _COVERAGE_MARK[entry.coverage]
        module = entry.sdacs_module or "—"
        lines.append(f"[{entry.category:11}] {mark:7} {entry.designation} — {entry.title}")
        lines.append(f"      → {module}")
    return "\n".join(lines)


def _format_report() -> str:
    cov = coverage_rollup()
    cat = category_rollup()
    pct = coverage_score() * 100
    published = sum(1 for s in REGISTRY if s.is_published)
    lines = [
        f"ISO/TC 20/SC 16 (UAS) 표준 커버리지 요약 (as of {AS_OF})",
        "",
        f"주제 커버리지 : {pct:.0f}% "
        f"(완전 {cov['full']} · 부분 {cov['partial']} · 미커버 {cov['none']} / 총 {len(REGISTRY)})",
        f"발행 표준    : {published}/{len(REGISTRY)} (개발 중 {len(REGISTRY) - published})",
        "",
        "범주별 표준 수:",
    ]
    for category in CATEGORIES:
        lines.append(f"  {category:11}: {cat[category]}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ISO/TC 20/SC 16 (UAS) 표준 동향 추적 매트릭스 (ODYSSEY Phase 462)"
    )
    parser.add_argument("--matrix", action="store_true", help="전체 추적 매트릭스 출력")
    parser.add_argument("--report", action="store_true", help="커버리지 요약 출력")
    parser.add_argument("--gaps", action="store_true", help="미커버(gap) 표준 출력")
    parser.add_argument("--category", choices=CATEGORIES, help="범주별 표준 출력")
    parser.add_argument("--validate", action="store_true", help="레지스트리 정합성 검사")
    parser.add_argument("--manifest", action="store_true", help="매니페스트(JSON) 출력")
    parser.add_argument("--markdown", action="store_true", help="대시보드(Markdown) 출력")
    args = parser.parse_args(argv)

    if args.matrix:
        print(_format_matrix())
    elif args.report:
        print(_format_report())
    elif args.gaps:
        for entry in gaps():
            print(f"[{entry.category}] {entry.designation}: {entry.summary}")
    elif args.category:
        for entry in standards_by_category(args.category):
            print(f"{entry.designation} [{entry.coverage}]: {entry.title}")
    elif args.validate:
        result = validate()
        for err in result.errors:
            print(f"ERROR  {err}", file=sys.stderr)
        for warn in result.warnings:
            print(f"WARN   {warn}")
        print(result.summary())
        return 0 if result.is_valid else 1
    elif args.manifest:
        print(json.dumps(manifest(), ensure_ascii=False, indent=2))
    elif args.markdown:
        print(markdown_table())
    else:
        print(_format_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
