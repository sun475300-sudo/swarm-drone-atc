"""GENESIS Phase 363 -- LLM ATC 명령 프로덕션 파이프라인.

조종사/관제사 자연어 ATC 명령을 결정론적으로 파싱·검증·확인하는 프로덕션 계층.
실제 LLM 호출은 src/llm/voice_atc.py 가 담당하며, 이 모듈은 그 하류의
구조화·안전검증·2단계 확인 파이프라인을 제공합니다.

CLI:
    python simulation/llm_atc_production.py --parse "drone-5 climb to 120m"
    python simulation/llm_atc_production.py --pipeline "drone-12 turn heading 270"
    python simulation/llm_atc_production.py --pipeline "drone-3 descend 30m" --validate
    python simulation/llm_atc_production.py --pipeline "drone-3 descend 30m" --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CommandType(Enum):
    """ATC 명령 유형."""

    CLIMB = "CLIMB"
    DESCEND = "DESCEND"
    TURN = "TURN"
    HOLD = "HOLD"
    EVADE = "EVADE"
    EXPEDITE = "EXPEDITE"
    SQUAWK = "SQUAWK"


class RiskLevel(Enum):
    """안전 검사 위험 수준."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# Frozen dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ATCCommand:
    """파싱된 ATC 명령."""

    command_type: CommandType
    target_id: str
    parameters: MappingProxyType
    priority: int
    timestamp_s: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "command_type": self.command_type.value,
            "target_id": self.target_id,
            "parameters": dict(self.parameters),
            "priority": self.priority,
            "timestamp_s": self.timestamp_s,
        }


@dataclass(frozen=True)
class CommandConfirmation:
    """2단계 확인 결과."""

    command: ATCCommand
    pilot_readback: str
    confirmed: bool
    confirmation_time_s: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "command": self.command.as_dict(),
            "pilot_readback": self.pilot_readback,
            "confirmed": self.confirmed,
            "confirmation_time_s": self.confirmation_time_s,
        }


@dataclass(frozen=True)
class SafetyCheck:
    """안전 검사 결과."""

    command: ATCCommand
    is_safe: bool
    violations: tuple[str, ...]
    risk_level: RiskLevel

    def as_dict(self) -> dict[str, Any]:
        return {
            "command": self.command.as_dict(),
            "is_safe": self.is_safe,
            "violations": list(self.violations),
            "risk_level": self.risk_level.value,
        }


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_AIRSPACE_CEILING_M: float = 150.0
DEFAULT_MIN_ALTITUDE_M: float = 10.0
DEFAULT_PRIORITY: int = 5
DEFAULT_TIMESTAMP_S: float = 0.0
MIN_SEPARATION_M: float = 30.0

