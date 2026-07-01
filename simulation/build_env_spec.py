"""GENESIS Phase 316 -- 빌드 환경 사양서 자동 수집.

DO-178C §11.6(a) 기준 소프트웨어 빌드 환경의 정확한 기록을 위해
현재 개발/CI 환경 정보를 자동 수집합니다.

5개 카테고리 × 15개 항목의 환경 정보를 파일시스템 및 런타임에서 확인합니다.

CLI:
    python simulation/build_env_spec.py --collect
    python simulation/build_env_spec.py --category PYTHON
    python simulation/build_env_spec.py --categories
    python simulation/build_env_spec.py --json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import platform
import sys
from dataclasses import dataclass
from typing import Any

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

ENV_CATEGORIES: tuple[str, ...] = (
    "PYTHON",
    "DEPENDENCIES",
    "OS_ENV",
    "CI_CD",
    "CONTAINER",
)

CATEGORY_NAMES: dict[str, str] = {
    "PYTHON": "Python 런타임 (§11.6a)",
    "DEPENDENCIES": "의존성 관리 (§11.6b)",
    "OS_ENV": "운영체제 환경 (§11.6c)",
    "CI_CD": "CI/CD 파이프라인 (§11.6d)",
    "CONTAINER": "컨테이너/가상화 (§11.6e)",
}

ENV_ITEMS: tuple[tuple[str, str, str, str], ...] = (
    ("BE-001", "PYTHON", "Python 버전", "runtime"),
    ("BE-002", "PYTHON", "Python 구현체 (CPython/PyPy)", "runtime"),
    ("BE-003", "PYTHON", "Python 설치 경로", "runtime"),
    ("BE-004", "DEPENDENCIES", "pyproject.toml 존재", "file"),
    ("BE-005", "DEPENDENCIES", "requirements.txt 존재", "file"),
    ("BE-006", "DEPENDENCIES", "의존성 잠금 파일", "file"),
    ("BE-007", "OS_ENV", "운영체제 정보", "runtime"),
    ("BE-008", "OS_ENV", "아키텍처 (x86_64/ARM)", "runtime"),
    ("BE-009", "OS_ENV", "호스트네임", "runtime"),
    ("BE-010", "CI_CD", "GitHub Actions 워크플로", "file"),
    ("BE-011", "CI_CD", "CI 설정 파일", "file"),
    ("BE-012", "CI_CD", "pre-commit 설정", "file"),
    ("BE-013", "CONTAINER", "Dockerfile 존재", "file"),
    ("BE-014", "CONTAINER", "docker-compose 존재", "file"),
    ("BE-015", "CONTAINER", ".dockerignore 존재", "file"),
)

_FILE_CHECKS: dict[str, tuple[str, ...]] = {
    "BE-004": ("pyproject.toml",),
    "BE-005": ("requirements.txt", "requirements-dev.txt", "requirements-test.txt"),
    "BE-006": ("poetry.lock", "Pipfile.lock", "pdm.lock", "uv.lock", "requirements.lock.txt"),
    "BE-010": (".github/workflows",),
    "BE-011": (".github/workflows/ci.yml", ".github/workflows/ci.yaml",
               ".github/workflows/test.yml", ".github/workflows/test.yaml"),
    "BE-012": (".pre-commit-config.yaml",),
    "BE-013": ("Dockerfile",),
    "BE-014": ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"),
    "BE-015": (".dockerignore",),
}


@dataclass(frozen=True)
class EnvItem:
    """개별 환경 항목."""

    code: str
    category: str
    item_name: str
    value: str
    status: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "category": self.category,
            "item_name": self.item_name,
            "value": self.value,
            "status": self.status,
        }


@dataclass(frozen=True)
class EnvReport:
    """빌드 환경 사양 보고서."""

    items: tuple[EnvItem, ...]
    total: int
    documented: int
    partial: int
    undocumented: int
    documentation_rate: float
    verdict: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "items": [i.as_dict() for i in self.items],
            "total": self.total,
            "documented": self.documented,
            "partial": self.partial,
            "undocumented": self.undocumented,
            "documentation_rate": round(self.documentation_rate, 4),
            "verdict": self.verdict,
        }


def _check_runtime(code: str) -> tuple[str, str]:
    """런타임 정보 수집."""
    if code == "BE-001":
        return sys.version.split()[0], "DOCUMENTED"
    if code == "BE-002":
        return platform.python_implementation(), "DOCUMENTED"
    if code == "BE-003":
        return sys.executable, "DOCUMENTED"
    if code == "BE-007":
        return f"{platform.system()} {platform.release()}", "DOCUMENTED"
    if code == "BE-008":
        return platform.machine(), "DOCUMENTED"
    if code == "BE-009":
        return platform.node(), "DOCUMENTED"
    return "", "UNDOCUMENTED"


def _check_file(code: str, root: pathlib.Path) -> tuple[str, str]:
    """파일 존재 확인."""
    paths = _FILE_CHECKS.get(code, ())
    found: list[str] = []
    seen_resolved: set[pathlib.Path] = set()
    for p in paths:
        full = root / p
        if not full.exists():
            continue
        resolved = full.resolve()
        if resolved in seen_resolved:
            continue
        seen_resolved.add(resolved)
        if full.is_dir():
            if any(full.iterdir()):
                found.append(p)
        else:
            found.append(p)
    if found:
        return ", ".join(found), "DOCUMENTED"
    return "", "UNDOCUMENTED"


def collect_env(
    repo_root: pathlib.Path | None = None,
) -> EnvReport:
    """빌드 환경 정보 수집."""
    root = repo_root or _REPO_ROOT
    if not root.is_dir():
        raise ValueError(f"repo_root does not exist: {root}")

    items: list[EnvItem] = []
    for code, category, item_name, check_type in ENV_ITEMS:
        if check_type == "runtime":
            value, status = _check_runtime(code)
        else:
            value, status = _check_file(code, root)
        items.append(EnvItem(code, category, item_name, value, status))

    documented = sum(1 for i in items if i.status == "DOCUMENTED")
    partial = sum(1 for i in items if i.status == "PARTIAL")
    undocumented = sum(1 for i in items if i.status == "UNDOCUMENTED")
    total = len(items)

    rate = (documented + partial * 0.5) / max(total, 1)

    if rate >= 0.8:
        verdict = "환경 문서화 충족"
    elif rate >= 0.5:
        verdict = "부분 문서화"
    else:
        verdict = "문서화 미흡"

    return EnvReport(
        items=tuple(items),
        total=total,
        documented=documented,
        partial=partial,
        undocumented=undocumented,
        documentation_rate=rate,
        verdict=verdict,
    )


def get_category_report(
    category: str, repo_root: pathlib.Path | None = None,
) -> dict[str, Any]:
    """특정 카테고리 환경 정보."""
    cat = category.upper()
    if cat not in ENV_CATEGORIES:
        raise ValueError(f"유효하지 않은 카테고리: {cat}")

    report = collect_env(repo_root)
    cat_items = [i for i in report.items if i.category == cat]
    documented = sum(1 for i in cat_items if i.status == "DOCUMENTED")
    partial = sum(1 for i in cat_items if i.status == "PARTIAL")
    total = len(cat_items)
    undocumented = total - documented - partial
    rate = (documented + partial * 0.5) / max(total, 1)

    return {
        "category": cat,
        "category_name": CATEGORY_NAMES[cat],
        "total": total,
        "documented": documented,
        "partial": partial,
        "undocumented": undocumented,
        "documentation_rate": round(rate, 4),
        "items": [i.as_dict() for i in cat_items],
    }


def list_categories() -> list[dict[str, Any]]:
    """환경 카테고리 목록."""
    return [
        {"code": c, "name": CATEGORY_NAMES[c]}
        for c in ENV_CATEGORIES
    ]


def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="GENESIS Phase 316 -- 빌드 환경 사양서 자동 수집",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--collect", action="store_true", help="전체 수집")
    group.add_argument("--category", type=str, help="카테고리별 수집")
    group.add_argument("--categories", action="store_true", help="카테고리 목록")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    if args.collect:
        _print_collect(args.json)
    elif args.category:
        _print_category(args.category, args.json)
    elif args.categories:
        _print_categories(args.json)
    else:
        parser.print_help()
        sys.exit(1)


def _print_collect(as_json: bool) -> None:
    report = collect_env()
    if as_json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        return
    print("=" * 60)
    print("  빌드 환경 사양서 (DO-178C §11.6)")
    print("=" * 60)
    for i in report.items:
        mark = {"DOCUMENTED": "✓", "PARTIAL": "△", "UNDOCUMENTED": "✗"}[i.status]
        val = f" = {i.value}" if i.value else ""
        print(f"  [{mark}] {i.code} {i.item_name}{val}")
    print("-" * 60)
    print(f"  문서화: {report.documented} | 부분: {report.partial} | 미문서: {report.undocumented}")
    print(f"  문서화율: {report.documentation_rate:.1%} | 판정: {report.verdict}")
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
    for i in result["items"]:
        val = f" = {i['value']}" if i["value"] else ""
        print(f"  [{i['status']}] {i['code']} {i['item_name']}{val}")


def _print_categories(as_json: bool) -> None:
    cats = list_categories()
    if as_json:
        print(json.dumps(cats, ensure_ascii=False, indent=2))
        return
    for c in cats:
        print(f"  {c['code']}: {c['name']}")


if __name__ == "__main__":
    _main()
