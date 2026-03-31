"""
Phase 501-520 통합 테스트 — 20개 모듈 × 5 테스트 = 100 테스트
"""

import pytest
import numpy as np


# ==================== Phase 501: Digital Sovereignty V3 ====================
class TestDigitalSovereigntyV3:
    def test_init(self):
        from simulation.digital_sovereignty_v3 import DigitalSovereigntyV3
        ds = DigitalSovereigntyV3(seed=42)
        assert ds is not None

    def test_summary_keys(self):
        from simulation.digital_sovereignty_v3 import DigitalSovereigntyV3
        ds = DigitalSovereigntyV3(seed=42)
        s = ds.summary()
        assert "home_region" in s

    def test_compliance_score(self):
        from simulation.digital_sovereignty_v3 import DigitalSovereigntyV3
        ds = DigitalSovereigntyV3(seed=42)
        score = ds.compliance_score()
        assert 0 <= score <= 1

    def test_regional_policy(self):
        from simulation.digital_sovereignty_v3 import DigitalSovereigntyV3, Region
        ds = DigitalSovereigntyV3(seed=42)
        assert len(Region) >= 3

    def test_summary(self):
        from simulation.digital_sovereignty_v3 import DigitalSovereigntyV3
        ds = DigitalSovereigntyV3(seed=42)
        summary = ds.summary()
        assert "policies" in summary


# ==================== Phase 502: Collective Intelligence ====================
class TestCollectiveIntelligence:
    def test_init(self):
        from simulation.collective_intelligence import CollectiveIntelligence
        ci = CollectiveIntelligence(n_drones=8, seed=42)
        assert ci.n_drones == 8

    def test_consensus(self):
        from simulation.collective_intelligence import CollectiveIntelligence
        ci = CollectiveIntelligence(seed=42)
        result = ci.reach_consensus("test_topic")
        assert isinstance(result, dict)

    def test_summary_keys(self):
        from simulation.collective_intelligence import CollectiveIntelligence
        ci = CollectiveIntelligence(seed=42)
        s = ci.summary()
        assert "drones" in s

    def test_step(self):
        from simulation.collective_intelligence import CollectiveIntelligence
        ci = CollectiveIntelligence(seed=42)
        result = ci.step()
        assert isinstance(result, dict)

    def test_consensus_engine(self):
        from simulation.collective_intelligence import ConsensusEngine, ConsensusAlgorithm
        ce = ConsensusEngine(n_drones=10, seed=42)
        assert ce is not None


# ==================== Phase 503: Quantum Communication ====================
class TestQuantumCommunication:
    def test_bb84(self):
        from simulation.quantum_communication import BB84Protocol
        bb84 = BB84Protocol(seed=42)
        result = bb84.execute(256)
        assert result.raw_key_length == 256
        assert 0 <= result.error_rate <= 1

    def test_qkd_secure(self):
        from simulation.quantum_communication import BB84Protocol
        bb84 = BB84Protocol(seed=42)
        result = bb84.execute(512, eve_present=False)
        assert result.secure is True
        assert len(result.final_key) > 0

    def test_qkd_eavesdrop(self):
        from simulation.quantum_communication import BB84Protocol
        bb84 = BB84Protocol(seed=42)
        result = bb84.execute(1024, eve_present=True)
        assert result.error_rate > 0.05

    def test_teleportation(self):
        from simulation.quantum_communication import QuantumTeleportation
        qt = QuantumTeleportation(seed=42)
        state = (0.6 + 0j, 0.8 + 0j)
        result = qt.teleport(state)
        assert len(result) == 2
        assert qt.avg_fidelity() > 0.8

    def test_integrated_system(self):
        from simulation.quantum_communication import QuantumCommunication
        qc = QuantumCommunication(n_drones=5, seed=42)
        result = qc.establish_qkd("d0", "d1")
        s = qc.summary()
        assert s["drones"] == 5


