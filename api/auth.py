"""P712 — JWT/RBAC + 감사로그.

JWT HS256 토큰 발급·검증, 역할 기반 접근제어(RBAC), 감사로그를 제공한다.
외부 의존성 없이 표준 라이브러리만 사용한다.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from fastapi import Depends, Header, HTTPException

LOGGER = logging.getLogger("sdacs.auth")

JWT_SECRET: str = os.getenv("SDACS_JWT_SECRET", "sdacs-dev-secret-change-in-production")
JWT_EXPIRE_SECONDS: int = int(os.getenv("SDACS_JWT_EXPIRE", "3600"))
_JWT_HEADER_B64: str = (
    base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=").decode()
)


# --- 역할 정의 ---

class Role(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    Role.ADMIN: frozenset({"read", "write", "run", "admin"}),
    Role.OPERATOR: frozenset({"read", "write", "run"}),
    Role.VIEWER: frozenset({"read"}),
}


# --- 토큰 페이로드 ---

@dataclass(frozen=True)
class TokenPayload:
    sub: str
    role: Role
    iat: int
    exp: int


# --- 감사 로그 ---

@dataclass
class AuditEvent:
    timestamp_ns: int
    subject: str
    role: str
    method: str
    endpoint: str
    status_code: int | None = None
    client_ip: str | None = None


_audit_log: list[AuditEvent] = []
_MAX_AUDIT_ENTRIES = 10_000


def record_audit_event(event: AuditEvent) -> None:
    _audit_log.append(event)
    if len(_audit_log) > _MAX_AUDIT_ENTRIES:
        del _audit_log[:1000]
    LOGGER.info(
        "AUDIT sub=%s role=%s %s %s status=%s",
        event.subject, event.role, event.method, event.endpoint, event.status_code,
    )


def get_audit_log(limit: int = 100) -> list[dict[str, Any]]:
    return [
        {
            "timestamp_ns": e.timestamp_ns,
            "subject": e.subject,
            "role": e.role,
            "method": e.method,
            "endpoint": e.endpoint,
            "status_code": e.status_code,
            "client_ip": e.client_ip,
        }
        for e in _audit_log[-limit:]
    ]


# --- JWT helpers ---

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    pad = (4 - len(s) % 4) % 4
    return base64.urlsafe_b64decode(s + "=" * pad)


def _hs256_sign(header_b64: str, body_b64: str, secret: str) -> str:
    msg = f"{header_b64}.{body_b64}".encode()
    sig = hmac.new(secret.encode(), msg, hashlib.sha256).digest()
    return _b64url_encode(sig)


def create_token(sub: str, role: Role, secret: str = JWT_SECRET) -> str:
    """JWT HS256 토큰을 생성한다."""
    now = int(time.time())
    payload = {"sub": sub, "role": role.value, "iat": now, "exp": now + JWT_EXPIRE_SECONDS}
    body_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    sig = _hs256_sign(_JWT_HEADER_B64, body_b64, secret)
    return f"{_JWT_HEADER_B64}.{body_b64}.{sig}"


def decode_token(token: str, secret: str = JWT_SECRET) -> TokenPayload:
    """JWT 토큰을 검증하고 페이로드를 반환한다."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("malformed token")
        header_b64, body_b64, sig_b64 = parts
        expected_sig = _hs256_sign(header_b64, body_b64, secret)
        if not hmac.compare_digest(expected_sig, sig_b64):
            raise ValueError("signature mismatch")
        payload = json.loads(_b64url_decode(body_b64))
        if payload.get("exp", 0) < time.time():
            raise ValueError("token expired")
        return TokenPayload(
            sub=str(payload["sub"]),
            role=Role(payload["role"]),
            iat=int(payload["iat"]),
            exp=int(payload["exp"]),
        )
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=401, detail=f"invalid token: {exc}") from exc


# --- FastAPI 의존성 ---

async def get_token_payload(authorization: str = Header(default="")) -> TokenPayload:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    return decode_token(authorization[len("Bearer "):])


def require_permission(permission: str):
    """특정 permission이 필요한 FastAPI Depends 팩토리."""
    async def _dep(payload: TokenPayload = Depends(get_token_payload)) -> TokenPayload:
        allowed = _ROLE_PERMISSIONS.get(payload.role, frozenset())
        if permission not in allowed:
            raise HTTPException(
                status_code=403,
                detail=f"role '{payload.role}' lacks permission '{permission}'",
            )
        record_audit_event(AuditEvent(
            timestamp_ns=time.time_ns(),
            subject=payload.sub,
            role=payload.role.value,
            method="",
            endpoint="",
            status_code=200,
        ))
        return payload
    return _dep


require_read = require_permission("read")
require_write = require_permission("write")
require_run = require_permission("run")
require_admin = require_permission("admin")
