"""
Plugin System for AIPENSA Runtime

Provides a flexible plugin architecture for extending runtime capabilities.
Every tool, MCP, runtime, browser, and integration is a plugin.
"""

from runtime.plugins.base import (
    Plugin,
    PluginManager,
    PluginRegistry,
    PluginType,
    PluginStatus,
    PluginMetadata,
    PluginInstance,
)

# Enhanced plugin manager with auto-discovery, hot-reload, dependency resolution
from runtime.plugins.manager import (
    EnhancedPluginManager,
    TopologicalSorter,
    DiscoveredPlugin,
    PluginWatcher,
)

# Plugin manifest schemas
from runtime.plugins.schemas import (
    PluginType as SchemaPluginType,
    DependencyType,
    ConfigProperty,
    ConfigSchema,
    PluginDependency,
    PluginManifest,
    PluginManifestSummary,
    load_manifest,
    validate_manifest_dict,
)

# Local plugin implementations
from runtime.plugins.local_plugins import (
    LocalBrowserPlugin,
    LocalExecutionPlugin,
    LocalToolsPlugin,
    LocalMemoryPlugin,
    LocalPlanningPlugin,
    LocalMCPPlugin,
    LocalFileSystemPlugin,
    LocalNetworkPlugin,
    LocalDockerPlugin,
)

# Re-export for convenience
__all__ = [
    # Base
    "Plugin",
    "PluginManager",
    "PluginRegistry",
    "PluginType",
    "PluginStatus",
    "PluginMetadata",
    "PluginInstance",
    # Enhanced Manager
    "EnhancedPluginManager",
    "TopologicalSorter",
    "DiscoveredPlugin",
    "PluginWatcher",
    # Schemas
    "SchemaPluginType",
    "DependencyType",
    "ConfigProperty",
    "ConfigSchema",
    "PluginDependency",
    "PluginManifest",
    "PluginManifestSummary",
    "load_manifest",
    "validate_manifest_dict",
    # Local plugins
    "LocalBrowserPlugin",
    "LocalExecutionPlugin",
    "LocalToolsPlugin",
    "LocalMemoryPlugin",
    "LocalPlanningPlugin",
    "LocalMCPPlugin",
    "LocalFileSystemPlugin",
    "LocalNetworkPlugin",
    "LocalDockerPlugin",
]