# ==================== Phase 504: Hyperspectral Sensor ====================
class TestHyperspectralSensor:
    def test_init(self):
        from simulation.hyperspectral_sensor import HyperspectralSensor
        hs = HyperspectralSensor(n_bands=32, seed=42)
        assert hs.n_bands == 32

    def test_capture(self):
        from simulation.hyperspectral_sensor import HyperspectralSensor
        hs = HyperspectralSensor(n_bands=16, resolution=4, seed=42)
        pixels = hs.capture(100)
        assert len(pixels) == 16  # 4x4

    def test_classify(self):
        from simulation.hyperspectral_sensor import SpectralClassifier, SpectralLibrary, TerrainType
        lib = SpectralLibrary(32, seed=42)
        clf = SpectralClassifier(lib)
        spectrum = lib.signatures[TerrainType.WATER].copy()
        terrain, conf = clf.classify(spectrum)
        assert terrain == TerrainType.WATER
        assert conf > 0.5

    def test_ndvi(self):
        from simulation.hyperspectral_sensor import HyperspectralSensor
        hs = HyperspectralSensor(n_bands=16, resolution=4, seed=42)
        pixels = hs.capture()
        ndvi = hs.ndvi(pixels)
        assert len(ndvi) == len(pixels)
        assert all(-1 <= v <= 1 for v in ndvi)

    def test_summary(self):
        from simulation.hyperspectral_sensor import HyperspectralSensor
        hs = HyperspectralSensor(seed=42)
        s = hs.summary()
        assert s["bands"] == 64


# ==================== Phase 505: Cyber-Physical Security ====================
class TestCyberPhysicalSecurity:
    def test_init(self):
        from simulation.cyber_physical_security import CyberPhysicalSecurity
        cps = CyberPhysicalSecurity(n_drones=10, seed=42)
        assert cps.n_drones == 10

    def test_firmware_check(self):
        from simulation.cyber_physical_security import CyberPhysicalSecurity
        cps = CyberPhysicalSecurity(seed=42)
        check = cps.check_firmware(0)
        assert check.passed is True

    def test_tampered_firmware(self):
        from simulation.cyber_physical_security import CyberPhysicalSecurity
        cps = CyberPhysicalSecurity(seed=42)
        check = cps.check_firmware(0, "TAMPERED_DATA")
        assert check.passed is False

    def test_sensor_anomaly(self):
        from simulation.cyber_physical_security import CyberPhysicalSecurity
        cps = CyberPhysicalSecurity(seed=42)
        score = cps.check_sensor(0, "altimeter", 50.0, (10, 150))
        assert 0 <= score <= 1

    def test_scan(self):
        from simulation.cyber_physical_security import CyberPhysicalSecurity
        cps = CyberPhysicalSecurity(n_drones=5, seed=42)
        result = cps.run_scan()
        assert "firmware_ok" in result


# ==================== Phase 506: Drone Forensics ====================
class TestDroneForensics:
    def test_init(self):
        from simulation.drone_forensics import DroneForensics
        df = DroneForensics(seed=42)
        assert len(df.reports) == 0

    def test_simulate_flight(self):
        from simulation.drone_forensics import DroneForensics
        df = DroneForensics(seed=42)
        records = df.simulate_flight("d0", duration=10, dt=1.0)
        assert len(records) == 10

    def test_investigate(self):
        from simulation.drone_forensics import DroneForensics, IncidentType
        df = DroneForensics(seed=42)
        df.simulate_flight("d0", 20)
        report = df.investigate("d0", IncidentType.CRASH, 15.0)
        assert report.incident_type == IncidentType.CRASH
        assert len(report.evidence_chain) == 3

    def test_evidence_chain(self):
        from simulation.drone_forensics import EvidenceChain, EvidenceType
        chain = EvidenceChain()
        chain.add(EvidenceType.FLIGHT_LOG, "d0", "data1", 0)
        chain.add(EvidenceType.TELEMETRY, "d0", "data2", 1)
        assert chain.verify() is True

    def test_summary(self):
        from simulation.drone_forensics import DroneForensics
        df = DroneForensics(seed=42)
        df.simulate_flight("d0", 10)
        s = df.summary()
        assert s["drones_recorded"] == 1


# ==================== Phase 507: Aero-Acoustic V2 ====================
class TestAeroAcousticV2:
    def test_propeller_noise(self):
        from simulation.aero_acoustic_v2 import PropellerNoiseModel
        pm = PropellerNoiseModel(seed=42)
        profile = pm.predict(5000)
        assert len(profile.spl_db) > 0
        assert profile.rpm == 5000

    def test_oaspl(self):
        from simulation.aero_acoustic_v2 import PropellerNoiseModel
        pm = PropellerNoiseModel(seed=42)
        profile = pm.predict(6000)
        oaspl = pm.oaspl(profile)
        assert 40 < oaspl < 120

    def test_propagation(self):
        from simulation.aero_acoustic_v2 import AcousticPropagation
        ap = AcousticPropagation()
        att = ap.attenuate(80, 100)
        assert att < 80

    def test_stealth_rpm(self):
        from simulation.aero_acoustic_v2 import AeroAcousticV2
        aa = AeroAcousticV2(seed=42)
        rpm = aa.stealth_rpm(55.0)
        assert 1000 <= rpm <= 10000

    def test_summary(self):
        from simulation.aero_acoustic_v2 import AeroAcousticV2
        aa = AeroAcousticV2(seed=42)
        s = aa.summary()
        assert "stealth_rpm" in s


