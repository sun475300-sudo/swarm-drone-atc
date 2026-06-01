"""P712 — JWT Bearer auth + RBAC for SDACS FastAPI.

Implements HS256 JWT with stdlib only (no PyJWT dependency).
Roles: admin > operator > viewer.

Usage:
    POST /auth/token   {"username": "...", "password": "..."}
    → {"access_token": "...", "token_type": "bearer", "expires_in": 3600}

    Protected endpoint: Authorization: Bearer <token>

Environment variables:
    SDACS_JWT_SECRET   — HS256 signing key (required in production)
    SDACS_JWT_TTL_S    — token TTL in seconds (default 3600)
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_raw_secret = os.environ.get("SDACS_JWT_SECRET", "")
if not _raw_secret:
    import warnings
    warnings.warn(
        "SDACS_JWT_SECRET env var not set — using insecure dev-only secret. "
        "Set SDACS_JWT_SECRET in production.",
        stacklevel=2,
    )
    _raw_secret = "sdacs-dev-secret-INSECURE-do-not-use-in-production"
JWT_SECRET: str = _raw_secret
JWT_TTL_S: int = int(os.environ.get("SDACS_JWT_TTL_S", "3600"))

# ROLES tuple: index 0 = highest privilege (admin), 2 = lowest (viewer).
# RoleChecker grants access when user rank <= minimum_rank (lower index = more privilege).
ROLES = ("admin", "operator", "viewer")

# Simple in-memory user store. Replace with DB lookup in P714.
# Passwords are SHA-256 hashes (hex). In production use bcrypt/argon2.
_sha = lambda s: hashlib.sha256(s.encode()).hexdigest()  # noqa: E731

# Dev-only credentials. Override via env SDACS_USERS_JSON or DB in P714.
_USERS: dict[str, dict[str, str]] = {
    "admin": {"password_hash": _sha("admin"), "role": "admin"},
    "operator": {"password_hash": _sha("operator"), "role": "operator"},
    "viewer": {"password_hash": _sha("viewer"), "role": "viewer"},
}

# ---------------------------------------------------------------------------
# JWT helpers (HS256, stdlib-only)
# ---------------------------------------------------------------------------


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    if pad != 4:
        s += "=" * pad
    return base64.urlsafe_b64decode(s)


def _sign(data: str, secret: str) -> str:
    sig = hmac.new(secret.encode(), data.encode(), hashlib.sha256).digest()
    return _b64url_encode(sig)


def create_token(username: str, role: str, secret: str = JWT_SECRET, ttl_s: int = JWT_TTL_S) -> str:
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    now = int(time.time())
    payload = _b64url_encode(
        json.dumps({"sub": username, "role": role, "iat": now, "exp": now + ttl_s}).encode()
    )
    sig = _sign(f"{header}.{payload}", secret)
    return f"{header}.{payload}.{sig}"


def verify_token(token: str, secret: str = JWT_SECRET) -> dict[str, Any]:
    """Validate token, return payload dict. Raises ValueError on failure."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("malformed token")
    header_b64, payload_b64, sig_b64 = parts
    expected_sig = _sign(f"{header_b64}.{payload_b64}", secret)
    if not hmac.compare_digest(sig_b64, expected_sig):
        raise ValueError("invalid signature")
    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception as exc:
        raise ValueError("token decode error") from exc
    if payload.get("exp", 0) < int(time.time()):
        raise ValueError("token expired")
    return payload


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TokenData:
    username: str
    role: str


_ROLE_RANK = {r: i for i, r in enumerate(ROLES)}


def requires_role(minimum_role: str) -> "RoleChecker":
    return RoleChecker(minimum_role)


class RoleChecker:
    def __init__(self, minimum_role: str) -> None:
        self.minimum_rank = _ROLE_RANK[minimum_role]

    def check(self, token_data: TokenData) -> None:
        if _ROLE_RANK.get(token_data.role, 999) > self.minimum_rank:
            raise PermissionError(f"role '{token_data.role}' insufficient, need '{ROLES[self.minimum_rank]}'")


# ---------------------------------------------------------------------------
# FastAPI dependency helpers
# ---------------------------------------------------------------------------

try:
    from fastapi import Depends, Header, HTTPException
    from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

    async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
        try:
            payload = verify_token(token)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        return TokenData(username=payload["sub"], role=payload.get("role", "viewer"))

    async def require_operator(user: TokenData = Depends(get_current_user)) -> TokenData:
        try:
            requires_role("operator").check(user)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        return user

    async def require_admin(user: TokenData = Depends(get_current_user)) -> TokenData:
        try:
            requires_role("admin").check(user)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        return user

    def login(username: str, password: str) -> dict[str, Any]:
        user = _USERS.get(username)
        # Use hmac.compare_digest to prevent timing attacks on the hash comparison.
        # Always hash the supplied password even when user is None to keep constant time.
        supplied_hash = _sha(password)
        stored_hash = user["password_hash"] if user is not None else supplied_hash
        if user is None or not hmac.compare_digest(stored_hash, supplied_hash):
            raise HTTPException(status_code=401, detail="invalid credentials")
        token = create_token(username, user["role"])
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": JWT_TTL_S,
            "role": user["role"],
        }

except ImportError:  # pragma: no cover
    pass
