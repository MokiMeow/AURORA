"""Planner routing utilities."""

from __future__ import annotations

from typing import Sequence

from .config import ModelRoute, PlannerConfig, RoutingRule, RoutingStrategy


class PlannerRouter:
    """Selects model routes based on task metadata and routing rules."""

    def __init__(self, config: PlannerConfig) -> None:
        self._config = config
        self._routes = {route.name: route for route in config.routes}
        primary_route = ModelRoute(
            name="primary",
            provider=config.primary.provider,
            endpoint=config.primary.endpoint,
            model=config.primary.model,
            timeout_seconds=config.primary.timeout_seconds,
        )
        self._routes.setdefault(primary_route.name, primary_route)
        self._routing = config.routing or RoutingStrategy(default_route=primary_route.name, rules=())

    def routes(self) -> Sequence[ModelRoute]:
        return tuple(self._routes.values())

    def get(self, name: str) -> ModelRoute:
        try:
            return self._routes[name]
        except KeyError as exc:  # pragma: no cover - defensive
            raise ValueError(f"Unknown model route {name}") from exc

    def select_route(
        self,
        task: str,
        context_summaries: Sequence[str] | None = None,
        auto: bool = False,
    ) -> ModelRoute:
        text = self._normalise(task, context_summaries)
        for rule in self._routing.rules:
            if rule.auto_only and not auto:
                continue
            if self._match_keywords(rule, text):
                route = self._routes.get(rule.route)
                if route:
                    return route
        return self._routes.get(self._routing.default_route, next(iter(self._routes.values())))

    @staticmethod
    def _normalise(task: str, context_summaries: Sequence[str] | None) -> str:
        parts = [task]
        if context_summaries:
            parts.extend(context_summaries)
        return " ".join(parts).lower()

    @staticmethod
    def _match_keywords(rule: RoutingRule, text: str) -> bool:
        if not rule.keywords:
            return True
        return all(keyword.lower() in text for keyword in rule.keywords)

