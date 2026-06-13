"""Smoke tests for 0% coverage safety/coordination modules."""
import numpy as np


class TestAutoLandingSystem:
    def test_compute_approach_no_target(self):
        from simulation.auto_landing_system import AutoLandingSystem
        als = AutoLandingSystem()
        result = als.compute_approach(np.zeros(3))
        assert np.allclose(result, np.zeros(3))

    def test_compute_approach_with_target(self):
        from simulation.auto_landing_system import AutoLandingSystem, LandingTarget
        als = AutoLandingSystem()
        als.set_target(LandingTarget(10.0, 10.0, 0.0, 5.0))
        result = als.compute_approach(np.zeros(3))
        assert np.linalg.norm(result) > 0

    def test_is_landed_no_target(self):
        from simulation.auto_landing_system import AutoLandingSystem
        als = AutoLandingSystem()
        assert als.is_landed(np.zeros(3)) is False

    def test_is_landed_at_target(self):
        from simulation.auto_landing_system import AutoLandingSystem, LandingTarget
        als = AutoLandingSystem()
        als.set_target(LandingTarget(0.0, 0.0, 0.0, 5.0))
        assert als.is_landed(np.array([0.0, 0.0, 0.0]))

    def test_is_landed_far(self):
        from simulation.auto_landing_system import AutoLandingSystem, LandingTarget
        als = AutoLandingSystem()
        als.set_target(LandingTarget(0.0, 0.0, 0.0, 5.0))
        assert not als.is_landed(np.array([100.0, 0.0, 0.0]))


class TestSwarmCoordinationHub:
    def test_register_drone(self):
        from simulation.swarm_coordination_hub import SwarmCoordinationHub
        hub = SwarmCoordinationHub()
        hub.register_drone("d1", ["delivery", "survey"])
        assert "d1" in hub.drones
        assert hub.drones["d1"]["status"] == "idle"

    def test_send_command(self):
        from simulation.swarm_coordination_hub import SwarmCoordinationHub
        hub = SwarmCoordinationHub()
        hub.register_drone("d1", ["delivery"])
        hub.send_command("d1", "takeoff", {"altitude": 50})
        assert len(hub.command_queue) == 1
        assert hub.command_queue[0].command == "takeoff"

    def test_broadcast_command(self):
        from simulation.swarm_coordination_hub import SwarmCoordinationHub
        hub = SwarmCoordinationHub()
        hub.register_drone("d1", [])
        hub.register_drone("d2", [])
        hub.broadcast_command("land")
        assert len(hub.command_queue) == 2

    def test_get_drone_status(self):
        from simulation.swarm_coordination_hub import SwarmCoordinationHub
        hub = SwarmCoordinationHub()
        hub.register_drone("d1", ["survey"])
        status = hub.get_drone_status("d1")
        assert status["status"] == "idle"

    def test_get_unknown_drone_status(self):
        from simulation.swarm_coordination_hub import SwarmCoordinationHub
        hub = SwarmCoordinationHub()
        assert hub.get_drone_status("nonexistent") == {}


class TestHomeBaseSystem:
    def test_set_and_get_home(self):
        from simulation.home_base_system import HomeBaseSystem
        hbs = HomeBaseSystem()
        pos = np.array([100.0, 200.0, 0.0])
        hbs.set_home(pos)
        result = hbs.get_home_position()
        assert np.allclose(result, pos)

    def test_get_home_no_base(self):
        from simulation.home_base_system import HomeBaseSystem
        hbs = HomeBaseSystem()
        assert hbs.get_home_position() is None

    def test_is_at_home_true(self):
        from simulation.home_base_system import HomeBaseSystem
        hbs = HomeBaseSystem()
        hbs.set_home(np.zeros(3), radius=15.0)
        assert hbs.is_at_home(np.array([5.0, 5.0, 0.0]))

    def test_is_at_home_false(self):
        from simulation.home_base_system import HomeBaseSystem
        hbs = HomeBaseSystem()
        hbs.set_home(np.zeros(3), radius=5.0)
        assert not hbs.is_at_home(np.array([100.0, 0.0, 0.0]))

    def test_is_at_home_no_base(self):
        from simulation.home_base_system import HomeBaseSystem
        hbs = HomeBaseSystem()
        assert hbs.is_at_home(np.zeros(3)) is False


class TestAltitudeManager:
    def test_assign_altitude(self):
        from simulation.altitude_manager import AltitudeManager
        am = AltitudeManager()
        result = am.assign_altitude("d1", heading_deg=90.0, priority=2)
        assert result.drone_id == "d1"
        assert 30.0 <= result.altitude_m <= 120.0

    def test_heading_band(self):
        from simulation.altitude_manager import AltitudeManager
        am = AltitudeManager()
        band, idx = am._heading_band(0.0)
        assert band == "N"
        band_e, idx_e = am._heading_band(90.0)
        assert band_e == "E"

    def test_release(self):
        from simulation.altitude_manager import AltitudeManager
        am = AltitudeManager()
        am.assign_altitude("d1", heading_deg=0.0)
        assert am.release("d1") is True
        assert am.get_assignment("d1") is None

    def test_release_unknown(self):
        from simulation.altitude_manager import AltitudeManager
        am = AltitudeManager()
        assert am.release("unknown") is False

    def test_vertical_separation_ok(self):
        from simulation.altitude_manager import AltitudeManager
        am = AltitudeManager()
        am.assign_altitude("d1", heading_deg=0.0)
        am.assign_altitude("d2", heading_deg=180.0)
        result = am.vertical_separation_ok("d1", "d2")
        assert isinstance(result, bool)

    def test_summary(self):
        from simulation.altitude_manager import AltitudeManager
        am = AltitudeManager()
        am.assign_altitude("d1", heading_deg=45.0)
        summary = am.summary()
        assert summary["total_assigned"] == 1

    def test_congested_layers(self):
        from simulation.altitude_manager import AltitudeManager
        am = AltitudeManager()
        for i in range(6):
            am.assign_altitude(f"d{i}", heading_deg=0.0)
        congested = am.congested_layers(threshold=5)
        assert isinstance(congested, list)

    def test_reassign_congested(self):
        from simulation.altitude_manager import AltitudeManager
        am = AltitudeManager()
        for i in range(3):
            am.assign_altitude(f"d{i}", heading_deg=0.0)
        result = am.reassign_congested(max_per_layer=2)
        assert isinstance(result, list)
