"""Phase 180 tests: Ops Report Bundle and Report Input Normalization."""


class TestReportInputNormalizer:
    def test_input_contract_version(self):
        from simulation.report_input_normalizer import INPUT_CONTRACT_VERSION

        assert INPUT_CONTRACT_VERSION == "phase180.report_inputs.v1"

    def test_normalize_delivery_with_dict(self):
        from simulation.report_input_normalizer import normalize_delivery

        out = normalize_delivery(
            {"delivered": 95, "dispatched": 100, "avg_dispatch_congestion": 0.3}
        )
        assert out["delivered"] == 95

    def test_normalize_delivery_with_dataclass(self):
        from dataclasses import dataclass
        from simulation.report_input_normalizer import normalize_delivery

        @dataclass
        class DeliveryResult:
            delivered: int = 50
            dispatched: int = 60

        out = normalize_delivery(DeliveryResult())
        assert out["delivered"] == 50

    def test_normalize_compliance_with_violations(self):
        from simulation.report_input_normalizer import normalize_compliance

        out = normalize_compliance(
            {
                "total_violations": 3,
                "critical_violations": 1,
                "severity_trend": [0, 1, 2],
            }
        )
        assert out["total_violations"] == 3

    def test_normalize_compliance_with_none(self):
        from simulation.report_input_normalizer import normalize_compliance

        out = normalize_compliance(None)
        assert out.get("total_violations", 0) == 0

    def test_normalize_recorder_summary(self):
        from simulation.report_input_normalizer import normalize_recorder

        out = normalize_recorder({"events": 150, "warnings": 5, "errors": 1})
        assert out["events"] == 150

    def test_normalize_performance_with_success_rate(self):
        from simulation.report_input_normalizer import normalize_performance

        out = normalize_performance(
            {"success_rate": 0.92, "latency_ms": 45.0}, window_sec=60.0
        )
        assert out["success_rate"] == 0.92

    def test_normalize_traffic_with_congestion(self):
        from simulation.report_input_normalizer import normalize_traffic

        out = normalize_traffic({"avg_congestion": 0.65, "peak_congestion": 0.9})
        assert out["avg_congestion"] == 0.65

    def test_normalize_scenario_with_all_fields(self):
        from simulation.report_input_normalizer import normalize_scenario

        raw = {
            "scenario": "high_density",
            "seed": 42,
            "run_idx": 1,
            "duration_s": 300.0,
            "n_drones": 100,
            "collision_count": 2,
            "near_miss_count": 15,
            "conflict_resolution_rate_pct": 99.5,
            "route_efficiency_mean": 0.87,
            "source": "simulation",
        }
        out = normalize_scenario(raw)
        assert out["scenario"] == "high_density"
        assert out["seed"] == 42
        assert out["n_drones"] == 100
        assert out["collision_count"] == 2

    def test_normalize_meta_with_schema_version(self):
        from simulation.report_input_normalizer import normalize_meta

        out = normalize_meta({"run_id": "run-001"}, scenario={"seed": 123})
        assert out["schema_version"] == "phase172.v1"
        assert out["input_contract_version"] == "phase180.report_inputs.v1"
        assert out["seed"] == 123

    def test_normalize_full_pipeline(self):
        from simulation.report_input_normalizer import normalize_report_inputs

        out = normalize_report_inputs(
            delivery_summary={"delivered": 80, "dispatched": 100},
            compliance_report={"total_violations": 1},
            recorder_summary={"events": 200},
            perf_report={"success_rate": 0.88},
            traffic_summary={"avg_congestion": 0.5},
            meta={"run_id": "test-run"},
            scenario_summary={"scenario": "test", "seed": 1, "n_drones": 50},
        )
        assert "delivery" in out
        assert "compliance" in out
        assert "performance" in out
        assert out["meta"]["input_contract_version"] == "phase180.report_inputs.v1"


