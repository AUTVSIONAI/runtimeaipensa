"""
Plugin System for AIPENSA Runtime

Provides a flexible plugin architecture for extending runtime capabilities.
Every tool, MCP, runtime, browser, and integration is a plugin.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type
import importlib
import inspect
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class PluginType(Enum):
    """Types of plugins supported by the runtime."""

    TOOL = "tool"
    MCP = "mcp"
    BROWSER = "browser"
    RUNTIME = "runtime"
    SANDBOX = "sandbox"
    MEMORY = "memory"
    LLM = "llm"
    AUTH = "auth"
    STORAGE = "storage"
    NETWORK = "network"
    CUSTOM = "custom"


class PluginStatus(Enum):
    """Plugin lifecycle status."""

    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    ACTIVE = "active"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class PluginMetadata:
    """Metadata describing a plugin."""

    name: str
    version: str
    description: str
    author: str = ""
    license: str = "MIT"
    plugin_type: PluginType = PluginType.CUSTOM
    dependencies: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)  # Services/exports provided
    requires: List[str] = field(default_factory=list)  # Services required
    tags: Set[str] = field(default_factory=set)
    entry_point: str = ""  # Module:Class or function path
    config_schema: Dict[str, Any] = field(default_factory=dict)
    min_runtime_version: str = "1.0.0"
    max_runtime_version: str = ""


@dataclass
class PluginInstance:
    """Runtime instance of a plugin."""

    metadata: PluginMetadata
    instance: Any = None
    status: PluginStatus = PluginStatus.UNLOADED
    config: Dict[str, Any] = field(default_factory=dict)
    loaded_at: Optional[datetime] = None
    initialized_at: Optional[datetime] = None
    error: Optional[str] = None


class Plugin(ABC):
    """
    Base class for all plugins.

    Plugins must implement lifecycle methods and declare their metadata.
    """

    metadata: PluginMetadata

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._initialized = False

    @classmethod
    def get_metadata(cls) -> PluginMetadata:
        """Get plugin metadata. Must be implemented by subclasses."""
        raise NotImplementedError

    @abstractmethod
    async def initialize(self, runtime: "Runtime") -> None:
        """Initialize the plugin with runtime reference."""
        pass

    @abstractmethod
    async def start(self) -> None:
        """Start the plugin (activate subscriptions, connections, etc.)."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the plugin gracefully."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources."""
        pass

    def validate_config(self) -> bool:
        """Validate plugin configuration. Override for custom validation."""
        return True


class PluginRegistry:
    """
    Registry for discovering and managing plugin metadata.
    """

    def __init__(self):
        self._plugins: Dict[str, PluginMetadata] = {}
        self._entry_points: Dict[str, str] = {}

    def register(self, metadata: PluginMetadata, entry_point: str) -> None:
        """Register a plugin metadata with its entry point."""
        self._plugins[metadata.name] = metadata
        self._entry_points[metadata.name] = entry_point
        logger.debug(f"Registered plugin: {metadata.name} v{metadata.version}")

    def unregister(self, name: str) -> bool:
        """Unregister a plugin."""
        if name in self._plugins:
            del self._plugins[name]
            del self._entry_points[name]
            return True
        return False

    def get(self, name: str) -> Optional[PluginMetadata]:
        """Get plugin metadata by name."""
        return self._plugins.get(name)

    def get_all(self) -> List[PluginMetadata]:
        """Get all registered plugin metadata."""
        return list(self._plugins.values())

    def get_by_type(self, plugin_type: PluginType) -> List[PluginMetadata]:
        """Get plugins filtered by type."""
        return [m for m in self._plugins.values() if m.plugin_type == plugin_type]

    def get_entry_point(self, name: str) -> Optional[str]:
        """Get entry point for a plugin."""
        return self._entry_points.get(name)

    def discover_plugins(self, package_path: str) -> List[PluginMetadata]:
        """Discover plugins in a Python package."""
        discovered = []
        try:
            package = importlib.import_module(package_path)
            package_dir = Path(package.__file__).parent

            for py_file in package_dir.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                module_name = f"{package_path}.{py_file.stem}"
                try:
                    module = importlib.import_module(module_name)
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and issubclass(obj, Plugin) and obj != Plugin:
                            metadata = obj.get_metadata()
                            self.register(metadata, f"{module_name}:{name}")
                            discovered.append(metadata)
                except Exception as e:
                    logger.warning(f"Failed to load plugin module {module_name}: {e}")

        except Exception as e:
            logger.error(f"Failed to discover plugins in {package_path}: {e}")

        return discovered


class PluginManager:
    """
    Manages plugin lifecycle: loading, initialization, starting, stopping.
    """

    def __init__(self, registry: Optional[PluginRegistry] = None):
        self.registry = registry or PluginRegistry()
        self._instances: Dict[str, PluginInstance] = {}
        self._load_order: List[str] = []
        self._runtime = None

    def set_runtime(self, runtime: "Runtime") -> None:
        """Set the runtime reference for plugins."""
        self._runtime = runtime

    async def load_plugin(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None,
        entry_point: Optional[str] = None
    ) -> PluginInstance:
        """Load and instantiate a plugin."""
        if name in self._instances:
            logger.warning(f"Plugin {name} already loaded")
            return self._instances[name]

        # Get metadata
        metadata = self.registry.get(name)
        if not metadata:
            if entry_point:
                # Try to load from entry point
                metadata = await self._load_from_entry_point(name, entry_point)
            else:
                # Try to find entry point
                entry_point = self.registry.get_entry_point(name)
                if entry_point:
                    metadata = await self._load_from_entry_point(name, entry_point)

        if not metadata:
            raise ValueError(f"Plugin {name} not found in registry")

        # Check dependencies
        for dep in metadata.dependencies:
            if dep not in self._instances:
                raise ValueError(f"Plugin {name} requires dependency {dep} which is not loaded")

        # Create instance
        plugin_cls = await self._load_plugin_class(metadata, entry_point)
        instance = plugin_cls(config=config or {})

        plugin_instance = PluginInstance(
            metadata=metadata,
            instance=instance,
            config=config or {},
            status=PluginStatus.LOADING,
            loaded_at=datetime.utcnow(),
        )

        self._instances[name] = plugin_instance
        logger.info(f"Loaded plugin: {name} v{metadata.version}")

        return plugin_instance

    async def _load_from_entry_point(self, name: str, entry_point: str) -> Optional[PluginMetadata]:
        """Load plugin metadata from entry point string."""
        try:
            module_path, class_name = entry_point.split(":")
            module = importlib.import_module(module_path)
            plugin_cls = getattr(module, class_name)
            metadata = plugin_cls.get_metadata()
            self.registry.register(metadata, entry_point)
            return metadata
        except Exception as e:
            logger.error(f"Failed to load plugin from entry point {entry_point}: {e}")
            return None

    async def _load_plugin_class(self, metadata: PluginMetadata, entry_point: Optional[str] = None) -> Type[Plugin]:
        """Load the plugin class."""
        if entry_point:
            module_path, class_name = entry_point.split(":")
        else:
            ep = self.registry.get_entry_point(metadata.name)
            if not ep:
                raise ValueError(f"No entry point for plugin {metadata.name}")
            module_path, class_name = ep.split(":")

        module = importlib.import_module(module_path)
        return getattr(module, class_name)

    async def initialize_plugin(self, name: str) -> None:
        """Initialize a loaded plugin."""
        instance = self._instances.get(name)
        if not instance:
            raise ValueError(f"Plugin {name} not loaded")

        if instance.status in (PluginStatus.INITIALIZED, PluginStatus.ACTIVE):
            return

        instance.status = PluginStatus.INITIALIZING
        try:
            if not instance.instance.validate_config():
                raise ValueError(f"Plugin {name} configuration validation failed")

            if self._runtime:
                await instance.instance.initialize(self._runtime)
            else:
                await instance.instance.initialize(None)

            instance.status = PluginStatus.INITIALIZED
            instance.initialized_at = datetime.utcnow()
            logger.info(f"Initialized plugin: {name}")

        except Exception as e:
            instance.status = PluginStatus.ERROR
            instance.error = str(e)
            logger.error(f"Failed to initialize plugin {name}: {e}")
            raise

    async def start_plugin(self, name: str) -> None:
        """Start a plugin."""
        instance = self._instances.get(name)
        if not instance:
            raise ValueError(f"Plugin {name} not loaded")

        if instance.status == PluginStatus.ACTIVE:
            return

        instance.status = PluginStatus.ACTIVE
        try:
            await instance.instance.start()
            logger.info(f"Started plugin: {name}")
        except Exception as e:
            instance.status = PluginStatus.ERROR
            instance.error = str(e)
            logger.error(f"Failed to start plugin {name}: {e}")
            raise

    async def stop_plugin(self, name: str) -> None:
        """Stop a plugin."""
        instance = self._instances.get(name)
        if not instance:
            return

        if instance.status not in (PluginStatus.ACTIVE, PluginStatus.INITIALIZED):
            return

        instance.status = PluginStatus.STOPPING
        try:
            await instance.instance.stop()
            instance.status = PluginStatus.STOPPED
            logger.info(f"Stopped plugin: {name}")
        except Exception as e:
            instance.status = PluginStatus.ERROR
            instance.error = str(e)
            logger.error(f"Failed to stop plugin {name}: {e}")
            raise

    async def cleanup_plugin(self, name: str) -> None:
        """Clean up a plugin."""
        instance = self._instances.get(name)
        if not instance:
            return

        try:
            await instance.instance.cleanup()
            del self._instances[name]
            logger.info(f"Cleaned up plugin: {name}")
        except Exception as e:
            logger.error(f"Failed to cleanup plugin {name}: {e}")

    async def load_and_initialize(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None,
        entry_point: Optional[str] = None
    ) -> PluginInstance:
        """Load, initialize, and start a plugin in one call."""
        instance = await self.load_plugin(name, config, entry_point)
        await self.initialize_plugin(name)
        await self.start_plugin(name)
        return instance

    async def shutdown_all(self) -> None:
        """Shutdown all plugins in reverse order."""
        for name in reversed(self._load_order):
            if name in self._instances:
                await self.stop_plugin(name)
                await self.cleanup_plugin(name)

    def get_instance(self, name: str) -> Optional[PluginInstance]:
        """Get plugin instance by name."""
        return self._instances.get(name)

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get plugin instance object by name."""
        inst = self._instances.get(name)
        return inst.instance if inst else None

    def get_all_instances(self) -> Dict[str, PluginInstance]:
        """Get all plugin instances."""
        return self._instances.copy()

    def get_active_plugins(self, plugin_type: Optional[PluginType] = None) -> List[Plugin]:
        """Get all active plugins, optionally filtered by type."""
        plugins = [
            inst.instance for inst in self._instances.values()
            if inst.status == PluginStatus.ACTIVE
        ]
        if plugin_type:
            plugins = [p for p in plugins if p.metadata.plugin_type == plugin_type]
        return plugins


# Convenience function for creating event handlers
def event_handler(*event_types: str, priority: PluginType = PluginType.CUSTOM):
    """Decorator to create event handlers."""
    # Note: This is a simplified version - full implementation would use EventPriority
    def decorator(func: Callable[[Event], Any]) -> Plugin:
        class _DecoratedHandler(Plugin):
            metadata = PluginMetadata(
                name=func.__name__,
                version="1.0.0",
                description=f"Event handler for {func.__name__}",
                plugin_type=PluginType.CUSTOM
            )

            async def initialize(self, runtime: "Runtime") -> None:
                pass

            async def start(self) -> None:
                pass

            async def stop(self) -> None:
                pass

            async def cleanup(self) -> None:
                pass

            async def handle(self, event: Event) -> None:
                await func(event)

            @property
            def handles_event_types(self) -> List[str]:
                return list(event_types)

        return _DecoratedHandler()
    return decorator


# Placeholder for the Runtime type
class Runtime:
    pass


__all__ = [
    "PluginType",
    "PluginStatus",
    "PluginMetadata",
    "PluginInstance",
    "Plugin",
    "PluginRegistry",
    "PluginManager",
    "event_handler",
    "Runtime",
]