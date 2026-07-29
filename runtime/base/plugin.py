"""
AIPENSA Runtime Base - Plugin Abstraction

Defines the plugin interface and lifecycle that all runtime plugins
must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Type
import logging
import uuid

logger = logging.getLogger(__name__)


class PluginType(Enum):
    """Types of plugins supported by the runtime."""

    TOOL = "tool"              # Function calling, tools
    ADAPTER = "adapter"        # External service adapters
    STORAGE = "storage"        # Storage backends
    LLM = "llm"               # LLM providers
    BROWSER = "browser"       # Browser automation
    SANDBOX = "sandbox"       # Code execution sandboxes
    AUTH = "auth"             # Authentication providers
    MONITORING = "monitoring" # Observability/monitoring
    INTEGRATION = "integration" # Third-party integrations
    CUSTOM = "custom"         # Custom plugin types


class PluginStatus(Enum):
    """Plugin lifecycle status."""

    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class PluginMetadata:
    """Plugin metadata for discovery and registration."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    plugin_type: PluginType = PluginType.CUSTOM
    dependencies: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)
    requires: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    entry_point: str = ""  # Module:Class path
    config_schema: Dict[str, Any] = field(default_factory=dict)
    min_runtime_version: str = "1.0.0"
    max_runtime_version: str = ""
    license: str = "MIT"


@dataclass
class PluginContext:
    """Context passed to plugins during initialization."""

    runtime: "Runtime"
    config: Dict[str, Any]
    plugin_id: str
    logger: logging.Logger


class RuntimePlugin(ABC):
    """
    Base class for all runtime plugins.

    Plugins extend runtime functionality without being core modules.
    They follow the same lifecycle as modules but are more lightweight
    and focused on specific integrations or capabilities.

    Lifecycle:
    1. __init__(config) - Construction with config
    2. initialize(runtime, config) - Setup with runtime reference
    3. start() - Begin operations
    4. stop() - Graceful shutdown
    5. cleanup() - Release resources
    6. health_check() - Return health status
    """

    metadata: PluginMetadata

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._runtime: Optional["Runtime"] = None
        self._status = PluginStatus.UNLOADED
        self._plugin_id = str(uuid.uuid4())[:8]
        self._started_at: Optional[datetime] = None
        self._logger = logging.getLogger(f"runtime.plugin.{self.metadata.name}")

    @property
    def plugin_id(self) -> str:
        return self._plugin_id

    @property
    def status(self) -> PluginStatus:
        return self._status

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def runtime(self) -> Optional["Runtime"]:
        return self._runtime

    @property
    def started_at(self) -> Optional[datetime]:
        return self._started_at

    @property
    def uptime_seconds(self) -> float:
        if self._started_at:
            return (datetime.utcnow() - self._started_at).total_seconds()
        return 0.0

    # =============================================
    # Abstract Methods (must be implemented)
    # =============================================

    @abstractmethod
    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        """
        Initialize the plugin with runtime reference and configuration.

        Called once during plugin loading.
        """
        self._runtime = runtime
        self._status = PluginStatus.INITIALIZED
        self._logger.info(f"Plugin {self.name} initialized")

    @abstractmethod
    async def start(self) -> None:
        """
        Start plugin operations.

        Should establish connections, register handlers, etc.
        """
        self._status = PluginStatus.RUNNING
        self._started_at = datetime.utcnow()
        self._logger.info(f"Plugin {self.name} started")

    @abstractmethod
    async def stop(self) -> None:
        """
        Stop plugin operations gracefully.
        """
        self._status = PluginStatus.STOPPED
        self._logger.info(f"Plugin {self.name} stopped")

    @abstractmethod
    async def cleanup(self) -> None:
        """
        Clean up all resources.

        Called during runtime shutdown.
        """
        self._status = PluginStatus.UNLOADED
        self._runtime = None
        self._started_at = None
        self._logger.info(f"Plugin {self.name} cleaned up")

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Return health status of the plugin.
        """
        return {
            "plugin": self.name,
            "healthy": self._status == PluginStatus.RUNNING,
            "status": self._status.value,
            "uptime_seconds": self.uptime_seconds,
        }

    # =============================================
    # Optional Methods (can be overridden)
    # =============================================

    def validate_config(self) -> bool:
        """
        Validate plugin configuration.

        Override for custom validation logic.
        """
        return True

    def get_services(self) -> List[str]:
        """
        Return list of services this plugin provides.

        Used for service discovery.
        """
        return self.metadata.provides.copy()

    async def execute(self, operation: str, **kwargs) -> Any:
        """
        Execute a plugin-specific operation.

        Generic execution interface for dynamic invocation.
        Override for plugin-specific operations.
        """
        raise NotImplementedError(
            f"Operation '{operation}' not supported by {self.name}"
        )


class PluginRegistry:
    """Registry for plugin implementations."""

    def __init__(self):
        self._plugins: Dict[str, Type[RuntimePlugin]] = {}
        self._metadata: Dict[str, PluginMetadata] = {}

    def register(self, plugin_class: Type[RuntimePlugin]) -> None:
        """Register a plugin class."""
        metadata = plugin_class.metadata
        self._plugins[metadata.name] = plugin_class
        self._metadata[metadata.name] = metadata
        logger.debug(f"Registered plugin: {metadata.name} v{metadata.version}")

    def unregister(self, name: str) -> bool:
        """Unregister a plugin."""
        if name in self._plugins:
            del self._plugins[name]
            del self._metadata[name]
            return True
        return False

    def get_plugin(self, name: str) -> Optional[Type[RuntimePlugin]]:
        """Get plugin class by name."""
        return self._plugins.get(name)

    def get_metadata(self, name: str) -> Optional[PluginMetadata]:
        """Get plugin metadata by name."""
        return self._metadata.get(name)

    def list_plugins(self) -> List[str]:
        """List all registered plugin names."""
        return list(self._plugins.keys())

    def list_by_type(self, plugin_type: PluginType) -> List[str]:
        """List plugins by type."""
        return [
            name for name, meta in self._metadata.items()
            if meta.plugin_type == plugin_type
        ]

    def list_by_tag(self, tag: str) -> List[str]:
        """List plugins by tag."""
        return [
            name for name, meta in self._metadata.items()
            if tag in meta.tags
        ]


# Global plugin registry instance
_global_plugin_registry: Optional[PluginRegistry] = None


def get_plugin_registry() -> PluginRegistry:
    """Get global plugin registry."""
    global _global_plugin_registry
    if _global_plugin_registry is None:
        _global_plugin_registry = PluginRegistry()
    return _global_plugin_registry


def set_plugin_registry(registry: PluginRegistry) -> None:
    """Set global plugin registry."""
    global _global_plugin_registry
    _global_plugin_registry = registry


# Import for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from runtime.base.runtime import Runtime