"""P712 — JWT/RBAC/감사로그 테스트."""
from __future__ import annotations

import time

import pytest
from fastapi import HTTPException

from api.auth import (
    AuditEvent,
    Role,
    TokenPayload,
    _b64url_decode,
    _b64url_encode,
    _hs256_sign,
    create_token,
    decode_token,
    get_audit_log,
    record_audit_event,
)


# --- b64url helpers ---

class TestB64UrlHelpers:
    def test_encode_decode_roundtrip(self):
        data = b"hello world \x00\x01\x02"
        assert _b64url_decode(_b64url_encode(data)) == data

    def test_no_padding_chars(self):
        encoded = _b64url_encode(b"x")
        assert "=" not in encoded

    def test_url_safe_chars(self):
        for data in [b"\xfb\xfc", b"\xfb\xfc\xfd", b"\xfb\xfc\xfd\xfe"]:
            enc = _b64url_encode(data)
            assert "+" not in enc
            assert "/" not in enc


# --- JWT 생성/검증 ---

class TestCreateToken:
    def test_returns_three_part_string(self):
        token = create_token("user1", Role.VIEWER)
        assert len(token.split(".")) == 3

    def test_different_roles_produce_different_tokens(self):
        t1 = create_token("user1", Role.ADMIN)
        t2 = create_token("user1", Role.VIEWER)
        assert t1 != t2

    def test_different_subjects_produce_different_tokens(self):
        t1 = create_token("alice", Role.OPERATOR)
        t2 = create_token("bob", Role.OPERATOR)
        assert t1 != t2


class TestDecodeToken:
    def test_roundtrip(self):
        token = create_token("alice", Role.OPERATOR)
        payload = decode_token(token)
        assert payload.sub == "alice"
        assert payload.role == Role.OPERATOR

    def test_all_roles(self):
        for role in Role:
            token = create_token("u", role)
            payload = decode_token(token)
            assert payload.role == role

    def test_invalid_signature_raises_401(self):
        token = create_token("u", Role.VIEWER, secret="secret-a")
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token, secret="secret-b")
        assert exc_info.value.status_code == 401

    def test_malformed_token_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            decode_token("not.a.valid.token.extra")
        assert exc_info.value.status_code == 401

    def test_expired_token_raises_401(self):
        import base64, json, hashlib, hmac as _hmac
        now = int(time.time()) - 7200
        payload = json.dumps({"sub": "u", "role": "viewer", "iat": now, "exp": now + 1})
        header_b64 = _b64url_encode(b'{"alg":"HS256","typ":"JWT"}')
        body_b64 = _b64url_encode(payload.encode())
        sig = _hs256_sign(header_b64, body_b64, "sdacs-dev-secret-change-in-production")
        token = f"{header_b64}.{body_b64}.{sig}"
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)
        assert exc_info.value.status_code == 401

    def test_payload_fields(self):
        before = int(time.time())
        token = create_token("bob", Role.ADMIN)
        payload = decode_token(token)
        assert payload.sub == "bob"
        assert payload.role == Role.ADMIN
        assert payload.iat >= before
        assert payload.exp > payload.iat


# --- 감사 로그 ---

class TestAuditLog:
    def test_record_and_retrieve(self):
        event = AuditEvent(
            timestamp_ns=time.time_ns(),
            subject="test-user",
            role="operator",
            method="POST",
            endpoint="/api/scenarios/foo/run",
            status_code=200,
        )
        record_audit_event(event)
        log = get_audit_log(limit=10)
        assert any(e["subject"] == "test-user" for e in log)

    def test_limit_respected(self):
        for _ in range(5):
            record_audit_event(AuditEvent(
                timestamp_ns=time.time_ns(),
                subject="bulk-user",
                role="viewer",
                method="GET",
                endpoint="/healthz",
            ))
        log = get_audit_log(limit=2)
        assert len(log) <= 2

    def test_event_fields_present(self):
        record_audit_event(AuditEvent(
            timestamp_ns=123,
            subject="field-check",
            role="admin",
            method="DELETE",
            endpoint="/api/audit",
            status_code=403,
            client_ip="127.0.0.1",
        ))
        log = get_audit_log(limit=100)
        entry = next((e for e in log if e["subject"] == "field-check"), None)
        assert entry is not None
        assert entry["role"] == "admin"
        assert entry["status_code"] == 403


# --- Role RBAC 권한 범위 ---

class TestRolePermissions:
    def test_admin_has_all_permissions(self):
        from api.auth import _ROLE_PERMISSIONS
        assert {"read", "write", "run", "admin"}.issubset(_ROLE_PERMISSIONS[Role.ADMIN])

    def test_viewer_only_read(self):
        from api.auth import _ROLE_PERMISSIONS
        assert _ROLE_PERMISSIONS[Role.VIEWER] == frozenset({"read"})

    def test_operator_no_admin(self):
        from api.auth import _ROLE_PERMISSIONS
        assert "admin" not in _ROLE_PERMISSIONS[Role.OPERATOR]
        assert "run" in _ROLE_PERMISSIONS[Role.OPERATOR]
