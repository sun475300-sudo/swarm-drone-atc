"""ODYSSEY Phase 469 — 정책 영향 비교 모델 테스트."""
import math
from dataclasses import replace

import pytest

from simulation.policy_impact import (
    PolicyConfig,
    airspace_capacity,
    altitude_layers,
    compare_policies,
    lateral_cell_area_m2,
    per_layer_capacity,
    utilization,
)

pytestmark = pytest.mark.unit


def _policy(**overrides) -> PolicyConfig:
    base = dict(
        lateral_min_m=50.0,
        vertical_min_m=15.0,
        min_altitude_m=0.0,
        max_altitude_m=120.0,
        area_m2=1_000_000.0,  # 1 km²
    )
    base.update(overrides)
    return PolicyConfig(**base)


class TestPolicyConfigValidation:
    def test_rejects_nonpositive_lateral(self):
        with pytest.raises(ValueError):
            _policy(lateral_min_m=0.0)

    def test_rejects_nonpositive_vertical(self):
        with pytest.raises(ValueError):
            _policy(vertical_min_m=-1.0)

    def test_rejects_nonpositive_area(self):
        with pytest.raises(ValueError):
            _policy(area_m2=0.0)

    def test_rejects_max_below_min_altitude(self):
        with pytest.raises(ValueError):
            _policy(min_altitude_m=120.0, max_altitude_m=30.0)

    def test_rejects_negative_min_altitude(self):
        with pytest.raises(ValueError):
            _policy(min_altitude_m=-10.0)

    def test_rejects_area_smaller_than_one_cell(self):
        # cell area for 50m separation ≈ 2165 m²; 100 m² can't fit a single drone
        with pytest.raises(ValueError):
            _policy(area_m2=100.0, lateral_min_m=50.0)

    def test_altitude_band_property(self):
        assert _policy(min_altitude_m=30.0, max_altitude_m=120.0).altitude_band_m == 90.0


class TestAltitudeLayers:
    def test_endpoints_included(self):
        # band 90, vsep 15 → 90//15 + 1 = 7 layers (0,15,...,90 offsets)
        assert altitude_layers(_policy(min_altitude_m=0.0, max_altitude_m=90.0)) == 7

    def test_minimum_one_layer_when_band_smaller_than_vsep(self):
        assert altitude_layers(_policy(min_altitude_m=0.0, max_altitude_m=10.0)) == 1

    def test_tighter_vertical_yields_more_layers(self):
        loose = altitude_layers(_policy(vertical_min_m=30.0))
        tight = altitude_layers(_policy(vertical_min_m=10.0))
        assert tight > loose

    def test_higher_ceiling_yields_more_layers(self):
        low = altitude_layers(_policy(max_altitude_m=60.0))
        high = altitude_layers(_policy(max_altitude_m=120.0))
        assert high > low


class TestLateralCellArea:
    def test_hex_packing_formula(self):
        # (sqrt(3)/2) * 50^2
        expected = (math.sqrt(3.0) / 2.0) * 50.0**2
        assert lateral_cell_area_m2(_policy(lateral_min_m=50.0)) == pytest.approx(expected)

    def test_wider_separation_larger_cell(self):
        assert lateral_cell_area_m2(_policy(lateral_min_m=70.0)) > lateral_cell_area_m2(
            _policy(lateral_min_m=50.0)
        )


class TestCapacity:
    def test_capacity_is_layers_times_per_layer(self):
        p = _policy()
        assert airspace_capacity(p) == altitude_layers(p) * per_layer_capacity(p)

    def test_tighter_lateral_reduces_capacity(self):
        loose = airspace_capacity(_policy(lateral_min_m=50.0))
        tight = airspace_capacity(_policy(lateral_min_m=80.0))
        assert tight < loose

    def test_higher_ceiling_increases_capacity(self):
        low = airspace_capacity(_policy(max_altitude_m=60.0))
        high = airspace_capacity(_policy(max_altitude_m=120.0))
        assert high > low

    def test_deterministic(self):
        assert airspace_capacity(_policy()) == airspace_capacity(_policy())


