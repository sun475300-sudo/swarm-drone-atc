"""P745: 음성·자연어 → ATC 명령 변환 (Whisper + Claude/GPT).

조종사·관제사 음성 명령을 SDACS AirspaceController가 실행 가능한 구조화 명령으로 변환.

Pipeline:
    음성 (mic / WAV)
      ↓ Whisper STT
    자연어 (한국어/영어)
      ↓ Claude/GPT function calling
    구조화 명령 (JSON)
      ↓ 검증
    AirspaceController.execute()

Example:
    "DR-001 RTL"
      → {"action": "RTL", "drone_id": "DR-001"}
    "Hold all drones at 100 meters"
      → {"action": "HOLD", "target": "all", "altitude_m": 100}
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VoiceCommand:
    """음성→텍스트→구조화 결과."""

    raw_audio_path: str | None
    transcript: str
    structured: dict[str, Any]
    confidence: float
    language: str


SYSTEM_PROMPT = """You are SDACS ATC voice assistant. Convert pilot/controller utterances
into structured drone control commands. Output ONLY valid JSON matching this schema:

{
  "action": "RTL" | "HOLD" | "EVADE" | "LAND" | "LAUNCH" | "ADVISORY",
  "target": "all" | "<drone_id>" | ["<id1>", "<id2>", ...],
  "altitude_m": <number>,           // optional
  "duration_s": <number>,           // optional
  "heading_deg": <number>,          // optional
  "reason": "<short text>"
}

Reject unsafe or ambiguous commands by returning {"action": "REJECT", "reason": "..."}.
"""


def _extract_text_content(content: list[Any]) -> str:
    """Anthropic 응답 블록 중 텍스트 블록만 안전하게 결합한다."""
    return "\n".join(
        text
        for block in content
        if isinstance((text := getattr(block, "text", None)), str)
    )


def transcribe_audio(audio_path: str, language: str = "ko") -> tuple[str, float]:
    """Whisper STT — 음성 파일을 텍스트로 변환."""
    try:
        import whisper  # type: ignore[import-not-found]
    except ImportError as e:
        raise RuntimeError("openai-whisper 필요: pip install openai-whisper") from e

    model = whisper.load_model("small")  # 244MB
    result = model.transcribe(audio_path, language=language)
    return result["text"].strip(), 1.0  # confidence는 word-level segments에서 추출 가능


def parse_command_claude(transcript: str, api_key: str) -> dict[str, Any]:
    """Claude로 자연어→JSON 변환."""
    try:
        import anthropic  # type: ignore[import-not-found]
    except ImportError as e:
        raise RuntimeError("anthropic 필요: pip install anthropic") from e

    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": transcript}],
    )
    text = _extract_text_content(msg.content)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"action": "REJECT", "reason": "Invalid JSON from LLM"}


def validate_command(cmd: dict[str, Any]) -> tuple[bool, str]:
    """명령 검증 — 안전 가드."""
    if cmd.get("action") == "REJECT":
        return False, cmd.get("reason", "rejected")
    if cmd.get("action") not in {"RTL", "HOLD", "EVADE", "LAND", "LAUNCH", "ADVISORY"}:
        return False, "unknown action"
    if cmd.get("altitude_m") and not (0 <= cmd["altitude_m"] <= 150):
        return False, "altitude out of range [0, 150]"
    if cmd.get("action") == "LAUNCH":
        return False, "LAUNCH requires explicit operator confirmation"
    return True, "ok"


def voice_to_command(audio_path: str, anthropic_api_key: str, language: str = "ko") -> VoiceCommand:
    """End-to-end: 음성 → 구조화 명령 + 검증."""
    transcript, conf = transcribe_audio(audio_path, language)
    structured = parse_command_claude(transcript, anthropic_api_key)
    ok, msg = validate_command(structured)
    if not ok:
        structured = {"action": "REJECT", "reason": msg}
    return VoiceCommand(
        raw_audio_path=audio_path,
        transcript=transcript,
        structured=structured,
        confidence=conf,
        language=language,
    )
