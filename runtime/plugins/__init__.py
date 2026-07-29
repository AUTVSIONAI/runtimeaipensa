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
    "Plugin",
    "PluginManager",
    "PluginRegistry",
    "PluginType",
    "PluginStatus",
    "PluginMetadata",
    "PluginInstance",
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