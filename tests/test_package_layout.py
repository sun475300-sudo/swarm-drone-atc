"""Module: tests/test_package_layout.py."""

from __future__ import annotations

import importlib


def test_api_package_imports():
    mod = importlib.import_module("api")
    assert mod is not None


def test_runtime_packages_import():
    for name in ("simulation", "visualization", "chatbot", "main"):
        mod = importlib.import_module(name)
        assert mod is not None
