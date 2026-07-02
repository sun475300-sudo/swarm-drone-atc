"""TRANSCENDENCE Phase 230 — LiPo 방전 곡선·사이클 노화 회귀."""

from __future__ import annotations

import pytest

from simulation.battery_aging import LipoAgingModel, LipoCell, soc_to_voltage


class TestSocToVoltage:
    def test_endpoints(self) -> None:
        assert soc_to_voltage(0.0) == 3.30
        assert soc_to_voltage(1.0) == 4.20

    def test_nominal_plateau(self) -> None:
        # LiPo 평탄 구간: SoC 0.2~0.5 에서 3.70~3.78V
        assert 3.70 <= soc_to_voltage(0.35) <= 3.78

    def test_monotonic_nondecreasing(self) -> None:
        vs = [soc_to_voltage(s / 100) for s in range(101)]
        assert all(a <= b for a, b in zip(vs, vs[1:]))

    def test_out_of_range_clamped(self) -> None:
        assert soc_to_voltage(-0.5) == 3.30
        assert soc_to_voltage(1.5) == 4.20


class TestLipoAgingModel:
    def test_new_pack_full_capacity(self) -> None:
        m = LipoAgingModel(LipoCell(cycles=0.0))
        assert m.capacity_factor() == 1.0
        assert m.effective_capacity_wh() == 80.0

    def test_literature_anchor_points(self) -> None:
        # 문헌 대표값 결속: 300cyc ≈ 90%, 500cyc ≈ 80%
        assert LipoAgingModel(LipoCell(cycles=300)).capacity_factor() == pytest.approx(0.90)
        assert LipoAgingModel(LipoCell(cycles=500)).capacity_factor() == pytest.approx(0.80)

    def test_aging_monotonic_decrease(self) -> None:
        caps = [LipoAgingModel(LipoCell(cycles=c)).capacity_factor() for c in (0, 100, 300, 500, 800, 2000)]
        assert all(a >= b for a, b in zip(caps, caps[1:]))
        assert caps[-1] == 0.65  # 800+ 클램프

    def test_pack_voltage_series_scaling(self) -> None:
        m = LipoAgingModel(LipoCell(cells_series=4))
        assert m.pack_voltage(1.0) == pytest.approx(16.8)  # 4S 만충
        assert m.pack_voltage(0.0) == pytest.approx(13.2)

    def test_endurance_scale_matches_capacity(self) -> None:
        m = LipoAgingModel(LipoCell(cycles=500))
        assert m.endurance_scale() == m.capacity_factor()

    def test_low_voltage_cutoff_soc_deterministic(self) -> None:
        m = LipoAgingModel(LipoCell())
        soc1 = m.low_voltage_cutoff_soc(3.5)
        soc2 = m.low_voltage_cutoff_soc(3.5)
        assert soc1 == soc2  # 결정성
        # 3.5V 는 곡선상 SoC 0.05 지점 — 근방이어야
        assert 0.03 <= soc1 <= 0.08
        assert soc_to_voltage(soc1) >= 3.5

    def test_invalid_spec_rejected(self) -> None:
        with pytest.raises(ValueError):
            LipoAgingModel(LipoCell(cells_series=0))
        with pytest.raises(ValueError):
            LipoAgingModel(LipoCell(capacity_wh_new=0))
        with pytest.raises(ValueError):
            LipoAgingModel(LipoCell(cycles=-1))
