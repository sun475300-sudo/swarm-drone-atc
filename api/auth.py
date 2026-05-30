"""SDACS API 인증/권한 모듈 — Phase P712.

JWT Bearer 토큰 기반 인증 + 역할(Role) 기반 접근 제어(RBAC).

역할 계층:
    viewer  → 조회만 가능
    operator→ 조회 + 시뮬레이션 실행
    admin   → 전체 권한 + 감사 로그 조회

환경변수:
    SDACS_JWT_SECRET  — HMAC-SHA256 서명 키 (필수, 32자 이상 권장)
    SDACS_JWT_EXPIRY  — 토큰 유효 시간(초), 기본 3600

사용법:
    from api.auth import require_role, Role, issue_token
    token = issue_token(sub="user@example.com", role=Role.OPERATOR)

    @app.get("/api/scenarios/{id}/run")
    async def run(user=Depends(require_role(Role.OPERATOR))):
        ...
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from enum import Enum
from typing import Any

from fastapi import Depends, Header, HTTPException, status

_SECRET: str | None = None
_EXPIRY_S: int = int(os.getenv("SDACS_JWT_EXPIRY", "3600"))


def _secret() -> str:
    global _SECRET
    if _SECRET is None:
        _SECRET = os.getenv("SDACS_JWT_SECRET", "")
    if not _SECRET:
        raise RuntimeError(
            "SDACS_JWT_SECRET 환경변수가 설정되지 않았습니다. "
            "export SDACS_JWT_SECRET=$(openssl rand -hex 32)"
        )
    return _SECRET


# ---------------------------------------------------------------------------
# Role
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


def _has_permission(user_role: Role, required: Role) -> bool:
    return _ROLE_RANK[user_role] >= _ROLE_RANK[required]


# ---------------------------------------------------------------------------
# Minimal JWT (HS256) — no external dependency
# ---------------------------------------------------------------------------

def _b64url_encode(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    return urlsafe_b64decode(s + "=" * (padding % 4))


def _sign(header_b64: str, payload_b64: str, secret: str) -> str:
    msg = f"{header_b64}.{payload_b64}".encode()
    sig = hmac.new(secret.encode(), msg, hashlib.sha256).digest()
    return _b64url_encode(sig)


def issue_token(
    sub: str,
    role: Role = Role.VIEWER,
    expiry_s: int | None = None,
) -> str:
    """JWT 토큰 발급.

    Args:
        sub: 사용자 식별자 (이메일 등).
        role: 부여할 역할.
        expiry_s: 유효 시간(초). None이면 환경변수 기본값 사용.

    Returns:
        JWT 문자열 (header.payload.signature).
    """
    secret = _secret()
    exp = int(time.time()) + (expiry_s if expiry_s is not None else _EXPIRY_S)
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64url_encode(
        json.dumps({"sub": sub, "role": role.value, "exp": exp, "iat": int(time.time())}).encode()
    )
    sig = _sign(header, payload, secret)
    return f"{header}.{payload}.{sig}"


def decode_token(token: str) -> dict[str, Any]:
    """JWT 토큰 검증 및 payload 반환.

    Raises:
        HTTPException 401: 토큰이 유효하지 않거나 만료됨.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="토큰 형식 오류")
    header_b64, payload_b64, sig_b64 = parts
    try:
        secret = _secret()
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    expected = _sign(header_b64, payload_b64, secret)
    if not hmac.compare_digest(expected, sig_b64):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="서명 검증 실패")

    try:
        payload: dict[str, Any] = json.loads(_b64url_decode(payload_b64))
    except Exception as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="payload 디코딩 오류") from exc

    if payload.get("exp", 0) < int(time.time()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="토큰 만료")

    return payload


# ---------------------------------------------------------------------------
# FastAPI dependency helpers
# ---------------------------------------------------------------------------

class TokenUser:
    """검증된 토큰에서 추출한 사용자 정보."""

    def __init__(self, sub: str, role: Role) -> None:
        self.sub = sub
        self.role = role

    def __repr__(self) -> str:
        return f"TokenUser(sub={self.sub!r}, role={self.role.value!r})"


async def _extract_user(authorization: str = Header(default="")) -> TokenUser:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Bearer 토큰 누락")
    token = authorization[len("Bearer "):]
    payload = decode_token(token)
    try:
        role = Role(payload["role"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="역할 정보 누락") from exc
    return TokenUser(sub=payload.get("sub", ""), role=role)


def require_role(minimum: Role = Role.VIEWER):
    """최소 역할을 요구하는 FastAPI Depends 팩토리.

    Usage::
        @app.get("/admin/logs")
        async def logs(user=Depends(require_role(Role.ADMIN))):
            ...
    """
    async def _check(user: TokenUser = Depends(_extract_user)) -> TokenUser:
        if not _has_permission(user.role, minimum):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail=f"{minimum.value} 이상의 권한이 필요합니다 (현재: {user.role.value})",
            )
        return user
    return _check


# ---------------------------------------------------------------------------
# 감사 로그 (in-memory, P714에서 TimescaleDB로 교체)
# ---------------------------------------------------------------------------

_AUDIT_LOG: list[dict[str, Any]] = []
_AUDIT_MAX = 10_000


def audit_log(user: TokenUser, action: str, detail: str = "") -> None:
    """감사 이벤트를 기록한다."""
    entry = {
        "ts": time.time(),
        "sub": user.sub,
        "role": user.role.value,
        "action": action,
        "detail": detail,
    }
    _AUDIT_LOG.append(entry)
    if len(_AUDIT_LOG) > _AUDIT_MAX:
        _AUDIT_LOG.pop(0)


def get_audit_log(limit: int = 100) -> list[dict[str, Any]]:
    """최근 감사 로그를 반환한다."""
    return _AUDIT_LOG[-limit:]
