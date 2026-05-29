"""P712 — api/auth.py 단위 테스트.

테스트 구조:
  - create_token / _verify_token 라운드트립
  - 만료 토큰 거부
  - 서명 위변조 거부
  - Claims.has_role 계층 검증
  - require_* FastAPI 의존성 (AsyncMock)
"""

from __future__ import annotations

import os
import time

import pytest


@pytest.fixture(autouse=True)
def set_jwt_secret(monkeypatch):
    """모든 테스트에서 SDACS_JWT_SECRET 환경 변수를 고정 값으로 설정."""
    monkeypatch.setenv("SDACS_JWT_SECRET", "test-secret-key-for-unit-testing-32b")
    # _SECRET 캐시 초기화 (다른 테스트에서 오염된 경우 대비)
    import api.auth as auth_mod
    auth_mod._SECRET = None
    yield
    auth_mod._SECRET = None


# ---------------------------------------------------------------------------
# create_token / _verify_token 라운드트립
# ---------------------------------------------------------------------------

def test_create_and_verify_roundtrip():
    from api.auth import _verify_token, create_token

    token = create_token(sub="alice", roles=["viewer", "operator"])
    payload = _verify_token(token)

    assert payload["sub"] == "alice"
    assert "viewer" in payload["roles"]
    assert "operator" in payload["roles"]


def test_token_contains_exp_and_iat():
    from api.auth import _verify_token, create_token

    before = int(time.time())
    token = create_token(sub="bob", roles=["viewer"], ttl=3600)
    after = int(time.time())
    payload = _verify_token(token)

    assert before <= payload["iat"] <= after
    assert before + 3600 <= payload["exp"] <= after + 3600


def test_custom_ttl():
    from api.auth import _verify_token, create_token

    token = create_token(sub="charlie", roles=["admin"], ttl=7200)
    payload = _verify_token(token)
    remaining = payload["exp"] - int(time.time())

    assert 7100 < remaining <= 7200


# ---------------------------------------------------------------------------
# 만료 토큰 거부
# ---------------------------------------------------------------------------

def test_expired_token_raises():
    from api.auth import _verify_token, create_token

    token = create_token(sub="expired_user", roles=["viewer"], ttl=-1)

    with pytest.raises(ValueError, match="만료"):
        _verify_token(token)


# ---------------------------------------------------------------------------
# 서명 위변조 거부
# ---------------------------------------------------------------------------

def test_tampered_signature_raises():
    from api.auth import _verify_token, create_token

    token = create_token(sub="mallory", roles=["admin"])
    parts = token.split(".")
    # 서명 마지막 문자 변경
    tampered = parts[0] + "." + parts[1] + "." + parts[2][:-2] + "XX"

    with pytest.raises(ValueError, match="서명"):
        _verify_token(tampered)


def test_tampered_payload_raises():
    from api.auth import _verify_token, create_token
    import base64, json

    token = create_token(sub="alice", roles=["viewer"])
    header_b64, payload_b64, sig = token.split(".")

    # payload에서 roles를 admin으로 교체
    pad = 4 - len(payload_b64) % 4
    payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=" * (pad % 4)))
    payload["roles"] = ["admin"]
    new_payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    tampered = f"{header_b64}.{new_payload_b64}.{sig}"

    with pytest.raises(ValueError, match="서명"):
        _verify_token(tampered)


def test_malformed_token_raises():
    from api.auth import _verify_token

    with pytest.raises(ValueError, match="형식"):
        _verify_token("not.a.valid.token.format")


# ---------------------------------------------------------------------------
# Claims.has_role 계층
# ---------------------------------------------------------------------------

def test_has_role_exact():
    from api.auth import Claims

    c = Claims(sub="u", roles=["viewer"])
    assert c.has_role("viewer")
    assert not c.has_role("operator")
    assert not c.has_role("admin")


def test_has_role_operator_includes_viewer():
    from api.auth import Claims

    c = Claims(sub="u", roles=["operator"])
    assert c.has_role("viewer")
    assert c.has_role("operator")
    assert not c.has_role("admin")


def test_has_role_admin_includes_all():
    from api.auth import Claims

    c = Claims(sub="u", roles=["admin"])
    assert c.has_role("viewer")
    assert c.has_role("operator")
    assert c.has_role("admin")


def test_has_role_multi_roles():
    from api.auth import Claims

    c = Claims(sub="u", roles=["viewer", "operator"])
    assert c.has_role("operator")
    assert not c.has_role("admin")


# ---------------------------------------------------------------------------
# require_* FastAPI 의존성 (정상/비정상 케이스)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_require_viewer_accepts_valid_token():
    from api.auth import create_token, require_viewer

    token = create_token(sub="alice", roles=["viewer"])
    claims = await require_viewer(authorization=f"Bearer {token}")
    assert claims.sub == "alice"


@pytest.mark.anyio
async def test_require_operator_rejects_viewer():
    from fastapi import HTTPException
    from api.auth import create_token, require_operator

    token = create_token(sub="alice", roles=["viewer"])
    with pytest.raises(HTTPException) as exc_info:
        await require_operator(authorization=f"Bearer {token}")
    assert exc_info.value.status_code == 403


@pytest.mark.anyio
async def test_require_admin_rejects_operator():
    from fastapi import HTTPException
    from api.auth import create_token, require_admin

    token = create_token(sub="alice", roles=["operator"])
    with pytest.raises(HTTPException) as exc_info:
        await require_admin(authorization=f"Bearer {token}")
    assert exc_info.value.status_code == 403


@pytest.mark.anyio
async def test_require_viewer_missing_bearer_raises_401():
    from fastapi import HTTPException
    from api.auth import require_viewer

    with pytest.raises(HTTPException) as exc_info:
        await require_viewer(authorization="InvalidHeader")
    assert exc_info.value.status_code == 401


@pytest.mark.anyio
async def test_require_token_returns_sub():
    from api.auth import create_token, require_token

    token = create_token(sub="op_user", roles=["operator"])
    sub = await require_token(authorization=f"Bearer {token}")
    assert sub == "op_user"


# ---------------------------------------------------------------------------
# dev token (SDACS_DEV_TOKEN 설정 시)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_dev_token_accepted_as_admin(monkeypatch):
    from api.auth import require_admin
    import api.auth as auth_mod

    monkeypatch.setenv("SDACS_DEV_TOKEN", "my-dev-token")
    auth_mod._SECRET = None  # 캐시 초기화

    claims = await require_admin(authorization="Bearer my-dev-token")
    assert claims.sub == "dev"
    assert "admin" in claims.roles
