"""GENESIS Phase 363 -- LLM ATC 프로덕션 파이프라인 테스트.

30+ tests covering:
  - ATCCommandParser: 7가지 명령 유형 파싱
  - ATCCommandValidator: 고도/방위/스쿼크/타겟 검증
  - TwoStepConfirmer: readback challenge 생성 및 확인
  - ProductionATCPipeline: 통합 파이프라인
  - Edge cases: 빈 입력, 극단 고도, 잘못된 형식
  - CLI args: argparse 구성
"""
from __future__ import annotations

import subprocess
import sys
from types import MappingProxyType

import pytest

from simulation.llm_atc_production import (
    DEFAULT_AIRSPACE_CEILING_M,
    DEFAULT_MIN_ALTITUDE_M,
    DEFAULT_PRIORITY,
    DEFAULT_TIMESTAMP_S,
    ATCCommand,
    ATCCommandParser,
    ATCCommandValidator,
    CommandConfirmation,
    CommandType,
    ProductionATCPipeline,
    RiskLevel,
    SafetyCheck,
    TwoStepConfirmer,
)

# ===========================================================================
# Helpers
# ===========================================================================

def _make_cmd(
    cmd_type: CommandType = CommandType.CLIMB,
    target: str = "drone-5",
    params: dict | None = None,
    priority: int = DEFAULT_PRIORITY,
    ts: float = DEFAULT_TIMESTAMP_S,
) -> ATCCommand:
    return ATCCommand(
        command_type=cmd_type,
        target_id=target,
        parameters=MappingProxyType(params or {}),
        priority=priority,
        timestamp_s=ts,
    )


# ===========================================================================
# ATCCommandParser tests
# ===========================================================================

class TestATCCommandParser:
    """ATCCommandParser 파싱 테스트."""

    def setup_method(self) -> None:
        self.parser = ATCCommandParser()

    # -- climb ---------------------------------------------------------------
    def test_parse_climb_basic(self) -> None:
        cmd = self.parser.parse("drone-5 climb to 120m")
        assert cmd is not None
        assert cmd.command_type == CommandType.CLIMB
        assert cmd.target_id == "drone-5"
        assert cmd.parameters["altitude_m"] == 120.0

    def test_parse_climb_without_to(self) -> None:
        cmd = self.parser.parse("drone-3 climb 80m")
        assert cmd is not None
        assert cmd.command_type == CommandType.CLIMB
        assert cmd.parameters["altitude_m"] == 80.0

    def test_parse_climb_decimal(self) -> None:
        cmd = self.parser.parse("drone-7 climb to 55.5m")
        assert cmd is not None
        assert cmd.parameters["altitude_m"] == 55.5

    # -- descend -------------------------------------------------------------
    def test_parse_descend_basic(self) -> None:
        cmd = self.parser.parse("drone-12 descend to 30m")
        assert cmd is not None
        assert cmd.command_type == CommandType.DESCEND
        assert cmd.target_id == "drone-12"
        assert cmd.parameters["altitude_m"] == 30.0

    def test_parse_descend_without_to(self) -> None:
        cmd = self.parser.parse("drone-1 descend 50m")
        assert cmd is not None
        assert cmd.command_type == CommandType.DESCEND

    # -- turn ----------------------------------------------------------------
    def test_parse_turn_heading(self) -> None:
        cmd = self.parser.parse("drone-12 turn heading 270")
        assert cmd is not None
        assert cmd.command_type == CommandType.TURN
        assert cmd.parameters["heading_deg"] == 270.0

    def test_parse_turn_without_heading_keyword(self) -> None:
        cmd = self.parser.parse("drone-4 turn 90")
        assert cmd is not None
        assert cmd.command_type == CommandType.TURN
        assert cmd.parameters["heading_deg"] == 90.0

    # -- hold ----------------------------------------------------------------
    def test_parse_hold_basic(self) -> None:
        cmd = self.parser.parse("drone-9 hold position")
        assert cmd is not None
        assert cmd.command_type == CommandType.HOLD
        assert cmd.target_id == "drone-9"
        assert dict(cmd.parameters) == {}

    def test_parse_hold_without_position(self) -> None:
        cmd = self.parser.parse("drone-2 hold")
        assert cmd is not None
        assert cmd.command_type == CommandType.HOLD

    # -- evade ---------------------------------------------------------------
    def test_parse_evade_with_direction(self) -> None:
        cmd = self.parser.parse("drone-8 evade left")
        assert cmd is not None
        assert cmd.command_type == CommandType.EVADE
        assert cmd.parameters["direction"] == "left"

    def test_parse_evade_auto(self) -> None:
        cmd = self.parser.parse("drone-6 evade")
        assert cmd is not None
        assert cmd.command_type == CommandType.EVADE
        assert cmd.parameters["direction"] == "auto"

    # -- expedite ------------------------------------------------------------
    def test_parse_expedite(self) -> None:
        cmd = self.parser.parse("drone-11 expedite climb")
        assert cmd is not None
        assert cmd.command_type == CommandType.EXPEDITE
        assert cmd.parameters["action"] == "climb"

    # -- squawk --------------------------------------------------------------
    def test_parse_squawk(self) -> None:
        cmd = self.parser.parse("drone-3 squawk 1200")
        assert cmd is not None
        assert cmd.command_type == CommandType.SQUAWK
        assert cmd.parameters["code"] == "1200"

    # -- edge cases ----------------------------------------------------------
    def test_parse_empty_string(self) -> None:
        assert self.parser.parse("") is None

    def test_parse_whitespace_only(self) -> None:
        assert self.parser.parse("   ") is None

    def test_parse_unrecognized(self) -> None:
        assert self.parser.parse("hello world") is None

    def test_parse_case_insensitive(self) -> None:
        cmd = self.parser.parse("DRONE-5 CLIMB TO 100M")
        assert cmd is not None
        assert cmd.command_type == CommandType.CLIMB

    def test_parse_custom_priority(self) -> None:
        cmd = self.parser.parse("drone-1 hold", priority=10)
        assert cmd is not None
        assert cmd.priority == 10

    def test_parse_custom_timestamp(self) -> None:
        cmd = self.parser.parse("drone-1 hold", timestamp_s=42.5)
        assert cmd is not None
        assert cmd.timestamp_s == 42.5

    def test_parse_drone_without_hyphen(self) -> None:
        cmd = self.parser.parse("drone5 climb to 100m")
        assert cmd is not None
        assert cmd.target_id == "drone-5"

    def test_parse_drone_with_space(self) -> None:
        cmd = self.parser.parse("drone 5 climb to 100m")
        assert cmd is not None
        assert cmd.target_id == "drone-5"