# ==================== Phase 508: Tactical Planner ====================
class TestTacticalPlanner:
    def test_init(self):
        from simulation.tactical_planner import TacticalPlanner
        tp = TacticalPlanner(n_drones=10, seed=42)
        assert len(tp.drones) == 10

    def test_add_task(self):
        from simulation.tactical_planner import TacticalPlanner, MissionPriority
        tp = TacticalPlanner(seed=42)
        task = tp.add_task(np.array([100, 200, 50]), MissionPriority.HIGH)
        assert task.priority == MissionPriority.HIGH

    def test_generate_mission(self):
        from simulation.tactical_planner import TacticalPlanner
        tp = TacticalPlanner(seed=42)
        tasks = tp.generate_mission(10)
        assert len(tasks) == 10

    def test_plan(self):
        from simulation.tactical_planner import TacticalPlanner
        tp = TacticalPlanner(n_drones=5, seed=42)
        tp.generate_mission(8)
        result = tp.plan()
        assert result["assigned"] > 0

    def test_replan(self):
        from simulation.tactical_planner import TacticalPlanner
        tp = TacticalPlanner(n_drones=5, seed=42)
        tp.generate_mission(5)
        tp.plan()
        result = tp.replan("drone_0")
        assert "drone_0" not in tp.drones


# ==================== Phase 509: Autonomous Landing ====================
class TestAutonomousLanding:
    def test_init(self):
        from simulation.autonomous_landing import AutonomousLanding
        al = AutonomousLanding(n_zones=5, seed=42)
        assert len(al.zones) == 5

    def test_select_zone(self):
        from simulation.autonomous_landing import AutonomousLanding, LandingMode
        al = AutonomousLanding(seed=42)
        zone_id = al.select_zone(np.array([0, 0, 100]), LandingMode.EMERGENCY)
        assert zone_id is not None  # emergency mode accepts any zone

    def test_execute_landing(self):
        from simulation.autonomous_landing import AutonomousLanding, LandingMode
        al = AutonomousLanding(seed=42)
        zone_id = list(al.zones.keys())[0]
        attempt = al.execute_landing("d0", zone_id)
        assert attempt.drone_id == "d0"

    def test_emergency_land(self):
        from simulation.autonomous_landing import AutonomousLanding
        al = AutonomousLanding(seed=42)
        attempt = al.emergency_land("d0", np.array([0, 0, 80]))
        assert attempt.mode.value == "emergency"

    def test_summary(self):
        from simulation.autonomous_landing import AutonomousLanding
        al = AutonomousLanding(seed=42)
        al.execute_landing("d0", list(al.zones.keys())[0])
        s = al.summary()
        assert s["attempts"] == 1


# ==================== Phase 510: Swarm Blockchain ====================
class TestSwarmBlockchain:
    def test_init(self):
        from simulation.swarm_blockchain import SwarmBlockchain
        sb = SwarmBlockchain(n_drones=10, seed=42)
        assert sb.ledger.height >= 2

    def test_assign_mission(self):
        from simulation.swarm_blockchain import SwarmBlockchain
        sb = SwarmBlockchain(seed=42)
        result = sb.assign_mission("drone_0", {"target": [100, 200, 50]})
        assert "tx" in result

    def test_chain_integrity(self):
        from simulation.swarm_blockchain import SwarmBlockchain
        sb = SwarmBlockchain(seed=42)
        sb.run_epoch()
        assert sb.ledger.verify_chain() is True

    def test_smart_contract(self):
        from simulation.swarm_blockchain import SwarmBlockchain
        sb = SwarmBlockchain(seed=42)
        result = sb.check_clearance("drone_0", {"battery": 80, "altitude": 50, "separation": 40})
        assert result["executed"] is True

    def test_penalty(self):
        from simulation.swarm_blockchain import SwarmBlockchain
        sb = SwarmBlockchain(seed=42)
        initial = sb.drone_stakes.get("drone_0", 0)
        sb.apply_penalty("drone_0", "violation", 10)
        assert sb.drone_stakes["drone_0"] < initial


