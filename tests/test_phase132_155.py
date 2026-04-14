"""Phase 132-155 테스트: 드론팩토리~시스템대시보드 (24 모듈, 104 테스트)"""
import pytest
import numpy as np


# ── Phase 132-139 ──────────────────────────────────────────

class TestDroneFactory:
    def setup_method(self):
        from simulation.drone_factory import DroneFactory
        self.f = DroneFactory()

    def test_create_delivery(self):
        spec = self.f.create("DELIVERY")
        assert spec.drone_type == "DELIVERY"
        assert spec.max_speed_ms > 0

    def test_create_agriculture(self):
        spec = self.f.create("AGRICULTURE")
        assert spec.payload_kg > 0

    def test_all_types(self):
        for t in self.f.available_types():
            spec = self.f.create(t)
            assert spec.drone_type == t

    def test_summary(self):
        self.f.create("DELIVERY")
        s = self.f.summary()
        assert s["total_created"] >= 1


class TestRealtimeRebalancer:
    def setup_method(self):
        from simulation.realtime_rebalancer import RealtimeRebalancer
        self.r = RealtimeRebalancer(grid_size=5)

    def test_update_positions(self):
        self.r.update_positions({"d1": (50, 50, 50), "d2": (900, 900, 50)})
        s = self.r.summary()
        assert s["drones"] >= 2

    def test_rebalance_empty(self):
        actions = self.r.rebalance()
        assert isinstance(actions, list)

    def test_rebalance_imbalanced(self):
        positions = {f"d{i}": (10.0, 10.0, 50.0) for i in range(10)}
        self.r.update_positions(positions)
        actions = self.r.rebalance()
        assert isinstance(actions, list)

    def test_summary(self):
        s = self.r.summary()
        assert "drones" in s


class TestBatteryDegradation:
    def setup_method(self):
        from simulation.battery_degradation import BatteryDegradation
        self.b = BatteryDegradation()

    def test_register(self):
        self.b.register_battery("b1", initial_capacity=80.0)
        soh = self.b.state_of_health("b1")
        assert soh == 100.0

    def test_cycle(self):
        self.b.register_battery("b1", initial_capacity=80.0)
        self.b.record_cycle("b1", depth=0.8, temp_c=25)
        soh = self.b.state_of_health("b1")
        assert soh <= 100.0

    def test_degradation_increases(self):
        self.b.register_battery("b1", initial_capacity=80.0)
        for _ in range(50):
            self.b.record_cycle("b1", depth=1.0, temp_c=45)
        soh = self.b.state_of_health("b1")
        assert soh < 100.0

    def test_summary(self):
        self.b.register_battery("b1")
        s = self.b.summary()
        assert s["batteries"] >= 1


class TestWindTunnel:
    def setup_method(self):
        from simulation.wind_tunnel import WindTunnel
        self.w = WindTunnel()

    def test_add_building(self):
        self.w.add_building((100, 100), width=50, height=80)
        s = self.w.summary()
        assert s["buildings"] >= 1

    def test_wind_at_open(self):
        wind = self.w.wind_at((500, 500, 50))
        assert len(wind) == 3

    def test_shelter_effect(self):
        self.w.add_building((100, 100), width=50, height=80)
        sheltered = self.w.is_sheltered((100, 130, 30))
        assert isinstance(sheltered, bool)

    def test_summary(self):
        s = self.w.summary()
        assert "buildings" in s


class TestLandingNetwork:
    def setup_method(self):
        from simulation.landing_network import LandingNetwork
        self.l = LandingNetwork()

    def test_add_pad(self):
        self.l.add_pad("p1", (100, 200), capacity=3)
        s = self.l.summary()
        assert s["pads"] >= 1

    def test_recommend(self):
        self.l.add_pad("p1", (100, 200), capacity=3)
        self.l.add_pad("p2", (500, 500), capacity=2)
        rec = self.l.recommend_pad((120, 210))
        assert rec is not None

    def test_land_depart(self):
        self.l.add_pad("p1", (100, 200), capacity=1)
        ok = self.l.land("p1", "d1")
        assert ok
        self.l.depart("p1")

    def test_summary(self):
        s = self.l.summary()
        assert "pads" in s


