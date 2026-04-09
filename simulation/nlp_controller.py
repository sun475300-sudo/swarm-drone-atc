"""
자연어 관제 인터페이스
====================
텍스트 명령 파싱 + 의도 분류 + 관제 실행.

사용법:
    nlp = NLPController()
    result = nlp.parse_command("드론 d1을 (500, 300)으로 이동시켜")
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import re


@dataclass
class ParsedCommand:
    intent: str  # MOVE, LAND, RETURN, STATUS, EMERGENCY, UNKNOWN
    target: str
    params: dict[str, Any]
    confidence: float
    raw_text: str


INTENT_PATTERNS = [
    (r"이동|move|goto|go to", "MOVE"),
    (r"착륙|land|landing", "LAND"),
    (r"귀환|return|rtl|복귀", "RETURN"),
    (r"상태|status|info|정보", "STATUS"),
    (r"비상|emergency|긴급", "EMERGENCY"),
    (r"정지|stop|hold|대기", "HOLD"),
]


class NLPController:
    def __init__(self) -> None:
        self._history: list[ParsedCommand] = []

    def parse_command(self, text: str) -> ParsedCommand:
        text_lower = text.lower()

        # 의도 분류
        intent = "UNKNOWN"
        confidence = 0.3
        for pattern, intent_name in INTENT_PATTERNS:
            if re.search(pattern, text_lower):
                intent = intent_name
                confidence = 0.9
                break

        # 드론 ID 추출
        target = ""
        drone_match = re.search(r"(d\d+|drone\s*\d+|드론\s*\d+)", text_lower)
        if drone_match:
            target = re.sub(r"[^d\d]", "", drone_match.group()).strip()
            if not target.startswith("d"):
                target = "d" + re.search(r"\d+", target).group()

        # 좌표 추출
        params: dict[str, Any] = {}
        coord_match = re.search(r"\((\d+)[,\s]+(\d+)\)", text)
        if coord_match:
            params["destination"] = (int(coord_match.group(1)), int(coord_match.group(2)))

        cmd = ParsedCommand(
            intent=intent, target=target,
            params=params, confidence=confidence, raw_text=text,
        )
        self._history.append(cmd)
        return cmd

    def batch_parse(self, texts: list[str]) -> list[ParsedCommand]:
        return [self.parse_command(t) for t in texts]

    def intent_stats(self) -> dict[str, int]:
        stats: dict[str, int] = {}
        for cmd in self._history:
            stats[cmd.intent] = stats.get(cmd.intent, 0) + 1
        return stats

    def summary(self) -> dict[str, Any]:
        return {
            "commands_parsed": len(self._history),
            "intent_distribution": self.intent_stats(),
            "avg_confidence": round(
                sum(c.confidence for c in self._history) / max(len(self._history), 1), 2
            ),
        }
