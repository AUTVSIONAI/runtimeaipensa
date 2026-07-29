"""
AIPENSA Runtime Base - Core Abstractions

Provides the foundational interfaces, base classes, and patterns
that all AIPENSA Runtime engines must implement.
"""

from runtime.base.runtime import (
    Runtime,
    RuntimeConfig,
    RuntimeStatus,
    RuntimeInfo,
)
from runtime.base.module import (
    RuntimeModule,
    ModuleMetadata,
    ModuleState,
)
from runtime.base.plugin import (
    RuntimePlugin,
    PluginMetadata,
    PluginStatus,
    PluginType,
)
from runtime.base.factory import (
    ModuleFactory,
    PluginFactory,
    DynamicModuleFactory,
    DynamicPluginFactory,
    CompositeFactory,
)
from runtime.base.runtime_factory import (
    RuntimeFactory,
)
from runtime.base.events import (
    RuntimeEvent,
    RuntimeEventType,
    RuntimeEventBus,
    event_handler,
    create_event,
)
from runtime.base.di import (
    RuntimeContainer,
    ServiceLifetime,
    injectable,
    singleton,
    transient,
    scoped,
)
from runtime.base.registry import (
    RuntimeRegistry,
)
from runtime.base.module import ModuleRegistry
from runtime.base.plugin import PluginRegistry

__all__ = [
    # Runtime
    "Runtime",
    "RuntimeConfig",
    "RuntimeStatus",
    "RuntimeInfo",
    # Module
    "RuntimeModule",
    "ModuleMetadata",
    "ModuleState",
    # Plugin
    "RuntimePlugin",
    "PluginMetadata",
    "PluginStatus",
    "PluginType",
    # Factory
    "ModuleFactory",
    "PluginFactory",
    "DynamicModuleFactory",
    "DynamicPluginFactory",
    "CompositeFactory",
    # Events
    "RuntimeEvent",
    "RuntimeEventType",
    "RuntimeEventBus",
    # DI
    "RuntimeContainer",
    "ServiceLifetime",
    "injectable",
    "singleton",
    "transient",
    "scoped",
    # Registry
    "RuntimeRegistry",
    "ModuleRegistry",
    "PluginRegistry",
]