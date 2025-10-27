"""Hardware detection utilities for learning pipeline."""

from __future__ import annotations

import logging

LOGGER = logging.getLogger(__name__)


class HardwareDetector:
    def detect(self) -> dict:
        # Placeholder detection; in production, inspect GPUs/CPUs.
        LOGGER.info("Detecting hardware for learning pipeline")
        return {"gpu": None, "mode": "cpu"}

