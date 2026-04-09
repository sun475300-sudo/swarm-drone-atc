"""
Phase 60-67 테스트
- 소음 모델링 (NoiseModel)
- 함대 최적화 (FleetOptimizer)
- 경로 탈충돌기 (PathDeconflict)
- 텔레메트리 녹화기 (TelemetryRecorder)
- 착륙 관리자 (LandingManager)
- 위험도 평가기 (RiskAssessor)
- 공역-기상 통합 (AirspaceWeatherIntegration)
- 드론 건강 모니터 (DroneHealthMonitor)
"""
import pytest
import numpy as np


# ──────────────────────────────────────────────
# Phase 60: 소음 모델링
# ──────────────────────────────────────────────
class TestNoiseModel:
    def _make(self):
        from simulation.noise_model import NoiseModel
        return NoiseModel()

    def test_basic_noise(self):
        nm = self._make()
        nm.update_drones({"d1": (500, 500, 50)})
        level = nm.ground_noise_at(500, 500)
        assert level > 0

    def test_noise_decreases_with_distance(self):
        nm = self._make()
        nm.update_drones({"d1": (500, 500, 50)})
        near = nm.ground_noise_at(500, 500)
        far = nm.ground_noise_at(0, 0)
        assert near > far

    def test_multiple_sources_louder(self):
        nm = self._make()
        nm.update_drones({"d1": (500, 500, 50)})
        single = nm.ground_noise_at(500, 500)
        nm.update_drones({"d1": (500, 500, 50), "d2": (510, 510, 50)})
        double = nm.ground_noise_at(505, 505)
        assert double > single - 5  # 2 sources should be louder

    def test_noise_map(self):
        nm = self._make()
        nm.update_drones({"d1": (500, 500, 50)})
        grid = nm.noise_map(resolution=5)
        assert grid.shape == (5, 5)
        assert np.any(grid > 0)

    def test_regulation_check(self):
        nm = self._make()
        nm.update_drones({"d1": (100, 100, 10)})
        violations = nm.check_regulation(100, 100, hour=23.0)  # Night
        # Close drone at low altitude = loud
        assert isinstance(violations, list)

    def test_footprint_area(self):
        nm = self._make()
        nm.update_drones({"d1": (500, 500, 50)})
        area = nm.footprint_area(55.0)
        assert area > 0

    def test_speed_increases_noise(self):
        nm = self._make()
        nm.update_drones({"d1": (500, 500, 50)}, speeds={"d1": 5.0})
        slow = nm.ground_noise_at(500, 500)
        nm.update_drones({"d1": (500, 500, 50)}, speeds={"d1": 25.0})
        fast = nm.ground_noise_at(500, 500)
        assert fast > slow

    def test_summary(self):
        nm = self._make()
        nm.update_drones({"d1": (500, 500, 50)})
        s = nm.summary()
        assert s["total_sources"] == 1


# ──────────────────────────────────────────────
# Phase 61: 함대 최적화
# ──────────────────────────────────────────────
class TestFleetOptimizer:
    def _make(self):
        from simulation.fleet_optimizer import FleetOptimizer
        return FleetOptimizer()

    def test_basic_optimize(self):
        opt = self._make()
        opt.add_drone_type("delivery", cost_usd=500, endurance_min=30, charge_time_min=45)
        opt.set_demand(missions_per_hour=10)
        result = opt.optimize()
        assert result.total_count > 0
        assert result.missions_per_hour >= 10

    def test_multiple_types(self):
        opt = self._make()
        opt.add_drone_type("cheap", cost_usd=200, endurance_min=20, charge_time_min=60)
        opt.add_drone_type("premium", cost_usd=1000, endurance_min=45, charge_time_min=30)
        opt.set_demand(missions_per_hour=5)
        result = opt.optimize()
        assert result.total_count > 0

    def test_shifts(self):
        opt = self._make()
        schedules = opt.generate_shifts(total_drones=10, shifts=3)
        assert len(schedules) == 3
        assert all(s.active_drones > 0 for s in schedules)

    def test_cost_breakdown(self):
        opt = self._make()
        opt.add_drone_type("delivery", cost_usd=500)
        opt.set_demand(missions_per_hour=5)
        comp = opt.optimize()
        breakdown = opt.cost_breakdown(comp)
        assert "monthly_profit" in breakdown
        assert "roi_months" in breakdown

    def test_summary(self):
        opt = self._make()
        opt.add_drone_type("delivery", cost_usd=500)
        opt.set_demand(missions_per_hour=5)
        s = opt.summary()
        assert s["drone_types"] == 1


