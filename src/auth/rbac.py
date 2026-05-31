"""역할 기반 접근 제어 (RBAC) — P712."""
from __future__ import annotations

from enum import Enum
from typing import Callable, Set


class Role(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    ANALYST = "analyst"
    VIEWER = "viewer"


class Permission(str, Enum):
    # 드론 제어
    DRONE_READ = "drone:read"
    DRONE_WRITE = "drone:write"
    DRONE_CMD = "drone:command"
    # 공역 관리
    AIRSPACE_READ = "airspace:read"
    AIRSPACE_WRITE = "airspace:write"
    # 보고서/분석
    REPORT_READ = "report:read"
    REPORT_EXPORT = "report:export"
    # 관리자 전용
    USER_MANAGE = "user:manage"
    AUDIT_READ = "audit:read"


ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.ADMIN: set(Permission),
    Role.OPERATOR: {
        Permission.DRONE_READ,
        Permission.DRONE_WRITE,
        Permission.DRONE_CMD,
        Permission.AIRSPACE_READ,
        Permission.AIRSPACE_WRITE,
        Permission.REPORT_READ,
        Permission.REPORT_EXPORT,
    },
    Role.ANALYST: {
        Permission.DRONE_READ,
        Permission.AIRSPACE_READ,
        Permission.REPORT_READ,
        Permission.REPORT_EXPORT,
    },
    Role.VIEWER: {
        Permission.DRONE_READ,
        Permission.AIRSPACE_READ,
        Permission.REPORT_READ,
    },
}


def require_permission(permission: Permission) -> Callable:
    """FastAPI dependency factory — 권한 부족 시 403 raise."""

    def _check(role: str) -> bool:
        try:
            r = Role(role)
        except ValueError:
            return False
        return permission in ROLE_PERMISSIONS.get(r, set())

    _check.__name__ = f"require_{permission.value.replace(':', '_')}"
    return _check
