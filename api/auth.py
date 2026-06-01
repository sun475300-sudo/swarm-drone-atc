"""P712 — JWT OAuth2 + RBAC 인증·인가 모듈.

역할(Role) 계층:
    admin        → 모든 권한
    atc_operator → airspace 읽기/쓰기, 시나리오 실행/조회, 감사 로그 조회
    pilot        → airspace 읽기/쓰기 (텔레메트리 송신)
    observer     → 읽기 전용

사용법:
    from api.auth import create_access_token, get_current_user, require_role

    @app.post("/auth/token")
    async def login(form: OAuth2PasswordRequestForm = Depends()):
        user = authenticate_user(form.username, form.password)
        ...
        token = create_access_token({"sub": user.username, "role": user.role})
        return {"access_token": token, "token_type": "bearer"}

    @app.get("/secure")
    async def secure(user=Depends(require_role("atc_operator"))):
        ...
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

try:
    from passlib.context import CryptContext
except ImportError as exc:
    raise RuntimeError(
        "passlib is required. pip install 'passlib[bcrypt]'"
    ) from exc

# JWT HS256은 표준 라이브러리만으로 구현 (cryptography 패키지 의존성 제거)
import base64
import hashlib
import hmac as _hmac
import json as _json

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SECRET_KEY: str = os.environ.get(
    "SDACS_JWT_SECRET",
    "dev-secret-change-me-in-production-at-least-32-chars",
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("SDACS_TOKEN_EXPIRE_MIN", "60"))

_pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# ---------------------------------------------------------------------------
# RBAC: permissions per role
# ---------------------------------------------------------------------------

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "admin": frozenset(
        {
            "airspace:read",
            "airspace:write",
            "scenario:read",
            "scenario:run",
            "audit:read",
            "admin:users",
            "admin:config",
        }
    ),
    "atc_operator": frozenset(
        {
            "airspace:read",
            "airspace:write",
            "scenario:read",
            "scenario:run",
            "audit:read",
        }
    ),
    "pilot": frozenset({"airspace:read", "airspace:write"}),
    "observer": frozenset({"airspace:read", "scenario:read"}),
}

ALL_ROLES: frozenset[str] = frozenset(ROLE_PERMISSIONS)

# ---------------------------------------------------------------------------
# User model
# ---------------------------------------------------------------------------


@dataclass
class UserRecord:
    """``UserRecord`` 데이터를 표현한다."""

    username: str
    hashed_password: str
    role: str
    disabled: bool = False
    created_at: float = field(default_factory=time.time)

    def has_permission(self, permission: str) -> bool:
        """`permission` 권한 보유 여부를 확인한다."""
        perms = ROLE_PERMISSIONS.get(self.role, frozenset())
        return permission in perms or "admin:*" in perms


# ---------------------------------------------------------------------------
# In-memory user store (replace with DB in P714)
# ---------------------------------------------------------------------------

def _hash(password: str) -> str:
    return _pwd_context.hash(password)


_USERS: dict[str, UserRecord] = {
    "admin": UserRecord(
        username="admin",
        hashed_password=_hash(os.environ.get("SDACS_ADMIN_PASSWORD", "admin")),
        role="admin",
    ),
    "atc_operator": UserRecord(
        username="atc_operator",
        hashed_password=_hash(os.environ.get("SDACS_OPERATOR_PASSWORD", "operator")),
        role="atc_operator",
    ),
    "pilot_demo": UserRecord(
        username="pilot_demo",
        hashed_password=_hash("pilot"),
        role="pilot",
    ),
    "observer_demo": UserRecord(
        username="observer_demo",
        hashed_password=_hash("observer"),
        role="observer",
    ),
}


def get_user(username: str) -> UserRecord | None:
    """`username` 사용자를 조회한다."""
    return _USERS.get(username)


def create_user(username: str, password: str, role: str) -> UserRecord:
    """`user` 항목을 생성한다."""
    if role not in ALL_ROLES:
        raise ValueError(f"unknown role {role!r}")
    if username in _USERS:
        raise ValueError(f"user {username!r} already exists")
    user = UserRecord(
        username=username,
        hashed_password=_hash(password),
        role=role,
    )
    _USERS[username] = user
    return user


def list_users() -> list[dict[str, Any]]:
    """모든 사용자 목록을 반환한다."""
    return [
        {
            "username": u.username,
            "role": u.role,
            "disabled": u.disabled,
            "created_at": u.created_at,
        }
        for u in _USERS.values()
    ]


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------


def verify_password(plain: str, hashed: str) -> bool:
    """`password` 일치 여부를 검증한다."""
    return _pwd_context.verify(plain, hashed)


def authenticate_user(username: str, password: str) -> UserRecord | None:
    """`user` 인증을 수행한다."""
    user = get_user(username)
    if user is None or user.disabled:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


_JWT_HEADER = _b64url_encode(_json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """JWT HS256 액세스 토큰을 생성한다 (표준 라이브러리 only)."""
    payload = data.copy()
    payload["exp"] = time.time() + (
        expires_delta.total_seconds()
        if expires_delta
        else ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    payload["iat"] = time.time()
    payload_b64 = _b64url_encode(_json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{_JWT_HEADER}.{payload_b64}".encode()
    sig = _hmac.new(SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
    return f"{_JWT_HEADER}.{payload_b64}.{_b64url_encode(sig)}"


def decode_token(token: str) -> dict[str, Any]:
    """JWT HS256 토큰을 검증하고 payload를 반환한다."""
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 서명 검증
    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected_sig = _hmac.new(SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
    try:
        provided_sig = _b64url_decode(sig_b64)
    except Exception:
        provided_sig = b""
    if not _hmac.compare_digest(expected_sig, provided_sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token signature",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # payload 파싱
    try:
        payload = _json.loads(_b64url_decode(payload_b64))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 만료 확인
    exp = payload.get("exp", 0)
    if time.time() > exp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


# ---------------------------------------------------------------------------
# FastAPI dependency helpers
# ---------------------------------------------------------------------------


async def get_current_user(token: str = Depends(_oauth2_scheme)) -> UserRecord:
    """현재 인증된 사용자를 반환한다."""
    payload = decode_token(token)
    username: str | None = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token missing subject claim",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = get_user(username)
    if user is None or user.disabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="user not found or disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_permission(permission: str):
    """주어진 permission을 가진 사용자만 허용하는 FastAPI Depends를 반환한다."""

    async def _checker(user: UserRecord = Depends(get_current_user)) -> UserRecord:
        if not user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"permission required: {permission}",
            )
        return user

    return _checker


def require_role(*roles: str):
    """지정된 역할 중 하나를 가진 사용자만 허용하는 FastAPI Depends를 반환한다."""
    role_set = frozenset(roles)

    async def _checker(user: UserRecord = Depends(get_current_user)) -> UserRecord:
        if user.role not in role_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"one of roles required: {sorted(role_set)}",
            )
        return user

    return _checker


__all__ = [
    "UserRecord",
    "ROLE_PERMISSIONS",
    "ALL_ROLES",
    "get_user",
    "create_user",
    "list_users",
    "authenticate_user",
    "create_access_token",
    "decode_token",
    "get_current_user",
    "require_permission",
    "require_role",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
]
