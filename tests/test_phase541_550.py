# Phase 541-550 통합 테스트
import pytest
import numpy as np


class TestPhase541Thermodynamics:
    def test_init(self):
        from simulation.swarm_thermodynamics import SwarmThermodynamics
        st = SwarmThermodynamics(10, 42)
        assert st.n_drones == 10

    def test_optimize(self):
        from simulation.swarm_thermodynamics import SwarmThermodynamics
        st = SwarmThermodynamics(10, 42)
        st.optimize(max_steps=50)
        assert st.result is not None
        assert st.result.final_energy <= st.result.initial_energy

    def test_boltzmann(self):
        from simulation.swarm_thermodynamics import BoltzmannDistribution
        bd = BoltzmannDistribution(42)
        assert bd.boltzmann_prob(-1, 10) == 1.0
        assert 0 < bd.boltzmann_prob(1, 10) < 1

    def test_entropy(self):
        from simulation.swarm_thermodynamics import BoltzmannDistribution
        bd = BoltzmannDistribution(42)
        pts = np.random.default_rng(42).normal(0, 10, (5, 3))
        assert bd.entropy(pts) > 0

    def test_summary(self):
        from simulation.swarm_thermodynamics import SwarmThermodynamics
        st = SwarmThermodynamics(10, 42)
        st.optimize(max_steps=50)
        s = st.summary()
        assert "energy" in s and "entropy" in s


class TestPhase542SwarmGrammar:
    def test_init(self):
        from simulation.drone_swarm_grammar import DroneSwarmGrammar
        dsg = DroneSwarmGrammar(10, 42)
        assert dsg.n_target == 10

    def test_generate(self):
        from simulation.drone_swarm_grammar import DroneSwarmGrammar
        dsg = DroneSwarmGrammar(10, 42)
        f = dsg.generate_formation("test_0")
        assert len(f.positions) > 0

    def test_lsystem(self):
        from simulation.drone_swarm_grammar import LSystem
        ls = LSystem("F", 42)
        ls.add_rule("F", "F+F")
        result = ls.generate(2)
        assert "+" in result

    def test_evolve(self):
        from simulation.drone_swarm_grammar import DroneSwarmGrammar
        dsg = DroneSwarmGrammar(10, 42)
        dsg.evolve(3, 4)
        assert dsg.best is not None

    def test_summary(self):
        from simulation.drone_swarm_grammar import DroneSwarmGrammar
        dsg = DroneSwarmGrammar(10, 42)
        dsg.evolve(3, 4)
        s = dsg.summary()
        assert s["formations_generated"] > 0


class TestPhase543ConsensusClock:
    def test_init(self):
        from simulation.distributed_consensus_clock import DistributedConsensusClock
        dcc = DistributedConsensusClock(5, 42)
        assert len(dcc.nodes) == 5

    def test_simulate(self):
        from simulation.distributed_consensus_clock import DistributedConsensusClock
        dcc = DistributedConsensusClock(5, 42)
        dcc.simulate(10)
        assert len(dcc.all_events) > 0

    def test_vector_clock(self):
        from simulation.distributed_consensus_clock import VectorClock
        vc1 = VectorClock({"a": 1, "b": 0})
        vc2 = VectorClock({"a": 1, "b": 1})
        assert vc1.happens_before(vc2)

    def test_lamport(self):
        from simulation.distributed_consensus_clock import LamportClock
        lc = LamportClock()
        t1 = lc.tick()
        t2 = lc.receive(5)
        assert t2 > t1

    def test_summary(self):
        from simulation.distributed_consensus_clock import DistributedConsensusClock
        dcc = DistributedConsensusClock(5, 42)
        dcc.simulate(10)
        s = dcc.summary()
        assert s["total_events"] > 0


