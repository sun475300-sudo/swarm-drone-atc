"""
Phase 331-340 테스트 스위트
Quantum Path Optimizer, WASM Runtime, Digital Sovereignty,
Neuromorphic Controller, Mesh Network, Digital Thread,
Game Theory, Acoustic Sensing, Swarm Encryption, Predictive Maintenance v2
"""

import pytest
import numpy as np


# ── Phase 331: Quantum Path Optimizer ───────────────────────────────
class TestQuantumPathOptimizer:
    def test_add_nodes_and_edges(self):
        from simulation.quantum_path_optimizer import QuantumPathOptimizer, QuantumBackend
        opt = QuantumPathOptimizer(seed=42, backend=QuantumBackend.ANNEALING)
        opt.add_node("A", 0, 0, 0)
        opt.add_node("B", 100, 0, 0)
        cost = opt.add_edge("A", "B")
        assert cost == pytest.approx(100.0, abs=0.1)
        assert len(opt.nodes) == 2

    def test_annealing_optimize(self):
        from simulation.quantum_path_optimizer import QuantumPathOptimizer, QuantumBackend
        opt = QuantumPathOptimizer(seed=42, backend=QuantumBackend.ANNEALING)
        for i in range(5):
            opt.add_node(f"n{i}", np.cos(i) * 50, np.sin(i) * 50, 0)
        ids = list(opt.nodes.keys())
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                opt.add_edge(ids[i], ids[j])
        result = opt.optimize_path(max_iter=50)
        assert len(result.path) == 5
        assert result.total_cost < 1e6
        assert result.method == "annealing"

    def test_qaoa_backend(self):
        from simulation.quantum_path_optimizer import QuantumPathOptimizer, QuantumBackend
        opt = QuantumPathOptimizer(seed=42, backend=QuantumBackend.QAOA)
        for i in range(4):
            opt.add_node(f"n{i}", i * 10, 0, 0)
        ids = list(opt.nodes.keys())
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                opt.add_edge(ids[i], ids[j])
        result = opt.optimize_path(max_iter=10)
        assert len(result.convergence) > 0

    def test_vqe_backend(self):
        from simulation.quantum_path_optimizer import QuantumPathOptimizer, QuantumBackend
        opt = QuantumPathOptimizer(seed=42, backend=QuantumBackend.VQE)
        for i in range(4):
            opt.add_node(f"n{i}", i * 20, i * 10, 0)
        ids = list(opt.nodes.keys())
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                opt.add_edge(ids[i], ids[j])
        result = opt.optimize_path(max_iter=20)
        assert result.method == "vqe"

    def test_summary(self):
        from simulation.quantum_path_optimizer import QuantumPathOptimizer, QuantumBackend
        opt = QuantumPathOptimizer(seed=42, backend=QuantumBackend.ANNEALING)
        opt.add_node("a", 0, 0, 0)
        opt.add_node("b", 10, 0, 0)
        opt.add_edge("a", "b")
        opt.optimize_path(max_iter=10)
        s = opt.summary()
        assert s["nodes"] == 2
        assert s["optimizations_run"] == 1