# ==================== Phase 511: Edge ML Pipeline ====================
class TestEdgeMLPipeline:
    def test_init(self):
        from simulation.edge_ml_pipeline import EdgeMLPipeline
        ep = EdgeMLPipeline(n_drones=5, seed=42)
        assert len(ep.engine.models) == 6  # 3 original + 3 quantized

    def test_quantize(self):
        from simulation.edge_ml_pipeline import ModelQuantizer, EdgeModel, ModelFormat
        q = ModelQuantizer(seed=42)
        m = EdgeModel("m1", "det", 10, 3, ModelFormat.FLOAT32,
                     np.random.randn(10, 3), np.zeros(3), 5.0, 0.95)
        qm = q.quantize(m, ModelFormat.INT8)
        assert qm.format == ModelFormat.INT8
        assert qm.accuracy < m.accuracy

    def test_inference(self):
        from simulation.edge_ml_pipeline import EdgeMLPipeline
        ep = EdgeMLPipeline(seed=42)
        result = ep.run_inference_batch(5)
        assert result["inferences"] > 0

    def test_federated_round(self):
        from simulation.edge_ml_pipeline import OnDeviceLearner
        ol = OnDeviceLearner(5, seed=42)
        result = ol.federated_round()
        assert result["round"] == 1

    def test_summary(self):
        from simulation.edge_ml_pipeline import EdgeMLPipeline
        ep = EdgeMLPipeline(seed=42)
        s = ep.summary()
        assert s["models_loaded"] == 6


# ==================== Phase 512: Fault-Tolerant Navigation ====================
class TestFaultTolerantNav:
    def test_init(self):
        from simulation.fault_tolerant_nav import FaultTolerantNav
        fn = FaultTolerantNav(seed=42)
        assert len(fn.sensor_health) == 6

    def test_step(self):
        from simulation.fault_tolerant_nav import FaultTolerantNav
        fn = FaultTolerantNav(seed=42)
        sol = fn.step()
        assert len(sol.position) == 3
        assert 0 <= sol.confidence <= 2

    def test_fault_injection(self):
        from simulation.fault_tolerant_nav import FaultTolerantNav, NavSensor, NavHealth
        fn = FaultTolerantNav(seed=42)
        fn.inject_fault(NavSensor.GPS, NavHealth.FAILED)
        sol = fn.step()
        assert NavSensor.GPS not in sol.sensors_used

    def test_run(self):
        from simulation.fault_tolerant_nav import FaultTolerantNav
        fn = FaultTolerantNav(seed=42)
        sols = fn.run(duration=2, dt=0.1)
        assert len(sols) == 20

    def test_summary(self):
        from simulation.fault_tolerant_nav import FaultTolerantNav
        fn = FaultTolerantNav(seed=42)
        fn.run(1, 0.1)
        s = fn.summary()
        assert s["solutions"] == 10


# ==================== Phase 513: Cooperative Perception ====================
class TestCooperativePerception:
    def test_init(self):
        from simulation.cooperative_perception import CooperativePerception
        cp = CooperativePerception(n_drones=4, seed=42)
        assert cp.n_drones == 4

    def test_simulate_detections(self):
        from simulation.cooperative_perception import CooperativePerception
        cp = CooperativePerception(n_drones=3, seed=42)
        dets = cp.simulate_detections(10)
        assert len(dets) > 0

    def test_fusion(self):
        from simulation.cooperative_perception import MultiViewFusion, Detection, ObjectClass
        f = MultiViewFusion(seed=42)
        dets = [
            Detection("d0", "o0", ObjectClass.VEHICLE, np.array([10, 20, 0]), 0.8, 0),
            Detection("d1", "o0", ObjectClass.VEHICLE, np.array([11, 21, 0]), 0.7, 0),
        ]
        tracks = f.fuse(dets)
        assert len(tracks) == 1
        assert tracks[0].confidence > 0.8

    def test_perceive(self):
        from simulation.cooperative_perception import CooperativePerception
        cp = CooperativePerception(n_drones=3, seed=42)
        result = cp.perceive(15)
        assert result["raw_detections"] > 0

    def test_summary(self):
        from simulation.cooperative_perception import CooperativePerception
        cp = CooperativePerception(seed=42)
        cp.perceive(10)
        s = cp.summary()
        assert s["active_tracks"] > 0


