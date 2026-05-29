"""Track A P691-P700 하드웨어 통합 SW 컴포넌트 단위 테스트.

실기 하드웨어 없이 소프트웨어 계약만 검증.
하드웨어 필요 테스트: @pytest.mark.hardware (CI에서 skip)
"""

from __future__ import annotations

import pytest
import numpy as np


# ── P691: PX4 펌웨어 검증 ────────────────────────────────────────────
class TestPX4FirmwareValidator:
    def test_valid_px4_version_passes(self):
        from simulation.px4_firmware_validator import PX4FirmwareValidator, ValidationResult
        v = PX4FirmwareValidator()
        params = {
            "COM_RCL_EXCEPT": 0, "NAV_RCL_ACT": 2, "NAV_DLL_ACT": 2,
            "MIS_TAKEOFF_ALT": 10.0, "MPC_THR_MIN": 0.12, "MPC_THR_MAX": 0.85,
            "GF_ACTION": 2, "EKF2_AID_MASK": 1, "CBRK_SUPPLY_CHK": 0, "SDLOG_MODE": 1,
        }
        report = v.validate("PX4 v1.15.2-abc1234", params)
        assert report.version_ok is True
        assert report.overall == ValidationResult.PASS

    def test_old_px4_version_fails(self):
        from simulation.px4_firmware_validator import PX4FirmwareValidator
        v = PX4FirmwareValidator()
        report = v.validate("PX4 v1.14.0", {})
        assert report.version_ok is False

    def test_missing_params_warn(self):
        from simulation.px4_firmware_validator import PX4FirmwareValidator, ValidationResult
        v = PX4FirmwareValidator()
        report = v.validate("PX4 v1.15.0", {})
        assert any(c.result == ValidationResult.WARN for c in report.param_checks)

    def test_invalid_param_value_fails(self):
        from simulation.px4_firmware_validator import PX4FirmwareValidator, ValidationResult
        v = PX4FirmwareValidator()
        params = {"GF_ACTION": 99}   # 허용값 범위 밖
        report = v.validate("PX4 v1.15.0", params)
        failures = report.failures
        assert any(p.param == "GF_ACTION" for p in failures)

    def test_ardupilot_version_parsing(self):
        from simulation.px4_firmware_validator import PX4FirmwareValidator, FirmwareFamily
        v = PX4FirmwareValidator()
        report = v.validate("ArduPilot ArduCopter v4.5.0", {})
        assert report.version.family == FirmwareFamily.ARDUPILOT

    def test_to_dict_keys(self):
        from simulation.px4_firmware_validator import PX4FirmwareValidator
        v = PX4FirmwareValidator()
        d = v.validate("PX4 v1.15.0", {}).to_dict()
        assert "version" in d and "overall" in d


# ── P692: SimPy 온보드 브릿지 ────────────────────────────────────────
class TestOnboardBridgeSim:
    def test_start_and_route_uart(self):
        import simpy
        from simulation.onboard_bridge import OnboardBridgeSim, MAVLinkMsg

        env = simpy.Environment()
        bridge = OnboardBridgeSim(env, "drone_0", uart_latency_ms=1.0, udp_latency_ms=2.0)
        received = []
        bridge.register_output_callback(lambda direction, msg: received.append((direction, msg)))
        bridge.start()

        msg = MAVLinkMsg(msg_id=0, seq=1, system_id=1, component_id=1)
        bridge.send_uart(msg)
        env.run(until=0.1)

        assert any("uart→udp" in d for d, _ in received)

    def test_stats_incremented(self):
        import simpy
        from simulation.onboard_bridge import OnboardBridgeSim, MAVLinkMsg

        env = simpy.Environment()
        bridge = OnboardBridgeSim(env, "drone_1")
        bridge.start()
        bridge.send_uart(MAVLinkMsg(0, 1, 1, 1))
        bridge.send_udp(MAVLinkMsg(0, 2, 1, 1))
        env.run(until=0.05)
        assert bridge.stats.uart_tx >= 1
        assert bridge.stats.udp_tx >= 1


