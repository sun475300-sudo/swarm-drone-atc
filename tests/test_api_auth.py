"""P712 — JWT + RBAC unit tests."""

from __future__ import annotations

import os
import time

import pytest


# Force a known test secret so tests don't depend on env
os.environ.setdefault("SDACS_JWT_SECRET", "test-secret-do-not-use-in-prod")


from api.auth import (  # noqa: E402
    AUDIT,
    AuditLog,
    Role,
    TokenClaims,
    _b64url_decode,
    _b64url_encode,
    issue_token,
    require_admin,
    require_operator,
    require_viewer,
    verify_token,
)


# --- Role ---

class TestRole:
    def test_ordering(self):
        assert Role.viewer < Role.operator < Role.admin

    def test_from_str_valid(self):
        assert Role.from_str("viewer") == Role.viewer
        assert Role.from_str("ADMIN") == Role.admin

    def test_from_str_invalid(self):
        with pytest.raises(ValueError, match="unknown role"):
            Role.from_str("superuser")


# --- Base64url helpers ---

class TestB64Url:
    def test_roundtrip(self):
        data = b"hello world \x00\xff"
        assert _b64url_decode(_b64url_encode(data)) == data

    def test_no_padding(self):
        enc = _b64url_encode(b"test")
        assert "=" not in enc


# --- issue_token / verify_token ---

class TestJWT:
    def test_issue_returns_three_parts(self):
        token = issue_token("alice", "operator")
        assert token.count(".") == 2

    def test_verify_valid_token(self):
        token = issue_token("alice", "operator")
        claims = verify_token(token)
        assert claims.sub == "alice"
        assert claims.role == "operator"
        assert claims.exp > int(time.time())

    def test_verify_admin_token(self):
        token = issue_token("root", "admin")
        claims = verify_token(token)
        assert claims.role == "admin"

    def test_verify_viewer_token(self):
        token = issue_token("bob", "viewer")
        claims = verify_token(token)
        assert claims.role == "viewer"

    def test_verify_tampered_signature_raises(self):
        token = issue_token("alice", "operator")
        h, p, s = token.split(".")
        bad = f"{h}.{p}.{s[:-4]}XXXX"
        with pytest.raises(ValueError, match="invalid signature"):
            verify_token(bad)

    def test_verify_malformed_raises(self):
        with pytest.raises(ValueError, match="malformed"):
            verify_token("notavalidtoken")

    def test_verify_expired_raises(self):
        token = issue_token("alice", "viewer", ttl_s=-1)
        with pytest.raises(ValueError, match="expired"):
            verify_token(token)

    def test_issue_unknown_role_raises(self):
        with pytest.raises(ValueError):
            issue_token("x", "superuser")

    def test_claims_frozen(self):
        token = issue_token("alice", "operator")
        claims = verify_token(token)
        assert isinstance(claims, TokenClaims)
        with pytest.raises((AttributeError, TypeError)):
            claims.role = "admin"  # type: ignore[misc]

    def test_jti_unique(self):
        t1 = issue_token("alice", "viewer")
        t2 = issue_token("alice", "viewer")
        c1 = verify_token(t1)
        c2 = verify_token(t2)
        assert c1.jti != c2.jti


# --- RBAC dependencies ---

class TestRBACDependencies:
    def test_require_viewer_valid(self):
        token = issue_token("alice", "viewer")
        claims = require_viewer(f"Bearer {token}")
        assert claims.sub == "alice"

    def test_require_viewer_missing_bearer(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            require_viewer("")
        assert exc_info.value.status_code == 401

    def test_require_operator_viewer_token_rejected(self):
        from fastapi import HTTPException
        token = issue_token("alice", "viewer")
        with pytest.raises(HTTPException) as exc_info:
            require_operator(f"Bearer {token}")
        assert exc_info.value.status_code == 403

    def test_require_operator_operator_token_accepted(self):
        token = issue_token("alice", "operator")
        claims = require_operator(f"Bearer {token}")
        assert claims.role == "operator"

    def test_require_admin_admin_token_accepted(self):
        token = issue_token("root", "admin")
        claims = require_admin(f"Bearer {token}")
        assert claims.role == "admin"

    def test_require_admin_operator_token_rejected(self):
        from fastapi import HTTPException
        token = issue_token("alice", "operator")
        with pytest.raises(HTTPException) as exc_info:
            require_admin(f"Bearer {token}")
        assert exc_info.value.status_code == 403


# --- AuditLog ---

class TestAuditLog:
    def test_record_and_recent(self):
        log = AuditLog(maxlen=10)
        log.record("alice", "operator", "run_scenario", "/api/scenarios/x/run", "ok")
        entries = log.recent(1)
        assert len(entries) == 1
        e = entries[0]
        assert e["sub"] == "alice"
        assert e["action"] == "run_scenario"
        assert e["status"] == "ok"
        assert e["timestamp_ns"] > 0

    def test_maxlen_enforced(self):
        log = AuditLog(maxlen=3)
        for i in range(5):
            log.record(f"u{i}", "viewer", "check", "/", "ok")
        assert len(log.recent(10)) == 3

    def test_recent_returns_last_n(self):
        log = AuditLog()
        for i in range(10):
            log.record(f"u{i}", "viewer", "check", "/", "ok")
        entries = log.recent(3)
        assert len(entries) == 3
        assert entries[-1]["sub"] == "u9"

    def test_global_audit_instance_is_auditlog(self):
        assert isinstance(AUDIT, AuditLog)

    def test_record_with_detail(self):
        log = AuditLog()
        log.record("alice", "admin", "delete", "/api/runs/abc", "ok", detail="forced deletion")
        entry = log.recent(1)[0]
        assert entry["detail"] == "forced deletion"
