"""Phase 172-179 tests: city map generation and traffic simulation."""


class TestCityMapGenerator:
    def setup_method(self):
        from simulation.city_map_generator import CityMapGenerator

        self.g = CityMapGenerator(width_m=1200, height_m=900, seed=42)

    def test_generate_buildings(self):
        out = self.g.generate_buildings(count=12)
        assert len(out) == 12
        assert out[0].width > 0

    def test_generate_corridors(self):
        out = self.g.generate_corridors(count=4)
        assert len(out) == 4
        assert out[0].width == 80.0

    def test_generate_landing_pads(self):
        out = self.g.generate_landing_pads(count=5)
        assert len(out) == 5
        assert out[0].pad_id.startswith("PAD-")

    def test_generate_map(self):
        m = self.g.generate_map(buildings=10, corridors=3, pads=4)
        assert len(m["buildings"]) == 10
        assert len(m["corridors"]) == 3
        assert len(m["landing_pads"]) == 4

    def test_summary(self):
        s = self.g.summary()
        assert s["width_m"] == 1200


class TestTrafficSimulator:
    def setup_method(self):
        from simulation.traffic_simulator import TrafficSimulator

        self.t = TrafficSimulator(base_demand=100, seed=42)

    def test_demand_at(self):
        d = self.t.demand_at(hour=8)
        assert d > 0

    def test_congestion_index(self):
        c = self.t.congestion_index(demand=100, capacity=200)
        assert 0 <= c <= 1

    def test_incident_probability(self):
        p = self.t.incident_probability(0.8)
        assert 0 < p <= 0.35

    def test_step(self):
        st = self.t.step(hour=18, weather_factor=1.1, capacity=160)
        assert st.hour == 18
        assert st.demand > 0

    def test_simulate_day(self):
        out = self.t.simulate_day()
        assert len(out) == 24

    def test_summary(self):
        self.t.simulate_day()
        s = self.t.summary()
        assert s["states"] == 24


class TestWeatherApiClient:
    def test_fetch_default_profile(self):
        from simulation.weather_api_client import WeatherApiClient

        c = WeatherApiClient(ttl_seconds=300)
        w = c.fetch(city="Seoul", now_ts=1000.0)
        assert w.condition == "clear"
        assert w.wind_mps >= 0

    def test_cache_hit_within_ttl(self):
        from simulation.weather_api_client import WeatherApiClient

        calls = {"n": 0}

        def provider(city: str):
            calls["n"] += 1
            return {
                "condition": "rain",
                "wind_mps": 6.0,
                "visibility_km": 7.0,
                "temperature_c": 16.0,
            }

        c = WeatherApiClient(provider=provider, ttl_seconds=120)
        a = c.fetch(city="Busan", now_ts=1000.0)
        b = c.fetch(city="Busan", now_ts=1050.0)
        assert calls["n"] == 1
        assert a.timestamp == b.timestamp

    def test_cache_expire_after_ttl(self):
        from simulation.weather_api_client import WeatherApiClient

        calls = {"n": 0}

        def provider(city: str):
            calls["n"] += 1
            return {
                "condition": "clear",
                "wind_mps": 2.0 + calls["n"],
                "visibility_km": 10.0,
                "temperature_c": 20.0,
            }

        c = WeatherApiClient(provider=provider, ttl_seconds=30)
        first = c.fetch(city="Incheon", now_ts=1000.0)
        second = c.fetch(city="Incheon", now_ts=1040.0)
        assert calls["n"] == 2
        assert second.timestamp > first.timestamp

    def test_traffic_factor_degrades_in_bad_weather(self):
        from simulation.weather_api_client import WeatherApiClient, WeatherSample

        c = WeatherApiClient(ttl_seconds=60)
        bad = WeatherSample(
            city="Seoul",
            condition="storm",
            wind_mps=13.0,
            visibility_km=2.5,
            temperature_c=9.0,
            timestamp=1000.0,
        )
        factor = c.traffic_factor(bad)
        assert 0.4 <= factor < 1.0

    def test_summary_fields(self):
        from simulation.weather_api_client import WeatherApiClient

        c = WeatherApiClient(ttl_seconds=60)
        c.fetch(city="Seoul", now_ts=1000.0)
        c.fetch(city="Seoul", now_ts=1001.0)
        s = c.summary()
        assert s["cache_size"] == 1
        assert s["hits"] >= 1