class TestGPSMultipath:
    def setup_method(self):
        from simulation.gps_multipath import GPSMultipath
        self.g = GPSMultipath(seed=42)

    def test_add_reflector(self):
        self.g.add_reflector((100, 100), height=80)
        s = self.g.summary()
        assert s["reflectors"] >= 1

    def test_measure(self):
        m = self.g.measure((500, 500, 100))
        assert m.error_m >= 0

    def test_hdop(self):
        self.g.add_reflector((100, 100), height=80, coeff=0.9)
        m = self.g.measure((100, 100, 50))
        assert m.hdop >= 1.0

    def test_summary(self):
        s = self.g.summary()
        assert "reflectors" in s


class TestDynamicObstacle:
    def setup_method(self):
        from simulation.dynamic_obstacle import DynamicObstacle
        self.d = DynamicObstacle()

    def test_add_obstacle(self):
        self.d.add_obstacle("bird1", pos=(100, 200, 50), velocity=(5, 0, 0))
        assert self.d.active_obstacles() >= 1

    def test_check_threats(self):
        self.d.add_obstacle("bird1", pos=(100, 200, 50), velocity=(-5, 0, 0))
        threats = self.d.check_threats(drone_pos=(200, 200, 50), drone_vel=(-5, 0, 0))
        assert isinstance(threats, list)

    def test_severity(self):
        self.d.add_obstacle("bird1", pos=(110, 200, 50), velocity=(-5, 0, 0))
        threats = self.d.check_threats(drone_pos=(120, 200, 50), drone_vel=(0, 0, 0))
        if threats:
            assert threats[0].severity in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    def test_summary(self):
        s = self.d.summary()
        assert "total_obstacles" in s


class TestPayloadManager:
    def setup_method(self):
        from simulation.payload_manager import PayloadManager
        self.p = PayloadManager()

    def test_load_cargo(self):
        self.p.register_drone("d1", max_payload_kg=5)
        ok = self.p.load_cargo("d1", cargo_id="c1", weight_kg=3)
        assert ok

    def test_overload(self):
        self.p.register_drone("d1", max_payload_kg=5)
        self.p.load_cargo("d1", cargo_id="c1", weight_kg=4)
        ok = self.p.load_cargo("d1", cargo_id="c2", weight_kg=3)
        assert not ok

    def test_performance_impact(self):
        self.p.register_drone("d1", max_payload_kg=5)
        self.p.load_cargo("d1", cargo_id="c1", weight_kg=4)
        impact = self.p.performance_impact("d1")
        assert impact.speed_reduction_pct > 0

    def test_summary(self):
        s = self.p.summary()
        assert "drones" in s


# ── Phase 140-147 ──────────────────────────────────────────

class TestMultiTenant:
    def setup_method(self):
        from simulation.multi_tenant import MultiTenant
        self.m = MultiTenant()

    def test_add_tenant(self):
        self.m.add_tenant("t1", max_drones=50)
        s = self.m.summary()
        assert s["tenants"] >= 1

    def test_assign_drone(self):
        self.m.add_tenant("t1", max_drones=50)
        ok = self.m.assign_drone("d1", "t1")
        assert ok

    def test_quota_exceeded(self):
        self.m.add_tenant("t1", max_drones=1)
        self.m.assign_drone("d1", "t1")
        ok = self.m.assign_drone("d2", "t1")
        assert not ok

    def test_summary(self):
        s = self.m.summary()
        assert "tenants" in s


class TestSLAContract:
    def setup_method(self):
        from simulation.sla_contract import SLAContract
        self.s = SLAContract()

    def test_add_contract(self):
        self.s.add_contract("c1", tier="GOLD")
        s = self.s.summary()
        assert s["contracts"] >= 1

    def test_record_performance(self):
        self.s.add_contract("c1", tier="GOLD", max_latency_s=5.0)
        self.s.record_performance("c1", latency_s=10.0)
        comp = self.s.compliance("c1")
        assert isinstance(comp, dict)

    def test_compliance(self):
        self.s.add_contract("c1", tier="PLATINUM")
        self.s.record_performance("c1", latency_s=1.0, available=True)
        comp = self.s.compliance("c1")
        assert isinstance(comp, dict)

    def test_summary(self):
        s = self.s.summary()
        assert "contracts" in s


