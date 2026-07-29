"""
AIPENSA Runtime Base - Runtime Factory

Factories for creating complete Runtime instances with configured modules and plugins.
Placed here to avoid circular imports with the factory module.
"""

from typing import Any, Dict, List, Optional, Type
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runtime.base.module import RuntimeModule, ModuleMetadata
    from runtime.base.plugin import RuntimePlugin, PluginMetadata
    from runtime.base.events import RuntimeEvent, RuntimeEventType, RuntimeEventBus
    from runtime.base.di import RuntimeContainer
    from runtime.base.registry import ModuleRegistry, PluginRegistry
    from runtime.base.runtime import Runtime, RuntimeConfig
    from runtime.base.factory import ModuleFactory, PluginFactory, FactoryConfig
else:
    from runtime.base.module import RuntimeModule
    from runtime.base.plugin import RuntimePlugin
    from runtime.base.factory import ModuleFactory, PluginFactory, FactoryConfig
    from runtime.base.runtime import Runtime, RuntimeConfig

logger = logging.getLogger(__name__)


class RuntimeFactory:
    """
    Factory for creating complete Runtime instances with
    configured modules and plugins.
    """

    def __init__(self, config: Optional[FactoryConfig] = None):
        self.config = config or FactoryConfig()
        self._module_factories: Dict[str, ModuleFactory] = {}
        self._plugin_factories: Dict[str, PluginFactory] = {}
        self._runtime_cache: Dict[str, Runtime] = {}

    def register_module_factory(self, factory: ModuleFactory) -> None:
        """Register a module factory."""
        self._module_factories[factory.module_type] = factory
        logger.debug(f"Registered module factory: {factory.module_type}")

    def register_plugin_factory(self, factory: PluginFactory) -> None:
        """Register a plugin factory."""
        self._plugin_factories[factory.plugin_type] = factory
        logger.debug(f"Registered plugin factory: {factory.plugin_type}")

    def get_module_factory(self, module_type: str) -> Optional[ModuleFactory]:
        """Get module factory by type."""
        return self._module_factories.get(module_type)

    def get_plugin_factory(self, plugin_type: str) -> Optional[PluginFactory]:
        """Get plugin factory by type."""
        return self._plugin_factories.get(plugin_type)

    async def create_runtime(
        self,
        config: Optional[RuntimeConfig] = None,
        modules: Optional[List[str]] = None,
        plugins: Optional[List[str]] = None
    ) -> Runtime:
        """
        Create a fully configured runtime instance.

        Args:
            config: Runtime configuration
            modules: List of module names to load
            plugins: List of plugin names to load

        Returns:
            Started runtime instance
        """
        if config is None:
            config = RuntimeConfig()

        # Create runtime instance
        runtime = Runtime(config)

        # Load modules
        if modules:
            for module_name in modules:
                await self._load_module(runtime, module_name)

        # Load plugins
        if plugins:
            for plugin_name in plugins:
                await self._load_plugin(runtime, plugin_name)

        return runtime

    async def _load_module(
        self,
        runtime: Runtime,
        module_name: str
    ) -> RuntimeModule:
        """Load a module into the runtime."""
        # Find factory that can create this module
        for factory in self._module_factories.values():
            if module_name in factory.get_available_modules():
                module = await factory.create(module_name, runtime=runtime)
                await module.initialize(runtime, {})
                await module.start()
                return module

        raise ValueError(f"No factory found for module: {module_name}")

    async def _load_plugin(
        self,
        runtime: Runtime,
        plugin_name: str
    ) -> RuntimePlugin:
        """Load a plugin into the runtime."""
        # Find factory that can create this plugin
        for factory in self._plugin_factories.values():
            if plugin_name in factory.get_available_plugins():
                plugin = await factory.create(plugin_name, runtime=runtime)
                await plugin.initialize(runtime, {})
                await plugin.start()
                return plugin

        raise ValueError(f"No factory found for plugin: {plugin_name}")