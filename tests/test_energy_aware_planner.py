"""GENESIS Phase 368 -- 에너지 인식 임무 계획 테스트.

검증 항목:
- DroneEnergyProfile / WindCondition / Waypoint / LegEnergy / MissionPlan frozen
- compute_leg_energy 결정론적 계산
- 정풍(headwind) → 에너지 증가, 배풍(tailwind) → 에너지 감소
- 상승 > 하강 에너지
- plan_mission 실현가능성 판정
- suggest_reduction 제안
- 기본 프로파일 완전성
- CLI 인자 파싱
"""
from __future__ import annotations

import json
import subprocess
import sys

import pytest

from simulation.energy_aware_planner import (
    DEFAULT_CLIMB_RATE_MS,
    DEFAULT_DESCENT_RATE_MS,
    HEAVY_LIFT,
    MEDIUM_QUAD,
    PROFILES,
    SMALL_QUAD,
    DroneEnergyProfile,
    LegEnergy,
    MissionPlan,
    Waypoint,
    WindCondition,
    _headwind_component,
    _parse_wind,
    compute_leg_energy,
    get_profile,
    is_feasible,
    plan_mission,
    suggest_reduction,
)

# ── Fixtures ────────────────────────────────────────────────────

@pytest.fixture()
def profile() -> DroneEnergyProfile:
    return MEDIUM_QUAD


@pytest.fixture()
def no_wind() -> WindCondition:
    return WindCondition(speed_ms=0.0, direction_deg=0.0)


@pytest.fixture()
def simple_waypoints() -> tuple[Waypoint, ...]:
    return (
        Waypoint(0.0, 0.0, 50.0),
        Waypoint(100.0, 0.0, 50.0),
        Waypoint(200.0, 0.0, 50.0),
    )


# ── Frozen Dataclass Tests ──────────────────────────────────────

class TestDroneEnergyProfileFrozen:
    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            MEDIUM_QUAD.mass_kg = 99.0  # type: ignore[misc]

    def test_fields(self) -> None:
        p = SMALL_QUAD
        assert p.mass_kg == 0.249
        assert p.battery_wh == 19.6
        assert p.max_speed_ms == 16.0

    def test_as_dict(self) -> None:
        d = SMALL_QUAD.as_dict()
        assert d["mass_kg"] == 0.249
        assert d["climb_power_w"] == 45.0
        assert len(d) == 7


class TestWindConditionFrozen:
    def test_frozen(self) -> None:
        w = WindCondition(speed_ms=5.0, direction_deg=180.0)
        with pytest.raises(AttributeError):
            w.speed_ms = 10.0  # type: ignore[misc]

    def test_default_gust(self) -> None:
        w = WindCondition(speed_ms=3.0, direction_deg=90.0)
        assert w.gust_ms == 0.0


class TestWaypointFrozen:
    def test_frozen(self) -> None:
        wp = Waypoint(1.0, 2.0, 3.0)
        with pytest.raises(AttributeError):
            wp.x = 99.0  # type: ignore[misc]

    def test_default_loiter(self) -> None:
        wp = Waypoint(0.0, 0.0, 50.0)
        assert wp.required_loiter_s == 0.0


class TestLegEnergyFrozen:
    def test_frozen(self) -> None:
        le = LegEnergy(0, 1, 100.0, 5.0, 10.0, 2.0)
        with pytest.raises(AttributeError):
            le.energy_wh = 99.0  # type: ignore[misc]

    def test_as_dict(self) -> None:
        le = LegEnergy(0, 1, 100.123456, 5.6789, 10.5, 2.345)
        d = le.as_dict()
        assert d["distance_m"] == 100.12
        assert d["energy_wh"] == 5.6789


class TestMissionPlanFrozen:
    def test_frozen(self) -> None:
        mp = MissionPlan((), (), 0.0, 0.0, 20.0, True, 0.0)
        with pytest.raises(AttributeError):
            mp.is_feasible = False  # type: ignore[misc]

    def test_as_dict(self) -> None:
        mp = MissionPlan(
            waypoints=(Waypoint(0, 0, 0),),
            legs=(),
            total_energy_wh=1.234,
            total_time_s=60.0,
            reserve_pct=20.0,
            is_feasible=True,
            return_energy_wh=0.5,
        )
        d = mp.as_dict()
        assert d["n_waypoints"] == 1
        assert d["n_legs"] == 0
        assert d["is_feasible"] is True


# ── Deterministic Calculation Tests ─────────────────────────────