class TestDroneLifecycle:
    def setup_method(self):
        from simulation.drone_lifecycle import DroneLifecycle
        self.d = DroneLifecycle()

    def test_register(self):
        self.d.register("d1", purchase_cost=10000)
        assert self.d.active_count() >= 1

    def test_retire(self):
        self.d.register("d1", purchase_cost=10000)
        self.d.retire("d1")
        s = self.d.summary()
        assert s["retired"] >= 1

    def test_tco(self):
        self.d.register("d1", purchase_cost=10000)
        self.d.record_operation("d1", hours=10, maintenance_cost=500)
        tco = self.d.tco("d1")
        assert tco >= 10500

    def test_summary(self):
        s = self.d.summary()
        assert "total" in s


class TestScheduleOptimizer:
    def setup_method(self):
        from simulation.schedule_optimizer import ScheduleOptimizer
        self.s = ScheduleOptimizer()

    def test_add_mission(self):
        self.s.add_mission("m1", duration_min=30, earliest=8, latest=18)
        s = self.s.summary()
        assert s["missions"] >= 1

    def test_optimize(self):
        for i in range(5):
            self.s.add_mission(f"m{i}", duration_min=30, earliest=8, latest=18)
        schedule = self.s.optimize()
        assert len(schedule) > 0

    def test_summary(self):
        s = self.s.summary()
        assert "missions" in s


class TestDeliveryOptimizer:
    def setup_method(self):
        from simulation.delivery_optimizer import DeliveryOptimizer
        self.d = DeliveryOptimizer()

    def test_add_delivery(self):
        self.d.add_delivery("o1", destination=(100, 200), weight_kg=2)
        s = self.d.summary()
        assert s["deliveries"] >= 1

    def test_optimize_route(self):
        self.d.add_delivery("o1", destination=(100, 200), weight_kg=2)
        self.d.add_delivery("o2", destination=(300, 100), weight_kg=1)
        route = self.d.optimize_route(depot=(0, 0), max_payload_kg=5)
        assert len(route) >= 2

    def test_capacity_constraint(self):
        self.d.add_delivery("o1", destination=(100, 200), weight_kg=3)
        self.d.add_delivery("o2", destination=(300, 100), weight_kg=3)
        route = self.d.optimize_route(depot=(0, 0), max_payload_kg=4)
        assert len(route) <= 2

    def test_summary(self):
        s = self.d.summary()
        assert "deliveries" in s


class TestPricingEngine:
    def setup_method(self):
        from simulation.pricing_engine import PricingEngine
        self.p = PricingEngine(base_price=5000)

    def test_basic_price(self):
        quote = self.p.calculate(distance_km=5)
        assert quote.total > 5000

    def test_demand_surge(self):
        q_normal = self.p.calculate(distance_km=5, demand_level=0.5)
        q_surge = self.p.calculate(distance_km=5, demand_level=2.0)
        assert q_surge.total > q_normal.total

    def test_weather_surcharge(self):
        q_clear = self.p.calculate(distance_km=5, wind_speed=2.0)
        q_storm = self.p.calculate(distance_km=5, wind_speed=20.0)
        assert q_storm.total > q_clear.total

    def test_summary(self):
        self.p.calculate(distance_km=5)
        s = self.p.summary()
        assert s["quotes_generated"] >= 1


class TestCustomerMetrics:
    def setup_method(self):
        from simulation.customer_metrics import CustomerMetrics
        self.c = CustomerMetrics()

    def test_record_delivery(self):
        self.c.record_delivery("c1", promised_min=30, actual_min=25)
        s = self.c.summary()
        assert s["deliveries"] >= 1

    def test_on_time_rate(self):
        self.c.record_delivery("c1", promised_min=30, actual_min=25)
        self.c.record_delivery("c2", promised_min=30, actual_min=40)
        rate = self.c.on_time_rate()
        assert 40 <= rate <= 60

    def test_satisfaction(self):
        self.c.record_delivery("c1", promised_min=30, actual_min=25, rating=5)
        avg = self.c.customer_satisfaction()
        assert avg == 5.0

    def test_summary(self):
        s = self.c.summary()
        assert "on_time_rate" in s