# ===========================================================================
# ATCCommandValidator tests
# ===========================================================================

class TestATCCommandValidator:
    """ATCCommandValidator 검증 테스트."""

    def setup_method(self) -> None:
        self.validator = ATCCommandValidator()

    def test_valid_climb(self) -> None:
        cmd = _make_cmd(CommandType.CLIMB, params={"altitude_m": 100.0})
        check = self.validator.validate(cmd)
        assert check.is_safe is True
        assert check.violations == ()
        assert check.risk_level == RiskLevel.LOW

    def test_altitude_exceeds_ceiling(self) -> None:
        cmd = _make_cmd(CommandType.CLIMB, params={"altitude_m": 200.0})
        check = self.validator.validate(cmd)
        assert check.is_safe is False
        assert any("ceiling" in v for v in check.violations)
        assert check.risk_level == RiskLevel.CRITICAL

    def test_altitude_below_minimum(self) -> None:
        cmd = _make_cmd(CommandType.DESCEND, params={"altitude_m": 5.0})
        check = self.validator.validate(cmd)
        assert check.is_safe is False
        assert any("below minimum" in v for v in check.violations)
        assert check.risk_level == RiskLevel.CRITICAL

    def test_altitude_at_ceiling_boundary(self) -> None:
        cmd = _make_cmd(CommandType.CLIMB, params={"altitude_m": DEFAULT_AIRSPACE_CEILING_M})
        check = self.validator.validate(cmd)
        assert check.is_safe is True

    def test_altitude_at_floor_boundary(self) -> None:
        cmd = _make_cmd(CommandType.DESCEND, params={"altitude_m": DEFAULT_MIN_ALTITUDE_M})
        check = self.validator.validate(cmd)
        assert check.is_safe is True

    def test_custom_ceiling(self) -> None:
        cmd = _make_cmd(CommandType.CLIMB, params={"altitude_m": 120.0})
        check = self.validator.validate(cmd, airspace_ceiling_m=100.0)
        assert check.is_safe is False

    def test_heading_valid(self) -> None:
        cmd = _make_cmd(CommandType.TURN, params={"heading_deg": 270.0})
        check = self.validator.validate(cmd)
        assert check.is_safe is True

    def test_heading_out_of_range(self) -> None:
        cmd = _make_cmd(CommandType.TURN, params={"heading_deg": 400.0})
        check = self.validator.validate(cmd)
        assert check.is_safe is False
        assert any("heading" in v for v in check.violations)

    def test_heading_negative(self) -> None:
        cmd = _make_cmd(CommandType.TURN, params={"heading_deg": -10.0})
        check = self.validator.validate(cmd)
        assert check.is_safe is False

    def test_squawk_invalid_octal(self) -> None:
        cmd = _make_cmd(CommandType.SQUAWK, params={"code": "8888"})
        check = self.validator.validate(cmd)
        assert check.is_safe is False
        assert any("octal" in v for v in check.violations)

    def test_squawk_valid(self) -> None:
        cmd = _make_cmd(CommandType.SQUAWK, params={"code": "1200"})
        check = self.validator.validate(cmd)
        assert check.is_safe is True

    def test_evade_inherent_medium_risk(self) -> None:
        cmd = _make_cmd(CommandType.EVADE, params={"direction": "left"})
        check = self.validator.validate(cmd)
        assert check.is_safe is True
        assert check.risk_level == RiskLevel.MEDIUM

    def test_hold_low_risk(self) -> None:
        cmd = _make_cmd(CommandType.HOLD)
        check = self.validator.validate(cmd)
        assert check.is_safe is True
        assert check.risk_level == RiskLevel.LOW

    def test_multiple_violations_high_risk(self) -> None:
        cmd = _make_cmd(CommandType.TURN, params={"heading_deg": 400.0, "altitude_m": 200.0})
        check = self.validator.validate(cmd)
        assert check.is_safe is False
        assert len(check.violations) >= 2


