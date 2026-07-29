"""
Runtime Modules - Core Module Interfaces

Defines the interfaces that all runtime modules must implement.
Each module follows the same lifecycle: initialize -> start -> stop -> cleanup
"""

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Set, Type, Union
import asyncio


class ModuleState(Enum):
    """Module lifecycle state."""

    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ModuleMetadata:
    """Module metadata."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)  # Services provided
    config_schema: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)


class RuntimeModule(ABC):
    """
    Base class for all runtime modules.

    All modules must implement the full lifecycle:
    - initialize(runtime, config) - Setup with runtime reference
    - start() - Begin operation (subscribe to events, open connections)
    - stop() - Graceful shutdown
    - cleanup() - Release resources
    - health_check() - Return health status
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.state = ModuleState.UNINITIALIZED
        self._runtime = None
        self._config = config or {}

    @property
    @abstractmethod
    def metadata(self) -> ModuleMetadata:
        """Module metadata."""
        pass

    @abstractmethod
    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        """Initialize module with runtime reference and configuration."""
        self._runtime = runtime
        self._config = config
        self.state = ModuleState.INITIALIZED

    @abstractmethod
    async def start(self) -> None:
        """Start module operations."""
        self.state = ModuleState.RUNNING

    @abstractmethod
    async def stop(self) -> None:
        """Stop module operations."""
        self.state = ModuleState.STOPPED

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources."""
        self.state = ModuleState.UNINITIALIZED
        self._runtime = None
        self._config = {}

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Return health status."""
        return {
            "module": self.metadata.name,
            "status": self.state.value,
            "healthy": self.state == ModuleState.RUNNING,
        }

    @property
    def runtime(self) -> Optional["Runtime"]:
        return self._runtime

    @property
    def config(self) -> Dict[str, Any]:
        return self._config


# ============================================
# Browser Module Interface
# ============================================