class TestUtilization:
    def test_half_capacity(self):
        p = _policy()
        cap = airspace_capacity(p)
        assert utilization(p, cap // 2) == pytest.approx((cap // 2) / cap)

    def test_oversaturation_above_one(self):
        p = _policy()
        assert utilization(p, airspace_capacity(p) * 2) > 1.0

    def test_zero_drones_zero_utilization(self):
        assert utilization(_policy(), 0) == 0.0

    def test_negative_count_raises(self):
        with pytest.raises(ValueError):
            utilization(_policy(), -1)


class TestComparePolicies:
    def test_tighter_lateral_reports_capacity_loss(self):
        baseline = _policy(lateral_min_m=50.0)
        proposed = _policy(lateral_min_m=70.0)
        cmp = compare_policies(baseline, proposed, drone_count=100)
        assert cmp.capacity_delta < 0
        assert cmp.capacity_pct_change < 0.0
        assert cmp.proposed_utilization > cmp.baseline_utilization

    def test_relaxed_ceiling_reports_capacity_gain(self):
        baseline = _policy(max_altitude_m=90.0)
        proposed = _policy(max_altitude_m=150.0)
        cmp = compare_policies(baseline, proposed, drone_count=100)
        assert cmp.capacity_delta > 0
        assert cmp.capacity_pct_change > 0.0

    def test_identical_policies_zero_delta(self):
        cmp = compare_policies(_policy(), _policy(), drone_count=100)
        assert cmp.capacity_delta == 0
        assert cmp.capacity_pct_change == 0.0

    def test_oversaturation_flag(self):
        baseline = _policy(lateral_min_m=50.0)
        proposed = _policy(lateral_min_m=50.0)
        count = airspace_capacity(proposed) + 1
        cmp = compare_policies(baseline, proposed, drone_count=count)
        assert cmp.is_oversaturated is True

    def test_summary_contains_arrow_and_pct(self):
        cmp = compare_policies(_policy(lateral_min_m=50.0), _policy(lateral_min_m=70.0), 100)
        s = cmp.summary()
        assert "→" in s and "%" in s

    def test_summary_unchanged_for_identical(self):
        cmp = compare_policies(_policy(), _policy(), 100)
        assert "변동없음" in cmp.summary()
        assert "증가" not in cmp.summary()

    def test_frozen_immutable(self):
        cmp = compare_policies(_policy(), _policy(), 100)
        with pytest.raises(Exception):
            cmp.baseline_capacity = 0  # type: ignore[misc]


class TestFromConfig:
    def test_loads_real_config_keys(self):
        p = PolicyConfig.from_config()
        # config: lateral 50, vertical 15, z [0,0.12]km, drones.min_altitude_m 30, area 100km²
        assert p.lateral_min_m == 50.0
        assert p.vertical_min_m == 15.0
        assert p.max_altitude_m == pytest.approx(120.0)
        assert p.area_m2 == pytest.approx(100_000_000.0)

    def test_uses_drone_floor_not_zero(self):
        # 운용 바닥은 z[0]=0 이 아니라 drones.min_altitude_m=30 (더 제약적)
        p = PolicyConfig.from_config()
        assert p.min_altitude_m == pytest.approx(30.0)

    def test_missing_config_path_raises(self):
        with pytest.raises(FileNotFoundError):
            PolicyConfig.from_config(path="nonexistent_config_xyz.yaml")

    def test_config_policy_capacity_positive(self):
        assert airspace_capacity(PolicyConfig.from_config()) > 0

    def test_replace_for_proposed_policy(self):
        base = PolicyConfig.from_config()
        proposed = replace(base, lateral_min_m=base.lateral_min_m * 1.4)
        cmp = compare_policies(base, proposed, 100)
        assert cmp.capacity_delta < 0
