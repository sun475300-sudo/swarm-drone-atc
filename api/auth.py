<<<<<<< HEAD
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

=======
"""P712 — OAuth2/RBAC authentication layer for the SDACS FastAPI backend.

Design:
    - HS256 JWT tokens (stdlib only, no cryptography dep required).
    - Roles: admin > operator > viewer.
    - Every mutating endpoint requires at least operator scope.
    - Audit log emitted on every authenticated request.
    - /auth/token issues tokens; /auth/refresh extends expiry.

Environment variables:
    SDACS_JWT_SECRET   — HS256 signing key (required in production).
                         Defaults to an insecure dev key when missing.
    SDACS_TOKEN_TTL_S  — access token TTL seconds (default 3600).
"""
from __future__ import annotations

import base64
>>>>>>> c712bbd5ecb51bce6d827215bbc998a957a56a02
import hashlib
import hmac
import json
import logging
import os
import time
<<<<<<< HEAD
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
=======
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel, Field

LOGGER = logging.getLogger("sdacs.auth")

_JWT_SECRET = os.environ.get("SDACS_JWT_SECRET", "dev-insecure-secret-change-in-prod")
_TOKEN_TTL_S = int(os.environ.get("SDACS_TOKEN_TTL_S", "3600"))


# ---------------------------------------------------------------------------
# Role hierarchy
# ---------------------------------------------------------------------------

class Role(str, Enum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"


_ROLE_RANK: dict[Role, int] = {
    Role.VIEWER: 0,
    Role.OPERATOR: 1,
    Role.ADMIN: 2,
}


def role_gte(actual: Role, required: Role) -> bool:
    """Return True if *actual* role has at least the *required* privilege."""
    return _ROLE_RANK[actual] >= _ROLE_RANK[required]


# ---------------------------------------------------------------------------
# Pure-stdlib HS256 JWT (avoids broken cryptography package in this env)
# ---------------------------------------------------------------------------

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    if pad != 4:
        s += "=" * pad
    return base64.urlsafe_b64decode(s)


def _sign(header_b64: str, payload_b64: str, secret: str) -> str:
    msg = f"{header_b64}.{payload_b64}".encode()
    sig = hmac.new(secret.encode(), msg, hashlib.sha256).digest()
    return _b64url_encode(sig)


def create_token(
    sub: str,
    role: Role,
    ttl_s: int = _TOKEN_TTL_S,
    extra: dict[str, Any] | None = None,
) -> str:
    """Issue a signed HS256 JWT.

    Args:
        sub:   Subject (user ID or service name).
        role:  RBAC role.
        ttl_s: Token lifetime in seconds.
        extra: Additional claims merged into the payload.

    Returns:
        Compact JWT string ``header.payload.signature``.
    """
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": sub,
        "role": role.value,
        "iat": now,
        "exp": now + ttl_s,
        "jti": uuid.uuid4().hex,
    }
    if extra:
        payload.update(extra)
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = _b64url_encode(json.dumps(payload).encode())
    sig = _sign(header, body, _JWT_SECRET)
    return f"{header}.{body}.{sig}"


