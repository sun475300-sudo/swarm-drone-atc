"""P712 — Full JWT authentication + RBAC for SDACS FastAPI backend.

Roles:
    admin    — full access (read, write, run, admin)
    operator — run scenarios, read/write
    viewer   — read-only

Usage:
    # create a token (e.g. in tests or a /token endpoint)
    token = create_token("alice", Role.operator)

    # FastAPI dependency
    @app.get("/protected")
    async def route(ctx: AuthContext = Depends(require_auth)):
        ctx.require("run")
        ...

Environment variables:
    SDACS_JWT_SECRET   — signing secret (MUST override in production)
    SDACS_TOKEN_TTL_S  — token lifetime in seconds (default 3600)
    SDACS_AUDIT_LOG    — audit log path (default logs/audit.jsonl)
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

try:
    import jwt  # PyJWT>=2.8
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("PyJWT required: pip install 'PyJWT>=2.8'") from exc

try:
    from fastapi import Depends, Header, HTTPException
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "FastAPI required: pip install 'fastapi>=0.110'"
    ) from exc

LOGGER = logging.getLogger("sdacs.auth")

_JWT_SECRET: str = os.environ.get("SDACS_JWT_SECRET", "change-me-in-production")
_JWT_ALGORITHM = "HS256"
_TOKEN_TTL_S: int = int(os.environ.get("SDACS_TOKEN_TTL_S", "3600"))
_AUDIT_PATH = Path(os.environ.get("SDACS_AUDIT_LOG", "logs/audit.jsonl"))


class Role(str, Enum):
    admin = "admin"
    operator = "operator"
    viewer = "viewer"


_ROLE_PERMISSIONS: dict[Role, frozenset[str]] = {
    Role.admin: frozenset({"read", "write", "run", "admin"}),
    Role.operator: frozenset({"read", "write", "run"}),
    Role.viewer: frozenset({"read"}),
}


def _write_audit(event: str, subject: str, detail: dict[str, Any] | None = None) -> None:
    _AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "sub": subject,
    }
    if detail:
        entry.update(detail)
    try:
        with _AUDIT_PATH.open("a") as fh:
            fh.write(json.dumps(entry) + "\n")
    except OSError as exc:
        LOGGER.warning("audit write failed: %s", exc)


def create_token(subject: str, role: Role, extra: dict[str, Any] | None = None) -> str:
    """Issue a signed JWT for *subject* with *role*."""
    now = time.time()
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role.value,
        "iat": int(now),
        "exp": int(now) + _TOKEN_TTL_S,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def _decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, detail="token expired")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(401, detail=f"invalid token: {exc}")


@dataclass
class AuthContext:
    subject: str
    role: Role
    _payload: dict[str, Any]

    def require(self, permission: str) -> None:
        if permission not in _ROLE_PERMISSIONS.get(self.role, frozenset()):
            _write_audit("permission_denied", self.subject, {"perm": permission, "role": self.role.value})
            raise HTTPException(403, detail=f"role '{self.role.value}' lacks '{permission}'")


async def require_auth(authorization: str = Header(default="")) -> AuthContext:
    """FastAPI dependency — validates Bearer JWT and returns AuthContext."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, detail="missing bearer token")
    token = authorization[7:]
    payload = _decode_token(token)
    subject: str = payload.get("sub", "unknown")
    role_str: str = payload.get("role", "viewer")
    try:
        role = Role(role_str)
    except ValueError:
        raise HTTPException(401, detail=f"unknown role: {role_str!r}")
    _write_audit("auth_ok", subject, {"role": role_str})
    return AuthContext(subject=subject, role=role, _payload=payload)


def require_permission(permission: str):
    """Dependency factory: raises 403 if the caller lacks *permission*."""

    async def _dep(ctx: AuthContext = Depends(require_auth)) -> AuthContext:
        ctx.require(permission)
        return ctx

    return _dep
