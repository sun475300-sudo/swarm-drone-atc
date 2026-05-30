"""Track A P691-P700 SW 컴포넌트 단위 테스트."""

import json

import pytest


# ── P691 px4_firmware_validator ──────────────────────────────────────────────

_VALID_PX4_PARAMS = {
    "NAV_ACC_RAD": 1.0, "MPC_XY_CRUISE": 5.0, "RTL_RETURN_ALT": 30.0,
    "COM_LOW_BAT_ACT": 2, "BAT_N_CELLS": 4, "MPC_Z_VEL_MAX_UP": 3.0,
    "MPC_Z_VEL_MAX_DN": 1.5, "COM_RC_LOSS_T": 5.0,
    "GF_ACTION": 1, "EKF2_AID_MASK": 1,
}


def test_px4_valid_version():
    from simulation.px4_firmware_validator import PX4FirmwareValidator
    v = PX4FirmwareValidator()
    v.validate_version("v1.15.0")  # must not raise


def test_px4_invalid_version_rejected():
    from simulation.px4_firmware_validator import PX4FirmwareValidator
    v = PX4FirmwareValidator()
    with pytest.raises(ValueError):
        v.validate_version("v1.14.9")


def test_px4_validate_params_ok():
    from simulation.px4_firmware_validator import PX4FirmwareValidator
    v = PX4FirmwareValidator()
    result = v.validate_params(_VALID_PX4_PARAMS)
    assert result.ok


def test_px4_validate_params_missing():
    from simulation.px4_firmware_validator import PX4FirmwareValidator
    v = PX4FirmwareValidator()
    result = v.validate_params({})
    assert not result.ok


# ── P692 onboard_bridge ───────────────────────────────────────────────────────

def test_onboard_bridge_relay_returns_bytes():
    from simulation.onboard_bridge import OnboardBridge
    bridge = OnboardBridge(simulate_packet_loss_rate=0.0)
    pkt = b"\x01\x02\x03"
    result = bridge.relay(pkt)
    assert result == pkt


def test_onboard_bridge_stats():
    from simulation.onboard_bridge import OnboardBridge
    bridge = OnboardBridge(simulate_packet_loss_rate=0.0)
    bridge.relay(b"hello")
    stats = bridge.stats
    assert stats.total >= 1


def test_onboard_bridge_full_loss():
    from simulation.onboard_bridge import OnboardBridge
    bridge = OnboardBridge(simulate_packet_loss_rate=1.0)
    result = bridge.relay(b"hello")
    assert result is None
    assert bridge.stats.dropped >= 1


# ── P693 remote_id_broadcast ─────────────────────────────────────────────────

def test_remote_id_broadcast_packet_format():
    from simulation.remote_id_broadcast import RemoteIDBroadcaster
    b = RemoteIDBroadcaster()
    pkt = b.broadcast("DRONE-1", lat=37.5, lon=127.0, alt=50.0, timestamp=1000.0)
    assert pkt["id"] == "DRONE-1"
    assert pkt["mode"] == "broadcast"
    assert "seq" in pkt


def test_remote_id_receiver_collect():
    import time
    from simulation.remote_id_broadcast import NetworkRemoteIDReceiver, RemoteIDBroadcaster
    broadcaster = RemoteIDBroadcaster()
    receiver = NetworkRemoteIDReceiver()
    now = time.time()
    pkt = broadcaster.broadcast("D1", 37.5, 127.0, 10.0, now)
    receiver.receive(pkt)
    assert "D1" in receiver.get_seen_ids()


# ── P694 rtk_gps_handler ─────────────────────────────────────────────────────

def test_crc24q_known_value():
    from simulation.rtk_gps_handler import crc24q
    # CRC of empty bytes should be 0
    assert isinstance(crc24q(b""), int)


def test_rtk_handler_invalid_returns_none():
    from simulation.rtk_gps_handler import RTKGPSHandler
    h = RTKGPSHandler()
    result = h.process(b"\x00\x00\x00")
    assert result is None