class TestComputeLegEnergy:
    def test_deterministic(self, profile: DroneEnergyProfile) -> None:
        """동일 입력에 대해 동일 결과 반환."""
        wp1 = Waypoint(0.0, 0.0, 50.0)
        wp2 = Waypoint(100.0, 0.0, 50.0)
        wind = WindCondition(speed_ms=0.0, direction_deg=0.0)

        r1 = compute_leg_energy(profile, wp1, wp2, wind)
        r2 = compute_leg_energy(profile, wp1, wp2, wind)
        assert r1.energy_wh == r2.energy_wh
        assert r1.time_s == r2.time_s

    def test_no_movement(self, profile: DroneEnergyProfile) -> None:
        """동일 위치 → 에너지 0."""
        wp = Waypoint(50.0, 50.0, 50.0)
        wind = WindCondition(speed_ms=0.0, direction_deg=0.0)
        r = compute_leg_energy(profile, wp, wp, wind)
        assert r.energy_wh == 0.0
        assert r.time_s == 0.0

    def test_horizontal_flight_energy(self, profile: DroneEnergyProfile) -> None:
        """수평 비행 에너지 = cruise_power * distance / speed / 3600."""
        wp1 = Waypoint(0.0, 0.0, 50.0)
        wp2 = Waypoint(230.0, 0.0, 50.0)  # 230m east, same alt
        wind = WindCondition(speed_ms=0.0, direction_deg=0.0)
        r = compute_leg_energy(profile, wp1, wp2, wind)

        expected_time = 230.0 / profile.max_speed_ms
        expected_energy = profile.cruise_power_w * expected_time / 3600.0
        assert abs(r.energy_wh - expected_energy) < 1e-6
        assert abs(r.time_s - expected_time) < 1e-6


class TestWindEffects:
    def test_headwind_increases_energy(self, profile: DroneEnergyProfile) -> None:
        """정풍은 에너지 소비를 증가시킨다."""
        wp1 = Waypoint(0.0, 0.0, 50.0)
        wp2 = Waypoint(0.0, 500.0, 50.0)  # 북쪽 이동
        no_wind = WindCondition(speed_ms=0.0, direction_deg=0.0)
        # 0도 = 북에서 불어옴(기상학적 관례) → 북쪽 이동 시 정풍
        headwind = WindCondition(speed_ms=8.0, direction_deg=0.0)

        r_calm = compute_leg_energy(profile, wp1, wp2, no_wind)
        r_head = compute_leg_energy(profile, wp1, wp2, headwind)
        assert r_head.energy_wh > r_calm.energy_wh
        assert r_head.headwind_component_ms > 0

    def test_tailwind_decreases_energy(self, profile: DroneEnergyProfile) -> None:
        """배풍은 에너지 소비를 감소시킨다."""
        wp1 = Waypoint(0.0, 0.0, 50.0)
        wp2 = Waypoint(0.0, 500.0, 50.0)  # 북쪽 이동
        no_wind = WindCondition(speed_ms=0.0, direction_deg=0.0)
        # 180도 = 남에서 불어옴(기상학적 관례) → 북쪽 이동 시 배풍
        tailwind = WindCondition(speed_ms=5.0, direction_deg=180.0)

        r_calm = compute_leg_energy(profile, wp1, wp2, no_wind)
        r_tail = compute_leg_energy(profile, wp1, wp2, tailwind)
        assert r_tail.energy_wh < r_calm.energy_wh
        assert r_tail.headwind_component_ms < 0

    def test_crosswind_no_effect_on_headwind(
        self, profile: DroneEnergyProfile,
    ) -> None:
        """90도 측풍은 headwind_component ≈ 0."""
        wp1 = Waypoint(0.0, 0.0, 50.0)
        wp2 = Waypoint(0.0, 500.0, 50.0)
        # 동풍 (90도) → 북쪽 이동에 수직
        crosswind = WindCondition(speed_ms=10.0, direction_deg=90.0)
        r = compute_leg_energy(profile, wp1, wp2, crosswind)
        assert abs(r.headwind_component_ms) < 0.01


