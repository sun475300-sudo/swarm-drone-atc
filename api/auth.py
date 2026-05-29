"""P712 — JWT Bearer + RBAC 인증 모듈.

환경 변수:
    SDACS_JWT_SECRET   : HS256 서명 키 (필수, 최소 32바이트)
    SDACS_JWT_ALG      : 알고리즘 (기본 HS256)
    SDACS_JWT_TTL_S    : 토큰 유효 시간(초, 기본 3600)
    SDACS_DEV_TOKEN    : 개발 편의용 고정 토큰 (운영에서 절대 사용 금지)

역할(Role) 체계:
    viewer   — 읽기 전용 (snapshot, scenario 목록)
    operator — 시나리오 실행 + 읽기
    admin    — 전체 (telemetry push, 관리 API)

사용법 (FastAPI Depends):
    @app.get("/api/runs/{run_id}")
    async def get_run(run_id: str, claims: Claims = Depends(require_operator)):
        ...
"""

from __future__ import annotations

import hmac
import hashlib
import json
import logging
import os
import time
import base64
from dataclasses import dataclass
from typing import Iterable

from fastapi import Depends, Header, HTTPException

LOGGER = logging.getLogger("sdacs.auth")

# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------
_SECRET: bytes | None = None
_ALG = os.environ.get("SDACS_JWT_ALG", "HS256")
_TTL = int(os.environ.get("SDACS_JWT_TTL_S", "3600"))
_DEV_TOKEN = os.environ.get("SDACS_DEV_TOKEN", "")


def _secret() -> bytes:
    """JWT 서명 키를 반환한다. 미설정 시 RuntimeError."""
    global _SECRET
    if _SECRET is None:
        raw = os.environ.get("SDACS_JWT_SECRET", "")
        if not raw:
            raise RuntimeError(
                "SDACS_JWT_SECRET 환경 변수가 설정되지 않았습니다. "
                "운영 환경에서는 반드시 32바이트 이상의 난수 문자열을 설정하세요."
            )
        if len(raw) < 32:
            LOGGER.warning("SDACS_JWT_SECRET 길이가 32바이트 미만입니다. 보안을 강화하세요.")
        _SECRET = raw.encode()
    return _SECRET


# ---------------------------------------------------------------------------
# JWT 직접 구현 (PyJWT 미설치 환경 대응)
# ---------------------------------------------------------------------------

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * (pad % 4))


def _sign(header_b64: str, payload_b64: str) -> str:
    msg = f"{header_b64}.{payload_b64}".encode()
    sig = hmac.new(_secret(), msg, hashlib.sha256).digest()
    return _b64url_encode(sig)


def create_token(sub: str, roles: Iterable[str], ttl: int | None = None) -> str:
    """JWT를 발급한다."""
    now = int(time.time())
    exp = now + (ttl if ttl is not None else _TTL)
    header = _b64url_encode(json.dumps({"alg": _ALG, "typ": "JWT"}).encode())
    payload = _b64url_encode(json.dumps({
        "sub": sub,
        "roles": list(roles),
        "iat": now,
        "exp": exp,
    }).encode())
    sig = _sign(header, payload)
    return f"{header}.{payload}.{sig}"


def _verify_token(token: str) -> dict:
    """토큰을 검증하고 페이로드 dict를 반환한다. 실패 시 ValueError."""
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError:
        raise ValueError("JWT 형식 오류")

    expected_sig = _sign(header_b64, payload_b64)
    if not hmac.compare_digest(expected_sig, sig_b64):
        raise ValueError("JWT 서명 불일치")

    payload = json.loads(_b64url_decode(payload_b64))
    if payload.get("exp", 0) < int(time.time()):
        raise ValueError("JWT 만료")
    return payload


# ---------------------------------------------------------------------------
# 역할(Role) 체계
# ---------------------------------------------------------------------------

ROLES = {"viewer", "operator", "admin"}
_ROLE_HIERARCHY = {"viewer": 0, "operator": 1, "admin": 2}


@dataclass
class Claims:
    """검증된 JWT 페이로드."""
    sub: str
    roles: list[str]

    def has_role(self, required: str) -> bool:
        """required 역할 이상의 권한을 보유하는지 확인한다."""
        req_level = _ROLE_HIERARCHY.get(required, 999)
        return any(_ROLE_HIERARCHY.get(r, -1) >= req_level for r in self.roles)


# ---------------------------------------------------------------------------
# FastAPI 의존성
# ---------------------------------------------------------------------------

def _extract_claims(authorization: str) -> Claims:
    """Authorization 헤더에서 Claims를 추출한다."""
    # 개발 편의 토큰: 환경 변수를 동적으로 읽어 재시작 없이도 설정/해제 가능 (운영에서 절대 사용 금지)
    dev_token = os.environ.get("SDACS_DEV_TOKEN", "")
    if dev_token and authorization == f"Bearer {dev_token}":
        LOGGER.warning("개발용 고정 토큰이 사용되었습니다. 운영 환경에서 SDACS_DEV_TOKEN을 제거하세요.")
        return Claims(sub="dev", roles=["admin"])

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer 토큰이 필요합니다")

    token = authorization[len("Bearer "):]
    try:
        payload = _verify_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    return Claims(sub=payload.get("sub", ""), roles=payload.get("roles", []))


async def require_viewer(authorization: str = Header(default="")) -> Claims:
    """viewer 이상 역할을 요구하는 의존성."""
    claims = _extract_claims(authorization)
    if not claims.has_role("viewer"):
        raise HTTPException(status_code=403, detail="viewer 권한 필요")
    return claims


async def require_operator(authorization: str = Header(default="")) -> Claims:
    """operator 이상 역할을 요구하는 의존성."""
    claims = _extract_claims(authorization)
    if not claims.has_role("operator"):
        raise HTTPException(status_code=403, detail="operator 권한 필요")
    return claims


async def require_admin(authorization: str = Header(default="")) -> Claims:
    """admin 역할을 요구하는 의존성."""
    claims = _extract_claims(authorization)
    if not claims.has_role("admin"):
        raise HTTPException(status_code=403, detail="admin 권한 필요")
    return claims


# require_token은 fastapi_server.py 기존 코드와의 호환성을 위해 유지
async def require_token(authorization: str = Header(default="")) -> str:
    """기존 stub 대체: operator 이상 역할 검증 후 sub를 반환한다."""
    claims = await require_operator(authorization)
    return claims.sub
