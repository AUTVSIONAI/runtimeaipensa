"""
Plugin Wrappers for Local Runtime Modules

These plugins wrap the local module implementations and make them
discoverable by the plugin system.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

from runtime.plugins.base import (
    Plugin,
    PluginMetadata,
    PluginType,
    PluginStatus,
)
from runtime.modules import (
    BrowserModule,
    ExecutionModule,
    ToolModule,
    MemoryModule,
    PlanningModule,
    MCPModule,
    FileSystemModule,
    NetworkModule,
    DockerModule,
)
# Import new modules directly from their respective packages
from runtime.conversation.module import ConversationModule
from runtime.agent.module import AgentModule
from runtime.workflow.module import WorkflowModule
from runtime.scheduler.module import SchedulerModule
from runtime.queue.module import QueueModule
from runtime.notification.module import NotificationModule
from runtime.storage.module import StorageModule
from runtime.authentication.module import AuthenticationModule
from runtime.workspace.module import WorkspaceModule
# AI Capabilities modules
from runtime.voice.module import VoiceModule
from runtime.vision.module import VisionModule
from runtime.video.module import VideoModule
from runtime.image.module import ImageModule
from runtime.embedding.module import EmbeddingModule
from runtime.rag.module import RAGModule
from runtime.reasoning.module import ReasoningModule
from runtime.llm.module import LLMModule

logger = logging.getLogger(__name__)


class LocalBrowserPlugin(Plugin):
    """Plugin wrapper for LocalBrowserModule."""

    metadata = PluginMetadata(
        name="local-browser",
        version="1.0.0",
        description="Local Playwright browser automation",
        author="AIPENSA",
        plugin_type=PluginType.BROWSER,
        provides=["browser_automation", "web_scraping", "screenshot"],
        tags={"local", "playwright", "browser"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[BrowserModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        from runtime.browser.local_browser import LocalBrowserModule
        self._module = LocalBrowserModule(self.config)
        await self._module.initialize(runtime, self.config)
        # Register module with runtime using plugin name
        module_name = self.metadata.name
        runtime._modules[module_name] = self._module
        runtime._module_registry.set_instance(module_name, self._module)
        logger.info(f"LocalBrowserPlugin initialized as {module_name}")

    async def start(self) -> None:
        await self._module.start()
        logger.info("LocalBrowserPlugin started")

    async def stop(self) -> None:
        await self._module.stop()
        logger.info("LocalBrowserPlugin stopped")

    async def cleanup(self) -> None:
        await self._module.cleanup()
        self._module = None
        logger.info("LocalBrowserPlugin cleaned up")


class LocalExecutionPlugin(Plugin):
    """Plugin wrapper for LocalExecutionModule."""

    metadata = PluginMetadata(
        name="local-execution",
        version="1.0.0",
        description="Local Python and shell execution",
        author="AIPENSA",
        plugin_type=PluginType.RUNTIME,
        provides=["python_execution", "shell_execution", "sandbox_management"],
        tags={"local", "execution", "python", "shell"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[ExecutionModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        from runtime.execution.local_execution import LocalExecutionModule
        self._module = LocalExecutionModule(self.config)
        await self._module.initialize(runtime, self.config)
        module_name = self.metadata.name
        runtime._modules[module_name] = self._module
        runtime._module_registry.set_instance(module_name, self._module)
        logger.info(f"LocalExecutionPlugin initialized as {module_name}")

    async def start(self) -> None:
        await self._module.start()
        logger.info("LocalExecutionPlugin started")

    async def stop(self) -> None:
        await self._module.stop()
        logger.info("LocalExecutionPlugin stopped")

    async def cleanup(self) -> None:
        await self._module.cleanup()
        self._module = None
        logger.info("LocalExecutionPlugin cleaned up")


class LocalToolsPlugin(Plugin):
    """Plugin wrapper for LocalToolsModule."""

    metadata = PluginMetadata(
        name="local-tools",
        version="1.0.0",
        description="Local tool registration and execution",
        author="AIPENSA",
        plugin_type=PluginType.TOOL,
        provides=["tool_registry", "tool_execution", "function_calling"],
        tags={"local", "tools", "functions"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[ToolModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        from runtime.toolcalling.local_tools import LocalToolsModule
        self._module = LocalToolsModule(self.config)
        await self._module.initialize(runtime, self.config)
        module_name = self.metadata.name
        runtime._modules[module_name] = self._module
        runtime._module_registry.set_instance(module_name, self._module)
        logger.info(f"LocalToolsPlugin initialized as {module_name}")

    async def start(self) -> None:
        await self._module.start()
        logger.info("LocalToolsPlugin started")

    async def stop(self) -> None:
        await self._module.stop()
        logger.info("LocalToolsPlugin stopped")

    async def cleanup(self) -> None:
        await self._module.cleanup()
        self._module = None
        logger.info("LocalToolsPlugin cleaned up")


class LocalMemoryPlugin(Plugin):
    """Plugin wrapper for LocalMemoryModule."""

    metadata = PluginMetadata(
        name="local-memory",
        version="1.0.0",
        description="Local memory storage with search",
        author="AIPENSA",
        plugin_type=PluginType.MEMORY,
        provides=["memory_store", "memory_retrieve", "memory_search"],
        tags={"local", "memory", "storage"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[MemoryModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        from runtime.memory.local_memory import LocalMemoryModule
        self._module = LocalMemoryModule(self.config)
        await self._module.initialize(runtime, self.config)
        module_name = self.metadata.name
        runtime._modules[module_name] = self._module
        runtime._module_registry.set_instance(module_name, self._module)
        logger.info(f"LocalMemoryPlugin initialized as {module_name}")

    async def start(self) -> None:
        await self._module.start()
        logger.info("LocalMemoryPlugin started")

    async def stop(self) -> None:
        await self._module.stop()
        logger.info("LocalMemoryPlugin stopped")

    async def cleanup(self) -> None:
        await self._module.cleanup()
        self._module = None
        logger.info("LocalMemoryPlugin cleaned up")


class LocalPlanningPlugin(Plugin):
    """Plugin wrapper for LocalPlanningModule."""

    metadata = PluginMetadata(
        name="local-planning",
        version="1.0.0",
        description="LLM-based planning and execution",
        author="AIPENSA",
        plugin_type=PluginType.CUSTOM,
        provides=["plan_creation", "plan_execution", "plan_management"],
        tags={"local", "planning", "llm"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[PlanningModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        from runtime.planning.local_planning import LocalPlanningModule
        self._module = LocalPlanningModule(self.config)
        await self._module.initialize(runtime, self.config)
        module_name = self.metadata.name
        runtime._modules[module_name] = self._module
        runtime._module_registry.set_instance(module_name, self._module)
        logger.info(f"LocalPlanningPlugin initialized as {module_name}")

    async def start(self) -> None:
        await self._module.start()
        logger.info("LocalPlanningPlugin started")

    async def stop(self) -> None:
        await self._module.stop()
        logger.info("LocalPlanningPlugin stopped")

    async def cleanup(self) -> None:
        await self._module.cleanup()
        self._module = None
        logger.info("LocalPlanningPlugin cleaned up")


class LocalMCPPlugin(Plugin):
    """Plugin wrapper for LocalMCPModule."""

    metadata = PluginMetadata(
        name="local-mcp",
        version="1.0.0",
        description="Model Context Protocol client",
        author="AIPENSA",
        plugin_type=PluginType.MCP,
        provides=["mcp_connect", "mcp_call_tool", "mcp_list_tools"],
        tags={"local", "mcp", "protocol"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[MCPModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        try:
            from runtime.mcp.local_mcp import LocalMCPModule
            self._module = LocalMCPModule(self.config)
            await self._module.initialize(runtime, self.config)
            module_name = self.metadata.name
            runtime._modules[module_name] = self._module
            runtime._module_registry.set_instance(module_name, self._module)
            logger.info(f"LocalMCPPlugin initialized as {module_name}")
        except Exception as e:
            logger.warning(f"MCP module not available: {e}")
            raise

    async def start(self) -> None:
        if self._module:
            await self._module.start()
        logger.info("LocalMCPPlugin started")

    async def stop(self) -> None:
        if self._module:
            await self._module.stop()
        logger.info("LocalMCPPlugin stopped")

    async def cleanup(self) -> None:
        if self._module:
            await self._module.cleanup()
        self._module = None
        logger.info("LocalMCPPlugin cleaned up")


class LocalFileSystemPlugin(Plugin):
    """Plugin wrapper for LocalFileSystemModule."""

    metadata = PluginMetadata(
        name="local-filesystem",
        version="1.0.0",
        description="Local file system operations",
        author="AIPENSA",
        plugin_type=PluginType.STORAGE,
        provides=["file_read", "file_write", "file_delete", "file_list", "file_search"],
        tags={"local", "filesystem", "storage"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[FileSystemModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        from runtime.filesystem.local_filesystem import LocalFileSystemModule
        self._module = LocalFileSystemModule(self.config)
        await self._module.initialize(runtime, self.config)
        module_name = self.metadata.name
        runtime._modules[module_name] = self._module
        runtime._module_registry.set_instance(module_name, self._module)
        logger.info(f"LocalFileSystemPlugin initialized as {module_name}")

    async def start(self) -> None:
        await self._module.start()
        logger.info("LocalFileSystemPlugin started")

    async def stop(self) -> None:
        await self._module.stop()
        logger.info("LocalFileSystemPlugin stopped")

    async def cleanup(self) -> None:
        await self._module.cleanup()
        self._module = None
        logger.info("LocalFileSystemPlugin cleaned up")


class LocalNetworkPlugin(Plugin):
    """Plugin wrapper for LocalNetworkModule."""

    metadata = PluginMetadata(
        name="local-network",
        version="1.0.0",
        description="HTTP/HTTPS network operations",
        author="AIPENSA",
        plugin_type=PluginType.NETWORK,
        provides=["http_request", "http_get", "http_post", "file_download"],
        tags={"local", "network", "http", "aiohttp"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[NetworkModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        from runtime.network.local_network import LocalNetworkModule
        self._module = LocalNetworkModule(self.config)
        await self._module.initialize(runtime, self.config)
        module_name = self.metadata.name
        runtime._modules[module_name] = self._module
        runtime._module_registry.set_instance(module_name, self._module)
        logger.info(f"LocalNetworkPlugin initialized as {module_name}")

    async def start(self) -> None:
        await self._module.start()
        logger.info("LocalNetworkPlugin started")

    async def stop(self) -> None:
        await self._module.stop()
        logger.info("LocalNetworkPlugin stopped")

    async def cleanup(self) -> None:
        await self._module.cleanup()
        self._module = None
        logger.info("LocalNetworkPlugin cleaned up")


class LocalDockerPlugin(Plugin):
    """Plugin wrapper for LocalDockerModule."""

    metadata = PluginMetadata(
        name="local-docker",
        version="1.0.0",
        description="Local Docker container management",
        author="AIPENSA",
        plugin_type=PluginType.SANDBOX,
        provides=["container_run", "container_stop", "container_logs", "container_inspect"],
        tags={"local", "docker", "container"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[DockerModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        try:
            from runtime.docker.local_docker import LocalDockerModule
            self._module = LocalDockerModule(self.config)
            await self._module.initialize(runtime, self.config)
            module_name = self.metadata.name
            runtime._modules[module_name] = self._module
            runtime._module_registry.set_instance(module_name, self._module)
            logger.info(f"LocalDockerPlugin initialized as {module_name}")
        except Exception as e:
            logger.warning(f"Docker module not available: {e}")
            raise

    async def start(self) -> None:
        if self._module:
            await self._module.start()
        logger.info("LocalDockerPlugin started")

    async def stop(self) -> None:
        if self._module:
            await self._module.stop()
        logger.info("LocalDockerPlugin stopped")

    async def cleanup(self) -> None:
        if self._module:
            await self._module.cleanup()
        self._module = None
        logger.info("LocalDockerPlugin cleaned up")


class LocalConversationPlugin(Plugin):
    """Plugin wrapper for ConversationModule."""

    metadata = PluginMetadata(
        name="conversation",
        version="1.0.0",
        description="Conversation management and message history",
        author="AIPENSA",
        plugin_type=PluginType.CUSTOM,
        provides=["conversation_management", "message_history", "context_management", "streaming"],
        tags={"local", "conversation", "chat", "streaming"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[ConversationModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        from runtime.conversation.module import ConversationModule
        self._module = ConversationModule(self.config)
        await self._module.initialize(runtime, self.config)
        module_name = self.metadata.name
        runtime._modules[module_name] = self._module
        runtime._module_registry.set_instance(module_name, self._module)
        logger.info(f"LocalConversationPlugin initialized as {module_name}")

    async def start(self) -> None:
        await self._module.start()
        logger.info("LocalConversationPlugin started")

    async def stop(self) -> None:
        await self._module.stop()
        logger.info("LocalConversationPlugin stopped")

    async def cleanup(self) -> None:
        await self._module.cleanup()
        self._module = None
        logger.info("LocalConversationPlugin cleaned up")


class LocalAgentPlugin(Plugin):
    """Plugin wrapper for AgentModule."""

    metadata = PluginMetadata(
        name="agent",
        version="1.0.0",
        description="Agent lifecycle management and orchestration",
        author="AIPENSA",
        plugin_type=PluginType.CUSTOM,
        provides=["agent_management", "task_execution", "message_passing", "tool_orchestration"],
        tags={"local", "agent", "orchestration", "automation"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[AgentModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        from runtime.agent.module import AgentModule
        self._module = AgentModule(self.config)
        await self._module.initialize(runtime, self.config)
        module_name = self.metadata.name
        runtime._modules[module_name] = self._module
        runtime._module_registry.set_instance(module_name, self._module)
        logger.info(f"LocalAgentPlugin initialized as {module_name}")

    async def start(self) -> None:
        await self._module.start()
        logger.info("LocalAgentPlugin started")

    async def stop(self) -> None:
        await self._module.stop()
        logger.info("LocalAgentPlugin stopped")

    async def cleanup(self) -> None:
        await self._module.cleanup()
        self._module = None
        logger.info("LocalAgentPlugin cleaned up")


class LocalWorkflowPlugin(Plugin):
    """Plugin wrapper for WorkflowModule."""

    metadata = PluginMetadata(
        name="workflow",
        version="1.0.0",
        description="Workflow orchestration with DAG execution",
        author="AIPENSA",
        plugin_type=PluginType.CUSTOM,
        provides=["workflow_orchestration", "dag_execution", "workflow_management"],
        tags={"local", "workflow", "dag", "automation"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[WorkflowModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        from runtime.workflow.module import WorkflowModule
        self._module = WorkflowModule()
        await self._module.initialize(runtime, self.config)
        module_name = self.metadata.name
        runtime._modules[module_name] = self._module
        runtime._module_registry.set_instance(module_name, self._module)
        logger.info(f"LocalWorkflowPlugin initialized as {module_name}")

    async def start(self) -> None:
        await self._module.start()
        logger.info("LocalWorkflowPlugin started")

    async def stop(self) -> None:
        await self._module.stop()
        logger.info("LocalWorkflowPlugin stopped")

    async def cleanup(self) -> None:
        await self._module.cleanup()
        self._module = None
        logger.info("LocalWorkflowPlugin cleaned up")


class LocalSchedulerPlugin(Plugin):
    """Plugin wrapper for SchedulerModule."""

    metadata = PluginMetadata(
        name="scheduler",
        version="1.0.0",
        description="Task scheduling and cron-like execution",
        author="AIPENSA",
        plugin_type=PluginType.CUSTOM,
        provides=["task_scheduling", "cron_jobs", "scheduled_execution"],
        tags={"local", "scheduler", "cron", "scheduling"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[SchedulerModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        from runtime.scheduler.module import SchedulerModule
        self._module = SchedulerModule()
        await self._module.initialize(runtime, self.config)
        module_name = self.metadata.name
        runtime._modules[module_name] = self._module
        runtime._module_registry.set_instance(module_name, self._module)
        logger.info(f"LocalSchedulerPlugin initialized as {module_name}")

    async def start(self) -> None:
        await self._module.start()
        logger.info("LocalSchedulerPlugin started")

    async def stop(self) -> None:
        await self._module.stop()
        logger.info("LocalSchedulerPlugin stopped")

    async def cleanup(self) -> None:
        await self._module.cleanup()
        self._module = None
        logger.info("LocalSchedulerPlugin cleaned up")


class LocalQueuePlugin(Plugin):
    """Plugin wrapper for QueueModule."""

    metadata = PluginMetadata(
        name="queue",
        version="1.0.0",
        description="Task queue management",
        author="AIPENSA",
        plugin_type=PluginType.CUSTOM,
        provides=["task_queue", "message_queue", "priority_queue"],
        tags={"local", "queue", "task", "message"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[QueueModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        from runtime.queue.module import QueueModule
        self._module = QueueModule()
        await self._module.initialize(runtime, self.config)
        module_name = self.metadata.name
        runtime._modules[module_name] = self._module
        runtime._module_registry.set_instance(module_name, self._module)
        logger.info(f"LocalQueuePlugin initialized as {module_name}")

    async def start(self) -> None:
        await self._module.start()
        logger.info("LocalQueuePlugin started")

    async def stop(self) -> None:
        await self._module.stop()
        logger.info("LocalQueuePlugin stopped")

    async def cleanup(self) -> None:
        await self._module.cleanup()
        self._module = None
        logger.info("LocalQueuePlugin cleaned up")


class LocalNotificationPlugin(Plugin):
    """Plugin wrapper for NotificationModule."""

    metadata = PluginMetadata(
        name="notification",
        version="1.0.0",
        description="Notification delivery and management",
        author="AIPENSA",
        plugin_type=PluginType.CUSTOM,
        provides=["notification_delivery", "alert_management", "webhook_notification"],
        tags={"local", "notification", "alert", "webhook"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[NotificationModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        from runtime.notification.module import NotificationModule
        self._module = NotificationModule()
        await self._module.initialize(runtime, self.config)
        module_name = self.metadata.name
        runtime._modules[module_name] = self._module
        runtime._module_registry.set_instance(module_name, self._module)
        logger.info(f"LocalNotificationPlugin initialized as {module_name}")

    async def start(self) -> None:
        await self._module.start()
        logger.info("LocalNotificationPlugin started")

    async def stop(self) -> None:
        await self._module.stop()
        logger.info("LocalNotificationPlugin stopped")

    async def cleanup(self) -> None:
        await self._module.cleanup()
        self._module = None
        logger.info("LocalNotificationPlugin cleaned up")


class LocalStoragePlugin(Plugin):
    """Plugin wrapper for StorageModule."""

    metadata = PluginMetadata(
        name="storage",
        version="1.0.0",
        description="Data storage and retrieval",
        author="AIPENSA",
        plugin_type=PluginType.STORAGE,
        provides=["data_storage", "blob_storage", "key_value_store"],
        tags={"local", "storage", "blob", "key_value"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[StorageModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        from runtime.storage.module import StorageModule
        self._module = StorageModule()
        await self._module.initialize(runtime, self.config)
        module_name = self.metadata.name
        runtime._modules[module_name] = self._module
        runtime._module_registry.set_instance(module_name, self._module)
        logger.info(f"LocalStoragePlugin initialized as {module_name}")

    async def start(self) -> None:
        await self._module.start()
        logger.info("LocalStoragePlugin started")

    async def stop(self) -> None:
        await self._module.stop()
        logger.info("LocalStoragePlugin stopped")

    async def cleanup(self) -> None:
        await self._module.cleanup()
        self._module = None
        logger.info("LocalStoragePlugin cleaned up")


class LocalAuthenticationPlugin(Plugin):
    """Plugin wrapper for AuthenticationModule."""

    metadata = PluginMetadata(
        name="authentication",
        version="1.0.0",
        description="Authentication and authorization",
        author="AIPENSA",
        plugin_type=PluginType.AUTH,
        provides=["user_authentication", "token_management", "access_control"],
        tags={"local", "authentication", "auth", "security"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[AuthenticationModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        from runtime.authentication.module import AuthenticationModule
        self._module = AuthenticationModule()
        await self._module.initialize(runtime, self.config)
        module_name = self.metadata.name
        runtime._modules[module_name] = self._module
        runtime._module_registry.set_instance(module_name, self._module)
        logger.info(f"LocalAuthenticationPlugin initialized as {module_name}")

    async def start(self) -> None:
        await self._module.start()
        logger.info("LocalAuthenticationPlugin started")

    async def stop(self) -> None:
        await self._module.stop()
        logger.info("LocalAuthenticationPlugin stopped")

    async def cleanup(self) -> None:
        await self._module.cleanup()
        self._module = None
        logger.info("LocalAuthenticationPlugin cleaned up")


class LocalWorkspacePlugin(Plugin):
    """Plugin wrapper for WorkspaceModule."""

    metadata = PluginMetadata(
        name="workspace",
        version="1.0.0",
        description="Workspace and project management",
        author="AIPENSA",
        plugin_type=PluginType.CUSTOM,
        provides=["workspace_management", "project_management", "resource_isolation"],
        tags={"local", "workspace", "project", "isolation"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[WorkspaceModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        from runtime.workspace.module import WorkspaceModule
        self._module = WorkspaceModule()
        await self._module.initialize(runtime, self.config)
        module_name = self.metadata.name
        runtime._modules[module_name] = self._module
        runtime._module_registry.set_instance(module_name, self._module)
        logger.info(f"LocalWorkspacePlugin initialized as {module_name}")

    async def start(self) -> None:
        await self._module.start()
        logger.info("LocalWorkspacePlugin started")

    async def stop(self) -> None:
        await self._module.stop()
        logger.info("LocalWorkspacePlugin stopped")

    async def cleanup(self) -> None:
        await self._module.cleanup()
        self._module = None
        logger.info("LocalWorkspacePlugin cleaned up")


# AI Capabilities Plugins
class LocalVoicePlugin(Plugin):
    """Plugin wrapper for VoiceModule."""

    metadata = PluginMetadata(
        name="voice",
        version="1.0.0",
        description="Voice synthesis and recognition",
        author="AIPENSA",
        plugin_type=PluginType.CUSTOM,
        provides=["text_to_speech", "speech_to_text", "voice_cloning"],
        tags={"local", "voice", "tts", "stt", "ai"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[VoiceModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        from runtime.voice.module import VoiceModule
        self._module = VoiceModule(self.config)
        await self._module.initialize(runtime, self.config)
        module_name = self.metadata.name
        runtime._modules[module_name] = self._module
        runtime._module_registry.set_instance(module_name, self._module)
        logger.info(f"LocalVoicePlugin initialized as {module_name}")

    async def start(self) -> None:
        await self._module.start()
        logger.info("LocalVoicePlugin started")

    async def stop(self) -> None:
        await self._module.stop()
        logger.info("LocalVoicePlugin stopped")

    async def cleanup(self) -> None:
        await self._module.cleanup()
        self._module = None
        logger.info("LocalVoicePlugin cleaned up")


class LocalVisionPlugin(Plugin):
    """Plugin wrapper for VisionModule."""

    metadata = PluginMetadata(
        name="vision",
        version="1.0.0",
        description="Computer vision and image analysis",
        author="AIPENSA",
        plugin_type=PluginType.CUSTOM,
        provides=["object_detection", "image_classification", "ocr", "face_recognition"],
        tags={"local", "vision", "cv", "ai", "image_analysis"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[VisionModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        from runtime.vision.module import VisionModule
        self._module = VisionModule(self.config)
        await self._module.initialize(runtime, self.config)
        module_name = self.metadata.name
        runtime._modules[module_name] = self._module
        runtime._module_registry.set_instance(module_name, self._module)
        logger.info(f"LocalVisionPlugin initialized as {module_name}")

    async def start(self) -> None:
        await self._module.start()
        logger.info("LocalVisionPlugin started")

    async def stop(self) -> None:
        await self._module.stop()
        logger.info("LocalVisionPlugin stopped")

    async def cleanup(self) -> None:
        await self._module.cleanup()
        self._module = None
        logger.info("LocalVisionPlugin cleaned up")


class LocalVideoPlugin(Plugin):
    """Plugin wrapper for VideoModule."""

    metadata = PluginMetadata(
        name="video",
        version="1.0.0",
        description="Video processing and analysis",
        author="AIPENSA",
        plugin_type=PluginType.CUSTOM,
        provides=["video_analysis", "video_transcoding", "frame_extraction", "video_generation"],
        tags={"local", "video", "ai", "processing"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[VideoModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        from runtime.video.module import VideoModule
        self._module = VideoModule(self.config)
        await self._module.initialize(runtime, self.config)
        module_name = self.metadata.name
        runtime._modules[module_name] = self._module
        runtime._module_registry.set_instance(module_name, self._module)
        logger.info(f"LocalVideoPlugin initialized as {module_name}")

    async def start(self) -> None:
        await self._module.start()
        logger.info("LocalVideoPlugin started")

    async def stop(self) -> None:
        await self._module.stop()
        logger.info("LocalVideoPlugin stopped")

    async def cleanup(self) -> None:
        await self._module.cleanup()
        self._module = None
        logger.info("LocalVideoPlugin cleaned up")


class LocalImagePlugin(Plugin):
    """Plugin wrapper for ImageModule."""

    metadata = PluginMetadata(
        name="image",
        version="1.0.0",
        description="Image processing and generation",
        author="AIPENSA",
        plugin_type=PluginType.CUSTOM,
        provides=["image_generation", "image_editing", "image_analysis", "style_transfer"],
        tags={"local", "image", "ai", "generation", "editing"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[ImageModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        from runtime.image.module import ImageModule
        self._module = ImageModule(self.config)
        await self._module.initialize(runtime, self.config)
        module_name = self.metadata.name
        runtime._modules[module_name] = self._module
        runtime._module_registry.set_instance(module_name, self._module)
        logger.info(f"LocalImagePlugin initialized as {module_name}")

    async def start(self) -> None:
        await self._module.start()
        logger.info("LocalImagePlugin started")

    async def stop(self) -> None:
        await self._module.stop()
        logger.info("LocalImagePlugin stopped")

    async def cleanup(self) -> None:
        await self._module.cleanup()
        self._module = None
        logger.info("LocalImagePlugin cleaned up")


class LocalEmbeddingPlugin(Plugin):
    """Plugin wrapper for EmbeddingModule."""

    metadata = PluginMetadata(
        name="embedding",
        version="1.0.0",
        description="Text and multimodal embeddings",
        author="AIPENSA",
        plugin_type=PluginType.CUSTOM,
        provides=["text_embedding", "image_embedding", "similarity_search"],
        tags={"local", "embedding", "ai", "vector", "similarity"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[EmbeddingModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        from runtime.embedding.module import EmbeddingModule
        self._module = EmbeddingModule(self.config)
        await self._module.initialize(runtime, self.config)
        module_name = self.metadata.name
        runtime._modules[module_name] = self._module
        runtime._module_registry.set_instance(module_name, self._module)
        logger.info(f"LocalEmbeddingPlugin initialized as {module_name}")

    async def start(self) -> None:
        await self._module.start()
        logger.info("LocalEmbeddingPlugin started")

    async def stop(self) -> None:
        await self._module.stop()
        logger.info("LocalEmbeddingPlugin stopped")

    async def cleanup(self) -> None:
        await self._module.cleanup()
        self._module = None
        logger.info("LocalEmbeddingPlugin cleaned up")


class LocalRAGPlugin(Plugin):
    """Plugin wrapper for RAGModule."""

    metadata = PluginMetadata(
        name="rag",
        version="1.0.0",
        description="Retrieval-Augmented Generation",
        author="AIPENSA",
        plugin_type=PluginType.CUSTOM,
        provides=["document_indexing", "semantic_search", "question_answering", "context_retrieval"],
        tags={"local", "rag", "ai", "retrieval", "qa"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[RAGModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        from runtime.rag.module import RAGModule
        self._module = RAGModule(self.config)
        await self._module.initialize(runtime, self.config)
        module_name = self.metadata.name
        runtime._modules[module_name] = self._module
        runtime._module_registry.set_instance(module_name, self._module)
        logger.info(f"LocalRAGPlugin initialized as {module_name}")

    async def start(self) -> None:
        await self._module.start()
        logger.info("LocalRAGPlugin started")

    async def stop(self) -> None:
        await self._module.stop()
        logger.info("LocalRAGPlugin stopped")

    async def cleanup(self) -> None:
        await self._module.cleanup()
        self._module = None
        logger.info("LocalRAGPlugin cleaned up")


class LocalReasoningPlugin(Plugin):
    """Plugin wrapper for ReasoningModule."""

    metadata = PluginMetadata(
        name="reasoning",
        version="1.0.0",
        description="Logical reasoning and chain-of-thought",
        author="AIPENSA",
        plugin_type=PluginType.CUSTOM,
        provides=["chain_of_thought", "logical_reasoning", "problem_solving", "deductive_reasoning"],
        tags={"local", "reasoning", "ai", "logic", "cot"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[ReasoningModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        from runtime.reasoning.module import ReasoningModule
        self._module = ReasoningModule(self.config)
        await self._module.initialize(runtime, self.config)
        module_name = self.metadata.name
        runtime._modules[module_name] = self._module
        runtime._module_registry.set_instance(module_name, self._module)
        logger.info(f"LocalReasoningPlugin initialized as {module_name}")

    async def start(self) -> None:
        await self._module.start()
        logger.info("LocalReasoningPlugin started")

    async def stop(self) -> None:
        await self._module.stop()
        logger.info("LocalReasoningPlugin stopped")

    async def cleanup(self) -> None:
        await self._module.cleanup()
        self._module = None
        logger.info("LocalReasoningPlugin cleaned up")


class LocalLLMPlugin(Plugin):
    """Plugin wrapper for LLMModule."""

    metadata = PluginMetadata(
        name="llm",
        version="1.0.0",
        description="Unified LLM interface with multi-provider support",
        author="AIPENSA",
        plugin_type=PluginType.CUSTOM,
        provides=["completion", "streaming", "function_calling", "cost_tracking"],
        tags={"local", "llm", "openai", "anthropic", "ai", "generation"},
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._module: Optional[LLMModule] = None

    async def initialize(self, runtime: "Runtime") -> None:
        from runtime.llm.module import LLMModule
        self._module = LLMModule(self.config)
        await self._module.initialize(runtime, self.config)
        module_name = self.metadata.name
        runtime._modules[module_name] = self._module
        runtime._module_registry.set_instance(module_name, self._module)
        logger.info(f"LocalLLMPlugin initialized as {module_name}")

    async def start(self) -> None:
        await self._module.start()
        logger.info("LocalLLMPlugin started")

    async def stop(self) -> None:
        await self._module.stop()
        logger.info("LocalLLMPlugin stopped")

    async def cleanup(self) -> None:
        await self._module.cleanup()
        self._module = None
        logger.info("LocalLLMPlugin cleaned up")