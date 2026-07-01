"""Phase 361: 온보드 RL 추론 벤치마크 테스트."""
from __future__ import annotations

import json

import pytest

from simulation.onboard_rl_bench import (
    DEVICE_CATALOG,
    DEVICE_CATEGORIES,
    DEVICE_MAP,
    ONNX_EXPORT_SPEC,
    PPO_HIDDEN_LAYERS,
    PPO_INPUT_DIM,
    PPO_OUTPUT_DIM,
    REALTIME_THRESHOLD_MS,
    DeviceSpec,
    ModelSpec,
    bench_matrix,
    benchmark_all,
    compute_flops,
    compute_total_params,
    estimate_inference,
    main,
    make_ppo_model_spec,
    recommend_deployment,
)

# ---------------------------------------------------------------------------
# 테스트 헬퍼
# ---------------------------------------------------------------------------


def _device(**kw: object) -> DeviceSpec:
    defaults = dict(
        name="test_device",
        compute_capability_tflops=1.0,
        memory_gb=8.0,
        power_watts=10.0,
        category="EDGE",
    )
    defaults.update(kw)
    return DeviceSpec(**defaults)


def _model(**kw: object) -> ModelSpec:
    defaults = dict(
        name="test_model",
        input_dim=10,
        output_dim=3,
        hidden_layers=(32, 32),
        total_params=compute_total_params(10, 3, (32, 32)),
        format="ONNX",
    )
    defaults.update(kw)
    return ModelSpec(**defaults)


# ---------------------------------------------------------------------------
# DeviceSpec 검증 (5 tests)
# ---------------------------------------------------------------------------


class TestDeviceSpec:
    def test_valid_device(self) -> None:
        dev = _device()
        assert dev.name == "test_device"
        assert dev.category == "EDGE"

    def test_invalid_category_rejected(self) -> None:
        with pytest.raises(ValueError, match="category must be one of"):
            _device(category="INVALID")

    def test_negative_tflops_rejected(self) -> None:
        with pytest.raises(ValueError, match="compute_capability_tflops"):
            _device(compute_capability_tflops=-1.0)

    def test_zero_memory_rejected(self) -> None:
        with pytest.raises(ValueError, match="memory_gb must be > 0"):
            _device(memory_gb=0.0)

    def test_zero_power_rejected(self) -> None:
        with pytest.raises(ValueError, match="power_watts must be > 0"):
            _device(power_watts=0.0)


# ---------------------------------------------------------------------------
# ModelSpec 검증 (4 tests)
# ---------------------------------------------------------------------------


class TestModelSpec:
    def test_valid_model(self) -> None:
        m = _model()
        assert m.input_dim == 10
        assert m.format == "ONNX"

    def test_invalid_format_rejected(self) -> None:
        with pytest.raises(ValueError, match="format must be one of"):
            _model(format="CAFFE")

    def test_zero_input_dim_rejected(self) -> None:
        with pytest.raises(ValueError, match="input_dim must be > 0"):
            _model(input_dim=0)

    def test_zero_params_rejected(self) -> None:
        with pytest.raises(ValueError, match="total_params must be > 0"):
            _model(total_params=0)


# ---------------------------------------------------------------------------
# 디바이스 카탈로그 (5 tests)
# ---------------------------------------------------------------------------


class TestDeviceCatalog:
    def test_catalog_not_empty(self) -> None:
        assert len(DEVICE_CATALOG) >= 5

    def test_catalog_unique_names(self) -> None:
        names = [d.name for d in DEVICE_CATALOG]
        assert len(names) == len(set(names))

    def test_all_categories_valid(self) -> None:
        for d in DEVICE_CATALOG:
            assert d.category in DEVICE_CATEGORIES

    def test_expected_devices_present(self) -> None:
        names = {d.name for d in DEVICE_CATALOG}
        expected = {
            "jetson_nano", "jetson_xavier", "jetson_orin",
            "rpi5", "x86_workstation",
        }
        assert expected <= names

    def test_device_map_matches_catalog(self) -> None:
        assert len(DEVICE_MAP) == len(DEVICE_CATALOG)
        for d in DEVICE_CATALOG:
            assert DEVICE_MAP[d.name] is d


