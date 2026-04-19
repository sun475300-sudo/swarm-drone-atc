"""Phase 671-680: Hardware Integration 모듈 테스트."""

import numpy as np
import pytest


# ── PX4 SITL Bridge ────────────────────────────────────────────────────
class TestPX4SITLBridge:
    def test_connect(self):
        from simulation.px4_sitl_bridge import PX4SITLBridge
        bridge = PX4SITLBridge()
        assert bridge.connect("127.0.0.1", 14540)
        assert bridge.connected

    def test_disconnect(self):
        from simulation.px4_sitl_bridge import PX4SITLBridge
        bridge = PX4SITLBridge()
        bridge.connect()
        bridge.disconnect()
        assert not bridge.connected

    def test_arm_disarm(self):
        from simulation.px4_sitl_bridge import PX4SITLBridge
        bridge = PX4SITLBridge()
        bridge.connect()
        assert bridge.arm_drone("d1")
        state = bridge.get_vehicle_state("d1")
        assert state["armed"] is True
        bridge.disarm_drone("d1")
        state = bridge.get_vehicle_state("d1")
        assert state["armed"] is False

    def test_set_mode(self):
        from simulation.px4_sitl_bridge import PX4SITLBridge
        bridge = PX4SITLBridge()
        bridge.connect()
        bridge.arm_drone("d1")
        assert bridge.set_mode("d1", "GUIDED")
        state = bridge.get_vehicle_state("d1")
        assert state["mode"] == "GUIDED"

    def test_set_invalid_mode(self):
        from simulation.px4_sitl_bridge import PX4SITLBridge
        bridge = PX4SITLBridge()
        bridge.connect()
        assert not bridge.set_mode("d1", "INVALID_MODE")

    def test_send_waypoint(self):
        from simulation.px4_sitl_bridge import PX4SITLBridge
        bridge = PX4SITLBridge()
        bridge.connect()
        bridge.arm_drone("d1")
        assert bridge.send_waypoint("d1", 37.5, 127.0, 50.0)

    def test_receive_telemetry(self):
        from simulation.px4_sitl_bridge import PX4SITLBridge
        bridge = PX4SITLBridge()
        bridge.connect()
        bridge.arm_drone("d1")
        msg = bridge.receive_telemetry()
        assert msg is not None
        assert msg.msg_type in ("GLOBAL_POSITION_INT", "HEARTBEAT")

    def test_not_connected_fails(self):
        from simulation.px4_sitl_bridge import PX4SITLBridge
        bridge = PX4SITLBridge()
        assert not bridge.arm_drone("d1")
        assert bridge.receive_telemetry() is None

    def test_connection_stats(self):
        from simulation.px4_sitl_bridge import PX4SITLBridge
        bridge = PX4SITLBridge()
        bridge.connect()
        bridge.arm_drone("d1")
        stats = bridge.get_connection_stats()
        assert stats["connected"] is True
        assert stats["msgs_sent"] >= 1

    def test_send_command(self):
        from simulation.px4_sitl_bridge import PX4SITLBridge
        bridge = PX4SITLBridge()
        bridge.connect()
        assert bridge.send_command("MAV_CMD_NAV_TAKEOFF", {"alt": 10})


# ── ROS2 Bridge ─────────────────────────────────────────────────────────
class TestROS2Bridge:
    def test_create_publisher(self):
        from simulation.ros2_bridge import ROS2Bridge
        bridge = ROS2Bridge()
        pub_id = bridge.create_publisher("/drone/pose", "geometry_msgs/PoseStamped")
        assert pub_id > 0

    def test_publish_and_subscribe(self):
        from simulation.ros2_bridge import ROS2Bridge
        bridge = ROS2Bridge()
        received = []
        pub_id = bridge.create_publisher("/drone/pose")
        bridge.create_subscriber("/drone/pose", lambda m: received.append(m))
        bridge.publish(pub_id, {"x": 1.0, "y": 2.0})
        bridge.spin_once()
        assert len(received) == 1

    def test_service_call(self):
        from simulation.ros2_bridge import ROS2Bridge
        bridge = ROS2Bridge()
        bridge.create_service("get_state", lambda req: {"state": "ok"})
        resp = bridge.call_service("get_state", {})
        assert resp == {"state": "ok"}

    def test_service_not_found(self):
        from simulation.ros2_bridge import ROS2Bridge
        bridge = ROS2Bridge()
        assert bridge.call_service("missing", {}) is None

    def test_topic_list(self):
        from simulation.ros2_bridge import ROS2Bridge
        bridge = ROS2Bridge()
        bridge.create_publisher("/a")
        bridge.create_subscriber("/b", lambda m: None)
        topics = bridge.get_topic_list()
        assert "/a" in topics and "/b" in topics

    def test_tf_transform(self):
        from simulation.ros2_bridge import ROS2Bridge, TFTransform
        bridge = ROS2Bridge()
        tf = TFTransform(
            parent_frame="world", child_frame="drone_1",
            translation=np.array([1.0, 2.0, 3.0]),
            rotation=np.array([0.0, 0.0, 0.0, 1.0]),
        )
        bridge.set_transform(tf)
        result = bridge.lookup_transform("world", "drone_1")
        assert result is not None
        np.testing.assert_array_equal(result.translation, [1.0, 2.0, 3.0])

    def test_node_stats(self):
        from simulation.ros2_bridge import ROS2Bridge
        bridge = ROS2Bridge()
        bridge.create_publisher("/test")
        stats = bridge.get_node_stats()
        assert stats["publishers"] == 1

    def test_publish_invalid_id(self):
        from simulation.ros2_bridge import ROS2Bridge
        bridge = ROS2Bridge()
        assert not bridge.publish(999, {"x": 0})


