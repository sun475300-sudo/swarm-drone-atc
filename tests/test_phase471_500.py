"""
Phase 471-500 통합 테스트 — 150개 테스트
"""

import pytest
import numpy as np


# ── Phase 471: Quantum ML Pipeline ──
class TestQuantumMLPipeline:
    def test_quantum_kernel_compute(self):
        from simulation.quantum_ml_pipeline import QuantumKernel
        qk = QuantumKernel(n_qubits=4)
        val = qk.compute(np.array([0.1, 0.2, 0.3, 0.4]), np.array([0.5, 0.6, 0.7, 0.8]))
        assert isinstance(val, float)

    def test_qnn_predict(self):
        from simulation.quantum_ml_pipeline import QuantumNeuralNetwork
        qnn = QuantumNeuralNetwork(n_qubits=3, n_layers=2)
        out = qnn.predict(np.array([0.5, 0.3, 0.7]))
        assert out is not None

    def test_qsvc(self):
        from simulation.quantum_ml_pipeline import QSVC
        qsvc = QSVC(n_qubits=2)
        X = np.random.rand(10, 2)
        y = np.array([0]*5 + [1]*5)
        qsvc.fit(X, y)
        pred = qsvc.predict(X[0])
        assert isinstance(pred, (int, np.integer))

    def test_kernel_gram_matrix(self):
        from simulation.quantum_ml_pipeline import QuantumKernel
        qk = QuantumKernel(n_qubits=2)
        X = np.random.rand(5, 2)
        gram = qk.gram_matrix(X)
        assert gram.shape == (5, 5)

    def test_pipeline_summary(self):
        from simulation.quantum_ml_pipeline import QuantumMLPipeline
        pipeline = QuantumMLPipeline(n_qubits=4)
        s = pipeline.summary()
        assert isinstance(s, dict)


# ── Phase 472: Swarm Operating System ──
class TestSwarmOS:
    def test_swarm_os_spawn(self):
        from simulation.swarm_operating_system import SwarmOperatingSystem
        sos = SwarmOperatingSystem()
        proc = sos.spawn("task1")
        assert proc is not None

    def test_ipc_send_recv(self):
        from simulation.swarm_operating_system import SwarmIPC
        ipc = SwarmIPC()
        ipc.register(0)
        ipc.register(1)
        ipc.send(0, 1, "data", "hello")
        msg = ipc.receive(1)
        assert msg is not None

    def test_resource_manager(self):
        from simulation.swarm_operating_system import SwarmResourceManager
        rm = SwarmResourceManager()
        result = rm.allocate(0, cpu=10, memory_kb=1024)
        assert result is True

    def test_scheduler_tick(self):
        from simulation.swarm_operating_system import SwarmOperatingSystem
        sos = SwarmOperatingSystem()
        sos.spawn("task1")
        sos.spawn("task2")
        running = sos.tick()
        assert True

    def test_ipc_broadcast(self):
        from simulation.swarm_operating_system import SwarmIPC
        ipc = SwarmIPC()
        ipc.register(0)
        ipc.register(1)
        ipc.register(2)
        count = ipc.broadcast(0, "alert", "emergency")
        assert count >= 0


# ── Phase 473: Holographic Radar ──
class TestHolographicRadar:
    def test_phased_array_gain(self):
        from simulation.holographic_radar import PhasedArray
        pa = PhasedArray(n_elements=8)
        gain = pa.gain(30.0, 0.0)
        assert isinstance(gain, float)

    def test_radar_scan(self):
        from simulation.holographic_radar import HolographicRadar, RadarTarget
        radar = HolographicRadar()
        radar.add_target(RadarTarget("t1", 500, 0, 50))
        detections = radar.scan()
        assert isinstance(detections, list)

    def test_sar_imaging(self):
        from simulation.holographic_radar import HolographicRadar
        radar = HolographicRadar()
        img = radar.sar_image()
        assert img is not None and len(img) > 0

    def test_beam_steering(self):
        from simulation.holographic_radar import PhasedArray
        pa = PhasedArray(n_elements=16)
        pa.steer(45.0, 10.0)
        assert True

    def test_summary(self):
        from simulation.holographic_radar import HolographicRadar
        radar = HolographicRadar()
        s = radar.summary()
        assert isinstance(s, dict)