# ---------------------------------------------------------------------------
# 파라미터 & FLOP 계산 (4 tests)
# ---------------------------------------------------------------------------


class TestComputeParams:
    def test_no_hidden_layers(self) -> None:
        # W(10x3) + b(3) = 33
        assert compute_total_params(10, 3, ()) == 33

    def test_single_hidden_layer(self) -> None:
        # (10*32+32) + (32*3+3) = 352 + 99 = 451
        assert compute_total_params(10, 3, (32,)) == 451

    def test_two_hidden_layers(self) -> None:
        # (10*32+32) + (32*32+32) + (32*3+3) = 352 + 1056 + 99 = 1507
        assert compute_total_params(10, 3, (32, 32)) == 1507

    def test_flops_no_hidden(self) -> None:
        # 2 * 10 * 3 = 60
        assert compute_flops(10, 3, ()) == 60


# ---------------------------------------------------------------------------
# PPO ModelSpec (2 tests)
# ---------------------------------------------------------------------------


class TestPPOModelSpec:
    def test_ppo_spec_dimensions(self) -> None:
        m = make_ppo_model_spec()
        assert m.input_dim == PPO_INPUT_DIM == 63
        assert m.output_dim == PPO_OUTPUT_DIM == 3
        assert m.hidden_layers == PPO_HIDDEN_LAYERS

    def test_ppo_spec_format_override(self) -> None:
        m = make_ppo_model_spec(fmt="TFLITE")
        assert m.format == "TFLITE"


# ---------------------------------------------------------------------------
# 추론 추정: 결정론성 & 정확도 (5 tests)
# ---------------------------------------------------------------------------


class TestEstimateInference:
    def test_deterministic(self) -> None:
        dev = _device()
        m = _model()
        b1 = estimate_inference(dev, m)
        b2 = estimate_inference(dev, m)
        assert b1.latency_ms == b2.latency_ms
        assert b1.throughput_hz == b2.throughput_hz
        assert b1.memory_usage_mb == b2.memory_usage_mb
        assert b1.power_per_inference_mw == b2.power_per_inference_mw

    def test_higher_tflops_lower_latency(self) -> None:
        m = _model()
        slow = estimate_inference(
            _device(compute_capability_tflops=0.1), m,
        )
        fast = estimate_inference(
            _device(compute_capability_tflops=100.0), m,
        )
        assert fast.latency_ms < slow.latency_ms

    def test_realtime_threshold(self) -> None:
        m = _model()
        fast = estimate_inference(
            _device(compute_capability_tflops=1000.0), m,
        )
        assert fast.meets_realtime is True
        assert fast.latency_ms < REALTIME_THRESHOLD_MS

    def test_slow_device_fails_realtime(self) -> None:
        # 큰 모델 + 극도로 느린 디바이스 -> 실시간 미충족
        big = _model(
            input_dim=1000,
            output_dim=100,
            hidden_layers=(512, 512),
            total_params=compute_total_params(1000, 100, (512, 512)),
        )
        slow = estimate_inference(
            _device(compute_capability_tflops=0.00001), big,
        )
        assert slow.meets_realtime is False
        assert slow.latency_ms >= REALTIME_THRESHOLD_MS

    def test_throughput_inverse_of_latency(self) -> None:
        dev = _device()
        m = _model()
        b = estimate_inference(dev, m)
        expected_hz = 1000.0 / b.latency_ms
        assert abs(b.throughput_hz - expected_hz) < 1e-6


# ---------------------------------------------------------------------------
# 전력 효율 순위 (1 test)
# ---------------------------------------------------------------------------


class TestPowerEfficiency:
    def test_power_scales_with_latency_and_watts(self) -> None:
        m = _model()
        low_power = estimate_inference(
            _device(power_watts=5.0, compute_capability_tflops=10.0), m,
        )
        high_power = estimate_inference(
            _device(power_watts=100.0, compute_capability_tflops=10.0), m,
        )
        assert (
            high_power.power_per_inference_mw
            > low_power.power_per_inference_mw
        )