class TestWeatherRiskModel:
    def test_score_low_risk(self):
        from simulation.weather_risk_model import WeatherRiskInput, WeatherRiskModel

        model = WeatherRiskModel()
        out = model.score(
            WeatherRiskInput(
                wind_mps=2.0,
                visibility_km=10.0,
                precipitation_level=0.0,
                congestion=0.1,
            )
        )
        assert out.category == "GREEN"
        assert 0.0 <= out.score < 0.25

    def test_score_high_risk(self):
        from simulation.weather_risk_model import WeatherRiskInput, WeatherRiskModel

        model = WeatherRiskModel()
        out = model.score(
            WeatherRiskInput(
                wind_mps=22.0,
                visibility_km=1.0,
                precipitation_level=1.0,
                congestion=0.95,
            )
        )
        assert out.category == "RED"
        assert out.score >= 0.75

    def test_score_clamps_input_range(self):
        from simulation.weather_risk_model import WeatherRiskInput, WeatherRiskModel

        model = WeatherRiskModel()
        out = model.score(
            WeatherRiskInput(
                wind_mps=-5.0,
                visibility_km=30.0,
                precipitation_level=-1.0,
                congestion=3.0,
            )
        )
        assert 0.0 <= out.score <= 1.0


class TestDeliverySimulation:
    def setup_method(self):
        from simulation.delivery_simulation import DeliverySimulation

        self.s = DeliverySimulation()
        self.s.register_drone("D1", position=(0, 0), max_payload_kg=3.0, speed_mps=12.0)
        self.s.register_drone("D2", position=(300, 0), max_payload_kg=5.0, speed_mps=10.0)

    def test_add_order_and_pending(self):
        self.s.add_order("O1", destination=(120, 80), weight_kg=1.5)
        assert self.s.pending_orders() == 1

    def test_dispatch_next_assigns_nearest_available(self):
        self.s.add_order("O1", destination=(100, 0), weight_kg=1.0, priority=7)
        rec = self.s.dispatch_next(congestion=0.1, weather_factor=1.0)
        assert rec is not None
        assert rec.order_id == "O1"
        assert rec.drone_id == "D1"
        assert rec.eta_min > 0

    def test_dispatch_respects_payload_limit(self):
        self.s.add_order("O2", destination=(100, 0), weight_kg=4.0, priority=9)
        rec = self.s.dispatch_next(congestion=0.2, weather_factor=1.0)
        assert rec is not None
        assert rec.drone_id == "D2"

    def test_complete_delivery_releases_drone(self):
        self.s.add_order("O3", destination=(90, 0), weight_kg=1.0)
        rec = self.s.dispatch_next()
        assert rec is not None
        assert self.s.complete_delivery("O3") is True
        summary = self.s.summary()
        assert summary["delivered"] == 1
        assert summary["busy_drones"] == 0

    def test_dispatch_returns_none_when_no_candidate(self):
        self.s.add_order("O4", destination=(80, 0), weight_kg=10.0)
        rec = self.s.dispatch_next()
        assert rec is None

    def test_summary_counts(self):
        self.s.add_order("O5", destination=(100, 100), weight_kg=2.0)
        rec = self.s.dispatch_next()
        assert rec is not None
        summary = self.s.summary()
        assert summary["drones"] == 2
        assert summary["dispatches"] == 1

    def test_dispatch_with_airspace_reservation(self):
        from simulation.airspace_reservation import AirspaceReservation

        ar = AirspaceReservation(grid_size=100)
        self.s.set_airspace_reservation(ar, altitude_band=(40, 80))
        self.s.add_order("O6", destination=(210, 110), weight_kg=1.0, created_min=5)
        rec = self.s.dispatch_next()
        assert rec is not None
        assert rec.reservation_id is not None
        assert len(ar.active_reservations()) == 1

    def test_dispatch_fails_on_slot_conflict(self):
        from simulation.airspace_reservation import AirspaceReservation

        ar = AirspaceReservation(grid_size=100)
        ar.reserve("X1", (2, 1), 0, 60, altitude_band=(40, 80), priority=1)
        self.s.set_airspace_reservation(ar, altitude_band=(40, 80))
        self.s.add_order("O7", destination=(210, 110), weight_kg=1.0, priority=8, created_min=1)
        rec = self.s.dispatch_next()
        assert rec is None

    def test_complete_delivery_cancels_reservation(self):
        from simulation.airspace_reservation import AirspaceReservation

        ar = AirspaceReservation(grid_size=100)
        self.s.set_airspace_reservation(ar, altitude_band=(35, 75))
        self.s.add_order("O8", destination=(100, 20), weight_kg=1.0)
        rec = self.s.dispatch_next()
        assert rec is not None
        assert rec.reservation_id is not None
        assert self.s.complete_delivery("O8") is True
        assert len(ar.active_reservations()) == 0

    def test_summary_reserved_slots(self):
        from simulation.airspace_reservation import AirspaceReservation

        ar = AirspaceReservation(grid_size=100)
        self.s.set_airspace_reservation(ar)
        self.s.add_order("O9", destination=(150, 40), weight_kg=1.0)
        rec = self.s.dispatch_next()
        assert rec is not None
        assert self.s.summary()["reserved_slots"] == 1

    def test_slot_policy_shifts_altitude_in_bad_weather(self):
        from simulation.airspace_reservation import AirspaceReservation

        ar = AirspaceReservation(grid_size=100)
        self.s.set_airspace_reservation(ar, altitude_band=(30, 90))
        self.s.add_order("O10", destination=(110, 30), weight_kg=1.0, created_min=2)
        rec = self.s.dispatch_next(congestion=0.1, weather_factor=0.5)
        assert rec is not None
        active = ar.active_reservations()
        assert len(active) == 1
        assert active[0].altitude_band[0] > 30

    def test_slot_policy_escalates_priority_under_heavy_congestion(self):
        from simulation.airspace_reservation import AirspaceReservation

        ar = AirspaceReservation(grid_size=100)
        ar.reserve("HIGH", (1, 0), 0, 60, altitude_band=(30, 90), priority=3)
        self.s.set_airspace_reservation(ar, altitude_band=(30, 90))
        self.s.add_order("O11", destination=(110, 30), weight_kg=1.0, priority=8, created_min=1)
        rec = self.s.dispatch_next(congestion=0.95, weather_factor=0.6)
        assert rec is not None
        assert len(ar.active_reservations()) == 1
        assert ar.active_reservations()[0].drone_id in {"D1", "D2"}

    def test_set_slot_policy_changes_thresholds(self):
        self.s.set_slot_policy(
            congestion_alt_step=20,
            bad_weather_alt_step=10,
            weather_threshold=0.9,
            congestion_threshold=0.5,
        )
        summary = self.s.summary()
        assert summary["slot_policy"]["congestion_alt_step"] == 20.0
        assert summary["slot_policy"]["weather_threshold"] == 0.9

    def test_dispatch_with_traffic_state(self):
        from simulation.traffic_simulator import TrafficSimulator

        t = TrafficSimulator(base_demand=120, seed=42)
        state = t.step(hour=18, weather_factor=1.0, capacity=160)
        self.s.add_order("O12", destination=(90, 20), weight_kg=1.2)
        rec = self.s.dispatch_with_traffic_state(state, weather_factor=1.0)
        assert rec is not None
        assert rec.traffic_demand == state.demand
        assert rec.traffic_congestion == round(state.congestion, 4)

    def test_summary_includes_dispatch_traffic_metrics(self):
        from simulation.traffic_simulator import TrafficSimulator

        t = TrafficSimulator(base_demand=100, seed=42)
        self.s.add_order("O13", destination=(100, 10), weight_kg=1.0)
        self.s.add_order("O14", destination=(120, 20), weight_kg=1.0)
        r1 = self.s.dispatch_with_traffic_state(t.step(hour=8, capacity=180), weather_factor=1.0)
        assert r1 is not None
        self.s.complete_delivery("O13")
        r2 = self.s.dispatch_with_traffic_state(t.step(hour=19, capacity=180), weather_factor=0.9)
        assert r2 is not None
        s = self.s.summary()
        assert s["avg_dispatch_congestion"] > 0.0
        assert s["avg_dispatch_demand"] > 0.0


