"""JWT/RBAC authentication module for SDACS FastAPI backend.

P712: Full JWT validation replacing the Bearer-prefix stub in fastapi_server.py.

Usage:
    from api.auth import create_access_token, decode_token, require_role, Role, authenticate_user
"""

from __future__ import annotations

import os
import sys
import time
import unittest.mock
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

# ---------------------------------------------------------------------------
# PyJWT bootstrap
# ---------------------------------------------------------------------------
# The system cryptography package has broken Rust/pyo3 bindings (_cffi_backend
# missing) that cause a hard panic when imported.  HS256 only needs hmac/hashlib
# (pure Python), so we block the broken modules before importing jwt.
# Remove this block once the environment's cryptography package is fixed.
_CRYPTO_STUB_MODULES = {
    "cryptography": None,
    "cryptography.hazmat": None,
    "cryptography.hazmat._oid": None,
    "cryptography.hazmat.bindings": None,
    "cryptography.hazmat.bindings._rust": None,
    "cryptography.hazmat.backends": None,
    "cryptography.hazmat.primitives": None,
    "cryptography.hazmat.primitives.asymmetric": None,
    "cryptography.hazmat.primitives.asymmetric.ec": None,
    "cryptography.hazmat.primitives.asymmetric.utils": None,
    "cryptography.hazmat.primitives.hashes": None,
    "cryptography.hazmat.primitives.padding": None,
    "cryptography.exceptions": None,
}

# Only patch if the module hasn't been successfully imported yet
if "jwt" not in sys.modules:
    _pyjwt_local = "/tmp/pyjwt_local"
    if _pyjwt_local not in sys.path:
        sys.path.insert(0, _pyjwt_local)
    with unittest.mock.patch.dict("sys.modules", _CRYPTO_STUB_MODULES):
        import jwt as _jwt_module
    sys.modules["jwt"] = _jwt_module
else:
    _jwt_module = sys.modules["jwt"]

import jwt  # noqa: E402  (now safe — loaded above)
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError  # noqa: E402

try:
    from fastapi import Depends, HTTPException, Header
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("FastAPI is required: pip install 'fastapi>=0.110'") from exc

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SECRET_KEY: str = os.environ.get("SDACS_SECRET_KEY", "dev-secret-key-change-in-production!")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

# ---------------------------------------------------------------------------
# Role hierarchy
# ---------------------------------------------------------------------------


class Role(IntEnum):
    """Role hierarchy.  Higher value = higher privilege."""

    VIEWER = 1
    OPERATOR = 2
    ADMIN = 3


# ---------------------------------------------------------------------------
# TokenData
# ---------------------------------------------------------------------------


@dataclass
class TokenData:
    """Decoded JWT payload."""

    sub: str
    role: Role
    exp: int


# ---------------------------------------------------------------------------
# In-memory user store (dev only)
# ---------------------------------------------------------------------------

# NOTE: passwords are stored as plaintext here for development convenience.
# Replace with bcrypt hashed passwords in production (e.g. bcrypt.checkpw()).
USERS: dict[str, dict] = {
    "admin": {"password_hash": "admin123", "role": Role.ADMIN},
    "operator": {"password_hash": "op123", "role": Role.OPERATOR},
    "viewer": {"password_hash": "view123", "role": Role.VIEWER},
}

# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def create_access_token(sub: str, role: Role) -> str:
    """Create a signed JWT access token for the given subject and role."""
    exp = int(time.time()) + ACCESS_TOKEN_EXPIRE_MINUTES * 60
    payload = {"sub": sub, "role": role.name, "exp": exp}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> TokenData:
    """Decode and validate a JWT token.

    Raises:
        HTTPException(401): if the token is missing, expired, or invalid.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token expired")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="invalid token")

    sub = payload.get("sub")
    role_name = payload.get("role")
    exp = payload.get("exp")

    if not sub or not role_name or exp is None:
        raise HTTPException(status_code=401, detail="malformed token payload")

    try:
        role = Role[role_name]
    except KeyError:
        raise HTTPException(status_code=401, detail=f"unknown role: {role_name}")

    return TokenData(sub=sub, role=role, exp=int(exp))


def authenticate_user(username: str, password: str) -> Optional[TokenData]:
    """Authenticate a user by plaintext password (dev only — use bcrypt in prod).

    Returns:
        TokenData if credentials are valid, None otherwise.
    """
    user = USERS.get(username)
    if user is None:
        return None
    # NOTE: plaintext comparison — replace with bcrypt in prod
    if user["password_hash"] != password:
        return None
    return TokenData(
        sub=username,
        role=user["role"],
        exp=int(time.time()) + ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ---------------------------------------------------------------------------
# FastAPI dependency factory
# ---------------------------------------------------------------------------


def require_role(minimum_role: Role):
    """Return a FastAPI dependency that enforces a minimum role.

    Usage::

        @app.post("/admin-only")
        async def admin_endpoint(_: TokenData = Depends(require_role(Role.ADMIN))):
            ...
    """

    async def _dependency(authorization: str = Header(default="")) -> TokenData:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="missing bearer token")
        token_data = decode_token(authorization[len("Bearer "):])
        if token_data.role < minimum_role:
            raise HTTPException(
                status_code=403,
                detail=f"requires {minimum_role.name} role, got {token_data.role.name}",
            )
        return token_data

    return _dependency
