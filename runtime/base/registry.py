"""
AIPENSA Runtime Base - Registry System

Provides global registry for runtime, module, and plugin implementations
with support for discovery, registration, and metadata.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type
import logging
import importlib
import inspect

logger = logging.getLogger(__name__)


class RuntimeRegistry:
    """Registry for runtime implementations."""

    def __init__(self):
        self._runtimes: Dict[str, Type["Runtime"]] = {}
        self._metadata: Dict[str, "RuntimeMetadata"] = {}

    def register(self, runtime_class: Type["Runtime"]) -> None:
        """Register a runtime class."""
        metadata = runtime_class.metadata
        self._runtimes[metadata.name] = runtime_class
        self._metadata[metadata.name] = metadata
        logger.debug(f"Registered runtime: {metadata.name} v{metadata.version}")

    def unregister(self, name: str) -> bool:
        """Unregister a runtime."""
        if name in self._runtimes:
            del self._runtimes[name]
            del self._metadata[name]
            return True
        return False

    def get_runtime(self, name: str) -> Optional[Type["Runtime"]]:
        """Get runtime class by name."""
        return self._runtimes.get(name)

    def get_metadata(self, name: str) -> Optional["RuntimeMetadata"]:
        """Get runtime metadata by name."""
        return self._metadata.get(name)

    def list_runtimes(self) -> List[str]:
        """List all registered runtime names."""
        return list(self._runtimes.keys())

    def list_by_type(self, runtime_type: str) -> List[str]:
        """List runtimes by type."""
        return [
            name for name, meta in self._metadata.items()
            if meta.runtime_type == runtime_type
        ]


@dataclass
class RuntimeMetadata:
    """Runtime metadata for discovery and registration."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    runtime_type: str = "runtime"
    dependencies: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)
    requires: List[str] = field(default_factory=list)
    min_runtime_version: str = "1.0.0"
    max_runtime_version: str = ""


# Global runtime registry
_global_runtime_registry: Optional[RuntimeRegistry] = None


def get_runtime_registry() -> RuntimeRegistry:
    """Get global runtime registry."""
    global _global_runtime_registry
    if _global_runtime_registry is None:
        _global_runtime_registry = RuntimeRegistry()
    return _global_runtime_registry


def set_runtime_registry(registry: RuntimeRegistry) -> None:
    """Set global runtime registry."""
    global _global_runtime_registry
    _global_runtime_registry = registry


# Import for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from runtime.base.module import ModuleRegistry, ModuleMetadata, ModuleState
    from runtime.base.plugin import PluginRegistry, PluginMetadata, PluginStatus
    from runtime.base.runtime import Runtime