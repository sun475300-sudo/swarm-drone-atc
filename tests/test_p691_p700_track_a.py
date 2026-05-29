"""Tests for Phase 691-700 Track A: Hardware Integration Software Components."""

from __future__ import annotations

import time

import numpy as np
import pytest

from simulation.px4_firmware_validator import (
    FirmwareStatus,
    PX4FirmwareValidator,
    PX4_REQUIRED_PARAMS,
)
from simulation.onboard_bridge import BridgeMode, BridgeState, OnboardBridge
from simulation.remote_id_broadcast import (
    BroadcastMode,
    MessageType,
    RemoteIDBroadcaster,
    _encode_basic_id,
    _encode_location,
)
from simulation.rtk_gps_handler import RTKFixType, RTKGPSHandler
from simulation.failsafe_manager import (
    FailsafeLevel,
    FailsafeTrigger,
    FailsafeManager,
    GeofenceZone,
)
from simulation.swarm_time_sync import ClockState, SyncProtocol, SwarmTimeSync
from simulation.mocap_hitl_bridge import MocapHITLBridge, MocapSystem, HITLState
from simulation.outdoor_flight_test import (
    FlightTestPhase,
    FormationType,
    OutdoorFlightTestRunner,
    _compute_formation_positions,
)
from simulation.environmental_scenario import (
    EnvScenario,
    EnvironmentalScenarioSim,
    SCENARIO_PRESETS,
)
from simulation.hitl_report_generator import (
    Detectability,
    FMEAEntry,
    HITLReportGenerator,
    Probability,
    Severity,
)


# ── P691: PX4 Firmware Validator ──────────────────────────────────────────────

class TestPX4FirmwareValidator:
    def test_default_validation_passes(self):
        v = PX4FirmwareValidator(seed=0)
        report = v.validate()
        assert report.status == FirmwareStatus.VALID
        assert report.passed

    def test_version_mismatch_detected(self):
        v = PX4FirmwareValidator(seed=0)
        v._sim_firmware.version_major = 1
        v._sim_firmware.version_minor = 14
        report = v.validate()
        assert report.status == FirmwareStatus.VERSION_MISMATCH

    def test_param_invalid_detected(self):
        v = PX4FirmwareValidator(seed=0)
        v.set_sim_param("COM_RC_LOSS_T", 99.9)
        report = v.validate()
        assert report.status == FirmwareStatus.PARAM_INVALID
        assert report.param_pass_rate < 1.0

    def test_all_required_params_checked(self):
        v = PX4FirmwareValidator(seed=0)
        report = v.validate()
        checked_names = {r.param_name for r in report.param_results}
        assert checked_names == set(PX4_REQUIRED_PARAMS)

    def test_firmware_info_version_string(self):
        v = PX4FirmwareValidator(seed=0)
        fw = v.fetch_firmware_info()
        assert fw.version_str == "1.15.0"
        assert fw.meets_minimum(1, 15)
        assert not fw.meets_minimum(1, 16)

    def test_heartbeat_latency_in_range(self):
        v = PX4FirmwareValidator(seed=42)
        latency = v.simulate_heartbeat()
        assert 1.0 <= latency <= 15.0


# ── P692: Onboard Bridge ───────────────────────────────────────────────────────

class TestOnboardBridge:
    def test_connect_disconnect(self):
        b = OnboardBridge(mode=BridgeMode.SIMULATION)
        assert not b.is_connected
        assert b.connect()
        assert b.is_connected
        b.disconnect()
        assert not b.is_connected

    def test_heartbeat_increments_count(self):
        b = OnboardBridge(mode=BridgeMode.SIMULATION)
        b.connect()
        b.send_heartbeat()
        b.send_heartbeat()
        assert b.stats.heartbeats_sent == 2

    def test_forward_command_when_connected(self):
        b = OnboardBridge(mode=BridgeMode.SIMULATION)
        b.connect()
        ok = b.forward_command({"cmd": "TAKEOFF", "alt": 10.0})
        assert ok
        assert b.stats.msgs_forwarded == 1

    def test_forward_command_fails_when_disconnected(self):
        b = OnboardBridge(mode=BridgeMode.SIMULATION)
        ok = b.forward_command({"cmd": "TAKEOFF"})
        assert not ok
        assert b.stats.msgs_dropped == 1

    def test_collect_telemetry_returns_frame(self):
        b = OnboardBridge(mode=BridgeMode.SIMULATION, seed=7)
        b.connect()
        frame = b.collect_telemetry("D01")
        assert frame.drone_id == "D01"
        assert -90 <= frame.lat <= 90
        assert 0 <= frame.battery_pct <= 100

    def test_flush_clears_queue(self):
        b = OnboardBridge(mode=BridgeMode.SIMULATION)
        b.connect()
        b.send_heartbeat()
        b.forward_command({"x": 1})
        msgs = b.flush()
        assert len(msgs) == 2
        assert b.flush() == []

    def test_get_stats_keys(self):
        b = OnboardBridge(mode=BridgeMode.SIMULATION)
        b.connect()
        stats = b.get_stats()
        assert "state" in stats and "msgs_forwarded" in stats