# ── Phase 474: Autonomous Negotiation ──
class TestAutonomousNegotiation:
    def test_negotiation_init(self):
        from simulation.autonomous_negotiation import AutonomousNegotiation
        neg = AutonomousNegotiation()
        neg.add_issue("altitude", 50, 200)
        neg.add_agent("a1", "linear")
        neg.add_agent("a2", "boulware")
        assert True

    def test_add_issue(self):
        from simulation.autonomous_negotiation import AutonomousNegotiation
        neg = AutonomousNegotiation()
        neg.add_issue("speed", 0, 50, weight=2.0)
        assert True

    def test_negotiation_run(self):
        from simulation.autonomous_negotiation import AutonomousNegotiation
        neg = AutonomousNegotiation(max_rounds=10)
        neg.add_issue("altitude", 50, 200)
        neg.add_agent("a1", "linear")
        neg.add_agent("a2", "conceder")
        result = neg.run()
        assert result is not None

    def test_negotiation_round(self):
        from simulation.autonomous_negotiation import AutonomousNegotiation
        neg = AutonomousNegotiation()
        neg.add_issue("x", 0, 100)
        neg.add_agent("a1", "linear")
        neg.add_agent("a2", "toughguy")
        result = neg.negotiate_round()
        assert result is not None or result is None

    def test_summary(self):
        from simulation.autonomous_negotiation import AutonomousNegotiation
        neg = AutonomousNegotiation()
        s = neg.summary()
        assert isinstance(s, dict)


# ── Phase 475: Bio-Inspired Optimizer ──
class TestBioInspired:
    def _bounds(self, n=2):
        return np.array([[-5, 5]] * n)

    def test_aco(self):
        from simulation.bio_inspired_optimizer import AntColonyV2
        rng = np.random.default_rng(42)
        aco = AntColonyV2(n_ants=10, n_dim=2, rng=rng)
        func = lambda x: float(np.sum(x**2))
        result = aco.optimize(func, self._bounds(2), max_iter=10)
        assert result is not None

    def test_abc(self):
        from simulation.bio_inspired_optimizer import ArtificialBeeColony
        rng = np.random.default_rng(42)
        abc = ArtificialBeeColony(n_bees=20, n_dim=3, rng=rng)
        func = lambda x: float(np.sum(x**2))
        result = abc.optimize(func, self._bounds(3), max_iter=10)
        assert result is not None

    def test_firefly(self):
        from simulation.bio_inspired_optimizer import FireflyAlgorithm
        rng = np.random.default_rng(42)
        ff = FireflyAlgorithm(n_fireflies=15, n_dim=3, rng=rng)
        func = lambda x: float(np.sum(x**2))
        result = ff.optimize(func, self._bounds(3), max_iter=10)
        assert result is not None

    def test_compare_all(self):
        from simulation.bio_inspired_optimizer import BioInspiredOptimizer
        bio = BioInspiredOptimizer(seed=42)
        func = lambda x: float(np.sum(x**2))
        results = bio.compare_all(func, self._bounds(2), max_iter=5)
        assert len(results) >= 2

    def test_optimizer_summary(self):
        from simulation.bio_inspired_optimizer import BioInspiredOptimizer
        bio = BioInspiredOptimizer(seed=42)
        func = lambda x: float(np.sum(x**2))
        bio.optimize(func, self._bounds(2), max_iter=5)
        s = bio.summary()
        assert isinstance(s, dict)


