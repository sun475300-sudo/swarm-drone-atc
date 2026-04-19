# Phase 601-610 Tests — Python Modules
"""
Phase 601: Swarm Topology Control
Phase 602: Drone Auction Market
Phase 603: Swarm Information Field
Phase 604: Probabilistic Roadmap (PRM)
Phase 605: Drone Formation Control
Phase 606: Swarm Optogenetics
Phase 607: Multi-Fidelity Simulation
Phase 608: Drone Reputation System
Phase 609: Swarm Electrostatics
Phase 610: Constraint Satisfaction
"""

import pytest
import numpy as np


# ── Phase 601: Swarm Topology Control ──────────────────────────

class TestSwarmTopologyControl:
    def test_import(self):
        from simulation.swarm_topology_control import SwarmTopologyControl
        stc = SwarmTopologyControl(15, 42)
        assert stc is not None

    def test_run(self):
        from simulation.swarm_topology_control import SwarmTopologyControl
        stc = SwarmTopologyControl(15, 42)
        stc.run(50)
        s = stc.summary()
        assert s["steps"] == 50

    def test_summary_keys(self):
        from simulation.swarm_topology_control import SwarmTopologyControl
        stc = SwarmTopologyControl(10, 42)
        stc.run(20)
        s = stc.summary()
        assert "agents" in s
        assert "rewires" in s

    def test_topology_manager(self):
        from simulation.swarm_topology_control import TopologyManager
        tm = TopologyManager(10, 42)
        assert tm.adj.shape == (10, 10)
        tm.rewire_step()

    def test_connectivity(self):
        from simulation.swarm_topology_control import TopologyManager
        tm = TopologyManager(8, 42)
        c = tm.algebraic_connectivity()
        assert isinstance(c, float)


# ── Phase 602: Drone Auction Market ────────────────────────────

class TestDroneAuctionMarket:
    def test_import(self):
        from simulation.drone_auction_market import DroneAuctionMarket
        dam = DroneAuctionMarket(10, 5, 42)
        assert dam is not None

    def test_run(self):
        from simulation.drone_auction_market import DroneAuctionMarket
        dam = DroneAuctionMarket(10, 5, 42)
        dam.run(20)
        s = dam.summary()
        assert s["rounds"] == 20

    def test_summary_keys(self):
        from simulation.drone_auction_market import DroneAuctionMarket
        dam = DroneAuctionMarket(10, 5, 42)
        dam.run(10)
        s = dam.summary()
        assert "total_revenue" in s
        assert "drones" in s

    def test_vickrey(self):
        from simulation.drone_auction_market import VickreyAuction
        va = VickreyAuction(42)
        result = va.run_auction([("a", 10.0), ("b", 8.0), ("c", 5.0)])
        assert result is not None

    def test_no_bidders(self):
        from simulation.drone_auction_market import VickreyAuction
        va = VickreyAuction(42)
        result = va.run_auction([])
        assert result is None


# ── Phase 603: Swarm Information Field ─────────────────────────

class TestSwarmInformationField:
    def test_import(self):
        from simulation.swarm_information_field import SwarmInformationField
        sif = SwarmInformationField(15, 42)
        assert sif is not None

    def test_run(self):
        from simulation.swarm_information_field import SwarmInformationField
        sif = SwarmInformationField(15, 42)
        sif.run(50)
        s = sif.summary()
        assert s["steps"] == 50

    def test_summary_keys(self):
        from simulation.swarm_information_field import SwarmInformationField
        sif = SwarmInformationField(10, 42)
        sif.run(20)
        s = sif.summary()
        assert "agents" in s

    def test_fisher_info(self):
        from simulation.swarm_information_field import InformationField
        field = InformationField(10, 42)
        fi = field.compute_fisher_info()
        assert isinstance(fi, (float, np.floating))

    def test_field_step(self):
        from simulation.swarm_information_field import InformationField
        field = InformationField(10, 42)
        field.step()


# ── Phase 604: Probabilistic Roadmap ──────────────────────────