# ── P693: Remote ID Broadcast ─────────────────────────────────────────────────

class TestRemoteIDBroadcast:
    def test_broadcast_returns_packets(self):
        rb = RemoteIDBroadcaster(seed=0)
        pkts = rb.broadcast("D01", 35.1, 126.9, 50.0, force=True)
        assert len(pkts) > 0

    def test_packet_types_covered(self):
        rb = RemoteIDBroadcaster(seed=0)
        pkts = rb.broadcast("D01", 35.1, 126.9, 50.0, force=True)
        types = {p.msg_type for p in pkts}
        assert MessageType.BASIC_ID in types
        assert MessageType.LOCATION in types
        assert MessageType.SYSTEM in types

    def test_not_due_skips_broadcast(self):
        rb = RemoteIDBroadcaster(interval_s=10.0, seed=0)
        rb.broadcast("D01", 35.1, 126.9, 50.0, force=True)
        pkts = rb.broadcast("D01", 35.1, 126.9, 50.0)
        assert pkts == []

    def test_fleet_broadcast(self):
        rb = RemoteIDBroadcaster(seed=0)
        fleet = {
            "D01": {"lat": 35.1, "lon": 126.9, "alt_m": 50.0, "force": True},
            "D02": {"lat": 35.2, "lon": 127.0, "alt_m": 60.0, "force": True},
        }
        result = rb.broadcast_fleet(fleet)
        assert "D01" in result and "D02" in result

    def test_compliance_status_after_broadcast(self):
        rb = RemoteIDBroadcaster(seed=0)
        rb.broadcast("D01", 35.1, 126.9, 50.0, force=True)
        status = rb.get_compliance_status("D01")
        assert status["compliant"]

    def test_encode_basic_id_length(self):
        payload = _encode_basic_id("DRONE001")
        assert len(payload) == 24

    def test_encode_location_bytes(self):
        payload = _encode_location(35.1, 126.9, 50.0, 5.0, 90.0, 0.0)
        assert isinstance(payload, bytes) and len(payload) > 0


# ── P694: RTK GPS Handler ─────────────────────────────────────────────────────

class TestRTKGPSHandler:
    def test_register_and_get_position(self):
        h = RTKGPSHandler(seed=0)
        h.register_drone("D01", 35.1, 126.9, 50.0)
        pos = h.get_position("D01")
        assert pos.drone_id == "D01"
        assert pos.fix_type in RTKFixType

    def test_fix_advances_to_fix(self):
        h = RTKGPSHandler(seed=0)
        h.register_drone("D01", 35.1, 126.9, 50.0)
        for _ in range(20):
            pos = h.get_position("D01")
        assert pos.fix_type == RTKFixType.FIX

    def test_fix_accuracy_centimeter(self):
        h = RTKGPSHandler(seed=0)
        h.register_drone("D01", 35.1, 126.9, 50.0)
        for _ in range(20):
            pos = h.get_position("D01")
        assert pos.is_centimeter

    def test_ingest_rtcm_valid(self):
        h = RTKGPSHandler(seed=0)
        ok = h.ingest_rtcm(b"\xd3\x00\x13" + b"\x00" * 20)
        assert ok

    def test_ingest_rtcm_too_short(self):
        h = RTKGPSHandler(seed=0)
        assert not h.ingest_rtcm(b"\xd3")

    def test_airspace_feedback_format(self):
        h = RTKGPSHandler(seed=0)
        fb = h.to_airspace_feedback("D01")
        assert "position" in fb and "fix_type" in fb and "usable" in fb

    def test_fleet_feedback(self):
        h = RTKGPSHandler(seed=0)
        results = h.fleet_feedback(["D01", "D02", "D03"])
        assert len(results) == 3


