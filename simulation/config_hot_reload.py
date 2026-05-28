"""
Config hot reload infrastructure.
================================
Provides file-based config reload with versioning and rollback support.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ConfigSnapshot:
    """``ConfigSnapshot`` 관련 기능을 제공한다."""
    version: int
    loaded_at: float
    checksum: str
    data: dict[str, Any]


class ConfigHotReload:
    """``ConfigHotReload`` 관련 기능을 제공한다."""
    def __init__(self, path: str) -> None:
        """인스턴스를 초기화한다."""
        self.path = Path(path)
        self._current: ConfigSnapshot | None = None
        self._history: list[ConfigSnapshot] = []
        self._reloads = 0

    def _now(self) -> float:
        return time.monotonic()

    def _read_text(self) -> str:
        return self.path.read_text(encoding="utf-8")

    def _checksum(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _parse(self, content: str) -> dict[str, Any]:
        suffix = self.path.suffix.lower()
        if suffix in {".yaml", ".yml"}:
            return yaml.safe_load(content) or {}
        if suffix == ".json":
            return json.loads(content)
        raise ValueError(f"Unsupported config extension: {suffix}")

    def load(self) -> dict[str, Any]:
        """`대상` 정보를 조회한다."""
        content = self._read_text()
        checksum = self._checksum(content)
        data = self._parse(content)

        version = 1 if self._current is None else self._current.version + 1
        snapshot = ConfigSnapshot(version=version, loaded_at=self._now(), checksum=checksum, data=data)
        if self._current is not None:
            self._history.append(self._current)
        self._current = snapshot
        self._reloads += 1
        return dict(data)

    def reload_if_changed(self) -> bool:
        """``reload_if_changed`` 동작을 수행한다."""
        if not self.path.exists():
            return False
        content = self._read_text()
        checksum = self._checksum(content)
        if self._current is not None and self._current.checksum == checksum:
            return False
        self.load()
        return True

    def rollback(self) -> bool:
        """``rollback`` 동작을 수행한다."""
        if not self._history:
            return False
        self._current = self._history.pop()
        return True

    def current(self) -> dict[str, Any]:
        """``current`` 동작을 수행한다."""
        if self._current is None:
            return {}
        return dict(self._current.data)

    def summary(self) -> dict[str, Any]:
        """현재 상태 요약을 반환한다."""
        return {
            "path": str(self.path),
            "version": self._current.version if self._current else 0,
            "reloads": self._reloads,
            "history": len(self._history),
        }