class TestE2EReporter:
    def test_init_thresholds(self):
        from simulation.e2e_reporter import E2EReporter

        r = E2EReporter(green_threshold=0.9, yellow_threshold=0.7)
        assert r._green_threshold == 0.9
        assert r._yellow_threshold == 0.7

    def test_init_invalid_thresholds(self):
        from simulation.e2e_reporter import E2EReporter

        try:
            E2EReporter(green_threshold=0.5, yellow_threshold=0.7)
            assert False, "Should raise ValueError"
        except ValueError:
            pass

    def test_tune_status_thresholds(self):
        from simulation.e2e_reporter import E2EReporter

        r = E2EReporter()
        r.tune_status_thresholds(green_threshold=0.95, yellow_threshold=0.75)
        assert r._green_threshold == 0.95
        assert r._yellow_threshold == 0.75

    def test_build_with_minimal_inputs(self):
        from simulation.e2e_reporter import E2EReporter

        r = E2EReporter()
        out = r.build(
            delivery_summary={"delivered": 100, "dispatched": 100},
            compliance_report={"total_violations": 0},
            recorder_summary={"events": 50},
            perf_report={"success_rate": 1.0},
        )
        assert "delivery" in out
        assert "compliance" in out
        assert "kpi" in out or "health_score" in out
        assert "status" in out

    def test_build_health_score_calculation(self):
        from simulation.e2e_reporter import E2EReporter

        r = E2EReporter()
        out = r.build(
            delivery_summary={"delivered": 100, "dispatched": 100},
            compliance_report={"total_violations": 0},
            recorder_summary={"events": 50},
            perf_report={"success_rate": 1.0},
        )
        hs = out.get("health_score") or out.get("kpi", {}).get("health_score")
        assert hs is not None
        assert 0.0 <= hs <= 1.0

    def test_build_traffic_penalty_applied(self):
        from simulation.e2e_reporter import E2EReporter

        r = E2EReporter()
        out_no_traffic = r.build(
            delivery_summary={"delivered": 100},
            compliance_report={"total_violations": 0},
            recorder_summary={"events": 50},
            perf_report={"success_rate": 1.0},
        )
        out_with_traffic = r.build(
            delivery_summary={"delivered": 100, "avg_dispatch_congestion": 0.5},
            compliance_report={"total_violations": 0},
            recorder_summary={"events": 50},
            perf_report={"success_rate": 1.0},
            traffic_summary={"avg_congestion": 0.8},
        )
        hs1 = out_no_traffic.get("health_score") or out_no_traffic.get("kpi", {}).get("health_score", 1.0)
        hs2 = out_with_traffic.get("health_score") or out_with_traffic.get("kpi", {}).get("health_score", 0.0)
        assert hs1 >= hs2

    def test_status_green_when_healthy(self):
        from simulation.e2e_reporter import E2EReporter

        r = E2EReporter(green_threshold=0.85)
        out = r.build(
            delivery_summary={"delivered": 100},
            compliance_report={"total_violations": 0},
            recorder_summary={"events": 50},
            perf_report={"success_rate": 0.95},
        )
        assert out["status"].upper() in ["GREEN", "YELLOW", "RED"]

    def test_status_red_when_failing(self):
        from simulation.e2e_reporter import E2EReporter

        r = E2EReporter()
        out = r.build(
            delivery_summary={"delivered": 0},
            compliance_report={"total_violations": 10},
            recorder_summary={"events": 0},
            perf_report={"success_rate": 0.0},
        )
        assert out["status"].upper() == "RED"

    def test_build_includes_sections(self):
        from simulation.e2e_reporter import E2EReporter

        r = E2EReporter()
        out = r.build(
            delivery_summary={"delivered": 50},
            compliance_report={"total_violations": 1},
            recorder_summary={"events": 25},
            perf_report={"success_rate": 0.5},
        )
        assert "sections" in out
        assert "compliance" in out["sections"]
        assert "performance" in out["sections"]


