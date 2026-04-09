"""Phase 200-219 tests: ML Pipeline, Analytics, and Advanced Features."""


class TestMLPipelineIntegration:
    def test_collision_predictor_init(self):
        from simulation.ml_pipeline_integration import CollisionPredictor

        p = CollisionPredictor()
        assert p.version == "1.0.0"

    def test_collision_predictor_predict(self):
        from simulation.ml_pipeline_integration import CollisionPredictor
        import numpy as np

        p = CollisionPredictor()
        features = np.array([[50.0, 10.0, 5.0], [100.0, 20.0, 3.0]])
        result = p.predict(features)
        assert len(result) == 2

    def test_collision_predictor_proba(self):
        from simulation.ml_pipeline_integration import CollisionPredictor
        import numpy as np

        p = CollisionPredictor()
        features = np.array([[30.0, 5.0, 8.0]])
        result = p.predict_proba(features)
        assert result.shape[1] == 2

    def test_collision_risk_prediction(self):
        from simulation.ml_pipeline_integration import CollisionPredictor
        import numpy as np

        p = CollisionPredictor()
        positions = np.array([[0.0, 0.0, 50.0], [40.0, 0.0, 50.0]])
        velocities = np.array([[10.0, 0.0, 0.0], [-10.0, 0.0, 0.0]])
        risks = p.predict_collision_risk(positions, velocities)
        assert len(risks) == 2

    def test_route_optimizer_init(self):
        from simulation.ml_pipeline_integration import RouteOptimizer

        r = RouteOptimizer()
        assert r.version == "1.0.0"

    def test_route_optimizer_predict(self):
        from simulation.ml_pipeline_integration import RouteOptimizer
        import numpy as np

        r = RouteOptimizer()
        features = np.array([[0.0, 0.0, 100.0, 100.0, 2.0, 1.0]])
        result = r.predict(features)
        assert result.shape[0] == 1

    def test_route_optimization(self):
        from simulation.ml_pipeline_integration import RouteOptimizer
        import numpy as np

        r = RouteOptimizer()
        start = np.array([0.0, 0.0, 50.0])
        end = np.array([100.0, 100.0, 50.0])
        result = r.optimize_route(start, end)
        assert "waypoints" in result
        assert "total_distance" in result
        assert result["estimated_time"] > 0

    def test_route_with_obstacles(self):
        from simulation.ml_pipeline_integration import RouteOptimizer
        import numpy as np

        r = RouteOptimizer()
        start = np.array([0.0, 0.0, 50.0])
        end = np.array([100.0, 100.0, 50.0])
        obstacles = [np.array([50.0, 50.0, 50.0])]
        result = r.optimize_route(start, end, obstacles)
        assert result["obstacle_avoidance"] is True

    def test_demand_forecaster_init(self):
        from simulation.ml_pipeline_integration import DemandForecaster

        d = DemandForecaster()
        assert d.version == "1.0.0"

    def test_demand_forecaster_predict(self):
        from simulation.ml_pipeline_integration import DemandForecaster
        import numpy as np

        d = DemandForecaster()
        features = np.array([[8.0, 1.0, 1.0, 100.0], [22.0, 1.0, 0.8, 50.0]])
        result = d.predict(features)
        assert len(result) == 2

    def test_demand_forecast(self):
        from simulation.ml_pipeline_integration import DemandForecaster

        d = DemandForecaster()
        result = d.forecast_demand(hours_ahead=12)
        assert "forecasts" in result
        assert len(result["forecasts"]) == 12
        assert "total_demand" in result

    def test_demand_forecast_rain_scenario(self):
        from simulation.ml_pipeline_integration import DemandForecaster

        d = DemandForecaster()
        result = d.forecast_demand(hours_ahead=6, weather_scenario="rain")
        assert result["weather_scenario"] == "rain"
        assert result["total_demand"] < 500

    def test_ml_inference_pipeline_init(self):
        from simulation.ml_pipeline_integration import MLInferencePipeline

        p = MLInferencePipeline()
        stats = p.get_pipeline_stats()
        assert stats["gpu_enabled"] is False
        assert stats["cache_size"] == 0

    def test_ml_inference_pipeline_gpu(self):
        from simulation.ml_pipeline_integration import MLInferencePipeline

        p = MLInferencePipeline()
        p.enable_gpu()
        assert p._use_gpu is True

    def test_full_inference_pipeline(self):
        from simulation.ml_pipeline_integration import MLInferencePipeline
        import numpy as np

        p = MLInferencePipeline()
        positions = np.random.rand(5, 3) * 100
        velocities = np.random.rand(5, 3) * 10
        start = np.array([0.0, 0.0, 50.0])
        end = np.array([100.0, 100.0, 50.0])
        result = p.run_full_inference(positions, velocities, start, end)
        assert "collision_risks" in result
        assert "route" in result
        assert "demand_forecast" in result


