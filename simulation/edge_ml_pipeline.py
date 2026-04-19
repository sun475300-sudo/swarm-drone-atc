"""
Phase 511: Edge ML Pipeline
엣지 디바이스 ML 추론, 모델 경량화, 온디바이스 학습.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple


class ModelFormat(Enum):
    FLOAT32 = "float32"
    FLOAT16 = "float16"
    INT8 = "int8"
    INT4 = "int4"
    BINARY = "binary"


class InferenceMode(Enum):
    BATCH = "batch"
    STREAMING = "streaming"
    ON_DEMAND = "on_demand"


@dataclass
class EdgeModel:
    model_id: str
    name: str
    input_dim: int
    output_dim: int
    format: ModelFormat
    weights: np.ndarray
    bias: np.ndarray
    latency_ms: float = 0.0
    accuracy: float = 0.0


@dataclass
class InferenceResult:
    model_id: str
    input_hash: str
    output: np.ndarray
    latency_ms: float
    confidence: float


class ModelQuantizer:
    """Model quantization for edge deployment."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def quantize(self, model: EdgeModel, target: ModelFormat) -> EdgeModel:
        scale_map = {
            ModelFormat.FLOAT16: 0.99,
            ModelFormat.INT8: 0.95,
            ModelFormat.INT4: 0.88,
            ModelFormat.BINARY: 0.75,
        }
        acc_scale = scale_map.get(target, 1.0)
        speed_map = {
            ModelFormat.FLOAT16: 0.7,
            ModelFormat.INT8: 0.4,
            ModelFormat.INT4: 0.25,
            ModelFormat.BINARY: 0.15,
        }
        speed_scale = speed_map.get(target, 1.0)

        new_weights = model.weights.copy()
        if target == ModelFormat.INT8:
            new_weights = np.round(new_weights * 127) / 127
        elif target == ModelFormat.INT4:
            new_weights = np.round(new_weights * 7) / 7
        elif target == ModelFormat.BINARY:
            new_weights = np.sign(new_weights)

        return EdgeModel(
            f"{model.model_id}_q{target.value}", model.name,
            model.input_dim, model.output_dim, target,
            new_weights, model.bias.copy(),
            round(model.latency_ms * speed_scale, 2),
            round(model.accuracy * acc_scale, 4))


class EdgeInferenceEngine:
    """Lightweight inference engine for drone edge computing."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.models: Dict[str, EdgeModel] = {}
        self.results: List[InferenceResult] = []

    def load_model(self, model: EdgeModel):
        self.models[model.model_id] = model

    def infer(self, model_id: str, input_data: np.ndarray) -> Optional[InferenceResult]:
        model = self.models.get(model_id)
        if model is None:
            return None

        output = input_data @ model.weights[:input_data.shape[-1], :model.output_dim]
        output = output + model.bias[:model.output_dim]
        output = 1 / (1 + np.exp(-output))  # sigmoid

        latency = model.latency_ms + self.rng.uniform(0, 0.5)
        confidence = float(np.max(output))
        inp_hash = str(hash(input_data.tobytes()))[:12]

        result = InferenceResult(model_id, inp_hash, output, round(latency, 2), round(confidence, 4))
        self.results.append(result)
        return result


class OnDeviceLearner:
    """Federated on-device learning with gradient compression."""

    def __init__(self, n_devices: int = 10, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_devices = n_devices
        self.global_weights: Optional[np.ndarray] = None
        self.rounds: List[Dict] = []

    def init_global(self, dim: Tuple[int, int]):
        self.global_weights = self.rng.standard_normal(dim) * 0.1

    def local_update(self, device_id: int, data: np.ndarray, labels: np.ndarray,
                     lr: float = 0.01, steps: int = 5) -> np.ndarray:
        if self.global_weights is None:
            return np.array([])
        w = self.global_weights.copy()
        for _ in range(steps):
            pred = data @ w
            error = pred - labels
            grad = data.T @ error / len(data)
            w -= lr * grad
        return w - self.global_weights

    def aggregate(self, gradients: List[np.ndarray]) -> np.ndarray:
        if not gradients or self.global_weights is None:
            return np.array([])
        avg_grad = np.mean(gradients, axis=0)
        self.global_weights += avg_grad
        return self.global_weights

    def federated_round(self) -> Dict:
        if self.global_weights is None:
            self.init_global((10, 3))
        grads = []
        for i in range(self.n_devices):
            data = self.rng.standard_normal((20, self.global_weights.shape[0]))
            labels = self.rng.standard_normal((20, self.global_weights.shape[1]))
            g = self.local_update(i, data, labels)
            grads.append(g)
        self.aggregate(grads)
        result = {"round": len(self.rounds) + 1, "devices": self.n_devices,
                  "weight_norm": round(float(np.linalg.norm(self.global_weights)), 4)}
        self.rounds.append(result)
        return result


class EdgeMLPipeline:
    """End-to-end edge ML pipeline for drone swarms."""

    def __init__(self, n_drones: int = 10, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.quantizer = ModelQuantizer(seed)
        self.engine = EdgeInferenceEngine(seed)
        self.learner = OnDeviceLearner(n_drones, seed)

        for i in range(3):
            dim_in, dim_out = 10 + i * 5, 3 + i
            w = self.rng.standard_normal((dim_in, dim_out)) * 0.1
            b = self.rng.standard_normal(dim_out) * 0.01
            model = EdgeModel(f"model_{i}", f"detector_{i}",
                             dim_in, dim_out, ModelFormat.FLOAT32,
                             w, b, self.rng.uniform(1, 10), self.rng.uniform(0.85, 0.98))
            self.engine.load_model(model)
            q_model = self.quantizer.quantize(model, ModelFormat.INT8)
            self.engine.load_model(q_model)

    def run_inference_batch(self, n_samples: int = 50) -> Dict:
        results = []
        for mid, model in self.engine.models.items():
            data = self.rng.standard_normal((n_samples, model.input_dim))
            for row in data:
                r = self.engine.infer(mid, row.reshape(1, -1))
                if r:
                    results.append(r)
        avg_lat = np.mean([r.latency_ms for r in results]) if results else 0
        return {"inferences": len(results), "avg_latency_ms": round(avg_lat, 2)}

    def summary(self) -> Dict:
        return {
            "drones": self.n_drones,
            "models_loaded": len(self.engine.models),
            "total_inferences": len(self.engine.results),
            "federated_rounds": len(self.learner.rounds),
        }
