"""Smoke tests for 0% coverage mission-related modules."""
import numpy as np
import pytest


class TestMissionSchedulerOptimizer:
    def test_add_and_optimize(self):
        from simulation.mission_scheduler_optimizer import MissionSchedulerOptimizer, Mission
        import time
        opt = MissionSchedulerOptimizer()
        m = Mission("m1", time.time() + 1, 10.0, ["d1", "d2"], priority=5)
        opt.add_mission(m)
        schedule = opt.optimize_schedule()
        assert "m1_d1" in schedule
        assert "m1_d2" in schedule

    def test_priority_ordering(self):
        from simulation.mission_scheduler_optimizer import MissionSchedulerOptimizer, Mission
        import time
        opt = MissionSchedulerOptimizer()
        t = time.time()
        opt.add_mission(Mission("low", t, 5.0, ["d1"], priority=1))
        opt.add_mission(Mission("high", t, 5.0, ["d2"], priority=10))
        assert opt.missions[0].priority == 10

    def test_reschedule_on_delay(self):
        from simulation.mission_scheduler_optimizer import MissionSchedulerOptimizer, Mission
        import time
        opt = MissionSchedulerOptimizer()
        m = Mission("m1", time.time(), 5.0, ["d1"], priority=3)
        opt.add_mission(m)
        opt.optimize_schedule()
        original = opt.schedule.get("m1_d1", 0.0)
        opt.reschedule_on_delay("m1", 100.0)
        assert opt.schedule.get("m1_d1", 0.0) == original + 100.0


class TestCoveragePlanningSystem:
    def test_plan_survey_path_empty(self):
        from simulation.coverage_planning_system import CoveragePlanningSystem
        cps = CoveragePlanningSystem()
        assert cps.plan_survey_path(2) == []

    def test_plan_survey_path(self):
        from simulation.coverage_planning_system import CoveragePlanningSystem, CoverageRegion
        cps = CoveragePlanningSystem()
        region = CoverageRegion(0.0, 100.0, 0.0, 50.0)
        cps.add_region(region)
        paths = cps.plan_survey_path(2)
        assert len(paths) == 1
        assert len(paths[0]) > 0
        for point in paths[0]:
            assert len(point) == 3

    def test_lawnmower_z_fixed(self):
        from simulation.coverage_planning_system import CoveragePlanningSystem, CoverageRegion
        cps = CoveragePlanningSystem()
        region = CoverageRegion(0.0, 50.0, 0.0, 30.0)
        cps.add_region(region)
        paths = cps.plan_survey_path(1)
        for pt in paths[0]:
            assert pt[2] == 50


class TestMissionPlanningSystem:
    def test_plan_mission(self):
        from simulation.mission_planning_system import MissionPlanningSystem
        mps = MissionPlanningSystem()
        mission = mps.plan_mission("m1", 5, (0, 1000, 0, 1000))
        assert mission.mission_id == "m1"
        assert len(mission.waypoints) == 5
        assert "m1" in mps.missions

    def test_optimize_route(self):
        from simulation.mission_planning_system import MissionPlanningSystem
        mps = MissionPlanningSystem()
        mission = mps.plan_mission("m2", 4, (0, 100, 0, 100))
        sorted_wps = mps.optimize_route(mission)
        assert len(sorted_wps) == 4
        xs = [w.x + w.y for w in sorted_wps]
        assert xs == sorted(xs)


class TestFlightValidationSystem:
    def test_valid_plan(self):
        from simulation.flight_validation_system import FlightValidationSystem, FlightPlan
        fvs = FlightValidationSystem()
        plan = FlightPlan(
            drone_id="d1",
            waypoints=[np.array([0.0, 0.0, 60.0])],
            max_altitude=120.0,
            battery_required=30.0,
        )
        valid, errors = fvs.validate_plan(plan, current_battery=50.0)
        assert valid is True
        assert len(errors) == 0

    def test_altitude_violation(self):
        from simulation.flight_validation_system import FlightValidationSystem, FlightPlan
        fvs = FlightValidationSystem(max_altitude_m=100.0)
        plan = FlightPlan(
            drone_id="d1",
            waypoints=[np.array([0.0, 0.0, 150.0])],
            max_altitude=150.0,
            battery_required=20.0,
        )
        valid, errors = fvs.validate_plan(plan, current_battery=50.0)
        assert valid is False
        assert len(errors) == 1

    def test_battery_violation(self):
        from simulation.flight_validation_system import FlightValidationSystem, FlightPlan
        fvs = FlightValidationSystem(min_battery_percent=30.0)
        plan = FlightPlan(
            drone_id="d1",
            waypoints=[np.array([0.0, 0.0, 60.0])],
            max_altitude=120.0,
            battery_required=30.0,
        )
        valid, errors = fvs.validate_plan(plan, current_battery=10.0)
        assert valid is False

    def test_collision_risk_detected(self):
        from simulation.flight_validation_system import FlightValidationSystem, FlightPlan
        fvs = FlightValidationSystem()
        wp = np.array([0.0, 0.0, 60.0])
        plan1 = FlightPlan("d1", [wp.copy()], 120.0, 20.0)
        plan2 = FlightPlan("d2", [wp.copy()], 120.0, 20.0)
        assert fvs.check_collision_risk(plan1, plan2) is True

    def test_no_collision_risk(self):
        from simulation.flight_validation_system import FlightValidationSystem, FlightPlan
        fvs = FlightValidationSystem()
        plan1 = FlightPlan("d1", [np.array([0.0, 0.0, 60.0])], 120.0, 20.0)
        plan2 = FlightPlan("d2", [np.array([1000.0, 0.0, 60.0])], 120.0, 20.0)
        assert fvs.check_collision_risk(plan1, plan2) is False