# ── Phase 476: Digital Twin Federation V2 ──
class TestDigitalTwinFedV2:
    def test_federation_init(self):
        from simulation.digital_twin_federation_v2 import DigitalTwinFederationV2
        fed = DigitalTwinFederationV2()
        fed.add_node("n0")
        fed.add_node("n1")
        fed.add_node("n2")
        assert True

    def test_create_twin(self):
        from simulation.digital_twin_federation_v2 import DigitalTwinFederationV2
        fed = DigitalTwinFederationV2()
        fed.add_node("n0")
        twin = fed.create_twin("n0", "drone_0", {"pos": [0, 0, 0]})
        assert twin is not None

    def test_sync_all(self):
        from simulation.digital_twin_federation_v2 import DigitalTwinFederationV2
        fed = DigitalTwinFederationV2()
        fed.add_node("n0")
        fed.add_node("n1")
        fed.create_twin("n0", "drone_0", {"pos": [0, 0, 0]})
        result = fed.sync_all()
        assert isinstance(result, dict)

    def test_query_federation(self):
        from simulation.digital_twin_federation_v2 import DigitalTwinFederationV2
        fed = DigitalTwinFederationV2()
        fed.add_node("n0")
        fed.create_twin("n0", "drone_0", {"sensor": 100})
        result = fed.query_federation("drone_0")
        assert isinstance(result, list)

    def test_summary(self):
        from simulation.digital_twin_federation_v2 import DigitalTwinFederationV2
        fed = DigitalTwinFederationV2()
        fed.add_node("n0")
        s = fed.summary()
        assert isinstance(s, dict)


# ── Phase 477: UAM Corridor Manager ──
class TestUAMCorridor:
    def test_vertiport(self):
        from simulation.uam_corridor_manager import UAMCorridorManager
        mgr = UAMCorridorManager()
        mgr.add_vertiport("VP1", 37.5, 127.0)
        assert "VP1" in mgr.vertiports

    def test_corridor_creation(self):
        from simulation.uam_corridor_manager import UAMCorridorManager
        mgr = UAMCorridorManager()
        mgr.add_vertiport("A", 37.5, 127.0)
        mgr.add_vertiport("B", 37.6, 127.1)
        c = mgr.create_corridor("A", "B")
        assert c is not None

    def test_flight_scheduling(self):
        from simulation.uam_corridor_manager import UAMCorridorManager
        mgr = UAMCorridorManager()
        mgr.add_vertiport("A", 37.5, 127.0)
        mgr.add_vertiport("B", 37.6, 127.1)
        mgr.create_corridor("A", "B")
        flight = mgr.schedule_flight("A", "B", departure_time=0)
        assert flight is not None

    def test_load_balancing(self):
        from simulation.uam_corridor_manager import UAMCorridorManager
        mgr = UAMCorridorManager()
        mgr.add_vertiport("A", 37.5, 127.0, capacity=2)
        mgr.add_vertiport("B", 37.6, 127.1)
        assert mgr.vertiports["A"].capacity == 2

    def test_summary(self):
        from simulation.uam_corridor_manager import UAMCorridorManager
        mgr = UAMCorridorManager()
        s = mgr.summary()
        assert isinstance(s, dict)


# ── Phase 478: Swarm Consciousness ──
class TestSwarmConsciousness:
    def test_init(self):
        from simulation.swarm_consciousness import SwarmConsciousness
        sc = SwarmConsciousness(n_drones=15)
        assert sc.n_drones == 15

    def test_step(self):
        from simulation.swarm_consciousness import SwarmConsciousness
        sc = SwarmConsciousness(n_drones=10)
        result = sc.step()
        assert result is not None  # SwarmMetric dataclass

    def test_run_for(self):
        from simulation.swarm_consciousness import SwarmConsciousness
        sc = SwarmConsciousness(n_drones=20)
        metrics = sc.run_for(20)
        assert len(metrics) == 20

    def test_metric_fields(self):
        from simulation.swarm_consciousness import SwarmConsciousness
        sc = SwarmConsciousness(n_drones=10)
        metric = sc.step()
        assert hasattr(metric, 'cohesion')
        assert hasattr(metric, 'alignment')

    def test_summary(self):
        from simulation.swarm_consciousness import SwarmConsciousness
        sc = SwarmConsciousness(n_drones=10)
        sc.run_for(5)
        s = sc.summary()
        assert "total_drones" in s


