"""
Flight Envelope Protection
Phase 359 - G-limit, Stall Protection, Speed Limits, Load Factor
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from enum import Enum


class EnvelopeLimitType(Enum):
    STALL_SPEED = "stall_speed"
    MAX_SPEED = "max_speed"
    MAX_ALTITUDE = "max_altitude"
    MIN_ALTITUDE = "min_altitude"
    MAX_LOAD_FACTOR = "max_load_factor"
    MIN_LOAD_FACTOR = "min_load_factor"
    MAX_BANK_ANGLE = "max_bank_angle"
    MAX_PITCH_ANGLE = "max_pitch_angle"
    MAX_RATE_OF_CLIMB = "max_rate_of_climb"
    MAX_G = "max_g"
    MIN_G = "min_g"


class ProtectionLevel(Enum):
    WARNING = "warning"
    CAUTION = "caution"
    PROTECTION = "protection"
    HARD_LIMIT = "hard_limit"


@dataclass
class FlightEnvelope:
    stall_speed_ms: float = 15.0
    max_speed_ms: float = 50.0
    max_altitude_m: float = 120.0
    min_altitude_m: float = 5.0
    max_load_factor: float = 4.0
    min_load_factor: float = -1.0
    max_bank_angle_deg: float = 45.0
    max_pitch_angle_deg: float = 30.0
    max_rate_of_climb_ms: float = 10.0
    max_g: float = 4.0
    min_g: float = -1.5


@dataclass
class DroneState:
    position: Tuple[float, float, float]
    velocity: Tuple[float, float, float]
    attitude: Tuple[float, float, float]
    acceleration: Tuple[float, float, float]
    mass: float
    battery_percent: float


@dataclass
class EnvelopeAlert:
    limit_type: EnvelopeLimitType
    level: ProtectionLevel
    current_value: float
    limit_value: float
    message: str
    recommended_action: str


class StallProtection:
    def __init__(self, envelope: FlightEnvelope):
        self.envelope = envelope
        self.stall_speed_buffer = 3.0

    def calculate_stall_speed(
        self, angle_of_attack: float, density_altitude: float
    ) -> float:
        base_stall = self.envelope.stall_speed_ms
        aoa_factor = 1.0 + (angle_of_attack / 20.0)
        density_factor = 1.0 - (density_altitude / 20000.0)

        return base_stall * aoa_factor * max(0.5, density_factor)

    def check_stall(self, state: DroneState) -> Optional[EnvelopeAlert]:
        speed = np.linalg.norm(state.velocity)

        altitude = state.position[2]
        density_alt = altitude * (1 - 0.00002 * altitude)

        aoa = self._estimate_aoa(state)
        current_stall = self.calculate_stall_speed(aoa, density_alt)

        if speed < current_stall:
            return EnvelopeAlert(
                limit_type=EnvelopeLimitType.STALL_SPEED,
                level=ProtectionLevel.HARD_LIMIT,
                current_value=speed,
                limit_value=current_stall,
                message=f"STALL WARNING: Speed {speed:.1f} < Stall speed {current_stall:.1f} m/s",
                recommended_action="Reduce pitch angle, increase airspeed",
            )
        elif speed < current_stall + self.stall_speed_buffer:
            return EnvelopeAlert(
                limit_type=EnvelopeLimitType.STALL_SPEED,
                level=ProtectionLevel.WARNING,
                current_value=speed,
                limit_value=current_stall,
                message=f"STALL CAUTION: Approaching stall speed",
                recommended_action="Reduce angle of attack",
            )

        return None

    def _estimate_aoa(self, state: DroneState) -> float:
        speed = np.linalg.norm(state.velocity)
        if speed < 1:
            return 0.0

        vertical_component = abs(state.velocity[2])
        aoa = np.degrees(np.arcsin(vertical_component / speed))

        return aoa


class LoadFactorProtection:
    def __init__(self, envelope: FlightEnvelope):
        self.envelope = envelope
        self.turn_rate_limit = 180.0

    def calculate_load_factor(self, speed: float, turn_rate: float) -> float:
        if speed < 1:
            return 1.0

        radius = speed / (np.radians(turn_rate) + 0.001)

        load_factor = 1.0 + (speed**2) / (radius * 9.81)

        return load_factor

    def calculate_bank_load_factor(self, bank_angle: float, speed: float) -> float:
        bank_rad = np.radians(bank_angle)

        if speed < 1:
            return 1.0 / np.cos(bank_rad)

        load_factor = 1.0 / np.cos(bank_rad)

        return load_factor

    def check_load_factor(self, state: DroneState) -> Optional[EnvelopeAlert]:
        accel_mag = np.linalg.norm(state.acceleration)

        load_factor = accel_mag / 9.81

        bank = abs(state.attitude[2])
        pitch = state.attitude[1]

        total_load = load_factor * (1 + abs(np.radians(pitch)) / np.pi)

        if total_load > self.envelope.max_load_factor:
            return EnvelopeAlert(
                limit_type=EnvelopeLimitType.MAX_LOAD_FACTOR,
                level=ProtectionLevel.HARD_LIMIT,
                current_value=total_load,
                limit_value=self.envelope.max_load_factor,
                message=f"OVERLOAD: Load factor {total_load:.1f}g > {self.envelope.max_load_factor}g",
                recommended_action="Reduce bank angle and pitch immediately",
            )
        elif total_load > self.envelope.max_load_factor * 0.8:
            return EnvelopeAlert(
                limit_type=EnvelopeLimitType.MAX_LOAD_FACTOR,
                level=ProtectionLevel.CAUTION,
                current_value=total_load,
                limit_value=self.envelope.max_load_factor,
                message=f"LOAD CAUTION: Approaching load limit",
                recommended_action="Reduce maneuver intensity",
            )

        if load_factor < self.envelope.min_load_factor:
            return EnvelopeAlert(
                limit_type=EnvelopeLimitType.MIN_LOAD_FACTOR,
                level=ProtectionLevel.HARD_LIMIT,
                current_value=load_factor,
                limit_value=self.envelope.min_load_factor,
                message=f"NEGATIVE G: Load factor {load_factor:.1f}g < {self.envelope.min_load_factor}g",
                recommended_action="Recover from dive",
            )

        return None


class SpeedProtection:
    def __init__(self, envelope: FlightEnvelope):
        self.envelope = envelope
        self.speed_buffer = 5.0

    def check_speed(self, state: DroneState) -> Optional[EnvelopeAlert]:
        speed = np.linalg.norm(state.velocity)

        if speed > self.envelope.max_speed_ms:
            return EnvelopeAlert(
                limit_type=EnvelopeLimitType.MAX_SPEED,
                level=ProtectionLevel.HARD_LIMIT,
                current_value=speed,
                limit_value=self.envelope.max_speed_ms,
                message=f"OVERSPEED: {speed:.1f} m/s > {self.envelope.max_speed_ms} m/s",
                recommended_action="Reduce throttle, increase drag",
            )
        elif speed > self.envelope.max_speed_ms - self.speed_buffer:
            return EnvelopeAlert(
                limit_type=EnvelopeLimitType.MAX_SPEED,
                level=ProtectionLevel.WARNING,
                current_value=speed,
                limit_value=self.envelope.max_speed_ms,
                message=f"SPEED CAUTION: Approaching max speed",
                recommended_action="Reduce airspeed",
            )

        return None


class AltitudeProtection:
    def __init__(self, envelope: FlightEnvelope):
        self.envelope = envelope
        self.low_alt_buffer = 10.0
        self.high_alt_buffer = 10.0

    def check_altitude(self, state: DroneState) -> Optional[EnvelopeAlert]:
        altitude = state.position[2]

        if altitude > self.envelope.max_altitude_m:
            return EnvelopeAlert(
                limit_type=EnvelopeLimitType.MAX_ALTITUDE,
                level=ProtectionLevel.HARD_LIMIT,
                current_value=altitude,
                limit_value=self.envelope.max_altitude_m,
                message=f"ALTITUDE: {altitude:.1f}m > {self.envelope.max_altitude_m}m",
                recommended_action="Descend immediately",
            )
        elif altitude > self.envelope.max_altitude_m - self.high_alt_buffer:
            return EnvelopeAlert(
                limit_type=EnvelopeLimitType.MAX_ALTITUDE,
                level=ProtectionLevel.WARNING,
                current_value=altitude,
                limit_value=self.envelope.max_altitude_m,
                message=f"ALTITUDE CAUTION: Approaching ceiling",
                recommended_action="Reduce climb rate",
            )

        if altitude < self.envelope.min_altitude_m:
            return EnvelopeAlert(
                limit_type=EnvelopeLimitType.MIN_ALTITUDE,
                level=ProtectionLevel.HARD_LIMIT,
                current_value=altitude,
                limit_value=self.envelope.min_altitude_m,
                message=f"LOW ALTITUDE: {altitude:.1f}m < {self.envelope.min_altitude_m}m",
                recommended_action="Climb immediately",
            )
        elif altitude < self.envelope.min_altitude_m + self.low_alt_buffer:
            return EnvelopeAlert(
                limit_type=EnvelopeLimitType.MIN_ALTITUDE,
                level=ProtectionLevel.WARNING,
                current_value=altitude,
                limit_value=self.envelope.min_altitude_m,
                message=f"LOW ALTITUDE WARNING",
                recommended_action="Monitor altitude",
            )

        return None


class AttitudeProtection:
    def __init__(self, envelope: FlightEnvelope):
        self.envelope = envelope

    def check_attitude(self, state: DroneState) -> List[EnvelopeAlert]:
        alerts = []

        roll = np.degrees(state.attitude[2])
        pitch = np.degrees(state.attitude[1])

        if abs(roll) > self.envelope.max_bank_angle_deg:
            level = (
                ProtectionLevel.HARD_LIMIT
                if abs(roll) > self.envelope.max_bank_angle_deg * 1.2
                else ProtectionLevel.CAUTION
            )
            alerts.append(
                EnvelopeAlert(
                    limit_type=EnvelopeLimitType.MAX_BANK_ANGLE,
                    level=level,
                    current_value=abs(roll),
                    limit_value=self.envelope.max_bank_angle_deg,
                    message=f"BANK: {abs(roll):.1f}° > {self.envelope.max_bank_angle_deg}°",
                    recommended_action="Level wings",
                )
            )

        if abs(pitch) > self.envelope.max_pitch_angle_deg:
            level = (
                ProtectionLevel.HARD_LIMIT
                if abs(pitch) > self.envelope.max_pitch_angle_deg * 1.2
                else ProtectionLevel.CAUTION
            )
            alerts.append(
                EnvelopeAlert(
                    limit_type=EnvelopeLimitType.MAX_PITCH_ANGLE,
                    level=level,
                    current_value=abs(pitch),
                    limit_value=self.envelope.max_pitch_angle_deg,
                    message=f"PITCH: {abs(pitch):.1f}° > {self.envelope.max_pitch_angle_deg}°",
                    recommended_action="Level pitch",
                )
            )

        return alerts


class FlightEnvelopeProtectionSystem:
    def __init__(self, envelope: Optional[FlightEnvelope] = None):
        self.envelope = envelope or FlightEnvelope()

        self.stall_protection = StallProtection(self.envelope)
        self.load_protection = LoadFactorProtection(self.envelope)
        self.speed_protection = SpeedProtection(self.envelope)
        self.altitude_protection = AltitudeProtection(self.envelope)
        self.attitude_protection = AttitudeProtection(self.envelope)

        self.active_alerts: List[EnvelopeAlert] = []
        self.alert_history: List[EnvelopeAlert] = []

    def check_all_limits(self, state: DroneState) -> List[EnvelopeAlert]:
        self.active_alerts = []

        alerts = []

        stall_alert = self.stall_protection.check_stall(state)
        if stall_alert:
            alerts.append(stall_alert)

        speed_alert = self.speed_protection.check_speed(state)
        if speed_alert:
            alerts.append(speed_alert)

        alt_alert = self.altitude_protection.check_altitude(state)
        if alt_alert:
            alerts.append(alt_alert)

        load_alert = self.load_protection.check_load_factor(state)
        if load_alert:
            alerts.append(load_alert)

        attitude_alerts = self.attitude_protection.check_attitude(state)
        alerts.extend(attitude_alerts)

        self.active_alerts = sorted(alerts, key=lambda a: a.level.value)
        self.alert_history.extend(alerts)

        return self.active_alerts

    def get_protection_command(self, state: DroneState) -> Dict:
        alerts = self.check_all_limits(state)

        if not alerts:
            return {"status": "normal", "command": None}

        max_level = max(alerts, key=lambda a: self._level_priority(a.level))

        command = self._generate_protection_command(max_level, state)

        return {
            "status": max_level.level.value,
            "alert": max_level.message,
            "command": command,
            "all_alerts": [a.message for a in alerts],
        }

    def _level_priority(self, level: ProtectionLevel) -> int:
        priorities = {
            ProtectionLevel.HARD_LIMIT: 4,
            ProtectionLevel.PROTECTION: 3,
            ProtectionLevel.CAUTION: 2,
            ProtectionLevel.WARNING: 1,
        }
        return priorities.get(level, 0)

    def _generate_protection_command(
        self, alert: EnvelopeAlert, state: DroneState
    ) -> Dict:
        if alert.limit_type == EnvelopeLimitType.STALL_SPEED:
            return {"pitch": -10, "throttle": 1.0}
        elif alert.limit_type == EnvelopeLimitType.MAX_SPEED:
            return {"throttle": 0.3, "pitch": 5}
        elif alert.limit_type == EnvelopeLimitType.MAX_ALTITUDE:
            return {"pitch": -15, "throttle": 0.5}
        elif alert.limit_type == EnvelopeLimitType.MIN_ALTITUDE:
            return {"pitch": 20, "throttle": 1.0}
        elif alert.limit_type == EnvelopeLimitType.MAX_LOAD_FACTOR:
            return {"roll": 0, "pitch": 0, "throttle": 0.7}

        return {}


def simulate_flight_envelope():
    envelope = FlightEnvelope()
    system = FlightEnvelopeProtectionSystem(envelope)

    print("=== Flight Envelope Protection Simulation ===")

    test_scenarios = [
        {
            "name": "Normal flight",
            "pos": (100, 100, 50),
            "vel": (10, 10, 0),
            "att": (0, 0, 0),
            "acc": (0, 0, 0),
        },
        {
            "name": "Stall approach",
            "pos": (100, 100, 50),
            "vel": (12, 0, -2),
            "att": (0, -20, 0),
            "acc": (0, 0, 0),
        },
        {
            "name": "Overspeed",
            "pos": (100, 100, 50),
            "vel": (55, 0, 0),
            "att": (0, 0, 0),
            "acc": (0, 0, 0),
        },
        {
            "name": "High altitude",
            "pos": (100, 100, 130),
            "vel": (20, 0, 5),
            "att": (0, 10, 0),
            "acc": (0, 0, 0),
        },
        {
            "name": "Low altitude",
            "pos": (100, 100, 3),
            "vel": (20, 0, -3),
            "att": (0, -10, 0),
            "acc": (0, 0, 0),
        },
        {
            "name": "High load",
            "pos": (100, 100, 50),
            "vel": (30, 0, 0),
            "att": (0, 0, 45),
            "acc": (25, 0, 0),
        },
        {
            "name": "Extreme bank",
            "pos": (100, 100, 50),
            "vel": (25, 0, 0),
            "att": (0, 0, 60),
            "acc": (15, 0, 0),
        },
    ]

    for scenario in test_scenarios:
        state = DroneState(
            position=scenario["pos"],
            velocity=scenario["vel"],
            attitude=np.radians(scenario["att"]),
            acceleration=scenario["acc"],
            mass=5.0,
            battery_percent=80.0,
        )

        result = system.get_protection_command(state)

        print(f"\n{scenario['name']}:")
        print(f"  Status: {result['status']}")
        if result.get("alert"):
            print(f"  Alert: {result['alert']}")
        if result.get("command"):
            print(f"  Command: {result['command']}")

    print(f"\n=== Summary ===")
    print(f"Total alerts: {len(system.alert_history)}")
    print(
        f"Hard limits: {sum(1 for a in system.alert_history if a.level == ProtectionLevel.HARD_LIMIT)}"
    )

    return system.alert_history


if __name__ == "__main__":
    simulate_flight_envelope()
