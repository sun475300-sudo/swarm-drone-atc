"""
Phase 455: Configuration Management System
"""

import numpy as np
from typing import Dict, Any, List
import json
import time


class ConfigurationManagementSystem:
    def __init__(self):
        self.configs: Dict[str, Dict] = {}
        self.version_history: Dict[str, List] = {}

    def set_config(self, key: str, value: Any):
        if key not in self.configs:
            self.version_history[key] = []

        self.version_history[key].append(
            {"value": self.configs.get(key), "timestamp": time.time()}
        )

        self.configs[key] = value

    def get_config(self, key: str, default: Any = None) -> Any:
        return self.configs.get(key, default)

    def get_all_configs(self) -> Dict:
        return self.configs.copy()

    def rollback(self, key: str, version: int = -1) -> bool:
        if key not in self.version_history or not self.version_history[key]:
            return False

        history = self.version_history[key]
        if abs(version) > len(history):
            return False

        self.configs[key] = history[version]["value"]
        return True