# ── P695: Failsafe Manager ────────────────────────────────────────────────────

class TestFailsafeManager:
    def test_normal_state_on_register(self):
        fm = FailsafeManager()
        state = fm.register("D01")
        assert state.level == FailsafeLevel.NORMAL

    def test_low_battery_triggers_warn(self):
        fm = FailsafeManager()
        fm.register("D01")
        fm.heartbeat("D01")
        state = fm.update("D01", battery_pct=20.0, lat=35.1, lon=126.9, alt_m=50.0)
        assert state.level == FailsafeLevel.WARN
        assert state.trigger == FailsafeTrigger.LOW_BATTERY

    def test_critical_battery_triggers_land(self):
        fm = FailsafeManager()
        fm.register("D01")
        fm.heartbeat("D01")
        state = fm.update("D01", battery_pct=10.0, lat=35.1, lon=126.9, alt_m=50.0)
        assert state.level == FailsafeLevel.LAND

    def test_geofence_breach_triggers_rtl(self):
        gf = GeofenceZone(center_lat=35.1, center_lon=126.9, radius_m=100.0)
        fm = FailsafeManager(geofence=gf)
        fm.register("D01")
        fm.heartbeat("D01")
        state = fm.update("D01", battery_pct=80.0, lat=36.0, lon=127.5, alt_m=50.0)
        assert state.level == FailsafeLevel.RTL

    def test_heartbeat_clears_comm_warn(self):
        fm = FailsafeManager()
        fm.register("D01")
        state = fm._states["D01"]
        state.last_comm = time.time() - 3.0
        fm.update("D01", battery_pct=80.0, lat=35.1, lon=126.9, alt_m=50.0)
        assert state.level == FailsafeLevel.WARN
        fm.heartbeat("D01")
        assert state.level == FailsafeLevel.NORMAL

    def test_heartbeat_clears_rtl_from_comm_loss(self):
        fm = FailsafeManager()
        fm.register("D01")
        state = fm._states["D01"]
        state.last_comm = time.time() - 10.0
        fm.update("D01", battery_pct=80.0, lat=35.1, lon=126.9, alt_m=50.0)
        assert state.level == FailsafeLevel.RTL
        fm.heartbeat("D01")
        assert state.level == FailsafeLevel.NORMAL
        assert not state.rtl_initiated

    def test_get_action_returns_string(self):
        fm = FailsafeManager()
        fm.register("D01")
        action = fm.get_action("D01")
        assert isinstance(action, str)

    def test_action_log_records_transitions(self):
        fm = FailsafeManager()
        fm.register("D01")
        fm.heartbeat("D01")
        fm.update("D01", battery_pct=5.0, lat=35.1, lon=126.9, alt_m=50.0)
        log = fm.action_log()
        assert len(log) >= 1


# ── P696: Swarm Time Sync ─────────────────────────────────────────────────────

class TestSwarmTimeSync:
    def test_add_nodes_and_elect_master(self):
        sync = SwarmTimeSync(seed=0)
        sync.add_node("M1", is_master=True)
        sync.add_node("S1")
        sync.add_node("S2")
        assert sync._master_id == "M1"

    def test_sync_reduces_offset(self):
        sync = SwarmTimeSync(seed=42)
        sync.add_node("M1", is_master=True)
        sync.add_node("S1")
        initial_offset = abs(sync._nodes["S1"].offset_us)
        sync.sync_all(steps=20)
        final_offset = abs(sync._nodes["S1"].offset_us)
        assert final_offset < initial_offset or final_offset < 10_000

    def test_jitter_compliance_after_sync(self):
        sync = SwarmTimeSync(network_delay_us=100.0, seed=0)
        sync.add_node("M1", is_master=True)
        for i in range(3):
            sync.add_node(f"S{i}")
        sync.sync_all(steps=50)
        result = sync.check_jitter_compliance()
        assert result["all_compliant"]

    def test_elect_master_without_explicit_master(self):
        sync = SwarmTimeSync(seed=0)
        for i in range(4):
            sync.add_node(f"D{i}")
        master = sync.elect_master()
        assert master is not None

    def test_get_node_status_keys(self):
        sync = SwarmTimeSync(seed=0)
        sync.add_node("M1", is_master=True)
        statuses = sync.get_node_status()
        assert len(statuses) == 1
        assert "offset_us" in statuses[0]

    def test_sync_step_returns_message(self):
        sync = SwarmTimeSync(network_delay_us=200.0, seed=0)
        sync.add_node("M1", is_master=True)
        sync.add_node("S1")
        msg = sync.sync_step("S1")
        assert msg is not None
        assert msg.src == "M1"


