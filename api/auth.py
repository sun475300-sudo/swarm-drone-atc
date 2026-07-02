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
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel, Field

LOGGER = logging.getLogger("sdacs.auth")

# 보안: SDACS_PROD=1 (또는 truthy 값) 환경변수 옵트인 시 SDACS_JWT_SECRET 누락을
# 명시적 RuntimeError 로 거부. 개발(default) 모드에서는 약한 dev 키를 사용하지만
# 경고를 1회 emit 해 운영 환경에서 누락을 사일런트로 넘어가지 않게 함.
def _resolve_jwt_secret() -> str:
    secret = os.environ.get("SDACS_JWT_SECRET")
    prod = os.environ.get("SDACS_PROD", "").strip().lower() in {"1", "true", "yes", "on"}
    if secret:
        return secret
    if prod:
        raise RuntimeError(
            "SDACS_JWT_SECRET 환경변수가 SDACS_PROD 모드에서 필수입니다. "
            "강한 무작위 비밀(>=32바이트)을 설정하세요."
        )
    LOGGER.warning(
        "⚠ SDACS_JWT_SECRET 미설정 — 개발용 약한 키 사용 중. "
        "운영 배포 시 SDACS_PROD=1 + 강한 비밀 설정 필수."
    )
    return "dev-insecure-secret-change-in-prod"


_JWT_SECRET = _resolve_jwt_secret()
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


# ---------------------------------------------------------------------------
# Revocation registry (P1-B enhancement)
# ---------------------------------------------------------------------------
# In-memory blocklist of revoked JTIs (insertion-ordered dict for FIFO eviction).
# For multi-instance deployments swap this for a Redis SET with per-key TTL.
_REVOKED_JTIS: dict[str, None] = {}
_MAX_REVOKED_JTIS = 100_000


def revoke_token(jti: str) -> None:
    """Add a JWT ID (jti claim) to the revocation blocklist.

    Subsequent ``verify_token`` calls for any token bearing this jti will
    raise HTTPException(401, detail="token revoked"). Idempotent. Empty
    jti is a no-op. Evicts oldest entry when at capacity.
    """
    if not jti:
        return
    if jti in _REVOKED_JTIS:
        return
    if len(_REVOKED_JTIS) >= _MAX_REVOKED_JTIS:
        oldest = next(iter(_REVOKED_JTIS))
        del _REVOKED_JTIS[oldest]
    _REVOKED_JTIS[jti] = None


def is_revoked(jti: str) -> bool:
    """Return True if the given jti has been revoked."""
    return bool(jti) and jti in _REVOKED_JTIS


def _reset_revocation_for_tests() -> None:
    """Test-only helper to clear the blocklist between cases."""
    _REVOKED_JTIS.clear()


def verify_token(token: str) -> dict[str, Any]:
    """Validate an HS256 JWT and return its payload.

    Raises:
        HTTPException(401): if the token is malformed, expired, has a bad
            signature, or has been revoked.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="malformed token")

    header_b64, body_b64, sig_b64 = parts
    # 알고리즘 명시 검증 (defense in depth) — alg=none / alg=RS256 등 변조 차단.
    # 자체 _sign 이 항상 HS256 이라 잘못된 alg 는 서명 mismatch 로 자동 차단되지만,
    # 명시 검증으로 향후 다른 sign 경로가 추가되어도 안전 유지.
    try:
        header = json.loads(_b64url_decode(header_b64))
    except Exception as exc:
        raise HTTPException(status_code=401, detail="malformed token header") from exc
    if header.get("alg") != "HS256":
        raise HTTPException(status_code=401, detail="unsupported token algorithm")

    expected_sig = _sign(header_b64, body_b64, _JWT_SECRET)
    if not hmac.compare_digest(sig_b64, expected_sig):
        raise HTTPException(status_code=401, detail="invalid token signature")

    try:
        payload = json.loads(_b64url_decode(body_b64))
    except Exception as exc:
        raise HTTPException(status_code=401, detail="malformed token payload") from exc

    if int(time.time()) > payload.get("exp", 0):
        raise HTTPException(status_code=401, detail="token expired")

    if is_revoked(payload.get("jti", "")):
        raise HTTPException(status_code=401, detail="token revoked")

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
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="invalid role in token") from exc
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
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="invalid role") from exc
    new_token = create_token(payload["sub"], role)
    _audit(payload["sub"], role.value, "refresh", outcome="ok")
    return TokenResponse(access_token=new_token, role=role.value)


@auth_router.get("/me", summary="Current user info")
async def whoami(ctx: AuthContext = Depends(require_auth)) -> dict:
    """Return the authenticated user's identity and role."""
    return {"sub": ctx.sub, "role": ctx.role.value}


@auth_router.post("/logout", summary="Revoke current token")
async def logout(ctx: AuthContext = Depends(require_auth)) -> dict:
    """Revoke the JWT used in this request so it cannot be reused before expiry."""
    if ctx.jti:
        revoke_token(ctx.jti)
    _audit(ctx.sub, ctx.role.value, "logout", outcome="ok")
    return {"success": True}


@auth_router.get("/audit", summary="Audit log (admin only)")
async def audit_log(
    limit: int = 100,
    ctx: AuthContext = Depends(require_admin),
) -> dict:
    """Return the most recent audit entries. Requires admin role."""
    _audit(ctx.sub, ctx.role.value, "read_audit", outcome="ok")
    return {"success": True, "data": get_audit_log(limit)}
