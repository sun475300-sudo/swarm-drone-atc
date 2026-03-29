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
