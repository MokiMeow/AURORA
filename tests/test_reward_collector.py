"""Tests for reward metric collector."""

from aurora.reward import MetricCollector, MetricSnapshot


def test_metric_collector_records_snapshots():
    collector = MetricCollector()
    snapshot = MetricSnapshot(
        tests_passed=1,
        coverage_delta=0.1,
        perf_delta=-0.05,
        security_score=0.9,
        complexity_delta=-0.1,
        policy_bonus=0.2,
    )
    collector.record(snapshot)

    assert collector.last() == snapshot
    assert list(collector.history())[0] == snapshot