class TestProbabilisticRoadmap:
    def test_import(self):
        from simulation.probabilistic_roadmap import ProbabilisticRoadmapPlanner
        prm = ProbabilisticRoadmapPlanner(100, 42)
        assert prm is not None

    def test_run(self):
        from simulation.probabilistic_roadmap import ProbabilisticRoadmapPlanner
        prm = ProbabilisticRoadmapPlanner(100, 42)
        prm.run()
        s = prm.summary()
        assert "nodes" in s

    def test_summary_keys(self):
        from simulation.probabilistic_roadmap import ProbabilisticRoadmapPlanner
        prm = ProbabilisticRoadmapPlanner(50, 42)
        prm.run()
        s = prm.summary()
        assert "path_found" in s
        assert "path_length" in s

    def test_roadmap_build(self):
        from simulation.probabilistic_roadmap import PRMGraph
        g = PRMGraph(42)
        g.build(50, (0, 100), (0, 100))
        assert len(g.nodes) == 50

    def test_query(self):
        from simulation.probabilistic_roadmap import PRMGraph
        g = PRMGraph(42)
        g.build(100, (0, 100), (0, 100))
        path = g.query(np.array([5.0, 5.0]), np.array([95.0, 95.0]))
        # path may or may not be found depending on graph connectivity


# ── Phase 605: Drone Formation Control ─────────────────────────

class TestDroneFormationControl:
    def test_import(self):
        from simulation.drone_formation_control import DroneFormationControl
        dfc = DroneFormationControl(10, 42)
        assert dfc is not None

    def test_run(self):
        from simulation.drone_formation_control import DroneFormationControl
        dfc = DroneFormationControl(10, 42)
        dfc.run(100)
        s = dfc.summary()
        assert s["steps"] == 100

    def test_summary_keys(self):
        from simulation.drone_formation_control import DroneFormationControl
        dfc = DroneFormationControl(10, 42)
        dfc.run(50)
        s = dfc.summary()
        assert "formation" in s
        assert "final_error" in s

    def test_switch_formation(self):
        from simulation.drone_formation_control import DroneFormationControl
        dfc = DroneFormationControl(10, 42)
        dfc.switch_formation("circle")
        assert dfc.current_pattern == "circle"

    def test_laplacian(self):
        from simulation.drone_formation_control import ConsensusController
        cc = ConsensusController(5, 42)
        L = cc.laplacian()
        assert L.shape == (5, 5)
        assert np.allclose(L.sum(axis=1), 0)


# ── Phase 606: Swarm Optogenetics ──────────────────────────────

class TestSwarmOptogenetics:
    def test_import(self):
        from simulation.swarm_optogenetics import SwarmOptogenetics
        so = SwarmOptogenetics(20, 42)
        assert so is not None

    def test_run(self):
        from simulation.swarm_optogenetics import SwarmOptogenetics
        so = SwarmOptogenetics(20, 42)
        so.run(100)
        s = so.summary()
        assert s["steps"] == 100

    def test_summary_keys(self):
        from simulation.swarm_optogenetics import SwarmOptogenetics
        so = SwarmOptogenetics(15, 42)
        so.run(50)
        s = so.summary()
        assert "open" in s
        assert "closed" in s
        assert "inactivated" in s

    def test_channel_states(self):
        from simulation.swarm_optogenetics import SwarmOptogenetics
        so = SwarmOptogenetics(20, 42)
        so.run(100)
        s = so.summary()
        total = s["open"] + s["closed"] + s["inactivated"]
        assert total == 20

    def test_add_light(self):
        from simulation.swarm_optogenetics import OptogeneticController
        oc = OptogeneticController(10, 42)
        oc.add_light(50, 50, 1.0, "excite")
        assert len(oc.light_sources) == 1


# ── Phase 607: Multi-Fidelity Simulation ──────────────────────

class TestMultiFidelitySim:
    def test_import(self):
        from simulation.multi_fidelity_sim import MultiFidelitySim
        mf = MultiFidelitySim(10, 42)
        assert mf is not None

    def test_run(self):
        from simulation.multi_fidelity_sim import MultiFidelitySim
        mf = MultiFidelitySim(10, 42)
        mf.run(200)
        s = mf.summary()
        assert s["steps"] == 200

    def test_summary_keys(self):
        from simulation.multi_fidelity_sim import MultiFidelitySim
        mf = MultiFidelitySim(10, 42)
        mf.run(50)
        s = mf.summary()
        assert "total_cost" in s
        assert "fidelity_switches" in s

    def test_fidelity_levels(self):
        from simulation.multi_fidelity_sim import AdaptiveSimulator
        sim = AdaptiveSimulator(42)
        assert "low" in sim.levels
        assert "medium" in sim.levels
        assert "high" in sim.levels

    def test_step(self):
        from simulation.multi_fidelity_sim import AdaptiveSimulator
        sim = AdaptiveSimulator(42)
        state = sim.step()
        assert len(state) == 4
        assert sim.total_cost > 0