class TestFleetComposer:
    def setup_method(self):
        from simulation.fleet_composer import FleetComposer
        self.f = FleetComposer(budget=100000)

    def test_add_type(self):
        self.f.add_type("DELIVERY", cost=5000, revenue_per_mission=800)
        s = self.f.summary()
        assert s["types"] >= 1

    def test_optimize(self):
        self.f.add_type("DELIVERY", cost=5000, revenue_per_mission=800)
        self.f.add_type("SURVEY", cost=8000, revenue_per_mission=1000)
        fleet = self.f.optimize()
        assert isinstance(fleet, dict)
        assert sum(fleet.values()) > 0

    def test_summary(self):
        s = self.f.summary()
        assert "types" in s


# ── Phase 148-155 ──────────────────────────────────────────

class TestMCTSPlanner:
    def setup_method(self):
        from simulation.mcts_planner import MCTSPlanner
        self.m = MCTSPlanner(seed=42)

    def test_plan(self):
        path = self.m.plan(start=(0, 0, 50), goal=(500, 500, 50), n_iterations=50)
        assert len(path) >= 2

    def test_reaches_goal(self):
        path = self.m.plan(start=(0, 0, 50), goal=(100, 100, 50), n_iterations=100)
        last = path[-1]
        dist = np.sqrt(sum((a - b) ** 2 for a, b in zip(last, (100, 100, 50))))
        assert dist < 300

    def test_summary(self):
        self.m.plan(start=(0, 0, 50), goal=(100, 100, 50), n_iterations=10)
        s = self.m.summary()
        assert s["plans"] >= 1


class TestFederatedLearning:
    def setup_method(self):
        from simulation.federated_learning import FederatedLearning
        self.f = FederatedLearning(n_params=3)

    def test_register_client(self):
        self.f.register_client("d1")
        s = self.f.summary()
        assert s["clients"] >= 1

    def test_submit_aggregate(self):
        self.f.register_client("d1")
        self.f.register_client("d2")
        self.f.submit_update("d1", weights=[1.0, 2.0, 3.0])
        self.f.submit_update("d2", weights=[3.0, 4.0, 5.0])
        global_w = self.f.aggregate()
        assert len(global_w) == 3
        assert abs(global_w[0] - 2.0) < 0.01

    def test_summary(self):
        s = self.f.summary()
        assert "clients" in s


class TestNLPController:
    def setup_method(self):
        from simulation.nlp_controller import NLPController
        self.n = NLPController()

    def test_move_command(self):
        result = self.n.parse_command("move drone1 to 100 200 50")
        assert result.intent == "MOVE"

    def test_land_command(self):
        result = self.n.parse_command("land drone2")
        assert result.intent == "LAND"

    def test_emergency(self):
        result = self.n.parse_command("emergency stop all")
        assert result.intent == "EMERGENCY"

    def test_unknown(self):
        result = self.n.parse_command("xyzzy foobar")
        assert result.intent == "UNKNOWN"

    def test_summary(self):
        self.n.parse_command("move d1 to 0 0 0")
        s = self.n.summary()
        assert s["commands_parsed"] >= 1


class TestDigitalTwin:
    def setup_method(self):
        from simulation.digital_twin import DigitalTwin
        self.d = DigitalTwin()

    def test_register(self):
        self.d.update_from_telemetry("d1", position=(0, 0, 0), velocity=(0, 0, 0))
        s = self.d.summary()
        assert s["tracked_drones"] >= 1

    def test_update_predict(self):
        self.d.update_from_telemetry("d1", position=(100, 200, 50), velocity=(1, 0, 0), battery_pct=90)
        pred = self.d.get_prediction("d1", lookahead_s=10)
        assert pred["predicted_position"][0] > 100

    def test_divergence(self):
        self.d.update_from_telemetry("d1", position=(100, 200, 50), velocity=(0, 0, 0))
        div = self.d.get_divergence("d1", sim_position=(110, 200, 50))
        assert div == 10.0

    def test_summary(self):
        s = self.d.summary()
        assert "tracked_drones" in s


