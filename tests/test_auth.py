"""Tests for api/auth.py — P712 JWT authentication."""
from __future__ import annotations

import time

import pytest
from fastapi import HTTPException

from api.auth import (
    JWT_SECRET,
    JWT_TTL_S,
    RoleChecker,
    TokenData,
    _b64url_decode,
    _b64url_encode,
    _sign,
    create_token,
    login,
    requires_role,
    verify_token,
)


# ---------------------------------------------------------------------------
# _b64url helpers
# ---------------------------------------------------------------------------

class TestBase64Url:
    def test_roundtrip(self) -> None:
        data = b"hello world"
        assert _b64url_decode(_b64url_encode(data)) == data

    def test_no_padding_chars(self) -> None:
        encoded = _b64url_encode(b"test")
        assert "=" not in encoded

    def test_url_safe_chars(self) -> None:
        encoded = _b64url_encode(b"\xff\xfe")
        assert "+" not in encoded
        assert "/" not in encoded


# ---------------------------------------------------------------------------
# create_token / verify_token
# ---------------------------------------------------------------------------

class TestCreateVerifyToken:
    def test_valid_token_roundtrip(self) -> None:
        token = create_token("alice", "operator")
        payload = verify_token(token)
        assert payload["sub"] == "alice"
        assert payload["role"] == "operator"

    def test_payload_has_iat_exp(self) -> None:
        before = int(time.time())
        token = create_token("bob", "viewer")
        payload = verify_token(token)
        assert payload["iat"] >= before
        assert payload["exp"] > payload["iat"]

    def test_ttl_respected(self) -> None:
        token = create_token("alice", "admin", ttl_s=3600)
        payload = verify_token(token)
        assert payload["exp"] - payload["iat"] == 3600

    def test_wrong_secret_raises(self) -> None:
        token = create_token("alice", "operator", secret="secret-a")
        with pytest.raises(ValueError, match="invalid signature"):
            verify_token(token, secret="secret-b")

    def test_expired_token_raises(self) -> None:
        token = create_token("alice", "operator", ttl_s=-1)
        with pytest.raises(ValueError, match="expired"):
            verify_token(token)

    def test_malformed_token_raises(self) -> None:
        with pytest.raises(ValueError, match="malformed"):
            verify_token("not.a.valid.jwt.token.with.extra.dots")

    def test_tampered_payload_raises(self) -> None:
        token = create_token("alice", "viewer")
        parts = token.split(".")
        # flip a byte in the payload
        tampered = parts[0] + "." + parts[1][:-2] + "XX" + "." + parts[2]
        with pytest.raises(ValueError):
            verify_token(tampered)

    def test_token_has_three_parts(self) -> None:
        token = create_token("alice", "admin")
        assert token.count(".") == 2


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------

class TestRoleChecker:
    def test_admin_passes_admin(self) -> None:
        requires_role("admin").check(TokenData("u", "admin"))

    def test_admin_passes_operator(self) -> None:
        requires_role("operator").check(TokenData("u", "admin"))

    def test_admin_passes_viewer(self) -> None:
        requires_role("viewer").check(TokenData("u", "admin"))

    def test_operator_fails_admin(self) -> None:
        with pytest.raises(PermissionError):
            requires_role("admin").check(TokenData("u", "operator"))

    def test_operator_passes_operator(self) -> None:
        requires_role("operator").check(TokenData("u", "operator"))

    def test_operator_passes_viewer(self) -> None:
        requires_role("viewer").check(TokenData("u", "operator"))

    def test_viewer_fails_operator(self) -> None:
        with pytest.raises(PermissionError):
            requires_role("operator").check(TokenData("u", "viewer"))

    def test_viewer_fails_admin(self) -> None:
        with pytest.raises(PermissionError):
            requires_role("admin").check(TokenData("u", "viewer"))

    def test_unknown_role_fails_all(self) -> None:
        for role in ("admin", "operator", "viewer"):
            with pytest.raises(PermissionError):
                requires_role(role).check(TokenData("u", "unknown_role"))


# ---------------------------------------------------------------------------
# login()
# ---------------------------------------------------------------------------

class TestLogin:
    def test_correct_credentials_returns_token(self) -> None:
        result = login("operator", "operator")
        assert "access_token" in result
        assert result["token_type"] == "bearer"
        assert result["role"] == "operator"
        assert result["expires_in"] == JWT_TTL_S

    def test_token_is_valid_jwt(self) -> None:
        result = login("admin", "admin")
        payload = verify_token(result["access_token"])
        assert payload["sub"] == "admin"
        assert payload["role"] == "admin"

    def test_wrong_password_raises_401(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            login("admin", "wrongpassword")
        assert exc_info.value.status_code == 401

    def test_unknown_user_raises_401(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            login("nonexistent", "password")
        assert exc_info.value.status_code == 401

    def test_each_role_maps_correctly(self) -> None:
        for username in ("admin", "operator", "viewer"):
            result = login(username, username)
            assert result["role"] == username

    def test_empty_password_raises_401(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            login("admin", "")
        assert exc_info.value.status_code == 401
