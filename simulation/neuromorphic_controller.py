"""
Phase 334: Neuromorphic Controller
Spiking Neural Network (SNN) 기반 드론 제어.
LIF(Leaky Integrate-and-Fire) 뉴런 + STDP 학습.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple


class NeuronType(Enum):
    LIF = "lif"           # Leaky Integrate-and-Fire
    IZHIKEVICH = "izhikevich"
    ADAPTIVE_LIF = "adaptive_lif"


@dataclass
class SpikeTrain:
    neuron_id: int
    spike_times: List[float] = field(default_factory=list)
    rate: float = 0.0


@dataclass
class Synapse:
    pre_id: int
    post_id: int
    weight: float
    delay: float = 1.0
    last_pre_spike: float = -1e6
    last_post_spike: float = -1e6


class LIFNeuron:
    """Leaky Integrate-and-Fire neuron model."""

    def __init__(self, neuron_id: int, tau_m: float = 20.0,
                 v_rest: float = -65.0, v_thresh: float = -55.0,
                 v_reset: float = -70.0, tau_ref: float = 2.0):
        self.neuron_id = neuron_id
        self.tau_m = tau_m
        self.v_rest = v_rest
        self.v_thresh = v_thresh
        self.v_reset = v_reset
        self.tau_ref = tau_ref
        self.v = v_rest
        self.last_spike = -1e6
        self.input_current = 0.0
        self.spike_count = 0

    def step(self, dt: float, current_time: float) -> bool:
        if current_time - self.last_spike < self.tau_ref:
            return False

        dv = (-(self.v - self.v_rest) + self.input_current) / self.tau_m * dt
        self.v += dv
        self.input_current = 0.0

        if self.v >= self.v_thresh:
            self.v = self.v_reset
            self.last_spike = current_time
            self.spike_count += 1
            return True
        return False

    def receive_spike(self, weight: float) -> None:
        self.input_current += weight


class STDPRule:
    """Spike-Timing-Dependent Plasticity learning rule."""

    def __init__(self, a_plus: float = 0.01, a_minus: float = 0.012,
                 tau_plus: float = 20.0, tau_minus: float = 20.0,
                 w_max: float = 5.0, w_min: float = 0.0):
        self.a_plus = a_plus
        self.a_minus = a_minus
        self.tau_plus = tau_plus
        self.tau_minus = tau_minus
        self.w_max = w_max
        self.w_min = w_min

    def update(self, synapse: Synapse, pre_spike_time: float,
               post_spike_time: float) -> float:
        dt = post_spike_time - pre_spike_time
        if dt > 0:
            dw = self.a_plus * np.exp(-dt / self.tau_plus)
        elif dt < 0:
            dw = -self.a_minus * np.exp(dt / self.tau_minus)
        else:
            dw = 0.0

        synapse.weight = np.clip(synapse.weight + dw, self.w_min, self.w_max)
        return dw


class SNNLayer:
    """A layer of spiking neurons."""

    def __init__(self, n_neurons: int, neuron_type: NeuronType = NeuronType.LIF,
                 label: str = ""):
        self.label = label
        self.neurons = [LIFNeuron(i) for i in range(n_neurons)]
        self.spike_trains: Dict[int, SpikeTrain] = {
            i: SpikeTrain(i) for i in range(n_neurons)
        }

    def step(self, dt: float, t: float) -> List[int]:
        spiked = []
        for neuron in self.neurons:
            if neuron.step(dt, t):
                spiked.append(neuron.neuron_id)
                self.spike_trains[neuron.neuron_id].spike_times.append(t)
        return spiked


class NeuromorphicController:
    """SNN-based drone flight controller."""

    def __init__(self, n_inputs: int = 6, n_hidden: int = 20,
                 n_outputs: int = 4, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_inputs = n_inputs
        self.n_hidden = n_hidden
        self.n_outputs = n_outputs

        self.input_layer = SNNLayer(n_inputs, label="input")
        self.hidden_layer = SNNLayer(n_hidden, label="hidden")
        self.output_layer = SNNLayer(n_outputs, label="output")

        self.synapses_ih: List[Synapse] = []
        self.synapses_ho: List[Synapse] = []

        for i in range(n_inputs):
            for h in range(n_hidden):
                w = self.rng.uniform(0.5, 2.0)
                self.synapses_ih.append(Synapse(i, h, w, delay=1.0))

        for h in range(n_hidden):
            for o in range(n_outputs):
                w = self.rng.uniform(0.5, 2.0)
                self.synapses_ho.append(Synapse(h, o, w, delay=1.0))

        self.stdp = STDPRule()
        self.dt = 0.5
        self.current_time = 0.0
        self.total_spikes = 0
        self.step_count = 0

    def encode_input(self, values: List[float]) -> None:
        for i, val in enumerate(values[:self.n_inputs]):
            current = val * 15.0 + self.rng.standard_normal() * 0.5
            self.input_layer.neurons[i].input_current = current

    def step(self) -> List[float]:
        self.current_time += self.dt
        self.step_count += 1

        input_spikes = self.input_layer.step(self.dt, self.current_time)
        self.total_spikes += len(input_spikes)

        for syn in self.synapses_ih:
            if syn.pre_id in input_spikes:
                self.hidden_layer.neurons[syn.post_id].receive_spike(syn.weight)
                syn.last_pre_spike = self.current_time

        hidden_spikes = self.hidden_layer.step(self.dt, self.current_time)
        self.total_spikes += len(hidden_spikes)

        for syn in self.synapses_ho:
            if syn.pre_id in hidden_spikes:
                self.output_layer.neurons[syn.post_id].receive_spike(syn.weight)
                syn.last_pre_spike = self.current_time

        output_spikes = self.output_layer.step(self.dt, self.current_time)
        self.total_spikes += len(output_spikes)

        # STDP learning on hidden→output
        for syn in self.synapses_ho:
            if syn.pre_id in hidden_spikes and syn.post_id in output_spikes:
                self.stdp.update(syn, self.current_time, self.current_time)

        outputs = []
        for o in range(self.n_outputs):
            n = self.output_layer.neurons[o]
            rate = n.spike_count / max(self.current_time / 1000.0, 0.001)
            outputs.append(rate)
        return outputs

    def control_step(self, sensor_data: Dict[str, float]) -> Dict[str, float]:
        inputs = [
            sensor_data.get("roll_error", 0),
            sensor_data.get("pitch_error", 0),
            sensor_data.get("yaw_error", 0),
            sensor_data.get("alt_error", 0),
            sensor_data.get("vx_error", 0),
            sensor_data.get("vy_error", 0),
        ]
        self.encode_input(inputs)
        outputs = self.step()
        scale = 0.01
        return {
            "roll_cmd": outputs[0] * scale if len(outputs) > 0 else 0,
            "pitch_cmd": outputs[1] * scale if len(outputs) > 1 else 0,
            "yaw_cmd": outputs[2] * scale if len(outputs) > 2 else 0,
            "thrust_cmd": outputs[3] * scale if len(outputs) > 3 else 0,
        }

    def run_for(self, sensor_sequence: List[Dict[str, float]]) -> List[Dict[str, float]]:
        results = []
        for sensor_data in sensor_sequence:
            cmd = self.control_step(sensor_data)
            results.append(cmd)
        return results

    def get_weight_stats(self) -> Dict[str, float]:
        all_w = [s.weight for s in self.synapses_ih + self.synapses_ho]
        return {
            "mean": float(np.mean(all_w)),
            "std": float(np.std(all_w)),
            "min": float(np.min(all_w)),
            "max": float(np.max(all_w)),
        }

    def summary(self) -> Dict:
        return {
            "layers": f"{self.n_inputs}-{self.n_hidden}-{self.n_outputs}",
            "synapses": len(self.synapses_ih) + len(self.synapses_ho),
            "total_spikes": self.total_spikes,
            "steps": self.step_count,
            "sim_time_ms": self.current_time,
            "weight_stats": self.get_weight_stats(),
        }


if __name__ == "__main__":
    ctrl = NeuromorphicController(n_inputs=6, n_hidden=20, n_outputs=4)

    for t in range(50):
        sensor = {
            "roll_error": np.sin(t * 0.1) * 5,
            "pitch_error": np.cos(t * 0.1) * 3,
            "yaw_error": 0.5,
            "alt_error": 2.0 - t * 0.04,
            "vx_error": 1.0,
            "vy_error": -0.5,
        }
        cmd = ctrl.control_step(sensor)

    print(f"Summary: {ctrl.summary()}")