class TestAutoMissionPlanner:
    def setup_method(self):
        from simulation.auto_mission_planner import AutoMissionPlanner
        self.a = AutoMissionPlanner()

    def test_add_objective(self):
        self.a.add_objective("survey", priority=8)
        s = self.a.summary()
        assert s["objectives"] >= 1

    def test_generate(self):
        self.a.add_objective("survey", priority=8)
        missions = self.a.generate_missions(available_drones=["d1", "d2"])
        assert len(missions) >= 1

    def test_priority_order(self):
        self.a.add_objective("low", priority=1)
        self.a.add_objective("high", priority=9)
        missions = self.a.generate_missions(available_drones=["d1"])
        assert missions[0].objective == "high"

    def test_summary(self):
        s = self.a.summary()
        assert "missions_generated" in s


class TestMultimodalSensor:
    def setup_method(self):
        from simulation.multimodal_sensor import MultimodalSensor
        self.m = MultimodalSensor(seed=42)

    def test_add_sensor(self):
        self.m.add_sensor("d1", "CAMERA", accuracy=0.9)
        s = self.m.summary()
        assert s["total_sensors"] >= 1

    def test_detect(self):
        self.m.add_sensor("d1", "CAMERA", accuracy=0.95, range_m=500)
        dets = self.m.detect("d1", drone_pos=(0, 0, 50), objects=[{"id": "o1", "pos": (100, 0, 50)}])
        assert len(dets) >= 1

    def test_fuse(self):
        self.m.add_sensor("d1", "CAMERA", accuracy=0.95, range_m=500)
        self.m.add_sensor("d1", "LIDAR", accuracy=0.9, range_m=300)
        self.m.detect("d1", drone_pos=(0, 0, 50), objects=[{"id": "o1", "pos": (100, 0, 50)}])
        fused = self.m.fuse_detections("o1")
        assert fused is not None

    def test_summary(self):
        s = self.m.summary()
        assert "total_detections" in s


class TestEventArchitecture:
    def setup_method(self):
        from simulation.event_architecture import EventArchitecture
        self.e = EventArchitecture()

    def test_emit(self):
        ev = self.e.emit("DroneCreated", {"drone_id": "d1"})
        assert ev.seq == 1

    def test_replay(self):
        self.e.emit("DroneCreated", {"drone_id": "d1"})
        self.e.emit("DroneMoving", {"drone_id": "d1", "pos": (100, 200, 50)})
        events = self.e.replay()
        assert len(events) == 2

    def test_snapshot(self):
        self.e.emit("DroneCreated", {"drone_id": "d1", "type": "DELIVERY"})
        snap = self.e.snapshot()
        assert "d1" in snap["drones"]

    def test_handler(self):
        captured = []
        self.e.on("Test", lambda ev: captured.append(ev))
        self.e.emit("Test", {"val": 1})
        assert len(captured) == 1

    def test_summary(self):
        s = self.e.summary()
        assert "total_events" in s


class TestSystemDashboard:
    def setup_method(self):
        from simulation.system_dashboard import SystemDashboard
        self.s = SystemDashboard()

    def test_register_module(self):
        self.s.register_module("apf", status="OK")
        board = self.s.get_board()
        assert "apf" in board["modules"]

    def test_kpi(self):
        self.s.update_kpi("collision_rate", 0.001)
        self.s.update_kpi("collision_rate", 0.002)
        val = self.s.get_kpi("collision_rate")
        assert abs(val - 0.0015) < 0.001

    def test_health_critical(self):
        self.s.register_module("m1", status="ERROR")
        board = self.s.get_board()
        assert board["overall_health"] == "CRITICAL"

    def test_alerts(self):
        self.s.register_module("m1")
        self.s.update_module_status("m1", "ERROR", t=10)
        board = self.s.get_board()
        assert len(board["recent_alerts"]) >= 1

    def test_summary(self):
        s = self.s.summary()
        assert "overall" in s
