"""P712 — Tests for OAuth2/RBAC auth layer (api/auth.py)."""
from __future__ import annotations

import time

import pytest

pytest.importorskip("fastapi", reason="fastapi required for P712 auth tests")

from api.auth import (  # noqa: E402
    AuditEntry,
    AuthContext,
    Role,
    TokenRequest,
    _hash_pw,
    _USERS,
    create_token,
    get_audit_log,
    role_gte,
    verify_token,
    _audit,
)
from fastapi import HTTPException  # noqa: E402


# ---------------------------------------------------------------------------
# Role hierarchy
# ---------------------------------------------------------------------------

class TestRoleHierarchy:
    def test_admin_gte_all(self):
        assert role_gte(Role.ADMIN, Role.VIEWER)
        assert role_gte(Role.ADMIN, Role.OPERATOR)
        assert role_gte(Role.ADMIN, Role.ADMIN)

    def test_operator_gte_viewer(self):
        assert role_gte(Role.OPERATOR, Role.VIEWER)
        assert role_gte(Role.OPERATOR, Role.OPERATOR)
        assert not role_gte(Role.OPERATOR, Role.ADMIN)

    def test_viewer_only_viewer(self):
        assert role_gte(Role.VIEWER, Role.VIEWER)
        assert not role_gte(Role.VIEWER, Role.OPERATOR)
        assert not role_gte(Role.VIEWER, Role.ADMIN)


# ---------------------------------------------------------------------------
# JWT create / verify
# ---------------------------------------------------------------------------

class TestJWT:
    def test_round_trip(self):
        token = create_token("alice", Role.OPERATOR)
        payload = verify_token(token)
        assert payload["sub"] == "alice"
        assert payload["role"] == "operator"

    def test_admin_round_trip(self):
        token = create_token("bob", Role.ADMIN)
        payload = verify_token(token)
        assert payload["role"] == "admin"

    def test_extra_claims(self):
        token = create_token("svc", Role.VIEWER, extra={"tenant": "acme"})
        payload = verify_token(token)
        assert payload["tenant"] == "acme"

    def test_expired_token_raises(self):
        token = create_token("x", Role.VIEWER, ttl_s=-1)
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail

    def test_bad_signature_raises(self):
        token = create_token("x", Role.VIEWER)
        tampered = token[:-4] + "XXXX"
        with pytest.raises(HTTPException) as exc_info:
            verify_token(tampered)
        assert exc_info.value.status_code == 401

    def test_malformed_token_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            verify_token("not.a.jwt.value.extra")
        assert exc_info.value.status_code == 401

    def test_jti_is_unique(self):
        t1 = create_token("x", Role.VIEWER)
        t2 = create_token("x", Role.VIEWER)
        p1 = verify_token(t1)
        p2 = verify_token(t2)
        assert p1["jti"] != p2["jti"]


# ---------------------------------------------------------------------------
# Password hash
# ---------------------------------------------------------------------------

class TestPasswordHash:
    def test_consistent(self):
        assert _hash_pw("abc") == _hash_pw("abc")

    def test_different_passwords(self):
        assert _hash_pw("abc") != _hash_pw("xyz")


# ---------------------------------------------------------------------------
# User store
# ---------------------------------------------------------------------------

class TestUserStore:
    def test_default_users_exist(self):
        assert "admin" in _USERS
        assert "operator" in _USERS
        assert "viewer" in _USERS

    def test_admin_role(self):
        assert _USERS["admin"].role == Role.ADMIN

    def test_operator_role(self):
        assert _USERS["operator"].role == Role.OPERATOR

    def test_viewer_role(self):
        assert _USERS["viewer"].role == Role.VIEWER


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

class TestAuditLog:
    def test_audit_entries_recorded(self):
        before = len(get_audit_log(1000))
        _audit("testuser", "admin", "test_action", outcome="ok")
        after_entries = get_audit_log(1000)
        assert len(after_entries) > before

    def test_audit_entry_fields(self):
        _audit("u1", "viewer", "read", resource="/api/x", outcome="ok", detail="info")
        entry = get_audit_log(1)[0]
        assert entry["sub"] == "u1"
        assert entry["role"] == "viewer"
        assert entry["action"] == "read"
        assert entry["resource"] == "/api/x"
        assert entry["outcome"] == "ok"

    def test_get_audit_log_limit(self):
        for i in range(10):
            _audit(f"user{i}", "viewer", "ping")
        result = get_audit_log(3)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# FastAPI route integration (via TestClient)
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from api.auth import auth_router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(auth_router)
    return TestClient(app)


class TestAuthRoutes:
    def test_issue_token_admin(self, client):
        resp = client.post("/auth/token", json={"username": "admin", "password": "admin123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["role"] == "admin"

    def test_issue_token_operator(self, client):
        resp = client.post("/auth/token", json={"username": "operator", "password": "op123"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "operator"

    def test_issue_token_viewer(self, client):
        resp = client.post("/auth/token", json={"username": "viewer", "password": "view123"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "viewer"

    def test_bad_password_401(self, client):
        resp = client.post("/auth/token", json={"username": "admin", "password": "wrong"})
        assert resp.status_code == 401

    def test_unknown_user_401(self, client):
        resp = client.post("/auth/token", json={"username": "ghost", "password": "x"})
        assert resp.status_code == 401

    def test_whoami(self, client):
        token_resp = client.post("/auth/token", json={"username": "admin", "password": "admin123"})
        token = token_resp.json()["access_token"]
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["sub"] == "admin"
        assert resp.json()["role"] == "admin"

    def test_whoami_no_token_401(self, client):
        resp = client.get("/auth/me")
        assert resp.status_code == 401

    def test_refresh_token(self, client):
        token_resp = client.post("/auth/token", json={"username": "viewer", "password": "view123"})
        old_token = token_resp.json()["access_token"]
        resp = client.post("/auth/refresh", json={"token": old_token})
        assert resp.status_code == 200
        new_token = resp.json()["access_token"]
        assert new_token != old_token

    def test_audit_requires_admin(self, client):
        token_resp = client.post("/auth/token", json={"username": "viewer", "password": "view123"})
        token = token_resp.json()["access_token"]
        resp = client.get("/auth/audit", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_audit_accessible_by_admin(self, client):
        token_resp = client.post("/auth/token", json={"username": "admin", "password": "admin123"})
        token = token_resp.json()["access_token"]
        resp = client.get("/auth/audit", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["success"] is True