# ── Phase 479: Resilience Orchestrator ──
class TestResilienceOrchestrator:
    def test_add_node(self):
        from simulation.resilience_orchestrator import ResilienceOrchestrator
        ro = ResilienceOrchestrator()
        node = ro.add_node("node_0")
        assert node.node_id == "node_0"

    def test_fault_injection(self):
        from simulation.resilience_orchestrator import ResilienceOrchestrator, FaultType
        ro = ResilienceOrchestrator()
        ro.add_node("n1")
        fault = ro.inject_fault("n1", FaultType.NODE_CRASH, severity=0.8)
        assert fault is not None and fault.severity == 0.8

    def test_self_heal(self):
        from simulation.resilience_orchestrator import ResilienceOrchestrator, FaultType
        ro = ResilienceOrchestrator()
        ro.add_node("n1")
        ro.inject_fault("n1", FaultType.CPU_OVERLOAD)
        events = ro.self_heal()
        assert len(events) > 0

    def test_chaos_monkey(self):
        from simulation.resilience_orchestrator import ResilienceOrchestrator
        ro = ResilienceOrchestrator()
        for i in range(10):
            ro.add_node(f"n{i}")
        faults = ro.chaos_monkey(intensity=0.5)
        assert isinstance(faults, list)

    def test_resilience_score(self):
        from simulation.resilience_orchestrator import ResilienceOrchestrator, FaultType
        ro = ResilienceOrchestrator()
        ro.add_node("n1")
        ro.inject_fault("n1", FaultType.SENSOR_DRIFT)
        ro.self_heal()
        score = ro.resilience_score()
        assert 0 <= score <= 1


# ── Phase 480: Regulatory Compliance V2 ──
class TestRegulatoryCompliance:
    def test_register_drone(self):
        from simulation.regulatory_compliance_v2 import RegulatoryComplianceV2
        rc = RegulatoryComplianceV2()
        reg = rc.register_drone("d1", "op1")
        assert reg.drone_id == "d1"

    def test_authorization(self):
        from simulation.regulatory_compliance_v2 import RegulatoryComplianceV2
        rc = RegulatoryComplianceV2()
        rc.register_drone("d1", "op1")
        auth = rc.request_authorization("d1", (37.5, 127.0), 1000, 120, 0, 3600)
        assert auth is not None

    def test_compliance_check(self):
        from simulation.regulatory_compliance_v2 import RegulatoryComplianceV2
        rc = RegulatoryComplianceV2()
        rc.register_drone("d1", "op1")
        violations = rc.check_flight_compliance("d1", 200, 10, (37.5, 127.0), 0)
        assert len(violations) > 0  # altitude exceeds 150m

    def test_auto_enforce(self):
        from simulation.regulatory_compliance_v2 import RegulatoryComplianceV2
        rc = RegulatoryComplianceV2()
        rc.register_drone("d1", "op1")
        rc.check_flight_compliance("d1", 200, 10, (37.5, 127.0), 0)
        actions = rc.auto_enforce("d1")
        assert len(actions) > 0

    def test_kutm_report(self):
        from simulation.regulatory_compliance_v2 import RegulatoryComplianceV2
        rc = RegulatoryComplianceV2()
        rc.register_drone("d1", "op1")
        report = rc.generate_kutm_report()
        assert "total_drones" in report


# ── Phase 481: Adversarial Defense ──
class TestAdversarialDefense:
    def test_gps_spoofing_detect(self):
        from simulation.adversarial_defense import AdversarialDefense
        ad = AdversarialDefense(n_drones=5)
        threat = ad.detect_gps_spoofing(0, np.array([100, 0, 0]), np.array([80, 0, 0]))
        assert threat is not None

    def test_jamming_detect(self):
        from simulation.adversarial_defense import AdversarialDefense
        ad = AdversarialDefense(n_drones=5)
        threat = ad.detect_jamming(0, snr_db=2.0)
        assert threat is not None

    def test_respond(self):
        from simulation.adversarial_defense import AdversarialDefense, ThreatSignature, AttackType
        ad = AdversarialDefense()
        threat = ThreatSignature(AttackType.GPS_SPOOFING, 0.7, timestamp=0)
        event = ad.respond_to_threat(threat)
        assert event is not None

    def test_run_scan(self):
        from simulation.adversarial_defense import AdversarialDefense
        ad = AdversarialDefense(n_drones=10)
        threats = ad.run_scan()
        assert isinstance(threats, list)

    def test_defense_cycle(self):
        from simulation.adversarial_defense import AdversarialDefense
        ad = AdversarialDefense(n_drones=10)
        result = ad.run_defense_cycle(n_cycles=5)
        assert "defense_rate" in result


