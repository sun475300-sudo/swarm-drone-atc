"""
좌표계 변환 유틸리티 단위 테스트
ned_to_xyz, xyz_to_ned, grid_to_ned, ned_to_grid 전체 커버
"""
from __future__ import annotations

import numpy as np
import pytest

from src.airspace_control.utils.coordinate_systems import (
    ned_to_xyz,
    xyz_to_ned,
    grid_to_ned,
    ned_to_grid,
)


class TestNedToXyz:
    def test_origin(self):
        result = ned_to_xyz(np.array([0.0, 0.0, 0.0]))
        assert np.allclose(result, [0.0, 0.0, 0.0])

    def test_north_becomes_y(self):
        """NED의 North → XYZ의 Y"""
        result = ned_to_xyz(np.array([10.0, 0.0, 0.0]))
        assert result[1] == pytest.approx(10.0)
        assert result[0] == pytest.approx(0.0)

    def test_east_becomes_x(self):
        """NED의 East → XYZ의 X"""
        result = ned_to_xyz(np.array([0.0, 20.0, 0.0]))
        assert result[0] == pytest.approx(20.0)

    def test_down_becomes_negative_z(self):
        """NED의 Down → XYZ의 -Z (Up)"""
        result = ned_to_xyz(np.array([0.0, 0.0, 5.0]))
        assert result[2] == pytest.approx(-5.0)

    def test_roundtrip(self):
        """NED → XYZ → NED 왕복 변환"""
        ned = np.array([3.0, 7.0, -2.0])
        assert np.allclose(xyz_to_ned(ned_to_xyz(ned)), ned)


class TestXyzToNed:
    def test_origin(self):
        result = xyz_to_ned(np.array([0.0, 0.0, 0.0]))
        assert np.allclose(result, [0.0, 0.0, 0.0])

    def test_x_becomes_east(self):
        result = xyz_to_ned(np.array([10.0, 0.0, 0.0]))
        assert result[1] == pytest.approx(10.0)  # East

    def test_y_becomes_north(self):
        result = xyz_to_ned(np.array([0.0, 10.0, 0.0]))
        assert result[0] == pytest.approx(10.0)  # North

    def test_z_becomes_negative_down(self):
        result = xyz_to_ned(np.array([0.0, 0.0, 10.0]))
        assert result[2] == pytest.approx(-10.0)  # Down


class TestGridToNed:
    def test_origin(self):
        result = grid_to_ned(0.0, 0.0, 0.0)
        assert np.allclose(result, [0.0, 0.0, 0.0])

    def test_grid_mapping(self):
        """grid_x → East(NED[1]), grid_y → North(NED[0])"""
        result = grid_to_ned(3.0, 5.0, 100.0, grid_size_m=10.0)
        assert result[0] == pytest.approx(50.0)   # north = grid_y * size
        assert result[1] == pytest.approx(30.0)   # east = grid_x * size
        assert result[2] == pytest.approx(-100.0)  # down = -alt

    def test_custom_grid_size(self):
        result = grid_to_ned(1.0, 1.0, 0.0, grid_size_m=50.0)
        assert result[0] == pytest.approx(50.0)
        assert result[1] == pytest.approx(50.0)


class TestNedToGrid:
    def test_origin(self):
        gx, gy = ned_to_grid(np.array([0.0, 0.0, 0.0]))
        assert gx == 0 and gy == 0

    def test_positive(self):
        ned = np.array([50.0, 30.0, -60.0])
        gx, gy = ned_to_grid(ned, grid_size_m=10.0)
        assert gx == 3   # east / grid_size
        assert gy == 5   # north / grid_size

    def test_roundtrip_with_grid_to_ned(self):
        """grid → ned → grid 왕복"""
        gx_orig, gy_orig = 4, 7
        ned = grid_to_ned(float(gx_orig), float(gy_orig), 60.0, grid_size_m=10.0)
        gx, gy = ned_to_grid(ned, grid_size_m=10.0)
        assert gx == gx_orig
        assert gy == gy_orig