def verify_token(token: str) -> dict[str, Any]:
    """Validate an HS256 JWT and return its payload.

    Raises:
        HTTPException(401): if the token is malformed, expired, or has a bad signature.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="malformed token")

    header_b64, body_b64, sig_b64 = parts
    expected_sig = _sign(header_b64, body_b64, _JWT_SECRET)
    if not hmac.compare_digest(sig_b64, expected_sig):
        raise HTTPException(status_code=401, detail="invalid token signature")

    try:
        payload = json.loads(_b64url_decode(body_b64))
    except Exception:
        raise HTTPException(status_code=401, detail="malformed token payload")

    if int(time.time()) > payload.get("exp", 0):
        raise HTTPException(status_code=401, detail="token expired")

    return payload


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

@dataclass
class AuditEntry:
    """Single audit record emitted for every authenticated action."""
    ts: float = field(default_factory=time.time)
    sub: str = ""
    role: str = ""
    action: str = ""
    resource: str = ""
    outcome: str = "ok"  # "ok" | "denied" | "error"
    detail: str = ""


_AUDIT_LOG: list[AuditEntry] = []
_MAX_AUDIT_ENTRIES = 10_000


def _audit(sub: str, role: str, action: str, resource: str = "", outcome: str = "ok", detail: str = "") -> None:
    entry = AuditEntry(
        sub=sub, role=role, action=action,
        resource=resource, outcome=outcome, detail=detail,
    )
    LOGGER.info("AUDIT sub=%s role=%s action=%s resource=%s outcome=%s %s",
                sub, role, action, resource, outcome, detail)
    _AUDIT_LOG.append(entry)
    if len(_AUDIT_LOG) > _MAX_AUDIT_ENTRIES:
        del _AUDIT_LOG[:1000]


def get_audit_log(limit: int = 100) -> list[dict[str, Any]]:
    """Return the most recent *limit* audit entries."""
    entries = _AUDIT_LOG[-limit:]
    return [
        {
            "ts": e.ts, "sub": e.sub, "role": e.role,
            "action": e.action, "resource": e.resource,
            "outcome": e.outcome, "detail": e.detail,
        }
        for e in reversed(entries)
    ]


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AuthContext:
    """Injected into route handlers that require authentication."""
    sub: str
    role: Role
    jti: str


async def _extract_token(authorization: str = Header(default="")) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    return authorization[len("Bearer "):]


async def require_auth(token: str = Depends(_extract_token)) -> AuthContext:
    """FastAPI dependency: validate JWT, return AuthContext."""
    payload = verify_token(token)
    try:
        role = Role(payload["role"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=401, detail="invalid role in token")
    ctx = AuthContext(sub=payload["sub"], role=role, jti=payload.get("jti", ""))
    _audit(ctx.sub, ctx.role.value, "authenticate", outcome="ok")
    return ctx


def require_role(minimum: Role):
    """Return a FastAPI dependency that enforces a minimum role."""
    async def _dep(ctx: AuthContext = Depends(require_auth)) -> AuthContext:
        if not role_gte(ctx.role, minimum):
            _audit(ctx.sub, ctx.role.value, "authorize", outcome="denied",
                   detail=f"required={minimum.value}")
            raise HTTPException(status_code=403, detail=f"requires {minimum.value} role")
        return ctx
    return _dep


require_viewer = require_role(Role.VIEWER)
require_operator = require_role(Role.OPERATOR)
require_admin = require_role(Role.ADMIN)


# ---------------------------------------------------------------------------
# In-memory user store (replace with DB in P714)
# ---------------------------------------------------------------------------

@dataclass
class _UserRecord:
    sub: str
    password_hash: str
    role: Role


def _hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


_USERS: dict[str, _UserRecord] = {
    "admin": _UserRecord("admin", _hash_pw("admin123"), Role.ADMIN),
    "operator": _UserRecord("operator", _hash_pw("op123"), Role.OPERATOR),
    "viewer": _UserRecord("viewer", _hash_pw("view123"), Role.VIEWER),
}


# ---------------------------------------------------------------------------
# Pydantic request/response models
# ---------------------------------------------------------------------------

class TokenRequest(BaseModel):
    """OAuth2 password flow body."""
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    """Issued token envelope."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = _TOKEN_TTL_S
    role: str


class RefreshRequest(BaseModel):
    """Refresh an existing (non-expired) token to extend TTL."""
    token: str


# ---------------------------------------------------------------------------
# Auth router (mount at /auth in fastapi_server.py)
# ---------------------------------------------------------------------------

from fastapi import APIRouter  # noqa: E402  (after dataclasses to avoid circular-import look)

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/token", response_model=TokenResponse, summary="Issue JWT")
async def issue_token(body: TokenRequest) -> TokenResponse:
    """Password-grant: exchange credentials for a JWT."""
    user = _USERS.get(body.username)
    if user is None or user.password_hash != _hash_pw(body.password):
        _audit(body.username, "", "login", outcome="denied")
        raise HTTPException(status_code=401, detail="invalid credentials")
    token = create_token(user.sub, user.role)
    _audit(user.sub, user.role.value, "login", outcome="ok")
    return TokenResponse(access_token=token, role=user.role.value)


@auth_router.post("/refresh", response_model=TokenResponse, summary="Refresh JWT")
async def refresh_token(body: RefreshRequest) -> TokenResponse:
    """Extend a valid token's lifetime without re-entering credentials."""
    payload = verify_token(body.token)
    try:
        role = Role(payload["role"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=401, detail="invalid role")
    new_token = create_token(payload["sub"], role)
    _audit(payload["sub"], role.value, "refresh", outcome="ok")
    return TokenResponse(access_token=new_token, role=role.value)


@auth_router.get("/me", summary="Current user info")
async def whoami(ctx: AuthContext = Depends(require_auth)) -> dict:
    """Return the authenticated user's identity and role."""
    return {"sub": ctx.sub, "role": ctx.role.value}


@auth_router.get("/audit", summary="Audit log (admin only)")
async def audit_log(
    limit: int = 100,
    ctx: AuthContext = Depends(require_admin),
) -> dict:
    """Return the most recent audit entries. Requires admin role."""
    _audit(ctx.sub, ctx.role.value, "read_audit", outcome="ok")
    return {"success": True, "data": get_audit_log(limit)}
>>>>>>> c712bbd5ecb51bce6d827215bbc998a957a56a02
