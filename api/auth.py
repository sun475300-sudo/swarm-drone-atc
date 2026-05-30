"""P712: JWT Bearer 인증 + RBAC + 감사 로그.

Usage:
    from api.auth import create_access_token, get_current_user, require_role, Role

Quickstart (dev):
    export SDACS_JWT_SECRET=changeme
    token = create_access_token({"sub": "operator1", "role": "OPERATOR"})
    # Pass as: Authorization: Bearer <token>
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from enum import Enum
from typing import Any

from fastapi import Depends, Header, HTTPException, Request, status
from pydantic import BaseModel

# PyJWT의 cryptography 의존성이 환경에 따라 깨질 수 있으므로
# HS256을 표준 라이브러리(hmac+hashlib)로 직접 구현한다.
import base64
import hashlib
import hmac
import json as _json

LOGGER = logging.getLogger("sdacs.auth")

_JWT_SECRET = os.environ.get("SDACS_JWT_SECRET", "sdacs-dev-secret-change-in-prod")
_JWT_ALGORITHM = "HS256"
_ACCESS_TOKEN_TTL_S = int(os.environ.get("SDACS_JWT_TTL_S", "3600"))


class Role(str, Enum):
    """API 접근 역할 정의."""

    VIEWER = "VIEWER"      # 읽기 전용
    OPERATOR = "OPERATOR"  # 시나리오 실행 가능
    ADMIN = "ADMIN"        # 전체 권한 (토큰 발급 포함)


_ROLE_HIERARCHY: dict[Role, int] = {
    Role.VIEWER: 0,
    Role.OPERATOR: 1,
    Role.ADMIN: 2,
}


class TokenPayload(BaseModel):
    """JWT 페이로드 스키마."""

    sub: str
    role: Role = Role.VIEWER
    exp: int = 0
    iat: int = 0


class TokenRequest(BaseModel):
    """POST /auth/token 요청 본문."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """POST /auth/token 응답 본문."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = _ACCESS_TOKEN_TTL_S


# 개발용 인메모리 사용자 DB — 프로덕션에서는 P714 PostgreSQL 로 교체
_DEV_USERS: dict[str, dict[str, Any]] = {
    "admin": {"password": os.environ.get("SDACS_ADMIN_PASS", "admin-secret"), "role": Role.ADMIN},
    "operator": {"password": os.environ.get("SDACS_OP_PASS", "op-secret"), "role": Role.OPERATOR},
    "viewer": {"password": os.environ.get("SDACS_VIEWER_PASS", "viewer-secret"), "role": Role.VIEWER},
}


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * (pad % 4))


def create_access_token(data: dict[str, Any], ttl_s: int = _ACCESS_TOKEN_TTL_S) -> str:
    """서명된 JWT HS256 액세스 토큰을 생성한다."""
    now = int(time.time())
    payload = {**data, "iat": now, "exp": now + ttl_s}
    header = _b64url_encode(_json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    claims = _b64url_encode(_json.dumps(payload).encode())
    signing_input = f"{header}.{claims}"
    sig = hmac.new(
        _JWT_SECRET.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    return f"{signing_input}.{_b64url_encode(sig)}"


def decode_token(token: str) -> TokenPayload:
    """JWT 토큰을 검증하고 페이로드를 반환한다. 만료·서명 오류 시 HTTPException 401."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("malformed jwt")
        header_b64, claims_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{claims_b64}"
        expected = hmac.new(
            _JWT_SECRET.encode(), signing_input.encode(), hashlib.sha256
        ).digest()
        provided = _b64url_decode(sig_b64)
        if not hmac.compare_digest(expected, provided):
            raise ValueError("signature mismatch")
        raw = _json.loads(_b64url_decode(claims_b64))
    except Exception as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid token") from exc

    if raw.get("exp", 0) < int(time.time()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="token expired")
    return TokenPayload(**raw)


async def get_current_user(authorization: str = Header(default="")) -> TokenPayload:
    """FastAPI Dependency — Authorization: Bearer <token> 헤더 검증."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    token = authorization[len("Bearer "):]
    return decode_token(token)


def require_role(minimum_role: Role) -> Callable[..., TokenPayload]:
    """최소 역할 수준을 요구하는 FastAPI Dependency 팩토리."""

    async def _dependency(user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
        if _ROLE_HIERARCHY[user.role] < _ROLE_HIERARCHY[minimum_role]:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail=f"role {minimum_role.value} required, got {user.role.value}",
            )
        return user

    return _dependency


def log_audit(request: Request, user: TokenPayload, action: str, detail: str = "") -> None:
    """감사 로그 기록 (P714 DB 저장 전 임시 로거 기반 구현)."""
    LOGGER.info(
        "AUDIT user=%s role=%s action=%s detail=%s ip=%s",
        user.sub,
        user.role.value,
        action,
        detail,
        request.client.host if request.client else "unknown",
    )


def issue_token(username: str, password: str) -> TokenResponse:
    """사용자명/비밀번호를 검증하고 JWT 토큰을 발급한다."""
    user = _DEV_USERS.get(username)
    if user is None or user["password"] != password:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    token = create_access_token({"sub": username, "role": user["role"].value})
    return TokenResponse(access_token=token)
