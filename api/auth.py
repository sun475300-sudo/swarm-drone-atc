"""P712 — JWT Bearer 인증 + RBAC 모듈."""
from __future__ import annotations

import os
import time
import uuid
from enum import Enum
from typing import Optional

try:
    import jwt as pyjwt
except ImportError:
    pyjwt = None  # type: ignore

from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel

_SECRET = os.environ.get("SDACS_JWT_SECRET", "sdacs-dev-secret-change-in-prod")
_ALGORITHM = "HS256"
_TOKEN_TTL = int(os.environ.get("SDACS_TOKEN_TTL_S", "3600"))


class Role(str, Enum):
    admin = "admin"
    operator = "operator"
    viewer = "viewer"


_ROLE_RANK: dict[Role, int] = {
    Role.viewer: 0,
    Role.operator: 1,
    Role.admin: 2,
}


class TokenPayload(BaseModel):
    sub: str
    role: Role
    iat: int
    exp: int
    jti: str


def create_token(subject: str, role: Role) -> str:
    """JWT 발행 (SDACS_JWT_SECRET 환경변수 기반)."""
    if pyjwt is None:
        raise RuntimeError("PyJWT not installed: pip install PyJWT")
    now = int(time.time())
    payload = {
        "sub": subject,
        "role": role.value,
        "iat": now,
        "exp": now + _TOKEN_TTL,
        "jti": str(uuid.uuid4()),
    }
    return pyjwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def _decode_token(token: str) -> TokenPayload:
    if pyjwt is None:
        raise HTTPException(status_code=501, detail="PyJWT not installed")
    try:
        raw = pyjwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token expired")
    except pyjwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"invalid token: {exc}")
    return TokenPayload(**raw)


def require_auth(authorization: str = Header(default="")) -> TokenPayload:
    """FastAPI 의존성 — Bearer 토큰 검증."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    return _decode_token(authorization[len("Bearer "):])


def require_role(minimum: Role):
    """최소 역할 요구 의존성 팩토리."""
    def _check(payload: TokenPayload = Depends(require_auth)) -> TokenPayload:
        if _ROLE_RANK[payload.role] < _ROLE_RANK[minimum]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"role '{payload.role}' insufficient (need {minimum})",
            )
        return payload
    return _check


# 감사 로그용 간단 인메모리 링 버퍼 (production은 DB로 교체)
_audit_log: list[dict] = []
_AUDIT_MAX = 10_000


def audit(event: str, subject: str, detail: Optional[str] = None) -> None:
    _audit_log.append({"ts": time.time(), "event": event, "sub": subject, "detail": detail})
    if len(_audit_log) > _AUDIT_MAX:
        _audit_log.pop(0)


def get_audit_log(limit: int = 100) -> list[dict]:
    return _audit_log[-limit:]
