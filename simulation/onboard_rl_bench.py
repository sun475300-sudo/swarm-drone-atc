"""Phase 361: 온보드 RL 추론 벤치마크 -- 분석적 FLOP 기반 추정.

SDACS PPO 충돌 회피 정책을 엣지 디바이스에 배포할 때
추론 지연시간, 처리량, 메모리, 전력 소모를 **분석적으로** 추정한다.

**주의**: 이 모듈의 추정치는 실측이 아닌 FLOP/TFLOPS 비율 기반
해석적 모델이다. 실제 하드웨어 벤치마크와 차이가 있을 수 있다.

실행:
    python -m simulation.onboard_rl_bench --bench
    python -m simulation.onboard_rl_bench --device jetson_orin
    python -m simulation.onboard_rl_bench --recommend
    python -m simulation.onboard_rl_bench --json
"""
from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

DEVICE_CATEGORIES: tuple[str, ...] = ("EDGE", "WORKSTATION", "CLOUD")
MODEL_FORMATS: tuple[str, ...] = ("ONNX", "PYTORCH", "TFLITE")

# 10 Hz 제어 루프 -- 100 ms 이내 추론 완료 필수
REALTIME_THRESHOLD_MS: float = 100.0

# PPO 정책 네트워크 기본 사양 (ppo_collision.py 기준)
# obs_dim = FEATURES_PER_ENTITY * (max_neighbors + 1) = 7 * 9 = 63
# action_dim = 3 (ax, ay, az)
PPO_INPUT_DIM: int = 63
PPO_OUTPUT_DIM: int = 3
PPO_HIDDEN_LAYERS: tuple[int, ...] = (64, 64)

# 추론 오버헤드 계수 (메모리 접근, 커널 론치, 프레임워크 부하)
OVERHEAD_FACTOR: float = 2.5

# 활성화 버퍼 배수 (가장 큰 은닉층 크기의 배수)
ACTIVATION_BUFFER_FACTOR: int = 4

# float32 바이트 크기
SIZEOF_FLOAT32: int = 4

# ---------------------------------------------------------------------------
# 데이터 클래스
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeviceSpec:
    """엣지/워크스테이션/클라우드 디바이스 사양."""

    name: str
    compute_capability_tflops: float
    memory_gb: float
    power_watts: float
    category: str

    def __post_init__(self) -> None:
        if self.category not in DEVICE_CATEGORIES:
            raise ValueError(
                f"category must be one of {DEVICE_CATEGORIES}, "
                f"got {self.category!r}"
            )
        if self.compute_capability_tflops < 0:
            raise ValueError("compute_capability_tflops must be >= 0")
        if self.memory_gb <= 0:
            raise ValueError("memory_gb must be > 0")
        if self.power_watts <= 0:
            raise ValueError("power_watts must be > 0")


@dataclass(frozen=True)
class ModelSpec:
    """RL 정책 네트워크 사양."""

    name: str
    input_dim: int
    output_dim: int
    hidden_layers: tuple[int, ...]
    total_params: int
    format: str

    def __post_init__(self) -> None:
        if self.format not in MODEL_FORMATS:
            raise ValueError(
                f"format must be one of {MODEL_FORMATS}, "
                f"got {self.format!r}"
            )
        if self.input_dim <= 0:
            raise ValueError("input_dim must be > 0")
        if self.output_dim <= 0:
            raise ValueError("output_dim must be > 0")
        if self.total_params <= 0:
            raise ValueError("total_params must be > 0")


@dataclass(frozen=True)
class InferenceBenchmark:
    """단일 디바이스-모델 추론 벤치마크 결과."""

    device: DeviceSpec
    model: ModelSpec
    latency_ms: float
    throughput_hz: float
    memory_usage_mb: float
    power_per_inference_mw: float
    meets_realtime: bool