@dataclass
class BrowserSession:
    """Browser session information."""

    session_id: str
    url: str = "about:blank"
    title: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BrowserState:
    """Current browser state."""

    session_id: str
    url: str
    title: str
    viewport: Dict[str, int]
    screenshot: Optional[str] = None  # base64
    dom_snapshot: Optional[str] = None
    console_logs: List[str] = field(default_factory=list)
    network_requests: List[Dict] = field(default_factory=list)
    cookies: List[Dict] = field(default_factory=list)
    local_storage: Dict[str, str] = field(default_factory=dict)
    session_storage: Dict[str, str] = field(default_factory=dict)
    tabs: List[Dict] = field(default_factory=list)
    pixels_above: int = 0
    pixels_below: int = 0
    viewport_height: int = 0
    interactive_elements: str = ""
    screenshot_base64: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class BrowserModule(RuntimeModule):
    """Interface for browser automation modules."""

    @abstractmethod
    async def create_session(
        self,
        url: str = "about:blank",
        config: Optional[Dict[str, Any]] = None
    ) -> BrowserSession:
        """Create a new browser session."""
        pass

    @abstractmethod
    async def navigate(self, session_id: str, url: str, wait_until: str = "networkidle") -> Dict[str, Any]:
        """Navigate to URL."""
        pass

    @abstractmethod
    async def get_state(self, session_id: str) -> BrowserState:
        """Get current browser state."""
        pass

    @abstractmethod
    async def execute_action(
        self,
        session_id: str,
        action: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute browser action (click, type, scroll, etc.)."""
        pass

    @abstractmethod
    async def extract_content(
        self,
        session_id: str,
        goal: str,
        selector: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract content from page based on goal."""
        pass

    @abstractmethod
    async def take_screenshot(
        self,
        session_id: str,
        full_page: bool = True,
        format: str = "png"
    ) -> str:
        """Take screenshot (returns base64)."""
        pass

    @abstractmethod
    async def close_session(self, session_id: str) -> bool:
        """Close browser session."""
        pass

    @abstractmethod
    async def list_sessions(self) -> List[BrowserSession]:
        """List all active sessions."""
        pass


# ============================================
# Execution Module Interface
# ============================================

@dataclass
class ExecutionResult:
    """Code execution result."""

    success: bool
    output: str = ""
    error: Optional[str] = None
    execution_time: float = 0.0
    # Backward compatibility fields
    stdout: str = ""
    stderr: str = ""
    return_value: Any = None
    execution_time_ms: float = 0
    memory_used_mb: float = 0
    exit_code: int = 0


@dataclass
class SandboxInfo:
    """Sandbox/container information."""

    sandbox_id: str
    status: str
    image: str
    created_at: datetime
    resources: Dict[str, Any] = field(default_factory=dict)
    endpoint: Optional[str] = None


class ExecutionModule(RuntimeModule):
    """Interface for code execution modules."""

    @abstractmethod
    async def execute_python(
        self,
        code: str,
        sandbox_id: Optional[str] = None,
        timeout_seconds: int = 30,
        packages: Optional[List[str]] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        """Execute Python code."""
        pass

    @abstractmethod
    async def execute_shell(
        self,
        command: str,
        sandbox_id: Optional[str] = None,
        timeout_seconds: int = 60,
        working_dir: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        """Execute shell command."""
        pass

    @abstractmethod
    async def create_sandbox(
        self,
        image: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> SandboxInfo:
        """Create a new sandbox/container."""
        pass

    @abstractmethod
    async def destroy_sandbox(self, sandbox_id: str) -> bool:
        """Destroy a sandbox."""
        pass

    @abstractmethod
    async def get_sandbox(self, sandbox_id: str) -> Optional[SandboxInfo]:
        """Get sandbox info."""
        pass

    @abstractmethod
    async def list_sandboxes(self) -> List[SandboxInfo]:
        """List all sandboxes."""
        pass


# ============================================
# Tool Module Interface
# ============================================

@dataclass
class ToolDefinition:
    """Tool definition."""

    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    returns: Dict[str, Any] = field(default_factory=dict)
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    requires_approval: bool = False
    version: str = "1.0.0"
    author: str = ""
    examples: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ToolExecution:
    """Tool execution record."""

    tool_name: str
    arguments: Dict[str, Any]
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = ""

    @property
    def success(self) -> bool:
        """Check if tool execution was successful."""
        return self.error is None


class ToolModule(RuntimeModule):
    """Interface for tool management modules."""

    @abstractmethod
    async def register_tool(
        self,
        definition: ToolDefinition,
        handler: callable
    ) -> bool:
        """Register a new tool."""
        pass

    @abstractmethod
    async def unregister_tool(self, tool_name: str) -> bool:
        """Unregister a tool."""
        pass

    @abstractmethod
    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolExecution:
        """Execute a tool."""
        pass

    @abstractmethod
    async def get_tool(self, tool_name: str) -> Optional[ToolDefinition]:
        """Get tool definition."""
        pass

    @abstractmethod
    async def list_tools(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[ToolDefinition]:
        """List available tools."""
        pass

    @abstractmethod
    async def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get tool JSON schema for LLM."""
        pass


# ============================================
# Memory Module Interface
# ============================================

@dataclass
class MemoryEntry:
    """Memory entry."""

    key: str
    value: Any
    memory_type: str = "default"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    size_bytes: int = 0


@dataclass
class SearchResult:
    """Memory search result."""

    entry: MemoryEntry
    score: float
    snippet: str = ""


class MemoryModule(RuntimeModule):
    """Interface for memory/storage modules."""

    @abstractmethod
    async def store(
        self,
        key: str,
        value: Any,
        memory_type: str = "default",
        tags: Optional[List[str]] = None,
        ttl_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryEntry:
        """Store a value in memory."""
        pass

    @abstractmethod
    async def retrieve(
        self,
        key: str,
        memory_type: str = "default"
    ) -> Optional[MemoryEntry]:
        """Retrieve a value from memory."""
        pass

    @abstractmethod
    async def delete(self, key: str, memory_type: str = "default") -> bool:
        """Delete a value from memory."""
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        memory_type: str = "default",
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search memory."""
        pass

    @abstractmethod
    async def clear(self, memory_type: Optional[str] = None) -> int:
        """Clear memory (optionally by type)."""
        pass

    @abstractmethod
    async def list_keys(
        self,
        memory_type: str = "default",
        pattern: Optional[str] = None,
        limit: int = 100
    ) -> List[str]:
        """List memory keys."""
        pass

    @abstractmethod
    async def get_stats(self, memory_type: Optional[str] = None) -> Dict[str, Any]:
        """Get memory statistics."""
        pass


# ============================================
# Planning Module Interface
# ============================================

class PlanStatus(Enum):
    """Plan execution status."""

    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    """Plan step status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """Plan step."""

    step_id: str
    name: str
    description: str
    action: str  # Tool/action to execute
    parameters: Dict[str, Any] = field(default_factory=dict)
    agent_type: str = "default"
    dependencies: List[str] = field(default_factory=list)  # step_ids
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class Plan:
    """Execution plan."""

    plan_id: str
    goal: str
    context: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    steps: List[PlanStep] = field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PlanningModule(RuntimeModule):
    """Interface for planning modules."""

    @abstractmethod
    async def create_plan(
        self,
        goal: str,
        context: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None
    ) -> Plan:
        """Create an execution plan from goal."""
        pass

    @abstractmethod
    async def execute_plan(
        self,
        plan_id: str,
        agents: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a plan with given agents."""
        pass

    @abstractmethod
    async def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Get plan by ID."""
        pass

    @abstractmethod
    async def update_plan(self, plan: Plan) -> Plan:
        """Update plan."""
        pass

    @abstractmethod
    async def cancel_plan(self, plan_id: str) -> bool:
        """Cancel plan execution."""
        pass

    @abstractmethod
    async def list_plans(
        self,
        status: Optional[PlanStatus] = None,
        limit: int = 50
    ) -> List[Plan]:
        """List plans."""
        pass


# ============================================
# MCP Module Interface
# ============================================

@dataclass
class MCPServer:
    """MCP Server connection info."""

    server_id: str
    name: str
    transport: str  # sse, stdio
    endpoint: str
    status: str = "disconnected"
    tools: List[Dict[str, Any]] = field(default_factory=list)
    connected_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MCPModule(RuntimeModule):
    """Interface for MCP (Model Context Protocol) modules."""

    @abstractmethod
    async def connect_server(
        self,
        server_id: str,
        config: Dict[str, Any]
    ) -> MCPServer:
        """Connect to MCP server."""
        pass

    @abstractmethod
    async def disconnect_server(self, server_id: str) -> bool:
        """Disconnect from MCP server."""
        pass

    @abstractmethod
    async def call_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Any:
        """Call MCP tool."""
        pass

    @abstractmethod
    async def list_servers(self) -> List[MCPServer]:
        """List connected servers."""
        pass

    @abstractmethod
    async def get_server(self, server_id: str) -> Optional[MCPServer]:
        """Get server info."""
        pass

    @abstractmethod
    async def get_server_tools(self, server_id: str) -> List[Dict[str, Any]]:
        """Get available tools from server."""
        pass


# ============================================
# File System Module Interface
# ============================================

@dataclass
class FileInfo:
    """File information."""

    path: str
    name: str
    is_directory: bool
    size: int
    modified_at: datetime
    created_at: datetime
    mime_type: Optional[str] = None
    permissions: Optional[str] = None
    checksum: Optional[str] = None


class FileSystemModule(RuntimeModule):
    """Interface for file system modules."""

    @abstractmethod
    async def read_file(self, path: str, encoding: str = "utf-8") -> str:
        """Read file contents."""
        pass

    @abstractmethod
    async def write_file(
        self,
        path: str,
        content: str,
        encoding: str = "utf-8",
        create_dirs: bool = True
    ) -> FileInfo:
        """Write file contents."""
        pass

    @abstractmethod
    async def delete_file(self, path: str) -> bool:
        """Delete file or directory."""
        pass

    @abstractmethod
    async def list_directory(
        self,
        path: str,
        recursive: bool = False,
        pattern: Optional[str] = None
    ) -> List[FileInfo]:
        """List directory contents."""
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if path exists."""
        pass

    @abstractmethod
    async def copy_file(self, src: str, dst: str) -> FileInfo:
        """Copy file."""
        pass

    @abstractmethod
    async def move_file(self, src: str, dst: str) -> FileInfo:
        """Move/rename file."""
        pass

    @abstractmethod
    async def get_file_info(self, path: str) -> Optional[FileInfo]:
        """Get file info."""
        pass

    @abstractmethod
    async def search_files(
        self,
        pattern: str,
        path: str = ".",
        content_pattern: Optional[str] = None
    ) -> List[FileInfo]:
        """Search files by name and optionally content."""
        pass


# Add uuid import
import uuid


# ============================================
# Module Registry
# ============================================

class ModuleRegistry:
    """Registry for runtime modules."""

    def __init__(self):
        self._module_classes: Dict[str, Type[RuntimeModule]] = {}
        self._instances: Dict[str, RuntimeModule] = {}

    def register(self, module_class: Type[RuntimeModule]) -> None:
        """Register a module class."""
        name = module_class.metadata.name
        self._module_classes[name] = module_class

    def unregister(self, name: str) -> bool:
        """Unregister a module."""
        if name in self._module_classes:
            del self._module_classes[name]
            return True
        return False

    def get_module_class(self, name: str) -> Optional[Type[RuntimeModule]]:
        """Get module class by name."""
        return self._module_classes.get(name)

    def set_instance(self, name: str, instance: RuntimeModule) -> None:
        """Set a module instance."""
        self._instances[name] = instance

    def get_instance(self, name: str) -> Optional[RuntimeModule]:
        """Get a module instance."""
        return self._instances.get(name)

    def list_modules(self) -> List[str]:
        """List registered module names."""
        return list(self._module_classes.keys())

    def list_instances(self) -> List[str]:
        """List loaded instance names."""
        return list(self._instances.keys())


# ============================================
# Network Module Interface
# ============================================

@dataclass
class NetworkRequest:
    """Network request."""
    url: str
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    body: Any = None
    params: Dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 30


@dataclass
class NetworkResponse:
    """Network response."""
    status_code: int
    body: bytes
    headers: Dict[str, str]
    duration_ms: float = 0
    success: bool = True
    error: Optional[str] = None


class NetworkModule(RuntimeModule):
    """Interface for network/HTTP modules."""

    @abstractmethod
    async def request(self, request: NetworkRequest) -> NetworkResponse:
        """Make HTTP request."""
        pass

    @abstractmethod
    async def get(self, url: str, **kwargs) -> NetworkResponse:
        """HTTP GET request."""
        pass

    @abstractmethod
    async def post(self, url: str, **kwargs) -> NetworkResponse:
        """HTTP POST request."""
        pass

    @abstractmethod
    async def put(self, url: str, **kwargs) -> NetworkResponse:
        """HTTP PUT request."""
        pass

    @abstractmethod
    async def delete(self, url: str, **kwargs) -> NetworkResponse:
        """HTTP DELETE request."""
        pass

    @abstractmethod
    async def patch(self, url: str, **kwargs) -> NetworkResponse:
        """HTTP PATCH request."""
        pass

    @abstractmethod
    async def head(self, url: str, **kwargs) -> NetworkResponse:
        """HTTP HEAD request."""
        pass

    @abstractmethod
    async def download_file(
        self,
        url: str,
        destination: str,
        progress_callback: Optional[callable] = None,
        **kwargs
    ) -> NetworkResponse:
        """Download a file."""
        pass

    @abstractmethod
    async def upload_file(
        self,
        url: str,
        file_path: str,
        field_name: str = "file",
        additional_data: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> NetworkResponse:
        """Upload a file."""
        pass


# ============================================
# Docker Module Interface
# ============================================

@dataclass
class ContainerInfo:
    """Container information."""
    container_id: str
    name: str
    image: str
    status: str
    created_at: datetime
    ports: Dict[str, Any] = field(default_factory=dict)
    env_vars: Dict[str, str] = field(default_factory=dict)
    resources: Dict[str, Any] = field(default_factory=dict)


class DockerModule(RuntimeModule):
    """Interface for Docker/container modules."""

    @abstractmethod
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
        pass

    @abstractmethod
    async def stop_container(self, container_id: str, timeout: int = 10) -> bool:
        """Stop a container."""
        pass

    @abstractmethod
    async def remove_container(self, container_id: str, force: bool = False) -> bool:
        """Remove a container."""
        pass

    @abstractmethod
    async def get_logs(
        self,
        container_id: str,
        tail: int = 100,
        follow: bool = False,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> AsyncIterator[str]:
        """Get container logs."""
        pass

    @abstractmethod
    async def inspect_container(self, container_id: str) -> Optional[ContainerInfo]:
        """Inspect a container."""
        pass

    @abstractmethod
    async def list_containers(self, all: bool = True) -> List[ContainerInfo]:
        """List containers."""
        pass

    @abstractmethod
    async def build_image(
        self,
        path: str,
        tag: str,
        dockerfile: str = "Dockerfile",
        **kwargs
    ) -> str:
        """Build a Docker image."""
        pass

    @abstractmethod
    async def pull_image(self, image: str) -> None:
        """Pull a Docker image."""
        pass