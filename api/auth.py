"""P712 — JWT HS256 + RBAC 인증 모듈 (stdlib only, no PyJWT)"""

import base64
import hashlib
import hmac
import json
import os
import threading
import time
from enum import IntEnum
from typing import Callable


class Role(IntEnum):
    VIEWER = 1
    OPERATOR = 2
    ADMIN = 3


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


class JWTAuth:
    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        secret = os.environ.get("SDACS_JWT_SECRET")
        if not secret:
            raise RuntimeError("SDACS_JWT_SECRET environment variable is required")
        self._secret = secret.encode()
        self._blacklist: set[str] = set()
        self._audit: list[dict] = []
        self._lock = threading.Lock()
        self._initialized = True

    def _sign(self, message: str) -> str:
        sig = hmac.new(self._secret, message.encode(), hashlib.sha256).digest()
        return _b64url_encode(sig)

    def _make_jti(self, user_id: str, now: float) -> str:
        raw = f"{user_id}:{now}:{os.urandom(8).hex()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def issue(self, user_id: str, role: Role, expires_in: int = 3600) -> str:
        now = int(time.time())
        jti = self._make_jti(user_id, now)
        header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        payload = _b64url_encode(json.dumps({
            "sub": user_id,
            "role": int(role),
            "iat": now,
            "exp": now + expires_in,
            "jti": jti,
        }).encode())
        sig = self._sign(f"{header}.{payload}")
        token = f"{header}.{payload}.{sig}"
        with self._lock:
            self._audit.append({"ts": now, "action": "issue", "user_id": user_id, "jti": jti})
        return token

    def verify(self, token: str) -> dict:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token format")
        header_b64, payload_b64, provided_sig = parts
        expected_sig = self._sign(f"{header_b64}.{payload_b64}")
        if not hmac.compare_digest(expected_sig, provided_sig):
            raise ValueError("Invalid token signature")
        try:
            payload = json.loads(_b64url_decode(payload_b64))
        except Exception:
            raise ValueError("Invalid token payload")
        now = int(time.time())
        if payload.get("exp", 0) < now:
            raise ValueError("Token has expired")
        jti = payload.get("jti", "")
        with self._lock:
            if jti in self._blacklist:
                raise ValueError("Token has been revoked")
        return payload

    def revoke(self, token: str) -> None:
        parts = token.split(".")
        if len(parts) != 3:
            return
        _, payload_b64, _ = parts
        try:
            payload = json.loads(_b64url_decode(payload_b64))
            jti = payload.get("jti", "")
            user_id = payload.get("sub", "")
        except Exception:
            return
        if not jti:
            return
        with self._lock:
            self._blacklist.add(jti)
            self._audit.append({
                "ts": int(time.time()),
                "action": "revoke",
                "user_id": user_id,
                "jti": jti,
            })

    def require_role(self, min_role: Role) -> Callable:
        """FastAPI Dependency factory — returns a dependency function."""
        def dependency(authorization: str = "") -> dict:
            # In a real FastAPI app, authorization comes from Header(...)
            # Here we accept the raw token string for testability
            if not authorization:
                raise ValueError("Missing authorization token")
            token = authorization.removeprefix("Bearer ").strip()
            payload = self.verify(token)
            user_role = Role(payload.get("role", 0))
            if user_role < min_role:
                raise PermissionError(
                    f"Role {user_role.name} insufficient; requires {min_role.name}"
                )
            return payload
        return dependency

    def get_audit_log(self) -> list[dict]:
        with self._lock:
            return list(self._audit)
