"""감사 로그 — 인증/접근 이벤트 기록 (P712)."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("sdacs.audit")


def log_auth_event(
    event: str,
    user: str,
    resource: Optional[str] = None,
    success: bool = True,
    detail: Optional[str] = None,
) -> None:
    """구조화된 감사 이벤트를 JSON 로그로 기록."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "user": user,
        "resource": resource,
        "success": success,
        "detail": detail,
    }
    if success:
        logger.info(json.dumps(record))
    else:
        logger.warning(json.dumps(record))
