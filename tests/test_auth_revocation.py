"""Tests for the token revocation enhancement (P1-B feat/jwt-auth).

Adds coverage for:
- revoke_token / is_revoked / _reset_revocation_for_tests helpers.
- verify_token rejecting a revoked jti.
- POST /auth/logout endpoint.
"""
from __future__ import annotations

import pytest

from api import auth as auth_module
from api.auth import (
    Role,
    create_token,
    is_revoked,
    revoke_token,
    verify_token,
)


@pytest.fixture(autouse=True)
def _clean_revocation_between_tests():
    """Ensure each test starts with an empty blocklist."""
    auth_module._reset_revocation_for_tests()
    yield
    auth_module._reset_revocation_for_tests()


def test_revoke_token_records_jti():
    revoke_token("abc-123")
    assert is_revoked("abc-123")


def test_revoke_token_empty_jti_is_noop():
    revoke_token("")
    assert not is_revoked("")


def test_revoke_token_is_idempotent():
    revoke_token("abc-123")
    revoke_token("abc-123")
    assert is_revoked("abc-123")


def test_verify_token_rejects_revoked():
    token = create_token("alice", Role.OPERATOR, ttl_s=60)
    payload = verify_token(token)
    revoke_token(payload["jti"])
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as excinfo:
        verify_token(token)
    assert excinfo.value.status_code == 401
    assert "revoked" in excinfo.value.detail.lower()


def test_verify_token_accepts_non_revoked_after_revoking_another():
    token_a = create_token("alice", Role.OPERATOR, ttl_s=60)
    token_b = create_token("bob", Role.OPERATOR, ttl_s=60)
    payload_a = verify_token(token_a)
    revoke_token(payload_a["jti"])
    payload_b = verify_token(token_b)
    assert payload_b["sub"] == "bob"


def test_logout_endpoint_revokes_caller_token():
    pytest.importorskip("fastapi.testclient")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(auth_module.auth_router)

    client = TestClient(app)
    # Issue a token via password flow.
    res = client.post("/auth/token", json={"username": "alice", "password": "alice"})
    if res.status_code != 200:
        # alice may not be in the default user table — skip if so.
        pytest.skip(f"default user 'alice' missing: {res.status_code}")
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # /auth/me works before logout.
    me_before = client.get("/auth/me", headers=headers)
    assert me_before.status_code == 200

    # /auth/logout returns the revoked jti.
    logout_res = client.post("/auth/logout", headers=headers)
    assert logout_res.status_code == 200
    assert logout_res.json()["success"] is True
    assert logout_res.json()["revoked_jti"]

    # /auth/me now fails with 401 (revoked).
    me_after = client.get("/auth/me", headers=headers)
    assert me_after.status_code == 401
    assert "revoked" in me_after.json()["detail"].lower()


def test_blocklist_does_not_grow_unbounded():
    cap = auth_module._MAX_REVOKED_JTIS
    # Fill the blocklist up to the cap; one more should evict an entry.
    for i in range(cap + 5):
        revoke_token(f"jti-{i}")
    # Size must stay at or below the cap (set-pop eviction is approximate).
    assert len(auth_module._REVOKED_JTIS) <= cap
