"""P712: HMAC-SHA256 JWT + RBAC + in-memory audit log.

Token lifecycle:
    POST /api/auth/token  → issue JWT (HS256, 1-hour TTL)
    Authorization: Bearer <token>  → require_operator / require_admin

Roles (ordered, least → most privileged):
    viewer → operator → admin

Env vars:
    SDACS_JWT_SECRET  — signing secret (required in production)
    SDACS_JWT_TTL_S   — token TTL in seconds (default 3600)
"""

from __future__ import annotations

import base64
import collections
import hashlib
import hmac
import json
import os
import time
import uuid
import warnings
from dataclasses import dataclass, field
from enum import IntEnum

# --- Config ---

_DEV_SECRET = "sdacs-dev-secret-change-in-production"  # nosec B105 — intentional insecure dev default, production must set SDACS_JWT_SECRET
JWT_SECRET: str = os.environ.get("SDACS_JWT_SECRET", _DEV_SECRET)
JWT_TTL_S: int = int(os.environ.get("SDACS_JWT_TTL_S", "3600"))

if JWT_SECRET == _DEV_SECRET:
    warnings.warn(
        "SDACS_JWT_SECRET is not set — using insecure dev default. "
        "Set the env var before deploying to production.",
        stacklevel=1,
    )


# --- Roles ---


class Role(IntEnum):
    viewer = 1
    operator = 2
    admin = 3

    @classmethod
    def from_str(cls, s: str) -> "Role":
        try:
            return cls[s.lower()]
        except KeyError:
            raise ValueError(f"unknown role: {s!r}")


# --- JWT (HS256, stdlib only — no external dependencies) ---


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padded = s + "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(padded)


@dataclass(frozen=True)
class TokenClaims:
    sub: str    # subject (user/client id)
    role: str   # "viewer" | "operator" | "admin"
    exp: int    # expiry Unix timestamp
    iat: int    # issued-at Unix timestamp
    jti: str    # unique token id (for revocation lists — P714)


def issue_token(sub: str, role: str, ttl_s: int = JWT_TTL_S) -> str:
    """Issue an HS256 JWT. Raises ValueError for unknown roles."""
    Role.from_str(role)
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": sub,
        "role": role,
        "iat": now,
        "exp": now + ttl_s,
        "jti": str(uuid.uuid4()),
    }
    h = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{h}.{p}".encode()
    sig = hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url_encode(sig)}"


def verify_token(token: str) -> TokenClaims:
    """Verify HS256 JWT. Raises ValueError on malformed/expired/invalid token."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("malformed token: expected 3 parts")
    h, p, s = parts
    signing_input = f"{h}.{p}".encode()
    expected_sig = hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    try:
        actual_sig = _b64url_decode(s)
    except Exception as exc:
        raise ValueError("signature decode error") from exc
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("invalid signature")
    try:
        payload = json.loads(_b64url_decode(p))
    except Exception as exc:
        raise ValueError(f"payload decode error: {exc}") from exc
    if payload.get("exp", 0) < int(time.time()):
        raise ValueError("token expired")
    return TokenClaims(
        sub=str(payload.get("sub", "")),
        role=str(payload.get("role", "viewer")),
        exp=int(payload.get("exp", 0)),
        iat=int(payload.get("iat", 0)),
        jti=str(payload.get("jti", "")),
    )


# --- Audit log ---

_MAX_AUDIT_ENTRIES = 1000


@dataclass
class AuditEntry:
    timestamp_ns: int
    sub: str
    role: str
    action: str
    resource: str
    status: str     # "ok" | "denied" | "error"
    detail: str = ""


class AuditLog:
    """Thread-safe in-memory circular audit log. Swap with DB write in P714."""

    def __init__(self, maxlen: int = _MAX_AUDIT_ENTRIES) -> None:
        self._entries: collections.deque[AuditEntry] = collections.deque(maxlen=maxlen)

    def record(
        self,
        sub: str,
        role: str,
        action: str,
        resource: str,
        status: str,
        detail: str = "",
    ) -> None:
        self._entries.append(
            AuditEntry(
                timestamp_ns=time.time_ns(),
                sub=sub,
                role=role,
                action=action,
                resource=resource,
                status=status,
                detail=detail,
            )
        )

    def recent(self, n: int = 50) -> list[dict]:
        entries = list(self._entries)
        tail = entries[-n:] if n < len(entries) else entries
        return [
            {
                "timestamp_ns": e.timestamp_ns,
                "sub": e.sub,
                "role": e.role,
                "action": e.action,
                "resource": e.resource,
                "status": e.status,
                "detail": e.detail,
            }
            for e in tail
        ]


AUDIT: AuditLog = AuditLog()


# --- FastAPI dependency helpers ---


def _parse_bearer(authorization: str) -> str:
    if not authorization.startswith("Bearer "):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="missing or invalid bearer token")
    return authorization[len("Bearer "):]


def _check_min_role(authorization: str, min_role: Role) -> TokenClaims:
    from fastapi import HTTPException
    token = _parse_bearer(authorization)
    try:
        claims = verify_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    if Role.from_str(claims.role) < min_role:
        raise HTTPException(
            status_code=403,
            detail=f"role {claims.role!r} insufficient (need {min_role.name!r})",
        )
    return claims


def require_viewer(authorization: str = "") -> TokenClaims:
    """FastAPI dependency: any authenticated user."""
    return _check_min_role(authorization, Role.viewer)


def require_operator(authorization: str = "") -> TokenClaims:
    """FastAPI dependency: operator or admin."""
    return _check_min_role(authorization, Role.operator)


def require_admin(authorization: str = "") -> TokenClaims:
    """FastAPI dependency: admin only."""
    return _check_min_role(authorization, Role.admin)