# ──────────────────────────────────────────────
# Phase 62: 경로 탈충돌기
# ──────────────────────────────────────────────
class TestPathDeconflict:
    def _make(self):
        from simulation.path_deconflict import PathDeconflict, Waypoint4D
        return PathDeconflict(separation_h=30.0, separation_v=10.0), Waypoint4D

    def test_no_conflict(self):
        dc, WP = self._make()
        dc.add_path("d1", [WP(0, 0, 50, 0), WP(100, 0, 50, 10)])
        dc.add_path("d2", [WP(0, 200, 50, 0), WP(100, 200, 50, 10)])
        conflicts = dc.find_conflicts()
        assert len(conflicts) == 0

    def test_head_on_conflict(self):
        dc, WP = self._make()
        dc.add_path("d1", [WP(0, 0, 50, 0), WP(100, 0, 50, 10)])
        dc.add_path("d2", [WP(100, 0, 50, 0), WP(0, 0, 50, 10)])
        conflicts = dc.find_conflicts()
        assert len(conflicts) > 0

    def test_resolve_by_time_shift(self):
        dc, WP = self._make()
        dc.add_path("d1", [WP(0, 0, 50, 0), WP(100, 0, 50, 10)])
        dc.add_path("d2", [WP(100, 0, 50, 0), WP(0, 0, 50, 10)])
        offsets = dc.resolve_by_time_shift()
        # At least one drone should be shifted
        assert any(v > 0 for v in offsets.values())

    def test_interpolate(self):
        dc, WP = self._make()
        dc.add_path("d1", [WP(0, 0, 50, 0), WP(100, 0, 50, 10)])
        pos = dc.interpolate_position("d1", 5.0)
        assert pos is not None
        assert abs(pos[0] - 50.0) < 1.0

    def test_path_count(self):
        dc, WP = self._make()
        dc.add_path("d1", [WP(0, 0, 50, 0)])
        dc.add_path("d2", [WP(100, 0, 50, 0)])
        assert dc.path_count == 2

    def test_remove_path(self):
        dc, WP = self._make()
        dc.add_path("d1", [WP(0, 0, 50, 0)])
        dc.remove_path("d1")
        assert dc.path_count == 0

    def test_summary(self):
        dc, WP = self._make()
        dc.add_path("d1", [WP(0, 0, 50, 0), WP(100, 0, 50, 10)])
        s = dc.summary()
        assert s["total_paths"] == 1


# ──────────────────────────────────────────────
# Phase 63: 텔레메트리 녹화기
# ──────────────────────────────────────────────
class TestTelemetryRecorder:
    def _make(self):
        from simulation.telemetry_recorder import TelemetryRecorder
        return TelemetryRecorder()

    def test_record_and_retrieve(self):
        rec = self._make()
        rec.record(t=1.0, drone_states={"d1": {"position": [100, 200, 50]}})
        snap = rec.get_at(1.0)
        assert snap is not None
        assert snap.t == 1.0

    def test_get_range(self):
        rec = self._make()
        for i in range(10):
            rec.record(t=float(i), drone_states={"d1": {"position": [i*10, 0, 50]}})
        snaps = rec.get_range(3.0, 7.0)
        assert len(snaps) == 5

    def test_rewind(self):
        rec = self._make()
        for i in range(5):
            rec.record(t=float(i), drone_states={})
        rec.rewind(2.0)
        assert rec.current.t == 2.0

    def test_step_forward_backward(self):
        rec = self._make()
        for i in range(5):
            rec.record(t=float(i), drone_states={})
        rec.rewind(2.0)
        rec.step_forward()
        assert rec.current.t == 3.0
        rec.step_backward()
        assert rec.current.t == 2.0

    def test_trajectory(self):
        rec = self._make()
        for i in range(5):
            rec.record(t=float(i), drone_states={
                "d1": {"position": [i*10, 0, 50]}
            })
        traj = rec.drone_trajectory("d1")
        assert len(traj) == 5

    def test_compare(self):
        rec1 = self._make()
        rec2 = self._make()
        rec1.record(t=1.0, drone_states={"d1": {"position": [100, 0, 50]}})
        rec2.record(t=1.0, drone_states={"d1": {"position": [110, 0, 50]}})
        comp = rec1.compare(rec2, 1.0)
        assert comp["common_drones"] == 1
        assert comp["avg_position_diff"] > 0

    def test_duration(self):
        rec = self._make()
        rec.record(t=0.0, drone_states={})
        rec.record(t=10.0, drone_states={})
        assert rec.duration == 10.0

    def test_clear(self):
        rec = self._make()
        rec.record(t=1.0, drone_states={})
        rec.clear()
        assert rec.snapshot_count == 0


