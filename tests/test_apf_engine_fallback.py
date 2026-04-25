"""apf_engine torch fallback 회귀 방지 테스트.

배경: 2026-04-26 Windows Application Control이 torch DLL을 차단하면서
apf_engine 초기화가 OSError로 깨지는 회귀 발견. (`docs/REGRESSION_NOTES_2026-04-26.md`)

이 테스트는 graceful fallback 계약을 강제한다:
- apf_engine 모듈은 torch 미설치/로드 실패와 무관하게 import 성공해야 한다.
- batch_compute_forces는 torch가 없어도 NumPy CPU 경로로 동작해야 한다.
- get_apf_backend_info는 사전에 정의된 키를 항상 반환해야 한다.
"""
from __future__ import annotations

import importlib
import sys

import numpy as np
import pytest


def test_apf_engine_imports_without_torch(monkeypatch):
    """torch import가 OSError로 깨져도 apf_engine 모듈은 정상 로드되어야 한다."""

    # apf_engine과 apf_gpu를 캐시에서 제거하여 재로드 강제
    for mod in [
        "simulation.apf_engine",
        "simulation.apf_engine.apf_gpu",
    ]:
        sys.modules.pop(mod, None)

    real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

    def blocking_import(name, *args, **kwargs):
        if name == "torch" or name.startswith("torch."):
            raise OSError("simulated WinError 4551 — DLL blocked")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", blocking_import)

    apf_engine = importlib.import_module("simulation.apf_engine")
    assert hasattr(apf_engine, "batch_compute_forces")
    assert hasattr(apf_engine, "get_apf_backend_info")


def test_backend_info_reports_cpu_when_torch_unavailable(monkeypatch):
    """torch 로드 실패 시 backend_info는 numpy-cpu로 보고해야 한다."""

    for mod in [
        "simulation.apf_engine",
        "simulation.apf_engine.apf_gpu",
    ]:
        sys.modules.pop(mod, None)

    real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

    def blocking_import(name, *args, **kwargs):
        if name == "torch" or name.startswith("torch."):
            raise OSError("simulated DLL block")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", blocking_import)

    apf_engine = importlib.import_module("simulation.apf_engine")
    info = apf_engine.get_apf_backend_info()

    assert isinstance(info, dict)
    assert info.get("backend") == "numpy-cpu"
    assert info.get("device") == "cpu"
    assert info.get("gpu") is None


def test_batch_compute_forces_callable_with_empty_input(monkeypatch):
    """torch 없이도 batch_compute_forces가 빈 입력에 대해 dict를 반환해야 한다."""

    for mod in [
        "simulation.apf_engine",
        "simulation.apf_engine.apf_gpu",
    ]:
        sys.modules.pop(mod, None)

    real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

    def blocking_import(name, *args, **kwargs):
        if name == "torch" or name.startswith("torch."):
            raise OSError("simulated DLL block")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", blocking_import)

    apf_engine = importlib.import_module("simulation.apf_engine")
    result = apf_engine.batch_compute_forces(states=[], goals={}, obstacles=[])
    assert isinstance(result, dict)


def test_real_environment_does_not_crash():
    """현재 환경에서 apf_engine 일반 사용이 정상 동작해야 한다 (smoke).

    monkeypatch 없이 실제 import를 사용 — torch가 깔려있든 아니든
    fallback이 정상 작동하면 통과한다.
    """
    # 캐시된 상태가 있을 수 있으니 그대로 사용
    from simulation.apf_engine import (
        batch_compute_forces,
        get_apf_backend_info,
    )

    info = get_apf_backend_info()
    assert "backend" in info
    assert "device" in info

    result = batch_compute_forces(states=[], goals={}, obstacles=[])
    assert isinstance(result, dict)
