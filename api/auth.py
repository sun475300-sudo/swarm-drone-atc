"""P712 — JWT Bearer auth + RBAC for SDACS API.

Usage:
    from api.auth import require_role, Role, create_access_token

Roles (low → high privilege):
    viewer   — read-only endpoints
    operator — can trigger scenario runs
    admin    — full access + audit log

Token lifecycle:
    POST /auth/token  {username, password} → {access_token, token_type}
    All protected endpoints: Authorization: Bearer <token>

Secrets:
    JWT_SECRET  — env var (required in production)
    JWT_ALGORITHM — default HS256
    JWT_EXPIRE_MINUTES — default 60

In-memory user store is replaced by a DB in P714.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

try:
    from fastapi import Depends, HTTPException, Security, status
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
    from pydantic import BaseModel
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("fastapi + pydantic required: pip install 'fastapi>=0.110'") from exc

_HAS_JWT = False
try:
    import jwt as _jwt  # PyJWT
    # 호환성 확인: PyJWT는 jwt.encode가 str을 반환함
    _HAS_JWT = hasattr(_jwt, "encode") and callable(getattr(_jwt, "decode", None))
except Exception:  # pragma: no cover — 환경 의존성 오류 무시
    pass

LOGGER = logging.getLogger("sdacs.auth")

_JWT_SECRET = os.environ.get("JWT_SECRET", "CHANGE_ME_IN_PRODUCTION_sdacs_2026")
_JWT_ALGORITHM = "HS256"
_JWT_EXPIRE_SECONDS = int(os.environ.get("JWT_EXPIRE_MINUTES", "60")) * 60

_BEARER_SCHEME = HTTPBearer(auto_error=False)


class Role(str, Enum):
    viewer = "viewer"
    operator = "operator"
    admin = "admin"


_ROLE_LEVEL: dict[Role, int] = {
    Role.viewer: 0,
    Role.operator: 1,
    Role.admin: 2,
}


@dataclass
class UserRecord:
    username: str
    password_hash: str  # SHA-256 hex
    role: Role
    disabled: bool = False


def _sha256(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# Seed users — replace with DB lookup in P714
_USERS: dict[str, UserRecord] = {
    "admin": UserRecord("admin", _sha256(os.environ.get("ADMIN_PASSWORD", "admin123")), Role.admin),
    "operator": UserRecord("operator", _sha256(os.environ.get("OPERATOR_PASSWORD", "op123")), Role.operator),
    "viewer": UserRecord("viewer", _sha256(os.environ.get("VIEWER_PASSWORD", "view123")), Role.viewer),
}


# --- Audit log (in-memory, flushed to file if AUDIT_LOG_PATH set) ---

_AUDIT_LOG: list[dict[str, Any]] = []
_AUDIT_LOG_PATH = os.environ.get("AUDIT_LOG_PATH", "")


def _audit(action: str, username: str, detail: str = "") -> None:
    entry = {"ts": time.time(), "action": action, "user": username, "detail": detail}
    _AUDIT_LOG.append(entry)
    if _AUDIT_LOG_PATH:
        import json
        with open(_AUDIT_LOG_PATH, "a") as fh:
            fh.write(json.dumps(entry) + "\n")
    LOGGER.info("AUDIT %s user=%s %s", action, username, detail)


def get_audit_log() -> list[dict[str, Any]]:
    return list(_AUDIT_LOG)


# --- Token creation ---


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = _JWT_EXPIRE_SECONDS
    role: str


class LoginRequest(BaseModel):
    username: str
    password: str


def create_access_token(username: str, role: Role) -> str:
    payload: dict[str, Any] = {
        "sub": username,
        "role": role.value,
        "iat": int(time.time()),
        "exp": int(time.time()) + _JWT_EXPIRE_SECONDS,
    }
    if _HAS_JWT:
        return _jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)
    # Fallback: HMAC-signed JSON (no PyJWT)
    import base64
    import json as _json
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(_json.dumps(payload).encode()).rstrip(b"=").decode()
    sig_input = f"{header}.{body}".encode()
    sig = hmac.new(_JWT_SECRET.encode(), sig_input, hashlib.sha256).hexdigest()
    return f"{header}.{body}.{sig}"


def _decode_token(token: str) -> dict[str, Any]:
    if _HAS_JWT:
        try:
            return _jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
        except _jwt.ExpiredSignatureError:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="token expired")
        except _jwt.InvalidTokenError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=f"invalid token: {exc}")
    # Fallback validation
    import base64
    import json as _json
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="malformed token")
    header, body, sig = parts
    expected = hmac.new(_JWT_SECRET.encode(), f"{header}.{body}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid signature")
    padding = 4 - len(body) % 4
    payload = _json.loads(base64.urlsafe_b64decode(body + "=" * padding))
    if payload.get("exp", 0) < time.time():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="token expired")
    return payload


# --- FastAPI dependencies ---


async def _get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(_BEARER_SCHEME),
) -> UserRecord:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    payload = _decode_token(credentials.credentials)
    username = payload.get("sub", "")
    user = _USERS.get(username)
    if user is None or user.disabled:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="user not found or disabled")
    return user


def require_role(minimum: Role):
    """Dependency factory: require at least `minimum` role."""
    async def _check(user: UserRecord = Depends(_get_current_user)) -> UserRecord:
        if _ROLE_LEVEL[user.role] < _ROLE_LEVEL[minimum]:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail=f"requires role '{minimum.value}', got '{user.role.value}'",
            )
        return user
    return _check


# Convenience shorthands
require_viewer = Depends(require_role(Role.viewer))
require_operator = Depends(require_role(Role.operator))
require_admin = Depends(require_role(Role.admin))


# --- Login endpoint helper (mount in fastapi_server.py) ---


def authenticate_user(username: str, password: str) -> UserRecord:
    user = _USERS.get(username)
    if user is None or user.disabled:
        _audit("login_failed", username, "user not found")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    if not hmac.compare_digest(user.password_hash, _sha256(password)):
        _audit("login_failed", username, "wrong password")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    _audit("login_ok", username)
    return user
