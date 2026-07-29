"""GENESIS Phase 395 -- 교육 자산 레지스트리.

GENESIS 트랙에서 생산된 교육·인수인계 자산을 체계적으로 목록화.
Phase 400 Legacy 선언 전 교육 자산 공개 준비 상태를 확인합니다.

자산 유형: module(코드), document(문서), data(데이터/설정)

CLI:
    python simulation/education_asset_registry.py --list
    python simulation/education_asset_registry.py --asset practice_assignments
    python simulation/education_asset_registry.py --by-type module
    python simulation/education_asset_registry.py --verify
    python simulation/education_asset_registry.py --json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

VALID_TYPES: tuple[str, ...] = ("module", "document", "data")

TYPE_NAMES_KO: dict[str, str] = {
    "module": "코드 모듈",
    "document": "문서",
    "data": "데이터/설정",
}


@dataclass(frozen=True)
class AssetEntry:
    """교육 자산 항목."""

    asset_id: str
    phase: int
    asset_type: str
    path: str
    description: str
    test_count: int

    def __post_init__(self) -> None:
        if self.asset_type not in VALID_TYPES:
            raise ValueError(f"Invalid asset_type: {self.asset_type}")
        if self.phase < 301 or self.phase > 400:
            raise ValueError(f"Phase must be 301-400, got {self.phase}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "phase": self.phase,
            "asset_type": self.asset_type,
            "path": self.path,
            "description": self.description,
            "test_count": self.test_count,
        }


@dataclass(frozen=True)
class VerificationResult:
    """자산 검증 결과."""

    asset_id: str
    path: str
    exists: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "path": self.path,
            "exists": self.exists,
        }


@dataclass(frozen=True)
class RegistryReport:
    """레지스트리 보고서."""

    total_assets: int
    verified_count: int
    missing_count: int
    coverage_pct: float
    by_type: Mapping[str, int]
    verifications: tuple[VerificationResult, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_assets": self.total_assets,
            "verified_count": self.verified_count,
            "missing_count": self.missing_count,
            "coverage_pct": self.coverage_pct,
            "by_type": dict(self.by_type),
            "verifications": [v.as_dict() for v in self.verifications],
        }


ASSET_REGISTRY: tuple[AssetEntry, ...] = (
    AssetEntry("practice_assignments", 382, "module",
               "simulation/practice_assignments.py",
               "학부 수업용 실습 과제 10종 (채점 기준·검증 스크립트)", 44),
    AssetEntry("curriculum_slides", 383, "module",
               "simulation/curriculum_slide_package.py",
               "15주 캡스톤 커리큘럼 슬라이드 패키지", 50),
    AssetEntry("pilot_exam_bank", 384, "module",
               "simulation/pilot_exam_bank.py",
               "조종자 자격 이론 문제은행 40문항 (1~4종)", 49),
    AssetEntry("onboarding_automation", 385, "module",
               "simulation/onboarding_automation.py",
               "후속 기수 온보딩 자동화 (환경 점검 + 아키텍처 투어)", 52),
    AssetEntry("code_archaeology", 386, "module",
               "simulation/code_archaeology.py",
               "코드 고고학 가이드 (Phase→커밋 매핑·검색·통계)", 50),
    AssetEntry("defense_kit", 387, "document",
               "docs/presentation/DEFENSE_KIT.md",
               "졸업 심사 발표 키트 (10분 데모·예상 질문·체크리스트)", 0),
    AssetEntry("tech_debt_ledger", 388, "document",
               "docs/TECH_DEBT_LEDGER.md",
               "기술 부채 대장 (자동 생성)", 0),
    AssetEntry("maintenance_mode", 389, "document",
               "docs/MAINTENANCE_MINIMAL_MODE.md",
               "유지보수 최소 모드 (코어 서브셋·워크플로·비상 절차)", 0),
    AssetEntry("archive_strategy", 390, "module",
               "simulation/archive_strategy.py",
               "아카이브 전략 (Zenodo 검증·Software Heritage·졸업 체크리스트)", 45),
    AssetEntry("demo_experience", 391, "module",
               "simulation/demo_experience.py",
               "고교·일반인 체험판 (난이도 프리셋·쉬운 용어·가이드 시나리오)", 74),
    AssetEntry("achievement_summary", 392, "module",
               "simulation/achievement_summary.py",
               "성과 요약 대시보드 데이터 (트랙 진척·마일스톤·자동 집계)", 46),
    AssetEntry("maturity_assessment", 393, "module",
               "simulation/maturity_assessment.py",
               "프로젝트 성숙도 자가 평가 (7차원 30항목·A~F 등급)", 42),
    AssetEntry("handover_checklist", 394, "module",
               "simulation/handover_checklist.py",
               "인수인계 체크리스트 (5카테고리 25항목·준비도 산정)", 39),
    AssetEntry("pilot_license_mapping", 309, "document",
               "docs/certification/PILOT_LICENSE_MAPPING.md",
               "조종자 자격증명(1~4종) ↔ SDACS 모듈 매핑", 0),
    AssetEntry("sim_config_default", 301, "data",
               "config/default_simulation.yaml",
               "기본 시뮬레이션 파라미터 설정", 0),
    AssetEntry("scenario_params", 301, "data",
               "config/scenario_params",
               "9개 시나리오 정의 YAML", 0),
)

_ASSET_INDEX: dict[str, AssetEntry] = {}
for _entry in ASSET_REGISTRY:
    if _entry.asset_id in _ASSET_INDEX:
        raise ValueError(f"Duplicate asset_id in registry: {_entry.asset_id}")
    _ASSET_INDEX[_entry.asset_id] = _entry


def list_assets() -> list[dict[str, Any]]:
    """전체 자산 목록."""
    return [a.as_dict() for a in ASSET_REGISTRY]


def get_asset(asset_id: str) -> AssetEntry:
    """특정 자산 조회."""
    try:
        return _ASSET_INDEX[asset_id]
    except KeyError:
        raise ValueError(
            f"Unknown asset: {asset_id}. "
            f"Valid: {', '.join(_ASSET_INDEX)}"
        ) from None


def list_by_type(asset_type: str) -> list[dict[str, Any]]:
    """유형별 자산 목록."""
    if asset_type not in VALID_TYPES:
        raise ValueError(
            f"Unknown type: {asset_type}. Valid: {', '.join(VALID_TYPES)}"
        )
    return [a.as_dict() for a in ASSET_REGISTRY if a.asset_type == asset_type]


def verify_assets(
    repo_root: pathlib.Path | None = None,
) -> RegistryReport:
    """모든 자산의 존재 여부 검증."""
    root = repo_root or _REPO_ROOT

    verifications: list[VerificationResult] = []
    for a in ASSET_REGISTRY:
        target = root / a.path
        exists = target.exists()
        verifications.append(VerificationResult(a.asset_id, a.path, exists))

    total = len(verifications)
    verified = sum(1 for v in verifications if v.exists)
    missing = total - verified
    pct = round(verified / total * 100, 1) if total > 0 else 0.0

    by_type: dict[str, int] = {}
    for t in VALID_TYPES:
        by_type[t] = sum(1 for a in ASSET_REGISTRY if a.asset_type == t)

    return RegistryReport(
        total_assets=total,
        verified_count=verified,
        missing_count=missing,
        coverage_pct=pct,
        by_type=MappingProxyType(by_type),
        verifications=tuple(verifications),
    )


def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="GENESIS Phase 395 -- 교육 자산 레지스트리",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--list", action="store_true", help="전체 자산 목록")
    group.add_argument("--asset", type=str, help="특정 자산 조회")
    group.add_argument("--by-type", type=str, help="유형별 자산")
    group.add_argument("--verify", action="store_true", help="자산 존재 검증")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    if args.list:
        _print_list(args.json)
    elif args.asset:
        _print_asset(args.asset, args.json)
    elif args.by_type:
        _print_by_type(args.by_type, args.json)
    elif args.verify:
        _print_verify(args.json)
    else:
        parser.print_help()
        sys.exit(1)


def _print_list(as_json: bool) -> None:
    data = list_assets()
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print("=== SDACS 교육 자산 레지스트리 ===")
    print(f"  총 {len(data)}개 자산")
    print()
    for a in data:
        typ = TYPE_NAMES_KO.get(a["asset_type"], a["asset_type"])
        tests = f" ({a['test_count']}건)" if a["test_count"] > 0 else ""
        print(f"  Phase {a['phase']:>3} [{typ}] {a['asset_id']}{tests}")
        print(f"           {a['description']}")


def _print_asset(asset_id: str, as_json: bool) -> None:
    try:
        a = get_asset(asset_id)
    except ValueError as e:
        print(f"오류: {e}", file=sys.stderr)
        sys.exit(1)
    if as_json:
        print(json.dumps(a.as_dict(), ensure_ascii=False, indent=2))
        return
    typ = TYPE_NAMES_KO.get(a.asset_type, a.asset_type)
    print(f"=== {a.asset_id} ===")
    print(f"  Phase: {a.phase}")
    print(f"  유형:  {typ}")
    print(f"  경로:  {a.path}")
    print(f"  설명:  {a.description}")
    if a.test_count > 0:
        print(f"  테스트: {a.test_count}건")


def _print_by_type(asset_type: str, as_json: bool) -> None:
    try:
        data = list_by_type(asset_type)
    except ValueError as e:
        print(f"오류: {e}", file=sys.stderr)
        sys.exit(1)
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    typ_ko = TYPE_NAMES_KO.get(asset_type, asset_type)
    print(f"=== {typ_ko} 자산 ===")
    print(f"  총 {len(data)}개")
    print()
    for a in data:
        print(f"  Phase {a['phase']:>3} {a['asset_id']}: {a['description']}")


def _print_verify(as_json: bool) -> None:
    report = verify_assets()
    if as_json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        return
    print("=== 교육 자산 검증 ===")
    print(f"  검증: {report.verified_count}/{report.total_assets} ({report.coverage_pct}%)")
    print(f"  누락: {report.missing_count}개")
    print()
    for v in report.verifications:
        marker = "+" if v.exists else "-"
        print(f"  {marker} {v.asset_id}: {v.path}")


if __name__ == "__main__":
    _main()