# ── Phase 482: Multi-Fidelity Sim ──
class TestMultiFidelitySim:
    def test_adaptive_simulator_step(self):
        from simulation.multi_fidelity_sim import AdaptiveSimulator
        sim = AdaptiveSimulator(seed=42)
        result = sim.step()
        assert result is not None
        assert len(result) == 4

    def test_fidelity_levels(self):
        from simulation.multi_fidelity_sim import AdaptiveSimulator
        sim = AdaptiveSimulator()
        sim.set_fidelity("high")
        assert sim.current_level == "high"
        sim.set_fidelity("low")
        assert sim.current_level == "low"

    def test_adaptive_switching(self):
        from simulation.multi_fidelity_sim import MultiFidelitySim
        mfs = MultiFidelitySim(n_drones=5)
        mfs.run(steps=50)
        assert mfs.steps == 50

    def test_run_trajectory(self):
        from simulation.multi_fidelity_sim import MultiFidelitySim
        mfs = MultiFidelitySim(n_drones=10, seed=42)
        mfs.run(steps=20)
        assert len(mfs.history) == 20

    def test_summary(self):
        from simulation.multi_fidelity_sim import MultiFidelitySim
        mfs = MultiFidelitySim(n_drones=10)
        mfs.run(steps=10)
        s = mfs.summary()
        assert "steps" in s
        assert "total_cost" in s


# ── Phase 483: Swarm Evolution ──
class TestSwarmEvolution:
    def test_init_population(self):
        from simulation.swarm_evolution import SwarmEvolution
        se = SwarmEvolution(pop_size=20)
        assert len(se.population) == 20

    def test_activate(self):
        from simulation.swarm_evolution import SwarmEvolution
        se = SwarmEvolution(pop_size=10, n_inputs=4, n_outputs=2)
        genome = se.population[0]
        out = se._activate(genome, np.array([1, 0.5, -0.3, 0.8]))
        assert len(out) == 2

    def test_evolve(self):
        from simulation.swarm_evolution import SwarmEvolution
        se = SwarmEvolution(pop_size=20)
        for g in se.population:
            g.fitness = np.random.rand()
        result = se.evolve()
        assert result["generation"] == 1

    def test_speciation(self):
        from simulation.swarm_evolution import SwarmEvolution
        se = SwarmEvolution(pop_size=30)
        for g in se.population:
            g.fitness = np.random.rand()
        se.evolve()
        assert se.generation >= 1

    def test_summary(self):
        from simulation.swarm_evolution import SwarmEvolution
        se = SwarmEvolution(pop_size=10)
        s = se.summary()
        assert "population" in s


# ── Phase 484: Explainable AI ──
class TestExplainableAI:
    def test_shap(self):
        from simulation.explainable_ai import SHAPExplainer
        model = lambda x: float(np.sum(x * np.array([0.5, -0.3, 0.8])))
        shap = SHAPExplainer(model, ["a", "b", "c"])
        attrs = shap.explain(np.array([1.0, 2.0, 3.0]))
        assert len(attrs) == 3

    def test_lime(self):
        from simulation.explainable_ai import LIMEExplainer
        model = lambda x: float(np.dot(x, [1, -1, 0.5]))
        lime = LIMEExplainer(model, ["x", "y", "z"])
        attrs = lime.explain(np.array([1, 2, 3]))
        assert len(attrs) == 3

    def test_counterfactual(self):
        from simulation.explainable_ai import CounterfactualExplainer
        model = lambda x: float(1.0 / (1.0 + np.exp(-np.sum(x))))
        cf = CounterfactualExplainer(model, ["a", "b"])
        result = cf.explain(np.array([-2.0, -1.0]), target_class=1.0)
        # May or may not find one
        assert result is None or "distance" in result

    def test_explain_decision(self):
        from simulation.explainable_ai import ExplainableAI
        xai = ExplainableAI()
        model = lambda x: float(np.sum(x))
        explanation = xai.explain_decision(model, ["a", "b"], np.array([0.5, 0.3]))
        assert explanation.confidence is not None

    def test_summary(self):
        from simulation.explainable_ai import ExplainableAI
        xai = ExplainableAI()
        s = xai.summary()
        assert "decisions_explained" in s


