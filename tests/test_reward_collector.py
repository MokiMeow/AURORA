"""Tests for reward metric collector."""

from aurora.reward import MetricCollector, MetricSnapshot


def test_metric_collector_records_snapshots():
    collector = MetricCollector(history_window=2)
    snapshot = MetricSnapshot(
        suite="ci",
        tests_passed=1,
        tests_failed=0,
        coverage_percent=82.5,
        coverage_delta=0.1,
        perf_p95_ms=450.0,
        perf_delta=-0.05,
        security_score=0.9,
        security_findings=0,
        complexity_delta=-0.1,
        policy_bonus=0.2,
        bias_score=0.01,
        duration_seconds=30.0,
    )
    collector.record(snapshot)

    assert collector.last() == snapshot
    assert list(collector.history())[0] == snapshot


def test_metric_collector_parses_ci_metrics(tmp_path):
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(
        """
{
  "tests": {"passed": 8, "failed": 1},
  "coverage": {"percent": 85.0, "delta": 0.3},
  "performance": {"p95_ms": 420, "delta_ms": -15},
  "security": {"score": 0.8, "findings": 1},
  "complexity": {"delta": -0.2},
  "policy": {"bonus": 0.5},
  "bias": {"score": 0.07}
}
        """.strip(),
        encoding="utf-8",
    )
    collector = MetricCollector()
    snapshot = collector.from_ci_results(
        [
            {
                "suite": "ci",
                "metrics_path": str(metrics_path),
                "duration_seconds": 12,
            }
        ]
    )

    assert snapshot.tests_passed == 8.0
    assert snapshot.tests_failed == 1.0
    assert snapshot.coverage_percent == 85.0
    assert snapshot.security_findings == 1.0
    assert snapshot.bias_score == 0.07