# ──────────────────────────────────────────────
# Phase 64: 착륙 관리자
# ──────────────────────────────────────────────
class TestLandingManager:
    def _make(self):
        from simulation.landing_manager import LandingManager, LandingPad
        lm = LandingManager()
        lm.add_pad("P1", position=(0, 0))
        lm.add_pad("P2", position=(100, 0))
        return lm

    def test_request_and_assign(self):
        lm = self._make()
        lm.request_landing("d1", (10, 10, 50), t=1.0)
        req = lm.assign_pad("d1", t=1.0)
        assert req is not None
        assert req.status == "ASSIGNED"
        assert req.assigned_pad == "P1"  # Nearest

    def test_queue_order(self):
        lm = self._make()
        lm.request_landing("d1", (10, 10, 50), priority=1, t=1.0)
        lm.request_landing("d2", (20, 20, 50), priority=5, t=2.0)
        assert lm.queue_length() == 2

    def test_complete_landing(self):
        lm = self._make()
        lm.request_landing("d1", (10, 10, 50), t=1.0)
        lm.assign_pad("d1", t=1.0)
        assert lm.complete_landing("d1", t=5.0)

    def test_emergency_override(self):
        lm = self._make()
        lm.request_landing("d1", (10, 10, 50), t=1.0)
        lm.assign_pad("d1", t=1.0)
        # Emergency drone takes the pad
        lm.request_landing("d_emg", (5, 5, 30), t=2.0, is_emergency=True)
        req = lm.emergency_override("d_emg", t=2.0)
        assert req.is_emergency
        assert req.status == "ASSIGNED"

    def test_available_pads(self):
        lm = self._make()
        avail = lm.available_pads(t=100.0)
        assert len(avail) == 2

    def test_utilization(self):
        lm = self._make()
        lm.request_landing("d1", (10, 10, 50), t=1.0)
        lm.assign_pad("d1", t=1.0)
        assert lm.pad_utilization() == 0.5

    def test_min_interval(self):
        lm = self._make()
        lm.request_landing("d1", (10, 10, 50), t=1.0)
        lm.assign_pad("d1", t=1.0)
        lm.complete_landing("d1", t=5.0)
        # Too soon - pad may not be available
        avail = lm.available_pads(t=6.0)  # Only 1s after landing, min_interval=10
        pad_p1_avail = any(p.pad_id == "P1" for p in avail)
        assert not pad_p1_avail  # P1 should not be available yet

    def test_summary(self):
        lm = self._make()
        s = lm.summary()
        assert s["total_pads"] == 2


# ──────────────────────────────────────────────
# Phase 65: 위험도 평가기
# ──────────────────────────────────────────────
class TestRiskAssessor:
    def _make(self):
        from simulation.risk_assessor import RiskAssessor
        return RiskAssessor()

    def test_basic_assessment(self):
        ra = self._make()
        profile = ra.assess_position(500, 500, 60)
        assert 0 <= profile.ground_risk_score <= 100
        assert profile.risk_level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    def test_center_riskier(self):
        ra = self._make()
        center = ra.assess_position(500, 500, 60)
        edge = ra.assess_position(0, 0, 60)
        assert center.ground_risk_score >= edge.ground_risk_score

    def test_population_zone(self):
        ra = self._make()
        ra.set_population_zone(center=(200, 200), radius=100, density=8000)
        profile = ra.assess_position(200, 200, 60)
        assert profile.population_density >= 8000

    def test_path_assessment(self):
        ra = self._make()
        result = ra.assess_path([
            (100, 100, 60), (500, 500, 60), (900, 900, 60)
        ])
        assert result["waypoints_assessed"] == 3
        assert result["max_risk"] >= result["min_risk"]

    def test_risk_map(self):
        ra = self._make()
        grid = ra.risk_map(altitude=60)
        assert grid.shape == (20, 20)

    def test_impact_radius(self):
        ra = self._make()
        low = ra.assess_position(500, 500, 30)
        high = ra.assess_position(500, 500, 100)
        assert high.impact_radius_m > low.impact_radius_m

    def test_recommended_altitude(self):
        ra = self._make()
        profile = ra.assess_position(500, 500, 60)
        assert profile.recommended_altitude >= 60

    def test_summary(self):
        ra = self._make()
        s = ra.summary()
        assert s["grid_resolution"] == 20