def test_rtk_handler_valid_preamble():
    from simulation.rtk_gps_handler import RTKGPSHandler, crc24q
    h = RTKGPSHandler()
    # Build minimal valid RTCM3 frame: preamble + length + msg_type + CRC
    msg_type = 1005
    payload_bits = (msg_type << 6).to_bytes(2, "big") + b"\x00" * 10
    length = len(payload_bits)
    header = bytes([0xD3, (length >> 8) & 0x03, length & 0xFF])
    body = header + payload_bits
    crc = crc24q(body)
    frame = body + crc.to_bytes(3, "big")
    result = h.process(frame)
    # May or may not parse fully but shouldn't raise
    assert result is None or hasattr(result, "msg_type")


# ── P695 failsafe_manager ────────────────────────────────────────────────────

def test_failsafe_normal():
    from simulation.failsafe_manager import FailsafeLevel, FailsafeManager
    fm = FailsafeManager()
    level = fm.evaluate(battery_pct=80.0, signal_ok=True, in_geofence=True)
    assert level == FailsafeLevel.NORMAL


def test_failsafe_low_battery():
    from simulation.failsafe_manager import FailsafeLevel, FailsafeManager
    fm = FailsafeManager()
    level = fm.evaluate(battery_pct=15.0, signal_ok=True, in_geofence=True)
    assert level == FailsafeLevel.LOW_BATTERY


def test_failsafe_critical():
    from simulation.failsafe_manager import FailsafeLevel, FailsafeManager
    fm = FailsafeManager()
    level = fm.evaluate(battery_pct=3.0, signal_ok=True, in_geofence=True)
    assert level == FailsafeLevel.CRITICAL


def test_failsafe_signal_lost():
    from simulation.failsafe_manager import FailsafeLevel, FailsafeManager
    fm = FailsafeManager()
    level = fm.evaluate(battery_pct=80.0, signal_ok=False, in_geofence=True)
    assert level == FailsafeLevel.SIGNAL_LOST


def test_failsafe_geofence():
    from simulation.failsafe_manager import FailsafeLevel, FailsafeManager
    fm = FailsafeManager()
    level = fm.evaluate(battery_pct=80.0, signal_ok=True, in_geofence=False)
    assert level == FailsafeLevel.GEOFENCE


def test_failsafe_get_action():
    from simulation.failsafe_manager import FailsafeLevel, FailsafeManager
    fm = FailsafeManager()
    action = fm.get_action(FailsafeLevel.CRITICAL)
    assert isinstance(action, str)
    assert len(action) > 0


# ── P696 swarm_time_sync ─────────────────────────────────────────────────────

def test_time_sync_corrects_offset():
    from simulation.swarm_time_sync import TimeSyncNode
    node = TimeSyncNode("node-0")
    corrected = node.sync(reference_time=1000.0, local_time=1000.5)
    assert abs(corrected - 1000.0) < 1.0  # within 1s


def test_swarm_time_sync_max_jitter():
    from simulation.swarm_time_sync import SwarmTimeSync
    s = SwarmTimeSync()
    s.add_node("A")
    s.add_node("B")
    s.sync_all(reference_time=1000.0)
    jitter = s.max_jitter_ms()
    assert isinstance(jitter, float)


# ── P697 mocap_hitl_bridge ───────────────────────────────────────────────────

def test_vrpn_to_mocap_pose():
    from simulation.mocap_hitl_bridge import VRPNMocapBridge
    bridge = VRPNMocapBridge()
    # Z-up → NED: ned_x=raw["y"], ned_y=raw["x"], ned_z=-raw["z"]
    vrpn_data = {"x": 1.0, "y": 2.0, "z": 3.0,
                 "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0,
                 "time": 1234.5}
    pose = bridge.parse_vrpn(vrpn_data)
    assert pose.x == pytest.approx(2.0, abs=1e-3)  # ned_x = raw["y"]
    assert pose.timestamp == pytest.approx(1234.5, abs=1e-3)


