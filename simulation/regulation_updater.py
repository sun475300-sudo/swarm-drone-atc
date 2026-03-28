"""
규제 동적 업데이트
=================
외부 규제 변경 반영 + 버전 관리 + 자동 적용.

사용법:
    ru = RegulationUpdater()
    ru.add_regulation("MAX_ALT", value=120, unit="m")
    ru.update_regulation("MAX_ALT", value=150, reason="규제 완화")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Regulation:
    """규제 항목"""
    name: str
    value: Any
    unit: str = ""
    version: int = 1
    description: str = ""
    mandatory: bool = True


@dataclass
class RegulationChange:
    """규제 변경 이력"""
    name: str
    old_value: Any
    new_value: Any
    version: int
    reason: str = ""


class RegulationUpdater:
    """규제 동적 업데이트."""

    def __init__(self) -> None:
        self._regulations: dict[str, Regulation] = {}
        self._changes: list[RegulationChange] = []
        self._callbacks: dict[str, list] = {}

    def add_regulation(
        self, name: str, value: Any, unit: str = "",
        description: str = "", mandatory: bool = True,
    ) -> None:
        self._regulations[name] = Regulation(
            name=name, value=value, unit=unit,
            description=description, mandatory=mandatory,
        )

    def update_regulation(self, name: str, value: Any, reason: str = "") -> bool:
        reg = self._regulations.get(name)
        if not reg:
            return False

        old_value = reg.value
        reg.version += 1
        reg.value = value

        change = RegulationChange(
            name=name, old_value=old_value,
            new_value=value, version=reg.version, reason=reason,
        )
        self._changes.append(change)

        # 콜백 실행
        for cb in self._callbacks.get(name, []):
            try:
                cb(name, value)
            except Exception:
                pass

        return True

    def get_value(self, name: str) -> Any:
        reg = self._regulations.get(name)
        return reg.value if reg else None

    def get_version(self, name: str) -> int:
        reg = self._regulations.get(name)
        return reg.version if reg else 0

    def on_change(self, name: str, callback) -> None:
        if name not in self._callbacks:
            self._callbacks[name] = []
        self._callbacks[name].append(callback)

    def check_compliance(self, name: str, actual_value: float) -> bool:
        """규제 준수 확인"""
        reg = self._regulations.get(name)
        if not reg:
            return True
        try:
            return actual_value <= float(reg.value)
        except (TypeError, ValueError):
            return True

    def mandatory_regulations(self) -> list[Regulation]:
        return [r for r in self._regulations.values() if r.mandatory]

    def change_history(self, name: str | None = None, n: int = 20) -> list[RegulationChange]:
        changes = self._changes
        if name:
            changes = [c for c in changes if c.name == name]
        return changes[-n:]

    def summary(self) -> dict[str, Any]:
        return {
            "total_regulations": len(self._regulations),
            "mandatory": len(self.mandatory_regulations()),
            "total_changes": len(self._changes),
        }
