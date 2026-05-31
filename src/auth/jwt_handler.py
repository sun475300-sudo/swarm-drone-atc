"""JWT Bearer 토큰 발급 및 검증 (P712).

PyJWT 없이 표준 라이브러리(hmac, hashlib, base64, json)만 사용.
HS256(HMAC-SHA256) 구현.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Optional

SECRET_KEY: str = os.environ.get("SDACS_JWT_SECRET", "change-me-in-production")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS: int = int(
    os.environ.get("SDACS_JWT_EXPIRE_MINUTES", "60")
) * 60


@dataclass
class TokenData:
    sub: str
    role: str
    exp: Optional[float] = None


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def create_access_token(sub: str, role: str = "viewer") -> str:
    """JWT 액세스 토큰 생성 (HS256)."""
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64url_encode(
        json.dumps(
            {"sub": sub, "role": role, "exp": time.time() + ACCESS_TOKEN_EXPIRE_SECONDS}
        ).encode()
    )
    signing_input = f"{header}.{payload}"
    sig = hmac.new(
        SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    return f"{signing_input}.{_b64url_encode(sig)}"


def decode_token(token: str) -> TokenData:
    """JWT 토큰 검증 및 페이로드 반환. 실패 시 ValueError."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid token format")
    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}"
    expected_sig = hmac.new(
        SECRET_KEY.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    actual_sig = _b64url_decode(sig_b64)
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("Invalid token signature")
    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception as exc:
        raise ValueError(f"Invalid token payload: {exc}") from exc
    if payload.get("exp", 0) < time.time():
        raise ValueError("Token expired")
    return TokenData(
        sub=payload["sub"],
        role=payload.get("role", "viewer"),
        exp=payload.get("exp"),
    )