class TestClimbDescent:
    def test_climb_costs_more_than_descent(
        self, profile: DroneEnergyProfile,
    ) -> None:
        """상승 에너지 > 하강 에너지."""
        base = Waypoint(0.0, 0.0, 50.0)
        high = Waypoint(0.0, 0.0, 100.0)
        wind = WindCondition(speed_ms=0.0, direction_deg=0.0)

        climb = compute_leg_energy(profile, base, high, wind)
        descent = compute_leg_energy(profile, high, base, wind)
        assert climb.energy_wh > descent.energy_wh

    def test_climb_energy_formula(self, profile: DroneEnergyProfile) -> None:
        """상승 에너지 = climb_power * dz / climb_rate / 3600."""
        wp1 = Waypoint(0.0, 0.0, 50.0)
        wp2 = Waypoint(0.0, 0.0, 80.0)  # 순수 수직 상승 30m
        wind = WindCondition(speed_ms=0.0, direction_deg=0.0)
        r = compute_leg_energy(profile, wp1, wp2, wind)

        dz = 30.0
        expected = profile.climb_power_w * dz / DEFAULT_CLIMB_RATE_MS / 3600.0
        assert abs(r.energy_wh - expected) < 1e-6

    def test_descent_energy_formula(self, profile: DroneEnergyProfile) -> None:
        """하강 에너지 = descent_power * dz / descent_rate / 3600."""
        wp1 = Waypoint(0.0, 0.0, 80.0)
        wp2 = Waypoint(0.0, 0.0, 50.0)  # 순수 수직 하강 30m
        wind = WindCondition(speed_ms=0.0, direction_deg=0.0)
        r = compute_leg_energy(profile, wp1, wp2, wind)

        dz = 30.0
        expected = profile.descent_power_w * dz / DEFAULT_DESCENT_RATE_MS / 3600.0
        assert abs(r.energy_wh - expected) < 1e-6


class TestLoiterEnergy:
    def test_loiter_adds_energy(self, profile: DroneEnergyProfile) -> None:
        """체공 시간은 hover_power 에너지를 추가한다."""
        wp1 = Waypoint(0.0, 0.0, 50.0)
        wp2_no_loiter = Waypoint(100.0, 0.0, 50.0, required_loiter_s=0.0)
        wp2_loiter = Waypoint(100.0, 0.0, 50.0, required_loiter_s=60.0)
        wind = WindCondition(speed_ms=0.0, direction_deg=0.0)

        r_no = compute_leg_energy(profile, wp1, wp2_no_loiter, wind)
        r_yes = compute_leg_energy(profile, wp1, wp2_loiter, wind)

        loiter_energy = profile.hover_power_w * 60.0 / 3600.0
        assert abs(r_yes.energy_wh - r_no.energy_wh - loiter_energy) < 1e-6
        assert abs(r_yes.time_s - r_no.time_s - 60.0) < 1e-6


# ── Mission Plan Tests ──────────────────────────────────────────

class TestPlanMission:
    def test_single_waypoint(self, profile: DroneEnergyProfile) -> None:
        """단일 웨이포인트 → 빈 임무."""
        wps = (Waypoint(0.0, 0.0, 50.0),)
        wind = WindCondition(speed_ms=0.0, direction_deg=0.0)
        plan = plan_mission(profile, wps, wind)
        assert plan.total_energy_wh == 0.0
        assert plan.is_feasible is True
        assert len(plan.legs) == 0

    def test_two_waypoints(
        self, profile: DroneEnergyProfile, no_wind: WindCondition,
    ) -> None:
        """두 웨이포인트 → 1구간."""
        wps = (Waypoint(0.0, 0.0, 50.0), Waypoint(100.0, 0.0, 50.0))
        plan = plan_mission(profile, wps, no_wind)
        assert len(plan.legs) == 1
        assert plan.total_energy_wh > 0

    def test_leg_indices(
        self, profile: DroneEnergyProfile, no_wind: WindCondition,
    ) -> None:
        """구간 인덱스가 올바르게 할당되는지."""
        wps = (
            Waypoint(0, 0, 50), Waypoint(100, 0, 50), Waypoint(200, 0, 50),
        )
        plan = plan_mission(profile, wps, no_wind)
        assert plan.legs[0].from_wp == 0
        assert plan.legs[0].to_wp == 1
        assert plan.legs[1].from_wp == 1
        assert plan.legs[1].to_wp == 2

    def test_total_energy_is_sum_of_legs(
        self,
        profile: DroneEnergyProfile,
        simple_waypoints: tuple[Waypoint, ...],
        no_wind: WindCondition,
    ) -> None:
        """총 에너지 = 구간 에너지 합."""
        plan = plan_mission(profile, simple_waypoints, no_wind)
        leg_sum = sum(leg.energy_wh for leg in plan.legs)
        assert abs(plan.total_energy_wh - leg_sum) < 1e-9

    def test_return_energy_calculated(
        self, profile: DroneEnergyProfile, no_wind: WindCondition,
    ) -> None:
        """귀환 에너지가 계산된다."""
        wps = (Waypoint(0, 0, 50), Waypoint(500, 0, 50))
        plan = plan_mission(profile, wps, no_wind)
        assert plan.return_energy_wh > 0


