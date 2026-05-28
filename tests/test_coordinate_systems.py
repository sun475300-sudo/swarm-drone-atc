"""좌표계 변환 유틸리티 테스트"""
import numpy as np
import pytest

from src.airspace_control.utils.coordinate_systems import (
    grid_to_ned,
    ned_to_grid,
    ned_to_xyz,
    xyz_to_ned,
)

pytestmark = pytest.mark.unit


class TestNedToXyz:
    def test_known_conversion(self):
        ned = np.array([1.0, 2.0, 3.0])  # N=1, E=2, D=3
        xyz = ned_to_xyz(ned)
        # X=East=ned[1], Y=North=ned[0], Z=Up=-ned[2]
        np.testing.assert_array_equal(xyz, [2.0, 1.0, -3.0])

    def test_zeros(self):
        np.testing.assert_array_equal(ned_to_xyz(np.zeros(3)), np.zeros(3))

    def test_negative_down_becomes_positive_up(self):
        ned = np.array([0.0, 0.0, -100.0])
        xyz = ned_to_xyz(ned)
        assert xyz[2] == pytest.approx(100.0)

    def test_output_shape(self):
        assert ned_to_xyz(np.array([1.0, 2.0, 3.0])).shape == (3,)


class TestXyzToNed:
    def test_known_conversion(self):
        xyz = np.array([2.0, 1.0, -3.0])  # X=East, Y=North, Z=Up
        ned = xyz_to_ned(xyz)
        # N=xyz[1], E=xyz[0], D=-xyz[2]
        np.testing.assert_array_equal(ned, [1.0, 2.0, 3.0])

    def test_zeros(self):
        np.testing.assert_array_equal(xyz_to_ned(np.zeros(3)), np.zeros(3))

    def test_roundtrip(self):
        original = np.array([5.0, -3.0, 10.0])
        np.testing.assert_allclose(xyz_to_ned(ned_to_xyz(original)), original)

    def test_roundtrip_reverse(self):
        original = np.array([1.0, 2.0, -4.0])
        np.testing.assert_allclose(ned_to_xyz(xyz_to_ned(original)), original)


class TestGridToNed:
    def test_origin(self):
        ned = grid_to_ned(0, 0, 0.0)
        np.testing.assert_array_equal(ned, [0.0, 0.0, 0.0])

    def test_default_grid_size(self):
        ned = grid_to_ned(3, 2, 50.0)
        # N = grid_y * 10 = 20, E = grid_x * 10 = 30, D = -alt = -50
        np.testing.assert_array_equal(ned, [20.0, 30.0, -50.0])

    def test_custom_grid_size(self):
        ned = grid_to_ned(1, 1, 0.0, grid_size_m=100.0)
        np.testing.assert_array_equal(ned, [100.0, 100.0, 0.0])

    def test_altitude_negative_down(self):
        ned = grid_to_ned(0, 0, 200.0)
        assert ned[2] == pytest.approx(-200.0)


class TestNedToGrid:
    def test_origin(self):
        gx, gy = ned_to_grid(np.array([0.0, 0.0, 0.0]))
        assert gx == 0
        assert gy == 0

    def test_known_grid(self):
        ned = np.array([20.0, 30.0, -50.0])  # N=20, E=30
        gx, gy = ned_to_grid(ned)
        # gx = int(ned[1]/10) = 3, gy = int(ned[0]/10) = 2
        assert gx == 3
        assert gy == 2

    def test_custom_grid_size(self):
        ned = np.array([100.0, 100.0, 0.0])
        gx, gy = ned_to_grid(ned, grid_size_m=100.0)
        assert gx == 1
        assert gy == 1

    def test_returns_ints(self):
        gx, gy = ned_to_grid(np.array([15.5, 25.7, 0.0]))
        assert isinstance(gx, int)
        assert isinstance(gy, int)

    def test_roundtrip_with_grid_to_ned(self):
        gx, gy = ned_to_grid(grid_to_ned(5, 3, 10.0))
        assert gx == 5
        assert gy == 3
