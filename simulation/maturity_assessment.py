"""GENESIS Phase 393 -- 프로젝트 성숙도 자가 평가.

소프트웨어 프로젝트 성숙도를 7개 차원으로 자가 평가하는 모듈.
각 차원별 체크항목을 파일시스템 기반으로 자동 판정합니다.

차원: 문서화·테스트·CI/CD·보안·코드 품질·커뮤니티·배포

CLI:
    python simulation/maturity_assessment.py --assess
    python simulation/maturity_assessment.py --dimension documentation
    python simulation/maturity_assessment.py --dimensions
    python simulation/maturity_assessment.py --json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from dataclasses import dataclass
from typing import Any

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

VALID_DIMENSIONS: tuple[str, ...] = (
    "documentation",
    "testing",
    "ci_cd",
    "security",
    "code_quality",
    "community",
    "deployment",
)


@dataclass(frozen=True)
class CheckItem:
    """성숙도 체크 항목."""

    check_id: str
    dimension: str
    description: str
    weight: float
    passed: bool

    def __post_init__(self) -> None:
        if self.dimension not in VALID_DIMENSIONS:
            raise ValueError(f"Invalid dimension: {self.dimension}")
        if self.weight <= 0:
            raise ValueError(f"weight must be > 0, got {self.weight}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "dimension": self.dimension,
            "description": self.description,
            "weight": self.weight,
            "passed": self.passed,
        }


@dataclass(frozen=True)
class DimensionScore:
    """차원별 점수."""

    dimension: str
    name_ko: str
    checks: tuple[CheckItem, ...]
    passed_count: int
    total_count: int
    weighted_score: float
    max_weighted: float

    @property
    def score_pct(self) -> float:
        if self.max_weighted == 0:
            return 0.0
        return round(self.weighted_score / self.max_weighted * 100, 1)

    def as_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "name_ko": self.name_ko,
            "passed_count": self.passed_count,
            "total_count": self.total_count,
            "score_pct": self.score_pct,
            "checks": [c.as_dict() for c in self.checks],
        }


@dataclass(frozen=True)
class MaturityAssessment:
    """전체 성숙도 평가 보고서."""

    dimensions: tuple[DimensionScore, ...]
    overall_score: float
    grade: str
    total_checks: int
    total_passed: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "grade": self.grade,
            "total_checks": self.total_checks,
            "total_passed": self.total_passed,
            "dimensions": [d.as_dict() for d in self.dimensions],
        }


DIMENSION_NAMES_KO: dict[str, str] = {
    "documentation": "문서화",
    "testing": "테스트",
    "ci_cd": "CI/CD",
    "security": "보안",
    "code_quality": "코드 품질",
    "community": "커뮤니티",
    "deployment": "배포",
}

CHECK_DEFINITIONS: tuple[tuple[str, str, str, float], ...] = (
    ("doc_readme", "documentation", "README.md 존재", 2.0),
    ("doc_changelog", "documentation", "CHANGELOG.md 존재", 1.5),
    ("doc_license", "documentation", "LICENSE 파일 존재", 2.0),
    ("doc_api", "documentation", "API 문서 (docs/ 디렉토리)", 1.5),
    ("doc_architecture", "documentation", "아키텍처 문서", 1.0),
    ("doc_roadmap", "documentation", "ROADMAP.md 존재", 1.0),
    ("doc_contributing", "documentation", "CONTRIBUTING.md 존재", 1.0),
    ("test_exists", "testing", "테스트 디렉토리 존재", 2.0),
    ("test_count_10", "testing", "테스트 파일 10개 이상", 1.5),
    ("test_count_50", "testing", "테스트 파일 50개 이상", 1.0),
    ("test_config", "testing", "테스트 설정 파일 존재", 1.0),
    ("ci_workflow", "ci_cd", "CI 워크플로우 존재", 2.0),
    ("ci_config", "ci_cd", "CI 설정 파일 존재", 1.5),
    ("ci_lint", "ci_cd", "린터 설정 존재", 1.0),
    ("sec_gitignore", "security", ".gitignore 존재", 1.5),
    ("sec_no_env", "security", ".env 파일 미추적", 2.0),
    ("sec_license", "security", "라이선스 명시", 1.0),
    ("sec_deps", "security", "의존성 명세 존재", 1.5),
    ("qual_type_hints", "code_quality", "타입 힌트 설정", 1.5),
    ("qual_formatter", "code_quality", "포맷터 설정", 1.0),
    ("qual_config", "code_quality", "프로젝트 설정 파일", 1.5),
    ("qual_modular", "code_quality", "모듈화 구조", 1.0),
    ("comm_issues", "community", "이슈 템플릿 존재", 1.0),
    ("comm_pr_template", "community", "PR 템플릿 존재", 1.0),
    ("comm_coc", "community", "행동 강령 존재", 0.5),
    ("comm_citation", "community", "인용 파일 존재", 0.5),
    ("deploy_docker", "deployment", "Docker 설정 존재", 1.0),
    ("deploy_release", "deployment", "릴리스 문서 존재", 1.0),
    ("deploy_config", "deployment", "배포 설정 디렉토리", 1.0),
    ("deploy_electron", "deployment", "데스크톱 앱 존재", 1.0),
)


def _check_file(root: pathlib.Path, rel: str) -> bool:
    return (root / rel).exists()


def _check_dir(root: pathlib.Path, rel: str) -> bool:
    return (root / rel).is_dir()


def _count_test_files(root: pathlib.Path) -> int:
    test_dir = root / "tests"
    if not test_dir.is_dir():
        return 0
    return len(list(test_dir.glob("test_*.py")))


def _doc_checks(root: pathlib.Path) -> dict[str, bool]:
    return {
        "doc_readme": _check_file(root, "README.md"),
        "doc_changelog": _check_file(root, "CHANGELOG.md"),
        "doc_license": _check_file(root, "LICENSE"),
        "doc_api": _check_dir(root, "docs"),
        "doc_architecture": _check_file(root, "CLAUDE.md") or _check_dir(root, "docs"),
        "doc_roadmap": _check_file(root, "ROADMAP.md"),
        "doc_contributing": _check_file(root, "CONTRIBUTING.md"),
    }


def _test_checks(root: pathlib.Path, test_count: int) -> dict[str, bool]:
    return {
        "test_exists": _check_dir(root, "tests"),
        "test_count_10": test_count >= 10,
        "test_count_50": test_count >= 50,
        "test_config": (
            _check_file(root, "pytest.ini")
            or _check_file(root, "pyproject.toml")
            or _check_file(root, "setup.cfg")
        ),
    }


def _ci_checks(root: pathlib.Path) -> dict[str, bool]:
    return {
        "ci_workflow": _check_dir(root, ".github/workflows"),
        "ci_config": _check_dir(root, ".github/workflows") or _check_file(root, ".gitlab-ci.yml"),
        "ci_lint": _check_file(root, "ruff.toml") or _check_file(root, ".flake8") or _check_file(root, "pyproject.toml"),
    }


def _sec_checks(root: pathlib.Path) -> dict[str, bool]:
    return {
        "sec_gitignore": _check_file(root, ".gitignore"),
        "sec_no_env": not _check_file(root, ".env"),
        "sec_license": _check_file(root, "LICENSE"),
        "sec_deps": _check_file(root, "requirements.txt") or _check_file(root, "pyproject.toml"),
    }


def _qual_checks(root: pathlib.Path) -> dict[str, bool]:
    return {
        "qual_type_hints": _check_file(root, "mypy.ini") or _check_file(root, "pyproject.toml"),
        "qual_formatter": _check_file(root, "pyproject.toml") or _check_file(root, ".prettierrc"),
        "qual_config": _check_file(root, "pyproject.toml"),
        "qual_modular": _check_dir(root, "simulation") and _check_dir(root, "src"),
    }


def _comm_checks(root: pathlib.Path) -> dict[str, bool]:
    return {
        "comm_issues": _check_dir(root, ".github/ISSUE_TEMPLATE"),
        "comm_pr_template": _check_file(root, ".github/pull_request_template.md"),
        "comm_coc": _check_file(root, "CODE_OF_CONDUCT.md"),
        "comm_citation": _check_file(root, "CITATION.cff"),
    }


def _deploy_checks(root: pathlib.Path) -> dict[str, bool]:
    return {
        "deploy_docker": _check_file(root, "Dockerfile") or _check_file(root, "docker-compose.yml"),
        "deploy_release": _check_dir(root, "docs") and any((root / "docs").glob("*RELEASE*")),
        "deploy_config": _check_dir(root, "config"),
        "deploy_electron": _check_dir(root, "electron"),
    }


def _run_checks(repo_root: pathlib.Path | None = None) -> tuple[CheckItem, ...]:
    """모든 체크항목 실행."""
    root = repo_root if repo_root is not None else _REPO_ROOT
    test_count = _count_test_files(root)

    evaluators: dict[str, bool] = {
        **_doc_checks(root),
        **_test_checks(root, test_count),
        **_ci_checks(root),
        **_sec_checks(root),
        **_qual_checks(root),
        **_comm_checks(root),
        **_deploy_checks(root),
    }

    items: list[CheckItem] = []
    for cid, dim, desc, weight in CHECK_DEFINITIONS:
        passed = evaluators.get(cid, False)
        items.append(CheckItem(cid, dim, desc, weight, passed))
    return tuple(items)


def _score_dimension(
    dimension: str, checks: tuple[CheckItem, ...],
) -> DimensionScore:
    """단일 차원 점수 산정."""
    dim_checks = tuple(c for c in checks if c.dimension == dimension)
    passed = sum(1 for c in dim_checks if c.passed)
    weighted = sum(c.weight for c in dim_checks if c.passed)
    max_w = sum(c.weight for c in dim_checks)
    return DimensionScore(
        dimension=dimension,
        name_ko=DIMENSION_NAMES_KO[dimension],
        checks=dim_checks,
        passed_count=passed,
        total_count=len(dim_checks),
        weighted_score=round(weighted, 2),
        max_weighted=round(max_w, 2),
    )


def _compute_grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def assess(
    repo_root: pathlib.Path | None = None,
) -> MaturityAssessment:
    """전체 성숙도 평가 실행."""
    root = repo_root or _REPO_ROOT
    if not root.is_dir():
        raise ValueError(f"repo_root does not exist or is not a directory: {root}")
    checks = _run_checks(root)

    dim_scores: list[DimensionScore] = []
    for dim in VALID_DIMENSIONS:
        dim_scores.append(_score_dimension(dim, checks))

    total_weighted = sum(d.weighted_score for d in dim_scores)
    total_max = sum(d.max_weighted for d in dim_scores)
    overall = round(total_weighted / total_max * 100, 1) if total_max > 0 else 0.0
    grade = _compute_grade(overall)

    total_checks = len(checks)
    total_passed = sum(1 for c in checks if c.passed)

    return MaturityAssessment(
        dimensions=tuple(dim_scores),
        overall_score=overall,
        grade=grade,
        total_checks=total_checks,
        total_passed=total_passed,
    )


def get_dimension(
    dimension: str,
    repo_root: pathlib.Path | None = None,
) -> DimensionScore:
    """특정 차원 점수 조회."""
    if dimension not in VALID_DIMENSIONS:
        raise ValueError(
            f"Unknown dimension: {dimension}. "
            f"Valid: {', '.join(VALID_DIMENSIONS)}"
        )
    checks = _run_checks(repo_root)
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
        description="GENESIS Phase 393 -- 성숙도 자가 평가",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--assess", action="store_true", help="전체 평가")
    group.add_argument("--dimension", type=str, help="특정 차원 평가")
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
    result = assess()
    if as_json:
        print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
        return
    print("=== SDACS 프로젝트 성숙도 평가 ===")
    print(f"  종합 점수: {result.overall_score}% (등급: {result.grade})")
    print(f"  체크 항목: {result.total_passed}/{result.total_checks} 통과")
    print()
    for d in result.dimensions:
        filled = max(0, min(10, int(d.score_pct / 10)))
        bar = "█" * filled + "░" * (10 - filled)
        print(f"  [{d.name_ko}] {bar} {d.score_pct}% ({d.passed_count}/{d.total_count})")


def _print_dimension(dimension: str, as_json: bool) -> None:
    try:
        d = get_dimension(dimension)
    except ValueError as e:
        print(f"오류: {e}", file=sys.stderr)
        sys.exit(1)
    if as_json:
        print(json.dumps(d.as_dict(), ensure_ascii=False, indent=2))
        return
    print(f"=== {d.name_ko} 성숙도 ===")
    print(f"  점수: {d.score_pct}% ({d.passed_count}/{d.total_count})")
    print()
    for c in d.checks:
        marker = "+" if c.passed else "-"
        print(f"  {marker} {c.description}")


def _print_dimensions(as_json: bool) -> None:
    data = list_dimensions()
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    print("=== 성숙도 평가 차원 ===")
    for d in data:
        print(f"  {d['dimension']}: {d['name_ko']}")


if __name__ == "__main__":
    _main()
