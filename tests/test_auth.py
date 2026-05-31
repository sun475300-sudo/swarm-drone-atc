"""Tests for P712 — api/auth.py JWT + RBAC."""
from __future__ import annotations

import os
import time

import pytest

os.environ.setdefault("SDACS_JWT_SECRET", "test-secret-do-not-use")
os.environ.setdefault("SDACS_AUDIT_LOG", "/tmp/test_audit.jsonl")


def _import() -> tuple:
    from api.auth import AuthContext, Role, _decode_token, _ROLE_PERMISSIONS, create_token
    return AuthContext, Role, _decode_token, _ROLE_PERMISSIONS, create_token


class TestRoles:
    def test_admin_has_all_permissions(self) -> None:
        _, Role, _, perms, _ = _import()
        assert {"read", "write", "run", "admin"} == perms[Role.admin]

    def test_operator_lacks_admin(self) -> None:
        _, Role, _, perms, _ = _import()
        assert "admin" not in perms[Role.operator]
        assert "run" in perms[Role.operator]

    def test_viewer_read_only(self) -> None:
        _, Role, _, perms, _ = _import()
        assert perms[Role.viewer] == frozenset({"read"})


class TestCreateToken:
    def test_round_trip(self) -> None:
        AuthContext, Role, decode, _, create = _import()
        token = create("alice", Role.operator)
        payload = decode(token)
        assert payload["sub"] == "alice"
        assert payload["role"] == "operator"

    def test_expiry_in_future(self) -> None:
        _, Role, decode, _, create = _import()
        token = create("bob", Role.viewer)
        payload = decode(token)
        assert payload["exp"] > time.time()

    def test_extra_claims(self) -> None:
        _, Role, decode, _, create = _import()
        token = create("carol", Role.admin, extra={"org": "sdacs"})
        payload = decode(token)
        assert payload["org"] == "sdacs"


class TestDecodeToken:
    def test_invalid_token_raises_401(self) -> None:
        from fastapi import HTTPException
        _, _, decode, _, _ = _import()
        with pytest.raises(HTTPException) as exc_info:
            decode("not.a.token")
        assert exc_info.value.status_code == 401

    def test_wrong_secret_raises_401(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from fastapi import HTTPException
        import api.auth as auth_mod
        _, Role, _, _, create = _import()
        token = create("dave", Role.viewer)
        monkeypatch.setattr(auth_mod, "_JWT_SECRET", "wrong-secret")
        with pytest.raises(HTTPException) as exc_info:
            auth_mod._decode_token(token)
        assert exc_info.value.status_code == 401


class TestAuthContext:
    def test_require_allowed(self) -> None:
        AuthContext, Role, decode, _, create = _import()
        token = create("eve", Role.operator)
        payload = decode(token)
        ctx = AuthContext(subject="eve", role=Role.operator, _payload=payload)
        ctx.require("run")  # should not raise

    def test_require_denied(self) -> None:
        from fastapi import HTTPException
        AuthContext, Role, decode, _, create = _import()
        token = create("frank", Role.viewer)
        payload = decode(token)
        ctx = AuthContext(subject="frank", role=Role.viewer, _payload=payload)
        with pytest.raises(HTTPException) as exc_info:
            ctx.require("run")
        assert exc_info.value.status_code == 403
