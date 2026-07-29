"""Tests for GENESIS Phase 321 -- Plugin SDK v1."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from simulation.plugin_sdk import (
    PluginMeta,
    PluginRegistry,
    PluginType,
    PluginValidation,
    build_cli_parser,
    validate_meta,
)


def _make_meta(
    name: str = "my-plugin",
    version: str = "1.0.0",
    author: str = "tester",
    plugin_type: PluginType = PluginType.SCENARIO,
    description: str = "A test plugin",
    entry_point: str = "my_plugin:main",
    dependencies: tuple[str, ...] = (),
) -> PluginMeta:
    return PluginMeta(
        name=name,
        version=version,
        author=author,
        plugin_type=plugin_type,
        description=description,
        entry_point=entry_point,
        dependencies=dependencies,
    )


# ── PluginMeta frozen dataclass ──────────────────────────────────────

class TestPluginMeta:

    def test_frozen(self) -> None:
        meta = _make_meta()
        with pytest.raises(AttributeError):
            meta.name = "changed"  # type: ignore[misc]

    def test_as_dict_fields(self) -> None:
        meta = _make_meta(dependencies=("dep-a",))
        d = meta.as_dict()
        assert d["name"] == "my-plugin"
        assert d["plugin_type"] == "scenario"
        assert isinstance(d["dependencies"], list)
        assert d["dependencies"] == ["dep-a"]

    def test_default_dependencies_empty(self) -> None:
        meta = _make_meta()
        assert meta.dependencies == ()


# ── PluginValidation frozen dataclass ────────────────────────────────

class TestPluginValidation:

    def test_frozen(self) -> None:
        v = PluginValidation(is_valid=True, errors=(), warnings=())
        with pytest.raises(AttributeError):
            v.is_valid = False  # type: ignore[misc]

    def test_as_dict(self) -> None:
        v = PluginValidation(
            is_valid=False,
            errors=("err1",),
            warnings=("warn1",),
        )
        d = v.as_dict()
        assert d["is_valid"] is False
        assert isinstance(d["errors"], list)
        assert isinstance(d["warnings"], list)


# ── validate_meta ────────────────────────────────────────────────────

class TestValidateMeta:

    def test_valid_meta(self) -> None:
        result = validate_meta(_make_meta())
        assert result.is_valid is True
        assert result.errors == ()

    def test_empty_name(self) -> None:
        result = validate_meta(_make_meta(name=""))
        assert result.is_valid is False
        assert any("name" in e for e in result.errors)

    def test_non_kebab_name_uppercase(self) -> None:
        result = validate_meta(_make_meta(name="MyPlugin"))
        assert result.is_valid is False

    def test_non_kebab_name_underscore(self) -> None:
        result = validate_meta(_make_meta(name="my_plugin"))
        assert result.is_valid is False

    def test_non_kebab_name_space(self) -> None:
        result = validate_meta(_make_meta(name="my plugin"))
        assert result.is_valid is False

    def test_valid_kebab_names(self) -> None:
        for name in ("a", "my-plugin", "sensor-v2", "x1-y2-z3"):
            result = validate_meta(_make_meta(name=name))
            assert result.is_valid is True, f"'{name}' should be valid"

    def test_empty_version(self) -> None:
        result = validate_meta(_make_meta(version=""))
        assert result.is_valid is False

    def test_invalid_version(self) -> None:
        for v in ("1.0", "v1.0.0", "1", "abc", "1.0.0.0"):
            result = validate_meta(_make_meta(version=v))
            assert result.is_valid is False, f"'{v}' should be invalid"

    def test_valid_semver(self) -> None:
        for v in ("0.0.1", "1.0.0", "2.3.4", "1.0.0-alpha", "1.0.0+build"):
            result = validate_meta(_make_meta(version=v))
            assert result.is_valid is True, f"'{v}' should be valid"

    def test_empty_entry_point(self) -> None:
        result = validate_meta(_make_meta(entry_point=""))
        assert result.is_valid is False

    def test_whitespace_entry_point(self) -> None:
        result = validate_meta(_make_meta(entry_point="   "))
        assert result.is_valid is False

    def test_warning_empty_description(self) -> None:
        result = validate_meta(_make_meta(description=""))
        assert result.is_valid is True
        assert any("description" in w for w in result.warnings)

    def test_warning_empty_author(self) -> None:
        result = validate_meta(_make_meta(author=""))
        assert result.is_valid is True
        assert any("author" in w for w in result.warnings)

    def test_multiple_errors(self) -> None:
        result = validate_meta(
            _make_meta(name="", version="bad", entry_point=""),
        )
        assert result.is_valid is False
        assert len(result.errors) >= 3


# ── PluginRegistry.register / get / unregister ───────────────────────

class TestRegistryBasic:

    def test_register_and_get(self) -> None:
        reg = PluginRegistry()
        meta = _make_meta()
        result = reg.register(meta)
        assert result.is_valid is True
        assert reg.get("my-plugin") is meta

    def test_register_returns_validation_on_invalid(self) -> None:
        reg = PluginRegistry()
        result = reg.register(_make_meta(name="BAD"))
        assert result.is_valid is False
        assert reg.get("BAD") is None

    def test_duplicate_registration(self) -> None:
        reg = PluginRegistry()
        reg.register(_make_meta())
        result = reg.register(_make_meta())
        assert result.is_valid is False
        assert any("already registered" in e for e in result.errors)

    def test_get_nonexistent(self) -> None:
        reg = PluginRegistry()
        assert reg.get("nope") is None

    def test_unregister_existing(self) -> None:
        reg = PluginRegistry()
        reg.register(_make_meta())
        assert reg.unregister("my-plugin") is True
        assert reg.get("my-plugin") is None

    def test_unregister_nonexistent(self) -> None:
        reg = PluginRegistry()
        assert reg.unregister("nope") is False

    def test_register_warns_missing_dependency(self) -> None:
        reg = PluginRegistry()
        meta = _make_meta(dependencies=("not-here",))
        result = reg.register(meta)
        assert result.is_valid is True
        assert any("not-here" in w for w in result.warnings)

    def test_register_no_warning_when_dep_present(self) -> None:
        reg = PluginRegistry()
        reg.register(_make_meta(name="dep-a"))
        result = reg.register(
            _make_meta(name="main-plugin", dependencies=("dep-a",)),
        )
        assert result.is_valid is True
        dep_warnings = [w for w in result.warnings if "dep-a" in w]
        assert len(dep_warnings) == 0


# ── PluginRegistry.list_plugins ──────────────────────────────────────

class TestRegistryList:

    def test_list_empty(self) -> None:
        reg = PluginRegistry()
        assert reg.list_plugins() == ()

    def test_list_all(self) -> None:
        reg = PluginRegistry()
        reg.register(_make_meta(name="a"))
        reg.register(_make_meta(name="b"))
        result = reg.list_plugins()
        assert len(result) == 2

    def test_list_returns_tuple(self) -> None:
        reg = PluginRegistry()
        reg.register(_make_meta())
        result = reg.list_plugins()
        assert isinstance(result, tuple)

    def test_list_filter_by_type(self) -> None:
        reg = PluginRegistry()
        reg.register(_make_meta(name="s1", plugin_type=PluginType.SCENARIO))
        reg.register(_make_meta(name="u1", plugin_type=PluginType.UI_PANEL))
        reg.register(_make_meta(name="s2", plugin_type=PluginType.SCENARIO))
        scenarios = reg.list_plugins(PluginType.SCENARIO)
        assert len(scenarios) == 2
        assert all(p.plugin_type == PluginType.SCENARIO for p in scenarios)

    def test_list_filter_no_match(self) -> None:
        reg = PluginRegistry()
        reg.register(_make_meta(plugin_type=PluginType.SENSOR))
        assert reg.list_plugins(PluginType.ANALYTICS) == ()


# ── PluginRegistry dependency resolution ─────────────────────────────

class TestDependencyResolution:

    def test_no_deps(self) -> None:
        reg = PluginRegistry()
        reg.register(_make_meta(name="solo"))
        deps = reg.resolve_dependencies("solo")
        assert deps == ("solo",)

    def test_linear_chain(self) -> None:
        reg = PluginRegistry()
        reg.register(_make_meta(name="a"))
        reg.register(_make_meta(name="b", dependencies=("a",)))
        reg.register(_make_meta(name="c", dependencies=("b",)))
        deps = reg.resolve_dependencies("c")
        assert deps is not None
        assert deps.index("a") < deps.index("b") < deps.index("c")

    def test_diamond_deps(self) -> None:
        reg = PluginRegistry()
        reg.register(_make_meta(name="base"))
        reg.register(_make_meta(name="left", dependencies=("base",)))
        reg.register(_make_meta(name="right", dependencies=("base",)))
        reg.register(
            _make_meta(name="top", dependencies=("left", "right")),
        )
        deps = reg.resolve_dependencies("top")
        assert deps is not None
        assert deps.index("base") < deps.index("left")
        assert deps.index("base") < deps.index("right")
        assert deps.index("left") < deps.index("top")
        assert deps.index("right") < deps.index("top")
        assert len(set(deps)) == len(deps)

    def test_resolve_nonexistent(self) -> None:
        reg = PluginRegistry()
        assert reg.resolve_dependencies("nope") is None

    def test_circular_direct(self) -> None:
        reg = PluginRegistry()
        reg.register(_make_meta(name="a", dependencies=("b",)))
        reg.register(_make_meta(name="b", dependencies=("a",)))
        assert reg.has_circular_deps("a") is True
        assert reg.resolve_dependencies("a") is None

    def test_circular_indirect(self) -> None:
        reg = PluginRegistry()
        reg.register(_make_meta(name="a", dependencies=("b",)))
        reg.register(_make_meta(name="b", dependencies=("c",)))
        reg.register(_make_meta(name="c", dependencies=("a",)))
        assert reg.has_circular_deps("a") is True

    def test_no_circular_deps(self) -> None:
        reg = PluginRegistry()
        reg.register(_make_meta(name="a"))
        reg.register(_make_meta(name="b", dependencies=("a",)))
        assert reg.has_circular_deps("b") is False

    def test_has_circular_nonexistent(self) -> None:
        reg = PluginRegistry()
        assert reg.has_circular_deps("nope") is False

    def test_deps_with_unregistered_dep(self) -> None:
        reg = PluginRegistry()
        reg.register(_make_meta(name="a", dependencies=("missing",)))
        deps = reg.resolve_dependencies("a")
        assert deps is not None
        assert "a" in deps


# ── PluginType enum ──────────────────────────────────────────────────

class TestPluginType:

    def test_all_types_exist(self) -> None:
        expected = {
            "SCENARIO", "SENSOR", "UI_PANEL", "ANALYTICS", "CONTROLLER",
        }
        actual = {t.name for t in PluginType}
        assert actual == expected

    def test_values(self) -> None:
        assert PluginType.SCENARIO.value == "scenario"
        assert PluginType.UI_PANEL.value == "ui_panel"


# ── CLI parser ───────────────────────────────────────────────────────

class TestCLI:

    def test_parser_list(self) -> None:
        parser = build_cli_parser()
        args = parser.parse_args(["--list"])
        assert args.list is True

    def test_parser_validate(self) -> None:
        parser = build_cli_parser()
        args = parser.parse_args(["--validate", "my-plugin"])
        assert args.validate == "my-plugin"

    def test_parser_deps(self) -> None:
        parser = build_cli_parser()
        args = parser.parse_args(["--deps", "my-plugin"])
        assert args.deps == "my-plugin"

    def test_parser_json_flag(self) -> None:
        parser = build_cli_parser()
        args = parser.parse_args(["--list", "--json"])
        assert args.json is True

    def test_parser_type_filter(self) -> None:
        parser = build_cli_parser()
        args = parser.parse_args(["--list", "--type", "SCENARIO"])
        assert args.type == "SCENARIO"

    def test_cli_list_empty_json(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "simulation.plugin_sdk", "--list", "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data == []

    def test_cli_no_args_exits_nonzero(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "simulation.plugin_sdk"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        assert result.returncode != 0
