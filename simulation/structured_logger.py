"""구조화 로깅 모듈 — JSON 포맷 로거를 제공한다."""

import json
import logging
from datetime import datetime, timezone


class _JsonFormatter(logging.Formatter):
    """로그 레코드를 JSON 문자열로 변환하는 포매터."""

    def format(self, record: logging.LogRecord) -> str:
        # 기본 필드 구성
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }
        # extra 필드 병합 (예약 속성 제외)
        reserved = frozenset(vars(logging.LogRecord("", 0, "", 0, "", (), None)))
        extras = {
            k: v for k, v in vars(record).items()
            if k not in reserved and k != "message"
        }
        if extras:
            entry["extra"] = extras
        return json.dumps(entry, ensure_ascii=False, default=str)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """JSON 포맷 로거를 생성하여 반환한다.

    Args:
        name: 로거 이름 (모듈명 권장).
        level: 로깅 레벨 (기본 INFO).

    Returns:
        설정된 logging.Logger 인스턴스.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(_JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger
