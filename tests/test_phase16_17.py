"""
Phase 16-17 테스트: 설정 검증, SpatialHash, 드론 프로파일, 시뮬레이터 코어
"""
from __future__ import annotations

import numpy as np
import pytest


# ── SpatialHash 테스트 ──────────────────────────────────────


class TestSpatialHash:
    def _make_hash(self):
        from simulation.spatial_hash import SpatialHash
        return SpatialHash(cell_size=50.0)

    def test_insert_and_query_radius(self):
        sh = self._make_hash()
        sh.insert("A", np.array([0.0, 0.0, 0.0]))
        sh.insert("B", np.array([30.0, 0.0, 0.0]))
        result = sh.query_radius(np.zeros(3), 50.0)
        assert "A" in result
        assert "B" in result

    def test_query_radius_excludes_far(self):
        sh = self._make_hash()
        sh.insert("A", np.array([0.0, 0.0, 0.0]))
        sh.insert("B", np.array([200.0, 0.0, 0.0]))
        result = sh.query_radius(np.zeros(3), 50.0)
        assert "A" in result
        assert "B" not in result

    def test_query_pairs(self):
        sh = self._make_hash()
        sh.insert("A", np.array([0.0, 0.0, 0.0]))
        sh.insert("B", np.array([10.0, 0.0, 0.0]))
        sh.insert("C", np.array([500.0, 500.0, 0.0]))
        pairs = sh.query_pairs(50.0)
        assert frozenset(("A", "B")) in pairs
        assert frozenset(("A", "C")) not in pairs

    def test_query_pairs_with_dist(self):
        sh = self._make_hash()
        sh.insert("X", np.array([0.0, 0.0, 0.0]))
        sh.insert("Y", np.array([3.0, 4.0, 0.0]))
        pairs = list(sh.query_pairs_with_dist(10.0))
        assert len(pairs) == 1
        assert pairs[0][2] == pytest.approx(5.0, abs=0.01)

    def test_clear(self):
        sh = self._make_hash()
        sh.insert("A", np.zeros(3))
        sh.clear()
        result = sh.query_radius(np.zeros(3), 100.0)
        assert len(result) == 0

    def test_3d_distance(self):
        sh = self._make_hash()
        sh.insert("A", np.array([0.0, 0.0, 0.0]))
        sh.insert("B", np.array([0.0, 0.0, 40.0]))
        pairs = list(sh.query_pairs_with_dist(50.0))
        assert len(pairs) == 1
        assert pairs[0][2] == pytest.approx(40.0, abs=0.1)

    def test_empty_query(self):
        sh = self._make_hash()
        result = sh.query_radius(np.zeros(3), 100.0)
        assert result == []
        pairs = sh.query_pairs(50.0)
        assert len(pairs) == 0

    def test_many_drones_performance(self):
        """100대 삽입 후 쿼리가 에러 없이 완료"""
        sh = self._make_hash()
        rng = np.random.default_rng(42)
        for i in range(100):
            sh.insert(f"D{i}", rng.uniform(-1000, 1000, 3))
        pairs = list(sh.query_pairs_with_dist(50.0))
        assert isinstance(pairs, list)


# ── DroneProfile 테스트 ──────────────────────────────────────


class TestDroneProfiles:
    def test_all_profiles_exist(self):
        from src.airspace_control.agents.drone_profiles import DRONE_PROFILES
        expected = {"COMMERCIAL_DELIVERY", "SURVEILLANCE", "EMERGENCY",
                    "RECREATIONAL", "ROGUE"}
        assert set(DRONE_PROFILES.keys()) == expected

    def test_emergency_highest_priority(self):
        from src.airspace_control.agents.drone_profiles import DRONE_PROFILES
        emergency = DRONE_PROFILES["EMERGENCY"]
        for name, profile in DRONE_PROFILES.items():
            if name == "ROGUE":
                continue
            assert emergency.priority <= profile.priority

    def test_cruise_less_than_max(self):
        from src.airspace_control.agents.drone_profiles import DRONE_PROFILES
        for name, p in DRONE_PROFILES.items():
            assert p.cruise_speed_ms <= p.max_speed_ms, f"{name}: cruise > max"

    def test_rogue_no_comm(self):
        from src.airspace_control.agents.drone_profiles import DRONE_PROFILES
        assert DRONE_PROFILES["ROGUE"].comm_range_m == 0.0

    def test_profile_fields(self):
        from src.airspace_control.agents.drone_profiles import DroneProfile
        p = DroneProfile(name="test", max_speed_ms=10, cruise_speed_ms=5,
                         max_altitude_m=100, battery_wh=50, endurance_min=20,
                         comm_range_m=1000, priority=2)
        assert p.climb_rate_ms == 3.5  # default
        assert p.turn_rate_deg_s == 30.0  # default