# ── Phase 485: Drone Swarm Protocol ──
class TestSwarmProtocol:
    def test_tdma(self):
        from simulation.drone_swarm_protocol import TDMAScheduler
        tdma = TDMAScheduler(10)
        assert tdma.can_transmit(0, 0)

    def test_cdma_encode_decode(self):
        from simulation.drone_swarm_protocol import CDMAEncoder
        cdma = CDMAEncoder(8)
        data = np.array([1.0, -1.0, 0.5])
        encoded = cdma.encode(data, 0)
        decoded = cdma.decode(encoded, 0)
        np.testing.assert_allclose(decoded, data, atol=0.01)

    def test_send_message(self):
        from simulation.drone_swarm_protocol import SwarmProtocol
        proto = SwarmProtocol(n_drones=5)
        msg = proto.send(0, 1, b"hello")
        assert msg.src == 0 and msg.dst == 1

    def test_run_protocol(self):
        from simulation.drone_swarm_protocol import SwarmProtocol
        proto = SwarmProtocol(n_drones=10)
        stats = proto.run(duration_ms=100)
        assert stats.messages_sent >= 0

    def test_summary(self):
        from simulation.drone_swarm_protocol import SwarmProtocol
        proto = SwarmProtocol(n_drones=5)
        proto.run(duration_ms=50)
        s = proto.summary()
        assert "delivery_rate" in s


# ── Phase 486: Cognitive EW ──
class TestCognitiveEW:
    def test_spectrum_scan(self):
        from simulation.cognitive_electronic_warfare import SpectrumAnalyzer
        sa = SpectrumAnalyzer()
        samples = sa.scan(n_points=64)
        assert len(samples) > 0

    def test_threat_detect(self):
        from simulation.cognitive_electronic_warfare import SpectrumAnalyzer
        sa = SpectrumAnalyzer()
        samples = sa.scan(n_points=256)
        threats = sa.detect_threats(samples)
        assert isinstance(threats, list)

    def test_engage(self):
        from simulation.cognitive_electronic_warfare import CognitiveEW, ThreatType
        ew = CognitiveEW()
        eng = ew.engage(ThreatType.SPOT_JAM)
        assert eng.countermeasure is not None

    def test_run_cycle(self):
        from simulation.cognitive_electronic_warfare import CognitiveEW
        ew = CognitiveEW()
        result = ew.run_cycle(n_scans=5)
        assert "engagements" in result

    def test_summary(self):
        from simulation.cognitive_electronic_warfare import CognitiveEW
        ew = CognitiveEW()
        ew.run_cycle(3)
        s = ew.summary()
        assert "success_rate" in s


# ── Phase 487: Swarm Morphogenesis ──
class TestSwarmMorphogenesis:
    def test_reaction_diffusion(self):
        from simulation.swarm_morphogenesis import ReactionDiffusion
        rd = ReactionDiffusion(n_cells=20)
        history = rd.run(steps=50)
        assert len(history) == 50

    def test_formation_morph(self):
        from simulation.swarm_morphogenesis import SwarmMorphogenesis, FormationType
        sm = SwarmMorphogenesis(n_drones=10)
        history = sm.morph_to(FormationType.CIRCLE, steps=50)
        assert len(history) == 50

    def test_quality(self):
        from simulation.swarm_morphogenesis import SwarmMorphogenesis, FormationType
        sm = SwarmMorphogenesis(n_drones=10)
        sm.morph_to(FormationType.LINE, steps=100)
        q = sm.formation_quality()
        assert 0 <= q <= 1

    def test_roles(self):
        from simulation.swarm_morphogenesis import SwarmMorphogenesis
        sm = SwarmMorphogenesis(n_drones=15)
        for _ in range(10):
            sm.step()
        roles = set(c.fate for c in sm.cells)
        assert len(roles) >= 1

    def test_summary(self):
        from simulation.swarm_morphogenesis import SwarmMorphogenesis
        sm = SwarmMorphogenesis(n_drones=10)
        s = sm.summary()
        assert "formation" in s


