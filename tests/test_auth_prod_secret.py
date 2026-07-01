"""Security regression for SDACS_PROD JWT secret enforcement (3차 점검 #1).

`api.auth._resolve_jwt_secret` 가 SDACS_PROD=1 환경에서 SDACS_JWT_SECRET
누락 시 RuntimeError 를 발생시키는지 검증한다.
"""
from __future__ import annotations

import importlib

import pytest

pytest.importorskip("fastapi", reason="fastapi required for auth secret tests")


def _reload_auth(monkeypatch, prod: str | None, secret: str | None):
    """Reload api.auth 모듈로 import-time 환경변수 평가를 재실행."""
    if prod is None:
        monkeypatch.delenv("SDACS_PROD", raising=False)
    else:
        monkeypatch.setenv("SDACS_PROD", prod)
    if secret is None:
        monkeypatch.delenv("SDACS_JWT_SECRET", raising=False)
    else:
        monkeypatch.setenv("SDACS_JWT_SECRET", secret)

    import api.auth as mod
    return importlib.reload(mod)


def test_prod_mode_requires_jwt_secret(monkeypatch):
    """SDACS_PROD=1 + SECRET 누락 → RuntimeError."""
    monkeypatch.delenv("SDACS_JWT_SECRET", raising=False)
    monkeypatch.setenv("SDACS_PROD", "1")
    import api.auth as mod
    with pytest.raises(RuntimeError, match="SDACS_JWT_SECRET"):
        importlib.reload(mod)
    # 복구: 이후 테스트가 깨지지 않게 약한 dev 키로 reload
    monkeypatch.delenv("SDACS_PROD", raising=False)
    importlib.reload(mod)


def test_prod_mode_with_secret_succeeds(monkeypatch):
    """SDACS_PROD=1 + 강한 SECRET → 정상 로드."""
    mod = _reload_auth(monkeypatch, prod="1", secret="x" * 64)
    assert mod._JWT_SECRET == "x" * 64
    # 복구
    monkeypatch.delenv("SDACS_PROD", raising=False)
    monkeypatch.delenv("SDACS_JWT_SECRET", raising=False)
    importlib.reload(mod)


def test_dev_mode_falls_back_with_warning(monkeypatch, caplog):
    """SDACS_PROD 미설정 + SECRET 미설정 → 경고 후 dev 키 사용 (하위 호환)."""
    import logging
    caplog.set_level(logging.WARNING, logger="sdacs.auth")
    mod = _reload_auth(monkeypatch, prod=None, secret=None)
    assert mod._JWT_SECRET == "dev-insecure-secret-change-in-prod"
    assert any("SDACS_JWT_SECRET" in r.message for r in caplog.records)