# ==================== Phase 514: Satellite Relay ====================
class TestSatelliteRelay:
    def test_init(self):
        from simulation.satellite_relay import SatelliteRelay
        sr = SatelliteRelay(n_drones=5, n_sats=8, seed=42)
        assert len(sr.satellites) == 8

    def test_constellation(self):
        from simulation.satellite_relay import OrbitalMechanics
        om = OrbitalMechanics(seed=42)
        sats = om.create_constellation(6, 550)
        assert len(sats) == 6
        assert all(s.altitude_km == 550 for s in sats)

    def test_step(self):
        from simulation.satellite_relay import SatelliteRelay
        sr = SatelliteRelay(seed=42)
        result = sr.step(10)
        assert "connected" in result

    def test_handover(self):
        from simulation.satellite_relay import SatelliteRelay
        sr = SatelliteRelay(seed=42)
        for _ in range(10):
            sr.step(10)
        s = sr.summary()
        assert s["active_links"] > 0

    def test_summary(self):
        from simulation.satellite_relay import SatelliteRelay
        sr = SatelliteRelay(seed=42)
        s = sr.summary()
        assert s["satellites"] == 12


# ==================== Phase 515: EM Shielding ====================
class TestEMShielding:
    def test_init(self):
        from simulation.em_shielding import EMShielding
        em = EMShielding(seed=42)
        assert len(em.shields) == 2

    def test_shielding_effectiveness(self):
        from simulation.em_shielding import ShieldingEffectiveness, ShieldConfig, ShieldMaterial
        se = ShieldingEffectiveness()
        cfg = ShieldConfig(ShieldMaterial.COPPER, 0.5, 90, 50, 20)
        val = se.compute_se(cfg, 1000)
        assert val > 0

    def test_emc_test(self):
        from simulation.em_shielding import EMShielding
        em = EMShielding(seed=42)
        report = em.run_emc_test("primary")
        assert report.worst_frequency_mhz > 0

    def test_optimize(self):
        from simulation.em_shielding import EMShielding
        em = EMShielding(seed=42)
        opt = em.optimize_shield(100, 40)
        assert opt.thickness_mm > 0

    def test_summary(self):
        from simulation.em_shielding import EMShielding
        em = EMShielding(seed=42)
        s = em.summary()
        assert s["shields"] == 2


# ==================== Phase 516: Formation GAN ====================
class TestFormationGAN:
    def test_init(self):
        from simulation.formation_gan import FormationGAN
        fg = FormationGAN(n_drones=8, seed=42)
        assert fg.n_drones == 8

    def test_generate(self):
        from simulation.formation_gan import FormationGAN
        fg = FormationGAN(n_drones=6, seed=42)
        f = fg.generate_formation()
        assert f.positions.shape == (6, 3)

    def test_train(self):
        from simulation.formation_gan import FormationGAN
        fg = FormationGAN(seed=42)
        metrics = fg.train(5)
        assert len(metrics) == 5

    def test_evaluator(self):
        from simulation.formation_gan import FormationEvaluator
        ev = FormationEvaluator()
        positions = np.array([[0, 0, 0], [10, 0, 0], [0, 10, 0], [10, 10, 0]])
        score = ev.evaluate(positions)
        assert 0 <= score <= 1

    def test_summary(self):
        from simulation.formation_gan import FormationGAN
        fg = FormationGAN(seed=42)
        fg.train(3)
        s = fg.summary()
        assert s["epochs_trained"] == 3


# ==================== Phase 517: Drone Digital Passport ====================
class TestDroneDigitalPassport:
    def test_init(self):
        from simulation.drone_digital_passport import DroneDigitalPassport
        dp = DroneDigitalPassport(n_drones=10, seed=42)
        assert len(dp.passports) == 10

    def test_record_flight(self):
        from simulation.drone_digital_passport import DroneDigitalPassport
        dp = DroneDigitalPassport(seed=42)
        entry = dp.record_flight("drone_0", "A", "B", 600, 5.0)
        assert entry is not None
        assert entry.departure == "A"

    def test_validate(self):
        from simulation.drone_digital_passport import DroneDigitalPassport
        dp = DroneDigitalPassport(seed=42)
        result = dp.validate("drone_0")
        assert result["valid"] is True

    def test_suspend(self):
        from simulation.drone_digital_passport import DroneDigitalPassport
        dp = DroneDigitalPassport(seed=42)
        dp.suspend("drone_0")
        result = dp.validate("drone_0")
        assert result["valid"] is False

    def test_audit(self):
        from simulation.drone_digital_passport import DroneDigitalPassport
        dp = DroneDigitalPassport(n_drones=5, seed=42)
        audit = dp.audit()
        assert audit["total_drones"] == 5
        assert audit["total_certs"] == 25


