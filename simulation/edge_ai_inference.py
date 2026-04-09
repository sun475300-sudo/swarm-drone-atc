"""Phase 314: Edge AI Inference Engine — 에지 AI 추론 엔진.

모델 양자화, 경량 추론, 배치 스케줄링,
온디바이스 이상 탐지, 모델 캐싱.
"""

from __future__ import annotations
import numpy as np
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable


class ModelFormat(Enum):
    FLOAT32 = "float32"
    FLOAT16 = "float16"
    INT8 = "int8"
    INT4 = "int4"


class InferenceStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    CACHED = "cached"
    ERROR = "error"


@dataclass
class EdgeModel:
    model_id: str
    name: str
    input_shape: tuple
    output_shape: tuple
    format: ModelFormat = ModelFormat.FLOAT32
    size_mb: float = 10.0
    latency_ms: float = 5.0
    accuracy: float = 0.95
    weights: Optional[np.ndarray] = None  # simplified weight matrix

    def quantize(self, target: ModelFormat) -> 'EdgeModel':
        """Simulate model quantization."""
        scale = {"float32": 1.0, "float16": 0.5, "int8": 0.25, "int4": 0.125}
        acc_loss = {"float32": 0, "float16": 0.001, "int8": 0.01, "int4": 0.03}
        s = scale.get(target.value, 1.0)
        return EdgeModel(
            model_id=f"{self.model_id}_{target.value}",
            name=f"{self.name} ({target.value})",
            input_shape=self.input_shape,
            output_shape=self.output_shape,
            format=target,
            size_mb=self.size_mb * s,
            latency_ms=self.latency_ms * s,
            accuracy=self.accuracy - acc_loss.get(target.value, 0),
            weights=self.weights,
        )


@dataclass
class InferenceResult:
    model_id: str
    output: np.ndarray
    latency_ms: float
    confidence: float
    cached: bool = False
    timestamp: float = 0.0


class EdgeAIInferenceEngine:
    """에지 AI 추론 엔진.

    - 모델 양자화 (FP32→FP16→INT8→INT4)
    - 경량 추론 파이프라인
    - 결과 캐싱 (LRU)
    - 배치 추론
    - 이상 탐지 모드
    """

    def __init__(self, cache_size: int = 100, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self._models: Dict[str, EdgeModel] = {}
        self._cache: Dict[str, InferenceResult] = {}
        self._cache_size = cache_size
        self._inference_count = 0
        self._cache_hits = 0
        self._total_latency_ms = 0.0

    def load_model(self, model: EdgeModel):
        if model.weights is None:
            model.weights = self._rng.standard_normal(
                (model.input_shape[-1] if len(model.input_shape) > 0 else 10,
                 model.output_shape[-1] if len(model.output_shape) > 0 else 5)
            ).astype(np.float32)
        self._models[model.model_id] = model

    def quantize_model(self, model_id: str, target: ModelFormat) -> Optional[EdgeModel]:
        model = self._models.get(model_id)
        if not model:
            return None
        quantized = model.quantize(target)
        self._models[quantized.model_id] = quantized
        return quantized

    def infer(self, model_id: str, input_data: np.ndarray) -> Optional[InferenceResult]:
        model = self._models.get(model_id)
        if not model:
            return None

        # Check cache
        cache_key = f"{model_id}:{hash(input_data.tobytes())}"
        if cache_key in self._cache:
            self._cache_hits += 1
            cached = self._cache[cache_key]
            return InferenceResult(
                model_id=model_id, output=cached.output,
                latency_ms=0.1, confidence=cached.confidence,
                cached=True, timestamp=time.time(),
            )

        # Simulate inference
        start = time.perf_counter()
        if model.weights is not None:
            # Simple matrix multiply
            flat = input_data.flatten()
            if len(flat) < model.weights.shape[0]:
                flat = np.pad(flat, (0, model.weights.shape[0] - len(flat)))
            elif len(flat) > model.weights.shape[0]:
                flat = flat[:model.weights.shape[0]]
            output = flat @ model.weights
            # Softmax
            exp_out = np.exp(output - np.max(output))
            output = exp_out / np.sum(exp_out)
        else:
            output = self._rng.random(model.output_shape)

        elapsed = (time.perf_counter() - start) * 1000
        # Add simulated device latency
        total_latency = elapsed + model.latency_ms * (0.8 + self._rng.random() * 0.4)
        confidence = float(np.max(output)) * model.accuracy

        result = InferenceResult(
            model_id=model_id, output=output,
            latency_ms=round(total_latency, 3),
            confidence=round(confidence, 4),
            timestamp=time.time(),
        )

        # Update cache (simple LRU)
        if len(self._cache) >= self._cache_size:
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[cache_key] = result

        self._inference_count += 1
        self._total_latency_ms += total_latency
        return result

    def batch_infer(self, model_id: str, batch: List[np.ndarray]) -> List[Optional[InferenceResult]]:
        return [self.infer(model_id, inp) for inp in batch]

    def detect_anomaly(self, model_id: str, input_data: np.ndarray,
                       threshold: float = 0.5) -> Tuple[bool, float]:
        """Run anomaly detection using model output confidence."""
        result = self.infer(model_id, input_data)
        if not result:
            return True, 0.0
        is_anomaly = result.confidence < threshold
        return is_anomaly, result.confidence

    def get_model(self, model_id: str) -> Optional[EdgeModel]:
        return self._models.get(model_id)

    def summary(self) -> dict:
        return {
            "loaded_models": len(self._models),
            "inference_count": self._inference_count,
            "cache_size": len(self._cache),
            "cache_hits": self._cache_hits,
            "cache_hit_rate": round(
                self._cache_hits / max(self._inference_count, 1) * 100, 1),
            "avg_latency_ms": round(
                self._total_latency_ms / max(self._inference_count, 1), 3),
        }