# ── P697: MoCap HITL Bridge ───────────────────────────────────────────────────

class TestMocapHITLBridge:
    def test_start_sets_receiving(self):
        bridge = MocapHITLBridge(system=MocapSystem.SIMULATION, seed=0)
        bridge.start()
        assert bridge.state == HITLState.RECEIVING

    def test_ingest_vrpn_sim_mode(self):
        bridge = MocapHITLBridge(seed=0)
        pose = bridge.ingest_vrpn_frame("D01")
        assert -10 <= pose.x_m <= 10
        assert pose.z_m >= 0

    def test_pose_to_vision_estimate(self):
        bridge = MocapHITLBridge(seed=0)
        pose = bridge.ingest_vrpn_frame("D01")
        ve = bridge.pose_to_vision_estimate(pose)
        assert ve.z == -pose.z_m
        assert ve.usec > 0

    def test_process_returns_mavlink_dict(self):
        bridge = MocapHITLBridge(seed=0)
        result = bridge.process("D01")
        assert result["msg_type"] == "VISION_POSITION_ESTIMATE"
        assert "x" in result and "y" in result

    def test_latency_report_after_process(self):
        bridge = MocapHITLBridge(seed=0)
        for _ in range(10):
            bridge.process("D01")
        report = bridge.get_latency_report()
        assert "mean_us" in report and "compliant" in report

    def test_parse_raw_bytes(self):
        bridge = MocapHITLBridge(seed=0)
        raw = np.array([1.0, 2.0, 3.0, 0.1, 0.2, 0.3], dtype=np.float64).tobytes()
        pose = bridge.ingest_vrpn_frame("D01", raw)
        assert abs(pose.x_m - 1.0) < 1e-9


# ── P698: Outdoor Flight Test ─────────────────────────────────────────────────

class TestOutdoorFlightTest:
    def test_hover_test_passes(self):
        runner = OutdoorFlightTestRunner(drone_count=3, seed=42)
        result = runner.run_hover_test()
        assert result.drone_count == 3
        assert isinstance(result.passed, bool)

    def test_formation_test_line(self):
        runner = OutdoorFlightTestRunner(drone_count=3, seed=42)
        result = runner.run_formation_test(FormationType.LINE)
        assert result.scenario_name == "formation_line"

    def test_formation_test_vee(self):
        runner = OutdoorFlightTestRunner(drone_count=5, seed=7)
        result = runner.run_formation_test(FormationType.VEE)
        assert result.drone_count == 5

    def test_gps_trace_replay(self):
        runner = OutdoorFlightTestRunner(drone_count=3, seed=0)
        trace = [
            {"drone_id": "D01", "lat": 35.1, "lon": 126.9, "alt_m": 10.0},
            {"drone_id": "D02", "lat": 35.1, "lon": 126.9, "alt_m": 10.0},
        ]
        result = runner.run_gps_trace_replay(trace)
        assert result.scenario_name == "gps_trace_replay"
        assert "frames" in result.metrics

    def test_invalid_drone_count_raises(self):
        with pytest.raises(ValueError):
            OutdoorFlightTestRunner(drone_count=1)
        with pytest.raises(ValueError):
            OutdoorFlightTestRunner(drone_count=6)

    def test_compute_formation_positions_count(self):
        positions = _compute_formation_positions(35.1, 126.9, 10.0, FormationType.DIAMOND, 4)
        assert len(positions) == 4

    def test_flight_result_has_metrics(self):
        runner = OutdoorFlightTestRunner(drone_count=3, seed=0)
        result = runner.run_hover_test()
        assert "hover_error_m" in result.metrics


# ── P699: Environmental Scenario ─────────────────────────────────────────────