# Regex patterns for ATC phraseology
_TARGET_PATTERN = r"(?:drone[- ]?(\w+))"
_CLIMB_PATTERN = re.compile(
    rf"{_TARGET_PATTERN}\s+climb\s+(?:to\s+)?(\d+(?:\.\d+)?)\s*m",
    re.IGNORECASE,
)
_DESCEND_PATTERN = re.compile(
    rf"{_TARGET_PATTERN}\s+descend\s+(?:to\s+)?(\d+(?:\.\d+)?)\s*m",
    re.IGNORECASE,
)
_TURN_PATTERN = re.compile(
    rf"{_TARGET_PATTERN}\s+turn\s+(?:heading\s+)?(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_HOLD_PATTERN = re.compile(
    rf"{_TARGET_PATTERN}\s+hold(?:\s+position)?",
    re.IGNORECASE,
)
_EVADE_PATTERN = re.compile(
    rf"{_TARGET_PATTERN}\s+evade(?:\s+(\w+))?",
    re.IGNORECASE,
)
_EXPEDITE_PATTERN = re.compile(
    rf"{_TARGET_PATTERN}\s+expedite\s+(\w+)",
    re.IGNORECASE,
)
_SQUAWK_PATTERN = re.compile(
    rf"{_TARGET_PATTERN}\s+squawk\s+(\d{{4}})",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# ATCCommandParser
# ---------------------------------------------------------------------------

class ATCCommandParser:
    """결정론적 정규표현식 기반 ATC 명령 파서."""

    def parse(
        self,
        text: str,
        *,
        priority: int = DEFAULT_PRIORITY,
        timestamp_s: float = DEFAULT_TIMESTAMP_S,
    ) -> ATCCommand | None:
        """자연어 ATC 명령을 ATCCommand로 파싱. 인식 불가 시 None."""
        text = text.strip()
        if not text:
            return None

        result = self._try_climb(text)
        if result is None:
            result = self._try_descend(text)
        if result is None:
            result = self._try_turn(text)
        if result is None:
            result = self._try_hold(text)
        if result is None:
            result = self._try_evade(text)
        if result is None:
            result = self._try_expedite(text)
        if result is None:
            result = self._try_squawk(text)

        if result is None:
            return None

        cmd_type, target, params = result
        return ATCCommand(
            command_type=cmd_type,
            target_id=target,
            parameters=MappingProxyType(params),
            priority=priority,
            timestamp_s=timestamp_s,
        )

    # -- individual matchers -------------------------------------------------

    def _try_climb(self, text: str) -> tuple[CommandType, str, dict[str, Any]] | None:
        m = _CLIMB_PATTERN.search(text)
        if m is None:
            return None
        return CommandType.CLIMB, f"drone-{m.group(1)}", {"altitude_m": float(m.group(2))}

    def _try_descend(self, text: str) -> tuple[CommandType, str, dict[str, Any]] | None:
        m = _DESCEND_PATTERN.search(text)
        if m is None:
            return None
        return CommandType.DESCEND, f"drone-{m.group(1)}", {"altitude_m": float(m.group(2))}

    def _try_turn(self, text: str) -> tuple[CommandType, str, dict[str, Any]] | None:
        m = _TURN_PATTERN.search(text)
        if m is None:
            return None
        return CommandType.TURN, f"drone-{m.group(1)}", {"heading_deg": float(m.group(2))}

    def _try_hold(self, text: str) -> tuple[CommandType, str, dict[str, Any]] | None:
        m = _HOLD_PATTERN.search(text)
        if m is None:
            return None
        return CommandType.HOLD, f"drone-{m.group(1)}", {}

    def _try_evade(self, text: str) -> tuple[CommandType, str, dict[str, Any]] | None:
        m = _EVADE_PATTERN.search(text)
        if m is None:
            return None
        direction = m.group(2) or "auto"
        return CommandType.EVADE, f"drone-{m.group(1)}", {"direction": direction}

    def _try_expedite(self, text: str) -> tuple[CommandType, str, dict[str, Any]] | None:
        m = _EXPEDITE_PATTERN.search(text)
        if m is None:
            return None
        return CommandType.EXPEDITE, f"drone-{m.group(1)}", {"action": m.group(2).lower()}

    def _try_squawk(self, text: str) -> tuple[CommandType, str, dict[str, Any]] | None:
        m = _SQUAWK_PATTERN.search(text)
        if m is None:
            return None
        return CommandType.SQUAWK, f"drone-{m.group(1)}", {"code": m.group(2)}


# ---------------------------------------------------------------------------
# ATCCommandValidator
# ---------------------------------------------------------------------------

class ATCCommandValidator:
    """ATC 명령 안전 검증기."""

    def validate(
        self,
        cmd: ATCCommand,
        airspace_ceiling_m: float = DEFAULT_AIRSPACE_CEILING_M,
        min_altitude_m: float = DEFAULT_MIN_ALTITUDE_M,
    ) -> SafetyCheck:
        """명령의 안전성 검증. 위반 사항 목록과 위험 수준 반환."""
        violations: list[str] = []

        self._check_altitude_bounds(cmd, airspace_ceiling_m, min_altitude_m, violations)
        self._check_heading_range(cmd, violations)
        self._check_squawk_code(cmd, violations)
        self._check_target_id(cmd, violations)

        risk = self._assess_risk(cmd, violations)
        return SafetyCheck(
            command=cmd,
            is_safe=len(violations) == 0,
            violations=tuple(violations),
            risk_level=risk,
        )

    def _check_altitude_bounds(
        self,
        cmd: ATCCommand,
        ceiling: float,
        floor: float,
        violations: list[str],
    ) -> None:
        alt = cmd.parameters.get("altitude_m")
        if alt is None:
            return
        if alt > ceiling:
            violations.append(f"altitude {alt}m exceeds ceiling {ceiling}m")
        if alt < floor:
            violations.append(f"altitude {alt}m below minimum {floor}m")

    def _check_heading_range(self, cmd: ATCCommand, violations: list[str]) -> None:
        heading = cmd.parameters.get("heading_deg")
        if heading is None:
            return
        if not (0.0 <= heading < 360.0):
            violations.append(f"heading {heading} outside [0, 360) range")

    def _check_squawk_code(self, cmd: ATCCommand, violations: list[str]) -> None:
        code = cmd.parameters.get("code")
        if code is None:
            return
        if not re.fullmatch(r"\d{4}", str(code)):
            violations.append(f"invalid squawk code: {code}")
        elif any(int(d) > 7 for d in str(code)):
            violations.append(f"squawk digits must be 0-7 (octal): {code}")

    def _check_target_id(self, cmd: ATCCommand, violations: list[str]) -> None:
        if not cmd.target_id or not cmd.target_id.strip():
            violations.append("missing target drone identifier")

    def _assess_risk(self, cmd: ATCCommand, violations: list[str]) -> RiskLevel:
        if not violations:
            if cmd.command_type == CommandType.EVADE:
                return RiskLevel.MEDIUM
            return RiskLevel.LOW
        critical_keywords = ("ceiling", "below minimum")
        if any(kw in v for v in violations for kw in critical_keywords):
            return RiskLevel.CRITICAL
        if len(violations) >= 2:
            return RiskLevel.HIGH
        return RiskLevel.MEDIUM


# ---------------------------------------------------------------------------
# TwoStepConfirmer
# ---------------------------------------------------------------------------

class TwoStepConfirmer:
    """2단계 확인 (readback challenge / confirmation)."""

    def initiate(self, cmd: ATCCommand) -> str:
        """명령에 대한 readback challenge 텍스트 생성."""
        parts = [f"{cmd.target_id}"]
        ct = cmd.command_type

        if ct == CommandType.CLIMB:
            parts.append(f"climb to {cmd.parameters.get('altitude_m')}m")
        elif ct == CommandType.DESCEND:
            parts.append(f"descend to {cmd.parameters.get('altitude_m')}m")
        elif ct == CommandType.TURN:
            parts.append(f"turn heading {cmd.parameters.get('heading_deg')}")
        elif ct == CommandType.HOLD:
            parts.append("hold position")
        elif ct == CommandType.EVADE:
            parts.append(f"evade {cmd.parameters.get('direction', 'auto')}")
        elif ct == CommandType.EXPEDITE:
            parts.append(f"expedite {cmd.parameters.get('action', 'unknown')}")
        elif ct == CommandType.SQUAWK:
            parts.append(f"squawk {cmd.parameters.get('code')}")

        return ", ".join(parts) + ", readback"

    def confirm(
        self,
        cmd: ATCCommand,
        readback: str,
        *,
        confirmation_time_s: float = 0.0,
    ) -> CommandConfirmation:
        """readback 이 challenge 와 일치하는지 검증."""
        challenge = self.initiate(cmd)
        normalized_challenge = self._normalize(challenge)
        normalized_readback = self._normalize(readback)
        confirmed = normalized_challenge == normalized_readback
        return CommandConfirmation(
            command=cmd,
            pilot_readback=readback,
            confirmed=confirmed,
            confirmation_time_s=confirmation_time_s,
        )

    def _normalize(self, text: str) -> str:
        """비교용 정규화: 소문자, 공백 통합, readback 접미사 제거."""
        t = text.lower().strip()
        t = re.sub(r",?\s*readback\s*$", "", t)
        t = re.sub(r"\s+", " ", t)
        t = t.rstrip(", ")
        return t


# ---------------------------------------------------------------------------
# ProductionATCPipeline
# ---------------------------------------------------------------------------

class ProductionATCPipeline:
    """파싱 → 검증 → readback challenge 통합 파이프라인."""

    def __init__(
        self,
        *,
        airspace_ceiling_m: float = DEFAULT_AIRSPACE_CEILING_M,
        min_altitude_m: float = DEFAULT_MIN_ALTITUDE_M,
    ) -> None:
        self._parser = ATCCommandParser()
        self._validator = ATCCommandValidator()
        self._confirmer = TwoStepConfirmer()
        self._ceiling = airspace_ceiling_m
        self._floor = min_altitude_m

    def process(
        self,
        text: str,
        *,
        priority: int = DEFAULT_PRIORITY,
        timestamp_s: float = DEFAULT_TIMESTAMP_S,
    ) -> tuple[ATCCommand | None, SafetyCheck | None, str]:
        """파싱 → 검증 → readback challenge.

        Returns:
            (command, safety_check, message) 튜플.
            파싱 실패 시 (None, None, error_message).
            검증 실패 시 safety_check.is_safe == False.
        """
        cmd = self._parser.parse(text, priority=priority, timestamp_s=timestamp_s)
        if cmd is None:
            return None, None, f"unrecognized command: {text!r}"

        check = self._validator.validate(cmd, self._ceiling, self._floor)
        if not check.is_safe:
            msg = f"unsafe: {'; '.join(check.violations)}"
            return cmd, check, msg

        challenge = self._confirmer.initiate(cmd)
        return cmd, check, challenge


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="GENESIS Phase 363 -- LLM ATC 명령 프로덕션 파이프라인",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--parse", type=str, metavar="TEXT", help="ATC 명령 파싱")
    group.add_argument("--pipeline", type=str, metavar="TEXT", help="전체 파이프라인 실행")
    parser.add_argument("--validate", action="store_true", help="검증 결과 포함")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    if args.parse:
        _handle_parse(args.parse, args.json)
    elif args.pipeline:
        _handle_pipeline(args.pipeline, args.validate, args.json)
    else:
        parser.print_help()
        sys.exit(1)


def _handle_parse(text: str, as_json: bool) -> None:
    cmd = ATCCommandParser().parse(text)
    if cmd is None:
        print(f"인식 불가: {text!r}", file=sys.stderr)
        sys.exit(1)
    if as_json:
        print(json.dumps(cmd.as_dict(), ensure_ascii=False, indent=2))
    else:
        _print_command(cmd)


def _handle_pipeline(text: str, validate: bool, as_json: bool) -> None:
    pipeline = ProductionATCPipeline()
    cmd, check, message = pipeline.process(text)

    if as_json:
        result: dict[str, Any] = {
            "command": cmd.as_dict() if cmd else None,
            "safety_check": check.as_dict() if check else None,
            "message": message,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if cmd is None:
        print(f"파싱 실패: {message}", file=sys.stderr)
        sys.exit(1)

    _print_command(cmd)
    if validate and check:
        _print_safety(check)
    print(f"  메시지: {message}")


def _print_command(cmd: ATCCommand) -> None:
    print(f"  명령: {cmd.command_type.value}")
    print(f"  대상: {cmd.target_id}")
    print(f"  매개변수: {dict(cmd.parameters)}")
    print(f"  우선순위: {cmd.priority}")


def _print_safety(check: SafetyCheck) -> None:
    mark = "안전" if check.is_safe else "위험"
    print(f"  안전: {mark} ({check.risk_level.value})")
    if check.violations:
        for v in check.violations:
            print(f"    위반: {v}")


if __name__ == "__main__":
    _main()