# ── Config Schema 테스트 ──────────────────────────────────


class TestConfigSchema:
    def test_load_default_config(self):
        from simulation.config_schema import load_validated_config
        cfg = load_validated_config("config/default_simulation.yaml")
        assert cfg.drones.default_count == 100
        assert cfg.simulation.seed == 42

    def test_load_mc_config(self):
        from simulation.config_schema import load_validated_mc_config
        mc = load_validated_mc_config("config/monte_carlo.yaml")
        assert mc.master_seed == 42
        assert mc.quick_sweep.n_per_config >= 1

    def test_invalid_drone_count(self):
        from simulation.config_schema import DronesSection
        with pytest.raises(Exception):
            DronesSection(default_count=0)

    def test_invalid_altitude_range(self):
        from simulation.config_schema import DronesSection
        with pytest.raises(Exception):
            DronesSection(min_altitude_m=120.0, max_altitude_m=30.0)

    def test_invalid_cruise_vs_max(self):
        from simulation.config_schema import DronesSection
        with pytest.raises(Exception):
            DronesSection(cruise_speed_ms=20.0, max_speed_ms=10.0)

    def test_invalid_near_miss_greater_than_separation(self):
        from simulation.config_schema import SeparationSection
        with pytest.raises(Exception):
            SeparationSection(near_miss_lateral_m=60.0, lateral_min_m=50.0)

    def test_invalid_log_level(self):
        from simulation.config_schema import LoggingSection
        with pytest.raises(Exception):
            LoggingSection(level="VERBOSE")

    def test_valid_log_levels(self):
        from simulation.config_schema import LoggingSection
        for lvl in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            s = LoggingSection(level=lvl)
            assert s.level == lvl

    def test_bounds_range_validation(self):
        from simulation.config_schema import BoundsRange
        with pytest.raises(Exception):
            BoundsRange(x=[5.0, -5.0])  # min > max

    def test_bounds_range_wrong_count(self):
        from simulation.config_schema import BoundsRange
        with pytest.raises(Exception):
            BoundsRange(x=[1.0, 2.0, 3.0])

    def test_simulation_section_defaults(self):
        from simulation.config_schema import SimulationSection
        s = SimulationSection()
        assert s.seed == 42
        assert s.time_step_hz == 10

    def test_acceptance_thresholds(self):
        from simulation.config_schema import AcceptanceThresholds
        t = AcceptanceThresholds()
        assert t.collision_rate_per_1000h == 0.0
        assert t.conflict_resolution_rate_pct == 99.5

    def test_failure_injection_defaults(self):
        from simulation.config_schema import FailureInjectionSection
        f = FailureInjectionSection()
        assert f.drone_failure_rate == 0.0
        assert "MOTOR" in f.failure_types

    def test_extra_keys_allowed(self):
        from simulation.config_schema import SimulationConfig
        cfg = SimulationConfig(unknown_key="value")
        assert cfg.drones.default_count == 100


# ── Simulator Core 테스트 ──────────────────────────────────