@dataclass(frozen=True)
class BenchReport:
    """전체 벤치마크 보고서."""

    benchmarks: tuple[InferenceBenchmark, ...]
    realtime_capable: tuple[InferenceBenchmark, ...]
    recommendations: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.benchmarks, tuple):
            object.__setattr__(self, "benchmarks", tuple(self.benchmarks))
        if not isinstance(self.realtime_capable, tuple):
            object.__setattr__(
                self, "realtime_capable", tuple(self.realtime_capable),
            )
        if not isinstance(self.recommendations, tuple):
            object.__setattr__(
                self, "recommendations", tuple(self.recommendations),
            )


# ---------------------------------------------------------------------------
# 디바이스 카탈로그
# ---------------------------------------------------------------------------

DEVICE_CATALOG: tuple[DeviceSpec, ...] = (
    DeviceSpec(
        name="jetson_nano",
        compute_capability_tflops=0.472,
        memory_gb=4.0,
        power_watts=10.0,
        category="EDGE",
    ),
    DeviceSpec(
        name="jetson_xavier",
        compute_capability_tflops=11.0,
        memory_gb=32.0,
        power_watts=30.0,
        category="EDGE",
    ),
    DeviceSpec(
        name="jetson_orin",
        compute_capability_tflops=275.0,
        memory_gb=64.0,
        power_watts=60.0,
        category="EDGE",
    ),
    DeviceSpec(
        name="rpi5",
        compute_capability_tflops=0.032,
        memory_gb=8.0,
        power_watts=12.0,
        category="EDGE",
    ),
    DeviceSpec(
        name="x86_workstation",
        compute_capability_tflops=40.0,
        memory_gb=64.0,
        power_watts=350.0,
        category="WORKSTATION",
    ),
)

# 로드 타임 유일성 게이트
_DEVICE_NAMES = [d.name for d in DEVICE_CATALOG]
if len(_DEVICE_NAMES) != len(set(_DEVICE_NAMES)):
    raise RuntimeError("duplicate device name in DEVICE_CATALOG")

# 이름 -> DeviceSpec 불변 매핑
DEVICE_MAP: Mapping[str, DeviceSpec] = MappingProxyType(
    {d.name: d for d in DEVICE_CATALOG}
)

# ---------------------------------------------------------------------------
# ONNX 내보내기 사양
# ---------------------------------------------------------------------------

ONNX_EXPORT_SPEC: Mapping[str, object] = MappingProxyType({
    "opset_version": 17,
    "input_name": "observation",
    "input_shape": (1, PPO_INPUT_DIM),
    "input_dtype": "float32",
    "output_name": "action",
    "output_shape": (1, PPO_OUTPUT_DIM),
    "output_dtype": "float32",
    "description": (
        "SDACS PPO collision avoidance policy. "
        "Input: [batch, 63] observation "
        "(self + 8 neighbors * 7 features). "
        "Output: [batch, 3] continuous action "
        "(ax, ay, az in [-1, 1])."
    ),
})

# ---------------------------------------------------------------------------
# 모델 사양 유틸리티
# ---------------------------------------------------------------------------


def compute_total_params(
    input_dim: int,
    output_dim: int,
    hidden_layers: tuple[int, ...],
) -> int:
    """전결합 MLP의 총 파라미터 수 계산 (가중치 + 편향)."""
    if not hidden_layers:
        return input_dim * output_dim + output_dim
    total = 0
    prev = input_dim
    for h in hidden_layers:
        total += prev * h + h  # weight + bias
        prev = h
    total += prev * output_dim + output_dim
    return total


def compute_flops(
    input_dim: int,
    output_dim: int,
    hidden_layers: tuple[int, ...],
) -> int:
    """전결합 MLP 순전파 FLOPs 추정 (MAC * 2)."""
    if not hidden_layers:
        return 2 * input_dim * output_dim
    total = 0
    prev = input_dim
    for h in hidden_layers:
        total += 2 * prev * h
        prev = h
    total += 2 * prev * output_dim
    return total


def make_ppo_model_spec(fmt: str = "ONNX") -> ModelSpec:
    """SDACS PPO 정책 네트워크의 ModelSpec을 생성한다."""
    return ModelSpec(
        name="sdacs_ppo_collision",
        input_dim=PPO_INPUT_DIM,
        output_dim=PPO_OUTPUT_DIM,
        hidden_layers=PPO_HIDDEN_LAYERS,
        total_params=compute_total_params(
            PPO_INPUT_DIM, PPO_OUTPUT_DIM, PPO_HIDDEN_LAYERS,
        ),
        format=fmt,
    )


