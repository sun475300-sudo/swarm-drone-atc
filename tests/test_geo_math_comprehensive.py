"""
geo_math 포괄적 단위 테스트
haversine_distance, lla_to_ned, ned_to_lla, bearing, distance_3d, closest_approach 엣지 케이스 커버
"""
from __future__ import annotations

import numpy as np
import pytest

from src.airspace_control.utils.geo_math import (
    haversine_distance,
    lla_to_ned,
    ned_to_lla,
    bearing,
    distance_3d,
    closest_approach,
    EARTH_RADIUS_M,
)


class TestHaversineExtended:
    def test_antipodal_points(self):
        """지구 반대편 점 → 약 반둘레"""
        d = haversine_distance(0.0, 0.0, 0.0, 180.0)
        assert d == pytest.approx(np.pi * EARTH_RADIUS_M, rel=0.01)

    def test_symmetric(self):
        d1 = haversine_distance(37.5, 127.0, 35.0, 129.0)
        d2 = haversine_distance(35.0, 129.0, 37.5, 127.0)
        assert d1 == pytest.approx(d2, abs=0.01)

    def test_small_distance(self):
        """~111m 거리 (위도 0.001도 차이)"""
        d = haversine_distance(0.0, 0.0, 0.001, 0.0)
        assert 100.0 < d < 120.0

    def test_equator_longitude(self):
        """적도에서 경도 1도 → ~111km"""
        d = haversine_distance(0.0, 0.0, 0.0, 1.0)
        assert 110_000 < d < 112_000


class TestLlaToNedExtended:
    def test_east_positive(self):
        ned = lla_to_ned(0.0, 0.001, 0.0, 0.0, 0.0, 0.0)
        assert ned[1] > 0  # East

    def test_west_negative(self):
        ned = lla_to_ned(0.0, -0.001, 0.0, 0.0, 0.0, 0.0)
        assert ned[1] < 0

    def test_south_negative(self):
        ned = lla_to_ned(-0.001, 0.0, 0.0, 0.0, 0.0, 0.0)
        assert ned[0] < 0

    def test_altitude_higher_down_negative(self):
        """고도가 높으면 Down이 음수"""
        ned = lla_to_ned(0.0, 0.0, 100.0, 0.0, 0.0, 0.0)
        assert ned[2] < 0  # down = -(alt - ref_alt)


class TestNedToLlaExtended:
    def test_roundtrip_large_offset(self):
        """큰 NED 오프셋 왕복"""
        ref_lat, ref_lon, ref_alt = 37.5, 127.0, 50.0
        ned = np.array([1000.0, 500.0, -30.0])
        lat, lon, alt = ned_to_lla(ned, ref_lat, ref_lon, ref_alt)
        ned_back = lla_to_ned(lat, lon, alt, ref_lat, ref_lon, ref_alt)
        assert np.allclose(ned, ned_back, atol=0.1)

    def test_zero_offset(self):
        lat, lon, alt = ned_to_lla(np.zeros(3), 37.5, 127.0, 50.0)
        assert lat == pytest.approx(37.5)
        assert lon == pytest.approx(127.0)
        assert alt == pytest.approx(50.0)


class TestBearingExtended:
    def test_south(self):
        """남쪽 → 180도"""
        b = bearing(np.array([10.0, 0.0, 0.0]), np.array([0.0, 0.0, 0.0]))
        assert b == pytest.approx(180.0, abs=1.0)

    def test_west(self):
        """서쪽 → 270도"""
        b = bearing(np.array([0.0, 10.0, 0.0]), np.array([0.0, 0.0, 0.0]))
        assert b == pytest.approx(270.0, abs=1.0)

    def test_northeast(self):
        """북동쪽 → 45도"""
        b = bearing(np.array([0.0, 0.0, 0.0]), np.array([10.0, 10.0, 0.0]))
        assert b == pytest.approx(45.0, abs=1.0)

    def test_same_point(self):
        b = bearing(np.array([0.0, 0.0, 0.0]), np.array([0.0, 0.0, 0.0]))
        assert 0.0 <= b <= 360.0


class TestDistance3dExtended:
    def test_3d_diagonal(self):
        d = distance_3d(np.array([0, 0, 0]), np.array([1, 1, 1]))
        assert d == pytest.approx(np.sqrt(3))

    def test_negative_coords(self):
        d = distance_3d(np.array([-5, -5, -5]), np.array([5, 5, 5]))
        assert d == pytest.approx(np.sqrt(300))


class TestClosestApproachExtended:
    def test_perpendicular_paths(self):
        """수직 교차 경로"""
        dist, t = closest_approach(
            np.array([0.0, -100.0, 0.0]), np.array([0.0, 10.0, 0.0]),
            np.array([-100.0, 0.0, 0.0]), np.array([10.0, 0.0, 0.0]),
        )
        assert t > 0
        assert dist < 100.0  # 교차점 근처에서 최소 거리

    def test_diverging_paths(self):
        """멀어지는 경로 → CPA는 t=0"""
        dist, t = closest_approach(
            np.array([0.0, 0.0, 0.0]), np.array([10.0, 0.0, 0.0]),
            np.array([100.0, 0.0, 0.0]), np.array([10.0, 0.0, 0.0]),
        )
        # 같은 방향으로 이동하되 이미 멀어져있음 → t_cpa는 0 (clipped)
        assert t == pytest.approx(0.0)

    def test_lookahead_clamping(self):
        """룩어헤드 넘는 CPA는 클램핑"""
        dist, t = closest_approach(
            np.array([0.0, 0.0, 0.0]), np.array([0.1, 0.0, 0.0]),
            np.array([10000.0, 0.0, 0.0]), np.array([-0.1, 0.0, 0.0]),
            lookahead_s=10.0,
        )
        assert t <= 10.0

    def test_one_stationary_one_moving(self):
        """한쪽만 정지"""
        dist, t = closest_approach(
            np.array([0.0, 0.0, 0.0]), np.zeros(3),
            np.array([100.0, 0.0, 0.0]), np.array([-10.0, 0.0, 0.0]),
        )
        assert t == pytest.approx(10.0, abs=0.1)
        assert dist < 1.0

    def test_same_velocity_same_distance(self):
        """동일 속도이면 거리 유지"""
        vel = np.array([5.0, 0.0, 0.0])
        dist, t = closest_approach(
            np.array([0.0, 0.0, 0.0]), vel,
            np.array([50.0, 0.0, 0.0]), vel,
        )
        assert dist == pytest.approx(50.0, abs=0.1)
