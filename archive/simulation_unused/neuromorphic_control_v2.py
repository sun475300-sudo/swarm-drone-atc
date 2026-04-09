"""
Phase 475: Neuromorphic Control
Brain-inspired neuromorphic computing for drone swarm control.
"""

import numpy as np
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Any, Callable


class NeuronType(Enum):
    """Neuron model types."""

    LIF = auto()  # Leaky Integrate-and-Fire
    IZHIKEVICH = auto()
    HODGKIN_HUXLEY = auto()
    ADAPTIVE = auto()


class SynapseType(Enum):
    """Synapse types."""

    EXCITATORY = auto()
    INHIBITORY = auto()
    MODULATORY = auto()


@dataclass
class SpikingNeuron:
    """Spiking neuron model."""

    neuron_id: str
    neuron_type: NeuronType
    membrane_potential: float = -70.0
    threshold: float = -55.0
    reset_potential: float = -70.0
    membrane_capacitance: float = 1.0
    leak_conductance: float = 0.05
    refractory_period: float = 2.0
    last_spike_time: float = -100.0
    spike_count: int = 0
    adaptation: float = 0.0


@dataclass
class Synapse:
    """Synaptic connection."""

    synapse_id: str
    pre_neuron: str
    post_neuron: str
    weight: float
    synapse_type: SynapseType
    delay_ms: float = 1.0
    plasticity: float = 0.01


@dataclass
class SpikeEvent:
    """Spike event."""

    neuron_id: str
    timestamp: float
    amplitude: float = 1.0


@dataclass
class NeuralState:
    """Neural network state."""

    spikes: List[SpikeEvent]
    membrane_potentials: Dict[str, float]
    firing_rates: Dict[str, float]
    timestamp: float


class NeuromorphicController:
    """Neuromorphic controller for drone swarm."""

    def __init__(
        self, n_inputs: int = 6, n_hidden: int = 20, n_outputs: int = 3, seed: int = 42
    ):
        self.rng = np.random.default_rng(seed)
        self.n_inputs = n_inputs
        self.n_hidden = n_hidden
        self.n_outputs = n_outputs
        self.neurons: Dict[str, SpikingNeuron] = {}
        self.synapses: Dict[str, Synapse] = {}
        self.spike_history: List[SpikeEvent] = []
        self.time = 0.0
        self.dt = 0.1
        self._init_network()

    def _init_network(self) -> None:
        for i in range(self.n_inputs):
            nid = f"input_{i}"
            self.neurons[nid] = SpikingNeuron(nid, NeuronType.LIF)
        for i in range(self.n_hidden):
            nid = f"hidden_{i}"
            self.neurons[nid] = SpikingNeuron(nid, NeuronType.IZHIKEVICH)
        for i in range(self.n_outputs):
            nid = f"output_{i}"
            self.neurons[nid] = SpikingNeuron(nid, NeuronType.LIF)
        for i in range(self.n_inputs):
            for j in range(self.n_hidden):
                sid = f"syn_i{i}_h{j}"
                weight = self.rng.uniform(0.1, 0.5)
                self.synapses[sid] = Synapse(
                    sid, f"input_{i}", f"hidden_{j}", weight, SynapseType.EXCITATORY
                )
        for i in range(self.n_hidden):
            for j in range(self.n_outputs):
                sid = f"syn_h{i}_o{j}"
                weight = self.rng.uniform(0.1, 0.5)
                self.synapses[sid] = Synapse(
                    sid, f"hidden_{i}", f"output_{j}", weight, SynapseType.EXCITATORY
                )

    def _update_lif(self, neuron: SpikingNeuron, input_current: float) -> bool:
        if self.time - neuron.last_spike_time < neuron.refractory_period:
            return False
        dv = (
            (
                -neuron.leak_conductance
                * (neuron.membrane_potential - neuron.reset_potential)
                + input_current
            )
            / neuron.membrane_capacitance
            * self.dt
        )
        neuron.membrane_potential += dv - neuron.adaptation * self.dt
        if neuron.membrane_potential >= neuron.threshold:
            neuron.last_spike_time = self.time
            neuron.spike_count += 1
            neuron.membrane_potential = neuron.reset_potential
            neuron.adaptation += 0.1
            return True
        return False

    def _update_izhikevich(self, neuron: SpikingNeuron, input_current: float) -> bool:
        v = neuron.membrane_potential
        u = neuron.adaptation
        a, b, c, d = 0.02, 0.2, -65, 8
        dv = (0.04 * v * v + 5 * v + 140 - u + input_current) * self.dt
        du = a * (b * v - u) * self.dt
        neuron.membrane_potential += dv
        neuron.adaptation += du
        if neuron.membrane_potential >= 30:
            neuron.membrane_potential = c
            neuron.adaptation += d
            neuron.last_spike_time = self.time
            neuron.spike_count += 1
            return True
        return False

    def step(self, sensory_input: np.ndarray) -> np.ndarray:
        self.time += self.dt
        spikes = []
        for i in range(min(self.n_inputs, len(sensory_input))):
            nid = f"input_{i}"
            neuron = self.neurons[nid]
            fired = self._update_lif(neuron, sensory_input[i])
            if fired:
                spikes.append(SpikeEvent(nid, self.time))
                self.spike_history.append(SpikeEvent(nid, self.time))
        hidden_currents = np.zeros(self.n_hidden)
        for spike in spikes:
            for j in range(self.n_hidden):
                sid = f"syn_{spike.neuron_id.split('_')[0][0]}{spike.neuron_id.split('_')[1]}_h{j}"
                if sid in self.synapses:
                    hidden_currents[j] += self.synapses[sid].weight * spike.amplitude
        hidden_spikes = []
        for j in range(self.n_hidden):
            nid = f"hidden_{j}"
            neuron = self.neurons[nid]
            fired = self._update_izhikevich(neuron, hidden_currents[j])
            if fired:
                spikes.append(SpikeEvent(nid, self.time))
                hidden_spikes.append(SpikeEvent(nid, self.time))
                self.spike_history.append(SpikeEvent(nid, self.time))
        output_currents = np.zeros(self.n_outputs)
        for spike in hidden_spikes:
            for k in range(self.n_outputs):
                sid = f"syn_h{spike.neuron_id.split('_')[1]}_o{k}"
                if sid in self.synapses:
                    output_currents[k] += self.synapses[sid].weight * spike.amplitude
        output = np.zeros(self.n_outputs)
        for k in range(self.n_outputs):
            nid = f"output_{k}"
            neuron = self.neurons[nid]
            fired = self._update_lif(neuron, output_currents[k])
            if fired:
                output[k] = 1.0
                spikes.append(SpikeEvent(nid, self.time))
                self.spike_history.append(SpikeEvent(nid, self.time))
        return output

    def stdp_learning(
        self, pre_spike_time: float, post_spike_time: float, weight: float
    ) -> float:
        dt = post_spike_time - pre_spike_time
        if dt > 0:
            dw = 0.01 * np.exp(-dt / 20.0)
        else:
            dw = -0.012 * np.exp(dt / 20.0)
        return np.clip(weight + dw, 0, 1.0)

    def train_stdp(
        self, training_data: List[np.ndarray], n_epochs: int = 10
    ) -> List[float]:
        losses = []
        for epoch in range(n_epochs):
            total_spikes = 0
            for data in training_data:
                output = self.step(data)
                total_spikes += np.sum(output)
            loss = 1.0 / (1.0 + total_spikes)
            losses.append(loss)
            for syn in self.synapses.values():
                pre_neuron = self.neurons[syn.pre_neuron]
                post_neuron = self.neurons[syn.post_neuron]
                syn.weight = self.stdp_learning(
                    pre_neuron.last_spike_time, post_neuron.last_spike_time, syn.weight
                )
        return losses

    def get_firing_rates(self, window_ms: float = 100.0) -> Dict[str, float]:
        rates = {}
        for nid, neuron in self.neurons.items():
            recent_spikes = [
                s
                for s in self.spike_history
                if s.neuron_id == nid and s.timestamp > self.time - window_ms / 1000
            ]
            rates[nid] = len(recent_spikes) / (window_ms / 1000)
        return rates

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_neurons": len(self.neurons),
            "total_synapses": len(self.synapses),
            "total_spikes": len(self.spike_history),
            "time": self.time,
            "firing_rates": {
                k: v for k, v in list(self.get_firing_rates().items())[:5]
            },
        }