class TestAdvancedAnalytics:
    def test_metric_snapshot_creation(self):
        from simulation.advanced_analytics import MetricSnapshot

        s = MetricSnapshot(timestamp=1000.0, name="latency", value=45.5, unit="ms")
        assert s.name == "latency"
        assert s.value == 45.5

    def test_performance_report_creation(self):
        from simulation.advanced_analytics import PerformanceReport, MetricSnapshot

        snapshots = [
            MetricSnapshot(timestamp=1000.0, name="cpu", value=50.0),
            MetricSnapshot(timestamp=1001.0, name="cpu", value=55.0),
        ]
        r = PerformanceReport(
            report_id="test-001",
            created_at="2026-03-29T12:00:00",
            metrics=snapshots,
            summary={"cpu_mean": 52.5},
        )
        assert r.report_id == "test-001"
        assert len(r.metrics) == 2

    def test_analytics_aggregator_add_snapshot(self):
        from simulation.advanced_analytics import AnalyticsAggregator, MetricSnapshot

        a = AnalyticsAggregator()
        a.add_snapshot(MetricSnapshot(timestamp=1000.0, name="test", value=10.0))
        assert len(a.get_all_metric_names()) == 1

    def test_analytics_aggregator_statistics(self):
        from simulation.advanced_analytics import AnalyticsAggregator, MetricSnapshot

        a = AnalyticsAggregator()
        for i in range(10):
            a.add_snapshot(
                MetricSnapshot(timestamp=float(i), name="latency", value=float(i * 2))
            )
        stats = a.compute_statistics("latency")
        assert stats["count"] == 10
        assert stats["mean"] == 9.0
        assert stats["min"] == 0.0
        assert stats["max"] == 18.0

    def test_analytics_aggregator_anomaly_detection(self):
        from simulation.advanced_analytics import AnalyticsAggregator, MetricSnapshot

        a = AnalyticsAggregator()
        for i in range(10):
            a.add_snapshot(
                MetricSnapshot(timestamp=float(i), name="metric", value=float(i))
            )
        a.add_snapshot(MetricSnapshot(timestamp=10.0, name="metric", value=100.0))
        anomalies = a.detect_anomalies("metric", threshold_std=2.0)
        assert len(anomalies) >= 1

    def test_analytics_aggregator_correlation(self):
        from simulation.advanced_analytics import AnalyticsAggregator, MetricSnapshot

        a = AnalyticsAggregator()
        for i in range(10):
            a.add_snapshot(MetricSnapshot(timestamp=float(i), name="a", value=float(i)))
            a.add_snapshot(
                MetricSnapshot(timestamp=float(i), name="b", value=float(i * 2))
            )
        corr = a.compute_correlation("a", "b")
        assert abs(corr - 1.0) < 0.001

    def test_analytics_aggregator_report_generation(self):
        from simulation.advanced_analytics import AnalyticsAggregator, MetricSnapshot

        a = AnalyticsAggregator()
        for i in range(5):
            a.add_snapshot(
                MetricSnapshot(timestamp=float(i), name="test", value=float(i))
            )
        report = a.generate_report()
        assert report.report_id.startswith("report_")
        assert "test" in report.summary

    def test_performance_comparator_add_report(self):
        from simulation.advanced_analytics import (
            PerformanceComparator,
            PerformanceReport,
        )

        c = PerformanceComparator()
        report = PerformanceReport(
            report_id="r1",
            created_at="2026-03-29",
            metrics=[],
            summary={"latency": 45.0},
        )
        c.add_report("run1", report)
        assert "run1" in c._reports

    def test_performance_comparator_compare_metric(self):
        from simulation.advanced_analytics import (
            PerformanceComparator,
            PerformanceReport,
        )

        c = PerformanceComparator()
        c.add_report(
            "baseline",
            PerformanceReport("r1", "2026", [], {"latency": 50.0}),
        )
        c.add_report(
            "optimized",
            PerformanceReport("r2", "2026", [], {"latency": 40.0}),
        )
        comp = c.compare_metric("latency", "baseline")
        assert abs(comp["optimized"]["change_pct"] - (-20.0)) < 0.01

    def test_performance_comparator_find_best(self):
        from simulation.advanced_analytics import (
            PerformanceComparator,
            PerformanceReport,
        )

        c = PerformanceComparator()
        c.add_report("a", PerformanceReport("r1", "2026", [], {"score": 80.0}))
        c.add_report("b", PerformanceReport("r2", "2026", [], {"score": 95.0}))
        c.add_report("c", PerformanceReport("r3", "2026", [], {"score": 70.0}))
        best = c.find_best_performer("score", higher_is_better=True)
        assert best == "b"

    def test_trend_analyzer_moving_average(self):
        from simulation.advanced_analytics import TrendAnalyzer

        t = TrendAnalyzer(window_size=3)
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        ma = t.compute_moving_average(values, window=3)
        assert len(ma) == 5
        assert ma[2] == 2.0

    def test_trend_analyzer_detect_trend(self):
        from simulation.advanced_analytics import TrendAnalyzer

        t = TrendAnalyzer()
        assert t.detect_trend([1.0, 2.0, 3.0, 4.0, 5.0]) == "increasing"
        assert t.detect_trend([5.0, 4.0, 3.0, 2.0, 1.0]) == "decreasing"
        assert t.detect_trend([5.0, 5.0, 5.0, 5.0]) == "stable"

    def test_trend_analyzer_predict_next(self):
        from simulation.advanced_analytics import TrendAnalyzer

        t = TrendAnalyzer()
        values = [1.0, 2.0, 3.0, 4.0]
        predictions = t.predict_next_value(values, n_steps=2)
        assert len(predictions) == 2
        assert predictions[0] > 4.0


