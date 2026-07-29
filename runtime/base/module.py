"""
AIPENSA Runtime Base - Module Abstraction

Defines the base module interface and lifecycle that all runtime modules
must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Type
import logging

from runtime.base.events import RuntimeEvent, RuntimeEventType, create_event

logger = logging.getLogger(__name__)


class ModuleState(Enum):
    """Module lifecycle state."""

    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ModuleMetadata:
    """Module metadata for discovery and registration."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    module_type: str = "module"
    dependencies: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)
    requires: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    min_runtime_version: str = "1.0.0"
    max_runtime_version: str = ""


@dataclass
class ModuleContext:
    """Context passed to modules during initialization."""

    runtime: "Runtime"
    config: Dict[str, Any]
    logger: logging.Logger


class RuntimeModule(ABC):
    """
    Base class for all runtime modules.

    Modules are the core building blocks of a runtime, providing
    specific capabilities like browser automation, code execution,
    memory storage, etc.

    Lifecycle:
    1. __init__(config) - Construction with config
    2. initialize(runtime, config) - Setup with runtime reference
    3. start() - Begin operations (connections, subscriptions)
    4. stop() - Graceful shutdown
    5. cleanup() - Release resources
    6. health_check() - Return health status
    """

    metadata: ModuleMetadata

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._runtime: Optional["Runtime"] = None
        self._state = ModuleState.UNINITIALIZED
        self._started_at: Optional[datetime] = None
        self._logger = logging.getLogger(f"runtime.module.{self.metadata.name}")

    @property
    def state(self) -> ModuleState:
        return self._state

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
        Initialize the module with runtime reference and configuration.

        Called once during module loading.
        """
        self._runtime = runtime
        self._state = ModuleState.INITIALIZED
        if self._runtime and hasattr(self._runtime, 'event_bus'):
            from runtime.base.events import create_event, RuntimeEventType
            await self._runtime.event_bus.publish(create_event(
                event_type=RuntimeEventType.MODULE_INITIALIZED,
                source=self.name,
                payload={"module_name": self.name, "state": "initialized"}
            ))
        self._logger.info(f"Module {self.name} initialized")

    @abstractmethod
    async def start(self) -> None:
        """
        Start module operations.

        Should establish connections, start background tasks,
        subscribe to events, etc.
        """
        self._state = ModuleState.RUNNING
        self._started_at = datetime.utcnow()
        if self._runtime and hasattr(self._runtime, 'event_bus'):
            from runtime.base.events import create_event, RuntimeEventType
            await self._runtime.event_bus.publish(create_event(
                event_type=RuntimeEventType.MODULE_STARTED,
                source=self.name,
                payload={"module_name": self.name, "state": "running"}
            ))
        self._logger.info(f"Module {self.name} started")

    @abstractmethod
    async def stop(self) -> None:
        """
        Stop module operations gracefully.

        Should close connections, cancel background tasks,
        unsubscribe from events, etc.
        """
        self._state = ModuleState.STOPPED
        if self._runtime and hasattr(self._runtime, 'event_bus'):
            from runtime.base.events import create_event, RuntimeEventType
            await self._runtime.event_bus.publish(create_event(
                event_type=RuntimeEventType.MODULE_STOPPED,
                source=self.name,
                payload={"module_name": self.name, "state": "stopped"}
            ))
        self._logger.info(f"Module {self.name} stopped")

    @abstractmethod
    async def cleanup(self) -> None:
        """
        Clean up all resources.

        Called during runtime shutdown.
        """
        self._state = ModuleState.UNINITIALIZED
        if self._runtime and hasattr(self._runtime, 'event_bus'):
            from runtime.base.events import create_event, RuntimeEventType
            await self._runtime.event_bus.publish(create_event(
                event_type=RuntimeEventType.MODULE_STOPPED,
                source=self.name,
                payload={"module_name": self.name, "state": "uninitialized"}
            ))
        self._runtime = None
        self._started_at = None
        self._logger.info(f"Module {self.name} cleaned up")

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Return health status of the module.

        Should return dict with at least:
        - healthy: bool
        - state: str
        - details: dict (optional)
        """
        return {
            "module": self.name,
            "healthy": self._state == ModuleState.RUNNING,
            "state": self._state.value,
            "uptime_seconds": self.uptime_seconds,
        }

    # =============================================
    # Optional Methods (can be overridden)
    # =============================================

    async def on_event(self, event: "RuntimeEvent") -> None:
        """
        Handle runtime events.

        Override to react to events from other modules/plugins.
        """
        pass

    def validate_config(self) -> bool:
        """
        Validate module configuration.

        Override for custom validation logic.
        """
        return True

    def get_capabilities(self) -> List[str]:
        """
        Return list of capabilities this module provides.

        Used for capability-based routing and discovery.
        """
        return self.metadata.provides.copy()

    async def execute(self, operation: str, **kwargs) -> Any:
        """
        Execute a module-specific operation.

        Generic execution interface for dynamic invocation.
        Override for module-specific operations.
        """
        raise NotImplementedError(
            f"Operation '{operation}' not supported by {self.name}"
        )


# Import Runtime for type hints
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from runtime.base.runtime import Runtime
    from runtime.base.events import RuntimeEvent


class ModuleRegistry:
    """Registry for module implementations."""

    def __init__(self):
        self._modules: Dict[str, Type[RuntimeModule]] = {}
        self._metadata: Dict[str, ModuleMetadata] = {}

    def register(self, module_class: Type[RuntimeModule]) -> None:
        """Register a module class."""
        metadata = module_class.metadata
        self._modules[metadata.name] = module_class
        self._metadata[metadata.name] = metadata
        logger.debug(f"Registered module: {metadata.name} v{metadata.version}")

    def unregister(self, name: str) -> bool:
        """Unregister a module."""
        if name in self._modules:
            del self._modules[name]
            del self._metadata[name]
            return True
        return False

    def get_module(self, name: str) -> Optional[Type[RuntimeModule]]:
        """Get module class by name."""
        return self._modules.get(name)

    def get_metadata(self, name: str) -> Optional[ModuleMetadata]:
        """Get module metadata by name."""
        return self._metadata.get(name)

    def list_modules(self) -> List[str]:
        """List all registered module names."""
        return list(self._modules.keys())

    def list_by_type(self, module_type: str) -> List[str]:
        """List modules by type."""
        return [
            name for name, meta in self._metadata.items()
            if meta.module_type == module_type
        ]

    def list_by_tag(self, tag: str) -> List[str]:
        """List modules by tag."""
        return [
            name for name, meta in self._metadata.items()
            if tag in meta.tags
        ]


# Global module registry instance
_global_module_registry: Optional[ModuleRegistry] = None


def get_module_registry() -> ModuleRegistry:
    """Get global module registry."""
    global _global_module_registry
    if _global_module_registry is None:
        _global_module_registry = ModuleRegistry()
    return _global_module_registry


def set_module_registry(registry: ModuleRegistry) -> None:
    """Set global module registry."""
    global _global_module_registry
    _global_module_registry = registry