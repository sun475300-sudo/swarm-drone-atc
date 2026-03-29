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
