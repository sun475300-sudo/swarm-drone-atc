"""Tests for P712 JWT auth + RBAC module."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.auth import (
    AuditEntry,
    AuditLog,
    Role,
    UserClaims,
    create_token,
    verify_token,
)


class TestTokenCreation:
    def test_creates_valid_token(self) -> None:
        token = create_token("user1", Role.VIEWER)
        assert isinstance(token, str)
        parts = token.split(".")
        assert len(parts) == 3

    def test_token_roundtrip(self) -> None:
        token = create_token("admin1", Role.ADMIN)
        claims = verify_token(token)
        assert claims.sub == "admin1"
        assert claims.role == Role.ADMIN

    def test_all_roles(self) -> None:
        for role in Role:
            token = create_token("test", role)
            claims = verify_token(token)
            assert claims.role == role

    def test_custom_expiry(self) -> None:
        token = create_token("test", expire_minutes=120)
        claims = verify_token(token)
        assert claims.exp > claims.iat + 7000


class TestTokenVerification:
    def test_rejects_malformed(self) -> None:
        with pytest.raises(ValueError, match="malformed"):
            verify_token("not.a.valid.jwt.token")

    def test_rejects_tampered_signature(self) -> None:
        token = create_token("test")
        parts = token.split(".")
        parts[2] = parts[2][::-1]
        tampered = ".".join(parts)
        with pytest.raises(ValueError, match="invalid signature"):
            verify_token(tampered)

    def test_rejects_expired(self) -> None:
        token = create_token("test", expire_minutes=-1)
        with pytest.raises(ValueError, match="expired"):
            verify_token(token)


class TestRoleHierarchy:
    def test_admin_has_all_roles(self) -> None:
        claims = UserClaims(sub="x", role=Role.ADMIN, iat=0, exp=999999999999)
        assert claims.has_role(Role.VIEWER)
        assert claims.has_role(Role.OPERATOR)
        assert claims.has_role(Role.ADMIN)

    def test_operator_has_viewer(self) -> None:
        claims = UserClaims(sub="x", role=Role.OPERATOR, iat=0, exp=999999999999)
        assert claims.has_role(Role.VIEWER)
        assert claims.has_role(Role.OPERATOR)
        assert not claims.has_role(Role.ADMIN)

    def test_viewer_only_viewer(self) -> None:
        claims = UserClaims(sub="x", role=Role.VIEWER, iat=0, exp=999999999999)
        assert claims.has_role(Role.VIEWER)
        assert not claims.has_role(Role.OPERATOR)
        assert not claims.has_role(Role.ADMIN)


class TestAuditLog:
    def test_add_and_recent(self) -> None:
        log = AuditLog(max_entries=5)
        for i in range(3):
            log.add(AuditEntry(
                timestamp=float(i),
                method="GET",
                path=f"/test/{i}",
                user="u",
                role="viewer",
                status_code=200,
                duration_ms=1.0,
            ))
        entries = log.recent(10)
        assert len(entries) == 3

    def test_ring_buffer_overflow(self) -> None:
        log = AuditLog(max_entries=3)
        for i in range(10):
            log.add(AuditEntry(
                timestamp=float(i),
                method="GET",
                path=f"/test/{i}",
                user="u",
                role="viewer",
                status_code=200,
                duration_ms=1.0,
            ))
        entries = log.recent(100)
        assert len(entries) == 3
        assert entries[0].path == "/test/7"
