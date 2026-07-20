"""Security regression for SDACS_PROD JWT secret enforcement (3차 점검 #1).

`api.auth._resolve_jwt_secret` 가 SDACS_PROD=1 환경에서 SDACS_JWT_SECRET
누락 시 RuntimeError 를 발생시키는지 검증한다.
"""
from __future__ import annotations

import importlib

import pytest

pytest.importorskip("fastapi", reason="fastapi required for auth secret tests")


_ACCOUNT_ENV = ("SDACS_ADMIN_PASSWORD", "SDACS_OPERATOR_PASSWORD", "SDACS_VIEWER_PASSWORD")


def _set_account_passwords(monkeypatch):
    """SDACS_PROD 모드는 계정 비밀번호도 요구하므로 JWT 게이트 격리를 위해 주입."""
    for key in _ACCOUNT_ENV:
        monkeypatch.setenv(key, "strong-" + "y" * 24)


def _reload_auth(monkeypatch, prod: str | None, secret: str | None):
    """Reload api.auth 모듈로 import-time 환경변수 평가를 재실행."""
    if prod is None:
        monkeypatch.delenv("SDACS_PROD", raising=False)
    else:
        monkeypatch.setenv("SDACS_PROD", prod)
        _set_account_passwords(monkeypatch)
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


def test_prod_mode_requires_account_passwords(monkeypatch):
    """SDACS_PROD=1 + JWT SECRET 있음 + 계정 비밀번호 누락 → RuntimeError.

    기본 개발 자격증명(admin123 등)으로 운영 배포되는 사고를 차단한다.
    """
    monkeypatch.setenv("SDACS_PROD", "1")
    monkeypatch.setenv("SDACS_JWT_SECRET", "x" * 64)
    for key in _ACCOUNT_ENV:
        monkeypatch.delenv(key, raising=False)
    import api.auth as mod
    with pytest.raises(RuntimeError, match="SDACS_ADMIN_PASSWORD"):
        importlib.reload(mod)
    # 복구: 이후 테스트가 깨지지 않게 dev 모드로 reload
    monkeypatch.delenv("SDACS_PROD", raising=False)
    monkeypatch.delenv("SDACS_JWT_SECRET", raising=False)
    importlib.reload(mod)


def test_prod_mode_rejects_default_dev_password(monkeypatch):
    """SDACS_PROD=1 에서 기본 dev 비밀번호는 해시가 달라 로그인에 쓰일 수 없다."""
    mod = _reload_auth(monkeypatch, prod="1", secret="x" * 64)
    admin = mod._USERS["admin"]
    assert admin.password_hash != mod._hash_pw("admin123", admin.salt)
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
