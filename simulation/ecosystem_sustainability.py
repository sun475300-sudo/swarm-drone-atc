"""GENESIS Phase 397 -- 생태계 자생력 평가.

원저자 부재 시 프로젝트가 독립적으로 유지·발전 가능한지 평가.
6개 차원(문서화·테스트·의존성·빌드·커뮤니티·교육)의 체크 항목을
파일시스템 기반으로 자동 판정합니다.

CLI:
    python simulation/ecosystem_sustainability.py --assess
    python simulation/ecosystem_sustainability.py --dimension documentation
    python simulation/ecosystem_sustainability.py --dimensions
    python simulation/ecosystem_sustainability.py --json
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

VALID_DIMENSIONS: tuple[str, ...] = (
    "documentation",
    "testing",
    "dependencies",
    "build",
    "community",
    "education",
)

DIMENSION_NAMES_KO: dict[str, str] = {
    "documentation": "문서 완비도",
    "testing": "테스트 커버리지",
    "dependencies": "의존성 건전성",
    "build": "빌드·재현성",
    "community": "커뮤니티 기반",
    "education": "교육 자산",
}

SUSTAINABILITY_THRESHOLD: float = 70.0


@dataclass(frozen=True)
class CheckItem:
    """개별 체크 항목."""

    check_id: str
    dimension: str
    description: str
    passed: bool
    note: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "dimension": self.dimension,
            "description": self.description,
            "passed": self.passed,
            "note": self.note,
        }


@dataclass(frozen=True)
class DimensionResult:
    """차원별 결과."""

    dimension: str
    name_ko: str
    checks: tuple[CheckItem, ...]
    passed_count: int
    total_count: int
    score: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "name_ko": self.name_ko,
            "passed_count": self.passed_count,
            "total_count": self.total_count,
            "score": self.score,
            "checks": [c.as_dict() for c in self.checks],
        }


@dataclass(frozen=True)
class SustainabilityReport:
    """생태계 자생력 보고서."""

    dimensions: tuple[DimensionResult, ...]
    total_checks: int
    total_passed: int
    overall_score: float
    overall_grade: str
    self_sustaining: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_checks": self.total_checks,
            "total_passed": self.total_passed,
            "overall_score": self.overall_score,
            "overall_grade": self.overall_grade,
            "self_sustaining": self.self_sustaining,
            "dimensions": [d.as_dict() for d in self.dimensions],
        }


CHECK_DEFINITIONS: tuple[tuple[str, str, str], ...] = (
    ("doc_readme", "documentation", "README.md 존재"),
    ("doc_contributing", "documentation", "CONTRIBUTING.md 존재"),
    ("doc_changelog", "documentation", "CHANGELOG.md 존재"),
    ("doc_api", "documentation", "docs/ API 문서 디렉토리"),
    ("doc_architecture", "documentation", "아키텍처 문서 존재"),
    ("test_dir", "testing", "tests/ 디렉토리 존재"),
    ("test_conftest", "testing", "conftest.py 테스트 설정"),
    ("test_pyproject", "testing", "pyproject.toml 테스트 설정"),
    ("test_ci", "testing", "CI 테스트 자동화 설정"),
    ("dep_requirements", "dependencies", "requirements.txt 존재"),
    ("dep_pyproject", "dependencies", "pyproject.toml 존재"),
    ("dep_lock", "dependencies", "의존성 잠금 파일 존재"),
    ("dep_gitignore", "dependencies", ".gitignore 존재"),
    ("build_makefile", "build", "빌드 스크립트/Makefile 존재"),
    ("build_dockerfile", "build", "Dockerfile 존재"),
    ("build_ci_yaml", "build", "CI/CD 설정 파일 존재"),
    ("comm_license", "community", "LICENSE 파일 존재"),
    ("comm_coc", "community", "행동 강령(CODE_OF_CONDUCT) 존재"),
    ("comm_issues", "community", "이슈 템플릿 존재"),
    ("comm_security", "community", "SECURITY.md 존재"),
    ("edu_curriculum", "education", "커리큘럼 모듈 존재"),
    ("edu_onboarding", "education", "온보딩 모듈 존재"),
    ("edu_practice", "education", "실습 과제 모듈 존재"),
    ("edu_exam", "education", "문제은행 모듈 존재"),
)


def _build_check_map(root: pathlib.Path) -> dict[str, tuple[bool, str]]:
    """파일시스템 기반 체크 결과 맵 구축."""
    e = {p: (root / p).exists() for p in (
        "README.md", "CONTRIBUTING.md", "CHANGELOG.md",
        "CLAUDE.md", "docs/ARCHITECTURE.md",
        "conftest.py", "pyproject.toml",
        "requirements.txt", "requirements.lock.txt",
        ".gitignore", "Makefile",
        "Dockerfile", "Dockerfile.reproducible",
        "LICENSE", "CODE_OF_CONDUCT.md", "SECURITY.md",
        "simulation/curriculum_slide_package.py",
        "simulation/onboarding_automation.py",
        "simulation/practice_assignments.py",
        "simulation/pilot_exam_bank.py",
    )}
    d = {p: (root / p).is_dir() for p in (
        "docs", "tests", ".github/ISSUE_TEMPLATE",
        ".github/workflows",
    )}

    has_arch = e["CLAUDE.md"] or e["docs/ARCHITECTURE.md"]
    has_ci = d[".github/workflows"]
    has_docker = e["Dockerfile"] or e["Dockerfile.reproducible"]

    return {
        "doc_readme": (e["README.md"], "README.md"),
        "doc_contributing": (e["CONTRIBUTING.md"], "CONTRIBUTING.md"),
        "doc_changelog": (e["CHANGELOG.md"], "CHANGELOG.md"),
        "doc_api": (d["docs"], "docs/"),
        "doc_architecture": (has_arch, "아키텍처 문서"),
        "test_dir": (d["tests"], "tests/"),
        "test_conftest": (e["conftest.py"], "conftest.py"),
        "test_pyproject": (e["pyproject.toml"], "pyproject.toml(테스트)"),
        "test_ci": (has_ci, "CI 테스트 워크플로"),
        "dep_requirements": (e["requirements.txt"], "requirements.txt"),
        "dep_pyproject": (e["pyproject.toml"], "pyproject.toml(의존성)"),
        "dep_lock": (e["requirements.lock.txt"], "잠금 파일"),
        "dep_gitignore": (e[".gitignore"], ".gitignore"),
        "build_makefile": (e["Makefile"], "빌드 스크립트"),
        "build_dockerfile": (has_docker, "Dockerfile"),
        "build_ci_yaml": (has_ci, "CI/CD 빌드 파이프라인"),
        "comm_license": (e["LICENSE"], "LICENSE"),
        "comm_coc": (e["CODE_OF_CONDUCT.md"], "CODE_OF_CONDUCT.md"),
        "comm_issues": (d[".github/ISSUE_TEMPLATE"], "이슈 템플릿"),
        "comm_security": (e["SECURITY.md"], "SECURITY.md"),
        "edu_curriculum": (e["simulation/curriculum_slide_package.py"], "커리큘럼"),
        "edu_onboarding": (e["simulation/onboarding_automation.py"], "온보딩"),
        "edu_practice": (e["simulation/practice_assignments.py"], "실습"),
        "edu_exam": (e["simulation/pilot_exam_bank.py"], "문제은행"),
    }


def _run_checks(repo_root: pathlib.Path) -> tuple[CheckItem, ...]:
    """모든 체크 항목 자동 판정."""
    check_map = _build_check_map(repo_root)

    items: list[CheckItem] = []
    for cid, dim, desc in CHECK_DEFINITIONS:
        passed, note = check_map.get(cid, (False, "판정 불가"))
        items.append(CheckItem(cid, dim, desc, passed, note))
    return tuple(items)


def _score_dimension(
    dimension: str,
    checks: tuple[CheckItem, ...],
) -> DimensionResult:
    """차원별 점수 산정."""
    dim_checks = tuple(c for c in checks if c.dimension == dimension)
    passed = sum(1 for c in dim_checks if c.passed)
    total = len(dim_checks)
    score = round(passed / total * 100, 1) if total > 0 else 0.0
    return DimensionResult(
        dimension=dimension,
        name_ko=DIMENSION_NAMES_KO[dimension],
        checks=dim_checks,
        passed_count=passed,
        total_count=total,
        score=score,
    )


def _grade_from_score(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def assess_sustainability(
    repo_root: pathlib.Path | None = None,
) -> SustainabilityReport:
    """생태계 자생력 평가 실행."""
    root = repo_root or _REPO_ROOT
    if not root.is_dir():
        raise ValueError(f"repo_root does not exist: {root}")

    checks = _run_checks(root)
    dim_results: list[DimensionResult] = []
    for dim in VALID_DIMENSIONS:
        dim_results.append(_score_dimension(dim, checks))

    total = len(checks)
    passed = sum(1 for c in checks if c.passed)
    score = round(passed / total * 100, 1) if total > 0 else 0.0
    grade = _grade_from_score(score)

    return SustainabilityReport(
        dimensions=tuple(dim_results),
        total_checks=total,
        total_passed=passed,
        overall_score=score,
        overall_grade=grade,
        self_sustaining=score >= SUSTAINABILITY_THRESHOLD,
    )


def get_dimension(
    dimension: str,
    repo_root: pathlib.Path | None = None,
) -> DimensionResult:
    """특정 차원 결과 조회."""
    if dimension not in VALID_DIMENSIONS:
        raise ValueError(
            f"Unknown dimension: {dimension}. "
            f"Valid: {', '.join(VALID_DIMENSIONS)}"
        )
    root = repo_root or _REPO_ROOT
    checks = _run_checks(root)
    return _score_dimension(dimension, checks)


def list_dimensions() -> list[dict[str, str]]:
    """사용 가능한 차원 목록."""
    return [
        {"dimension": d, "name_ko": DIMENSION_NAMES_KO[d]}
        for d in VALID_DIMENSIONS
    ]


def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="GENESIS Phase 397 -- 생태계 자생력 평가",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--assess", action="store_true", help="전체 평가")
    group.add_argument("--dimension", type=str, help="특정 차원")
    group.add_argument("--dimensions", action="store_true", help="차원 목록")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    if args.assess:
        _print_assess(args.json)
    elif args.dimension:
        _print_dimension(args.dimension, args.json)
    elif args.dimensions:
        _print_dimensions(args.json)
    else:
        parser.print_help()
        sys.exit(1)


def _print_assess(as_json: bool) -> None:
    report = assess_sustainability()
    if as_json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        return
    print("=== 생태계 자생력 평가 ===")
    print(f"  점수: {report.overall_score}% (등급: {report.overall_grade})")
    print(f"  자생 가능: {'예' if report.self_sustaining else '아니오'}")
    print(f"  체크: {report.total_passed}/{report.total_checks} 통과")
    print()
    for d in report.dimensions:
        filled = max(0, min(10, int(d.score / 10)))
        bar = "█" * filled + "░" * (10 - filled)
        print(f"  [{d.name_ko}] {bar} {d.score}%")
        for c in d.checks:
            marker = "+" if c.passed else "-"
            print(f"    {marker} {c.description}: {c.note}")


def _print_dimension(dimension: str, as_json: bool) -> None:
    try:
        d = get_dimension(dimension)
    except ValueError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        sys.exit(1)
    if as_json:
        print(json.dumps(d.as_dict(), ensure_ascii=False, indent=2))
        return
    print(f"=== {d.name_ko} ===")
    print(f"  점수: {d.score}%")
    print(f"  체크: {d.passed_count}/{d.total_count} 통과")
    for c in d.checks:
        marker = "+" if c.passed else "-"
        print(f"  {marker} {c.description}: {c.note}")


def _print_dimensions(as_json: bool) -> None:
    data = list_dimensions()
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print("=== 자생력 평가 차원 ===")
    for d in data:
        print(f"  {d['dimension']}: {d['name_ko']}")


if __name__ == "__main__":
    _main()
