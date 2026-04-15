"""geo_math 유틸리티 테스트"""
import numpy as np
import pytest
from src.airspace_control.utils.geo_math import (
    haversine_distance, lla_to_ned, ned_to_lla,
    bearing, distance_3d, closest_approach,
)

pytestmark = pytest.mark.unit


class TestHaversine:
    def test_same_point_zero(self):
        assert haversine_distance(37.0, 127.0, 37.0, 127.0) == pytest.approx(0.0, abs=1.0)

    def test_known_distance(self):
        # 서울 ↔ 부산 약 325km
        d = haversine_distance(37.5665, 126.978, 35.1796, 129.0756)
        assert 300_000 < d < 400_000


class TestLlaToNed:
    def test_same_point_zero(self):
        ned = lla_to_ned(37.0, 127.0, 100.0, 37.0, 127.0, 100.0)
        np.testing.assert_allclose(ned, [0, 0, 0], atol=0.1)

    def test_north_positive(self):
        ned = lla_to_ned(37.001, 127.0, 100.0, 37.0, 127.0, 100.0)
        assert ned[0] > 0  # north
        assert abs(ned[1]) < 1.0  # east ~ 0

    def test_altitude_down(self):
        ned = lla_to_ned(37.0, 127.0, 200.0, 37.0, 127.0, 100.0)
        assert ned[2] < 0  # higher alt → negative down


class TestNedToLla:
    def test_roundtrip(self):
        ref = (37.0, 127.0, 100.0)
        ned = lla_to_ned(37.001, 127.001, 150.0, *ref)
        lat, lon, alt = ned_to_lla(ned, *ref)
        assert lat == pytest.approx(37.001, abs=0.0001)
        assert lon == pytest.approx(127.001, abs=0.0001)
        assert alt == pytest.approx(150.0, abs=1.0)


class TestBearing:
    def test_north(self):
        b = bearing(np.array([0, 0]), np.array([100, 0]))
        assert b == pytest.approx(0.0, abs=1.0)

    def test_east(self):
        b = bearing(np.array([0, 0]), np.array([0, 100]))
        assert b == pytest.approx(90.0, abs=1.0)


class TestDistance3d:
    def test_known(self):
        assert distance_3d(np.zeros(3), np.array([3, 4, 0])) == pytest.approx(5.0)

    def test_same_point(self):
        assert distance_3d(np.ones(3), np.ones(3)) == pytest.approx(0.0)


class TestClosestApproach:
    def test_head_on(self):
        dist, t = closest_approach(
            np.array([100, 0, 0]), np.array([-10, 0, 0]),
            np.array([-100, 0, 0]), np.array([10, 0, 0]),
        )
        assert dist < 1.0  # 거의 0
        assert t == pytest.approx(10.0, abs=0.5)

    def test_parallel_no_approach(self):
        dist, t = closest_approach(
            np.array([0, 0, 0]), np.array([10, 0, 0]),
            np.array([0, 100, 0]), np.array([10, 0, 0]),
        )
        assert dist == pytest.approx(100.0, abs=1.0)

    def test_stationary(self):
        dist, t = closest_approach(
            np.array([0, 0, 0]), np.zeros(3),
            np.array([50, 0, 0]), np.zeros(3),
        )
        assert dist == pytest.approx(50.0)
        assert t == 0.0