class TestIntegration:
    def test_ml_pipeline_to_analytics(self):
        from simulation.ml_pipeline_integration import MLInferencePipeline
        from simulation.advanced_analytics import AnalyticsAggregator, MetricSnapshot
        import numpy as np

        pipeline = MLInferencePipeline()
        aggregator = AnalyticsAggregator()

        positions = np.random.rand(3, 3) * 100
        velocities = np.random.rand(3, 3) * 10
        result = pipeline.run_full_inference(
            positions, velocities, np.zeros(3), np.ones(3) * 100
        )

        for i, risk in enumerate(result["collision_risks"]):
            aggregator.add_snapshot(
                MetricSnapshot(
                    timestamp=float(i), name="collision_risk", value=float(risk)
                )
            )

        stats = aggregator.compute_statistics("collision_risk")
        assert stats["count"] == 3

    def test_full_pipeline_with_export(self, tmp_path):
        from simulation.ml_pipeline_integration import MLInferencePipeline
        from simulation.advanced_analytics import AnalyticsAggregator
        import numpy as np

        pipeline = MLInferencePipeline()
        aggregator = AnalyticsAggregator()

        for i in range(5):
            positions = np.random.rand(3, 3) * 100
            velocities = np.random.rand(3, 3) * 10
            result = pipeline.run_full_inference(
                positions, velocities, np.zeros(3), np.ones(3) * 100
            )
            for risk in result["collision_risks"]:
                aggregator.add_snapshot(
                    __import__(
                        "simulation.advanced_analytics", fromlist=["MetricSnapshot"]
                    ).MetricSnapshot(timestamp=float(i), name="risk", value=float(risk))
                )

        export_path = tmp_path / "analytics_export.json"
        aggregator.export_to_json(export_path)
        assert export_path.exists()


class TestEdgeCases:
    def test_empty_aggregator_statistics(self):
        from simulation.advanced_analytics import AnalyticsAggregator

        a = AnalyticsAggregator()
        stats = a.compute_statistics("nonexistent")
        assert stats == {}

    def test_empty_correlation(self):
        from simulation.advanced_analytics import AnalyticsAggregator

        a = AnalyticsAggregator()
        corr = a.compute_correlation("a", "b")
        assert corr == 0.0

    def test_single_value_trend(self):
        from simulation.advanced_analytics import TrendAnalyzer

        t = TrendAnalyzer()
        trend = t.detect_trend([5.0])
        assert trend == "stable"

    def test_route_optimizer_no_obstacles(self):
        from simulation.ml_pipeline_integration import RouteOptimizer
        import numpy as np

        r = RouteOptimizer()
        result = r.optimize_route(np.zeros(3), np.ones(3) * 50)
        assert result["obstacle_avoidance"] is False

    def test_demand_forecast_empty_hours(self):
        from simulation.ml_pipeline_integration import DemandForecaster

        d = DemandForecaster()
        result = d.forecast_demand(hours_ahead=0)
        assert result["total_demand"] == 0.0