# ---------------------------------------------------------------------------
# 추론 추정
# ---------------------------------------------------------------------------


def estimate_inference(
    device: DeviceSpec,
    model: ModelSpec,
) -> InferenceBenchmark:
    """분석적 FLOP 기반 추론 지연시간/처리량/메모리/전력 추정.

    **주의**: 해석적 모델이며 실측값이 아님.
    """
    flops = compute_flops(
        model.input_dim, model.output_dim, model.hidden_layers,
    )
    device_flops = device.compute_capability_tflops * 1e12

    # 지연시간 (ms) = FLOPs / (device FLOPS) * 오버헤드 * 1000
    latency_ms = (flops / device_flops) * OVERHEAD_FACTOR * 1000.0

    # 처리량 (Hz) = 1000 / latency_ms
    throughput_hz = 1000.0 / latency_ms if latency_ms > 0 else float("inf")

    # 메모리 (MB) = 파라미터 * sizeof(float32) + 활성화 버퍼
    max_hidden = (
        max(model.hidden_layers) if model.hidden_layers else model.output_dim
    )
    param_mb = (model.total_params * SIZEOF_FLOAT32) / (1024 * 1024)
    activation_mb = (
        max_hidden * ACTIVATION_BUFFER_FACTOR * SIZEOF_FLOAT32
    ) / (1024 * 1024)
    memory_usage_mb = param_mb + activation_mb

    # 전력 (mW/inference) = 디바이스 전력 * latency_s * 1000
    latency_s = latency_ms / 1000.0
    power_per_inference_mw = device.power_watts * latency_s * 1000.0

    meets_realtime = latency_ms < REALTIME_THRESHOLD_MS

    return InferenceBenchmark(
        device=device,
        model=model,
        latency_ms=latency_ms,
        throughput_hz=throughput_hz,
        memory_usage_mb=memory_usage_mb,
        power_per_inference_mw=power_per_inference_mw,
        meets_realtime=meets_realtime,
    )


# ---------------------------------------------------------------------------
# 일괄 벤치마크 & 추천
# ---------------------------------------------------------------------------


def benchmark_all(model: ModelSpec) -> BenchReport:
    """모든 카탈로그 디바이스에 대해 추론 벤치마크를 실행한다."""
    benchmarks = tuple(
        estimate_inference(dev, model) for dev in DEVICE_CATALOG
    )
    sorted_benchmarks = tuple(
        sorted(benchmarks, key=lambda b: b.latency_ms),
    )
    realtime = tuple(b for b in sorted_benchmarks if b.meets_realtime)
    recommendations = recommend_deployment(model)
    return BenchReport(
        benchmarks=sorted_benchmarks,
        realtime_capable=realtime,
        recommendations=recommendations,
    )


def recommend_deployment(model: ModelSpec) -> tuple[str, ...]:
    """실시간 요건 충족 + 최소 전력 순으로 배포 추천 디바이스를 반환."""
    candidates: list[InferenceBenchmark] = []
    for dev in DEVICE_CATALOG:
        bench = estimate_inference(dev, model)
        if bench.meets_realtime:
            candidates.append(bench)
    # 전력 효율 순 정렬 (mW/inference 오름차순)
    candidates.sort(key=lambda b: b.power_per_inference_mw)
    return tuple(
        f"{b.device.name}: {b.latency_ms:.4f}ms, "
        f"{b.power_per_inference_mw:.4f}mW/inf"
        for b in candidates
    )


# ---------------------------------------------------------------------------
# 벤치마크 행렬 (MappingProxyType 출력)
# ---------------------------------------------------------------------------


def bench_matrix(model: ModelSpec) -> tuple[Mapping[str, object], ...]:
    """도구 연동용 불변 딕셔너리 튜플로 벤치마크 결과를 반환."""
    report = benchmark_all(model)
    return tuple(
        MappingProxyType({
            "device": b.device.name,
            "category": b.device.category,
            "latency_ms": round(b.latency_ms, 6),
            "throughput_hz": round(b.throughput_hz, 2),
            "memory_usage_mb": round(b.memory_usage_mb, 6),
            "power_per_inference_mw": round(b.power_per_inference_mw, 6),
            "meets_realtime": b.meets_realtime,
        })
        for b in report.benchmarks
    )