class TestPhase544HypergraphRouting:
    def test_init(self):
        from simulation.hypergraph_routing import HypergraphRouting
        hr = HypergraphRouting(10, 15, 42)
        assert hr.n_nodes == 10

    def test_route(self):
        from simulation.hypergraph_routing import HypergraphRouting
        hr = HypergraphRouting(10, 15, 42)
        r = hr.route("N_0", ["N_5", "N_9"])
        assert r.source == "N_0"

    def test_dijkstra(self):
        from simulation.hypergraph_routing import HyperGraph
        g = HyperGraph()
        g.add_hyperedge("e1", ["A", "B", "C"], 1.0)
        dist = g.dijkstra("A")
        assert dist["B"] == 1.0

    def test_batch(self):
        from simulation.hypergraph_routing import HypergraphRouting
        hr = HypergraphRouting(10, 15, 42)
        hr.run_batch(5)
        assert len(hr.results) == 5

    def test_summary(self):
        from simulation.hypergraph_routing import HypergraphRouting
        hr = HypergraphRouting(10, 15, 42)
        hr.run_batch(5)
        s = hr.summary()
        assert s["queries"] == 5


class TestPhase545Stigmergy:
    def test_init(self):
        from simulation.swarm_stigmergy import SwarmStigmergy
        ss = SwarmStigmergy(5, 20, 42)
        assert len(ss.agents) == 5

    def test_run(self):
        from simulation.swarm_stigmergy import SwarmStigmergy
        ss = SwarmStigmergy(5, 20, 42)
        ss.run(5)
        assert ss.total_steps == 5

    def test_pheromone_field(self):
        from simulation.swarm_stigmergy import PheromoneField
        pf = PheromoneField(10, 10)
        pf.deposit(5, 5, 10.0)
        assert pf.sample(5, 5) == 10.0

    def test_evaporation(self):
        from simulation.swarm_stigmergy import PheromoneField
        pf = PheromoneField(10, 10, evaporation=0.5)
        pf.deposit(5, 5, 10.0)
        pf.evaporate()
        assert pf.sample(5, 5) == 5.0

    def test_summary(self):
        from simulation.swarm_stigmergy import SwarmStigmergy
        ss = SwarmStigmergy(5, 20, 42)
        ss.run(5)
        s = ss.summary()
        assert s["steps"] == 5


class TestPhase546AcousticLocalization:
    def test_init(self):
        from simulation.drone_acoustic_localization import DroneAcousticLocalization
        dal = DroneAcousticLocalization(4, 3, 42)
        assert len(dal.mics) == 4

    def test_localize(self):
        from simulation.drone_acoustic_localization import DroneAcousticLocalization
        dal = DroneAcousticLocalization(4, 3, 42)
        dal.localize_all()
        assert len(dal.results) == 3

    def test_tdoa(self):
        from simulation.drone_acoustic_localization import TDOALocalizer, Microphone
        mics = [Microphone(f"m{i}", np.array([i*10.0, 0, 0])) for i in range(3)]
        loc = TDOALocalizer(mics, 42)
        tdoa = loc.compute_tdoa(np.array([15.0, 20.0, 5.0]))
        assert len(tdoa) > 0

    def test_beamformer(self):
        from simulation.drone_acoustic_localization import Beamformer, Microphone
        mics = [Microphone(f"m{i}", np.array([i*5.0, 0, 0])) for i in range(4)]
        bf = Beamformer(mics)
        pm = bf.power_map(1000, 30)
        assert len(pm) > 0

    def test_summary(self):
        from simulation.drone_acoustic_localization import DroneAcousticLocalization
        dal = DroneAcousticLocalization(4, 3, 42)
        s = dal.summary()
        assert s["localizations"] == 3


class TestPhase547FederatedAnomaly:
    def test_init(self):
        from simulation.federated_anomaly_detection import FederatedAnomalyDetection
        fad = FederatedAnomalyDetection(4, 10, 42)
        assert fad.n_clients == 4

    def test_train(self):
        from simulation.federated_anomaly_detection import FederatedAnomalyDetection
        fad = FederatedAnomalyDetection(4, 10, 42)
        fad.train(3)
        assert len(fad.rounds) == 3

    def test_detector(self):
        from simulation.federated_anomaly_detection import AnomalyDetector
        det = AnomalyDetector(8, 4, 42)
        x = np.random.default_rng(42).normal(0, 1, 8)
        err = det.reconstruction_error(x)
        assert err >= 0

    def test_round(self):
        from simulation.federated_anomaly_detection import FederatedAnomalyDetection
        fad = FederatedAnomalyDetection(4, 10, 42)
        fr = fad.train_round()
        assert fr.participants == 4

    def test_summary(self):
        from simulation.federated_anomaly_detection import FederatedAnomalyDetection
        fad = FederatedAnomalyDetection(4, 10, 42)
        fad.train(3)
        s = fad.summary()
        assert s["rounds"] == 3


