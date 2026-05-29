"""P712: JWT-HMAC HS256 RBAC + 감사 로그.

stdlib만 사용 (hmac, hashlib, base64, json, secrets).
외부 라이브러리 의존 없음.

주의:
- alg 혼동 공격 방지: 발급·검증 모두 HS256 고정
- 만료 검증 필수: exp 필드 항상 확인
- 상수 시간 비교: hmac.compare_digest 사용
"""

from __future__ import annotations

import base64
import collections
import hashlib
import hmac
import json
import logging
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

_logger = logging.getLogger(__name__)

# 기본 설정
DEFAULT_TOKEN_TTL_SEC = 3600            # 1시간
MAX_AUDIT_LOG_SIZE = 1000
ALGORITHM = "HS256"                     # 고정 — alg 혼동 방지
SUPPORTED_ALGORITHMS = frozenset(["HS256"])


class Role(Enum):
    VIEWER = 1
    OPERATOR = 2
    ADMIN = 3

    def __ge__(self, other: "Role") -> bool:
        return self.value >= other.value

    def __gt__(self, other: "Role") -> bool:
        return self.value > other.value


@dataclass
class TokenPayload:
    sub: str            # subject (user_id)
    role: Role
    iat: float          # issued at
    exp: float          # expiry
    jti: str = field(default_factory=lambda: secrets.token_hex(8))


@dataclass
class AuditEntry:
    timestamp: float
    action: str
    user_id: str
    detail: str = ""


class AuditLog:
    """인메모리 감사 로그 (maxlen 순환)."""

    def __init__(self, maxlen: int = MAX_AUDIT_LOG_SIZE) -> None:
        self._entries: collections.deque[AuditEntry] = collections.deque(maxlen=maxlen)

    def record(self, action: str, user_id: str, detail: str = "") -> None:
        self._entries.append(AuditEntry(time.time(), action, user_id, detail))

    def recent(self, n: int = 50) -> list[AuditEntry]:
        return list(self._entries)[-n:]

    def __len__(self) -> int:
        return len(self._entries)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    # base64url padding 복원
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def _sign(header_b64: str, payload_b64: str, secret: bytes) -> str:
    msg = f"{header_b64}.{payload_b64}".encode()
    return _b64url_encode(hmac.new(secret, msg, hashlib.sha256).digest())


class JWTAuth:
    """HS256 JWT 발급·검증 + RBAC 헬퍼."""

    def __init__(self, secret_key: str | None = None, ttl_sec: int = DEFAULT_TOKEN_TTL_SEC) -> None:
        raw_secret = secret_key or secrets.token_hex(32)
        self._secret = raw_secret.encode()
        self.ttl_sec = ttl_sec
        self.audit = AuditLog()
        self._revoked: set[str] = set()

    def issue(self, user_id: str, role: Role) -> str:
        """JWT 발급."""
        now = time.time()
        payload = TokenPayload(sub=user_id, role=role, iat=now, exp=now + self.ttl_sec)
        header = _b64url_encode(json.dumps({"alg": ALGORITHM, "typ": "JWT"}).encode())
        body = _b64url_encode(json.dumps({
            "sub": payload.sub,
            "role": payload.role.name,
            "iat": payload.iat,
            "exp": payload.exp,
            "jti": payload.jti,
        }).encode())
        sig = _sign(header, body, self._secret)
        self.audit.record("token_issued", user_id, f"role={role.name}")
        return f"{header}.{body}.{sig}"

    def verify(self, token: str) -> TokenPayload:
        """JWT 검증. 실패 시 ValueError 발생."""
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("JWT 구조 오류")

        header_b64, payload_b64, sig = parts

        # alg 혼동 방지: 헤더 alg 검증
        try:
            header = json.loads(_b64url_decode(header_b64))
        except Exception as exc:
            raise ValueError("JWT 헤더 파싱 실패") from exc

        if header.get("alg") not in SUPPORTED_ALGORITHMS:
            raise ValueError(f"지원하지 않는 알고리즘: {header.get('alg')}")

        # 서명 검증 (상수 시간 비교)
        expected_sig = _sign(header_b64, payload_b64, self._secret)
        if not hmac.compare_digest(expected_sig, sig):
            raise ValueError("서명 검증 실패")

        try:
            claims = json.loads(_b64url_decode(payload_b64))
        except Exception as exc:
            raise ValueError("JWT 페이로드 파싱 실패") from exc

        # 만료 검증
        if time.time() > claims.get("exp", 0):
            raise ValueError("토큰 만료")

        # 폐기 검증
        jti = claims.get("jti", "")
        if jti in self._revoked:
            raise ValueError("폐기된 토큰")

        try:
            role = Role[claims["role"]]
        except KeyError as exc:
            raise ValueError(f"알 수 없는 Role: {claims.get('role')}") from exc

        return TokenPayload(
            sub=claims["sub"],
            role=role,
            iat=claims["iat"],
            exp=claims["exp"],
            jti=jti,
        )

    def revoke(self, token: str) -> None:
        """토큰 폐기 (jti 블랙리스트 등록).

        만료된 토큰도 jti를 추출해 블랙리스트 등록 (감사 누락 방지).
        """
        parts = token.split(".")
        if len(parts) != 3:
            return
        try:
            claims = json.loads(_b64url_decode(parts[1]))
            jti = claims.get("jti", "")
            sub = claims.get("sub", "unknown")
        except Exception:
            return
        if jti:
            self._revoked.add(jti)
            self.audit.record("token_revoked", sub)

    def require_role(self, token: str, min_role: Role) -> TokenPayload:
        """역할 요구사항 검증. 부족 시 PermissionError."""
        payload = self.verify(token)
        if payload.role < min_role:
            self.audit.record("access_denied", payload.sub,
                              f"required={min_role.name}, actual={payload.role.name}")
            raise PermissionError(f"권한 부족: {min_role.name} 이상 필요")
        self.audit.record("access_granted", payload.sub, f"role={payload.role.name}")
        return payload


import threading as _threading

# 모듈 수준 공유 인스턴스 (FastAPI Depends 패턴)
_default_auth: JWTAuth | None = None
_auth_lock = _threading.Lock()


def get_auth() -> JWTAuth:
    """스레드 안전 싱글톤. SDACS_JWT_SECRET 환경변수 필수."""
    global _default_auth
    if _default_auth is None:
        with _auth_lock:
            if _default_auth is None:
                import os
                secret = os.environ.get("SDACS_JWT_SECRET")
                if not secret:
                    raise RuntimeError(
                        "SDACS_JWT_SECRET 환경변수 필요. "
                        "예: export SDACS_JWT_SECRET=$(python3 -c \"import secrets; print(secrets.token_hex(32))\")"
                    )
                _default_auth = JWTAuth(secret_key=secret)
    return _default_auth
