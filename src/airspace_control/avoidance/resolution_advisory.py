"""어드바이저리 생명주기 관리"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import uuid


def new_advisory_id() -> str:
    return f"ADV-{uuid.uuid4().hex[:8].upper()}"
