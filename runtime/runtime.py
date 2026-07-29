"""
Main Runtime Class for AIPENSA Runtime

The central orchestrator that manages all modules, plugins, and provides
the public API for executing tasks.
"""

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Set, Type, Union
import asyncio
import importlib
import logging
import uuid

from runtime.config import RuntimeConfig, RuntimeType, get_development_config
from runtime.events import get_event_bus, EventBus
from runtime.base.events import RuntimeEvent, RuntimeEventType, create_event
from runtime.plugins import Plugin, PluginManager, PluginRegistry, PluginType, PluginStatus
from runtime.di import Container, ServiceLifetime, get_container, set_container
from runtime.modules import (
    ModuleRegistry,
    ModuleState,
    RuntimeModule,
    BrowserModule,
    ExecutionModule,
    ToolModule,
    MemoryModule,
    PlanningModule,
    MCPModule,
    FileSystemModule,
    NetworkModule,
    DockerModule,
    BrowserSession,
    BrowserState,
    ExecutionResult,
    ToolDefinition,
    ToolExecution,
    MemoryEntry,
    SearchResult,
    Plan,
    MCPServer,
    FileInfo,
    ContainerInfo,
)

logger = logging.getLogger(__name__)


class RuntimeStatus(Enum):
    """Runtime status."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class RuntimeInfo:
    """Runtime information."""

    runtime_id: str
    name: str
    version: str
    status: RuntimeStatus
    started_at: Optional[datetime] = None
    config: Optional[RuntimeConfig] = None
    modules: Dict[str, ModuleState] = field(default_factory=dict)
    plugins: Dict[str, PluginStatus] = field(default_factory=dict)


class Runtime:
    """
    AIPENSA Runtime - Enterprise AI Execution Engine.

    This is the main entry point for the runtime. It provides:
    - Module management (browser, execution, tools, memory, planning, MCP, etc.)
    - Plugin system for extensibility
    - Event bus for observability
    - Dependency injection container
    - Configuration management
    - Unified API for task execution

    Usage:
        runtime = Runtime(RuntimeConfig(runtime_type=RuntimeType.LOCAL))
        await runtime.start()

        # Execute tasks
        result = await runtime.execute_tool("browser_navigate", {"url": "https://example.com"})
        result = await runtime.execute_python("print('Hello World')")
        result = await runtime.read_file("data.txt")

        await runtime.stop()
    """

    def __init__(
        self,
        config: Optional[RuntimeConfig] = None,
        container: Optional[Container] = None,
        event_bus: Optional[EventBus] = None,
    ):
        self.config = config or get_development_config()
        self.runtime_id = str(uuid.uuid4())[:8]
        self.name = f"AIPENSA-Runtime-{self.runtime_id}"
        self.version = "1.0.0"
        self.status = RuntimeStatus.STOPPED

        # Core infrastructure
        self._container = container or Container()
        self._event_bus = event_bus or get_event_bus()
        self._plugin_manager = PluginManager(PluginRegistry())
        self._module_registry = ModuleRegistry()

        # Module instances (lazy loaded)
        self._modules: Dict[str, RuntimeModule] = {}
        self._started_at: Optional[datetime] = None

        # Setup DI container
        self._setup_container()

        # Register local plugins
        self._register_local_plugins()

        # Register core modules
        self._register_core_modules()

    def _setup_container(self) -> None:
        """Setup dependency injection container."""
        # Register core services
        self._container.register_instance(Runtime, self)
        self._container.register_instance(EventBus, self._event_bus)
        self._container.register_instance(PluginManager, self._plugin_manager)
        self._container.register_instance(ModuleRegistry, self._module_registry)

        # Set as global container
        set_container(self._container)

    def _register_core_modules(self) -> None:
        """Register core module interfaces."""
        # Abstract interfaces are not registered - only concrete implementations
        # registered via plugins or built-in factory
        pass

    def _register_local_plugins(self) -> None:
        """Register local plugin implementations."""
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
            LocalConversationPlugin,
            LocalAgentPlugin,
            LocalWorkflowPlugin,
            LocalSchedulerPlugin,
            LocalQueuePlugin,
            LocalNotificationPlugin,
            LocalStoragePlugin,
            LocalAuthenticationPlugin,
            LocalWorkspacePlugin,
            LocalVoicePlugin,
            LocalVisionPlugin,
            LocalVideoPlugin,
            LocalImagePlugin,
            LocalEmbeddingPlugin,
            LocalRAGPlugin,
            LocalReasoningPlugin,
            LocalLLMPlugin,
        )

        plugins = [
            LocalBrowserPlugin,
            LocalExecutionPlugin,
            LocalToolsPlugin,
            LocalMemoryPlugin,
            LocalPlanningPlugin,
            LocalMCPPlugin,
            LocalFileSystemPlugin,
            LocalNetworkPlugin,
            LocalDockerPlugin,
            # Agent & Conversation
            LocalConversationPlugin,
            LocalAgentPlugin,
            # Orchestration
            LocalWorkflowPlugin,
            LocalSchedulerPlugin,
            LocalQueuePlugin,
            # Infrastructure
            LocalNotificationPlugin,
            LocalStoragePlugin,
            LocalAuthenticationPlugin,
            LocalWorkspacePlugin,
            # AI Capabilities
            LocalVoicePlugin,
            LocalVisionPlugin,
            LocalVideoPlugin,
            LocalImagePlugin,
            LocalEmbeddingPlugin,
            LocalRAGPlugin,
            LocalReasoningPlugin,
            LocalLLMPlugin,
        ]

        for plugin_cls in plugins:
            metadata = plugin_cls.metadata
            entry_point = f"runtime.plugins.local_plugins:{plugin_cls.__name__}"
            self._plugin_manager.registry.register(metadata, entry_point)
            logger.debug(f"Registered local plugin: {metadata.name}")

    @property
    def container(self) -> Container:
        """Get DI container."""
        return self._container

    @property
    def event_bus(self) -> EventBus:
        """Get event bus."""
        return self._event_bus

    @property
    def plugin_manager(self) -> PluginManager:
        """Get plugin manager."""
        return self._plugin_manager

    @property
    def modules(self) -> Dict[str, RuntimeModule]:
        """Get loaded modules."""
        return self._modules.copy()

    # ============================================
    # Lifecycle Management
    # ============================================

    async def start(self) -> None:
        """Start the runtime and all modules."""
        if self.status != RuntimeStatus.STOPPED:
            logger.warning(f"Runtime already {self.status.value}")
            return

        self.status = RuntimeStatus.STARTING
        self._started_at = datetime.utcnow()
        logger.info(f"Starting runtime {self.name}")

        try:
            # Start event bus
            await self._event_bus.start()

            # Start plugin manager
            self._plugin_manager.set_runtime(self)

            # Load plugins first - they may provide module implementations
            await self._load_plugins()

            # Initialize core modules based on config
            await self._initialize_modules()

            # Start all modules
            await self._start_modules()

            self.status = RuntimeStatus.RUNNING
            logger.info(f"Runtime {self.name} started successfully")

            # Publish startup event
            await self._event_bus.publish(create_event(
                event_type=RuntimeEventType.RUNTIME_STARTED,
                source=self.name,
                payload={"runtime_id": self.runtime_id, "version": self.version}
            ))

        except Exception as e:
            self.status = RuntimeStatus.ERROR
            logger.error(f"Failed to start runtime: {e}")
            await self._event_bus.publish(create_event(
                event_type=RuntimeEventType.SYSTEM_ERROR,
                source=self.name,
                payload={"error": str(e)}
            ))
            raise

    async def stop(self) -> None:
        """Stop the runtime gracefully."""
        if self.status == RuntimeStatus.STOPPED:
            return

        self.status = RuntimeStatus.STOPPING
        logger.info(f"Stopping runtime {self.name}")

        try:
            # Stop modules in reverse order
            await self._stop_modules()

            # Shutdown plugins
            await self._plugin_manager.shutdown_all()

            # Stop event bus
            await self._event_bus.stop()

            self.status = RuntimeStatus.STOPPED
            logger.info(f"Runtime {self.name} stopped")

            await self._event_bus.publish(create_event(
                event_type=RuntimeEventType.RUNTIME_STOPPED,
                source=self.name,
                payload={"runtime_id": self.runtime_id}
            ))

        except Exception as e:
            self.status = RuntimeStatus.ERROR
            logger.error(f"Error stopping runtime: {e}")
            raise

    async def _initialize_modules(self) -> None:
        """Initialize modules based on configuration."""
        module_configs = self.config.get_module_configs()

        for module_name, module_config in module_configs.items():
            if not module_config.get("enabled", True):
                logger.info(f"Module {module_name} disabled, skipping")
                continue

            # Check if module is already loaded (from plugins)
            if module_name in self._modules:
                logger.info(f"Module {module_name} already loaded via plugin")
                continue

            try:
                await self._initialize_module(module_name, module_config)
            except Exception as e:
                logger.error(f"Failed to initialize module {module_name}: {e}")
                if module_config.get("required", False):
                    raise

    async def _initialize_module(self, name: str, config: Dict[str, Any]) -> None:
        """Initialize a single module."""
        # Get module class from registry
        module_class = self._module_registry.get_module_class(name)
        if not module_class:
            # Try to load from plugin
            try:
                plugin = await self._plugin_manager.load_and_initialize(name, config)
                if plugin:
                    # Check if it provides a module
                    if hasattr(plugin, 'get_module'):
                        module = plugin.get_module()
                        if module:
                            self._modules[name] = module
                            self._module_registry.set_instance(name, module)
                            return
            except ValueError:
                # Plugin not found, continue to builtin
                pass
            except Exception as e:
                logger.warning(f"Failed to load plugin {name}: {e}")

            # Try built-in implementations
            module = await self._create_builtin_module(name, config)
            if not module:
                raise ValueError(f"No implementation found for module {name}")
        else:
            module = module_class()

        # Pass only the inner config dict to module.initialize
        module_config = config.get("config", config) if isinstance(config, dict) else config
        await module.initialize(self, module_config)
        await module.start()
        self._modules[name] = module
        self._module_registry.set_instance(name, module)
        logger.info(f"Initialized module: {name}")

    async def _create_builtin_module(self, name: str, config: Dict[str, Any]) -> Optional[RuntimeModule]:
        """Create built-in module implementation."""
        module_map = {
            "browser": ("runtime.browser.local_browser", "LocalBrowserModule"),
            "local-browser": ("runtime.browser.local_browser", "LocalBrowserModule"),
            "execution": ("runtime.execution.local_execution", "LocalExecutionModule"),
            "local-execution": ("runtime.execution.local_execution", "LocalExecutionModule"),
            "tools": ("runtime.toolcalling.local_tools", "LocalToolsModule"),
            "local-tools": ("runtime.toolcalling.local_tools", "LocalToolsModule"),
            "memory": ("runtime.memory.local_memory", "LocalMemoryModule"),
            "local-memory": ("runtime.memory.local_memory", "LocalMemoryModule"),
            "planning": ("runtime.planning.local_planning", "LocalPlanningModule"),
            "local-planning": ("runtime.planning.local_planning", "LocalPlanningModule"),
            "mcp": ("runtime.mcp.local_mcp", "LocalMCPModule"),
            "local-mcp": ("runtime.mcp.local_mcp", "LocalMCPModule"),
            "filesystem": ("runtime.filesystem.local_filesystem", "LocalFileSystemModule"),
            "local-filesystem": ("runtime.filesystem.local_filesystem", "LocalFileSystemModule"),
            "network": ("runtime.network.local_network", "LocalNetworkModule"),
            "local-network": ("runtime.network.local_network", "LocalNetworkModule"),
            "docker": ("runtime.docker.local_docker", "LocalDockerModule"),
            "local-docker": ("runtime.docker.local_docker", "LocalDockerModule"),
            # LLM module
            "llm": ("runtime.llm.module", "LLMModule"),
            # Agent & Conversation modules
            "conversation": ("runtime.conversation.module", "ConversationModule"),
            "agent": ("runtime.agent.module", "AgentModule"),
            # Orchestration modules
            "workflow": ("runtime.workflow.module", "WorkflowModule"),
            "scheduler": ("runtime.scheduler.module", "SchedulerModule"),
            "queue": ("runtime.queue.module", "QueueModule"),
            # Infrastructure modules
            "notification": ("runtime.notification.module", "NotificationModule"),
            "storage": ("runtime.storage.module", "StorageModule"),
            "authentication": ("runtime.authentication.module", "AuthenticationModule"),
            "workspace": ("runtime.workspace.module", "WorkspaceModule"),
            # AI Capabilities modules
            "voice": ("runtime.voice.module", "VoiceModule"),
            "vision": ("runtime.vision.module", "VisionModule"),
            "video": ("runtime.video.module", "VideoModule"),
            "image": ("runtime.image.module", "ImageModule"),
            "embedding": ("runtime.embedding.module", "EmbeddingModule"),
            "rag": ("runtime.rag.module", "RAGModule"),
            "reasoning": ("runtime.reasoning.module", "ReasoningModule"),
            "llm": ("runtime.llm.module", "LLMModule"),
            # Extensions Layer (NEW - doesn't modify kernel, only composes extensions)
            "company_context": ("runtime.extensions.company.engine", "CompanyContextModule"),
            "employee": ("runtime.extensions.employee.employee", "EmployeeModule"),
            "team": ("runtime.extensions.team.team", "TeamModule"),
            "provider": ("runtime.extensions.provider.provider", "ProviderModule"),
            "onboarding": ("runtime.extensions.onboarding.onboarding", "OnboardingModule"),
            "explorer": ("runtime.extensions.explorer.explorer", "ExplorerModule"),
            "sync": ("runtime.extensions.sync.sync", "SyncModule"),
        }

        if name not in module_map:
            return None

        module_path, class_name = module_map[name]
        try:
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            return cls(config)
        except Exception as e:
            logger.warning(f"Failed to load built-in module {name}: {e}")
            return None

    async def _load_plugins(self) -> None:
        """Load plugins from configuration."""
        # Get module configs to merge into plugin configs
        module_configs = self.config.get_module_configs()

        for plugin_name, plugin_config in self.config.plugin_configs.items():
            if not plugin_config.get("enabled", True):
                continue

            # Merge module config into plugin config for plugins that provide modules
            merged_config = dict(plugin_config.get("config", {}))
            if plugin_name in module_configs:
                module_config = module_configs[plugin_name]
                # The module config has "config" key with actual config
                if "config" in module_config:
                    merged_config = self._deep_merge(merged_config, module_config["config"])
                # Also include enabled/required flags
                merged_config["enabled"] = module_config.get("enabled", True)
                merged_config["required"] = module_config.get("required", False)
                logger.debug(f"Merged module config for plugin {plugin_name}: {list(module_config.get('config', {}).keys())}")

            try:
                await self._plugin_manager.load_and_initialize(
                    plugin_name,
                    merged_config,
                    plugin_config.get("entry_point")
                )
                logger.info(f"Loaded plugin: {plugin_name}")
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin_name}: {e}")
                if plugin_config.get("required", False):
                    raise

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries, with override taking precedence."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    async def _start_modules(self) -> None:
        """Start all initialized modules."""
        for name, module in self._modules.items():
            if module.state == ModuleState.INITIALIZED:
                await module.start()
                logger.info(f"Started module: {name}")

    async def _stop_modules(self) -> None:
        """Stop all modules in reverse order."""
        for name in reversed(list(self._modules.keys())):
            module = self._modules[name]
            try:
                await module.stop()
                await module.cleanup()
                logger.info(f"Stopped module: {name}")
            except Exception as e:
                logger.error(f"Error stopping module {name}: {e}")

    # ============================================
    # Module Access
    # ============================================

    def get_module(self, name: str) -> Optional[RuntimeModule]:
        """Get a module by name."""
        return self._modules.get(name)

    def get_browser(self) -> Optional[BrowserModule]:
        """Get browser module."""
        return self.get_module("browser") or self.get_module("local-browser")

    def get_execution(self) -> Optional[ExecutionModule]:
        """Get execution module."""
        return self.get_module("execution") or self.get_module("local-execution")

    def get_tools(self) -> Optional[ToolModule]:
        """Get tools module."""
        return self.get_module("tools") or self.get_module("local-tools")

    def get_memory(self) -> Optional[MemoryModule]:
        """Get memory module."""
        return self.get_module("memory") or self.get_module("local-memory")

    def get_planning(self) -> Optional[PlanningModule]:
        """Get planning module."""
        return self.get_module("planning") or self.get_module("local-planning")

    def get_mcp(self) -> Optional[MCPModule]:
        """Get MCP module."""
        return self.get_module("mcp") or self.get_module("local-mcp")

    def get_filesystem(self) -> Optional[FileSystemModule]:
        """Get filesystem module."""
        return self.get_module("filesystem") or self.get_module("local-filesystem")

    def get_network(self) -> Optional[NetworkModule]:
        """Get network module."""
        return self.get_module("network") or self.get_module("local-network")

    def get_docker(self) -> Optional[DockerModule]:
        """Get docker module."""
        return self.get_module("docker") or self.get_module("local-docker")

    # ============================================
    # Browser API
    # ============================================

    async def create_browser(
        self,
        url: str = "about:blank",
        config: Optional[Dict[str, Any]] = None
    ) -> BrowserSession:
        """Create a new browser session."""
        browser = self.get_browser()
        if not browser:
            raise RuntimeError("Browser module not available")
        return await browser.create_session(url, config)

    async def navigate(self, session_id: str, url: str) -> Dict[str, Any]:
        """Navigate browser to URL."""
        browser = self.get_browser()
        if not browser:
            raise RuntimeError("Browser module not available")
        return await browser.navigate(session_id, url)

    async def get_browser_state(self, session_id: str) -> BrowserState:
        """Get browser state."""
        browser = self.get_browser()
        if not browser:
            raise RuntimeError("Browser module not available")
        return await browser.get_state(session_id)

    async def browser_action(
        self,
        session_id: str,
        action: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute browser action."""
        browser = self.get_browser()
        if not browser:
            raise RuntimeError("Browser module not available")
        return await browser.execute_action(session_id, action, params)

    async def extract_content(
        self,
        session_id: str,
        goal: str,
        selector: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract content from page."""
        browser = self.get_browser()
        if not browser:
            raise RuntimeError("Browser module not available")
        return await browser.extract_content(session_id, goal, selector)

    async def browser_screenshot(
        self,
        session_id: str,
        full_page: bool = True
    ) -> str:
        """Take browser screenshot."""
        browser = self.get_browser()
        if not browser:
            raise RuntimeError("Browser module not available")
        return await browser.take_screenshot(session_id, full_page)

    async def close_browser(self, session_id: str) -> bool:
        """Close browser session."""
        browser = self.get_browser()
        if not browser:
            raise RuntimeError("Browser module not available")
        return await browser.close_session(session_id)

    # ============================================
    # Execution API
    # ============================================

    async def execute_python(
        self,
        code: str,
        sandbox_id: Optional[str] = None,
        timeout_seconds: int = 30,
        packages: Optional[List[str]] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        """Execute Python code."""
        execution = self.get_execution()
        if not execution:
            raise RuntimeError("Execution module not available")
        return await execution.execute_python(code, sandbox_id, timeout_seconds, packages, env_vars)

    async def execute_shell(
        self,
        command: str,
        sandbox_id: Optional[str] = None,
        timeout_seconds: int = 60,
        working_dir: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        """Execute shell command."""
        execution = self.get_execution()
        if not execution:
            raise RuntimeError("Execution module not available")
        return await execution.execute_shell(command, sandbox_id, timeout_seconds, working_dir, env_vars)

    async def execute_code(
        self,
        code: str,
        language: str = "python",
        sandbox_id: Optional[str] = None,
        **kwargs
    ) -> ExecutionResult:
        """Execute code in specified language."""
        execution = self.get_execution()
        if not execution:
            raise RuntimeError("Execution module not available")
        if language == "python":
            return await execution.execute_python(code, sandbox_id, **kwargs)
        else:
            return await execution.execute_shell(code, sandbox_id, **kwargs)

    async def create_sandbox(
        self,
        image: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> "SandboxInfo":
        """Create a new sandbox/container."""
        execution = self.get_execution()
        if not execution:
            raise RuntimeError("Execution module not available")
        return await execution.create_sandbox(image, config)

    async def destroy_sandbox(self, sandbox_id: str) -> bool:
        """Destroy a sandbox."""
        execution = self.get_execution()
        if not execution:
            raise RuntimeError("Execution module not available")
        return await execution.destroy_sandbox(sandbox_id)

    # ============================================
    # Tool API
    # ============================================

    async def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: callable,
        category: str = "general",
        tags: Optional[List[str]] = None,
        requires_approval: bool = False,
        returns: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Register a tool."""
        tools = self.get_tools()
        if not tools:
            raise RuntimeError("Tools module not available")

        definition = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            returns=returns or {},
            category=category,
            tags=tags or [],
            requires_approval=requires_approval,
        )
        return await tools.register_tool(definition, handler)

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolExecution:
        """Execute a tool."""
        tools = self.get_tools()
        if not tools:
            raise RuntimeError("Tools module not available")
        return await tools.execute_tool(tool_name, arguments, context)

    async def get_tool(self, tool_name: str) -> Optional[ToolDefinition]:
        """Get tool definition."""
        tools = self.get_tools()
        if not tools:
            raise RuntimeError("Tools module not available")
        return await tools.get_tool(tool_name)

    async def list_tools(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[ToolDefinition]:
        """List available tools."""
        tools = self.get_tools()
        if not tools:
            raise RuntimeError("Tools module not available")
        return await tools.list_tools(category, tags)

    # ============================================
    # Memory API
    # ============================================

    async def store_memory(
        self,
        key: str,
        value: Any,
        memory_type: str = "default",
        tags: Optional[List[str]] = None,
        ttl_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryEntry:
        """Store a value in memory."""
        memory = self.get_memory()
        if not memory:
            raise RuntimeError("Memory module not available")
        return await memory.store(key, value, memory_type, tags, ttl_seconds, metadata)

    async def retrieve_memory(
        self,
        key: str,
        memory_type: str = "default"
    ) -> Optional[MemoryEntry]:
        """Retrieve a value from memory."""
        memory = self.get_memory()
        if not memory:
            raise RuntimeError("Memory module not available")
        return await memory.retrieve(key, memory_type)

    async def delete_memory(self, key: str, memory_type: str = "default") -> bool:
        """Delete a value from memory."""
        memory = self.get_memory()
        if not memory:
            raise RuntimeError("Memory module not available")
        return await memory.delete(key, memory_type)

    async def search_memory(
        self,
        query: str,
        memory_type: str = "default",
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search memory."""
        memory = self.get_memory()
        if not memory:
            raise RuntimeError("Memory module not available")
        return await memory.search(query, memory_type, limit, filters)

    async def clear_memory(self, memory_type: Optional[str] = None) -> int:
        """Clear memory."""
        memory = self.get_memory()
        if not memory:
            raise RuntimeError("Memory module not available")
        return await memory.clear(memory_type)

    # ============================================
    # Planning API
    # ============================================

    async def create_plan(
        self,
        goal: str,
        context: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None
    ) -> Plan:
        """Create an execution plan."""
        planning = self.get_planning()
        if not planning:
            raise RuntimeError("Planning module not available")
        return await planning.create_plan(goal, context, constraints)

    async def execute_plan(
        self,
        plan_id: str,
        agents: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a plan."""
        planning = self.get_planning()
        if not planning:
            raise RuntimeError("Planning module not available")
        return await planning.execute_plan(plan_id, agents)

    # ============================================
    # MCP API
    # ============================================

    async def connect_mcp(self, server_id: str, config: Dict[str, Any]) -> MCPServer:
        """Connect to MCP server."""
        mcp = self.get_mcp()
        if not mcp:
            raise RuntimeError("MCP module not available")
        return await mcp.connect_server(server_id, config)

    async def disconnect_mcp(self, server_id: str) -> bool:
        """Disconnect from MCP server."""
        mcp = self.get_mcp()
        if not mcp:
            raise RuntimeError("MCP module not available")
        return await mcp.disconnect_server(server_id)

    async def call_mcp_tool(self, server_id: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call MCP tool."""
        mcp = self.get_mcp()
        if not mcp:
            raise RuntimeError("MCP module not available")
        return await mcp.call_tool(server_id, tool_name, arguments)

    # ============================================
    # File System API
    # ============================================

    async def read_file(self, path: str, encoding: str = "utf-8") -> str:
        """Read a file."""
        fs = self.get_filesystem()
        if not fs:
            raise RuntimeError("FileSystem module not available")
        return await fs.read_file(path, encoding)

    async def write_file(
        self,
        path: str,
        content: str,
        encoding: str = "utf-8",
        create_dirs: bool = True
    ) -> FileInfo:
        """Write a file."""
        fs = self.get_filesystem()
        if not fs:
            raise RuntimeError("FileSystem module not available")
        return await fs.write_file(path, content, encoding, create_dirs)

    async def delete_file(self, path: str) -> bool:
        """Delete a file."""
        fs = self.get_filesystem()
        if not fs:
            raise RuntimeError("FileSystem module not available")
        return await fs.delete_file(path)

    async def list_files(
        self,
        path: str,
        recursive: bool = False,
        pattern: Optional[str] = None
    ) -> List[FileInfo]:
        """List directory contents."""
        fs = self.get_filesystem()
        if not fs:
            raise RuntimeError("FileSystem module not available")
        return await fs.list_directory(path, recursive, pattern)

    # ============================================
    # Network API
    # ============================================

    async def http_get(self, url: str, **kwargs) -> "NetworkResponse":
        """HTTP GET request."""
        network = self.get_network()
        if not network:
            raise RuntimeError("Network module not available")
        return await network.get(url, **kwargs)

    async def http_post(self, url: str, **kwargs) -> "NetworkResponse":
        """HTTP POST request."""
        network = self.get_network()
        if not network:
            raise RuntimeError("Network module not available")
        return await network.post(url, **kwargs)

    async def download_file(
        self,
        url: str,
        destination: str,
        progress_callback: Optional[callable] = None
    ) -> "NetworkResponse":
        """Download a file."""
        network = self.get_network()
        if not network:
            raise RuntimeError("Network module not available")
        return await network.download_file(url, destination, progress_callback)

    # ============================================
    # Docker API
    # ============================================

    async def run_container(
        self,
        image: str,
        name: Optional[str] = None,
        command: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
        ports: Optional[Dict[int, int]] = None,
        volumes: Optional[Dict[str, str]] = None,
        detach: bool = True,
        **kwargs
    ) -> ContainerInfo:
        """Run a Docker container."""
        docker = self.get_docker()
        if not docker:
            raise RuntimeError("Docker module not available")
        return await docker.run_container(image, name, command, env_vars, ports, volumes, detach, **kwargs)

    async def stop_container(self, container_id: str, timeout: int = 10) -> bool:
        """Stop a container."""
        docker = self.get_docker()
        if not docker:
            raise RuntimeError("Docker module not available")
        return await docker.stop_container(container_id, timeout)

    async def get_container_logs(
        self,
        container_id: str,
        tail: int = 100
    ) -> AsyncIterator[str]:
        """Get container logs."""
        docker = self.get_docker()
        if not docker:
            raise RuntimeError("Docker module not available")
        async for log in docker.get_logs(container_id, tail):
            yield log

    # ============================================
    # Generic Task Execution
    # ============================================

    async def execute(self, task: "TaskRequest") -> "TaskResult":
        """Execute a generic task request."""
        from dataclasses import dataclass

        @dataclass
        class TaskRequest:
            type: str
            action: str
            params: Dict[str, Any]
            context: Optional[Dict[str, Any]] = None

        @dataclass
        class TaskResult:
            success: bool
            result: Any = None
            error: Optional[str] = None

        task_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        await self._event_bus.publish(create_event(
            event_type=RuntimeEventType.TASK_STARTED,
            source=self.name,
            payload={"task_id": task_id, "task_name": task.action}
        ))

        try:
            # Route to appropriate module based on task type
            result = await self._route_task(task.type, task.action, task.params, task.context)

            duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            await self._event_bus.publish(create_event(
                event_type=RuntimeEventType.TASK_COMPLETED,
                source=self.name,
                payload={"task_id": task_id, "task_name": task.action, "result": result, "duration_ms": duration}
            ))

            return TaskResult(success=True, result=result)

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            await self._event_bus.publish(create_event(
                event_type=RuntimeEventType.TASK_FAILED,
                source=self.name,
                payload={"task_id": task_id, "task_name": task.action, "error": str(e), "duration_ms": duration}
            ))

            return TaskResult(success=False, error=str(e))

    async def _route_task(
        self,
        task_type: str,
        action: str,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Any:
        """Route task to appropriate module."""
        if task_type == "browser":
            browser = self.get_browser()
            if not browser:
                raise RuntimeError("Browser module not available")
            return await browser.execute_action(params.get("session_id", ""), action, params)

        elif task_type == "execution":
            execution = self.get_execution()
            if not execution:
                raise RuntimeError("Execution module not available")
            if action == "python":
                return await execution.execute_python(**params)
            elif action == "shell":
                return await execution.execute_shell(**params)

        elif task_type == "tool":
            return await self.execute_tool(action, params, context)

        elif task_type == "memory":
            memory = self.get_memory()
            if not memory:
                raise RuntimeError("Memory module not available")
            if action == "store":
                return await memory.store(**params)
            elif action == "retrieve":
                return await memory.retrieve(**params)
            elif action == "search":
                return await memory.search(**params)

        elif task_type == "filesystem":
            fs = self.get_filesystem()
            if not fs:
                raise RuntimeError("Filesystem module not available")
            if action == "read":
                return await fs.read_file(**params)
            elif action == "write":
                return await fs.write_file(**params)
            elif action == "list":
                return await fs.list_directory(**params)

        elif task_type == "network":
            network = self.get_network()
            if not network:
                raise RuntimeError("Network module not available")
            if action == "get":
                return await network.get(**params)
            elif action == "post":
                return await network.post(**params)

        elif task_type == "docker":
            docker = self.get_docker()
            if not docker:
                raise RuntimeError("Docker module not available")
            if action == "run":
                return await docker.run_container(**params)
            elif action == "stop":
                return await docker.stop_container(**params)

        raise ValueError(f"Unknown task type: {task_type}")

    # ============================================
    # Information & Health
    # ============================================

    def get_info(self) -> RuntimeInfo:
        """Get runtime information."""
        return RuntimeInfo(
            runtime_id=self.runtime_id,
            name=self.name,
            version=self.version,
            status=self.status,
            started_at=self._started_at,
            config=self.config,
            modules={name: module.state for name, module in self._modules.items()},
            plugins={
                name: instance.status
                for name, instance in self._plugin_manager.get_all_instances().items()
            },
        )

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all modules."""
        health = {
            "runtime": {
                "status": self.status.value,
                "runtime_id": self.runtime_id,
                "uptime_seconds": (datetime.utcnow() - self._started_at).total_seconds() if self._started_at else 0,
            },
            "modules": {},
            "plugins": {},
        }

        for name, module in self._modules.items():
            try:
                health["modules"][name] = await module.health_check()
            except Exception as e:
                health["modules"][name] = {"status": "error", "error": str(e)}

        for name, instance in self._plugin_manager.get_all_instances().items():
            health["plugins"][name] = {
                "status": instance.status.value,
                "version": instance.metadata.version,
            }

        return health

    # ============================================
    # Context Manager
    # ============================================

    async def __aenter__(self) -> "Runtime":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()


# Convenience function for creating runtime
async def create_runtime(
    config: Optional[RuntimeConfig] = None,
    **kwargs
) -> Runtime:
    """Create and start a runtime."""
    runtime = Runtime(config, **kwargs)
    await runtime.start()
    return runtime


__all__ = [
    "Runtime",
    "RuntimeStatus",
    "RuntimeInfo",
    "create_runtime",
]