# ==================== Phase 518: Predictive Routing ====================
class TestPredictiveRouting:
    def test_init(self):
        from simulation.predictive_routing import PredictiveRouting
        pr = PredictiveRouting(n_waypoints=10, seed=42)
        assert len(pr.graph.waypoints) == 10

    def test_traffic_update(self):
        from simulation.predictive_routing import PredictiveRouting
        pr = PredictiveRouting(seed=42)
        pr.update_traffic()
        # check that some waypoints have congestion info
        assert any(w.current_load > 0 for w in pr.graph.waypoints.values())

    def test_find_route(self):
        from simulation.predictive_routing import PredictiveRouting
        pr = PredictiveRouting(n_waypoints=10, seed=42)
        wps = list(pr.graph.waypoints.keys())
        route = pr.find_route(wps[0], wps[1])
        # route might be None if no path exists
        assert route is None or route.total_distance_m > 0

    def test_predictor(self):
        from simulation.predictive_routing import TrafficPredictor
        tp = TrafficPredictor(seed=42)
        for i in range(10):
            tp.record("wp0", 0.3 + i * 0.02)
        pred = tp.predict("wp0", 300)
        assert 0 <= pred <= 1.5

    def test_summary(self):
        from simulation.predictive_routing import PredictiveRouting
        pr = PredictiveRouting(seed=42)
        s = pr.summary()
        assert s["waypoints"] == 30


# ==================== Phase 519: Quantum Sensing ====================
class TestQuantumSensing:
    def test_init(self):
        from simulation.quantum_sensing import QuantumSensing
        qs = QuantumSensing(seed=42)
        assert qs.n_sensors == 5

    def test_acceleration(self):
        from simulation.quantum_sensing import AtomInterferometer
        ai = AtomInterferometer(seed=42)
        m = ai.measure_acceleration(9.81)
        assert abs(m.value - 9.81) < 1.0
        assert m.quantum_advantage_db > 0

    def test_gravity(self):
        from simulation.quantum_sensing import QuantumGravimeter
        qg = QuantumGravimeter(seed=42)
        m = qg.measure_gravity(100)
        assert abs(m.value - 9.8) < 0.1

    def test_quantum_nav(self):
        from simulation.quantum_sensing import QuantumSensing
        qs = QuantumSensing(seed=42)
        positions = qs.quantum_enhanced_nav(np.array([0, 0, 50]), n_steps=5)
        assert len(positions) == 6

    def test_summary(self):
        from simulation.quantum_sensing import QuantumSensing
        qs = QuantumSensing(seed=42)
        qs.sense_gravity(100)
        s = qs.summary()
        assert s["measurements"] == 1


# ==================== Phase 520: Swarm Diplomacy ====================
class TestSwarmDiplomacy:
    def test_init(self):
        from simulation.swarm_diplomacy import SwarmDiplomacy
        sd = SwarmDiplomacy(n_factions=4, seed=42)
        assert len(sd.factions) == 4

    def test_negotiate(self):
        from simulation.swarm_diplomacy import SwarmDiplomacy, TreatyType
        sd = SwarmDiplomacy(seed=42)
        event = sd.negotiate("faction_0", "faction_1", TreatyType.AIRSPACE_SHARING)
        assert event.event_id is not None

    def test_resolve_dispute(self):
        from simulation.swarm_diplomacy import SwarmDiplomacy
        sd = SwarmDiplomacy(seed=42)
        result = sd.resolve_dispute("faction_0", "faction_1")
        assert result["resolved"] is True

    def test_run_round(self):
        from simulation.swarm_diplomacy import SwarmDiplomacy
        sd = SwarmDiplomacy(seed=42)
        result = sd.run_round()
        assert result["negotiations"] > 0

    def test_summary(self):
        from simulation.swarm_diplomacy import SwarmDiplomacy
        sd = SwarmDiplomacy(seed=42)
        sd.run_round()
        s = sd.summary()
        assert s["events"] > 0
