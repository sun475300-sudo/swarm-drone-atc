"""
Coverage boost tests for modules with 0% coverage.
Targets: swarm_summary, telemetry_aggregation_system, traffic_coordinator,
traffic_sign_recognition, video_streaming_system, wind_compensation_system,
wireless_communication_system, weather_adaptive_controller, zero_shot_adaptor,
ws_bridge.
"""

import time

import numpy as np
import pytest

# ── wind_compensation_system ────────────────────────────────────────────────

from simulation.wind_compensation_system import WindCompensationSystem, WindVector


class TestWindVector:
    def test_dataclass_fields(self):
        wv = WindVector(north_ms=1.0, east_ms=2.0, down_ms=3.0)
        assert wv.north_ms == 1.0
        assert wv.east_ms == 2.0
        assert wv.down_ms == 3.0


class TestWindCompensationSystem:
    def test_initial_wind_is_zero(self):
        wcs = WindCompensationSystem()
        assert wcs.current_wind == WindVector(0, 0, 0)

    def test_update_wind(self):
        wcs = WindCompensationSystem()
        new_wind = WindVector(5.0, 3.0, -1.0)
        wcs.update_wind(new_wind)
        assert wcs.current_wind is new_wind

    def test_compute_compensation_negates_wind(self):
        wcs = WindCompensationSystem()
        wcs.update_wind(WindVector(north_ms=2.0, east_ms=4.0, down_ms=1.0))
        velocity = np.array([10.0, 10.0, 10.0])
        comp = wcs.compute_compensation(velocity)
        # compensation = -[east, north, down]
        np.testing.assert_array_almost_equal(comp, np.array([-4.0, -2.0, -1.0]))

    def test_compute_compensation_zero_wind(self):
        wcs = WindCompensationSystem()
        comp = wcs.compute_compensation(np.zeros(3))
        np.testing.assert_array_almost_equal(comp, np.zeros(3))


# ── wireless_communication_system ───────────────────────────────────────────

from simulation.wireless_communication_system import WirelessCommunicationSystem


class TestWirelessCommunicationSystem:
    def test_establish_link_within_range(self):
        wcs = WirelessCommunicationSystem()
        assert wcs.establish_link("d1", "d2", 100.0) is True
        assert "d1_d2" in wcs.connections

    def test_establish_link_out_of_range(self):
        wcs = WirelessCommunicationSystem()
        assert wcs.establish_link("d1", "d2", 600.0) is False
        assert len(wcs.connections) == 0

    def test_establish_link_at_boundary(self):
        wcs = WirelessCommunicationSystem()
        # distance == max_range (500) is not > max_range, so link succeeds
        assert wcs.establish_link("d1", "d2", 500.0) is True
        # just over boundary fails
        assert wcs.establish_link("d3", "d4", 500.1) is False

    def test_connection_properties(self):
        wcs = WirelessCommunicationSystem()
        wcs.establish_link("d1", "d2", 200.0)
        conn = wcs.connections["d1_d2"]
        assert conn["snr"] == 30 - 200.0 / 20  # 20
        assert conn["latency"] == pytest.approx(200.0 / 300000 * 1000)
        assert conn["bandwidth"] == pytest.approx(100 * (1 - 200.0 / 500))

    def test_get_link_quality_existing(self):
        wcs = WirelessCommunicationSystem()
        wcs.establish_link("d1", "d2", 0.0)
        quality = wcs.get_link_quality("d1", "d2")
        assert quality == pytest.approx(1.0)

    def test_get_link_quality_nonexistent(self):
        wcs = WirelessCommunicationSystem()
        assert wcs.get_link_quality("x", "y") == 0.0


# ── swarm_summary ───────────────────────────────────────────────────────────

from simulation.swarm_summary import SwarmStatus, SwarmSummary


class TestSwarmStatus:
    def test_dataclass_fields(self):
        ss = SwarmStatus(total_drones=10, active_drones=5,
                         missions_completed=3, collisions_avoided=1)
        assert ss.total_drones == 10
        assert ss.active_drones == 5