# ===========================================================================
# TwoStepConfirmer tests
# ===========================================================================

class TestTwoStepConfirmer:
    """TwoStepConfirmer 2단계 확인 테스트."""

    def setup_method(self) -> None:
        self.confirmer = TwoStepConfirmer()

    def test_initiate_climb(self) -> None:
        cmd = _make_cmd(CommandType.CLIMB, params={"altitude_m": 100.0})
        challenge = self.confirmer.initiate(cmd)
        assert "drone-5" in challenge
        assert "climb to 100.0m" in challenge
        assert challenge.endswith("readback")

    def test_initiate_hold(self) -> None:
        cmd = _make_cmd(CommandType.HOLD)
        challenge = self.confirmer.initiate(cmd)
        assert "hold position" in challenge

    def test_initiate_squawk(self) -> None:
        cmd = _make_cmd(CommandType.SQUAWK, params={"code": "7700"})
        challenge = self.confirmer.initiate(cmd)
        assert "squawk 7700" in challenge

    def test_confirm_matching_readback(self) -> None:
        cmd = _make_cmd(CommandType.CLIMB, params={"altitude_m": 100.0})
        challenge = self.confirmer.initiate(cmd)
        result = self.confirmer.confirm(cmd, challenge)
        assert result.confirmed is True

    def test_confirm_mismatched_readback(self) -> None:
        cmd = _make_cmd(CommandType.CLIMB, params={"altitude_m": 100.0})
        result = self.confirmer.confirm(cmd, "totally wrong readback")
        assert result.confirmed is False

    def test_confirm_case_insensitive(self) -> None:
        cmd = _make_cmd(CommandType.HOLD)
        challenge = self.confirmer.initiate(cmd)
        result = self.confirmer.confirm(cmd, challenge.upper())
        assert result.confirmed is True

    def test_confirm_without_readback_suffix(self) -> None:
        cmd = _make_cmd(CommandType.HOLD)
        result = self.confirmer.confirm(cmd, "drone-5, hold position")
        assert result.confirmed is True

    def test_confirm_records_time(self) -> None:
        cmd = _make_cmd(CommandType.HOLD)
        challenge = self.confirmer.initiate(cmd)
        result = self.confirmer.confirm(cmd, challenge, confirmation_time_s=3.14)
        assert result.confirmation_time_s == 3.14


# ===========================================================================
# ProductionATCPipeline tests
# ===========================================================================

