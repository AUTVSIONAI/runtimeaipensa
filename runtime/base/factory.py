"""
AIPENSA Runtime Base - Factory Patterns

Provides factory abstractions for creating runtime instances,
modules, and plugins dynamically.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, TypeVar, Callable
import importlib
import inspect
import logging
import sys

from runtime.base.module import RuntimeModule, ModuleMetadata
from runtime.base.plugin import RuntimePlugin, PluginMetadata
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from runtime.base.runtime import Runtime, RuntimeConfig

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class FactoryConfig:
    """Configuration for factory operations."""

    auto_register: bool = True
    default_module_config: Dict[str, Any] = field(default_factory=dict)
    default_plugin_config: Dict[str, Any] = field(default_factory=dict)
    allowed_namespaces: List[str] = field(default_factory=lambda: ["runtime", "plugins"])


class ModuleFactory(ABC):
    """
    Factory for creating module instances.

    Each module type should have a factory that knows how to
    instantiate and configure the module.
    """

    def __init__(self, config: Optional[FactoryConfig] = None):
        self.config = config or FactoryConfig()
        self._module_cache: Dict[str, RuntimeModule] = {}

    @property
    @abstractmethod
    def module_type(self) -> str:
        """Return the module type this factory creates."""
        pass

    @abstractmethod
    async def create(
        self,
        module_name: str,
        config: Optional[Dict[str, Any]] = None,
        runtime: Optional["Runtime"] = None
    ) -> RuntimeModule:
        """
        Create and initialize a module instance.

        Args:
            module_name: Name of the module to create
            config: Module-specific configuration
            runtime: Runtime instance for initialization

        Returns:
            Initialized module instance
        """
        pass

    @abstractmethod
    def get_available_modules(self) -> List[str]:
        """Return list of available module names."""
        pass

    def get_module_class(self, module_name: str) -> Optional[Type[RuntimeModule]]:
        """Get module class by name."""
        # Default implementation - override in subclasses
        return None

    def get_metadata(self, module_name: str) -> Optional[ModuleMetadata]:
        """Get module metadata by name."""
        cls = self.get_module_class(module_name)
        if cls:
            return cls.metadata
        return None


class PluginFactory(ABC):
    """
    Factory for creating plugin instances.

    Each plugin type should have a factory that knows how to
    instantiate and configure the plugin.
    """

    def __init__(self, config: Optional[FactoryConfig] = None):
        self.config = config or FactoryConfig()
        self._plugin_cache: Dict[str, RuntimePlugin] = {}

    @property
    @abstractmethod
    def plugin_type(self) -> str:
        """Return the plugin type this factory creates."""
        pass

    @abstractmethod
    async def create(
        self,
        plugin_name: str,
        config: Optional[Dict[str, Any]] = None,
        runtime: Optional["Runtime"] = None
    ) -> RuntimePlugin:
        """
        Create and initialize a plugin instance.

        Args:
            plugin_name: Name of the plugin to create
            config: Plugin-specific configuration
            runtime: Runtime instance for initialization

        Returns:
            Initialized plugin instance
        """
        pass

    @abstractmethod
    def get_available_plugins(self) -> List[str]:
        """Return list of available plugin names."""
        pass

    def get_plugin_class(self, plugin_name: str) -> Optional[Type[RuntimePlugin]]:
        """Get plugin class by name."""
        return None

    def get_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """Get plugin metadata by name."""
        cls = self.get_plugin_class(plugin_name)
        if cls:
            return cls.metadata
        return None


class DynamicModuleFactory(ModuleFactory):
    """
    Dynamic module factory that discovers modules via entry points
    or module scanning.
    """

    def __init__(
        self,
        module_type: str,
        config: Optional[FactoryConfig] = None,
        search_paths: Optional[List[str]] = None
    ):
        super().__init__(config)
        self._module_type = module_type
        self._search_paths = search_paths or ["runtime.modules", "plugins.modules"]
        self._discovered_modules: Dict[str, Type[RuntimeModule]] = {}

    @property
    def module_type(self) -> str:
        return self._module_type

    def get_available_modules(self) -> List[str]:
        """Return list of available module names."""
        if not self._discovered_modules:
            self._discover_modules()
        return list(self._discovered_modules.keys())

    def get_module_class(self, module_name: str) -> Optional[Type[RuntimeModule]]:
        """Get module class by name."""
        if not self._discovered_modules:
            self._discover_modules()
        return self._discovered_modules.get(module_name)

    async def create(
        self,
        module_name: str,
        config: Optional[Dict[str, Any]] = None,
        runtime: Optional["Runtime"] = None
    ) -> RuntimeModule:
        """Create and initialize a module instance."""
        module_class = self.get_module_class(module_name)
        if not module_class:
            raise ValueError(f"Module not found: {module_name}")

        module = module_class(config or {})
        if runtime:
            await module.initialize(runtime, config or {})
            await module.start()

        return module

    def _discover_modules(self) -> None:
        """Discover modules in search paths."""
        for path in self._search_paths:
            try:
                module = importlib.import_module(path)
                self._scan_module(module)
            except ImportError:
                logger.debug(f"Could not import module search path: {path}")

    def _scan_module(self, module) -> None:
        """Scan a module for RuntimeModule subclasses."""
        for name, obj in inspect.getmembers(module):
            if (
                inspect.isclass(obj)
                and issubclass(obj, RuntimeModule)
                and obj != RuntimeModule
                and hasattr(obj, 'metadata')
            ):
                metadata = obj.metadata
                if metadata.module_type == self._module_type:
                    self._discovered_modules[metadata.name] = obj
                    logger.debug(f"Discovered module: {metadata.name}")


class DynamicPluginFactory(PluginFactory):
    """
    Dynamic plugin factory that discovers plugins via entry points
    or module scanning.
    """

    def __init__(
        self,
        plugin_type: str,
        config: Optional[FactoryConfig] = None,
        search_paths: Optional[List[str]] = None
    ):
        super().__init__(config)
        self._plugin_type = plugin_type
        self._search_paths = search_paths or ["runtime.plugins", "plugins"]
        self._discovered_plugins: Dict[str, Type[RuntimePlugin]] = {}

    @property
    def plugin_type(self) -> str:
        return self._plugin_type

    def get_available_plugins(self) -> List[str]:
        """Return list of available plugin names."""
        if not self._discovered_plugins:
            self._discover_plugins()
        return list(self._discovered_plugins.keys())

    def get_plugin_class(self, plugin_name: str) -> Optional[Type[RuntimePlugin]]:
        """Get plugin class by name."""
        if not self._discovered_plugins:
            self._discover_plugins()
        return self._discovered_plugins.get(plugin_name)

    async def create(
        self,
        plugin_name: str,
        config: Optional[Dict[str, Any]] = None,
        runtime: Optional["Runtime"] = None
    ) -> RuntimePlugin:
        """Create and initialize a plugin instance."""
        plugin_class = self.get_plugin_class(plugin_name)
        if not plugin_class:
            raise ValueError(f"Plugin not found: {plugin_name}")

        plugin = plugin_class(config or {})
        if runtime:
            await plugin.initialize(runtime, config or {})
            await plugin.start()

        return plugin

    def _discover_plugins(self) -> None:
        """Discover plugins in search paths."""
        for path in self._search_paths:
            try:
                module = importlib.import_module(path)
                self._scan_module(module)
            except ImportError:
                logger.debug(f"Could not import plugin search path: {path}")

    def _scan_module(self, module) -> None:
        """Scan a module for RuntimePlugin subclasses."""
        for name, obj in inspect.getmembers(module):
            if (
                inspect.isclass(obj)
                and issubclass(obj, RuntimePlugin)
                and obj != RuntimePlugin
                and hasattr(obj, 'metadata')
            ):
                metadata = obj.metadata
                if metadata.plugin_type.value == self._plugin_type:
                    self._discovered_plugins[metadata.name] = obj
                    logger.debug(f"Discovered plugin: {metadata.name}")


class CompositeFactory:
    """
    Composite factory that aggregates multiple module and plugin factories.
    """

    def __init__(self, config: Optional[FactoryConfig] = None):
        self.config = config or FactoryConfig()
        self.module_factories: List[ModuleFactory] = []
        self.plugin_factories: List[PluginFactory] = []

    def add_module_factory(self, factory: ModuleFactory) -> None:
        """Add a module factory."""
        self.module_factories.append(factory)

    def add_plugin_factory(self, factory: PluginFactory) -> None:
        """Add a plugin factory."""
        self.plugin_factories.append(factory)

    def get_available_modules(self) -> List[str]:
        """Get all available modules from all factories."""
        modules = []
        for factory in self.module_factories:
            modules.extend(factory.get_available_modules())
        return modules

    def get_available_plugins(self) -> List[str]:
        """Get all available plugins from all factories."""
        plugins = []
        for factory in self.plugin_factories:
            plugins.extend(factory.get_available_plugins())
        return plugins

    async def create_module(
        self,
        module_name: str,
        config: Optional[Dict[str, Any]] = None,
        runtime: Optional["Runtime"] = None
    ) -> RuntimeModule:
        """Create a module using the first factory that can create it."""
        for factory in self.module_factories:
            if module_name in factory.get_available_modules():
                return await factory.create(module_name, config, runtime)
        raise ValueError(f"No factory can create module: {module_name}")

    async def create_plugin(
        self,
        plugin_name: str,
        config: Optional[Dict[str, Any]] = None,
        runtime: Optional["Runtime"] = None
    ) -> RuntimePlugin:
        """Create a plugin using the first factory that can create it."""
        for factory in self.plugin_factories:
            if plugin_name in factory.get_available_plugins():
                return await factory.create(plugin_name, config, runtime)
        raise ValueError(f"No factory can create plugin: {plugin_name}")