# ── P693: Remote ID 방송 ─────────────────────────────────────────────
class TestRemoteIDBroadcast:
    def test_broadcast_success(self):
        from simulation.remote_id_broadcast import (
            RemoteIDBroadcaster, BroadcastMode, TransmitResult,
        )
        bc = RemoteIDBroadcaster("drone_0", BroadcastMode.BROADCAST, rate_hz=1.0)
        frames = []
        bc.subscribe(frames.append)

        msg = bc.build_message(34.9, 126.9, 30.0, 5.0, 90.0)
        result = bc.broadcast(msg)

        assert result == TransmitResult.SUCCESS
        assert len(frames) == 1
        assert frames[0].drone_id == "drone_0"

    def test_invalid_rate_raises(self):
        from simulation.remote_id_broadcast import RemoteIDBroadcaster, BroadcastMode
        with pytest.raises(ValueError, match="범위"):
            RemoteIDBroadcaster("drone_0", BroadcastMode.BROADCAST, rate_hz=0.5)

    def test_fleet_manager(self):
        from simulation.remote_id_broadcast import FleetRemoteIDManager, BroadcastMode
        mgr = FleetRemoteIDManager()
        mgr.register("d0", BroadcastMode.BROADCAST)
        mgr.register("d1", BroadcastMode.NETWORK)
        assert mgr.active_count() == 2
        stats = mgr.fleet_stats()
        assert "d0" in stats and "d1" in stats

    def test_stats_success_rate(self):
        from simulation.remote_id_broadcast import RemoteIDBroadcaster, BroadcastMode
        bc = RemoteIDBroadcaster("d0")
        msg = bc.build_message(34.9, 126.9, 10.0, 3.0, 0.0)
        bc.broadcast(msg)
        bc.broadcast(msg)
        assert bc.stats.total_sent == 2
        assert bc.stats.success_rate == 1.0


# ── P694: RTK GPS 핸들러 ─────────────────────────────────────────────
class TestRTKGPSHandler:
    def test_build_and_parse_fake_frame(self):
        from simulation.rtk_gps_handler import RTKGPSHandler, RTCM3_MSG_1074
        h = RTKGPSHandler("drone_0")
        raw = h.build_fake_rtcm_frame(RTCM3_MSG_1074)
        frame = h.ingest_rtcm(raw)
        assert frame is not None
        assert frame.crc_valid

    def test_invalid_frame_rejected(self):
        from simulation.rtk_gps_handler import RTKGPSHandler
        h = RTKGPSHandler("drone_0")
        frame = h.ingest_rtcm(b"\x00\x00\x00")
        assert frame is None
        assert h.stats.crc_errors == 1

    def test_position_callback(self):
        from simulation.rtk_gps_handler import RTKGPSHandler, RTKPosition, FixType
        h = RTKGPSHandler("drone_0")
        received = []
        h.register_position_callback(lambda did, pos: received.append((did, pos)))

        pos = RTKPosition(lat=34.9, lon=126.9, alt=30.0,
                          fix_type=FixType.RTK_FIXED, h_accuracy=0.02, v_accuracy=0.05)
        h.update_position(pos)

        assert len(received) == 1
        assert received[0][0] == "drone_0"
        assert received[0][1].is_rtk_fixed

    def test_stats_tracking(self):
        from simulation.rtk_gps_handler import RTKGPSHandler
        h = RTKGPSHandler("d0")
        raw = h.build_fake_rtcm_frame()
        h.ingest_rtcm(raw)
        h.ingest_rtcm(b"\xFF")   # invalid
        assert h.stats.total_frames == 2
        assert h.stats.valid_frames == 1


