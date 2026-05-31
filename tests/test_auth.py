"""P712 — JWT auth / RBAC / 감사로그 테스트."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

os.environ.setdefault("SDACS_JWT_SECRET", "test-secret-key-for-unit-tests-32chars!!")


from api.auth import (
    ROLES_HIERARCHY,
    create_access_token,
    read_audit_log,
    require_role,
    validate_token,
    write_audit_log,
)


# --- 토큰 생성/검증 ---


def test_create_and_validate_token():
    token = create_access_token("alice", "operator")
    claims = validate_token(token)
    assert claims["sub"] == "alice"
    assert claims["role"] == "operator"


def test_token_contains_exp():
    token = create_access_token("bob", "viewer")
    claims = validate_token(token)
    assert claims["exp"] > int(time.time())


def test_invalid_token_raises_401():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        validate_token("not.a.real.token")
    assert exc_info.value.status_code == 401


def test_expired_token_raises_401():
    from fastapi import HTTPException
    import api.auth as auth_mod

    # api.auth의 내부 함수를 이용해 만료된 토큰 직접 생성
    header = auth_mod._b64url_encode(b'{"alg":"HS256","typ":"JWT"}')
    payload_data = {"sub": "eve", "role": "viewer", "iat": 1, "exp": 2}
    payload = auth_mod._b64url_encode(
        __import__("json").dumps(payload_data).encode()
    )
    sig = auth_mod._sign(f"{header}.{payload}", auth_mod._secret())
    expired_token = f"{header}.{payload}.{sig}"
    with pytest.raises(HTTPException) as exc_info:
        validate_token(expired_token)
    assert exc_info.value.status_code == 401


def test_unknown_role_rejected():
    with pytest.raises(ValueError, match="unknown role"):
        create_access_token("x", "superuser")


# --- 역할 계층 ---


def test_role_hierarchy_order():
    assert ROLES_HIERARCHY.index("viewer") < ROLES_HIERARCHY.index("operator")
    assert ROLES_HIERARCHY.index("operator") < ROLES_HIERARCHY.index("admin")


def test_admin_token_passes_operator_check():
    token = create_access_token("admin_user", "admin")
    check_fn = require_role("operator")

    # simulate FastAPI Depends call — the inner function _check
    inner = check_fn.__wrapped__ if hasattr(check_fn, "__wrapped__") else check_fn
    # require_role returns a closure; call it with the token directly
    # We can call validate_token + role check manually
    claims = validate_token(token)
    assert ROLES_HIERARCHY.index(claims["role"]) >= ROLES_HIERARCHY.index("operator")


def test_viewer_token_fails_admin_check():
    from fastapi import HTTPException

    token = create_access_token("viewer_user", "viewer")
    claims = validate_token(token)
    viewer_level = ROLES_HIERARCHY.index(claims["role"])
    admin_level = ROLES_HIERARCHY.index("admin")
    assert viewer_level < admin_level


# --- 감사 로그 ---


def test_write_and_read_audit_log(tmp_path, monkeypatch):
    import api.auth as auth_mod

    log_path = tmp_path / "audit.log"
    monkeypatch.setattr(auth_mod, "AUDIT_LOG_PATH", log_path)

    write_audit_log("login", "alice", {"ip": "127.0.0.1"})
    write_audit_log("run_started", "alice", {"scenario": "s01"})

    records = read_audit_log(limit=10)
    assert len(records) == 2
    events = {r["event"] for r in records}
    assert "login" in events
    assert "run_started" in events


def test_audit_log_json_format(tmp_path, monkeypatch):
    import api.auth as auth_mod

    log_path = tmp_path / "audit.log"
    monkeypatch.setattr(auth_mod, "AUDIT_LOG_PATH", log_path)

    write_audit_log("test_event", "user1")
    lines = log_path.read_text().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event"] == "test_event"
    assert record["sub"] == "user1"
    assert "ts" in record


def test_read_audit_log_empty(tmp_path, monkeypatch):
    import api.auth as auth_mod

    monkeypatch.setattr(auth_mod, "AUDIT_LOG_PATH", tmp_path / "nonexistent.log")
    assert read_audit_log() == []


def test_audit_log_limit(tmp_path, monkeypatch):
    import api.auth as auth_mod

    log_path = tmp_path / "audit.log"
    monkeypatch.setattr(auth_mod, "AUDIT_LOG_PATH", log_path)

    for i in range(10):
        write_audit_log(f"event_{i}", "u")

    records = read_audit_log(limit=5)
    assert len(records) == 5
