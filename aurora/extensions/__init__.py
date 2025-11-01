"""Extension SDK exports."""

from .base import AuroraExtension, CIHook, ContextProvider, RewardCollector
from .manager import ExtensionManager
from .registry import ExtensionManifest, ExtensionRegistry

__all__ = [
    "AuroraExtension",
    "CIHook",
    "ContextProvider",
    "RewardCollector",
    "ExtensionManager",
    "ExtensionManifest",
    "ExtensionRegistry",
]