# ── P695: Failsafe 관리자 ────────────────────────────────────────────
class TestFailsafeManager:
    def test_trigger_rtl(self):
        from simulation.failsafe_manager import FailsafeManager, FailsafeTrigger, FailsafeLevel
        mgr = FailsafeManager()
        evt = mgr.trigger("d0", FailsafeTrigger.GPS_LOSS, "GPS satellite count low")
        assert evt.level == FailsafeLevel.RTL
        assert mgr.get_level("d0") == FailsafeLevel.RTL

    def test_battery_critical_emergency_land(self):
        from simulation.failsafe_manager import FailsafeManager, FailsafeTrigger, FailsafeLevel
        mgr = FailsafeManager()
        mgr.trigger("d0", FailsafeTrigger.BATTERY_CRITICAL)
        assert mgr.get_level("d0") == FailsafeLevel.EMERGENCY_LAND

    def test_level_only_increases(self):
        from simulation.failsafe_manager import FailsafeManager, FailsafeTrigger, FailsafeLevel
        mgr = FailsafeManager()
        mgr.trigger("d0", FailsafeTrigger.BATTERY_CRITICAL)   # Level 5
        mgr.trigger("d0", FailsafeTrigger.SENSOR_FAILURE)     # Level 1 — 하락 없음
        assert mgr.get_level("d0") == FailsafeLevel.EMERGENCY_LAND

    def test_callback_invoked(self):
        from simulation.failsafe_manager import FailsafeManager, FailsafeTrigger
        mgr = FailsafeManager()
        events = []
        mgr.register_callback(events.append)
        mgr.trigger("d0", FailsafeTrigger.COMM_LOSS)
        assert len(events) == 1

    def test_clear_and_nominal(self):
        from simulation.failsafe_manager import FailsafeManager, FailsafeTrigger, FailsafeLevel
        mgr = FailsafeManager()
        mgr.trigger("d0", FailsafeTrigger.SENSOR_FAILURE)
        mgr.clear("d0", FailsafeTrigger.SENSOR_FAILURE)
        assert mgr.get_level("d0") == FailsafeLevel.NOMINAL

    def test_active_failsafes_list(self):
        from simulation.failsafe_manager import FailsafeManager, FailsafeTrigger
        mgr = FailsafeManager()
        mgr.trigger("d0", FailsafeTrigger.COMM_LOSS)
        assert "d0" in mgr.active_failsafes()


# ── P696: 스웜 시간 동기화 ───────────────────────────────────────────
class TestSwarmTimeSync:
    def test_sync_reduces_offset(self):
        from simulation.swarm_time_sync import SwarmTimeSyncManager
        rng = np.random.default_rng(42)
        mgr = SwarmTimeSyncManager(rng=rng)
        mgr.register_drone("d0", initial_offset_ms=50.0)
        mgr.step_master(0.1)
        for _ in range(20):
            mgr.simulate_sync_round("d0", network_delay_ms=1.0)
            mgr.step_master(0.1)
        clock = mgr.get_clock("d0")
        assert abs(clock.offset_ms) < 50.0   # 오프셋이 줄어야 함

    def test_jitter_target(self):
        from simulation.swarm_time_sync import SwarmTimeSyncManager, SYNC_JITTER_TARGET_MS
        rng = np.random.default_rng(0)
        mgr = SwarmTimeSyncManager(rng=rng)
        mgr.register_drone("d0", initial_offset_ms=0.0)
        for _ in range(50):
            mgr.simulate_sync_round("d0", network_delay_ms=0.5)
            mgr.step_master(0.1)
        clock = mgr.get_clock("d0")
        assert clock.jitter_ms <= SYNC_JITTER_TARGET_MS

    def test_summary_keys(self):
        from simulation.swarm_time_sync import SwarmTimeSyncManager
        mgr = SwarmTimeSyncManager()
        mgr.register_drone("d0")
        summary = mgr.summary()
        assert "d0" in summary
        assert "offset_ms" in summary["d0"]

    def test_reproducibility(self):
        from simulation.swarm_time_sync import SwarmTimeSyncManager
        def run(seed: int) -> float:
            rng = np.random.default_rng(seed)
            mgr = SwarmTimeSyncManager(rng=rng)
            mgr.register_drone("d0", initial_offset_ms=10.0)
            for _ in range(5):
                mgr.simulate_sync_round("d0")
                mgr.step_master(0.1)
            return mgr.get_clock("d0").offset_ms

        assert run(7) == run(7)     # 동일 시드 → 동일 결과