class TestComplianceEngine:
    def setup_method(self):
        from simulation.compliance_engine import ComplianceEngine

        self.e = ComplianceEngine()

    def test_evaluate_flight_no_violation(self):
        out = self.e.evaluate_flight("D1", altitude_m=80, speed_mps=12, battery_pct=50)
        assert out == []

    def test_evaluate_flight_detects_violation(self):
        out = self.e.evaluate_flight("D1", altitude_m=140, speed_mps=12, battery_pct=50)
        assert len(out) == 1
        assert out[0].rule_name == "MAX_ALT"

    def test_evaluate_batch(self):
        result = self.e.evaluate_batch(
            [
                {"drone_id": "D1", "altitude_m": 25, "speed_mps": 10, "battery_pct": 80},
                {"drone_id": "D2", "altitude_m": 20, "speed_mps": 28, "battery_pct": 9},
            ]
        )
        assert "D1" in result
        assert "D2" in result
        assert len(result["D1"]) == 1  # MIN_ALT
        assert len(result["D2"]) == 3  # MIN_ALT + MAX_SPEED + MIN_BATTERY

    def test_violation_report(self):
        self.e.evaluate_flight("D1", altitude_m=150, speed_mps=35, battery_pct=5)
        report = self.e.violation_report()
        assert report["total_violations"] == 3
        assert report["by_rule"]["MAX_ALT"] == 1

    def test_custom_ruleset(self):
        from simulation.compliance_engine import ComplianceRule

        self.e.register_ruleset(
            [ComplianceRule(name="MAX_WIND", metric="wind_mps", max_value=12.0, severity="HIGH")]
        )
        out = self.e.evaluate_flight("D3", wind_mps=13.5)
        assert len(out) == 1
        assert out[0].rule_name == "MAX_WIND"

    def test_clear(self):
        self.e.evaluate_flight("D1", altitude_m=200)
        assert self.e.summary()["total_violations"] > 0
        self.e.clear()
        assert self.e.summary()["total_violations"] == 0

    def test_rule_hotspots(self):
        self.e.evaluate_flight("D1", altitude_m=200, speed_mps=40)
        self.e.evaluate_flight("D2", altitude_m=180, speed_mps=10)
        hot = self.e.rule_hotspots(top_n=2)
        assert len(hot) == 2
        assert hot[0]["rule"] == "MAX_ALT"
        assert hot[0]["count"] >= hot[1]["count"]

    def test_severity_trend(self):
        self.e.evaluate_flight("D1", altitude_m=200, speed_mps=40, battery_pct=5)
        self.e.evaluate_flight("D2", altitude_m=20, speed_mps=10, battery_pct=80)
        self.e.evaluate_flight("D3", altitude_m=130, speed_mps=40, battery_pct=9)
        trend = self.e.severity_trend(window=2)
        assert len(trend) == 2
        assert trend[0]["start_eval"] == 1
        assert trend[0]["end_eval"] == 2
        assert trend[0]["violations"] > 0

    def test_summary_contains_hotspots(self):
        self.e.evaluate_flight("D1", altitude_m=200)
        s = self.e.summary()
        assert "hotspots" in s
        assert len(s["hotspots"]) >= 1


