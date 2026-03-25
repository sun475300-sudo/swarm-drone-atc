"""WindModel 3종 테스트"""
import numpy as np
import pytest
from simulation.weather import (
    WindModel, ConstantWind, VariableWind, ShearWind, build_wind_models,
)


class TestConstantWind:
    def test_returns_correct_direction(self):
        w = ConstantWind(speed_ms=10.0, direction_deg=0.0)
        vec = w.get_wind_vector(np.zeros(3), 0.0)
        assert vec[0] == pytest.approx(10.0, abs=0.01)
        assert abs(vec[1]) < 0.01
        assert vec[2] == 0.0

    def test_90_degree(self):
        w = ConstantWind(speed_ms=5.0, direction_deg=90.0)
        vec = w.get_wind_vector(np.zeros(3), 0.0)
        assert abs(vec[0]) < 0.01
        assert vec[1] == pytest.approx(5.0, abs=0.01)

    def test_returns_copy(self):
        w = ConstantWind(speed_ms=3.0, direction_deg=0.0)
        v1 = w.get_wind_vector(np.zeros(3), 0.0)
        v2 = w.get_wind_vector(np.zeros(3), 0.0)
        v1[:] = 999.0
        assert v2[0] != 999.0


class TestVariableWind:
    def test_base_wind(self):
        w = VariableWind(
            mean_speed_ms=5.0, direction_deg=0.0,
            gust_speed_ms=0.0, gust_duration_s=1.0,
            rng=np.random.default_rng(42),
        )
        vec = w.get_wind_vector(np.zeros(3), 0.0)
        assert vec[0] == pytest.approx(5.0, abs=0.01)

    def test_gust_eventually_triggers(self):
        rng = np.random.default_rng(42)
        w = VariableWind(
            mean_speed_ms=0.0, direction_deg=0.0,
            gust_speed_ms=10.0, gust_duration_s=5.0,
            rng=rng,
        )
        magnitudes = []
        for t in range(200):
            vec = w.get_wind_vector(np.zeros(3), float(t))
            magnitudes.append(np.linalg.norm(vec))
        assert max(magnitudes) > 5.0  # 돌풍 발생 확인


class TestShearWind:
    def test_low_altitude(self):
        w = ShearWind(low_alt_speed_ms=2.0, high_alt_speed_ms=10.0,
                      direction_deg=0.0, transition_alt_m=60.0)
        vec = w.get_wind_vector(np.array([0, 0, 0]), 0.0)
        assert vec[0] == pytest.approx(2.0, abs=0.1)

    def test_high_altitude(self):
        w = ShearWind(low_alt_speed_ms=2.0, high_alt_speed_ms=10.0,
                      direction_deg=0.0, transition_alt_m=60.0)
        vec = w.get_wind_vector(np.array([0, 0, 60]), 0.0)
        assert vec[0] == pytest.approx(10.0, abs=0.1)

    def test_mid_altitude(self):
        w = ShearWind(low_alt_speed_ms=0.0, high_alt_speed_ms=10.0,
                      direction_deg=0.0, transition_alt_m=100.0)
        vec = w.get_wind_vector(np.array([0, 0, 50]), 0.0)
        assert vec[0] == pytest.approx(5.0, abs=0.1)


class TestBuildWindModels:
    def test_empty_config(self):
        models = build_wind_models({})
        assert models == []

    def test_constant(self):
        cfg = {"wind_models": [{"type": "constant", "speed_ms": 5, "direction_deg": 90}]}
        models = build_wind_models(cfg)
        assert len(models) == 1
        assert isinstance(models[0], ConstantWind)

    def test_multiple_models(self):
        cfg = {"wind_models": [
            {"type": "constant", "speed_ms": 5, "direction_deg": 0},
            {"type": "variable", "mean_speed_ms": 3, "direction_deg": 90,
             "gust_speed_ms": 8, "gust_duration_s": 10},
            {"type": "shear", "low_alt_speed_ms": 1, "high_alt_speed_ms": 8,
             "direction_deg": 45},
        ]}
        models = build_wind_models(cfg, np.random.default_rng(0))
        assert len(models) == 3
