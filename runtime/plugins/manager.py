"""
Plugin Manager with Auto-Discovery, Hot-Reload, and Dependency Resolution

Implements:
1. Filesystem auto-discovery from runtime/plugins/<type>/<name>/plugin.yaml
2. Pydantic schema validation for plugin.yaml manifests
3. Hot-reload with watchdog (dev mode only)
4. Dependency resolution with topological sort
"""

import os
import sys
import asyncio
import importlib.util
import importlib.machinery
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable, Awaitable, Union
from dataclasses import dataclass, field
from datetime import datetime
import logging
import yaml
from collections import defaultdict, deque

from runtime.plugins.base import (
    Plugin,
    PluginManager as BasePluginManager,
    PluginRegistry,
    PluginType,
    PluginStatus,
    PluginMetadata,
    PluginInstance,
    Runtime,
)
from runtime.plugins.schemas import (
    PluginManifest,
    PluginManifestSummary,
    PluginDependency,
    PluginType as SchemaPluginType,
    DependencyType,
    load_manifest,
    validate_manifest_dict,
)

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredPlugin:
    """Plugin discovered from filesystem."""
    manifest: PluginManifest
    plugin_dir: Path
    manifest_path: Path
    status: str = "discovered"  # discovered, loaded, initialized, active, error
    error: Optional[str] = None
    plugin_class: Optional[type] = None
    instance: Optional[Plugin] = None
    instance_wrapper: Optional[PluginInstance] = None


