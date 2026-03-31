# Phase 563: SNN Neuromorphic Controller — Spiking Neural Network
"""
스파이킹 신경망 제어기: LIF 뉴런 모델,
STDP 학습, 이벤트 기반 드론 제어.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class LIFNeuron:
    neuron_id: int
    v_mem: float = 0.0        # 막전위
    v_rest: float = -65.0     # mV
    v_thresh: float = -55.0
    v_reset: float = -70.0
    tau_m: float = 10.0       # ms
    spike_count: int = 0
    last_spike: float = -1.0


@dataclass
class Synapse:
    pre: int
    post: int
    weight: float
    delay: float = 1.0


class LIFNetwork:
    """LIF 뉴런 네트워크."""

    def __init__(self, n_neurons: int, seed=42):
        self.rng = np.random.default_rng(seed)
        self.neurons = [
            LIFNeuron(i, v_mem=-65.0 + self.rng.normal(0, 2))
            for i in range(n_neurons)
        ]
        self.synapses: list[Synapse] = []
        self.n = n_neurons
        self.time = 0.0

    def connect_random(self, p=0.3, w_range=(0.5, 2.0)):
        for i in range(self.n):
            for j in range(self.n):
                if i != j and self.rng.random() < p:
                    w = float(self.rng.uniform(*w_range))
                    self.synapses.append(Synapse(i, j, w))

    def step(self, dt=0.5, input_current: np.ndarray = None):
        self.time += dt
        spikes = []
        if input_current is None:
            input_current = np.zeros(self.n)

        # 시냅스 입력 계산
        syn_input = np.zeros(self.n)
        for s in self.synapses:
            pre = self.neurons[s.pre]
            if pre.last_spike >= 0 and (self.time - pre.last_spike) < 2 * dt:
                syn_input[s.post] += s.weight

        for i, n in enumerate(self.neurons):
            dv = (-n.v_mem + n.v_rest + input_current[i] + syn_input[i]) / n.tau_m * dt
            n.v_mem += dv

            if n.v_mem >= n.v_thresh:
                spikes.append(i)
                n.spike_count += 1
                n.last_spike = self.time
                n.v_mem = n.v_reset

        return spikes

    def stdp_update(self, spikes: list[int], lr=0.01, tau_stdp=20.0):
        for s in self.synapses:
            pre = self.neurons[s.pre]
            post = self.neurons[s.post]
            if pre.last_spike > 0 and post.last_spike > 0:
                dt_sp = post.last_spike - pre.last_spike
                if dt_sp > 0:
                    s.weight += lr * np.exp(-dt_sp / tau_stdp)
                elif dt_sp < 0:
                    s.weight -= lr * 0.5 * np.exp(dt_sp / tau_stdp)
                s.weight = float(np.clip(s.weight, 0.0, 5.0))


class SNNNeuromorphic:
    """SNN 기반 뉴로모픽 제어 시뮬레이션."""

    def __init__(self, n_neurons=32, seed=42):
        self.rng = np.random.default_rng(seed)
        self.network = LIFNetwork(n_neurons, seed)
        self.network.connect_random(0.2)
        self.n_neurons = n_neurons
        self.total_spikes = 0
        self.steps_run = 0
        self.spike_history: list[list[int]] = []

    def step(self, external_input: np.ndarray = None):
        if external_input is None:
            external_input = self.rng.normal(0, 3, self.n_neurons)
        spikes = self.network.step(0.5, external_input)
        self.network.stdp_update(spikes)
        self.total_spikes += len(spikes)
        self.steps_run += 1
        self.spike_history.append(spikes)
        return spikes

    def run(self, steps=200):
        for _ in range(steps):
            self.step()

    def firing_rate(self) -> float:
        if self.steps_run == 0:
            return 0.0
        return self.total_spikes / (self.n_neurons * self.steps_run)

    def summary(self):
        weights = [s.weight for s in self.network.synapses]
        return {
            "neurons": self.n_neurons,
            "synapses": len(self.network.synapses),
            "steps": self.steps_run,
            "total_spikes": self.total_spikes,
            "firing_rate": round(self.firing_rate(), 4),
            "avg_weight": round(float(np.mean(weights)) if weights else 0, 4),
            "sim_time_ms": round(self.network.time, 1),
        }


if __name__ == "__main__":
    snn = SNNNeuromorphic(32, 42)
    snn.run(200)
    for k, v in snn.summary().items():
        print(f"  {k}: {v}")