class TestSwarmSummary:
    def test_add_drone(self):
        summary = SwarmSummary()
        summary.add_drone("drone_1")
        assert "drone_1" in summary.drones
        assert summary.drones["drone_1"]["status"] == "idle"
        assert summary.drones["drone_1"]["battery"] == 100.0

    def test_get_status_empty(self):
        summary = SwarmSummary()
        status = summary.get_status()
        assert status.total_drones == 0
        assert status.active_drones == 0
        assert status.missions_completed == 0

    def test_get_status_with_active_drones(self):
        summary = SwarmSummary()
        summary.add_drone("d1")
        summary.add_drone("d2")
        summary.drones["d1"]["status"] = "active"
        status = summary.get_status()
        assert status.total_drones == 2
        assert status.active_drones == 1

    def test_missions_counted(self):
        summary = SwarmSummary()
        summary.missions.append({"id": "m1"})
        summary.missions.append({"id": "m2"})
        status = summary.get_status()
        assert status.missions_completed == 2


# ── video_streaming_system ──────────────────────────────────────────────────

from simulation.video_streaming_system import VideoStreamingSystem, VideoFrame


class TestVideoStreamingSystem:
    def test_start_stream(self):
        vss = VideoStreamingSystem()
        vss.start_stream("d1")
        assert "d1" in vss.active_streams
        assert vss.stream_quality["d1"] == 80

    def test_send_frame(self):
        vss = VideoStreamingSystem()
        vss.start_stream("d1")
        frame = VideoFrame(frame_id="f1", drone_id="d1",
                           timestamp=1.0, resolution=(1920, 1080),
                           data=b"\x00")
        vss.send_frame("d1", frame)
        assert len(vss.active_streams["d1"]) == 1

    def test_send_frame_no_stream(self):
        vss = VideoStreamingSystem()
        frame = VideoFrame(frame_id="f1", drone_id="d1",
                           timestamp=1.0, resolution=(1920, 1080),
                           data=b"\x00")
        vss.send_frame("d1", frame)  # should not raise

    def test_adjust_quality(self):
        vss = VideoStreamingSystem()
        vss.start_stream("d1")
        vss.adjust_quality("d1", 0.5)
        assert vss.stream_quality["d1"] == 50

    def test_adjust_quality_no_stream(self):
        vss = VideoStreamingSystem()
        vss.adjust_quality("d1", 0.5)  # should not raise

    def test_get_stream_stats_active(self):
        vss = VideoStreamingSystem()
        vss.start_stream("d1")
        stats = vss.get_stream_stats("d1")
        assert stats["active"] is True
        assert stats["quality"] == 80
        assert stats["frames_sent"] == 0

    def test_get_stream_stats_inactive(self):
        vss = VideoStreamingSystem()
        stats = vss.get_stream_stats("d1")
        assert stats["active"] is False
        assert stats["quality"] == 0
        assert stats["frames_sent"] == 0

    def test_custom_max_bitrate(self):
        vss = VideoStreamingSystem(max_bitrate_mbps=20)
        assert vss.max_bitrate == 20


# ── telemetry_aggregation_system ────────────────────────────────────────────

from simulation.telemetry_aggregation_system import (
    TelemetryAggregationSystem,
    TelemetryPacket,
)


class TestTelemetryAggregationSystem:
    def test_ingest_packet(self):
        tas = TelemetryAggregationSystem()
        pkt = TelemetryPacket(drone_id="d1", data={"battery": 90},
                              timestamp=time.time())
        tas.ingest(pkt)
        assert len(tas.telemetry_buffer["d1"]) == 1

    def test_aggregate_empty(self):
        tas = TelemetryAggregationSystem()
        result = tas.aggregate("d1")
        assert result == {}

    def test_aggregate_recent_packets(self):
        tas = TelemetryAggregationSystem(aggregation_window_sec=60)
        now = time.time()
        for batt in [80, 90, 100]:
            tas.ingest(TelemetryPacket(
                drone_id="d1", data={"battery": batt}, timestamp=now))
        result = tas.aggregate("d1")
        assert result["avg_battery"] == pytest.approx(90.0)
        assert result["packet_count"] == 3

    def test_aggregate_filters_old_packets(self):
        tas = TelemetryAggregationSystem(aggregation_window_sec=10)
        old_time = time.time() - 100  # 100 seconds ago
        tas.ingest(TelemetryPacket(
            drone_id="d1", data={"battery": 50}, timestamp=old_time))
        result = tas.aggregate("d1")
        assert result == {}

    def test_aggregate_default_battery(self):
        tas = TelemetryAggregationSystem()
        now = time.time()
        tas.ingest(TelemetryPacket(
            drone_id="d1", data={}, timestamp=now))
        result = tas.aggregate("d1")
        assert result["avg_battery"] == pytest.approx(50.0)