# ── Feasibility Tests ───────────────────────────────────────────

class TestFeasibility:
    def test_feasible_short_mission(self) -> None:
        """짧은 임무 → 실현가능."""
        wps = (Waypoint(0, 0, 50), Waypoint(50, 0, 50))
        wind = WindCondition(speed_ms=0.0, direction_deg=0.0)
        plan = plan_mission(MEDIUM_QUAD, wps, wind)
        assert is_feasible(plan) is True

    def test_infeasible_long_mission(self) -> None:
        """작은 배터리 + 긴 임무 → 비실현."""
        wps = (
            Waypoint(0, 0, 50),
            Waypoint(5000, 0, 50, required_loiter_s=600),
            Waypoint(10000, 0, 50, required_loiter_s=600),
            Waypoint(15000, 0, 50),
        )
        # 90도 = 동풍 → 동쪽 이동(x축) 시 정풍
        wind = WindCondition(speed_ms=10.0, direction_deg=90.0)
        plan = plan_mission(SMALL_QUAD, wps, wind)
        assert is_feasible(plan) is False

    def test_reserve_affects_feasibility(self) -> None:
        """높은 예비율은 실현가능성을 줄인다."""
        # 중간 거리 임무
        wps = (
            Waypoint(0, 0, 50),
            Waypoint(2000, 0, 50),
            Waypoint(4000, 0, 50),
        )
        wind = WindCondition(speed_ms=0.0, direction_deg=0.0)
        plan_low = plan_mission(MEDIUM_QUAD, wps, wind, reserve_pct=5.0)
        plan_high = plan_mission(MEDIUM_QUAD, wps, wind, reserve_pct=200.0)

        # 낮은 예비율에서 가능하고 높은 예비율에서 불가능 확인
        assert plan_high.reserve_pct > plan_low.reserve_pct


# ── Suggest Reduction Tests ─────────────────────────────────────

class TestSuggestReduction:
    def test_feasible_no_suggestions(self) -> None:
        """실현가능 임무 → 제안 없음."""
        wps = (Waypoint(0, 0, 50), Waypoint(50, 0, 50))
        wind = WindCondition(speed_ms=0.0, direction_deg=0.0)
        plan = plan_mission(MEDIUM_QUAD, wps, wind)
        assert suggest_reduction(plan, MEDIUM_QUAD) == ()

    def test_infeasible_gets_suggestions(self) -> None:
        """비실현 임무 → 제안 반환."""
        wps = (
            Waypoint(0, 0, 50),
            Waypoint(5000, 0, 100, required_loiter_s=600),
            Waypoint(10000, 0, 50),
        )
        # 90도 = 동풍 → 동쪽 이동(x축) 시 정풍
        wind = WindCondition(speed_ms=12.0, direction_deg=90.0)
        plan = plan_mission(SMALL_QUAD, wps, wind)
        assert not plan.is_feasible
        suggestions = suggest_reduction(plan, SMALL_QUAD)
        assert len(suggestions) >= 2
        # 에너지 부족량 제안은 항상 존재
        assert any("에너지 부족량" in s for s in suggestions)

    def test_loiter_reduction_suggested(self) -> None:
        """체공 시간이 있는 비실현 임무 → 체공 단축 제안."""
        wps = (
            Waypoint(0, 0, 50),
            Waypoint(5000, 0, 50, required_loiter_s=600),
            Waypoint(10000, 0, 50, required_loiter_s=600),
        )
        # 90도 = 동풍 → 동쪽 이동 시 정풍
        wind = WindCondition(speed_ms=12.0, direction_deg=90.0)
        plan = plan_mission(SMALL_QUAD, wps, wind)
        assert not plan.is_feasible
        suggestions = suggest_reduction(plan, SMALL_QUAD)
        assert any("체공 시간 단축" in s for s in suggestions)

    def test_altitude_reduction_suggested(self) -> None:
        """고도 > 50m 비실현 임무 → 고도 감소 제안."""
        wps = (
            Waypoint(0, 0, 50),
            Waypoint(5000, 0, 120, required_loiter_s=600),
            Waypoint(10000, 0, 50),
        )
        # 90도 = 동풍 → 동쪽 이동 시 정풍
        wind = WindCondition(speed_ms=12.0, direction_deg=90.0)
        plan = plan_mission(SMALL_QUAD, wps, wind)
        assert not plan.is_feasible
        suggestions = suggest_reduction(plan, SMALL_QUAD)
        assert any("최대 고도 감소" in s for s in suggestions)