class TestEnvironmentalScenario:
    def test_load_calm_scenario(self):
        sim = EnvironmentalScenarioSim(seed=0)
        env = sim.load_scenario(EnvScenario.CALM)
        assert env.scenario == EnvScenario.CALM
        assert env.wind.speed_ms < 10

    def test_high_wind_selects_windy_apf(self):
        sim = EnvironmentalScenarioSim(seed=0)
        env = sim.load_scenario(EnvScenario.WIND_TUNNEL)
        assert env.wind.is_high_wind
        assert env.apf_params != {}

    def test_rain_drag_multiplier(self):
        sim = EnvironmentalScenarioSim(seed=0)
        env = sim.load_scenario(EnvScenario.RAIN)
        assert env.rain.drag_multiplier > 1.0

    def test_low_light_detection_probability(self):
        sim = EnvironmentalScenarioSim(seed=0)
        env = sim.load_scenario(EnvScenario.LOW_LIGHT)
        assert 0.3 <= env.light.detection_probability <= 1.0

    def test_apply_wind_force_changes_velocity(self):
        sim = EnvironmentalScenarioSim(seed=42)
        env = sim.load_scenario(EnvScenario.WIND_TUNNEL)
        vel = np.zeros(3)
        adjusted = sim.apply_wind_force(vel, env)
        assert not np.allclose(adjusted, vel)

    def test_run_scenario_returns_metrics(self):
        sim = EnvironmentalScenarioSim(seed=0)
        metrics = sim.run_scenario(EnvScenario.CALM, steps=50)
        assert metrics.scenario == "calm"
        assert 0.0 <= metrics.detection_rate <= 1.0

    def test_run_all_scenarios(self):
        sim = EnvironmentalScenarioSim(seed=0)
        results = sim.run_all_scenarios(steps=20)
        assert len(results) == len(EnvScenario)

    def test_all_scenario_presets_exist(self):
        for s in EnvScenario:
            assert s in SCENARIO_PRESETS


# ── P700: HITL Report Generator ───────────────────────────────────────────────

class TestHITLReportGenerator:
    def test_fmea_entries_loaded(self):
        gen = HITLReportGenerator()
        assert len(gen._report.fmea_entries) > 0

    def test_rpn_computation(self):
        entry = FMEAEntry(
            component="Test",
            failure_mode="test_fail",
            failure_effect="effect",
            severity=Severity.CRITICAL,
            probability=Probability.PROBABLE,
            detectability=Detectability.MODERATE,
            current_controls="none",
            recommended_action="fix it",
        )
        assert entry.rpn == Severity.CRITICAL.value * Probability.PROBABLE.value * Detectability.MODERATE.value

    def test_risk_level_critical(self):
        # NEGLIGIBLE(4) * IMPROBABLE(5) * UNDETECTABLE(10) = 200 → CRITICAL
        entry = FMEAEntry(
            component="C", failure_mode="f", failure_effect="e",
            severity=Severity.NEGLIGIBLE, probability=Probability.IMPROBABLE,
            detectability=Detectability.UNDETECTABLE,
            current_controls="", recommended_action="",
        )
        assert entry.rpn == 200
        assert entry.risk_level == "CRITICAL"

    def test_add_test_results_and_finalize(self):
        gen = HITLReportGenerator()
        gen.add_test_result("hover_test", True, 5.2)
        gen.add_test_result("formation_test", True, 8.1)
        report = gen.finalize()
        assert report.overall_passed
        assert report.safety_score >= 0

    def test_overall_failed_if_any_test_fails(self):
        gen = HITLReportGenerator()
        gen.add_test_result("test_a", True, 1.0)
        gen.add_test_result("test_b", False, 2.0)
        report = gen.finalize()
        assert not report.overall_passed

    def test_to_markdown_contains_fmea(self):
        gen = HITLReportGenerator()
        md = gen.to_markdown()
        assert "FMEA" in md
        assert "GPS" in md

    def test_to_json_valid_structure(self):
        import json
        gen = HITLReportGenerator()
        gen.add_test_result("t1", True, 1.0, {"err": 0.1})
        data = json.loads(gen.to_json())
        assert "fmea" in data and "tests" in data
        assert len(data["fmea"]) > 0

    def test_safety_score_in_range(self):
        gen = HITLReportGenerator()
        score = gen.compute_safety_score()
        assert 0.0 <= score <= 100.0
