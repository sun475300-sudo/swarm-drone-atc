"""P712 — JWT/RBAC 인증 모듈 테스트."""

from __future__ import annotations

import os
import time

import pytest

os.environ.setdefault("SDACS_JWT_SECRET", "test-secret-key")
os.environ.setdefault("SDACS_JWT_EXPIRE_S", "3600")

from api.auth import (
    ROLES,
    TokenPayload,
    _ROLE_RANK,
    _JWT_SECRET,
    _audit,
    _AUDIT_LOG,
    _jwt_sign,
    _jwt_verify,
    create_access_token,
    get_audit_log,
    require_role,
)


# --- 토큰 생성 ---

class TestCreateAccessToken:
    def test_returns_string(self):
        token = create_access_token("user1", "viewer")
        assert isinstance(token, str)
        assert token.count(".") == 2

    def test_payload_fields(self):
        token = create_access_token("alice", "admin")
        data = _jwt_verify(token)
        assert data["sub"] == "alice"
        assert data["role"] == "admin"
        assert "exp" in data
        assert "iat" in data

    def test_invalid_role_raises(self):
        with pytest.raises(ValueError, match="invalid role"):
            create_access_token("user", "superuser")

    @pytest.mark.parametrize("role", ROLES)
    def test_all_valid_roles(self, role: str):
        token = create_access_token("user", role)
        data = _jwt_verify(token)
        assert data["role"] == role


# --- JWT 서명 검증 ---

class TestJWTVerify:
    def test_tampered_signature_rejected(self):
        token = create_access_token("user", "viewer")
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1] + "." + "invalidsig"
        with pytest.raises(ValueError, match="signature"):
            _jwt_verify(tampered)

    def test_expired_token_rejected(self):
        payload = {"sub": "x", "role": "viewer", "iat": 0, "exp": 1}  # 1970년
        token = _jwt_sign(payload)
        with pytest.raises(ValueError, match="expired"):
            _jwt_verify(token)

    def test_invalid_structure_rejected(self):
        with pytest.raises(ValueError, match="invalid token structure"):
            _jwt_verify("notavalidjwt")


# --- 역할 계층 ---

class TestRoleRank:
    def test_admin_has_lowest_rank(self):
        assert _ROLE_RANK["admin"] < _ROLE_RANK["operator"] < _ROLE_RANK["viewer"]

    def test_roles_tuple_order(self):
        assert ROLES[0] == "admin"
        assert ROLES[-1] == "viewer"


# --- require_role 팩토리 ---

class TestRequireRole:
    def test_returns_depends(self):
        dep = require_role("admin")
        assert dep is not None

    def test_invalid_minimum_role_raises(self):
        with pytest.raises(ValueError, match="unknown role"):
            require_role("superadmin")


# --- 감사 로그 ---

class TestAuditLog:
    def test_get_audit_log_returns_list(self):
        log = get_audit_log(limit=10)
        assert isinstance(log, list)

    def test_limit_respected(self):
        for i in range(20):
            _audit(f"user{i}", "test_action")
        log = get_audit_log(limit=5)
        assert len(log) <= 5

    def test_entries_have_expected_keys(self):
        _audit("tester", "test_event", "detail here")
        entry = get_audit_log(limit=1)[-1]
        assert set(entry.keys()) >= {"ts", "user", "action", "detail"}


# --- 통합: FastAPI TestClient ---

class TestFastAPIAuth:
    @pytest.fixture(autouse=True)
    def client(self):
        try:
            from fastapi.testclient import TestClient
            from api.fastapi_server import app
            self._client = TestClient(app, raise_server_exceptions=False)
        except Exception:
            pytest.skip("FastAPI/uvicorn not available in this env")

    def test_issue_token_success(self):
        os.environ["SDACS_ADMIN_SECRET"] = "test-admin-secret"
        resp = self._client.post("/auth/token", json={
            "sub": "alice",
            "role": "operator",
            "secret": "test-admin-secret",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_issue_token_wrong_secret(self):
        os.environ["SDACS_ADMIN_SECRET"] = "real-secret"
        resp = self._client.post("/auth/token", json={
            "sub": "bob",
            "role": "viewer",
            "secret": "wrong-secret",
        })
        assert resp.status_code == 401

    def test_protected_endpoint_no_token(self):
        resp = self._client.post("/api/scenarios/01/run", json={"seed": 0})
        assert resp.status_code == 401

    def test_protected_endpoint_viewer_rejected(self):
        token = create_access_token("viewer_user", "viewer")
        resp = self._client.post(
            "/api/scenarios/01/run",
            json={"seed": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_metrics_endpoint(self):
        resp = self._client.get("/metrics")
        assert resp.status_code in (200, 503)

    def test_audit_log_requires_admin(self):
        token = create_access_token("op_user", "operator")
        resp = self._client.get(
            "/admin/audit-log",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_audit_log_admin_access(self):
        token = create_access_token("admin_user", "admin")
        resp = self._client.get(
            "/admin/audit-log",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert "entries" in resp.json()