# ── MQTT/DDS Bridge ─────────────────────────────────────────────────────
class TestMQTTClient:
    def test_connect(self):
        from simulation.mqtt_dds_bridge import MQTTClient
        client = MQTTClient()
        assert client.connect()
        assert client.connected

    def test_publish(self):
        from simulation.mqtt_dds_bridge import MQTTClient
        client = MQTTClient()
        client.connect()
        assert client.publish("drone/telemetry", {"alt": 50})

    def test_publish_not_connected(self):
        from simulation.mqtt_dds_bridge import MQTTClient
        client = MQTTClient()
        assert not client.publish("topic", {})

    def test_subscribe_callback(self):
        from simulation.mqtt_dds_bridge import MQTTClient
        client = MQTTClient()
        client.connect()
        received = []
        client.subscribe("test", lambda m: received.append(m))
        client.publish("test", {"v": 1})
        assert len(received) == 1

    def test_stats(self):
        from simulation.mqtt_dds_bridge import MQTTClient
        client = MQTTClient()
        client.connect()
        client.publish("t", {})
        stats = client.get_stats()
        assert stats["msgs_sent"] == 1


class TestDDSParticipant:
    def test_create_writer(self):
        from simulation.mqtt_dds_bridge import DDSParticipant
        dds = DDSParticipant()
        wid = dds.create_writer("drone_state", "DroneState")
        assert wid > 0

    def test_write_and_read(self):
        from simulation.mqtt_dds_bridge import DDSParticipant
        dds = DDSParticipant()
        received = []
        wid = dds.create_writer("state")
        dds.create_reader("state", lambda d: received.append(d))
        dds.write(wid, {"pos": [1, 2, 3]})
        assert len(received) == 1

    def test_write_invalid_id(self):
        from simulation.mqtt_dds_bridge import DDSParticipant
        dds = DDSParticipant()
        assert not dds.write(999, {})

    def test_stats(self):
        from simulation.mqtt_dds_bridge import DDSParticipant
        dds = DDSParticipant()
        wid = dds.create_writer("t")
        dds.write(wid, {})
        stats = dds.get_stats()
        assert stats["samples_written"] == 1


class TestMQTTDDSBridge:
    def test_setup(self):
        from simulation.mqtt_dds_bridge import MQTTDDSBridge
        bridge = MQTTDDSBridge()
        assert bridge.setup()

    def test_publish_hybrid(self):
        from simulation.mqtt_dds_bridge import MQTTDDSBridge
        bridge = MQTTDDSBridge()
        bridge.setup()
        result = bridge.publish_hybrid("drone/pos", {"x": 1})
        assert result["mqtt"] is True
        assert result["dds"] is True

    def test_combined_stats(self):
        from simulation.mqtt_dds_bridge import MQTTDDSBridge
        bridge = MQTTDDSBridge()
        bridge.setup()
        bridge.publish_hybrid("t", {})
        stats = bridge.get_combined_stats()
        assert "mqtt" in stats and "dds" in stats


