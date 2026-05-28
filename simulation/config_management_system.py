"""
Phase 455: Configuration Management System
"""

import time
from typing import Any


class ConfigurationManagementSystem:
    """``ConfigurationManagementSystem`` 역할을 담당한다."""
    def __init__(self):
        """인스턴스를 초기화한다."""
        self.configs: dict[str, dict] = {}
        self.version_history: dict[str, list] = {}

    def set_config(self, key: str, value: Any):
        """`config` 상태를 갱신한다."""
        if key not in self.configs:
            self.version_history[key] = []

        self.version_history[key].append(
            {"value": self.configs.get(key), "timestamp": time.time()}
        )

        self.configs[key] = value

    def get_config(self, key: str, default: Any = None) -> Any:
        """`config` 정보를 조회한다."""
        return self.configs.get(key, default)

    def get_all_configs(self) -> dict:
        """`all configs` 정보를 조회한다."""
        return self.configs.copy()

    def rollback(self, key: str, version: int = -1) -> bool:
        """``rollback`` 동작을 수행한다."""
        if key not in self.version_history or not self.version_history[key]:
            return False

        history = self.version_history[key]
        if abs(version) > len(history):
            return False

        self.configs[key] = history[version]["value"]
        return True