# ── traffic_sign_recognition ────────────────────────────────────────────────

from simulation.traffic_sign_recognition import (
    TrafficSignRecognition,
    SignDetection,
    SignClass,
)


class TestTrafficSignRecognition:
    def test_init(self):
        tsr = TrafficSignRecognition()
        assert tsr.model_loaded is True
        assert len(tsr.sign_classes) == 5

    def test_detect_returns_list(self):
        rng = np.random.default_rng(seed=42)
        np.random.seed(42)  # module uses np.random directly
        tsr = TrafficSignRecognition()
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        detections = tsr.detect(image)
        assert isinstance(detections, list)
        for d in detections:
            assert isinstance(d, SignDetection)
            assert 1 <= d.sign_type <= 5
            assert 0.7 <= d.confidence <= 0.99

    def test_classify_sign(self):
        np.random.seed(42)
        tsr = TrafficSignRecognition()
        roi = np.zeros((50, 50, 3), dtype=np.uint8)
        result = tsr.classify_sign(roi)
        assert 1 <= result <= 5

    def test_sign_class_constants(self):
        assert SignClass.STOP == 1
        assert SignClass.YIELD == 2
        assert SignClass.SPEED_LIMIT == 3
        assert SignClass.NO_ENTRY == 4
        assert SignClass.WARNING == 5


# ── traffic_coordinator ─────────────────────────────────────────────────────

from simulation.traffic_coordinator import TrafficCoordinator, UAVTraffic


class TestTrafficCoordinator:
    def _make_uav(self, uav_id, pos, vel=None, dest=None):
        pos = np.array(pos, dtype=float)
        vel = np.zeros(3) if vel is None else np.array(vel, dtype=float)
        dest = np.zeros(3) if dest is None else np.array(dest, dtype=float)
        return UAVTraffic(uav_id=uav_id, position=pos, velocity=vel,
                          destination=dest)

    def test_register_uav(self):
        tc = TrafficCoordinator((0, 1000, 0, 1000, 0, 500))
        uav = self._make_uav("u1", [100, 200, 50])
        tc.register_uav(uav)
        assert "u1" in tc.uavs

    def test_detect_conflicts_none(self):
        tc = TrafficCoordinator((0, 1000, 0, 1000, 0, 500))
        tc.register_uav(self._make_uav("u1", [0, 0, 0]))
        tc.register_uav(self._make_uav("u2", [200, 200, 200]))
        conflicts = tc.detect_conflicts(separation_distance=50.0)
        assert len(conflicts) == 0

    def test_detect_conflicts_found(self):
        tc = TrafficCoordinator((0, 1000, 0, 1000, 0, 500))
        tc.register_uav(self._make_uav("u1", [10, 10, 10]))
        tc.register_uav(self._make_uav("u2", [15, 15, 15]))
        conflicts = tc.detect_conflicts(separation_distance=50.0)
        assert len(conflicts) == 1
        assert conflicts[0] == ("u1", "u2")

    def test_resolve_conflicts(self):
        tc = TrafficCoordinator((0, 1000, 0, 1000, 0, 500))
        tc.register_uav(self._make_uav("u1", [10, 10, 10]))
        tc.register_uav(self._make_uav("u2", [12, 12, 12]))
        tc.detect_conflicts(separation_distance=50.0)
        maneuvers = tc.resolve_conflicts()
        assert "u1" in maneuvers
        assert "u2" in maneuvers
        # Maneuvers should be in opposite directions
        np.testing.assert_array_almost_equal(
            maneuvers["u1"], -maneuvers["u2"])

    def test_resolve_no_conflicts(self):
        tc = TrafficCoordinator((0, 1000, 0, 1000, 0, 500))
        maneuvers = tc.resolve_conflicts()
        assert maneuvers == {}

    def test_get_traffic_density(self):
        tc = TrafficCoordinator((0, 1000, 0, 1000, 0, 500))
        tc.register_uav(self._make_uav("u1", [50, 50, 0]))
        tc.register_uav(self._make_uav("u2", [150, 150, 0]))
        tc.register_uav(self._make_uav("u3", [500, 500, 0]))
        # region covers x=[0,200], y=[0,200]
        density = tc.get_traffic_density((0, 200, 0, 200))
        assert density == 2

    def test_get_traffic_density_empty(self):
        tc = TrafficCoordinator((0, 1000, 0, 1000, 0, 500))
        density = tc.get_traffic_density((0, 100, 0, 100))
        assert density == 0


