"""
공역 접근 제어
==============
역할 기반 접근 + 권한 매트릭스 + 감사.

사용법:
    ac = AccessControl()
    ac.add_role("PILOT", permissions=["FLY", "LAND"])
    ac.assign_role("user1", "PILOT")
    ok = ac.check("user1", "FLY")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AuditEntry:
    """감사 항목"""
    user_id: str
    action: str
    allowed: bool
    t: float = 0.0
    reason: str = ""


class AccessControl:
    """역할 기반 접근 제어."""

    def __init__(self) -> None:
        self._roles: dict[str, set[str]] = {}  # role → permissions
        self._user_roles: dict[str, str] = {}
        self._audit: list[AuditEntry] = []

    def add_role(self, role: str, permissions: list[str]) -> None:
        self._roles[role] = set(permissions)

    def assign_role(self, user_id: str, role: str) -> bool:
        if role not in self._roles:
            return False
        self._user_roles[user_id] = role
        return True

    def check(self, user_id: str, action: str, t: float = 0.0) -> bool:
        role = self._user_roles.get(user_id)
        if not role:
            self._audit.append(AuditEntry(user_id, action, False, t, "역할 미할당"))
            return False

        perms = self._roles.get(role, set())
        allowed = action in perms or "ALL" in perms

        self._audit.append(AuditEntry(
            user_id, action, allowed, t,
            f"역할 {role}" if allowed else f"권한 부족 ({role})",
        ))
        return allowed

    def get_permissions(self, user_id: str) -> set[str]:
        role = self._user_roles.get(user_id)
        if not role:
            return set()
        return self._roles.get(role, set())

    def revoke_role(self, user_id: str) -> bool:
        if user_id in self._user_roles:
            del self._user_roles[user_id]
            return True
        return False

    def audit_log(self, user_id: str | None = None, n: int = 50) -> list[AuditEntry]:
        entries = self._audit
        if user_id:
            entries = [e for e in entries if e.user_id == user_id]
        return entries[-n:]

    def denied_actions(self) -> list[AuditEntry]:
        return [e for e in self._audit if not e.allowed]

    def summary(self) -> dict[str, Any]:
        return {
            "roles": len(self._roles),
            "users": len(self._user_roles),
            "audit_entries": len(self._audit),
            "denied_count": len(self.denied_actions()),
        }
