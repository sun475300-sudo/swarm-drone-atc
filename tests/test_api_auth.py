"""api/auth.py 단위 테스트 — Phase P712."""
from __future__ import annotations

import time

import pytest

# SDACS_JWT_SECRET 환경변수 없이도 테스트 가능하도록 monkeypatch 사용


@pytest.fixture(autouse=True)
def set_secret(monkeypatch):
    monkeypatch.setenv("SDACS_JWT_SECRET", "test-secret-key-for-unit-tests-1234")
    # 캐시 초기화
    import api.auth as _auth
    _auth._SECRET = None
    yield
    _auth._SECRET = None


# ---------------------------------------------------------------------------
# Role 계층
# ---------------------------------------------------------------------------

class TestRole:
    def test_viewer_rank_lowest(self):
        from api.auth import Role, _ROLE_RANK
        assert _ROLE_RANK[Role.VIEWER] < _ROLE_RANK[Role.OPERATOR]

    def test_admin_rank_highest(self):
        from api.auth import Role, _ROLE_RANK
        assert _ROLE_RANK[Role.ADMIN] > _ROLE_RANK[Role.OPERATOR]

    def test_has_permission_same_role(self):
        from api.auth import Role, _has_permission
        assert _has_permission(Role.OPERATOR, Role.OPERATOR)

    def test_has_permission_higher(self):
        from api.auth import Role, _has_permission
        assert _has_permission(Role.ADMIN, Role.VIEWER)

    def test_has_permission_lower_fails(self):
        from api.auth import Role, _has_permission
        assert not _has_permission(Role.VIEWER, Role.ADMIN)


# ---------------------------------------------------------------------------
# JWT 발급 / 검증
# ---------------------------------------------------------------------------

class TestJWT:
    def test_issue_and_decode_roundtrip(self):
        from api.auth import Role, decode_token, issue_token
        token = issue_token("user@test.com", Role.OPERATOR)
        payload = decode_token(token)
        assert payload["sub"] == "user@test.com"
        assert payload["role"] == "operator"

    def test_token_has_exp(self):
        from api.auth import Role, decode_token, issue_token
        token = issue_token("u", Role.VIEWER, expiry_s=3600)
        payload = decode_token(token)
        assert payload["exp"] > int(time.time())

    def test_expired_token_raises(self):
        from fastapi import HTTPException
        from api.auth import Role, decode_token, issue_token
        token = issue_token("u", Role.VIEWER, expiry_s=-1)
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)
        assert exc_info.value.status_code == 401

    def test_tampered_signature_raises(self):
        from fastapi import HTTPException
        from api.auth import Role, decode_token, issue_token
        token = issue_token("u", Role.ADMIN)
        parts = token.split(".")
        parts[2] = parts[2][:-4] + "XXXX"
        tampered = ".".join(parts)
        with pytest.raises(HTTPException) as exc_info:
            decode_token(tampered)
        assert exc_info.value.status_code == 401

    def test_malformed_token_raises(self):
        from fastapi import HTTPException
        from api.auth import decode_token
        with pytest.raises(HTTPException) as exc_info:
            decode_token("not.a.valid.jwt.token")
        assert exc_info.value.status_code == 401

    def test_wrong_secret_raises(self, monkeypatch):
        from fastapi import HTTPException
        import api.auth as _auth
        from api.auth import Role, issue_token, decode_token
        token = issue_token("u", Role.VIEWER)
        monkeypatch.setenv("SDACS_JWT_SECRET", "different-secret-key-xxxx-yyyy-zzzz")
        _auth._SECRET = None
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# 감사 로그
# ---------------------------------------------------------------------------

class TestAuditLog:
    def setup_method(self):
        import api.auth as _auth
        _auth._AUDIT_LOG.clear()

    def test_audit_log_appended(self):
        from api.auth import Role, TokenUser, audit_log, get_audit_log
        user = TokenUser("a@test.com", Role.OPERATOR)
        audit_log(user, "scenario.run", "id=01")
        logs = get_audit_log(limit=10)
        assert len(logs) == 1
        assert logs[0]["action"] == "scenario.run"
        assert logs[0]["sub"] == "a@test.com"

    def test_audit_log_limit(self):
        from api.auth import Role, TokenUser, audit_log, get_audit_log
        user = TokenUser("b@test.com", Role.VIEWER)
        for _ in range(5):
            audit_log(user, "read", "")
        logs = get_audit_log(limit=2)
        assert len(logs) == 2

    def test_audit_log_max_size(self):
        import api.auth as _auth
        from api.auth import Role, TokenUser, audit_log
        user = TokenUser("c@test.com", Role.ADMIN)
        for _ in range(_auth._AUDIT_MAX + 5):
            audit_log(user, "x", "")
        assert len(_auth._AUDIT_LOG) <= _auth._AUDIT_MAX


# ---------------------------------------------------------------------------
# FastAPI dependency integration
# ---------------------------------------------------------------------------

class TestFastAPIIntegration:
    """require_role 의존성 동작 확인."""

    @pytest.fixture
    def async_client(self):
        pytest.importorskip("httpx")
        from fastapi.testclient import TestClient
        import api.auth as _auth
        from api.auth import Role, issue_token

        # minimal FastAPI app for testing the dependency
        from fastapi import FastAPI, Depends
        mini = FastAPI()

        @mini.get("/protected")
        async def protected(user=Depends(_auth.require_role(Role.OPERATOR))):
            return {"sub": user.sub, "role": user.role.value}

        return TestClient(mini), issue_token

    def test_operator_can_access(self, async_client):
        from api.auth import Role
        client, issue_token = async_client
        token = issue_token("op@test.com", Role.OPERATOR)
        resp = client.get("/protected", headers={"authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "operator"

    def test_viewer_cannot_access_operator_endpoint(self, async_client):
        from api.auth import Role
        client, issue_token = async_client
        token = issue_token("viewer@test.com", Role.VIEWER)
        resp = client.get("/protected", headers={"authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_missing_token_returns_401(self, async_client):
        client, _ = async_client
        resp = client.get("/protected")
        assert resp.status_code == 401

    def test_admin_can_access_operator_endpoint(self, async_client):
        from api.auth import Role
        client, issue_token = async_client
        token = issue_token("admin@test.com", Role.ADMIN)
        resp = client.get("/protected", headers={"authorization": f"Bearer {token}"})
        assert resp.status_code == 200