# ── Phase 608: Drone Reputation System ─────────────────────────

class TestDroneReputationSystem:
    def test_import(self):
        from simulation.drone_reputation_system import DroneReputationSystem
        drs = DroneReputationSystem(20, 3, 42)
        assert drs is not None

    def test_run(self):
        from simulation.drone_reputation_system import DroneReputationSystem
        drs = DroneReputationSystem(20, 3, 42)
        drs.run(50)
        s = drs.summary()
        assert s["interactions"] > 0

    def test_summary_keys(self):
        from simulation.drone_reputation_system import DroneReputationSystem
        drs = DroneReputationSystem(20, 3, 42)
        drs.run(30)
        s = drs.summary()
        assert "true_positives" in s
        assert "avg_trust" in s

    def test_trust_score(self):
        from simulation.drone_reputation_system import Reputation
        r = Reputation(0, alpha=10, beta_param=2)
        assert 0.8 < r.trust_score < 0.9

    def test_detect_malicious(self):
        from simulation.drone_reputation_system import DroneReputationSystem
        drs = DroneReputationSystem(20, 3, 42)
        drs.run(50)
        detected = drs.system.detect_malicious()
        assert isinstance(detected, list)


# ── Phase 609: Swarm Electrostatics ───────────────────────────

class TestSwarmElectrostatics:
    def test_import(self):
        from simulation.swarm_electrostatics import SwarmElectrostatics
        se = SwarmElectrostatics(20, 42)
        assert se is not None

    def test_run(self):
        from simulation.swarm_electrostatics import SwarmElectrostatics
        se = SwarmElectrostatics(20, 42)
        se.run(200)
        s = se.summary()
        assert s["steps"] == 200

    def test_summary_keys(self):
        from simulation.swarm_electrostatics import SwarmElectrostatics
        se = SwarmElectrostatics(15, 42)
        se.run(50)
        s = se.summary()
        assert "initial_energy" in s
        assert "final_energy" in s

    def test_forces(self):
        from simulation.swarm_electrostatics import CoulombSwarm
        cs = CoulombSwarm(5, 42)
        forces = cs.compute_forces()
        assert forces.shape == (5, 2)

    def test_energy(self):
        from simulation.swarm_electrostatics import CoulombSwarm
        cs = CoulombSwarm(5, 42)
        e = cs.total_energy()
        assert isinstance(e, float)


# ── Phase 610: Constraint Satisfaction ─────────────────────────

class TestConstraintSatisfaction:
    def test_import(self):
        from simulation.constraint_satisfaction import ConstraintSatisfaction
        cs = ConstraintSatisfaction(8, 4, 42)
        assert cs is not None

    def test_run(self):
        from simulation.constraint_satisfaction import ConstraintSatisfaction
        cs = ConstraintSatisfaction(8, 4, 42)
        cs.run()
        s = cs.summary()
        assert s["solved"] is True

    def test_summary_keys(self):
        from simulation.constraint_satisfaction import ConstraintSatisfaction
        cs = ConstraintSatisfaction(6, 3, 42)
        cs.run()
        s = cs.summary()
        assert "backtracks" in s
        assert "assignments" in s

    def test_csp_solver(self):
        from simulation.constraint_satisfaction import CSPSolver
        solver = CSPSolver()
        solver.add_variable("a", [1, 2, 3])
        solver.add_variable("b", [1, 2, 3])
        solver.add_constraint("a", "b", "neq")
        sol = solver.solve()
        assert sol is not None
        assert sol["a"] != sol["b"]

    def test_ac3(self):
        from simulation.constraint_satisfaction import CSPSolver
        solver = CSPSolver()
        solver.add_variable("x", [1, 2])
        solver.add_variable("y", [1, 2])
        solver.add_constraint("x", "y", "neq")
        result = solver.ac3()
        assert result is True
