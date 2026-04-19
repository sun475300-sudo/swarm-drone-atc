"""Phase 675: Jetson Edge 디바이스 배포 시뮬레이션."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class EdgeDeviceConfig:
    device_type: str  # "jetson_nano", "jetson_xavier_nx", "jetson_orin"
    compute_capability: float = 5.3
    memory_mb: int = 4096
    power_budget_w: float = 10.0
    cuda_cores: int = 128


@dataclass
class ModelProfile:
    name: str
    size_mb: float
    inference_time_ms: float
    accuracy: float
    quantization: str = "fp32"  # fp32, fp16, int8


SUPPORTED_DEVICES: Dict[str, EdgeDeviceConfig] = {
    "jetson_nano": EdgeDeviceConfig(
        device_type="jetson_nano", compute_capability=5.3,
        memory_mb=4096, power_budget_w=10.0, cuda_cores=128,
    ),
    "jetson_xavier_nx": EdgeDeviceConfig(
        device_type="jetson_xavier_nx", compute_capability=7.2,
        memory_mb=8192, power_budget_w=15.0, cuda_cores=384,
    ),
    "jetson_orin": EdgeDeviceConfig(
        device_type="jetson_orin", compute_capability=8.7,
        memory_mb=16384, power_budget_w=40.0, cuda_cores=2048,
    ),
}


@dataclass
class _DeviceState:
    config: EdgeDeviceConfig
    deployed_models: Dict[str, ModelProfile] = field(default_factory=dict)
    utilization: float = 0.0
    temperature_c: float = 35.0
    memory_used_mb: float = 0.0
    inference_count: int = 0


class JetsonEdgeDeployer:
    """Simulated edge device deployment and inference pipeline."""

    def __init__(self, seed: int = 42) -> None:
        self.rng = np.random.default_rng(seed)
        self._next_id = 0
        self.devices: Dict[int, _DeviceState] = {}

    def register_device(self, config: Optional[EdgeDeviceConfig] = None) -> int:
        self._next_id += 1
        dev_id = self._next_id
        if config is None:
            config = SUPPORTED_DEVICES["jetson_nano"]
        self.devices[dev_id] = _DeviceState(config=config)
        return dev_id

    def optimize_model(
        self, model_name: str, target_device: str = "jetson_nano",
        quantization: str = "fp16",
    ) -> ModelProfile:
        """Simulate TensorRT model optimization."""
        base_size = self.rng.uniform(10.0, 200.0)
        base_latency = self.rng.uniform(5.0, 100.0)
        base_accuracy = self.rng.uniform(0.85, 0.98)

        size_mult = {"fp32": 1.0, "fp16": 0.5, "int8": 0.25}
        speed_mult = {"fp32": 1.0, "fp16": 0.6, "int8": 0.35}
        acc_penalty = {"fp32": 0.0, "fp16": 0.005, "int8": 0.02}

        device_speed = SUPPORTED_DEVICES.get(target_device, SUPPORTED_DEVICES["jetson_nano"])
        device_factor = 128.0 / max(device_speed.cuda_cores, 1)

        return ModelProfile(
            name=f"{model_name}_trt_{quantization}",
            size_mb=base_size * size_mult.get(quantization, 1.0),
            inference_time_ms=base_latency * speed_mult.get(quantization, 1.0) * device_factor,
            accuracy=max(0.0, base_accuracy - acc_penalty.get(quantization, 0.0)),
            quantization=quantization,
        )

    def deploy_model(self, device_id: int, model_profile: ModelProfile) -> bool:
        if device_id not in self.devices:
            return False
        dev = self.devices[device_id]
        if dev.memory_used_mb + model_profile.size_mb > dev.config.memory_mb:
            return False
        dev.deployed_models[model_profile.name] = model_profile
        dev.memory_used_mb += model_profile.size_mb
        return True

    def run_inference(
        self, device_id: int, input_data: Any, model_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        if device_id not in self.devices:
            return None
        dev = self.devices[device_id]
        if not dev.deployed_models:
            return None

        if model_name and model_name in dev.deployed_models:
            profile = dev.deployed_models[model_name]
        else:
            profile = next(iter(dev.deployed_models.values()))

        latency = profile.inference_time_ms * self.rng.uniform(0.9, 1.1)
        power = dev.config.power_budget_w * self.rng.uniform(0.6, 0.95)
        dev.utilization = min(1.0, dev.utilization + 0.1)
        dev.temperature_c += self.rng.uniform(0.1, 0.5)
        dev.inference_count += 1

        output_dim = 10
        output = self.rng.standard_normal(output_dim).tolist()

        return {
            "output": output,
            "latency_ms": latency,
            "power_w": power,
            "model": profile.name,
        }

    def get_device_stats(self, device_id: int) -> Optional[Dict[str, Any]]:
        if device_id not in self.devices:
            return None
        dev = self.devices[device_id]
        return {
            "device_type": dev.config.device_type,
            "utilization": dev.utilization,
            "temperature_c": dev.temperature_c,
            "memory_used_mb": dev.memory_used_mb,
            "memory_total_mb": dev.config.memory_mb,
            "deployed_models": len(dev.deployed_models),
            "inference_count": dev.inference_count,
        }

    def benchmark(self, device_id: int, iterations: int = 100) -> Optional[Dict[str, Any]]:
        if device_id not in self.devices:
            return None
        dev = self.devices[device_id]
        if not dev.deployed_models:
            return None

        profile = next(iter(dev.deployed_models.values()))
        latencies = self.rng.uniform(
            profile.inference_time_ms * 0.8,
            profile.inference_time_ms * 1.3,
            size=iterations,
        )
        fps = 1000.0 / np.mean(latencies)
        power_avg = dev.config.power_budget_w * 0.75

        return {
            "fps": fps,
            "latency_p50_ms": float(np.percentile(latencies, 50)),
            "latency_p99_ms": float(np.percentile(latencies, 99)),
            "power_avg_w": power_avg,
            "power_efficiency_fps_per_w": fps / max(power_avg, 0.01),
            "iterations": iterations,
        }
