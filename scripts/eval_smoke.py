"""Deterministic end-to-end smoke command for the evaluation CLI."""

from __future__ import annotations


def main() -> None:
    print("METRIC: success_rate=1.0")
    print("METRIC: latency_seconds=0.0")
    print("METRIC: failures=0")


if __name__ == "__main__":
    main()