# ── P697: MoCap HITL 브릿지 ──────────────────────────────────────────
class TestMocapHITLBridge:
    def test_vrpn_to_mavlink(self):
        from simulation.mocap_hitl_bridge import MocapHITLBridge, VRPNPose, MocapSystem
        bridge = MocapHITLBridge(system=MocapSystem.VICON)
        pose = VRPNPose("drone_0", x=1.0, y=2.0, z=3.0,
                        qw=1.0, qx=0.0, qy=0.0, qz=0.0)
        msg = bridge.ingest_vrpn(pose)
        assert msg.q == (1.0, 0.0, 0.0, 0.0)
        assert bridge.message_count == 1

    def test_callback_invoked(self):
        from simulation.mocap_hitl_bridge import MocapHITLBridge, VRPNPose
        bridge = MocapHITLBridge()
        received = []
        bridge.register_output_callback(lambda name, msg: received.append(name))
        bridge.ingest_vrpn(VRPNPose("d0", 0, 0, 1.0))
        assert received == ["d0"]

    def test_mavlink_pack_length(self):
        from simulation.mocap_hitl_bridge import MocapHITLBridge, VRPNPose
        bridge = MocapHITLBridge()
        msg = bridge.ingest_vrpn(VRPNPose("d0", 0.0, 0.0, 0.0))
        packed = msg.pack()
        # Q(8) + 4f(16) + 21f(84) = 108 bytes
        assert len(packed) == 120   # Q(8)+4f(16)+3f(12)+21f(84)

    def test_status_keys(self):
        from simulation.mocap_hitl_bridge import MocapHITLBridge
        bridge = MocapHITLBridge()
        status = bridge.status()
        assert "system" in status and "rate_hz" in status


# ── P698: 야외 비행 시험 프레임워크 ──────────────────────────────────
class TestOutdoorFlightTest:
    def test_generate_formation_line(self):
        from simulation.outdoor_flight_test import generate_formation, FormationType
        offsets = generate_formation(FormationType.LINE, 3, spacing_m=5.0)
        assert len(offsets) == 3
        assert offsets[0] == (0.0, 0.0, 0.0)   # 리더는 원점

    def test_generate_formation_circle(self):
        from simulation.outdoor_flight_test import generate_formation, FormationType
        offsets = generate_formation(FormationType.CIRCLE, 4, spacing_m=5.0)
        assert len(offsets) == 4

    def test_synthetic_logs_count(self):
        from simulation.outdoor_flight_test import (
            OutdoorFlightTestRunner, FlightTestConfig, FormationType,
        )
        runner = OutdoorFlightTestRunner(rng=np.random.default_rng(42))
        cfg = FlightTestConfig(n_drones=3, formation=FormationType.LINE,
                               test_duration_sec=10.0)
        logs = runner.generate_synthetic_logs(cfg)
        assert len(logs) == 3
        assert all(len(log.waypoints) == 10 for log in logs)

    def test_replay_no_violations(self):
        from simulation.outdoor_flight_test import (
            OutdoorFlightTestRunner, FlightTestConfig, FormationType,
        )
        runner = OutdoorFlightTestRunner(rng=np.random.default_rng(0))
        cfg = FlightTestConfig(n_drones=3, spacing_m=10.0, min_separation_m=3.0,
                               test_duration_sec=5.0)
        logs = runner.generate_synthetic_logs(cfg)
        result = runner.replay_gps_logs(logs, cfg)
        # 10m 간격에서 3m 최소 이격 → 위반 없어야 함
        assert result.separation_violations == 0

    def test_gps_point_distance(self):
        from simulation.outdoor_flight_test import GPSPoint
        p1 = GPSPoint(34.9, 126.9, 30.0)
        p2 = GPSPoint(34.9009, 126.9, 30.0)    # 북쪽 약 100m
        dist = p1.distance_to(p2)
        assert 90 < dist < 110   # 약 100m