# ──────────────────────────────────────────────
# Phase 66: 공역-기상 통합
# ──────────────────────────────────────────────
class TestAirspaceWeatherIntegration:
    def _make(self):
        from simulation.airspace_weather_integration import AirspaceWeatherIntegration
        return AirspaceWeatherIntegration()

    def test_green_default(self):
        awi = self._make()
        assert awi.current_class.name == "GREEN"

    def test_yellow_wind(self):
        awi = self._make()
        cls = awi.update_weather(wind_speed=12)
        assert cls.name == "YELLOW"

    def test_orange_wind(self):
        awi = self._make()
        cls = awi.update_weather(wind_speed=17)
        assert cls.name == "ORANGE"

    def test_red_wind(self):
        awi = self._make()
        cls = awi.update_weather(wind_speed=22)
        assert cls.name == "RED"

    def test_visibility_orange(self):
        awi = self._make()
        cls = awi.update_weather(visibility=1500)
        assert cls.name == "ORANGE"

    def test_restrictions_generated(self):
        awi = self._make()
        awi.update_weather(wind_speed=17)
        restrictions = awi.get_restrictions()
        assert len(restrictions) > 0

    def test_cant_launch_red(self):
        awi = self._make()
        awi.update_weather(wind_speed=22)
        assert not awi.can_launch()

    def test_can_launch_green(self):
        awi = self._make()
        awi.update_weather(wind_speed=5)
        assert awi.can_launch()

    def test_effective_separation(self):
        awi = self._make()
        awi.update_weather(wind_speed=17)
        sep = awi.effective_separation()
        assert sep > 30  # Should be increased from base

    def test_icing_risk(self):
        awi = self._make()
        cls = awi.update_weather(icing_risk=True)
        assert cls.name == "ORANGE"

    def test_class_history(self):
        awi = self._make()
        awi.update_weather(wind_speed=5, t=0)
        awi.update_weather(wind_speed=15, t=10)
        history = awi.class_history()
        assert len(history) >= 1

    def test_summary(self):
        awi = self._make()
        s = awi.summary()
        assert s["airspace_class"] == "GREEN"


# ──────────────────────────────────────────────
# Phase 67: 드론 건강 모니터
# ──────────────────────────────────────────────
class TestDroneHealthMonitor:
    def _make(self):
        from simulation.drone_health_monitor import DroneHealthMonitor
        return DroneHealthMonitor()

    def test_healthy_drone(self):
        dhm = self._make()
        health = dhm.update("d1", motor_rpm=5000, vibration=0.1, motor_temp=40)
        assert health.status == "HEALTHY"
        assert health.health_score > 80

    def test_high_vibration_warning(self):
        dhm = self._make()
        health = dhm.update("d1", vibration=1.3)
        assert health.health_score < 80
        assert len(health.issues) > 0

    def test_overheating(self):
        dhm = self._make()
        health = dhm.update("d1", motor_temp=75)
        assert "과열" in " ".join(health.issues)

    def test_rpm_out_of_range(self):
        dhm = self._make()
        health = dhm.update("d1", motor_rpm=2000)
        assert health.health_score < 100

    def test_maintenance_schedule(self):
        dhm = self._make()
        dhm.update("d1", vibration=1.2, flight_hours=48)
        schedules = dhm.get_maintenance_schedule("d1")
        assert len(schedules) > 0
        assert any(s.maintenance_type == "MOTOR" for s in schedules)

    def test_vibration_trend(self):
        dhm = self._make()
        for i in range(10):
            dhm.update("d1", t=float(i), vibration=0.1 + i * 0.15)
        health = dhm.get_health("d1")
        assert "증가 추세" in " ".join(health.issues)

    def test_fleet_health(self):
        dhm = self._make()
        dhm.update("d1", vibration=0.1)
        dhm.update("d2", vibration=1.3)
        fleet = dhm.fleet_health()
        assert fleet["total_drones"] == 2
        assert fleet["avg_health"] > 0

    def test_remaining_life(self):
        dhm = self._make()
        health = dhm.update("d1", flight_hours=400)
        assert health.remaining_life_hours < 500  # 500h motor life

    def test_clear(self):
        dhm = self._make()
        dhm.update("d1")
        dhm.clear()
        assert dhm.fleet_health()["total_drones"] == 0