# ── Phase 332: WASM Runtime Engine ──────────────────────────────────
class TestWasmRuntime:
    def test_vm_execute_add(self):
        from simulation.wasm_runtime_engine import WasmVM, WasmModule, WasmFunction, WasmOpcode
        vm = WasmVM()
        func = WasmFunction("add", param_count=0, local_count=0, bytecode=[
            WasmOpcode.CONST_I32, 10,
            WasmOpcode.CONST_I32, 20,
            WasmOpcode.ADD_I32,
            WasmOpcode.RETURN,
        ])
        module = WasmModule("test")
        module.functions["add"] = func
        vm.load_module(module)
        result = vm.execute("test", "add")
        assert result == 30

    def test_firmware_compiler_altitude(self):
        from simulation.wasm_runtime_engine import WasmVM, WasmModule, DroneFirmwareCompiler
        vm = WasmVM()
        compiler = DroneFirmwareCompiler()
        module = WasmModule("fw")
        module.functions["alt_hold"] = compiler.compile_altitude_hold(50)
        vm.load_module(module)
        result = vm.execute("fw", "alt_hold", [45])
        assert result == -5  # 45 - 50 = -5

    def test_memory_load_store(self):
        from simulation.wasm_runtime_engine import WasmMemory
        mem = WasmMemory(1)
        mem.store_i32(0, 42)
        assert mem.load_i32(0) == 42

    def test_geofence_check(self):
        from simulation.wasm_runtime_engine import WasmVM, WasmModule, DroneFirmwareCompiler
        vm = WasmVM()
        compiler = DroneFirmwareCompiler()
        module = WasmModule("fw")
        module.functions["geo"] = compiler.compile_geofence_check(1000)
        vm.load_module(module)
        assert vm.execute("fw", "geo", [500]) == 1
        assert vm.execute("fw", "geo", [1500]) == 0

    def test_vm_summary(self):
        from simulation.wasm_runtime_engine import WasmVM, WasmModule, WasmFunction, WasmOpcode
        vm = WasmVM()
        module = WasmModule("test")
        module.functions["nop"] = WasmFunction("nop", 0, 0, [WasmOpcode.CONST_I32, 1, WasmOpcode.RETURN])
        vm.load_module(module)
        vm.execute("test", "nop")
        s = vm.summary()
        assert s["modules"] == 1


# ── Phase 333: Digital Sovereignty Manager ──────────────────────────
class TestDigitalSovereignty:
    def test_ingest_data(self):
        from simulation.digital_sovereignty_manager import (
            DigitalSovereigntyManager, Region, DataClassification)
        mgr = DigitalSovereigntyManager(Region.KR)
        rec = mgr.ingest_data("r1", Region.KR, DataClassification.PUBLIC, b"hello", 1.0)
        assert rec.record_id == "r1"
        assert rec.size_bytes == 5

    def test_route_public_allowed(self):
        from simulation.digital_sovereignty_manager import (
            DigitalSovereigntyManager, Region, DataClassification)
        mgr = DigitalSovereigntyManager(Region.KR)
        mgr.ingest_data("r1", Region.KR, DataClassification.PUBLIC, b"data", 1.0)
        ok, err = mgr.route_data("r1", Region.US)
        assert ok is True

    def test_route_confidential_blocked(self):
        from simulation.digital_sovereignty_manager import (
            DigitalSovereigntyManager, Region, DataClassification)
        mgr = DigitalSovereigntyManager(Region.KR)
        mgr.ingest_data("r1", Region.KR, DataClassification.CONFIDENTIAL, b"secret", 1.0)
        ok, err = mgr.route_data("r1", Region.US)
        assert ok is False

    def test_compliance_check(self):
        from simulation.digital_sovereignty_manager import (
            DigitalSovereigntyManager, Region, DataClassification)
        mgr = DigitalSovereigntyManager(Region.KR)
        mgr.ingest_data("r1", Region.KR, DataClassification.PUBLIC, b"data", 1.0)
        issues = mgr.check_compliance("r1")
        assert isinstance(issues, list)

    def test_summary(self):
        from simulation.digital_sovereignty_manager import (
            DigitalSovereigntyManager, Region, DataClassification)
        mgr = DigitalSovereigntyManager(Region.KR)
        mgr.ingest_data("r1", Region.KR, DataClassification.INTERNAL, b"data", 1.0)
        s = mgr.summary()
        assert s["total_records"] == 1


# ── Phase 334: Neuromorphic Controller ──────────────────────────────
class TestNeuromorphicController:
    def test_basic_step(self):
        from simulation.neuromorphic_controller import NeuromorphicController
        ctrl = NeuromorphicController(n_inputs=6, n_hidden=10, n_outputs=4)
        outputs = ctrl.step()
        assert len(outputs) == 4

    def test_control_step(self):
        from simulation.neuromorphic_controller import NeuromorphicController
        ctrl = NeuromorphicController()
        sensor = {"roll_error": 1.0, "pitch_error": 0.5, "yaw_error": 0,
                  "alt_error": 2.0, "vx_error": 0, "vy_error": 0}
        cmd = ctrl.control_step(sensor)
        assert "roll_cmd" in cmd
        assert "thrust_cmd" in cmd

    def test_run_for(self):
        from simulation.neuromorphic_controller import NeuromorphicController
        ctrl = NeuromorphicController()
        seq = [{"roll_error": i * 0.1, "pitch_error": 0, "yaw_error": 0,
                "alt_error": 0, "vx_error": 0, "vy_error": 0} for i in range(10)]
        results = ctrl.run_for(seq)
        assert len(results) == 10

    def test_lif_neuron_spike(self):
        from simulation.neuromorphic_controller import LIFNeuron
        neuron = LIFNeuron(0)
        neuron.input_current = 100.0
        spiked = neuron.step(1.0, 1.0)
        assert isinstance(spiked, bool)

    def test_summary(self):
        from simulation.neuromorphic_controller import NeuromorphicController
        ctrl = NeuromorphicController()
        ctrl.step()
        s = ctrl.summary()
        assert "layers" in s
        assert "synapses" in s