# ---------------------------------------------------------------------------
# ONNX 사양 (2 tests)
# ---------------------------------------------------------------------------


class TestOnnxSpec:
    def test_onnx_spec_keys(self) -> None:
        required = {
            "opset_version", "input_name", "input_shape",
            "input_dtype", "output_name", "output_shape",
            "output_dtype", "description",
        }
        assert required <= set(ONNX_EXPORT_SPEC.keys())

    def test_onnx_spec_shapes_match_ppo(self) -> None:
        assert ONNX_EXPORT_SPEC["input_shape"] == (1, PPO_INPUT_DIM)
        assert ONNX_EXPORT_SPEC["output_shape"] == (1, PPO_OUTPUT_DIM)


# ---------------------------------------------------------------------------
# benchmark_all & recommend_deployment (3 tests)
# ---------------------------------------------------------------------------


class TestBenchmarkAll:
    def test_report_sorted_by_latency(self) -> None:
        m = make_ppo_model_spec()
        report = benchmark_all(m)
        latencies = [b.latency_ms for b in report.benchmarks]
        assert latencies == sorted(latencies)

    def test_realtime_subset(self) -> None:
        m = make_ppo_model_spec()
        report = benchmark_all(m)
        for b in report.realtime_capable:
            assert b.meets_realtime is True
        non_rt = [
            b for b in report.benchmarks if not b.meets_realtime
        ]
        rt_names = {b.device.name for b in report.realtime_capable}
        for b in non_rt:
            assert b.device.name not in rt_names

    def test_recommendations_nonempty(self) -> None:
        m = make_ppo_model_spec()
        recs = recommend_deployment(m)
        assert len(recs) > 0


# ---------------------------------------------------------------------------
# bench_matrix (2 tests)
# ---------------------------------------------------------------------------


class TestBenchMatrix:
    def test_matrix_is_immutable(self) -> None:
        m = make_ppo_model_spec()
        matrix = bench_matrix(m)
        for row in matrix:
            with pytest.raises(TypeError):
                row["device"] = "hacked"  # type: ignore[index]

    def test_matrix_fields(self) -> None:
        m = make_ppo_model_spec()
        matrix = bench_matrix(m)
        expected_keys = {
            "device", "category", "latency_ms", "throughput_hz",
            "memory_usage_mb", "power_per_inference_mw", "meets_realtime",
        }
        for row in matrix:
            assert set(row.keys()) == expected_keys


# ---------------------------------------------------------------------------
# BenchReport 불변성 (1 test)
# ---------------------------------------------------------------------------


class TestBenchReportImmutability:
    def test_frozen_report(self) -> None:
        m = make_ppo_model_spec()
        report = benchmark_all(m)
        with pytest.raises(AttributeError):
            report.benchmarks = ()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CLI (6 tests)
# ---------------------------------------------------------------------------


class TestCLI:
    def test_main_default(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        rc = main([])
        out = capsys.readouterr().out
        assert rc == 0
        assert "Onboard RL Inference Benchmark" in out
        assert "FLOP" in out

    def test_main_bench(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        rc = main(["--bench"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "jetson_nano" in out

    def test_main_device(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        rc = main(["--device", "jetson_orin"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "jetson_orin" in out
        assert "Analytical" in out

    def test_main_device_unknown(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        rc = main(["--device", "nonexistent"])
        out = capsys.readouterr().out
        assert rc == 1
        assert "Unknown device" in out

    def test_main_recommend(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        rc = main(["--recommend"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "Recommendations" in out

    def test_main_json(
        self, capsys: pytest.CaptureFixture[str],
    ) -> None:
        rc = main(["--json"])
        out = capsys.readouterr().out
        assert rc == 0
        data = json.loads(out)
        assert isinstance(data, list)
        assert len(data) == len(DEVICE_CATALOG)
        assert "device" in data[0]
        assert "meets_realtime" in data[0]