class TestSimRecorder:
    def setup_method(self):
        from simulation.sim_recorder import SimRecorder

        self.r = SimRecorder()

    def test_record_and_events(self):
        self.r.record(0.1, "TAKEOFF", drone_id="D1")
        out = self.r.events()
        assert len(out) == 1
        assert out[0].event_type == "TAKEOFF"

    def test_replay_window(self):
        self.r.record(1.0, "A")
        self.r.record(2.5, "B")
        self.r.record(4.0, "C")
        out = self.r.replay(start_sec=2.0, end_sec=3.0)
        assert len(out) == 1
        assert out[0].event_type == "B"

    def test_export_import(self):
        self.r.record(1.0, "STATE", x=1)
        rows = self.r.export()
        from simulation.sim_recorder import SimRecorder

        r2 = SimRecorder()
        r2.import_events(rows)
        assert len(r2.events()) == 1
        assert r2.events()[0].payload["x"] == 1

    def test_summary(self):
        self.r.record(0.0, "A")
        self.r.record(2.0, "A")
        self.r.record(3.0, "B")
        s = self.r.summary()
        assert s["events"] == 3
        assert s["by_type"]["A"] == 2


class TestPerfBenchmark:
    def setup_method(self):
        from simulation.perf_benchmark import PerfBenchmark

        self.b = PerfBenchmark()

    def test_add_sample_and_report(self):
        self.b.add_sample(12.5)
        self.b.add_sample(25.0)
        report = self.b.report(window_sec=10)
        assert report["samples"] == 2
        assert report["avg_ms"] > 0
        assert report["throughput_rps"] == 0.2

    def test_add_batch(self):
        self.b.add_batch([10, 20, 30, 40])
        report = self.b.report(window_sec=20)
        assert report["samples"] == 4
        assert report["p95_ms"] >= report["p50_ms"]

    def test_success_rate(self):
        self.b.add_sample(10, success=True)
        self.b.add_sample(11, success=False)
        self.b.add_sample(12, success=True)
        report = self.b.report(window_sec=3)
        assert report["success_rate"] == 0.6667

    def test_empty_report(self):
        report = self.b.report()
        assert report["samples"] == 0
        assert report["throughput_rps"] == 0.0