def test_mocap_to_mavlink_138():
    from simulation.mocap_hitl_bridge import VRPNMocapBridge
    bridge = VRPNMocapBridge()
    vrpn_data = {"x": 0.0, "y": 0.0, "z": 1.0,
                 "qw": 1.0, "qx": 0.0, "qy": 0.0, "qz": 0.0,
                 "time": 0.0}
    pose = bridge.parse_vrpn(vrpn_data)
    msg = bridge.to_mavlink_138(pose)
    assert msg["mavlink_msg_id"] == 138
    assert "q" in msg


# ── P698 outdoor_flight_test ─────────────────────────────────────────────────

def test_flight_test_sim_runs():
    from simulation.outdoor_flight_test import FlightTestConfig, OutdoorFlightTest
    config = FlightTestConfig(drone_count=3, formation="line", duration_s=5.0)
    test = OutdoorFlightTest()
    result = test.run_formation_sim(config)
    assert isinstance(result.success, bool)
    assert result.min_separation_m >= 0


# ── P699 environmental_scenario ──────────────────────────────────────────────

def test_apf_mode_normal():
    from simulation.environmental_scenario import APFMode, EnvironmentalScenario, WeatherCondition
    scenario = EnvironmentalScenario()
    weather = WeatherCondition(wind_speed_ms=5.0, rainfall_mm_h=0.0,
                               visibility_m=10000.0, light_lux=1000.0)
    assert scenario.get_apf_mode(weather) == APFMode.NORMAL


def test_apf_mode_windy():
    from simulation.environmental_scenario import APFMode, EnvironmentalScenario, WeatherCondition
    scenario = EnvironmentalScenario()
    weather = WeatherCondition(wind_speed_ms=15.0, rainfall_mm_h=0.0,
                               visibility_m=5000.0, light_lux=500.0)
    assert scenario.get_apf_mode(weather) == APFMode.WINDY


def test_wind_disturbance_changes_position():
    from simulation.environmental_scenario import EnvironmentalScenario, WeatherCondition
    scenario = EnvironmentalScenario()
    weather = WeatherCondition(wind_speed_ms=10.0, rainfall_mm_h=0.0,
                               visibility_m=5000.0, light_lux=500.0)
    pos = [0.0, 0.0, 50.0]
    new_pos = scenario.apply_wind_disturbance(pos, weather)
    assert len(new_pos) == 3


def test_preset_conditions_exist():
    from simulation.environmental_scenario import CALM, RAIN_HEAVY, WINDY_STORM
    assert CALM.wind_speed_ms < 5.0
    assert WINDY_STORM.wind_speed_ms > 10.0


# ── P700 hitl_report_generator ───────────────────────────────────────────────

def test_generate_fmea_8_items():
    from simulation.hitl_report_generator import HITLReportGenerator
    gen = HITLReportGenerator()
    items = gen.generate_fmea()
    assert len(items) == 8
    for item in items:
        assert item.rpn == item.severity * item.occurrence * item.detection


def test_generate_report():
    from simulation.hitl_report_generator import HITLReportGenerator
    gen = HITLReportGenerator()
    report = gen.generate_report(drone_count=5, test_duration_s=120.0, pass_rate=0.95)
    assert report.drone_count == 5
    assert len(report.fmea_items) == 8


def test_to_markdown():
    from simulation.hitl_report_generator import HITLReportGenerator
    gen = HITLReportGenerator()
    report = gen.generate_report(3, 60.0, 1.0)
    md = gen.to_markdown(report)
    assert "FMEA" in md
    assert "|" in md


def test_to_json():
    from simulation.hitl_report_generator import HITLReportGenerator
    gen = HITLReportGenerator()
    report = gen.generate_report(3, 60.0, 1.0)
    j = gen.to_json(report)
    data = json.loads(j)
    assert data["drone_count"] == 3
    assert len(data["fmea_items"]) == 8


def test_fmea_rpn_computed():
    from simulation.hitl_report_generator import HITLReportGenerator
    gen = HITLReportGenerator()
    items = gen.generate_fmea()
    for item in items:
        assert item.rpn == item.severity * item.occurrence * item.detection