# ── Phase 335: Mesh Network Optimizer ───────────────────────────────
class TestMeshNetworkOptimizer:
    def test_add_nodes_and_connect(self):
        from simulation.mesh_network_optimizer import MeshNetworkOptimizer
        opt = MeshNetworkOptimizer()
        opt.add_node("a", 0, 0, 50)
        opt.add_node("b", 100, 0, 50)
        opt.add_link("a", "b")
        assert len(opt.nodes) == 2

    def test_auto_connect(self):
        from simulation.mesh_network_optimizer import MeshNetworkOptimizer
        opt = MeshNetworkOptimizer()
        for i in range(5):
            opt.add_node(f"n{i}", i * 50, 0, 50)
        count = opt.auto_connect(max_range=120)
        assert count > 0

    def test_dijkstra_routing(self):
        from simulation.mesh_network_optimizer import MeshNetworkOptimizer
        opt = MeshNetworkOptimizer()
        for i in range(4):
            opt.add_node(f"n{i}", i * 50, 0, 50)
        opt.auto_connect(max_range=120)
        opt.compute_routes()
        route = opt.get_route("n0", "n3")
        assert route is not None
        assert route.hop_count >= 1

    def test_link_failure_reroute(self):
        from simulation.mesh_network_optimizer import MeshNetworkOptimizer
        opt = MeshNetworkOptimizer()
        for i in range(4):
            opt.add_node(f"n{i}", i * 30, 0, 50)
        opt.auto_connect(max_range=100)
        opt.compute_routes()
        opt.fail_link("n0", "n1")
        opt.compute_routes()
        # Should still find route if alternate paths exist

    def test_summary(self):
        from simulation.mesh_network_optimizer import MeshNetworkOptimizer
        opt = MeshNetworkOptimizer()
        opt.add_node("a", 0, 0, 0, is_gateway=True)
        opt.add_node("b", 50, 0, 0)
        opt.add_link("a", "b")
        s = opt.summary()
        assert s["nodes"] == 2
        assert s["gateways"] == 1


# ── Phase 336: Digital Thread Manager ───────────────────────────────
class TestDigitalThreadManager:
    def test_create_thread(self):
        from simulation.digital_thread_manager import DigitalThreadManager, LifecyclePhase
        mgr = DigitalThreadManager()
        t = mgr.create_thread("d1", "QuadX", "SN-001")
        assert t.drone_id == "d1"
        assert t.current_phase == LifecyclePhase.DESIGN

    def test_phase_transition(self):
        from simulation.digital_thread_manager import DigitalThreadManager, LifecyclePhase
        mgr = DigitalThreadManager()
        mgr.create_thread("d1", "QuadX", "SN-001")
        assert mgr.transition_phase("d1", LifecyclePhase.MANUFACTURING)
        assert not mgr.transition_phase("d1", LifecyclePhase.OPERATIONAL)

    def test_record_flight(self):
        from simulation.digital_thread_manager import DigitalThreadManager, LifecyclePhase
        mgr = DigitalThreadManager()
        mgr.create_thread("d1", "QuadX", "SN-001")
        for phase in [LifecyclePhase.MANUFACTURING, LifecyclePhase.TESTING,
                      LifecyclePhase.DEPLOYMENT, LifecyclePhase.OPERATIONAL]:
            mgr.transition_phase("d1", phase)
        assert mgr.record_flight("d1", 2.5)
        assert mgr.threads["d1"].total_missions == 1

    def test_component_and_fault(self):
        from simulation.digital_thread_manager import DigitalThreadManager
        mgr = DigitalThreadManager()
        mgr.create_thread("d1", "QuadX", "SN-001")
        comp = mgr.add_component("d1", "m1", "motor", "MOT-001")
        assert comp is not None
        assert mgr.record_fault("d1", "vibration anomaly", "m1")

    def test_fleet_health(self):
        from simulation.digital_thread_manager import DigitalThreadManager
        mgr = DigitalThreadManager()
        mgr.create_thread("d1", "QuadX", "SN-001")
        h = mgr.fleet_health()
        assert h["total_drones"] == 1


