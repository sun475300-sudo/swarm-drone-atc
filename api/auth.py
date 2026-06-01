"""P712 — JWT/RBAC 인증 모듈.

역할(Role) 계층:
    admin    — 전체 권한 (시나리오 실행, 사용자 관리, 감사 로그 조회)
    operator — 시뮬 실행 + 공역 스냅샷 조회 (사용자 관리 제외)
    viewer   — 읽기 전용 (스냅샷, 시나리오 목록)

환경 변수:
    SDACS_JWT_SECRET   — HS256 서명 키 (프로덕션 필수; 미설정 시 WARNING + 개발용 기본값)
    SDACS_JWT_EXPIRE_S — 토큰 유효기간(초), 기본 3600

Usage:
    from api.auth import require_role, create_access_token
    @app.get("/admin-only")
    async def handler(user: TokenPayload = Depends(require_role("admin"))):
        ...
"""

from __future__ import annotations

import base64
import collections
import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Callable

try:
    from fastapi import Depends, Header, HTTPException
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("FastAPI required: pip install 'fastapi>=0.110'") from exc

LOGGER = logging.getLogger("sdacs.auth")

_DEV_SECRET = "sdacs-dev-secret-CHANGE-IN-PROD"
_raw_secret = os.environ.get("SDACS_JWT_SECRET", "")
if not _raw_secret:
    LOGGER.warning(
        "SDACS_JWT_SECRET 환경변수 미설정 — 개발용 기본 시크릿 사용 중. "
        "프로덕션 배포 전 반드시 강력한 시크릿으로 교체하세요."
    )
    _raw_secret = _DEV_SECRET
_JWT_SECRET: str = _raw_secret
_JWT_EXPIRE_S = int(os.environ.get("SDACS_JWT_EXPIRE_S", "3600"))

ROLES: tuple[str, ...] = ("admin", "operator", "viewer")
_ROLE_RANK: dict[str, int] = {r: i for i, r in enumerate(ROLES)}
_EXPECTED_ALG = "HS256"


@dataclass(frozen=True)
class TokenPayload:
    sub: str
    role: str
    exp: int
    iat: int = field(default_factory=lambda: int(time.time()))


# --- 순수 Python HS256 JWT (cryptography 의존성 없음) ---

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    if pad != 4:
        s += "=" * pad
    return base64.urlsafe_b64decode(s)


def _jwt_sign(payload: dict) -> str:
    header = _b64url_encode(json.dumps({"alg": _EXPECTED_ALG, "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header}.{body}".encode()
    sig = hmac.new(_JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{body}.{_b64url_encode(sig)}"


def _jwt_verify(token: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("invalid token structure")
    header_b64, body_b64, sig_b64 = parts

    # alg 헤더 검증 (algorithm confusion 방지)
    try:
        header_data = json.loads(_b64url_decode(header_b64))
    except Exception:
        raise ValueError("invalid token structure")
    if header_data.get("alg") != _EXPECTED_ALG:
        raise ValueError("unsupported algorithm")

    signing_input = f"{header_b64}.{body_b64}".encode()
    expected_sig = hmac.new(_JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    try:
        actual_sig = _b64url_decode(sig_b64)
    except Exception:
        raise ValueError("invalid token structure")
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("signature verification failed")
    payload = json.loads(_b64url_decode(body_b64))
    if payload.get("exp", 0) < time.time():
        raise ValueError("token expired")
    return payload


# --- 감사 로그 (deque 링 버퍼 — append 원자적, P714 이후 DB로 교체) ---

_AUDIT_LOG: collections.deque[dict] = collections.deque(maxlen=10_000)


def _audit(user: str, action: str, detail: str = "") -> None:
    entry = {"ts": time.time(), "user": user, "action": action, "detail": detail}
    _AUDIT_LOG.append(entry)
    LOGGER.info("audit | user=%s action=%s detail=%s", user, action, detail)


def get_audit_log(limit: int = 100) -> list[dict]:
    entries = list(_AUDIT_LOG)
    return entries[-limit:]


# --- 토큰 생성 ---

def create_access_token(sub: str, role: str) -> str:
    if role not in ROLES:
        raise ValueError(f"invalid role '{role}'; must be one of {ROLES}")
    now = int(time.time())
    return _jwt_sign({"sub": sub, "role": role, "iat": now, "exp": now + _JWT_EXPIRE_S})


# --- FastAPI 의존성 ---

def _decode_token(authorization: str) -> TokenPayload:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization[len("Bearer "):]
    try:
        data = _jwt_verify(token)
    except ValueError as exc:
        # 내부 에러 메시지를 클라이언트에 노출하지 않음 (정보 유출 방지)
        LOGGER.warning("token validation failed: %s", exc)
        if "expired" in str(exc):
            raise HTTPException(status_code=401, detail="token expired")
        raise HTTPException(status_code=401, detail="invalid token")
    role = data.get("role", "")
    if role not in ROLES:
        raise HTTPException(status_code=403, detail="unknown role")
    return TokenPayload(sub=data["sub"], role=role, exp=data["exp"], iat=data.get("iat", 0))


def require_role(minimum_role: str) -> "Depends":
    """역할 최소 요건을 강제하는 FastAPI Depends 팩토리.

    require_role("operator") → viewer 거부, operator/admin 허용.
    """
    if minimum_role not in ROLES:
        raise ValueError(f"unknown role '{minimum_role}'")
    min_rank = _ROLE_RANK[minimum_role]

    async def dependency(authorization: str = Header(default="")) -> TokenPayload:
        payload = _decode_token(authorization)
        if _ROLE_RANK[payload.role] > min_rank:
            _audit(payload.sub, "access_denied", f"required={minimum_role} actual={payload.role}")
            raise HTTPException(status_code=403, detail="insufficient role")
        _audit(payload.sub, "access_granted", f"endpoint_role={minimum_role}")
        return payload

    return Depends(dependency)