class TopologicalSorter:
    """Topological sort for plugin dependency resolution."""

    @staticmethod
    def sort(plugins: Dict[str, DiscoveredPlugin]) -> List[str]:
        """
        Sort plugins by dependencies using Kahn's algorithm.
        Returns list of plugin names in load order.
        """
        # Build adjacency list and in-degree count
        graph: Dict[str, Set[str]] = defaultdict(set)
        in_degree: Dict[str, int] = defaultdict(int)
        all_nodes = set(plugins.keys())

        for name, plugin in plugins.items():
            # Ensure node exists
            if name not in in_degree:
                in_degree[name] = 0

            for dep in plugin.manifest.dependencies:
                if dep.optional:
                    continue  # Skip optional dependencies for ordering

                dep_name = dep.plugin_name  # Get just the plugin name part
                # Only add to graph if dependency is another plugin in our registry
                if dep.type == DependencyType.PLUGIN and dep_name in all_nodes:
                    graph[dep_name].add(name)
                    in_degree[name] += 1
                # EXTERNAL dependencies (runtime:*, skill:*, python_package:*)
                # are NOT added to the dependency graph - they're outside our control
                # and shouldn't cause cycles

        # Find all nodes with zero in-degree
        queue = deque([n for n in all_nodes if in_degree[n] == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Check for cycles
        if len(result) != len(all_nodes):
            # Find cycle
            remaining = all_nodes - set(result)
            cycle_info = f"Cycle detected involving: {remaining}"
            raise ValueError(f"Dependency cycle detected: {cycle_info}")

        return result

    @staticmethod
    def validate_no_cycles(plugins: Dict[str, DiscoveredPlugin]) -> bool:
        """Check if dependency graph has cycles."""
        try:
            TopologicalSorter.sort(plugins)
            return True
        except ValueError:
            return False


class PluginWatcher:
    """File system watcher for hot-reload in development mode."""

    def __init__(self, plugin_manager: "EnhancedPluginManager", plugin_dirs: List[Path]):
        self.plugin_manager = plugin_manager
        self.plugin_dirs = plugin_dirs
        self.observer = None
        self._running = False
        self._debounce_tasks: Dict[str, asyncio.Task] = {}

    async def start(self):
        """Start watching plugin directories."""
        if not self._running:
            try:
                from watchdog.observers import Observer
                from watchdog.events import FileSystemEventHandler

                class PluginEventHandler(FileSystemEventHandler):
                    def __init__(self, watcher: "PluginWatcher"):
                        self.watcher = watcher

                    def on_modified(self, event):
                        if not event.is_directory and event.src_path.endswith(".py"):
                            asyncio.create_task(self.watcher._on_file_changed(event.src_path))

                    def on_created(self, event):
                        if not event.is_directory and (event.src_path.endswith(".py") or event.src_path.endswith("plugin.yaml")):
                            asyncio.create_task(self.watcher._on_file_changed(event.src_path))

                    def on_deleted(self, event):
                        if not event.is_directory and (event.src_path.endswith(".py") or event.src_path.endswith("plugin.yaml")):
                            asyncio.create_task(self.watcher._on_file_changed(event.src_path))

                self.observer = Observer()
                for plugin_dir in self.plugin_dirs:
                    if plugin_dir.exists():
                        self.observer.schedule(PluginEventHandler(self), str(plugin_dir), recursive=True)

                self.observer.start()
                self._running = True
                logger.info("Plugin file watcher started for hot-reload")

            except ImportError:
                logger.warning("watchdog not installed - hot-reload disabled. Install with: pip install watchdog")
            except Exception as e:
                logger.error(f"Failed to start plugin watcher: {e}")

    async def stop(self):
        """Stop the file watcher."""
        self._running = False
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=2)
            self.observer = None
        # Cancel debounced tasks
        for task in self._debounce_tasks.values():
            task.cancel()
        self._debounce_tasks.clear()
        logger.info("Plugin file watcher stopped")

    async def _on_file_changed(self, file_path: str):
        """Handle file change with debouncing."""
        # Debounce: wait for rapid changes to settle
        if file_path in self._debounce_tasks:
            self._debounce_tasks[file_path].cancel()

        async def debounced_reload():
            await asyncio.sleep(0.5)  # 500ms debounce
            try:
                plugin_name = self._extract_plugin_name(file_path)
                if plugin_name:
                    logger.info(f"File changed, reloading plugin: {plugin_name}")
                    await self.plugin_manager.reload_plugin(plugin_name)
            except Exception as e:
                logger.error(f"Hot-reload failed for {file_path}: {e}")

        self._debounce_tasks[file_path] = asyncio.create_task(debounced_reload())

    def _extract_plugin_name(self, file_path: str) -> Optional[str]:
        """Extract plugin name from file path."""
        path = Path(file_path)
        # Walk up to find plugin.yaml
        for parent in path.parents:
            if (parent / "plugin.yaml").exists():
                try:
                    manifest = load_manifest(parent / "plugin.yaml")
                    return manifest.name
                except Exception:
                    pass
        return None


class EnhancedPluginManager(BasePluginManager):
    """
    Enhanced Plugin Manager with:
    - Filesystem auto-discovery from runtime/plugins/<type>/<name>/plugin.yaml
    - Pydantic schema validation for plugin.yaml manifests
    - Hot-reload with watchdog (dev mode only)
    - Dependency resolution with topological sort
    """

    def __init__(
        self,
        registry: Optional[PluginRegistry] = None,
        runtime: Optional["Runtime"] = None,
        plugin_dirs: Optional[List[Union[str, Path]]] = None,
        dev_mode: bool = False,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(registry)
        self._runtime = runtime
        self.dev_mode = dev_mode

        # Store config for later use
        self._config = config or {}

        # Default plugin directories - should point to base plugins directory
        # which contains type directories (tool/, llm/, custom/, etc.)
        base_dir = Path(__file__).parent
        if plugin_dirs:
            self.plugin_dirs = [Path(d) for d in plugin_dirs]
        else:
            # Point to base plugins directory which contains type subdirectories
            self.plugin_dirs = [base_dir]

        self._discovered: Dict[str, DiscoveredPlugin] = {}
        self._load_order: List[str] = []
        self._watcher: Optional[PluginWatcher] = None
        self._external_deps: Dict[str, Any] = {}  # Runtime modules, skills, etc.

        # Events
        self._discovery_handlers: List[Callable[[str, PluginManifest], Awaitable[None]]] = []
        self._load_handlers: List[Callable[[str, Plugin], Awaitable[None]]] = []

    # =====================================================
    # AUTO-DISCOVERY
    # =====================================================

    async def discover_plugins(self, runtime: Optional["Runtime"] = None) -> Dict[str, PluginManifestSummary]:
        """
        Discover all plugins from filesystem.

        Scans: runtime/plugins/<type>/<name>/plugin.yaml
        """
        if runtime:
            self._runtime = runtime
        self._discovered.clear()
        summaries = {}

        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                continue

            # The plugin_dir is now the base plugins directory
            # We need to scan type subdirectories like tool/, llm/, custom/, etc.
            for type_dir in plugin_dir.iterdir():
                if not type_dir.is_dir() or type_dir.name.startswith('.'):
                    continue

                # Validate plugin type
                try:
                    PluginType(type_dir.name)
                except ValueError:
                    logger.debug(f"Skipping unknown plugin type directory: {type_dir.name}")
                    continue

                for plugin_name_dir in type_dir.iterdir():
                    if not plugin_name_dir.is_dir() or plugin_name_dir.name.startswith('.'):
                        continue

                    manifest_path = plugin_name_dir / "plugin.yaml"
                    if not manifest_path.exists():
                        logger.debug(f"No plugin.yaml found in {plugin_name_dir}")
                        continue

                    try:
                        manifest = load_manifest(manifest_path)
                        discovered = DiscoveredPlugin(
                            manifest=manifest,
                            plugin_dir=plugin_name_dir,
                            manifest_path=manifest_path,
                        )
                        self._discovered[manifest.name] = discovered
                        summaries[manifest.name] = PluginManifestSummary(
                            name=manifest.name,
                            version=manifest.version,
                            type=manifest.type,
                            description=manifest.description,
                            author=manifest.author,
                            tags=manifest.tags,
                            capabilities=manifest.capabilities,
                            status="discovered",
                            plugin_dir=str(plugin_name_dir),
                            manifest_path=str(manifest_path),
                        )
                        logger.info(f"Discovered plugin: {manifest.name} v{manifest.version} ({manifest.type.value})")

                        # Emit discovery event
                        for handler in self._discovery_handlers:
                            try:
                                await handler(manifest.name, manifest)
                            except Exception as e:
                                logger.error(f"Discovery handler error: {e}")

                    except Exception as e:
                        logger.error(f"Failed to load manifest from {manifest_path}: {e}")
                        # Track as error
                        error_summary = PluginManifestSummary(
                            name=plugin_name_dir.name,
                            version="0.0.0",
                            type=PluginType.CUSTOM,
                            description=f"Error loading manifest: {e}",
                            author="",
                            status="error",
                            plugin_dir=str(plugin_name_dir),
                            manifest_path=str(manifest_path),
                        )
                        summaries[plugin_name_dir.name] = error_summary

        return summaries

    async def validate_all_manifests(self) -> Dict[str, List[str]]:
        """Validate all discovered manifests. Returns dict of plugin_name -> list of errors."""
        errors = {}
        for name, plugin in self._discovered.items():
            try:
                # Re-validate using Pydantic
                validate_manifest_dict(plugin.manifest.model_dump())
            except Exception as e:
                errors[name] = [str(e)]
        return errors

    # =====================================================
    # DEPENDENCY RESOLUTION
    # =====================================================

    async def resolve_dependencies(self) -> List[str]:
        """
        Resolve plugin load order using topological sort.

        Returns list of plugin names in dependency order.
        """
        # First validate no cycles
        if not TopologicalSorter.validate_no_cycles(self._discovered):
            # Try to find and report cycle
            try:
                TopologicalSorter.sort(self._discovered)
            except ValueError as e:
                raise ValueError(f"Plugin dependency cycle: {e}")

        # Sort topologically
        self._load_order = TopologicalSorter.sort(self._discovered)
        logger.info(f"Plugin load order resolved: {self._load_order}")
        return self._load_order

    def get_load_order(self) -> List[str]:
        """Get current computed load order."""
        return self._load_order.copy()

    def register_external_dependency(self, dep_type: DependencyType, name: str, instance: Any):
        """Register an external dependency (runtime module, skill, python package)."""
        key = f"{dep_type.value}:{name}"
        self._external_deps[key] = instance
        logger.debug(f"Registered external dependency: {key}")

    # =====================================================
    # PLUGIN LOADING
    # =====================================================

    async def load_plugin(self, name: str, config: Optional[Dict[str, Any]] = None) -> Optional[Plugin]:
        """
        Load a single plugin by name.

        1. Load plugin class from entry_point
        2. Instantiate with config
        3. Validate config against manifest schema
        """
        discovered = self._discovered.get(name)
        if not discovered:
            raise ValueError(f"Plugin not discovered: {name}")

        if discovered.status in ("loaded", "initialized", "active"):
            logger.warning(f"Plugin {name} already loaded, returning existing instance")
            return discovered.instance

        try:
            # Determine entry point file
            entry_file = discovered.plugin_dir / discovered.manifest.entry_point
            if not entry_file.exists():
                raise FileNotFoundError(f"Entry point not found: {entry_file}")

            # Load module
            spec = importlib.util.spec_from_file_location(
                f"aipensa_plugin_{name}",
                entry_file
            )
            if not spec or not spec.loader:
                raise ImportError(f"Could not load spec for {entry_file}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

            # Get plugin class
            class_name = discovered.manifest.class_name
            plugin_class = getattr(module, class_name, None)
            if not plugin_class:
                raise AttributeError(f"Class {class_name} not found in {entry_file}")

            # Verify it's a Plugin subclass
            if not issubclass(plugin_class, Plugin):
                raise TypeError(f"{class_name} is not a subclass of Plugin")

            discovered.plugin_class = plugin_class

            # Merge configs: manifest defaults + provided config + runtime config
            merged_config = self._merge_plugin_configs(discovered.manifest, config)

            # Validate config against schema
            if discovered.manifest.config_schema:
                # Could add jsonschema validation here
                pass

            # Instantiate plugin
            plugin_instance = plugin_class(merged_config)
            discovered.instance = plugin_instance
            discovered.status = "loaded"

            # Create PluginInstance wrapper for base manager
            instance_wrapper = PluginInstance(
                metadata=PluginMetadata(
                    name=discovered.manifest.name,
                    version=discovered.manifest.version,
                    description=discovered.manifest.description,
                    author=discovered.manifest.author,
                    plugin_type=discovered.manifest.type,
                    provides=discovered.manifest.capabilities,
                    tags=set(discovered.manifest.tags),
                ),
                instance=plugin_instance,
                status=PluginStatus.LOADED,
                config=merged_config,
                loaded_at=datetime.utcnow(),
            )
            discovered.instance_wrapper = instance_wrapper
            self._instances[name] = instance_wrapper
            self._load_order.append(name)

            # Emit load event
            for handler in self._load_handlers:
                try:
                    await handler(name, plugin_instance)
                except Exception as e:
                    logger.error(f"Load handler error for {name}: {e}")

            logger.info(f"Loaded plugin: {name}")
            return plugin_instance

        except Exception as e:
            discovered.status = "error"
            discovered.error = str(e)
            logger.error(f"Failed to load plugin {name}: {e}")
            raise

    def _merge_plugin_configs(
        self,
        manifest: PluginManifest,
        override_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Merge manifest defaults, runtime config, and override config."""
        config = {}

        # Start with config schema defaults
        if manifest.config_schema and manifest.config_schema.properties:
            for prop_name, prop in manifest.config_schema.properties.items():
                if prop.default is not None:
                    config[prop_name] = prop.default

        # Apply runtime module config
        if self._config and manifest.name in self._config:
            config.update(self._config[manifest.name])

        # Apply override config (highest priority)
        if override_config:
            config.update(override_config)

        return config

    async def initialize_all(self, runtime: Runtime) -> List[str]:
        """
        Initialize all discovered plugins in dependency order.
        """
        await self.resolve_dependencies()
        initialized = []

        for name in self._load_order:
            plugin = self._discovered.get(name)
            if not plugin or not plugin.instance:
                # Load if not already loaded
                await self.load_plugin(name)

            try:
                plugin.status = "initializing"
                await plugin.instance.initialize(runtime)
                plugin.status = "initialized"
                plugin.instance_wrapper.status = PluginStatus.INITIALIZED
                plugin.initialized_at = datetime.utcnow()
                initialized.append(name)
                logger.info(f"Initialized plugin: {name}")
            except Exception as e:
                plugin.status = "error"
                plugin.error = str(e)
                plugin.instance_wrapper.status = PluginStatus.ERROR
                plugin.instance_wrapper.error = str(e)
                logger.error(f"Failed to initialize plugin {name}: {e}")
                # Continue with others but mark failure
                raise

        return initialized

    async def start_all(self) -> List[str]:
        """Start all initialized plugins."""
        started = []
        for name in self._load_order:
            plugin = self._discovered.get(name)
            if not plugin or plugin.status != "initialized":
                continue

            try:
                plugin.status = "starting"
                await plugin.instance.start()
                plugin.status = "active"
                plugin.instance_wrapper.status = PluginStatus.ACTIVE
                started.append(name)
                logger.info(f"Started plugin: {name}")
            except Exception as e:
                plugin.status = "error"
                plugin.error = str(e)
                plugin.instance_wrapper.status = PluginStatus.ERROR
                plugin.instance_wrapper.error = str(e)
                logger.error(f"Failed to start plugin {name}: {e}")
                raise

        return started

    async def load_initialize_start_all(self, runtime: Runtime) -> Dict[str, str]:
        """
        Convenience: Load, initialize, and start all plugins in order.
        Returns dict of plugin_name -> status.
        """
        await self.discover_plugins()
        await self.resolve_dependencies()

        results = {}
        for name in self._load_order:
            try:
                await self.load_plugin(name)
                await self._discovered[name].instance.initialize(runtime)
                await self._discovered[name].instance.start()
                results[name] = "active"
            except Exception as e:
                results[name] = f"error: {e}"
                logger.error(f"Failed to load/init/start {name}: {e}")

        return results

    # =====================================================
    # HOT-RELOAD
    # =====================================================

    async def reload_plugin(self, name: str) -> bool:
        """
        Hot-reload a single plugin (dev mode only).

        1. Stop and cleanup existing instance
        2. Reload module from disk
        3. Re-initialize and start
        """
        if not self.dev_mode:
            logger.warning("Hot-reload only available in dev_mode=True")
            return False

        plugin = self._discovered.get(name)
        if not plugin or not plugin.instance:
            logger.warning(f"Plugin {name} not loaded, cannot reload")
            return False

        try:
            logger.info(f"Hot-reloading plugin: {name}")

            # Stop and cleanup
            await plugin.instance.stop()
            await plugin.instance.cleanup()

            # Remove from sys.modules to force reload
            module_name = f"aipensa_plugin_{name}"
            if module_name in sys.modules:
                del sys.modules[module_name]

            # Reload
            plugin.status = "reloading"
            old_instance = plugin.instance
            old_wrapper = plugin.instance_wrapper

            # Load new instance
            await self.load_plugin(name)

            # Re-initialize with runtime
            if self._runtime:
                await plugin.instance.initialize(self._runtime)
                await plugin.instance.start()

            logger.info(f"Successfully hot-reloaded plugin: {name}")
            return True

        except Exception as e:
            logger.error(f"Hot-reload failed for {name}: {e}")
            # Try to restore old instance
            if plugin.instance_wrapper:
                plugin.instance_wrapper.status = PluginStatus.ERROR
                plugin.instance_wrapper.error = str(e)
            plugin.status = "error"
            plugin.error = str(e)
            raise

    async def enable_hot_reload(self):
        """Enable file watcher for hot-reload (dev mode)."""
        if not self.dev_mode:
            logger.warning("Hot-reload only available in dev_mode")
            return

        if self._watcher is None:
            self._watcher = PluginWatcher(self, self.plugin_dirs)
            await self._watcher.start()

    async def disable_hot_reload(self):
        """Disable file watcher."""
        if self._watcher:
            await self._watcher.stop()
            self._watcher = None

    # =====================================================
    # EVENT HANDLERS
    # =====================================================

    def on_discovered(self, handler: Callable[[str, PluginManifest], Awaitable[None]]):
        """Register handler for plugin discovery."""
        self._discovery_handlers.append(handler)

    def on_loaded(self, handler: Callable[[str, Plugin], Awaitable[None]]):
        """Register handler for plugin load."""
        self._load_handlers.append(handler)

    # =====================================================
    # QUERY METHODS
    # =====================================================

    def get_discovered_plugins(self) -> Dict[str, PluginManifestSummary]:
        """Get all discovered plugins with summary info."""
        return {
            name: PluginManifestSummary(
                name=p.manifest.name,
                version=p.manifest.version,
                type=p.manifest.type,
                description=p.manifest.description,
                author=p.manifest.author,
                tags=p.manifest.tags,
                capabilities=p.manifest.capabilities,
                status=p.status,
                plugin_dir=str(p.plugin_dir),
                manifest_path=str(p.manifest_path),
            )
            for name, p in self._discovered.items()
        }

    def get_plugin_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get detailed status for a plugin."""
        plugin = self._discovered.get(name)
        if not plugin:
            return None

        return {
            "name": name,
            "version": plugin.manifest.version,
            "type": plugin.manifest.type.value,
            "status": plugin.status,
            "error": plugin.error,
            "plugin_dir": str(plugin.plugin_dir),
            "manifest_path": str(plugin.manifest_path),
            "dependencies": [d.full_spec for d in plugin.manifest.dependencies],
            "capabilities": plugin.manifest.capabilities,
            "load_order_index": self._load_order.index(name) if name in self._load_order else -1,
        }

    def get_dependency_graph(self) -> Dict[str, Dict[str, Any]]:
        """Get full dependency graph."""
        graph = {}
        for name, plugin in self._discovered.items():
            graph[name] = {
                "dependencies": [d.full_spec for d in plugin.manifest.dependencies],
                "dependents": [
                    n for n, p in self._discovered.items()
                    if any(d.plugin_name == name for d in p.manifest.dependencies if d.type == DependencyType.PLUGIN)
                ],
                "status": plugin.status,
            }
        return graph

    # =====================================================
    # SHUTDOWN
    # =====================================================

    async def shutdown_all(self) -> None:
        """Shutdown all plugins in reverse load order."""
        await super().shutdown_all()
        # Stop watcher
        await self.disable_hot_reload()
        logger.info("All plugins shut down")


# Backward compatibility alias
PluginManager = EnhancedPluginManager


__all__ = [
    "EnhancedPluginManager",
    "PluginManager",
    "TopologicalSorter",
    "DiscoveredPlugin",
    "PluginWatcher",
]