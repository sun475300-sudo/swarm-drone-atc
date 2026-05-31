"""P712 — JWT Bearer auth + RBAC + 감사 로그.

외부 라이브러리 없이 순수 Python(hmac·hashlib·base64)으로 HS256 JWT 구현.

환경변수:
    SDACS_JWT_SECRET   HS256 서명 키 (필수, 최소 32자)
    SDACS_JWT_TTL_MIN  토큰 유효 기간(분), 기본 60

역할(계층):
    viewer   — GET 엔드포인트만 허용
    operator — viewer + 시나리오 실행
    admin    — 전체 접근 + 감사 로그 조회
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

try:
    from fastapi import Depends, Header, HTTPException
except ImportError as exc:
    raise RuntimeError("fastapi required") from exc

LOGGER = logging.getLogger("sdacs.auth")

ALGORITHM = "HS256"
ROLES_HIERARCHY = ("viewer", "operator", "admin")
AUDIT_LOG_PATH = Path(os.getenv("SDACS_AUDIT_LOG", "data/audit.log"))

_DEV_SECRET = "dev-insecure-key-change-before-production-please!!"


def _secret() -> str:
    key = os.getenv("SDACS_JWT_SECRET", "")
    if len(key) < 32:
        LOGGER.warning("SDACS_JWT_SECRET not set or too short — using insecure dev key")
        return _DEV_SECRET
    return key


def _ttl_minutes() -> int:
    return int(os.getenv("SDACS_JWT_TTL_MIN", "60"))


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def _sign(header_payload: str, secret: str) -> str:
    sig = hmac.new(secret.encode(), header_payload.encode(), hashlib.sha256).digest()
    return _b64url_encode(sig)


def create_access_token(sub: str, role: str, extra: dict[str, Any] | None = None) -> str:
    """``sub`` / ``role`` 클레임으로 HS256 JWT 토큰을 발급한다."""
    if role not in ROLES_HIERARCHY:
        raise ValueError(f"unknown role {role!r}")
    now = int(time.time())
    header = _b64url_encode(json.dumps({"alg": ALGORITHM, "typ": "JWT"}).encode())
    payload_data: dict[str, Any] = {
        "sub": sub,
        "role": role,
        "iat": now,
        "exp": now + _ttl_minutes() * 60,
    }
    if extra:
        payload_data.update(extra)
    payload = _b64url_encode(json.dumps(payload_data).encode())
    sig = _sign(f"{header}.{payload}", _secret())
    return f"{header}.{payload}.{sig}"


def validate_token(token: str) -> dict[str, Any]:
    """JWT를 검증하고 클레임 딕셔너리를 반환한다. 실패 시 HTTPException(401)."""
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="malformed token")
    header_b64, payload_b64, sig_b64 = parts
    expected_sig = _sign(f"{header_b64}.{payload_b64}", _secret())
    if not hmac.compare_digest(expected_sig, sig_b64):
        raise HTTPException(status_code=401, detail="invalid token signature")
    try:
        claims: dict[str, Any] = json.loads(_b64url_decode(payload_b64))
    except Exception as exc:
        raise HTTPException(status_code=401, detail="token payload decode error") from exc
    if claims.get("exp", 0) < int(time.time()):
        raise HTTPException(status_code=401, detail="token expired")
    if "sub" not in claims or "role" not in claims:
        raise HTTPException(status_code=401, detail="token missing required claims")
    return claims


def _extract_token(authorization: str = Header(default="")) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    return authorization[len("Bearer "):]


def require_role(minimum_role: str):
    """FastAPI Depends 팩토리 — 최소 역할 이상인 토큰만 통과시킨다."""
    required_level = ROLES_HIERARCHY.index(minimum_role)

    def _check(token: str = Depends(_extract_token)) -> dict[str, Any]:
        claims = validate_token(token)
        role = claims.get("role", "")
        if role not in ROLES_HIERARCHY:
            raise HTTPException(status_code=403, detail=f"unknown role: {role}")
        if ROLES_HIERARCHY.index(role) < required_level:
            raise HTTPException(
                status_code=403,
                detail=f"requires {minimum_role!r} role, got {role!r}",
            )
        return claims

    return _check


def write_audit_log(event: str, subject: str, details: dict[str, Any] | None = None) -> None:
    """감사 로그를 NDJSON 형식으로 AUDIT_LOG_PATH 에 추가한다."""
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": time.time(),
        "event": event,
        "sub": subject,
        **(details or {}),
    }
    try:
        with AUDIT_LOG_PATH.open("a") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:
        LOGGER.warning("audit log write failed: %s", exc)


def read_audit_log(limit: int = 200) -> list[dict[str, Any]]:
    """감사 로그 마지막 ``limit`` 줄을 반환한다."""
    if not AUDIT_LOG_PATH.exists():
        return []
    lines = AUDIT_LOG_PATH.read_text().splitlines()
    records = []
    for line in reversed(lines[-limit:]):
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records