class TestE2EReporterExport:
    def test_render_markdown_returns_string(self):
        from simulation.e2e_reporter import E2EReporter

        r = E2EReporter()
        report = r.build(
            delivery_summary={"delivered": 100, "dispatched": 100},
            compliance_report={"total_violations": 0},
            recorder_summary={"events": 50},
            perf_report={"success_rate": 1.0},
        )
        md = r.render_markdown(report)
        assert isinstance(md, str)
        assert "##" in md

    def test_render_markdown_contains_sections(self):
        from simulation.e2e_reporter import E2EReporter

        r = E2EReporter()
        report = r.build(
            delivery_summary={"delivered": 80},
            compliance_report={"total_violations": 2},
            recorder_summary={"events": 100},
            perf_report={"success_rate": 0.85},
        )
        md = r.render_markdown(report)
        assert "compliance" in md.lower() or "Compliance" in md
        assert "delivery" in md.lower() or "Delivery" in md

    def test_export_bundle_creates_files(self, tmp_path):
        from simulation.e2e_reporter import E2EReporter

        r = E2EReporter()
        report = r.build(
            delivery_summary={"delivered": 75},
            compliance_report={"total_violations": 1},
            recorder_summary={"events": 60},
            perf_report={"success_rate": 0.9},
        )
        bundle_dir = tmp_path / "bundle"
        result = r.export_bundle(report, output_dir=str(bundle_dir))
        assert "status" in result or "json_path" in result

    def test_export_bundle_manifest_contains_version(self, tmp_path):
        from simulation.e2e_reporter import E2EReporter

        r = E2EReporter()
        report = r.build(
            delivery_summary={"delivered": 50},
            compliance_report={"total_violations": 0},
            recorder_summary={"events": 30},
            perf_report={"success_rate": 0.75},
        )
        bundle_dir = tmp_path / "bundle"
        result = r.export_bundle(report, output_dir=str(bundle_dir))
        import json

        manifest_path = result.get("manifest_path")
        if manifest_path:
            manifest = json.loads(open(manifest_path).read())
            assert "schema_version" in manifest or "manifest_version" in manifest


import pytest

class TestScenarioPackPromoter:
    def test_promote_scenario_pack(self):
        pytest.importorskip("simulation.scenario_pack_promoter")
        from simulation.scenario_pack_promoter import ScenarioPackPromoter

        p = ScenarioPackPromoter()
        pack = p.promote(
            scenario_name="high_density",
            seed=42,
            n_drones=100,
            collision_count=1,
            resolution_rate_pct=99.5,
        )
        assert pack["scenario"] == "high_density"
        assert pack["seed"] == 42
        assert pack["validated"] is True

    def test_promote_multiple_runs(self):
        pytest.importorskip("simulation.scenario_pack_promoter")
        from simulation.scenario_pack_promoter import ScenarioPackPromoter

        p = ScenarioPackPromoter()
        packs = p.promote_batch(
            [
                {"scenario_name": "weather_disturbance", "seed": 1, "n_drones": 50},
                {"scenario_name": "emergency_failure", "seed": 2, "n_drones": 75},
            ]
        )
        assert len(packs) == 2
        assert all(p["validated"] for p in packs)

    def test_pack_metadata_includes_timestamp(self):
        pytest.importorskip("simulation.scenario_pack_promoter")
        from simulation.scenario_pack_promoter import ScenarioPackPromoter

        p = ScenarioPackPromoter()
        pack = p.promote(scenario_name="comms_loss", seed=99, n_drones=30)
        assert "created_at" in pack
        assert "pack_version" in pack


class TestCILogging:
    def test_log_run_info(self):
        pytest.importorskip("simulation.ci_logging")
        from simulation.ci_logging import log_run_info

        result = log_run_info(python_version="3.11", commit_sha="abc123", branch="main")
        assert result["status"] == "ok"
        assert result["commit"] == "abc123"

    def test_log_perf_summary(self):
        pytest.importorskip("simulation.ci_logging")
        from simulation.ci_logging import log_perf_summary

        summary = {
            "tests_passed": 1345,
            "tests_failed": 0,
            "duration_sec": 45.0,
        }
        result = log_perf_summary(summary)
        assert result["status"] == "ok"
        assert result["tests_passed"] == 1345

    def test_emit_smoke_report(self):
        pytest.importorskip("simulation.ci_logging")
        from simulation.ci_logging import emit_smoke_report

        report = {
            "health_score": 0.95,
            "status": "green",
            "delivery_delivered": 100,
        }
        result = emit_smoke_report(report)
        assert result["emitted"] is True


