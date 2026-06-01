"""P712 — JWT/RBAC 인증 모듈 단위 테스트."""
from __future__ import annotations

import time

import pytest

try:
    import jwt as pyjwt
    pyjwt.encode({"t": 1}, "k", algorithm="HS256")  # probe: catches broken Rust bindings
    _HAS_JWT = True
except Exception:
    _HAS_JWT = False

from api.auth import Role, TokenPayload, _decode_token, create_token, get_audit_log, audit


@pytest.mark.skipif(not _HAS_JWT, reason="PyJWT not installed")
class TestCreateToken:
    def test_returns_string(self):
        token = create_token("user1", Role.viewer)
        assert isinstance(token, str)
        assert len(token) > 20

    def test_payload_fields(self):
        token = create_token("alice", Role.operator)
        payload = _decode_token(token)
        assert payload.sub == "alice"
        assert payload.role == Role.operator
        assert payload.exp > payload.iat

    def test_expired_token_raises(self, monkeypatch):
        import api.auth as auth_mod
        monkeypatch.setattr(auth_mod, "_TOKEN_TTL", -1)
        token = create_token("bob", Role.viewer)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _decode_token(token)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail

    def test_invalid_token_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _decode_token("not.a.valid.token")
        assert exc_info.value.status_code == 401

    def test_admin_role(self):
        token = create_token("admin", Role.admin)
        payload = _decode_token(token)
        assert payload.role == Role.admin


class TestAuditLog:
    def test_audit_appends_entry(self):
        before = len(get_audit_log(1000))
        audit("test_event", "test_user", "detail_value")
        after = len(get_audit_log(1000))
        assert after == before + 1

    def test_audit_entry_fields(self):
        audit("login", "charlie", "ip=1.2.3.4")
        log = get_audit_log(1)
        entry = log[-1]
        assert entry["event"] == "login"
        assert entry["sub"] == "charlie"
        assert entry["detail"] == "ip=1.2.3.4"
        assert "ts" in entry

    def test_get_audit_log_limit(self):
        for i in range(5):
            audit(f"evt_{i}", "user", None)
        result = get_audit_log(3)
        assert len(result) <= 3
