"""Tests for reward reporting."""

from pathlib import Path

from aurora.reward import RewardObservation, RewardReportWriter


def test_reward_report_writer_produces_artifacts(tmp_path: Path) -> None:
    writer = RewardReportWriter(tmp_path, formats=("json", "html"), keep_last=5)
    observation = RewardObservation(
        reward=1.0,
        components={"tests": 0.5, "coverage": 0.5},
        penalties={},
        metrics={"suite": "ci"},
        success=True,
        reasons=[],
        metadata={"task": "TASK-1"},
    )
    writer.write(observation)

    assert (tmp_path / "latest_reward.json").exists()
    assert (tmp_path / "latest_reward.html").exists()
    assert (tmp_path / "reward_trend.html").exists()


def test_reward_report_writer_escapes_dynamic_html(tmp_path: Path) -> None:
    writer = RewardReportWriter(tmp_path, formats=("html",))
    observation = RewardObservation(
        reward=0.0,
        components={"<component>": 0.0},
        penalties={},
        metrics={"suite": "<script>alert(1)</script>"},
        success=False,
        reasons=["<b>review</b>"],
        metadata={},
    )

    writer.write(observation)

    report = (tmp_path / "latest_reward.html").read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in report
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in report
    assert "&lt;b&gt;review&lt;/b&gt;" in report
