"""Python 배포 패키지의 CLI 진입점과 런타임 자산 포함 설정 회귀 테스트."""

from __future__ import annotations

import importlib
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[1]


def _pyproject() -> dict:
    with (ROOT / "pyproject.toml").open("rb") as stream:
        return tomllib.load(stream)


def test_sdacs_console_entrypoint_is_importable() -> None:
    """`sdacs = main:main` 대상이 실제 배포 모듈에서 호출 가능해야 한다."""
    target = _pyproject()["project"]["scripts"]["sdacs"]
    module_name, function_name = target.split(":", maxsplit=1)
    module = importlib.import_module(module_name)
    assert callable(getattr(module, function_name))


def test_wheel_discovers_runtime_packages_from_repository_root() -> None:
    """루트 레이아웃 패키지와 `main.py`가 휠 탐색 대상에서 빠지지 않아야 한다."""
    config = _pyproject()["tool"]["setuptools"]
    assert "main" in config["py-modules"]
    assert config["packages"]["find"]["where"] == ["."]

    includes = set(config["packages"]["find"]["include"])
    assert {"simulation*", "src*", "config*", "benchmarks*"} <= includes


def test_scenario_and_benchmark_data_are_packaged() -> None:
    """설치형 CLI가 참조하는 YAML 매니페스트 포함 규칙을 유지한다."""
    package_data = _pyproject()["tool"]["setuptools"]["package-data"]
    assert "scenario_params/**/*.yaml" in package_data["config"]
    assert "scenarios/**/*.yaml" in package_data["benchmarks"]
    assert (ROOT / "config" / "__init__.py").is_file()
    assert (ROOT / "benchmarks" / "__init__.py").is_file()