class TestSimulatorCore:
    def test_create_default(self):
        from simulation.simulator import SwarmSimulator
        sim = SwarmSimulator(seed=42)
        assert sim.seed == 42

    def test_deep_merge(self):
        from simulation.simulator import SwarmSimulator
        base = {"a": {"b": 1, "c": 2}, "d": 3}
        override = {"a": {"b": 10}, "e": 5}
        SwarmSimulator._deep_merge(base, override)
        assert base["a"]["b"] == 10
        assert base["a"]["c"] == 2
        assert base["e"] == 5

    def test_landing_pads_exist(self):
        from simulation.simulator import SwarmSimulator
        assert len(SwarmSimulator.LANDING_PADS) >= 4

    def test_bounds_from_config(self):
        from simulation.simulator import SwarmSimulator
        sim = SwarmSimulator(seed=42)
        assert sim.bounds_m > 0

    def test_short_simulation_runs(self):
        from simulation.simulator import SwarmSimulator
        sim = SwarmSimulator(seed=42, scenario_cfg={"drones": {"default_count": 5}})
        result = sim.run(duration_s=5.0)
        assert result.n_drones == 5
        assert result.duration_s == 5.0

    def test_result_has_comm_stats(self):
        from simulation.simulator import SwarmSimulator
        sim = SwarmSimulator(seed=42, scenario_cfg={"drones": {"default_count": 3}})
        result = sim.run(duration_s=3.0)
        assert hasattr(result, "comm_messages_sent")
        assert hasattr(result, "cbs_attempts")
        assert hasattr(result, "clearances_per_sec")

    def test_result_has_energy(self):
        from simulation.simulator import SwarmSimulator
        sim = SwarmSimulator(seed=42, scenario_cfg={"drones": {"default_count": 3}})
        result = sim.run(duration_s=3.0)
        assert hasattr(result, "energy_efficiency_wh_per_km")

    def test_failure_injection_config(self):
        from simulation.simulator import SwarmSimulator
        cfg_override = {
            "drones": {"default_count": 5},
            "failure_injection": {
                "drone_failure_rate": 0.5,
                "comms_loss_rate": 0.1,
            },
        }
        sim = SwarmSimulator(seed=42, scenario_cfg=cfg_override)
        assert sim._failure_rate == pytest.approx(0.5)
        assert sim._comms_loss_rate == pytest.approx(0.1)


# ── CommunicationBus 확장 테스트 ──────────────────────────


class TestCommBusExtended:
    def test_stats_tracking(self):
        import simpy
        from src.airspace_control.comms.communication_bus import CommunicationBus, CommMessage
        env = simpy.Environment()
        rng = np.random.default_rng(42)
        bus = CommunicationBus(env, rng, packet_loss_rate=0.0)
        bus.subscribe("RX", lambda m: None)
        bus.send(CommMessage("TX", "RX", "hello", 0.0))
        env.run(until=1.0)
        assert bus.stats["sent"] == 1
        assert bus.stats["delivered"] >= 1

    def test_packet_loss(self):
        import simpy
        from src.airspace_control.comms.communication_bus import CommunicationBus, CommMessage
        env = simpy.Environment()
        rng = np.random.default_rng(42)
        bus = CommunicationBus(env, rng, packet_loss_rate=1.0)  # 100% loss
        bus.subscribe("RX", lambda m: None)
        bus.send(CommMessage("TX", "RX", "hello", 0.0))
        env.run(until=1.0)
        assert bus.stats["dropped"] == 1
        assert bus.stats["delivered"] == 0

    def test_broadcast(self):
        import simpy
        from src.airspace_control.comms.communication_bus import CommunicationBus, CommMessage
        env = simpy.Environment()
        rng = np.random.default_rng(42)
        bus = CommunicationBus(env, rng)
        received = []
        bus.subscribe("A", lambda m: received.append("A"))
        bus.subscribe("B", lambda m: received.append("B"))
        bus.send(CommMessage("TX", "BROADCAST", "hello", 0.0))
        env.run(until=1.0)
        assert "A" in received
        assert "B" in received

    def test_range_filtering(self):
        import simpy
        from src.airspace_control.comms.communication_bus import CommunicationBus, CommMessage
        env = simpy.Environment()
        rng = np.random.default_rng(42)
        bus = CommunicationBus(env, rng, comm_range_m=100.0)
        bus.update_position("TX", np.zeros(3))
        bus.update_position("RX", np.array([200.0, 0.0, 0.0]))  # 200m, out of range
        received = []
        bus.subscribe("RX", lambda m: received.append(True))
        bus.send(CommMessage("TX", "RX", "hello", 0.0))
        env.run(until=1.0)
        assert len(received) == 0  # Out of range