# ---------------------------------------------------------------------------
# 포매팅
# ---------------------------------------------------------------------------


def _format_bench_table(model: ModelSpec) -> str:
    """사람이 읽을 수 있는 벤치마크 테이블 문자열."""
    report = benchmark_all(model)
    lines = [
        "=== Onboard RL Inference Benchmark "
        "(Analytical FLOP-based) ===",
        f"Model: {model.name} | Params: {model.total_params:,} | "
        f"Format: {model.format}",
        f"Hidden: {model.hidden_layers} | "
        f"Input: {model.input_dim} | Output: {model.output_dim}",
        "",
        f"{'Device':<20} {'Category':<13} {'Latency(ms)':>12} "
        f"{'Throughput(Hz)':>15} {'Mem(MB)':>10} {'Power(mW)':>12} "
        f"{'Realtime':>8}",
        "-" * 95,
    ]
    for b in report.benchmarks:
        rt = "YES" if b.meets_realtime else "NO"
        lines.append(
            f"{b.device.name:<20} {b.device.category:<13} "
            f"{b.latency_ms:>12.6f} {b.throughput_hz:>15.2f} "
            f"{b.memory_usage_mb:>10.6f} "
            f"{b.power_per_inference_mw:>12.6f} {rt:>8}"
        )
    lines.append("")
    lines.append(
        "NOTE: Estimates are analytical (FLOP-based), not measured."
    )
    return "\n".join(lines)


def _format_recommendations(model: ModelSpec) -> str:
    """추천 디바이스 목록 문자열."""
    recs = recommend_deployment(model)
    if not recs:
        return "No devices meet the realtime threshold (<100ms)."
    lines = [
        "=== Deployment Recommendations (realtime + min power) ===",
    ]
    for i, r in enumerate(recs, 1):
        lines.append(f"  {i}. {r}")
    lines.append("")
    lines.append(
        "NOTE: Estimates are analytical (FLOP-based), not measured."
    )
    return "\n".join(lines)


def _format_json(model: ModelSpec) -> str:
    """JSON 형식 벤치마크 결과."""
    matrix = bench_matrix(model)
    return json.dumps(
        [dict(m) for m in matrix],
        indent=2,
        ensure_ascii=False,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI 진입점."""
    parser = argparse.ArgumentParser(
        description=(
            "Onboard RL inference benchmark "
            "(analytical FLOP-based)"
        ),
    )
    parser.add_argument(
        "--bench", action="store_true",
        help="Run benchmark across all devices",
    )
    parser.add_argument(
        "--device", type=str, default=None,
        help="Benchmark a specific device by name",
    )
    parser.add_argument(
        "--recommend", action="store_true",
        help="Show deployment recommendations",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results in JSON format",
    )
    args = parser.parse_args(argv)
    model = make_ppo_model_spec()

    if args.json:
        print(_format_json(model))
    elif args.device:
        dev = DEVICE_MAP.get(args.device)
        if dev is None:
            print(f"Unknown device: {args.device!r}")
            print(f"Available: {', '.join(_DEVICE_NAMES)}")
            return 1
        bench = estimate_inference(dev, model)
        rt = "YES" if bench.meets_realtime else "NO"
        print(f"Device:    {bench.device.name}")
        print(f"Latency:   {bench.latency_ms:.6f} ms")
        print(f"Throughput:{bench.throughput_hz:.2f} Hz")
        print(f"Memory:    {bench.memory_usage_mb:.6f} MB")
        print(f"Power:     {bench.power_per_inference_mw:.6f} mW/inf")
        print(f"Realtime:  {rt}")
        print("\nNOTE: Analytical estimate, not measured.")
    elif args.recommend:
        print(_format_recommendations(model))
    elif args.bench:
        print(_format_bench_table(model))
    else:
        print(_format_bench_table(model))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
