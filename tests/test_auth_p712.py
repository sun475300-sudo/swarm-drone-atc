"""P712 — JWT/RBAC 인증 모듈 테스트."""
from __future__ import annotations

import time

import pytest

from api.auth import (
    ALL_ROLES,
    ROLE_PERMISSIONS,
    UserRecord,
    authenticate_user,
    create_access_token,
    create_user,
    decode_token,
    get_user,
    verify_password,
)


# ---------------------------------------------------------------------------
# 패스워드 검증
# ---------------------------------------------------------------------------


def test_verify_password_correct():
    from passlib.context import CryptContext

    ctx = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
    hashed = ctx.hash("mypassword")
    assert verify_password("mypassword", hashed) is True


def test_verify_password_wrong():
    from passlib.context import CryptContext

    ctx = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
    hashed = ctx.hash("mypassword")
    assert verify_password("wrongpassword", hashed) is False


# ---------------------------------------------------------------------------
# 사용자 조회 및 인증
# ---------------------------------------------------------------------------


def test_get_user_exists():
    user = get_user("admin")
    assert user is not None
    assert user.username == "admin"
    assert user.role == "admin"


def test_get_user_missing():
    assert get_user("no_such_user_xyz") is None


def test_authenticate_user_success():
    user = authenticate_user("admin", "admin")
    assert user is not None
    assert user.username == "admin"


def test_authenticate_user_wrong_password():
    assert authenticate_user("admin", "wrongpass") is None


def test_authenticate_user_missing():
    assert authenticate_user("ghost", "pass") is None


# ---------------------------------------------------------------------------
# 사용자 생성
# ---------------------------------------------------------------------------


def test_create_user_new():
    username = f"test_user_{int(time.time())}"
    user = create_user(username, "supersecret1", "pilot")
    assert user.username == username
    assert user.role == "pilot"

    # 재인증 가능해야 함
    auth = authenticate_user(username, "supersecret1")
    assert auth is not None


def test_create_user_duplicate_raises():
    with pytest.raises(ValueError, match="already exists"):
        create_user("admin", "pass", "observer")


def test_create_user_invalid_role():
    with pytest.raises(ValueError, match="unknown role"):
        create_user("newbie", "pass1234", "superadmin")


# ---------------------------------------------------------------------------
# JWT 토큰 생성·디코딩
# ---------------------------------------------------------------------------


def test_create_and_decode_token():
    token = create_access_token({"sub": "admin", "role": "admin"})
    payload = decode_token(token)
    assert payload["sub"] == "admin"
    assert payload["role"] == "admin"
    assert "exp" in payload
    assert "iat" in payload


def test_decode_expired_token():
    from datetime import timedelta
    from fastapi import HTTPException

    # exp를 -1초로 설정해서 이미 만료된 토큰 생성
    token = create_access_token({"sub": "admin"}, expires_delta=timedelta(seconds=-1))
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)
    assert exc_info.value.status_code == 401


def test_decode_invalid_signature():
    from fastapi import HTTPException

    # 유효한 토큰에서 서명을 변조
    token = create_access_token({"sub": "admin"})
    parts = token.split(".")
    tampered = f"{parts[0]}.{parts[1]}.invalidsignatureXXX"
    with pytest.raises(HTTPException) as exc_info:
        decode_token(tampered)
    assert exc_info.value.status_code == 401


def test_decode_invalid_format():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        decode_token("not-a-jwt-at-all")
    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# RBAC 권한 확인
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "role,permission,expected",
    [
        ("admin", "airspace:read", True),
        ("admin", "admin:users", True),
        ("atc_operator", "airspace:read", True),
        ("atc_operator", "scenario:run", True),
        ("atc_operator", "admin:users", False),
        ("pilot", "airspace:write", True),
        ("pilot", "scenario:run", False),
        ("pilot", "admin:users", False),
        ("observer", "airspace:read", True),
        ("observer", "airspace:write", False),
        ("observer", "scenario:run", False),
    ],
)
def test_rbac_permissions(role: str, permission: str, expected: bool):
    from passlib.context import CryptContext

    ctx = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
    user = UserRecord(
        username="test",
        hashed_password=ctx.hash("x"),
        role=role,
    )
    assert user.has_permission(permission) is expected


def test_all_roles_defined():
    assert ALL_ROLES == frozenset({"admin", "atc_operator", "pilot", "observer"})


def test_role_permissions_non_empty():
    for role, perms in ROLE_PERMISSIONS.items():
        assert len(perms) > 0, f"role {role} has no permissions"
