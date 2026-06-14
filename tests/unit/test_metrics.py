def test_metrics_collector_records_and_retrieves():
    from cherenkov.observability.metrics import MetricsCollector, StageMetric

    collector = MetricsCollector(db_path=":memory:")
    metric = StageMetric(
        run_id="test-run-1",
        stage="generate",
        latency_ms=1250.0,
        success=True,
        model_name="qwen2.5-coder:7b",
        provider_name="ollama",
    )
    collector.record(metric)
    summary = collector.get_summary(last_n_runs=5)
    assert len(summary) == 1
    assert summary[0]["stage"] == "generate"
    assert abs(summary[0]["avg_latency_ms"] - 1250.0) < 0.1
    assert summary[0]["success_rate"] == 1.0
    collector.close()


def test_metrics_collector_prometheus_output():
    from cherenkov.observability.metrics import MetricsCollector, StageMetric

    collector = MetricsCollector(db_path=":memory:")
    collector.record(
        StageMetric(run_id="r1", stage="ingest", latency_ms=300, success=True)
    )
    prom = collector.to_prometheus()
    assert "cherenkov_stage_latency_ms" in prom
    assert "ingest" in prom
    collector.close()


def test_metrics_collector_handles_empty_db():
    from cherenkov.observability.metrics import MetricsCollector

    collector = MetricsCollector(db_path=":memory:")
    summary = collector.get_summary()
    assert summary == []
    prom = collector.to_prometheus()
    assert isinstance(prom, str)
    collector.close()
