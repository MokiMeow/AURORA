"""Extension SDK base classes."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class AuroraExtension(Protocol):
    """Base protocol for all Aurora-SE extensions."""

    def on_autopilot_start(self) -> None:  # pragma: no cover - optional override
        """Hook executed when autopilot starts."""


class ContextProvider(AuroraExtension):
    def build_context(self, task: str) -> str:
        raise NotImplementedError


class CIHook(AuroraExtension):
    def before_ci(self, task: str) -> None:  # pragma: no cover - optional
        ...

    def after_ci(self, task: str) -> None:  # pragma: no cover - optional
        ...


class RewardCollector(AuroraExtension):
    def collect(self, task: str) -> dict:
        raise NotImplementedError