# ── weather_adaptive_controller ─────────────────────────────────────────────

from simulation.weather_adaptive_controller import (
    WeatherAdaptiveController,
    WeatherCondition,
)


class TestWeatherAdaptiveController:
    def _make_weather(self, wind=3.0, precipitation=0.0):
        return WeatherCondition(
            temperature_c=20.0, wind_speed_ms=wind,
            wind_direction_deg=180.0, humidity_percent=50.0,
            pressure_hpa=1013.0, visibility_m=10000.0,
            precipitation_mmh=precipitation)

    def test_no_weather_returns_empty(self):
        wac = WeatherAdaptiveController()
        assert wac.compute_adapted_parameters() == {}

    def test_calm_weather_params(self):
        wac = WeatherAdaptiveController()
        wac.update_weather(self._make_weather(wind=3.0))
        params = wac.compute_adapted_parameters()
        assert params["velocity_scale"] == 1.0
        assert params["path_margin"] == 1.0
        assert params["battery_buffer"] == 1.0
        assert params["control_gain"] == 1.0

    def test_moderate_wind_params(self):
        wac = WeatherAdaptiveController()
        wac.update_weather(self._make_weather(wind=7.0))
        params = wac.compute_adapted_parameters()
        assert params["velocity_scale"] == 0.85
        assert params["control_gain"] == 1.1

    def test_strong_wind_params(self):
        wac = WeatherAdaptiveController()
        wac.update_weather(self._make_weather(wind=15.0))
        params = wac.compute_adapted_parameters()
        assert params["velocity_scale"] == 0.7
        assert params["battery_buffer"] == 1.3

    def test_precipitation_modifier(self):
        wac = WeatherAdaptiveController()
        wac.update_weather(self._make_weather(wind=3.0, precipitation=5.0))
        params = wac.compute_adapted_parameters()
        assert params["velocity_scale"] == pytest.approx(1.0 * 0.8)
        assert params["battery_buffer"] == pytest.approx(1.0 * 1.2)

    def test_adaptation_history_recorded(self):
        wac = WeatherAdaptiveController()
        wac.update_weather(self._make_weather())
        wac.compute_adapted_parameters()
        assert len(wac.adaptation_history) == 1

    def test_predict_weather_trend_stable(self):
        wac = WeatherAdaptiveController()
        history = [self._make_weather(wind=w) for w in [3.0, 3.5, 3.2]]
        assert wac.predict_weather_trend(history) == "stable"

    def test_predict_weather_trend_changing(self):
        wac = WeatherAdaptiveController()
        history = [self._make_weather(wind=w) for w in [3.0, 7.0, 12.0]]
        assert wac.predict_weather_trend(history) == "changing"

    def test_predict_weather_trend_short_history(self):
        wac = WeatherAdaptiveController()
        history = [self._make_weather(wind=3.0)]
        assert wac.predict_weather_trend(history) == "stable"


# ── zero_shot_adaptor ───────────────────────────────────────────────────────

from simulation.zero_shot_adaptor import (
    ZeroShotAdaptor,
    TaskDescriptor,
    TaskDomain,
    AdaptationResult,
)