class SwarmNeuromorphicNetwork:
    """Neuromorphic network for swarm control."""

    def __init__(self, n_drones: int, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.controllers: Dict[str, NeuromorphicController] = {}
        self.drone_states: Dict[str, np.ndarray] = {}
        self._init_swarm(n_drones)

    def _init_swarm(self, n: int) -> None:
        for i in range(n):
            ctrl = NeuromorphicController(seed=self.rng.integers(10000))
            self.controllers[f"drone_{i}"] = ctrl
            self.drone_states[f"drone_{i}"] = self.rng.uniform(-1, 1, size=6)

    def step_all(self, sensory_data: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        outputs = {}
        for drone_id, ctrl in self.controllers.items():
            data = sensory_data.get(drone_id, self.drone_states[drone_id])
            output = ctrl.step(data)
            outputs[drone_id] = output
        return outputs

    def train_swarm(
        self, training_data: List[np.ndarray], n_epochs: int = 5
    ) -> Dict[str, List[float]]:
        results = {}
        for drone_id, ctrl in self.controllers.items():
            losses = ctrl.train_stdp(training_data, n_epochs)
            results[drone_id] = losses
        return results

    def get_swarm_stats(self) -> Dict[str, Any]:
        total_spikes = sum(len(c.spike_history) for c in self.controllers.values())
        return {
            "n_drones": len(self.controllers),
            "total_spikes": total_spikes,
            "avg_spikes_per_drone": total_spikes / len(self.controllers)
            if self.controllers
            else 0,
        }


if __name__ == "__main__":
    ctrl = NeuromorphicController(n_inputs=6, n_hidden=20, n_outputs=3, seed=42)
    for _ in range(100):
        sensory = np.random.uniform(0, 1, size=6)
        output = ctrl.step(sensory)
    print(f"Stats: {ctrl.get_stats()}")
    swarm = SwarmNeuromorphicNetwork(n_drones=5, seed=42)
    outputs = swarm.step_all({})
    print(f"Swarm stats: {swarm.get_swarm_stats()}")