class TestPhase548TDA:
    def test_init(self):
        from simulation.topological_data_analysis import TopologicalDataAnalysis
        tda = TopologicalDataAnalysis(10, 42)
        assert tda.n_drones == 10

    def test_analyze(self):
        from simulation.topological_data_analysis import TopologicalDataAnalysis
        tda = TopologicalDataAnalysis(10, 42)
        tda.analyze(30.0)
        assert tda.features is not None

    def test_vietoris_rips(self):
        from simulation.topological_data_analysis import VietorisRips
        vr = VietorisRips(1)
        pts = np.array([[0,0,0],[1,0,0],[0,1,0]], dtype=float)
        vr.build(pts, 2.0, 5)
        assert len(vr.simplices) >= 3

    def test_betti(self):
        from simulation.topological_data_analysis import TopologicalDataAnalysis
        tda = TopologicalDataAnalysis(10, 42)
        tda.analyze(30.0)
        assert tda.features.betti_0 >= 1

    def test_summary(self):
        from simulation.topological_data_analysis import TopologicalDataAnalysis
        tda = TopologicalDataAnalysis(10, 42)
        s = tda.summary()
        assert "betti_0" in s


class TestPhase549EvoGameTheory:
    def test_init(self):
        from simulation.evolutionary_game_theory import EvolutionaryGameTheory
        egt = EvolutionaryGameTheory(10, 42)
        assert egt.n_players == 10

    def test_evolve(self):
        from simulation.evolutionary_game_theory import EvolutionaryGameTheory
        egt = EvolutionaryGameTheory(10, 42)
        egt.evolve(5)
        assert len(egt.game_results) > 0

    def test_replicator(self):
        from simulation.evolutionary_game_theory import EvoReplicatorDynamics, EvoStrategy
        rd = EvoReplicatorDynamics([EvoStrategy.COOPERATE, EvoStrategy.DEFECT], 42)
        rd.step()
        assert abs(sum(rd.proportions) - 1.0) < 0.01

    def test_payoff(self):
        from simulation.evolutionary_game_theory import EvoPayoffMatrix, EvoStrategy
        pm = EvoPayoffMatrix()
        a, b = pm.get_payoff(EvoStrategy.COOPERATE, EvoStrategy.COOPERATE)
        assert a == 3 and b == 3

    def test_summary(self):
        from simulation.evolutionary_game_theory import EvolutionaryGameTheory
        egt = EvolutionaryGameTheory(10, 42)
        egt.evolve(5)
        s = egt.summary()
        assert s["total_games"] > 0


class TestPhase550DigitalTwin:
    def test_init(self):
        from simulation.drone_digital_twin import DroneDigitalTwinSystem
        dts = DroneDigitalTwinSystem(5, 42)
        assert dts.n_drones == 5

    def test_run(self):
        from simulation.drone_digital_twin import DroneDigitalTwinSystem
        dts = DroneDigitalTwinSystem(5, 42)
        dts.run(10)
        assert len(dts.twin_results) == 50

    def test_physics_model(self):
        from simulation.drone_digital_twin import PhysicsModel, DronePhysicalState
        pm = PhysicsModel()
        state = DronePhysicalState("d0", np.zeros(3), np.ones(3), 100,
                                    np.full(4, 3000.0), 25.0, 0.0)
        next_s = pm.predict_next(state)
        assert next_s.timestamp == 0.1

    def test_anomaly(self):
        from simulation.drone_digital_twin import AnomalyPredictor, DronePhysicalState
        ap = AnomalyPredictor()
        state = DronePhysicalState("d0", np.zeros(3), np.zeros(3), 10,
                                    np.full(4, 50.0), 60.0, 0.0)
        assert ap.needs_maintenance(state)

    def test_summary(self):
        from simulation.drone_digital_twin import DroneDigitalTwinSystem
        dts = DroneDigitalTwinSystem(5, 42)
        dts.run(10)
        s = dts.summary()
        assert s["drones"] == 5 and s["sync_steps"] == 10