class TestZeroShotAdaptor:
    def test_init(self):
        adaptor = ZeroShotAdaptor(confidence_threshold=0.5)
        assert len(adaptor.capability_embeddings) == 8
        assert len(adaptor.adaptation_strategies) == 4

    def test_describe_task(self):
        adaptor = ZeroShotAdaptor()
        task = TaskDescriptor(
            domain=TaskDomain.DETECTION,
            description="detect obstacles ahead",
            required_capabilities=["collision_detection"],
            constraints={"max_latency": 100})
        result = adaptor.describe_task(task)
        assert result["domain"] == "detection"
        assert "relevant_capabilities" in result
        assert result["complexity"] in ("low", "medium", "high")

    def test_estimate_complexity_low(self):
        adaptor = ZeroShotAdaptor()
        task = TaskDescriptor(
            domain=TaskDomain.DETECTION,
            description="simple task",
            required_capabilities=["one"],
            constraints={})
        assert adaptor._estimate_complexity(task) == "low"

    def test_estimate_complexity_high(self):
        adaptor = ZeroShotAdaptor()
        task = TaskDescriptor(
            domain=TaskDomain.DETECTION,
            description="complex task",
            required_capabilities=["a", "b", "c", "d", "e", "f", "g"],
            constraints={"a": 1, "b": 2, "c": 3})
        assert adaptor._estimate_complexity(task) == "high"

    def test_adapt_detection(self):
        adaptor = ZeroShotAdaptor(confidence_threshold=0.5)
        task = TaskDescriptor(
            domain=TaskDomain.DETECTION,
            description="detect drones",
            required_capabilities=["collision_detection"],
            constraints={})
        result = adaptor.adapt(task)
        assert isinstance(result, AdaptationResult)
        assert result.confidence > 0
        assert "model_type" in result.output

    def test_adapt_tracking(self):
        adaptor = ZeroShotAdaptor(confidence_threshold=0.5)
        task = TaskDescriptor(
            domain=TaskDomain.TRACKING,
            description="track objects",
            required_capabilities=[],
            constraints={})
        result = adaptor.adapt(task)
        assert "tracker_type" in result.output

    def test_adapt_navigation(self):
        adaptor = ZeroShotAdaptor(confidence_threshold=0.5)
        task = TaskDescriptor(
            domain=TaskDomain.NAVIGATION,
            description="navigate path",
            required_capabilities=[],
            constraints={})
        result = adaptor.adapt(task)
        assert "planner_type" in result.output

    def test_adapt_obstacle_avoidance(self):
        adaptor = ZeroShotAdaptor(confidence_threshold=0.5)
        task = TaskDescriptor(
            domain=TaskDomain.OBSTACLE_AVOIDANCE,
            description="avoid obstacles",
            required_capabilities=[],
            constraints={})
        result = adaptor.adapt(task)
        assert "method" in result.output
        assert result.output["method"] == "apf"

    def test_get_adaptation_stats_empty(self):
        adaptor = ZeroShotAdaptor()
        stats = adaptor.get_adaptation_stats()
        assert stats["total_tasks"] == 0

    def test_get_adaptation_stats_after_tasks(self):
        adaptor = ZeroShotAdaptor(confidence_threshold=0.5)
        for domain in [TaskDomain.DETECTION, TaskDomain.TRACKING]:
            task = TaskDescriptor(
                domain=domain, description="test",
                required_capabilities=[], constraints={})
            adaptor.adapt(task)
        stats = adaptor.get_adaptation_stats()
        assert stats["total_tasks"] == 2
        assert stats["success_rate"] > 0

    def test_calculate_confidence_with_error(self):
        adaptor = ZeroShotAdaptor()
        conf = adaptor._calculate_confidence(
            {"complexity": "low", "relevant_capabilities": []},
            {"error": "test"})
        assert conf == 0.0

    def test_encode_description(self):
        adaptor = ZeroShotAdaptor()
        emb = adaptor._encode_description("collision_detection test")
        assert emb.shape == (128,)
        assert not np.all(emb == 0)


# ── ws_bridge (argument parser only — no network) ──────────────────────────

from simulation.ws_bridge import main as ws_main


class TestWsBridge:
    def test_module_importable(self):
        """Verify the ws_bridge module can be imported without side effects."""
        import simulation.ws_bridge
        assert hasattr(simulation.ws_bridge, "_run_simulation")
        assert hasattr(simulation.ws_bridge, "main")
