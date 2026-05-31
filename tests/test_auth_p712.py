"""P712 — JWT/RBAC 인증 단위 테스트."""
from __future__ import annotations

import hashlib
import sys
import time
import types
import pytest

# 깨진 jwt 시스템 패키지 무력화 (HMAC fallback 경로 테스트)
if "jwt" not in sys.modules:
    sys.modules["jwt"] = types.ModuleType("jwt")  # empty module → _HAS_JWT = False

from api.auth import (
    Role, UserRecord, _sha256, _decode_token,
    authenticate_user, create_access_token, _USERS,
)


# --- create_access_token ---

def test_create_token_contains_username():
    token = create_access_token("admin", Role.admin)
    payload = _decode_token(token)
    assert payload["sub"] == "admin"


def test_create_token_contains_role():
    token = create_access_token("viewer", Role.viewer)
    payload = _decode_token(token)
    assert payload["role"] == "viewer"


def test_token_expiry_is_in_future():
    token = create_access_token("operator", Role.operator)
    payload = _decode_token(token)
    assert payload["exp"] > time.time()


# --- authenticate_user ---

def test_authenticate_valid_user():
    import os
    # 기본 admin 패스워드 (env 또는 기본값)
    pw = os.environ.get("ADMIN_PASSWORD", "admin123")
    user = authenticate_user("admin", pw)
    assert user.role == Role.admin


def test_authenticate_wrong_password_raises():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        authenticate_user("admin", "wrongpassword")
    assert exc_info.value.status_code == 401


def test_authenticate_unknown_user_raises():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        authenticate_user("nobody", "anything")
    assert exc_info.value.status_code == 401


# --- RBAC 롤 레벨 ---

def test_role_level_ordering():
    from api.auth import _ROLE_LEVEL
    assert _ROLE_LEVEL[Role.viewer] < _ROLE_LEVEL[Role.operator]
    assert _ROLE_LEVEL[Role.operator] < _ROLE_LEVEL[Role.admin]


# --- _sha256 ---

def test_sha256_deterministic():
    assert _sha256("hello") == _sha256("hello")
    assert _sha256("hello") != _sha256("world")


def test_sha256_length():
    assert len(_sha256("test")) == 64


# --- 감사 로그 ---

def test_audit_log_records_login():
    from api.auth import get_audit_log, _audit
    before = len(get_audit_log())
    _audit("test_action", "test_user", "detail")
    after = len(get_audit_log())
    assert after == before + 1
    entry = get_audit_log()[-1]
    assert entry["action"] == "test_action"
    assert entry["user"] == "test_user"
