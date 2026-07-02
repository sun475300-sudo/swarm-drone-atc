"""TRANSCENDENCE Phase 227 — KMA 풍속장 파서·보간·어댑터 회귀."""

from __future__ import annotations

import numpy as np
import pytest

from simulation.kma_wind_field import (
    GRID_SPACING_M,
    KmaGridPoint,
    KmaWindField,
    kma_wind_adapter,
    load_sample_field,
    parse_kma_items,
)


class TestParseKmaItems:
    def test_uuu_vvv_pair_parsed(self) -> None:
        pts = parse_kma_items([
            {"nx": 1, "ny": 1, "category": "UUU", "obsrValue": "2.5"},
            {"nx": 1, "ny": 1, "category": "VVV", "obsrValue": "-1.0"},
        ])
        assert pts == [KmaGridPoint(nx=1, ny=1, u_ms=2.5, v_ms=-1.0)]

    def test_wsd_vec_fallback_west_wind(self) -> None:
        # VEC=270 (서풍 — 서쪽에서 불어옴) → 공기는 동쪽으로: u=+WSD, v≈0
        pts = parse_kma_items([
            {"nx": 2, "ny": 2, "category": "WSD", "obsrValue": "5.0"},
            {"nx": 2, "ny": 2, "category": "VEC", "obsrValue": "270"},
        ])
        assert len(pts) == 1
        assert pts[0].u_ms == pytest.approx(5.0, abs=1e-9)
        assert pts[0].v_ms == pytest.approx(0.0, abs=1e-9)

    def test_missing_value_code_dropped(self) -> None:
        pts = parse_kma_items([
            {"nx": 3, "ny": 3, "category": "UUU", "obsrValue": "-999"},
            {"nx": 3, "ny": 3, "category": "VVV", "obsrValue": "1.0"},
        ])
        assert pts == []  # UUU 결측 → 셀 폐기 (silent NaN 금지)

    def test_malformed_items_tolerated(self) -> None:
        pts = parse_kma_items([
            {"category": "UUU"},                      # nx/ny 없음
            {"nx": "x", "ny": 1, "category": "UUU", "obsrValue": "1"},  # 비수치 nx
            {"nx": 4, "ny": 4, "category": "UUU", "obsrValue": "abc"},  # 비수치 값
        ])
        assert pts == []

    def test_deterministic_sorted_output(self) -> None:
        items = [
            {"nx": 9, "ny": 1, "category": "UUU", "obsrValue": "1"},
            {"nx": 9, "ny": 1, "category": "VVV", "obsrValue": "1"},
            {"nx": 1, "ny": 1, "category": "UUU", "obsrValue": "1"},
            {"nx": 1, "ny": 1, "category": "VVV", "obsrValue": "1"},
        ]
        pts = parse_kma_items(items)
        assert [(p.nx, p.ny) for p in pts] == [(1, 1), (9, 1)]  # 정렬 — 결정적


class TestKmaWindField:
    def _field(self) -> KmaWindField:
        return KmaWindField([
            KmaGridPoint(0, 0, u_ms=0.0, v_ms=0.0),
            KmaGridPoint(1, 0, u_ms=4.0, v_ms=0.0),
            KmaGridPoint(0, 1, u_ms=0.0, v_ms=2.0),
            KmaGridPoint(1, 1, u_ms=4.0, v_ms=2.0),
        ])

    def test_empty_field_rejected(self) -> None:
        with pytest.raises(ValueError):
            KmaWindField([])

    def test_exact_grid_point(self) -> None:
        f = self._field()
        assert f.wind_at(0.0, 0.0) == (0.0, 0.0)
        assert f.wind_at(GRID_SPACING_M, GRID_SPACING_M) == (4.0, 2.0)

    def test_bilinear_midpoint(self) -> None:
        f = self._field()
        u, v = f.wind_at(GRID_SPACING_M / 2, GRID_SPACING_M / 2)
        assert u == pytest.approx(2.0)
        assert v == pytest.approx(1.0)

    def test_missing_neighbors_nearest_fallback(self) -> None:
        f = KmaWindField([KmaGridPoint(0, 0, u_ms=3.0, v_ms=-1.0)])
        # 격자 밖 먼 좌표 → 유일 격자점 폴백
        assert f.wind_at(50_000.0, 50_000.0) == (3.0, -1.0)


class TestAdapterAndSample:
    def test_sample_field_loads(self) -> None:
        f = load_sample_field()
        # UUU/VVV 3셀 + WSD/VEC 폴백 1셀 = 4, 결측 -999 셀 폐기
        assert f.cell_count == 4

    def test_adapter_interface_matches_sim(self) -> None:
        """SwarmSimulator.wind_models 계약: get_wind_vector(pos, t) → ndarray(3)."""
        adapter = kma_wind_adapter(load_sample_field())
        vec = adapter.get_wind_vector(np.array([500.0, 500.0, 60.0]), t=1.0)
        assert isinstance(vec, np.ndarray) and vec.shape == (3,)
        assert vec[2] == 0.0  # 연직 성분 미제공 — 정직 공시
        assert np.all(np.isfinite(vec))