class TestE2EReporter:
    def setup_method(self):
        from simulation.e2e_reporter import E2EReporter

        self.r = E2EReporter()

    def test_build_report_shape(self):
        report = self.r.build(
            delivery_summary={"delivered": 3, "dispatches": 3},
            compliance_report={"total_violations": 0, "by_rule": {}},
            recorder_summary={"events": 24, "duration_sec": 12.0},
            perf_report={"samples": 10, "success_rate": 1.0, "p95_ms": 18.0},
            traffic_summary={"avg_congestion": 0.42, "peak_hour": 18},
            meta={"scenario": "phase172-e2e"},
        )
        assert report["meta"]["scenario"] == "phase172-e2e"
        assert report["kpi"]["delivered"] == 3
        assert "health_score" in report["kpi"]
        assert report["kpi"]["traffic_pressure"] == 0.42

    def test_health_score_degrades_with_violations(self):
        good = self.r.build(
            delivery_summary={"delivered": 2},
            compliance_report={"total_violations": 0},
            recorder_summary={"events": 10},
            perf_report={"success_rate": 1.0},
            traffic_summary={"avg_congestion": 0.2},
        )
        bad = self.r.build(
            delivery_summary={"delivered": 2},
            compliance_report={"total_violations": 4},
            recorder_summary={"events": 10},
            perf_report={"success_rate": 1.0},
            traffic_summary={"avg_congestion": 0.2},
        )
        assert bad["kpi"]["health_score"] < good["kpi"]["health_score"]

    def test_health_score_degrades_with_traffic_pressure(self):
        low = self.r.build(
            delivery_summary={"delivered": 2},
            compliance_report={"total_violations": 0},
            recorder_summary={"events": 10},
            perf_report={"success_rate": 1.0},
            traffic_summary={"avg_congestion": 0.1},
        )
        high = self.r.build(
            delivery_summary={"delivered": 2},
            compliance_report={"total_violations": 0},
            recorder_summary={"events": 10},
            perf_report={"success_rate": 1.0},
            traffic_summary={"avg_congestion": 0.95},
        )
        assert high["kpi"]["health_score"] < low["kpi"]["health_score"]

    def test_summary(self):
        self.r.build({}, {}, {}, {})
        self.r.build({}, {}, {}, {})
        s = self.r.summary()
        assert s["reports"] == 2
        assert 0.0 <= s["avg_health_score"] <= 1.0

    def test_clear(self):
        self.r.build({}, {}, {}, {})
        assert self.r.summary()["reports"] == 1
        self.r.clear()
        assert self.r.summary()["reports"] == 0