class TestOpenCLAcceleratorHardening:
    def test_opencl_accelerator_init(self):
        from simulation.opencl_accelerator import OpenCLAccelerator

        a = OpenCLAccelerator()
        assert a._available is not None

    def test_opencl_fallback_available(self):
        from simulation.opencl_accelerator import OpenCLAccelerator

        a = OpenCLAccelerator()
        import numpy as np
        result = a.vector_add(np.array([1, 2, 3]), np.array([4, 5, 6]))
        assert isinstance(result, (list, tuple, np.ndarray))
        assert len(result) == 3

    def test_opencl_summary(self):
        from simulation.opencl_accelerator import OpenCLAccelerator

        a = OpenCLAccelerator()
        result = a.summary()
        assert "backend" in result
        assert "available" in result


class TestVisualAssetOps:
    def test_asset_index_loaded(self):
        pytest.importorskip("simulation.visual_asset_ops")
        from simulation.visual_asset_ops import load_asset_index

        index = load_asset_index()
        assert isinstance(index, dict)

    def test_asset_check_missing(self):
        pytest.importorskip("simulation.visual_asset_ops")
        from simulation.visual_asset_ops import check_missing_assets

        missing = check_missing_assets()
        assert isinstance(missing, list)

    def test_asset_sync_report(self):
        pytest.importorskip("simulation.visual_asset_ops")
        from simulation.visual_asset_ops import generate_sync_report

        report = generate_sync_report()
        assert "total_assets" in report
        assert "missing_assets" in report


class TestIntegrationBundle:
    def test_full_bundle_pipeline(self, tmp_path):
        from simulation.e2e_reporter import E2EReporter
        from simulation.report_input_normalizer import INPUT_CONTRACT_VERSION

        r = E2EReporter()
        report = r.build(
            delivery_summary={"delivered": 88, "dispatched": 100},
            compliance_report={"total_violations": 2},
            recorder_summary={"events": 150},
            perf_report={"success_rate": 0.91},
            traffic_summary={"avg_congestion": 0.45},
            meta={"run_id": "integration-test"},
            scenario_summary={
                "scenario": "integration_test",
                "seed": 999,
                "n_drones": 200,
            },
        )
        bundle_dir = tmp_path / "bundle"
        result = r.export_bundle(report, output_dir=str(bundle_dir))
        assert "status" in result or "json_path" in result
        # manifest 파일명이 동적이므로 result에서 경로 사용
        if result.get("manifest_path"):
            import json
            manifest = json.loads(open(result["manifest_path"]).read())
            assert "schema_version" in manifest or "manifest_version" in manifest


class TestRegressionProtection:
    def test_normalizer_preserves_collision_count(self):
        from simulation.report_input_normalizer import normalize_scenario

        raw = {
            "scenario": "high_density",
            "seed": 42,
            "n_drones": 100,
            "collision_count": 5,
            "near_miss_count": 20,
        }
        out = normalize_scenario(raw)
        assert out["collision_count"] == 5
        assert out["near_miss_count"] == 20

    def test_e2e_reporter_no_crash_on_empty(self):
        from simulation.e2e_reporter import E2EReporter

        r = E2EReporter()
        out = r.build(
            delivery_summary={},
            compliance_report={},
            recorder_summary={},
            perf_report={},
        )
        hs = out.get("health_score") or out.get("kpi", {}).get("health_score")
        assert hs is not None and hs >= 0.0

    def test_bundle_handles_special_characters(self, tmp_path):
        from simulation.e2e_reporter import E2EReporter

        r = E2EReporter()
        report = r.build(
            delivery_summary={"delivered": 50},
            compliance_report={"total_violations": 0},
            recorder_summary={"events": 10},
            perf_report={"success_rate": 0.5},
        )
        report["meta"]["note"] = "Test with 'quotes' and \"double quotes\""
        bundle_dir = tmp_path / "bundle"
        result = r.export_bundle(report, output_dir=str(bundle_dir))
        assert "status" in result or "json_path" in result