# ── P699: 환경 시나리오 ──────────────────────────────────────────────
class TestEnvironmentalScenario:
    def test_wind_above_threshold_switches_apf(self):
        from simulation.environmental_scenario import (
            EnvironmentState, WindState, APF_PARAMS_WINDY, WIND_APF_SWITCH_THRESHOLD_MS,
        )
        env = EnvironmentState(wind=WindState(speed_ms=WIND_APF_SWITCH_THRESHOLD_MS + 1.0))
        assert env.active_apf_params is APF_PARAMS_WINDY

    def test_nominal_wind_uses_normal_apf(self):
        from simulation.environmental_scenario import (
            EnvironmentState, WindState, APF_PARAMS_NOMINAL,
        )
        env = EnvironmentState(wind=WindState(speed_ms=5.0))
        assert env.active_apf_params is APF_PARAMS_NOMINAL

    def test_preset_strong_wind(self):
        from simulation.environmental_scenario import EnvironmentalScenarioRunner
        runner = EnvironmentalScenarioRunner(rng=np.random.default_rng(0))
        state = runner.apply_preset("strong_wind")
        assert state.wind.speed_ms > 10.0

    def test_preset_night_low_light(self):
        from simulation.environmental_scenario import EnvironmentalScenarioRunner, ConditionSeverity
        runner = EnvironmentalScenarioRunner()
        state = runner.apply_preset("night")
        assert state.light.severity in (ConditionSeverity.SEVERE, ConditionSeverity.EXTREME)

    def test_invalid_preset_raises(self):
        from simulation.environmental_scenario import EnvironmentalScenarioRunner
        runner = EnvironmentalScenarioRunner()
        with pytest.raises(ValueError):
            runner.apply_preset("__nonexistent__")

    def test_to_dict_keys(self):
        from simulation.environmental_scenario import EnvironmentalScenarioRunner
        runner = EnvironmentalScenarioRunner()
        state = runner.apply_preset("calm")
        d = state.to_dict()
        assert "wind_ms" in d and "severity" in d and "apf_mode" in d


# ── P700: HITL 보고서 생성 ───────────────────────────────────────────
class TestHITLReportGenerator:
    def test_default_fmea_count(self):
        from simulation.hitl_report_generator import HITLReportGenerator, DEFAULT_FMEA_ITEMS
        gen = HITLReportGenerator()
        report = gen.build()
        assert len(report.fmea_items) == len(DEFAULT_FMEA_ITEMS) == 8

    def test_add_test_result(self):
        from simulation.hitl_report_generator import HITLReportGenerator
        gen = HITLReportGenerator()
        gen.add_test("T01", "모터 고장 Failsafe", passed=True, duration_sec=2.5)
        report = gen.build()
        assert len(report.hitl_results) == 1
        assert report.pass_rate == 1.0

    def test_pass_rate_calculation(self):
        from simulation.hitl_report_generator import HITLReportGenerator
        gen = HITLReportGenerator()
        gen.add_test("T01", "테스트A", passed=True, duration_sec=1.0)
        gen.add_test("T02", "테스트B", passed=False, duration_sec=1.0)
        assert gen.build().pass_rate == pytest.approx(0.5)

    def test_to_json_valid(self):
        import json
        from simulation.hitl_report_generator import HITLReportGenerator
        gen = HITLReportGenerator()
        json_str = gen.build().to_json()
        data = json.loads(json_str)
        assert "fmea_items" in data and "hitl_summary" in data

    def test_to_markdown_contains_table(self):
        from simulation.hitl_report_generator import HITLReportGenerator
        gen = HITLReportGenerator()
        md = gen.build().to_markdown()
        assert "FMEA" in md and "|" in md

    def test_mark_mitigated(self):
        from simulation.hitl_report_generator import HITLReportGenerator
        gen = HITLReportGenerator()
        gen.mark_fmea_mitigated("F01")
        report = gen.build()
        f01 = next(i for i in report.fmea_items if i.id == "F01")
        assert f01.mitigation_implemented is True

    def test_rpn_range(self):
        from simulation.hitl_report_generator import DEFAULT_FMEA_ITEMS
        for item in DEFAULT_FMEA_ITEMS:
            assert 1 <= item.rpn <= 125   # 5*5*5 = 125 최대
