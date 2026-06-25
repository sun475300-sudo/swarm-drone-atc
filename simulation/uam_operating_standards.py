"""GENESIS Phase 313 -- UAM 운용기준 정렬 점검.

한국 도심항공교통(UAM) ConOps 및 국토교통부 운용기준 초안에 대한
SDACS 프로젝트의 기술적 정렬도를 자동 점검합니다.

10개 기준 영역 × 다수 세부 항목에 대해 파일시스템 스캔 기반으로
ALIGNED / PARTIAL / NOT_ALIGNED 상태를 결정적으로 판정합니다.

CLI:
    python simulation/uam_operating_standards.py --check
    python simulation/uam_operating_standards.py --category AIRSPACE
    python simulation/uam_operating_standards.py --categories
    python simulation/uam_operating_standards.py --json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from dataclasses import dataclass
from typing import Any

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

CATEGORIES: tuple[str, ...] = (
    "AIRSPACE",
    "VERTIPORT",
    "VEHICLE_CERT",
    "PILOT",
    "WEATHER",
    "SAFETY",
    "SECURITY",
    "NOISE",
    "COMMUNICATION",
    "EMERGENCY",
)

CATEGORY_NAMES: dict[str, str] = {
    "AIRSPACE": "비행 공역",
    "VERTIPORT": "버티포트 운용",
    "VEHICLE_CERT": "기체 인증",
    "PILOT": "조종사 요건",
    "WEATHER": "기상 제한",
    "SAFETY": "안전 관리",
    "SECURITY": "보안 요건",
    "NOISE": "소음 기준",
    "COMMUNICATION": "통신 요건",
    "EMERGENCY": "비상 절차",
}

UAM_STANDARDS: tuple[tuple[str, str, str, tuple[tuple[str, ...], ...]], ...] = (
    ("U-001", "AIRSPACE", "공역 분리 최소 기준 (수평 30m / 수직 10m)",
     (("**/apf*",), ("**/separation*", "**/collision*"))),
    ("U-002", "AIRSPACE", "고도대 구분 (저고도 0-120m / 중고도 120-300m)",
     (("**/corridor*",), ("**/airspace*",))),
    ("U-003", "AIRSPACE", "지오펜싱 경계 설정 및 침범 탐지",
     (("**/geofence*",),)),
    ("U-004", "VERTIPORT", "버티포트 접근/이탈 절차 정의",
     (("**/vertiport*",),)),
    ("U-005", "VERTIPORT", "버티포트 용량 관리 및 스케줄링",
     (("**/vertiport*", "**/uam_corridor*"),)),
    ("U-006", "VEHICLE_CERT", "eVTOL 비행 성능 모델링",
     (("**/drone_agent*",), ("**/drone_factory*",))),
    ("U-007", "VEHICLE_CERT", "배터리 관리 및 에너지 소비 모델",
     (("**/battery*", "**/energy*"),)),
    ("U-008", "PILOT", "원격 조종사 모드 지원",
     (("**/pilot*", "**/remote*", "**/flight_following*"),)),
    ("U-009", "PILOT", "자율 비행 모드 전환",
     (("**/autonomous*",), ("**/drone_agent*",))),
    ("U-010", "WEATHER", "풍속 제한 기준 (>10 m/s 강풍 모드)",
     (("**/wind*",),)),
    ("U-011", "WEATHER", "시정/가시성 제한 반영",
     (("**/weather*", "**/metar*"),)),
    ("U-012", "SAFETY", "안전 관리 시스템 (SMS) 구현",
     (("**/safety*", "**/risk*"),)),
    ("U-013", "SAFETY", "충돌 회피 시스템",
     (("**/apf*", "**/collision*"),)),
    ("U-014", "SAFETY", "위험 평가 프레임워크",
     (("**/risk*", "**/hazard*"),)),
    ("U-015", "SECURITY", "사이버 보안 요건 충족",
     (("**/security*", "**/csap*"),)),
    ("U-016", "SECURITY", "GPS 스푸핑 탐지",
     (("**/gps_spoof*",),)),
    ("U-017", "SECURITY", "통신 암호화 및 인증",
     (("**/encrypt*", "**/auth*", "**/secure*"),)),
    ("U-018", "NOISE", "소음 영향 평가 모델",
     (("**/noise*", "**/acoustic*"),)),
    ("U-019", "COMMUNICATION", "C2 링크 요건",
     (("**/communication*", "**/comm*"),)),
    ("U-020", "COMMUNICATION", "ADS-B / Remote ID 구현",
     (("**/remote_id*", "**/ads_b*", "**/surveillance*"),)),
    ("U-021", "EMERGENCY", "비상 착륙 절차",
     (("**/emergency*", "**/contingency*"),)),
    ("U-022", "EMERGENCY", "통신 두절 시 대응",
     (("**/failsafe*", "**/fail_safe*", "**/lost_link*"),)),
    ("U-023", "EMERGENCY", "고장 전파 분석",
     (("**/failure_propagation*", "**/fault*"),)),
)


@dataclass(frozen=True)
class ComplianceResult:
    """개별 기준 점검 결과."""

    code: str
    category: str
    requirement: str
    status: str
    evidence: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "category": self.category,
            "requirement": self.requirement,
            "status": self.status,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class ComplianceReport:
    """UAM 운용기준 정렬 보고서."""

    results: tuple[ComplianceResult, ...]
    total: int
    aligned: int
    partial: int
    not_aligned: int
    alignment_rate: float
    verdict: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "results": [r.as_dict() for r in self.results],
            "total": self.total,
            "aligned": self.aligned,
            "partial": self.partial,
            "not_aligned": self.not_aligned,
            "alignment_rate": round(self.alignment_rate, 4),
            "verdict": self.verdict,
        }


_EXCLUDE_DIRS = frozenset((
    "__pycache__", ".mypy_cache", "node_modules", ".git", ".pytest_cache", ".claude",
))


def _glob_any(root: pathlib.Path, patterns: tuple[str, ...]) -> tuple[str, ...]:
    """패턴 그룹 내 하나라도 매치되는 파일 반환 (비소스 디렉토리 제외)."""
    found: list[str] = []
    for pat in patterns:
        for p in root.glob(pat):
            if not p.is_file():
                continue
            parts = p.relative_to(root).parts
            if _EXCLUDE_DIRS.intersection(parts):
                continue
            rel = str(p.relative_to(root))
            if rel not in found:
                found.append(rel)
    return tuple(sorted(found))


def _detect_status(
    root: pathlib.Path, pattern_groups: tuple[tuple[str, ...], ...],
) -> tuple[str, tuple[str, ...]]:
    """패턴 그룹 매치 결과로 상태 결정."""
    all_evidence: list[str] = []
    matched_groups = 0
    for group in pattern_groups:
        files = _glob_any(root, group)
        if files:
            matched_groups += 1
            all_evidence.extend(f for f in files if f not in all_evidence)

    evidence = tuple(sorted(all_evidence))
    if matched_groups == len(pattern_groups):
        return "ALIGNED", evidence
    if matched_groups > 0:
        return "PARTIAL", evidence
    return "NOT_ALIGNED", evidence


def check_standards(
    repo_root: pathlib.Path | None = None,
) -> ComplianceReport:
    """UAM 운용기준 정렬도 점검."""
    root = repo_root or _REPO_ROOT
    if not root.is_dir():
        raise ValueError(f"repo_root does not exist: {root}")

    results: list[ComplianceResult] = []
    for code, category, requirement, patterns in UAM_STANDARDS:
        status, evidence = _detect_status(root, patterns)
        results.append(ComplianceResult(code, category, requirement, status, evidence))

    aligned = sum(1 for r in results if r.status == "ALIGNED")
    partial = sum(1 for r in results if r.status == "PARTIAL")
    not_aligned = sum(1 for r in results if r.status == "NOT_ALIGNED")
    total = len(results)

    rate = (aligned + partial * 0.5) / max(total, 1)

    if rate >= 0.8:
        verdict = "적합"
    elif rate >= 0.5:
        verdict = "부분 적합"
    else:
        verdict = "미흡"

    return ComplianceReport(
        results=tuple(results),
        total=total,
        aligned=aligned,
        partial=partial,
        not_aligned=not_aligned,
        alignment_rate=rate,
        verdict=verdict,
    )


def get_category_report(
    category: str, repo_root: pathlib.Path | None = None,
) -> dict[str, Any]:
    """특정 카테고리 점검 결과."""
    cat = category.upper()
    if cat not in CATEGORIES:
        raise ValueError(f"유효하지 않은 카테고리: {cat}")

    report = check_standards(repo_root)
    cat_results = [r for r in report.results if r.category == cat]
    aligned = sum(1 for r in cat_results if r.status == "ALIGNED")
    partial = sum(1 for r in cat_results if r.status == "PARTIAL")
    total = len(cat_results)
    rate = (aligned + partial * 0.5) / max(total, 1)

    not_aligned = total - aligned - partial
    return {
        "category": cat,
        "category_name": CATEGORY_NAMES[cat],
        "total": total,
        "aligned": aligned,
        "partial": partial,
        "not_aligned": not_aligned,
        "alignment_rate": round(rate, 4),
        "results": [r.as_dict() for r in cat_results],
    }


def list_categories() -> list[dict[str, Any]]:
    """카테고리 목록."""
    return [
        {"code": c, "name": CATEGORY_NAMES[c]}
        for c in CATEGORIES
    ]


def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="GENESIS Phase 313 -- UAM 운용기준 정렬 점검",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="전체 점검")
    group.add_argument("--category", type=str, help="카테고리별 점검")
    group.add_argument("--categories", action="store_true", help="카테고리 목록")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    if args.check:
        _print_check(args.json)
    elif args.category:
        _print_category(args.category, args.json)
    elif args.categories:
        _print_categories(args.json)
    else:
        parser.print_help()
        sys.exit(1)


def _print_check(as_json: bool) -> None:
    report = check_standards()
    if as_json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        return
    print("=" * 60)
    print("  UAM 운용기준 정렬 점검 결과")
    print("=" * 60)
    for r in report.results:
        mark = {"ALIGNED": "✓", "PARTIAL": "△", "NOT_ALIGNED": "✗"}[r.status]
        print(f"  [{mark}] {r.code} {r.requirement}")
        if r.evidence:
            print(f"      증거: {', '.join(r.evidence[:3])}")
    print("-" * 60)
    print(f"  정렬: {report.aligned} | 부분: {report.partial} | 미정렬: {report.not_aligned}")
    print(f"  정렬률: {report.alignment_rate:.1%} | 판정: {report.verdict}")
    print("=" * 60)


def _print_category(category: str, as_json: bool) -> None:
    try:
        result = get_category_report(category)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"카테고리: {result['category_name']} ({result['category']})")
    for r in result["results"]:
        print(f"  [{r['status']}] {r['code']} {r['requirement']}")


def _print_categories(as_json: bool) -> None:
    cats = list_categories()
    if as_json:
        print(json.dumps(cats, ensure_ascii=False, indent=2))
        return
    for c in cats:
        print(f"  {c['code']}: {c['name']}")


if __name__ == "__main__":
    _main()