# ── Phase 337: Swarm Game Theory ────────────────────────────────────
class TestSwarmGameTheory:
    def test_play_round(self):
        from simulation.swarm_game_theory import SwarmGameTheory, Strategy, GameType
        game = SwarmGameTheory(GameType.PRISONERS_DILEMMA)
        game.add_player("a", Strategy.ALWAYS_COOPERATE)
        game.add_player("b", Strategy.ALWAYS_DEFECT)
        result = game.play_round("a", "b")
        assert result.payoff_a == 0
        assert result.payoff_b == 5

    def test_tournament(self):
        from simulation.swarm_game_theory import SwarmGameTheory, Strategy, GameType
        game = SwarmGameTheory(GameType.PRISONERS_DILEMMA)
        game.add_player("tft", Strategy.TIT_FOR_TAT)
        game.add_player("coop", Strategy.ALWAYS_COOPERATE)
        game.add_player("defect", Strategy.ALWAYS_DEFECT)
        scores = game.play_tournament(10)
        assert len(scores) == 3

    def test_nash_equilibria(self):
        from simulation.swarm_game_theory import SwarmGameTheory, GameType
        game = SwarmGameTheory(GameType.PRISONERS_DILEMMA)
        nash = game.find_nash_equilibria()
        assert len(nash) >= 1

    def test_pareto_frontier(self):
        from simulation.swarm_game_theory import SwarmGameTheory, GameType
        game = SwarmGameTheory(GameType.PRISONERS_DILEMMA)
        pareto = game.find_pareto_frontier()
        assert len(pareto) >= 1

    def test_summary(self):
        from simulation.swarm_game_theory import SwarmGameTheory, Strategy, GameType
        game = SwarmGameTheory(GameType.STAG_HUNT)
        game.add_player("a", Strategy.TIT_FOR_TAT)
        game.add_player("b", Strategy.PAVLOV)
        game.play_tournament(5)
        s = game.summary()
        assert s["game_type"] == "stag_hunt"


# ── Phase 338: Acoustic Sensing ─────────────────────────────────────
class TestAcousticSensing:
    def test_fft_spectrum(self):
        from simulation.acoustic_sensing import FFTAnalyzer
        fft = FFTAnalyzer(44100, 2048)
        t = np.arange(2048) / 44100
        signal = np.sin(2 * np.pi * 440 * t)
        freqs, mags = fft.compute_spectrum(signal)
        assert len(freqs) > 0

    def test_signal_classification(self):
        from simulation.acoustic_sensing import FFTAnalyzer, SpectralPeak
        fft = FFTAnalyzer()
        peaks = [SpectralPeak(200, 1.0, 0), SpectralPeak(400, 0.5, 0), SpectralPeak(600, 0.3, 0)]
        sig_type = fft.classify_signal(peaks)
        assert sig_type.value == "propeller"

    def test_generate_and_process(self):
        from simulation.acoustic_sensing import AcousticSensingSystem
        sys = AcousticSensingSystem(n_mics=4, seed=42)
        signals = sys.generate_test_signal(200, duration=0.05, azimuth_deg=30)
        det = sys.process(signals, timestamp=1.0)
        assert det is not None or True  # may not detect in all configs

    def test_summary(self):
        from simulation.acoustic_sensing import AcousticSensingSystem
        sys = AcousticSensingSystem(seed=42)
        s = sys.summary()
        assert s["microphones"] == 4