# ── Analytics 확장 테스트 ──────────────────────────────────


class TestAnalyticsExtended:
    def test_controller_stats_recorded(self):
        from simulation.analytics import SimulationAnalytics
        a = SimulationAnalytics({"logging": {"save_trajectory": False}})
        a.record_controller_stats(cbs_attempts=10, cbs_successes=8, astar_count=2, clearances_per_sec=1.5)
        result = a.finalize(seed=0, n_drones=0)
        assert result.cbs_attempts == 10
        assert result.cbs_successes == 8
        assert result.astar_fallbacks == 2
        assert result.clearances_per_sec == pytest.approx(1.5)

    def test_comm_stats_recorded(self):
        from simulation.analytics import SimulationAnalytics
        a = SimulationAnalytics({"logging": {"save_trajectory": False}})
        a.record_comm_stats(sent=100, delivered=90, dropped=10)
        result = a.finalize(seed=0, n_drones=0)
        assert result.comm_messages_sent == 100
        assert result.comm_messages_delivered == 90
        assert result.comm_messages_dropped == 10
        assert result.comm_drop_rate == pytest.approx(0.1)

    def test_comm_drop_rate_zero_sent(self):
        from simulation.analytics import SimulationAnalytics
        a = SimulationAnalytics({"logging": {"save_trajectory": False}})
        result = a.finalize(seed=0, n_drones=0)
        assert result.comm_drop_rate == 0.0

    def test_summary_table_has_cbs(self):
        from simulation.analytics import SimulationAnalytics
        a = SimulationAnalytics({"logging": {"save_trajectory": False}})
        a.record_controller_stats(cbs_attempts=5, cbs_successes=4, astar_count=1)
        result = a.finalize(seed=0, n_drones=0)
        table = result.summary_table()
        assert "CBS" in table
        assert "5/4" in table


# ── KDTree 최적화 테스트 ──────────────────────────────────


class TestKDTreeQuery:
    def test_kdtree_finds_close_pair(self):
        from src.airspace_control.controller.airspace_controller import AirspaceController
        positions = {
            "A": np.array([0.0, 0.0, 0.0]),
            "B": np.array([10.0, 0.0, 0.0]),
            "C": np.array([500.0, 500.0, 0.0]),
        }
        pairs = AirspaceController._kdtree_query_pairs(positions, 50.0)
        pair_sets = [frozenset((a, b)) for a, b, _ in pairs]
        assert frozenset(("A", "B")) in pair_sets
        assert frozenset(("A", "C")) not in pair_sets

    def test_kdtree_distance_accuracy(self):
        from src.airspace_control.controller.airspace_controller import AirspaceController
        positions = {
            "X": np.array([0.0, 0.0, 0.0]),
            "Y": np.array([3.0, 4.0, 0.0]),
        }
        pairs = AirspaceController._kdtree_query_pairs(positions, 10.0)
        assert len(pairs) == 1
        assert pairs[0][2] == pytest.approx(5.0, abs=0.01)

    def test_kdtree_empty(self):
        from src.airspace_control.controller.airspace_controller import AirspaceController
        pairs = AirspaceController._kdtree_query_pairs({}, 50.0)
        assert pairs == []

    def test_kdtree_single_drone(self):
        from src.airspace_control.controller.airspace_controller import AirspaceController
        positions = {"A": np.array([0.0, 0.0, 0.0])}
        pairs = AirspaceController._kdtree_query_pairs(positions, 50.0)
        assert pairs == []

    def test_kdtree_threshold_constant(self):
        from src.airspace_control.controller.airspace_controller import AirspaceController
        assert AirspaceController._KDTREE_THRESHOLD == 200