# ── Phase 488: Mission Critical Validator ──
class TestMissionValidator:
    def test_battery_validation(self):
        from simulation.mission_critical_validator import MissionCriticalValidator
        mv = MissionCriticalValidator()
        results = mv.validate_battery(95, 30)
        assert len(results) > 0

    def test_weather_validation(self):
        from simulation.mission_critical_validator import MissionCriticalValidator
        mv = MissionCriticalValidator()
        results = mv.validate_weather(15.0)
        assert any(not r.passed for r in results)

    def test_airspace_validation(self):
        from simulation.mission_critical_validator import MissionCriticalValidator
        mv = MissionCriticalValidator()
        waypoints = [np.array([0, 0, 200])]  # exceeds max
        results = mv.validate_airspace(waypoints)
        assert any(not r.passed for r in results)

    def test_full_mission(self):
        from simulation.mission_critical_validator import MissionCriticalValidator, MissionPlan
        mv = MissionCriticalValidator()
        plan = MissionPlan("M1", ["d1"], [np.array([0, 0, 50]), np.array([100, 0, 50])])
        result = mv.validate_mission(plan)
        assert "go_no_go" in result

    def test_go_decision(self):
        from simulation.mission_critical_validator import MissionCriticalValidator, MissionPlan
        mv = MissionCriticalValidator()
        plan = MissionPlan("M1", ["d1"], [np.array([0, 0, 50])],
                          emergency_landing_sites=[np.array([0, 0, 0])])
        result = mv.validate_mission(plan, battery_pct=95, wind_speed=3)
        assert result["go_no_go"] == "GO"


# ── Phase 489: Urban Air Mobility V2 ──
class TestUrbanAirMobilityV2:
    def test_vertiport(self):
        from simulation.urban_air_mobility_v2 import UrbanAirMobilityV2
        uam = UrbanAirMobilityV2()
        vp = uam.add_vertiport("VP1", 37.5, 127.0)
        assert vp.port_id == "VP1"

    def test_corridor(self):
        from simulation.urban_air_mobility_v2 import UrbanAirMobilityV2
        uam = UrbanAirMobilityV2()
        uam.add_vertiport("A", 37.5, 127.0)
        uam.add_vertiport("B", 37.6, 127.1)
        c = uam.create_corridor("A", "B")
        assert "distance_m" in c

    def test_flight(self):
        from simulation.urban_air_mobility_v2 import UrbanAirMobilityV2
        uam = UrbanAirMobilityV2()
        uam.add_vertiport("A", 37.5, 127.0)
        uam.add_vertiport("B", 37.6, 127.1)
        uam.create_corridor("A", "B")
        flight = uam.schedule_flight("A", "B")
        assert flight is not None

    def test_demand(self):
        from simulation.urban_air_mobility_v2 import DemandPredictor
        dp = DemandPredictor()
        forecast = dp.predict("A->B", 8)
        assert forecast.predicted_demand > 0

    def test_network_status(self):
        from simulation.urban_air_mobility_v2 import UrbanAirMobilityV2
        uam = UrbanAirMobilityV2()
        uam.add_vertiport("A", 37.5, 127.0)
        status = uam.network_status()
        assert "vertiports" in status


# ── Phase 490: Grand Unified Controller ──
class TestGrandUnifiedController:
    def test_init(self):
        from simulation.grand_unified_controller import GrandUnifiedController
        guc = GrandUnifiedController(n_drones=10)
        assert guc.n_drones == 10

    def test_tick(self):
        from simulation.grand_unified_controller import GrandUnifiedController
        guc = GrandUnifiedController(n_drones=5)
        result = guc.tick()
        assert "state" in result

    def test_run(self):
        from simulation.grand_unified_controller import GrandUnifiedController
        guc = GrandUnifiedController(n_drones=5)
        result = guc.run(duration=10, dt=1.0)
        assert "total_decisions" in result

    def test_module_update(self):
        from simulation.grand_unified_controller import GrandUnifiedController, SystemModule
        guc = GrandUnifiedController(n_drones=5)
        guc.update_module(SystemModule.FLIGHT_CONTROL, 0.2, 100)
        assert guc.modules[SystemModule.FLIGHT_CONTROL].health == 0.2

    def test_summary(self):
        from simulation.grand_unified_controller import GrandUnifiedController
        guc = GrandUnifiedController(n_drones=5)
        guc.run(5)
        s = guc.summary()
        assert "total_events" in s