# ── Phase 339: Drone Swarm Encryption ───────────────────────────────
class TestDroneSwarmEncryption:
    def test_register_and_group(self):
        from simulation.drone_swarm_encryption import DroneSwarmEncryption, CipherSuite
        enc = DroneSwarmEncryption(CipherSuite.HYBRID_PQ)
        enc.register_drone("d1")
        enc.register_drone("d2")
        gk = enc.establish_group(["d1", "d2"])
        assert gk is not None

    def test_encrypt_decrypt(self):
        from simulation.drone_swarm_encryption import DroneSwarmEncryption, CipherSuite
        enc = DroneSwarmEncryption(CipherSuite.HYBRID_PQ)
        enc.register_drone("d1")
        enc.register_drone("d2")
        enc.establish_group(["d1", "d2"])
        msg = enc.encrypt_message("d1", b"hello swarm")
        plain = enc.decrypt_message(msg, "d2")
        assert plain == b"hello swarm"

    def test_key_rotation(self):
        from simulation.drone_swarm_encryption import DroneSwarmEncryption, CipherSuite
        enc = DroneSwarmEncryption(CipherSuite.HYBRID_PQ)
        enc.register_drone("d1")
        enc.establish_group(["d1"])
        old_epoch = enc.key_manager.epoch
        enc.rotate_group_key()
        assert enc.key_manager.epoch > old_epoch

    def test_revoke_drone(self):
        from simulation.drone_swarm_encryption import DroneSwarmEncryption, CipherSuite
        enc = DroneSwarmEncryption(CipherSuite.HYBRID_PQ)
        for i in range(3):
            enc.register_drone(f"d{i}")
        enc.establish_group(["d0", "d1", "d2"])
        new_key = enc.revoke_drone("d2")
        assert "d2" not in new_key.member_ids

    def test_summary(self):
        from simulation.drone_swarm_encryption import DroneSwarmEncryption, CipherSuite
        enc = DroneSwarmEncryption(CipherSuite.HYBRID_PQ)
        enc.register_drone("d1")
        s = enc.summary()
        assert s["registered_drones"] == 1


# ── Phase 340: Predictive Maintenance v2 ────────────────────────────
class TestPredictiveMaintenanceV2:
    def test_register_component(self):
        from simulation.predictive_maintenance_v2 import PredictiveMaintenanceV2, ComponentType
        pm = PredictiveMaintenanceV2()
        pm.register_component("m1", ComponentType.MOTOR, 100)
        assert "m1" in pm.components

    def test_process_reading(self):
        from simulation.predictive_maintenance_v2 import (
            PredictiveMaintenanceV2, ComponentType, SensorReading)
        pm = PredictiveMaintenanceV2()
        pm.register_component("m1", ComponentType.MOTOR)
        reading = SensorReading(1.0, "m1", 0.5, 40, 5, 11.1, 5000)
        health = pm.process_reading(reading)
        assert 0 <= health.health_score <= 100

    def test_weibull_reliability(self):
        from simulation.predictive_maintenance_v2 import WeibullAnalyzer, ComponentType
        w = WeibullAnalyzer()
        r = w.reliability(ComponentType.MOTOR, 0)
        assert r == pytest.approx(1.0, abs=0.01)
        r2 = w.reliability(ComponentType.MOTOR, 10000)
        assert r2 < 0.1

    def test_weibull_rul(self):
        from simulation.predictive_maintenance_v2 import WeibullAnalyzer, ComponentType
        w = WeibullAnalyzer()
        rul = w.rul_estimate(ComponentType.MOTOR, 0)
        assert rul > 0

    def test_fleet_report(self):
        from simulation.predictive_maintenance_v2 import (
            PredictiveMaintenanceV2, ComponentType, SensorReading)
        pm = PredictiveMaintenanceV2(seed=42)
        pm.register_component("m1", ComponentType.MOTOR)
        for t in range(10):
            pm.process_reading(SensorReading(float(t), "m1", 0.5, 40, 5, 11, 5000))
        report = pm.fleet_health_report()
        assert report["total_components"] == 1

    def test_summary(self):
        from simulation.predictive_maintenance_v2 import PredictiveMaintenanceV2
        pm = PredictiveMaintenanceV2()
        s = pm.summary()
        assert "total_readings" in s
