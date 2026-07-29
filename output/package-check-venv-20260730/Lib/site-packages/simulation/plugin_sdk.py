"""GENESIS Phase 321 -- 플러그인 SDK v1 (Plugin SDK).

시나리오, 센서, UI 패널 등 플러그인 등록·검증·의존성 해석을 제공한다.

CLI:
    python simulation/plugin_sdk.py --list
    python simulation/plugin_sdk.py --list --type SCENARIO
    python simulation/plugin_sdk.py --validate <name>
    python simulation/plugin_sdk.py --deps <name>
    python simulation/plugin_sdk.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any

_KEBAB_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?"
    r"(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$",
)


class PluginType(Enum):
    SCENARIO = "scenario"
    SENSOR = "sensor"
    UI_PANEL = "ui_panel"
    ANALYTICS = "analytics"
    CONTROLLER = "controller"


@dataclass(frozen=True)
class PluginMeta:
    name: str
    version: str
    author: str
    plugin_type: PluginType
    description: str
    entry_point: str
    dependencies: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "plugin_type": self.plugin_type.value,
            "description": self.description,
            "entry_point": self.entry_point,
            "dependencies": list(self.dependencies),
        }


@dataclass(frozen=True)
class PluginValidation:
    is_valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


def _validate_name(name: str) -> tuple[str, ...]:
    if not name:
        return ("name must not be empty",)
    if not _KEBAB_RE.match(name):
        return ("name must be kebab-case (e.g. 'my-plugin')",)
    return ()


def _validate_version(version: str) -> tuple[str, ...]:
    if not version:
        return ("version must not be empty",)
    if not _SEMVER_RE.match(version):
        return ("version must follow semver (e.g. '1.0.0')",)
    return ()


def _validate_entry_point(entry_point: str) -> tuple[str, ...]:
    if not entry_point or not entry_point.strip():
        return ("entry_point must not be empty",)
    return ()


def validate_meta(meta: PluginMeta) -> PluginValidation:
    errors: tuple[str, ...] = (
        *_validate_name(meta.name),
        *_validate_version(meta.version),
        *_validate_entry_point(meta.entry_point),
    )
    warnings: tuple[str, ...] = ()
    if not meta.description:
        warnings = (*warnings, "description is empty")
    if not meta.author:
        warnings = (*warnings, "author is empty")
    return PluginValidation(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


class PluginRegistry:

    def __init__(self) -> None:
        self._plugins: dict[str, PluginMeta] = {}

    def validate(self, meta: PluginMeta) -> PluginValidation:
        return validate_meta(meta)

    def register(self, meta: PluginMeta) -> PluginValidation:
        validation = self.validate(meta)
        if not validation.is_valid:
            return validation
        if meta.name in self._plugins:
            return PluginValidation(
                is_valid=False,
                errors=(f"plugin '{meta.name}' is already registered",),
                warnings=validation.warnings,
            )
        missing = tuple(
            d for d in meta.dependencies if d not in self._plugins
        )
        warnings = validation.warnings
        if missing:
            warnings = (
                *warnings,
                *(f"dependency '{d}' is not yet registered" for d in missing),
            )
        self._plugins = {**self._plugins, meta.name: meta}
        return PluginValidation(
            is_valid=True,
            errors=(),
            warnings=warnings,
        )

    def unregister(self, name: str) -> bool:
        if name not in self._plugins:
            return False
        self._plugins = {
            k: v for k, v in self._plugins.items() if k != name
        }
        return True

    def get(self, name: str) -> PluginMeta | None:
        return self._plugins.get(name)

    def list_plugins(
        self, plugin_type: PluginType | None = None,
    ) -> tuple[PluginMeta, ...]:
        if plugin_type is None:
            return tuple(self._plugins.values())
        return tuple(
            p for p in self._plugins.values() if p.plugin_type == plugin_type
        )

    def has_circular_deps(self, name: str) -> bool:
        if name not in self._plugins:
            return False
        return self._check_cycle(name, frozenset())

    def _check_cycle(self, name: str, path: frozenset[str]) -> bool:
        if name in path:
            return True
        meta = self._plugins.get(name)
        if meta is None:
            return False
        new_path = path | {name}
        return any(
            self._check_cycle(dep, new_path) for dep in meta.dependencies
        )

    def resolve_dependencies(self, name: str) -> tuple[str, ...] | None:
        if name not in self._plugins:
            return None
        if self.has_circular_deps(name):
            return None
        visited: set[str] = set()
        order: list[str] = []

        def _visit(n: str) -> None:
            if n in visited:
                return
            visited.add(n)
            meta = self._plugins.get(n)
            if meta is not None:
                for dep in meta.dependencies:
                    _visit(dep)
            order.append(n)

        _visit(name)
        return tuple(order)


def _print_list(
    registry: PluginRegistry,
    plugin_type: PluginType | None,
    as_json: bool,
) -> None:
    plugins = registry.list_plugins(plugin_type)
    if as_json:
        data = [p.as_dict() for p in plugins]
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    if not plugins:
        print("(등록된 플러그인 없음)")
        return
    print(f"{'Name':<30} {'Type':<12} {'Version':<10} {'Author'}")
    print("=" * 70)
    for p in plugins:
        print(
            f"{p.name:<30} {p.plugin_type.value:<12} "
            f"{p.version:<10} {p.author}",
        )


def _print_validate(
    registry: PluginRegistry,
    name: str,
    as_json: bool,
) -> None:
    meta = registry.get(name)
    if meta is None:
        msg = f"plugin '{name}' not found"
        if as_json:
            print(json.dumps({"error": msg}, ensure_ascii=False, indent=2))
        else:
            print(msg, file=sys.stderr)
        sys.exit(1)
    result = registry.validate(meta)
    if as_json:
        print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
        return
    status = "VALID" if result.is_valid else "INVALID"
    print(f"Plugin '{name}': {status}")
    for err in result.errors:
        print(f"  ✗ {err}")
    for warn in result.warnings:
        print(f"  △ {warn}")


def _print_deps(
    registry: PluginRegistry,
    name: str,
    as_json: bool,
) -> None:
    if registry.get(name) is None:
        msg = f"plugin '{name}' not found"
        if as_json:
            print(json.dumps({"error": msg}, ensure_ascii=False, indent=2))
        else:
            print(msg, file=sys.stderr)
        sys.exit(1)
    if registry.has_circular_deps(name):
        msg = f"circular dependency detected for '{name}'"
        if as_json:
            print(json.dumps({"error": msg}, ensure_ascii=False, indent=2))
        else:
            print(msg, file=sys.stderr)
        sys.exit(1)
    deps = registry.resolve_dependencies(name)
    if as_json:
        print(json.dumps(list(deps or ()), ensure_ascii=False, indent=2))
        return
    if not deps:
        print(f"'{name}' has no dependencies")
        return
    print(f"Dependency resolution order for '{name}':")
    for i, d in enumerate(deps, 1):
        print(f"  {i}. {d}")


def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="GENESIS Phase 321 -- Plugin SDK v1",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--list", action="store_true", help="등록 플러그인 목록",
    )
    group.add_argument(
        "--validate", type=str, metavar="NAME", help="플러그인 검증",
    )
    group.add_argument(
        "--deps", type=str, metavar="NAME", help="의존성 해석",
    )
    parser.add_argument(
        "--type", type=str, metavar="TYPE", help="플러그인 타입 필터",
    )
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    return parser


def _resolve_plugin_type(type_str: str | None) -> PluginType | None:
    if type_str is None:
        return None
    upper = type_str.upper()
    try:
        return PluginType[upper]
    except KeyError:
        valid = ", ".join(t.name for t in PluginType)
        print(
            f"unknown type '{type_str}' (valid: {valid})", file=sys.stderr,
        )
        sys.exit(1)


def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = build_cli_parser()
    args = parser.parse_args()

    registry = PluginRegistry()

    if args.list:
        pt = _resolve_plugin_type(args.type)
        _print_list(registry, pt, args.json)
    elif args.validate:
        _print_validate(registry, args.validate, args.json)
    elif args.deps:
        _print_deps(registry, args.deps, args.json)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    _main()
