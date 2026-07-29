"""
AIPENSA Runtime Base - Core Runtime Abstraction

Defines the base Runtime class and interfaces that all runtime engines
(Agent, Conversation, Workflow, Scheduler, etc.) must implement.
"""

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Set, Type
import asyncio
import logging
import uuid

from runtime.base.module import RuntimeModule, ModuleMetadata, ModuleState, ModuleRegistry
from runtime.base.plugin import RuntimePlugin, PluginMetadata, PluginStatus, PluginRegistry
from runtime.base.factory import ModuleFactory, PluginFactory
from runtime.base.events import RuntimeEvent, RuntimeEventType, RuntimeEventBus
from runtime.base.di import RuntimeContainer
from runtime.base.registry import RuntimeRegistry

logger = logging.getLogger(__name__)


class RuntimeStatus(Enum):
    """Runtime lifecycle status."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    MAINTENANCE = "maintenance"


@dataclass
class RuntimeConfig:
    """Base configuration for all runtimes."""

    # Runtime identity
    runtime_id: str = ""
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    runtime_type: str = "base"

    # Module configuration
    modules: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    module_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Plugin configuration
    plugins: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    plugin_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Feature flags
    features: Dict[str, bool] = field(default_factory=dict)

    # Resource limits
    max_concurrent_tasks: int = 100
    max_memory_mb: int = 2048
    max_cpu_percent: float = 80.0
    task_timeout_seconds: int = 3600

    # Observability
    log_level: str = "INFO"
    enable_metrics: bool = True
    enable_tracing: bool = True
    enable_event_logging: bool = True

    # Security
    sandbox_enabled: bool = True
    allowed_operations: List[str] = field(default_factory=list)
    blocked_operations: List[str] = field(default_factory=lambda: [
        "rm -rf /", "sudo", "chmod 777", "format c:"
    ])

    def __post_init__(self):
        if not self.runtime_id:
            self.runtime_id = str(uuid.uuid4())[:8]
        if not self.name:
            self.name = f"{self.runtime_type}-runtime-{self.runtime_id}"


@dataclass
class RuntimeInfo:
    """Runtime information for monitoring and discovery."""

    runtime_id: str
    name: str
    version: str
    runtime_type: str
    status: RuntimeStatus
    description: str = ""
    started_at: Optional[datetime] = None
    uptime_seconds: float = 0
    modules: Dict[str, ModuleState] = field(default_factory=dict)
    plugins: Dict[str, PluginStatus] = field(default_factory=dict)
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Runtime(ABC):
    """
    Base Runtime class for all AIPENSA Runtime engines.

    All runtimes must implement this interface to ensure consistent
    lifecycle management, module/plugin loading, and event-driven communication.

    Architecture:
    - Each runtime is a self-contained execution engine
    - Modules provide core capabilities (local, cloud, hybrid)
    - Plugins extend functionality (tools, adapters, integrations)
    - Events enable observability and inter-runtime communication
    - DI Container manages dependencies and lifecycles
    """

    def __init__(
        self,
        config: Optional[RuntimeConfig] = None,
        container: Optional[RuntimeContainer] = None,
        event_bus: Optional[RuntimeEventBus] = None,
        module_registry: Optional[ModuleRegistry] = None,
        plugin_registry: Optional[PluginRegistry] = None,
    ):
        self.config = config or RuntimeConfig()
        self._container = container or RuntimeContainer()
        self._event_bus = event_bus or RuntimeEventBus()
        self._module_registry = module_registry or ModuleRegistry()
        self._plugin_registry = plugin_registry or PluginRegistry()

        # Runtime state
        self._status = RuntimeStatus.STOPPED
        self._started_at: Optional[datetime] = None
        self._modules: Dict[str, RuntimeModule] = {}
        self._plugins: Dict[str, RuntimePlugin] = {}
        self._module_factories: Dict[str, "ModuleFactory"] = {}
        self._plugin_factories: Dict[str, "PluginFactory"] = {}

        # Setup DI
        self._setup_container()

        # Register built-in modules
        self._register_builtin_modules()

    @property
    def status(self) -> RuntimeStatus:
        return self._status

    @property
    def runtime_id(self) -> str:
        return self.config.runtime_id

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def runtime_type(self) -> str:
        return self.config.runtime_type

    @property
    def container(self) -> RuntimeContainer:
        return self._container

    @property
    def event_bus(self) -> RuntimeEventBus:
        return self._event_bus

    @property
    def module_registry(self) -> ModuleRegistry:
        return self._module_registry

    @property
    def plugin_registry(self) -> PluginRegistry:
        return self._plugin_registry

    @property
    def modules(self) -> Dict[str, RuntimeModule]:
        return self._modules.copy()

    @property
    def plugins(self) -> Dict[str, RuntimePlugin]:
        return self._plugins.copy()

    # =============================================
    # Lifecycle Management
    # =============================================

    async def start(self) -> None:
        """Start the runtime and all loaded modules/plugins."""
        if self._status != RuntimeStatus.STOPPED:
            logger.warning(f"Runtime {self.name} already {self._status.value}")
            return

        self._status = RuntimeStatus.STARTING
        self._started_at = datetime.utcnow()
        logger.info(f"Starting runtime: {self.name}")

        try:
            # Start event bus
            await self._event_bus.start()

            # Publish startup event
            await self._publish_event(RuntimeEvent(
                event_type=RuntimeEventType.RUNTIME_STARTED,
                source=self.name,
                payload={"runtime_id": self.runtime_id, "runtime_type": self.runtime_type}
            ))

            # Initialize modules from config
            await self._initialize_modules()

            # Load plugins from config
            await self._load_plugins()

            # Start all modules
            await self._start_modules()

            # Start all plugins
            await self._start_plugins()

            self._status = RuntimeStatus.RUNNING
            logger.info(f"Runtime {self.name} started successfully")

            # Publish ready event
            await self._publish_event(RuntimeEvent(
                event_type=RuntimeEventType.RUNTIME_READY,
                source=self.name,
                payload={"runtime_id": self.runtime_id, "modules": list(self._modules.keys())}
            ))

        except Exception as e:
            self._status = RuntimeStatus.ERROR
            logger.error(f"Failed to start runtime {self.name}: {e}")
            await self._publish_event(RuntimeEvent(
                event_type=RuntimeEventType.RUNTIME_ERROR,
                source=self.name,
                payload={"error": str(e)}
            ))
            raise

    async def stop(self, graceful: bool = True) -> None:
        """Stop the runtime gracefully."""
        if self._status == RuntimeStatus.STOPPED:
            return

        self._status = RuntimeStatus.STOPPING
        logger.info(f"Stopping runtime: {self.name}")

        try:
            # Stop plugins
            await self._stop_plugins()

            # Stop modules
            await self._stop_modules()

            # Stop event bus
            await self._event_bus.stop()

            self._status = RuntimeStatus.STOPPED
            self._started_at = None
            logger.info(f"Runtime {self.name} stopped")

            await self._publish_event(RuntimeEvent(
                event_type=RuntimeEventType.RUNTIME_STOPPED,
                source=self.name,
                payload={"runtime_id": self.runtime_id}
            ))

        except Exception as e:
            self._status = RuntimeStatus.ERROR
            logger.error(f"Error stopping runtime {self.name}: {e}")
            if not graceful:
                raise

    async def restart(self) -> None:
        """Restart the runtime."""
        await self.stop()
        await self.start()

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on runtime and all modules."""
        module_health = {}
        for name, module in self._modules.items():
            try:
                module_health[name] = await module.health_check()
            except Exception as e:
                module_health[name] = {"healthy": False, "error": str(e)}

        plugin_health = {}
        for name, plugin in self._plugins.items():
            try:
                plugin_health[name] = await plugin.health_check()
            except Exception as e:
                plugin_health[name] = {"healthy": False, "error": str(e)}

        healthy = all(
            h.get("healthy", False) for h in module_health.values()
        ) and all(
            h.get("healthy", False) for h in plugin_health.values()
        )

        return {
            "runtime": self.name,
            "status": self._status.value,
            "healthy": healthy,
            "uptime_seconds": self._get_uptime(),
            "modules": module_health,
            "plugins": plugin_health,
            "resource_usage": await self._get_resource_usage(),
        }

    def get_info(self) -> RuntimeInfo:
        """Get runtime information."""
        return RuntimeInfo(
            runtime_id=self.runtime_id,
            name=self.name,
            version=self.config.version,
            runtime_type=self.runtime_type,
            status=self._status,
            description=self.config.description,
            started_at=self._started_at,
            uptime_seconds=self._get_uptime(),
            modules={name: m.state for name, m in self._modules.items()},
            plugins={name: p.status for name, p in self._plugins.items()},
            resource_usage=asyncio.run(self._get_resource_usage()) if self._status == RuntimeStatus.RUNNING else {},
        )

    # =============================================
    # Module Management
    # =============================================

    @abstractmethod
    def _register_builtin_modules(self) -> None:
        """Register built-in module factories. Must be implemented by subclasses."""
        pass

    def register_module_factory(self, name: str, factory: "ModuleFactory") -> None:
        """Register a module factory."""
        self._module_factories[name] = factory
        logger.debug(f"Registered module factory: {name}")

    def register_plugin_factory(self, name: str, factory: "PluginFactory") -> None:
        """Register a plugin factory."""
        self._plugin_factories[name] = factory
        logger.debug(f"Registered plugin factory: {name}")

    async def _initialize_modules(self) -> None:
        """Initialize modules from configuration."""
        for module_name, module_config in self.config.modules.items():
            if not module_config.get("enabled", True):
                logger.info(f"Module {module_name} disabled, skipping")
                continue

            try:
                await self.initialize_module(module_name, module_config)
            except Exception as e:
                logger.error(f"Failed to initialize module {module_name}: {e}")
                if module_config.get("required", False):
                    raise

    async def initialize_module(
        self,
        name: str,
        config: Dict[str, Any]
    ) -> RuntimeModule:
        """Initialize a single module by name."""
        if name in self._modules:
            logger.warning(f"Module {name} already initialized")
            return self._modules[name]

        # Try factory first
        factory = self._module_factories.get(name)
        if factory:
            module = factory.create(config)
        else:
            # Try registry
            module_class = self._module_registry.get_module(name)
            if module_class:
                module = module_class(config)
            else:
                raise ValueError(f"No module implementation found for: {name}")

        # Initialize module with runtime reference
        await module.initialize(self, config)
        self._modules[name] = module
        logger.info(f"Initialized module: {name}")
        return module

    async def _start_modules(self) -> None:
        """Start all initialized modules."""
        for name, module in self._modules.items():
            try:
                await module.start()
                logger.info(f"Started module: {name}")
            except Exception as e:
                logger.error(f"Failed to start module {name}: {e}")
                raise

    async def _stop_modules(self) -> None:
        """Stop all modules in reverse order."""
        for name in reversed(list(self._modules.keys())):
            module = self._modules[name]
            try:
                await module.stop()
                logger.info(f"Stopped module: {name}")
            except Exception as e:
                logger.error(f"Error stopping module {name}: {e}")

    def get_module(self, name: str) -> Optional[RuntimeModule]:
        """Get a module by name."""
        return self._modules.get(name)

    def get_module_required(self, name: str) -> RuntimeModule:
        """Get a module by name, raise if not found."""
        module = self._modules.get(name)
        if not module:
            raise ValueError(f"Module not found: {name}")
        return module

    # =============================================
    # Plugin Management
    # =============================================

    async def _load_plugins(self) -> None:
        """Load plugins from configuration."""
        for plugin_name, plugin_config in self.config.plugins.items():
            if not plugin_config.get("enabled", True):
                logger.info(f"Plugin {plugin_name} disabled, skipping")
                continue

            try:
                await self.load_plugin(plugin_name, plugin_config)
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin_name}: {e}")
                if plugin_config.get("required", False):
                    raise

    async def load_plugin(
        self,
        name: str,
        config: Dict[str, Any]
    ) -> RuntimePlugin:
        """Load a single plugin by name."""
        if name in self._plugins:
            logger.warning(f"Plugin {name} already loaded")
            return self._plugins[name]

        # Try factory first
        factory = self._plugin_factories.get(name)
        if factory:
            plugin = factory.create(config)
        else:
            # Try registry
            plugin_class = self._plugin_registry.get_plugin(name)
            if plugin_class:
                plugin = plugin_class(config)
            else:
                raise ValueError(f"No plugin implementation found for: {name}")

        # Initialize plugin
        await plugin.initialize(self, config)
        self._plugins[name] = plugin
        logger.info(f"Loaded plugin: {name}")
        return plugin

    async def _start_plugins(self) -> None:
        """Start all loaded plugins."""
        for name, plugin in self._plugins.items():
            try:
                await plugin.start()
                logger.info(f"Started plugin: {name}")
            except Exception as e:
                logger.error(f"Failed to start plugin {name}: {e}")
                raise

    async def _stop_plugins(self) -> None:
        """Stop all plugins."""
        for name in reversed(list(self._plugins.keys())):
            plugin = self._plugins[name]
            try:
                await plugin.stop()
                logger.info(f"Stopped plugin: {name}")
            except Exception as e:
                logger.error(f"Error stopping plugin {name}: {e}")

    def get_plugin(self, name: str) -> Optional[RuntimePlugin]:
        """Get a plugin by name."""
        return self._plugins.get(name)

    def get_plugin_required(self, name: str) -> RuntimePlugin:
        """Get a plugin by name, raise if not found."""
        plugin = self._plugins.get(name)
        if not plugin:
            raise ValueError(f"Plugin not found: {name}")
        return plugin

    # =============================================
    # Event Management
    # =============================================

    async def _publish_event(self, event: RuntimeEvent) -> None:
        """Publish an event to the event bus."""
        if self._event_bus:
            await self._event_bus.publish(event)

    def subscribe(
        self,
        event_type: RuntimeEventType,
        handler: callable
    ) -> None:
        """Subscribe to an event type."""
        self._event_bus.subscribe(event_type, handler)

    def unsubscribe(
        self,
        event_type: RuntimeEventType,
        handler: callable
    ) -> None:
        """Unsubscribe from an event type."""
        self._event_bus.unsubscribe(event_type, handler)

    # =============================================
    # Dependency Injection
    # =============================================

    def _setup_container(self) -> None:
        """Setup dependency injection container."""
        # Register core services
        self._container.register_instance(Runtime, self)
        self._container.register_instance(RuntimeEventBus, self._event_bus)
        self._container.register_instance(ModuleRegistry, self._module_registry)
        self._container.register_instance(PluginRegistry, self._plugin_registry)

    def resolve(self, service_type: Type) -> Any:
        """Resolve a service from the container."""
        return self._container.resolve(service_type)

    def resolve_optional(self, service_type: Type) -> Optional[Any]:
        """Resolve a service, return None if not found."""
        return self._container.resolve_optional(service_type)

    # =============================================
    # Helpers
    # =============================================

    def _get_uptime(self) -> float:
        """Get runtime uptime in seconds."""
        if self._started_at:
            return (datetime.utcnow() - self._started_at).total_seconds()
        return 0.0

    async def _get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage."""
        try:
            import psutil
            process = psutil.Process()
            return {
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "cpu_percent": process.cpu_percent(),
                "threads": process.num_threads(),
            }
        except ImportError:
            return {"memory_mb": 0, "cpu_percent": 0, "threads": 0}

    # =============================================
    # Context Manager
    # =============================================

    async def __aenter__(self) -> "Runtime":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()


# Convenience factory base classes
class ModuleFactory(ABC):
    """Base class for module factories."""

    @abstractmethod
    def create(self, config: Dict[str, Any]) -> RuntimeModule:
        """Create a module instance."""
        pass

    @property
    @abstractmethod
    def module_type(self) -> str:
        """Module type identifier."""
        pass


class PluginFactory(ABC):
    """Base class for plugin factories."""

    @abstractmethod
    def create(self, config: Dict[str, Any]) -> RuntimePlugin:
        """Create a plugin instance."""
        pass

    @property
    @abstractmethod
    def plugin_type(self) -> str:
        """Plugin type identifier."""
        pass