class TestProductionATCPipeline:
    """ProductionATCPipeline 통합 테스트."""

    def setup_method(self) -> None:
        self.pipeline = ProductionATCPipeline()

    def test_pipeline_valid_climb(self) -> None:
        cmd, check, msg = self.pipeline.process("drone-5 climb to 100m")
        assert cmd is not None
        assert check is not None
        assert check.is_safe is True
        assert "readback" in msg

    def test_pipeline_unsafe_altitude(self) -> None:
        cmd, check, msg = self.pipeline.process("drone-5 climb to 200m")
        assert cmd is not None
        assert check is not None
        assert check.is_safe is False
        assert "unsafe" in msg

    def test_pipeline_unrecognized(self) -> None:
        cmd, check, msg = self.pipeline.process("do something random")
        assert cmd is None
        assert check is None
        assert "unrecognized" in msg

    def test_pipeline_custom_ceiling(self) -> None:
        pipe = ProductionATCPipeline(airspace_ceiling_m=80.0)
        cmd, check, msg = pipe.process("drone-1 climb to 90m")
        assert check is not None
        assert check.is_safe is False

    def test_pipeline_custom_floor(self) -> None:
        pipe = ProductionATCPipeline(min_altitude_m=20.0)
        cmd, check, msg = pipe.process("drone-1 descend to 15m")
        assert check is not None
        assert check.is_safe is False

    def test_pipeline_priority_passthrough(self) -> None:
        cmd, _, _ = self.pipeline.process("drone-5 hold", priority=1)
        assert cmd is not None
        assert cmd.priority == 1

    def test_pipeline_timestamp_passthrough(self) -> None:
        cmd, _, _ = self.pipeline.process("drone-5 hold", timestamp_s=99.9)
        assert cmd is not None
        assert cmd.timestamp_s == 99.9


# ===========================================================================
# Dataclass immutability tests
# ===========================================================================

class TestImmutability:
    """Frozen dataclass 불변성 검증."""

    def test_atc_command_frozen(self) -> None:
        cmd = _make_cmd()
        with pytest.raises(AttributeError):
            cmd.priority = 99  # type: ignore[misc]

    def test_command_confirmation_frozen(self) -> None:
        cmd = _make_cmd()
        conf = CommandConfirmation(cmd, "test", True, 0.0)
        with pytest.raises(AttributeError):
            conf.confirmed = False  # type: ignore[misc]

    def test_safety_check_frozen(self) -> None:
        cmd = _make_cmd()
        check = SafetyCheck(cmd, True, (), RiskLevel.LOW)
        with pytest.raises(AttributeError):
            check.is_safe = False  # type: ignore[misc]

    def test_parameters_immutable(self) -> None:
        cmd = _make_cmd(params={"altitude_m": 100.0})
        with pytest.raises(TypeError):
            cmd.parameters["altitude_m"] = 999  # type: ignore[index]


# ===========================================================================
# as_dict / serialization tests
# ===========================================================================

class TestSerialization:
    """as_dict 직렬화 테스트."""

    def test_atc_command_as_dict(self) -> None:
        cmd = _make_cmd(CommandType.CLIMB, params={"altitude_m": 100.0})
        d = cmd.as_dict()
        assert d["command_type"] == "CLIMB"
        assert d["target_id"] == "drone-5"
        assert d["parameters"] == {"altitude_m": 100.0}
        assert isinstance(d["parameters"], dict)

    def test_safety_check_as_dict(self) -> None:
        cmd = _make_cmd()
        check = SafetyCheck(cmd, False, ("violation1",), RiskLevel.HIGH)
        d = check.as_dict()
        assert d["is_safe"] is False
        assert d["violations"] == ["violation1"]
        assert d["risk_level"] == "HIGH"

    def test_confirmation_as_dict(self) -> None:
        cmd = _make_cmd()
        conf = CommandConfirmation(cmd, "readback text", True, 1.5)
        d = conf.as_dict()
        assert d["pilot_readback"] == "readback text"
        assert d["confirmed"] is True
        assert d["confirmation_time_s"] == 1.5


# ===========================================================================
# CLI tests
# ===========================================================================

class TestCLI:
    """CLI argparse 테스트."""

    def test_cli_parse_json(self) -> None:
        result = subprocess.run(
            [sys.executable, "simulation/llm_atc_production.py",
             "--parse", "drone-5 climb to 100m", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        import json
        data = json.loads(result.stdout)
        assert data["command_type"] == "CLIMB"

    def test_cli_pipeline_json(self) -> None:
        result = subprocess.run(
            [sys.executable, "simulation/llm_atc_production.py",
             "--pipeline", "drone-3 hold", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        import json
        data = json.loads(result.stdout)
        assert data["command"] is not None
        assert data["safety_check"] is not None

    def test_cli_parse_failure(self) -> None:
        result = subprocess.run(
            [sys.executable, "simulation/llm_atc_production.py",
             "--parse", "gibberish input"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode != 0

    def test_cli_no_args_prints_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "simulation/llm_atc_production.py"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode != 0
