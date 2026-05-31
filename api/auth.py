"""P712 — JWT Authentication + RBAC for SDACS FastAPI backend.

Provides:
  - JWT token generation (HS256, configurable expiry)
  - Token validation dependency for FastAPI routes
  - Role-based access control (admin, operator, viewer)
  - Audit log middleware (request method, path, user, timestamp)

Configuration via environment variables:
  SDACS_JWT_SECRET   — signing key (REQUIRED in production)
  SDACS_JWT_EXPIRE_M — token lifetime in minutes (default: 60)
  SDACS_ADMIN_KEY    — bootstrap admin API key (dev/staging only)

Usage:
  from api.auth import require_role, Role, create_token

  @app.post("/api/admin/action")
  async def admin_action(user=Depends(require_role(Role.ADMIN))):
      ...
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from enum import Enum
from typing import Callable

try:
    from fastapi import Body, Depends, Header, HTTPException, Request
    from starlette.middleware.base import BaseHTTPMiddleware
except ImportError:
    pass

logger = logging.getLogger(__name__)

JWT_SECRET = os.environ.get("SDACS_JWT_SECRET", "dev-secret-change-in-production")
JWT_EXPIRE_MINUTES = int(os.environ.get("SDACS_JWT_EXPIRE_M", "60"))
ADMIN_API_KEY = os.environ.get("SDACS_ADMIN_KEY", "sdacs-dev-admin-key")


class Role(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


ROLE_HIERARCHY = {Role.ADMIN: 3, Role.OPERATOR: 2, Role.VIEWER: 1}


@dataclass(frozen=True)
class UserClaims:
    sub: str
    role: Role
    iat: int
    exp: int

    def has_role(self, minimum: Role) -> bool:
        return ROLE_HIERARCHY.get(self.role, 0) >= ROLE_HIERARCHY.get(minimum, 0)


def _b64url_encode(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return urlsafe_b64decode(s)


def _sign(payload_bytes: bytes, secret: str) -> str:
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = _b64url_encode(payload_bytes)
    message = f"{header}.{body}".encode()
    sig = hmac.new(secret.encode(), message, hashlib.sha256).digest()
    return f"{header}.{body}.{_b64url_encode(sig)}"


def create_token(
    subject: str,
    role: Role = Role.VIEWER,
    expire_minutes: int | None = None,
) -> str:
    now = int(time.time())
    exp = now + (expire_minutes or JWT_EXPIRE_MINUTES) * 60
    payload = json.dumps({
        "sub": subject,
        "role": role.value,
        "iat": now,
        "exp": exp,
    }).encode()
    return _sign(payload, JWT_SECRET)


def verify_token(token: str) -> UserClaims:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("malformed JWT")

    header_b, payload_b, sig_b = parts
    message = f"{header_b}.{payload_b}".encode()
    expected_sig = hmac.new(JWT_SECRET.encode(), message, hashlib.sha256).digest()
    actual_sig = _b64url_decode(sig_b)

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("invalid signature")

    payload = json.loads(_b64url_decode(payload_b))

    if payload.get("exp", 0) < int(time.time()):
        raise ValueError("token expired")

    return UserClaims(
        sub=str(payload["sub"]),
        role=Role(payload.get("role", "viewer")),
        iat=int(payload.get("iat", 0)),
        exp=int(payload["exp"]),
    )


async def get_current_user(authorization: str = Header(default="")) -> UserClaims:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization[len("Bearer "):]
    try:
        return verify_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def require_role(minimum: Role) -> Callable:
    async def _check(user: UserClaims = Depends(get_current_user)) -> UserClaims:
        if not user.has_role(minimum):
            raise HTTPException(
                status_code=403,
                detail=f"requires {minimum.value} role or higher",
            )
        return user
    return _check


@dataclass
class AuditEntry:
    timestamp: float
    method: str
    path: str
    user: str
    role: str
    status_code: int
    duration_ms: float


class AuditLog:
    def __init__(self, max_entries: int = 10_000) -> None:
        self._entries: list[AuditEntry] = []
        self._max = max_entries

    def add(self, entry: AuditEntry) -> None:
        self._entries.append(entry)
        if len(self._entries) > self._max:
            self._entries = self._entries[-self._max:]

    def recent(self, n: int = 100) -> list[AuditEntry]:
        return list(self._entries[-n:])


AUDIT_LOG = AuditLog()


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        user = "anonymous"
        role = "none"

        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                claims = verify_token(auth_header[7:])
                user = claims.sub
                role = claims.role.value
            except ValueError:
                pass

        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        AUDIT_LOG.add(AuditEntry(
            timestamp=time.time(),
            method=request.method,
            path=str(request.url.path),
            user=user,
            role=role,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        ))

        return response


def register_auth_routes(app) -> None:
    @app.post("/api/auth/token", tags=["auth"])
    async def create_auth_token(
        api_key: str = Body(..., embed=True),
        role: str = Body("viewer", embed=True),
    ) -> dict:
        if api_key != ADMIN_API_KEY:
            raise HTTPException(status_code=403, detail="invalid api key")
        try:
            r = Role(role)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"invalid role: {role}")
        token = create_token(subject="api_user", role=r)
        return {"token": token, "expires_in_minutes": JWT_EXPIRE_MINUTES}

    @app.get("/api/auth/me", tags=["auth"])
    async def whoami(user: UserClaims = Depends(get_current_user)) -> dict:
        return {"sub": user.sub, "role": user.role.value, "exp": user.exp}

    @app.get("/api/auth/audit", tags=["auth"])
    async def audit_log(
        n: int = 50,
        _user: UserClaims = Depends(require_role(Role.ADMIN)),
    ) -> list[dict]:
        return [
            {
                "timestamp": e.timestamp,
                "method": e.method,
                "path": e.path,
                "user": e.user,
                "role": e.role,
                "status_code": e.status_code,
                "duration_ms": e.duration_ms,
            }
            for e in AUDIT_LOG.recent(n)
        ]
