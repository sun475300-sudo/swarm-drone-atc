"""Voronoi 공역 분할 테스트"""
import numpy as np
import pytest
from simulation.voronoi_airspace.voronoi_partition import (
    compute_voronoi_partition, AirspaceCell,
)

pytestmark = pytest.mark.unit


class TestVoronoiPartition:
    def test_empty_dict_returns_empty(self):
        result = compute_voronoi_partition(
            {}, {"x": [-5000, 5000], "y": [-5000, 5000]}
        )
        assert result == {}

    def test_single_drone_full_airspace(self):
        result = compute_voronoi_partition(
            {"DR001": np.array([0, 0, 60])},
            {"x": [-5000, 5000], "y": [-5000, 5000]},
        )
        assert "DR001" in result
        assert isinstance(result["DR001"], AirspaceCell)

    def test_two_drones_two_cells(self):
        positions = {
            "DR001": np.array([-2000, 0, 60]),
            "DR002": np.array([2000, 0, 60]),
        }
        bounds = {"x": [-5000, 5000], "y": [-5000, 5000]}
        result = compute_voronoi_partition(positions, bounds)
        assert len(result) == 2
        assert "DR001" in result
        assert "DR002" in result

    def test_three_drones(self):
        positions = {
            "DR001": np.array([-2000, -2000, 60]),
            "DR002": np.array([2000, -2000, 60]),
            "DR003": np.array([0, 2000, 60]),
        }
        bounds = {"x": [-5000, 5000], "y": [-5000, 5000]}
        result = compute_voronoi_partition(positions, bounds)
        assert len(result) == 3
        for cell in result.values():
            assert cell.area_km2 > 0

    def test_cell_has_vertices(self):
        positions = {
            f"DR{i:03d}": np.array([np.cos(i) * 2000, np.sin(i) * 2000, 60])
            for i in range(5)
        }
        bounds = {"x": [-5000, 5000], "y": [-5000, 5000]}
        result = compute_voronoi_partition(positions, bounds)
        for cell in result.values():
            assert len(cell.vertices) >= 3