# ── Flight Test Framework ───────────────────────────────────────────────
class TestFlightTestFramework:
    def test_builtin_tests_registered(self):
        from simulation.flight_test_framework import FlightTestRunner
        runner = FlightTestRunner()
        assert "hover_stability" in runner.tests
        assert "waypoint_navigation" in runner.tests
        assert "emergency_landing" in runner.tests
        assert "collision_avoidance" in runner.tests
        assert "wind_resistance" in runner.tests

    def test_run_hover_stability(self):
        from simulation.flight_test_framework import FlightTestRunner
        runner = FlightTestRunner()
        result = runner.run_test("hover_stability")
        assert result.test_name == "hover_stability"
        assert "max_drift_m" in result.metrics

    def test_run_all(self):
        from simulation.flight_test_framework import FlightTestRunner
        runner = FlightTestRunner()
        results = runner.run_all()
        assert len(results) == 5

    def test_run_nonexistent(self):
        from simulation.flight_test_framework import FlightTestRunner
        runner = FlightTestRunner()
        result = runner.run_test("nonexistent")
        assert not result.passed
        assert len(result.errors) > 0

    def test_summary(self):
        from simulation.flight_test_framework import FlightTestRunner
        runner = FlightTestRunner()
        runner.run_all()
        summary = runner.get_summary()
        assert summary["total"] == 5
        assert summary["passed"] + summary["failed"] == 5

    def test_register_custom_test(self):
        from simulation.flight_test_framework import FlightTestRunner, TestCase
        runner = FlightTestRunner()
        runner.register_test(TestCase(name="custom", description="Custom test"))
        result = runner.run_test("custom")
        assert result.test_name == "custom"

    def test_run_by_tag(self):
        from simulation.flight_test_framework import FlightTestRunner
        runner = FlightTestRunner()
        results = runner.run_by_tag("safety")
        assert len(results) == 2  # emergency_landing + collision_avoidance


# ── Jetson Edge Deployer ────────────────────────────────────────────────
class TestJetsonEdgeDeployer:
    def test_register_device(self):
        from simulation.jetson_edge_deployer import JetsonEdgeDeployer
        deployer = JetsonEdgeDeployer()
        dev_id = deployer.register_device()
        assert dev_id > 0

    def test_optimize_model(self):
        from simulation.jetson_edge_deployer import JetsonEdgeDeployer
        deployer = JetsonEdgeDeployer()
        profile = deployer.optimize_model("collision_detector", "jetson_nano", "fp16")
        assert "fp16" in profile.name
        assert profile.size_mb > 0

    def test_deploy_model(self):
        from simulation.jetson_edge_deployer import JetsonEdgeDeployer
        deployer = JetsonEdgeDeployer()
        dev_id = deployer.register_device()
        profile = deployer.optimize_model("model_a", "jetson_nano")
        assert deployer.deploy_model(dev_id, profile)

    def test_deploy_exceeds_memory(self):
        from simulation.jetson_edge_deployer import JetsonEdgeDeployer, EdgeDeviceConfig, ModelProfile
        deployer = JetsonEdgeDeployer()
        config = EdgeDeviceConfig(device_type="tiny", memory_mb=1)
        dev_id = deployer.register_device(config)
        big_model = ModelProfile(name="big", size_mb=100, inference_time_ms=10, accuracy=0.9)
        assert not deployer.deploy_model(dev_id, big_model)

    def test_run_inference(self):
        from simulation.jetson_edge_deployer import JetsonEdgeDeployer
        deployer = JetsonEdgeDeployer()
        dev_id = deployer.register_device()
        profile = deployer.optimize_model("model_a", "jetson_nano")
        deployer.deploy_model(dev_id, profile)
        result = deployer.run_inference(dev_id, np.zeros(10))
        assert result is not None
        assert "latency_ms" in result

    def test_run_inference_no_model(self):
        from simulation.jetson_edge_deployer import JetsonEdgeDeployer
        deployer = JetsonEdgeDeployer()
        dev_id = deployer.register_device()
        assert deployer.run_inference(dev_id, np.zeros(10)) is None

    def test_device_stats(self):
        from simulation.jetson_edge_deployer import JetsonEdgeDeployer
        deployer = JetsonEdgeDeployer()
        dev_id = deployer.register_device()
        stats = deployer.get_device_stats(dev_id)
        assert stats["device_type"] == "jetson_nano"

    def test_benchmark(self):
        from simulation.jetson_edge_deployer import JetsonEdgeDeployer
        deployer = JetsonEdgeDeployer()
        dev_id = deployer.register_device()
        profile = deployer.optimize_model("model_a", "jetson_nano")
        deployer.deploy_model(dev_id, profile)
        bench = deployer.benchmark(dev_id)
        assert bench is not None
        assert bench["fps"] > 0

    def test_benchmark_no_model(self):
        from simulation.jetson_edge_deployer import JetsonEdgeDeployer
        deployer = JetsonEdgeDeployer()
        dev_id = deployer.register_device()
        assert deployer.benchmark(dev_id) is None

    def test_quantization_tradeoffs(self):
        from simulation.jetson_edge_deployer import JetsonEdgeDeployer
        deployer = JetsonEdgeDeployer()
        fp32 = deployer.optimize_model("m", "jetson_orin", "fp32")
        int8 = deployer.optimize_model("m", "jetson_orin", "int8")
        assert int8.size_mb < fp32.size_mb