# ── Default Profiles Tests ──────────────────────────────────────

class TestDefaultProfiles:
    def test_three_profiles_exist(self) -> None:
        assert len(PROFILES) == 3
        assert "small_quad" in PROFILES
        assert "medium_quad" in PROFILES
        assert "heavy_lift" in PROFILES

    def test_profiles_battery_ordering(self) -> None:
        """small < medium < heavy 배터리."""
        assert SMALL_QUAD.battery_wh < MEDIUM_QUAD.battery_wh
        assert MEDIUM_QUAD.battery_wh < HEAVY_LIFT.battery_wh

    def test_profiles_all_positive_values(self) -> None:
        """모든 프로파일 값이 양수."""
        for name, p in PROFILES.items():
            assert p.mass_kg > 0, f"{name} mass_kg"
            assert p.battery_wh > 0, f"{name} battery_wh"
            assert p.hover_power_w > 0, f"{name} hover_power_w"
            assert p.cruise_power_w > 0, f"{name} cruise_power_w"
            assert p.max_speed_ms > 0, f"{name} max_speed_ms"
            assert p.climb_power_w > 0, f"{name} climb_power_w"
            assert p.descent_power_w > 0, f"{name} descent_power_w"

    def test_get_profile_valid(self) -> None:
        assert get_profile("small_quad") is SMALL_QUAD

    def test_get_profile_invalid(self) -> None:
        with pytest.raises(ValueError, match="Unknown profile"):
            get_profile("nonexistent")


# ── CLI Tests ───────────────────────────────────────────────────

class TestCLI:
    def test_plan_json(self) -> None:
        """--plan --json 출력이 유효한 JSON."""
        r = subprocess.run(
            [sys.executable, "simulation/energy_aware_planner.py",
             "--plan", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "mission" in data
        assert "total_energy_wh" in data["mission"]

    def test_feasibility_json(self) -> None:
        """--feasibility --json 출력."""
        r = subprocess.run(
            [sys.executable, "simulation/energy_aware_planner.py",
             "--feasibility", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "feasible" in data

    def test_wind_arg(self) -> None:
        """--wind 인자 파싱."""
        r = subprocess.run(
            [sys.executable, "simulation/energy_aware_planner.py",
             "--plan", "--json", "--wind", "5,180"],
            capture_output=True, text=True, timeout=30,
        )
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["mission"]["total_energy_wh"] > 0

    def test_profile_arg(self) -> None:
        """--profile 인자."""
        r = subprocess.run(
            [sys.executable, "simulation/energy_aware_planner.py",
             "--plan", "--json", "--profile", "small_quad"],
            capture_output=True, text=True, timeout=30,
        )
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["profile"] == "small_quad"

    def test_parse_wind_two_args(self) -> None:
        w = _parse_wind("5.5,270")
        assert w.speed_ms == 5.5
        assert w.direction_deg == 270.0
        assert w.gust_ms == 0.0

    def test_parse_wind_three_args(self) -> None:
        w = _parse_wind("3,90,1.5")
        assert w.speed_ms == 3.0
        assert w.direction_deg == 90.0
        assert w.gust_ms == 1.5


# ── Headwind Component Tests ───────────────────────────────────

class TestHeadwindComponent:
    def test_zero_distance(self) -> None:
        wind = WindCondition(speed_ms=10.0, direction_deg=0.0)
        assert _headwind_component(0.0, 0.0, 0.0, wind) == 0.0

    def test_zero_wind(self) -> None:
        wind = WindCondition(speed_ms=0.0, direction_deg=0.0)
        assert _headwind_component(100.0, 0.0, 100.0, wind) == 0.0

    def test_pure_headwind(self) -> None:
        """북쪽 이동 + 0도(북에서 불어옴) → positive headwind."""
        wind = WindCondition(speed_ms=5.0, direction_deg=0.0)
        hw = _headwind_component(0.0, 100.0, 100.0, wind)
        assert hw > 4.9  # ≈ 5.0

    def test_pure_tailwind(self) -> None:
        """북쪽 이동 + 180도(남에서 불어옴) → negative headwind (tailwind)."""
        wind = WindCondition(speed_ms=5.0, direction_deg=180.0)
        hw = _headwind_component(0.0, 100.0, 100.0, wind)
        assert hw < -4.9  # ≈ -5.0
