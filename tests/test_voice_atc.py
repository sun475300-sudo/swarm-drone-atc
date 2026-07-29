"""ATC 음성 명령 응답 정규화 단위 테스트."""
from __future__ import annotations

from src.llm.voice_atc import _extract_text_content


class _TextBlock:
    """텍스트 응답 블록을 흉내 낸다."""

    text = '{"action":"RTL"}'


class _ToolBlock:
    """텍스트 속성이 없는 응답 블록을 흉내 낸다."""


def test_extract_text_content_ignores_non_text_blocks() -> None:
    """도구/추론 블록이 앞에 와도 실제 텍스트 명령만 반환한다."""
    assert _extract_text_content([_ToolBlock(), _TextBlock()]) == '{"action":"RTL"}'
