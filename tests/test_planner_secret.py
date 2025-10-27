"""Tests for secret redaction utility."""

from aurora.planner.secret import build_redactor


def test_redactor_replaces_matches():
    redactor = build_redactor((r"secret",))
    text, hits = redactor.redact("do not leak secret=12345")
    assert hits is True
    assert "<REDACTED>" in text


def test_redactor_no_matches():
    redactor = build_redactor((r"secret",))
    text, hits = redactor.redact("safe text")
    assert hits is False
    assert text == "safe text"

