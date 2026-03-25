"""
DroneProfile 및 DRONE_PROFILES 포괄적 단위 테스트
"""
from __future__ import annotations

import pytest

from src.airspace_control.agents.drone_profiles import DroneProfile, DRONE_PROFILES


class TestDroneProfile:
    def test_all_profiles_have_required_attrs(self):
        for name, profile in DRONE_PROFILES.items():
            assert hasattr(profile, "max_speed_ms")
            assert hasattr(profile, "cruise_speed_ms")
            assert hasattr(profile, "battery_wh")
            assert hasattr(profile, "endurance_min")
            assert hasattr(profile, "comm_range_m")
            assert hasattr(profile, "priority")
            assert hasattr(profile, "max_altitude_m")

    def test_emergency_highest_priority(self):
        assert DRONE_PROFILES["EMERGENCY"].priority < DRONE_PROFILES["COMMERCIAL_DELIVERY"].priority
        assert DRONE_PROFILES["EMERGENCY"].priority < DRONE_PROFILES["RECREATIONAL"].priority

    def test_rogue_lowest_priority(self):
        assert DRONE_PROFILES["ROGUE"].priority > DRONE_PROFILES["COMMERCIAL_DELIVERY"].priority

    def test_max_speed_greater_than_cruise(self):
        for name, profile in DRONE_PROFILES.items():
            assert profile.max_speed_ms >= profile.cruise_speed_ms

    def test_positive_battery(self):
        for name, profile in DRONE_PROFILES.items():
            assert profile.battery_wh > 0

    def test_positive_comm_range_except_rogue(self):
        """ROGUE는 comm_range=0 (미등록)"""
        for name, profile in DRONE_PROFILES.items():
            if name != "ROGUE":
                assert profile.comm_range_m > 0

    def test_rogue_no_comm_range(self):
        assert DRONE_PROFILES["ROGUE"].comm_range_m == 0.0

    def test_all_expected_profiles_exist(self):
        expected = {"COMMERCIAL_DELIVERY", "SURVEILLANCE", "EMERGENCY", "RECREATIONAL", "ROGUE"}
        assert expected.issubset(set(DRONE_PROFILES.keys()))

    def test_positive_endurance(self):
        for name, profile in DRONE_PROFILES.items():
            assert profile.endurance_min > 0

    def test_positive_max_altitude(self):
        for name, profile in DRONE_PROFILES.items():
            assert profile.max_altitude_m > 0
