"""
Pydantic models for AIPENSA Runtime API
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field

from runtime.base.events import RuntimeEventType, RuntimeEvent


# ============================================
# Request Models
# ============================================

class TaskRequestModel(BaseModel):
    type: str
    action: str
    params: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None


class ModuleOperationRequest(BaseModel):
    operation: str
    params: Dict[str, Any] = {}


class CreateConversationRequest(BaseModel):
    title: str = ""
    system_prompt: str = ""
    context: Optional[Dict[str, Any]] = None


class AddMessageRequest(BaseModel):
    role: str  # "system", "user", "assistant", "tool", "function"
    content: str
    message_type: str = "text"
    metadata: Optional[Dict[str, Any]] = None


class BrowserSessionRequest(BaseModel):
    url: str = "about:blank"
    config: Optional[Dict[str, Any]] = None


class BrowserActionRequest(BaseModel):
    action: str
    params: Dict[str, Any]


class ExecuteToolRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None


class ExecutePythonRequest(BaseModel):
    code: str
    sandbox_id: Optional[str] = None
    timeout_seconds: int = 30
    packages: Optional[List[str]] = None
    env_vars: Optional[Dict[str, str]] = None


class WriteFileRequest(BaseModel):
    path: str
    content: str
    encoding: str = "utf-8"
    create_dirs: bool = True


class TaskResult(BaseModel):
    success: bool
    result: Any = None
    error: Optional[str] = None


# ============================================
# Response Models
# ============================================

class ModuleInfo(BaseModel):
    name: str
    state: str
    metadata: Dict[str, Any] = {}


class ModulesResponse(BaseModel):
    modules: Dict[str, ModuleInfo]


class ModuleHealth(BaseModel):
    module: str
    status: str
    healthy: bool
    backends: Any = {}  # Allow any type for backends
    models_loaded: int = 0
    total_requests: int = 0
    details: Dict[str, Any] = {}


class ConversationResponse(BaseModel):
    conversation_id: str
    title: str
    messages: List[Dict[str, Any]] = []
    system_prompt: str = ""
    context: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    created_at: str
    updated_at: str
    max_messages: int
    max_tokens: int


class ConversationsResponse(BaseModel):
    conversations: List[ConversationResponse]


class MessageResponse(BaseModel):
    message_id: str
    role: str
    content: str
    type: str
    tool_calls: List[Dict[str, Any]] = []
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    metadata: Dict[str, Any] = {}
    timestamp: str


class MessagesResponse(BaseModel):
    messages: List[MessageResponse]


class StreamingResponse(BaseModel):
    conversation_id: str
    chunk: str
    done: bool
    metadata: Dict[str, Any] = {}


class StreamRequest(BaseModel):
    model: str
    temperature: float = 0.7
    max_tokens: int = 512


class BrowserSession(BaseModel):
    session_id: str
    url: str


class BrowserSessionsResponse(BaseModel):
    sessions: List[BrowserSession]


class BrowserState(BaseModel):
    url: str = ""
    title: str = ""
    tabs: List[Dict[str, Any]] = []
    pixels_above: int = 0
    pixels_below: int = 0
    viewport_height: int = 0
    interactive_elements: str = ""
    screenshot_base64: Optional[str] = None
    error: Optional[str] = None


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    returns: Dict[str, Any] = {}
    category: str = "general"
    tags: List[str] = []
    requires_approval: bool = False


class ToolsResponse(BaseModel):
    tools: List[ToolDefinition]


class ToolExecution(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    result: Any = None
    error: Optional[str] = None
    success: bool = False


class SearchResult(BaseModel):
    key: str
    value: Any
    score: float
    metadata: Dict[str, Any] = {}


class SearchResults(BaseModel):
    results: List[SearchResult]


class ExecutionResult(BaseModel):
    success: bool
    output: str = ""
    error: Optional[str] = None
    execution_time: float = 0.0


# ============================================
# Workflow API Models
# ============================================

class WorkflowStepModel(BaseModel):
    step_id: str = ""
    name: str = ""
    description: str = ""
    step_type: str = "task"
    action: str = ""
    parameters: Dict[str, Any] = {}
    agent_type: str = "default"
    depends_on: List[str] = []
    condition: Optional[str] = None
    loop_config: Optional[Dict[str, Any]] = None
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout_seconds: int = 300


class WorkflowModel(BaseModel):
    workflow_id: str = ""
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    steps: List[WorkflowStepModel] = []
    variables: Dict[str, Any] = {}
    status: str = "draft"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class WorkflowCreateRequest(BaseModel):
    name: str
    description: str = ""
    steps: List[WorkflowStepModel] = []
    variables: Dict[str, Any] = {}
    version: str = "1.0.0"


class WorkflowUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[List[WorkflowStepModel]] = None
    variables: Optional[Dict[str, Any]] = None
    version: Optional[str] = None


class WorkflowDAGRequest(BaseModel):
    name: str
    description: str = ""
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    variables: Dict[str, Any] = {}


class WorkflowExecuteRequest(BaseModel):
    workflow_id: str = ""
    variables: Dict[str, Any] = {}
    execution_id: Optional[str] = None


class WorkflowExecutionActionRequest(BaseModel):
    execution_id: str


class WorkflowStatusResponse(BaseModel):
    workflow_id: str
    name: str
    description: str
    version: str
    steps: List[WorkflowStepModel]
    variables: Dict[str, Any]
    status: str
    created_at: Optional[str]
    updated_at: Optional[str]


class WorkflowListResponse(BaseModel):
    workflows: List[WorkflowStatusResponse]


class WorkflowExecutionResponse(BaseModel):
    execution_id: str
    workflow_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    current_step: Optional[str] = None
    completed_steps: List[str] = []
    failed_steps: List[str] = []
    step_count: int = 0
    progress: float = 0.0


class WorkflowExecutionListResponse(BaseModel):
    executions: List[WorkflowExecutionResponse]


class WorkflowExportResponse(BaseModel):
    workflow_id: str
    name: str
    description: str
    version: str
    variables: Dict[str, Any]
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


# Existing models continue below...


class FileInfo(BaseModel):
    path: str
    name: str
    size: int
    is_dir: bool
    modified_at: str


class FilesResponse(BaseModel):
    files: List[FileInfo]


class RuntimeInfo(BaseModel):
    runtime_id: str
    name: str
    version: str
    status: str
    started_at: Optional[str] = None
    modules: Dict[str, str] = {}
    plugins: Dict[str, str] = {}


class HealthResponse(BaseModel):
    runtime: Dict[str, Any]
    modules: Dict[str, Any]
    plugins: Dict[str, Any]


# ============================================
# Plugin Models
# ============================================

class PluginInfo(BaseModel):
    id: str
    name: str
    version: str
    description: str
    author: str
    plugin_type: str
    provides: List[str] = []
    tags: List[str] = []
    enabled: bool
    running: bool
    configured: bool
    dependencies: List[str] = []


class PluginsResponse(BaseModel):
    plugins: List[PluginInfo]


class PluginConfigRequest(BaseModel):
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


# ============================================
# Settings Models
# ============================================

class SettingsRequest(BaseModel):
    key: str
    value: Any


class SettingsResponse(BaseModel):
    settings: Dict[str, Any]


class RuntimeConfigResponse(BaseModel):
    runtime_type: Optional[str] = None
    name: Optional[str] = None
    version: Optional[str] = None
    workspace: Optional[str] = None
    log_level: Optional[str] = None
    browser: Optional[Dict[str, Any]] = None
    sandbox: Optional[Dict[str, Any]] = None
    memory: Optional[Dict[str, Any]] = None
    llm: Optional[Dict[str, Any]] = None
    mcp: Optional[Dict[str, Any]] = None
    events: Optional[Dict[str, Any]] = None
    telemetry: Optional[Dict[str, Any]] = None
    security: Optional[Dict[str, Any]] = None
    modules: Optional[List[Dict[str, Any]]] = None
    plugin_configs: Optional[Dict[str, Dict[str, Any]]] = None
    features: Optional[Dict[str, bool]] = None
    max_concurrent_tasks: Optional[int] = None
    max_memory_mb: Optional[int] = None
    max_cpu_percent: Optional[float] = None
    task_timeout_seconds: Optional[int] = None


class ThemeConfig(BaseModel):
    theme: str  # 'light', 'dark', 'system'
    accent_color: Optional[str] = None
    density: Optional[str] = None  # 'comfortable', 'cozy', 'compact'


class BackupExportResponse(BaseModel):
    data: Dict[str, Any]
    timestamp: str
    version: str


class BackupImportRequest(BaseModel):
    data: Dict[str, Any]
    overwrite: bool = False


# ============================================
# Agent Loop Models
# ============================================

class AgentEvent(BaseModel):
    """Single event from the agent loop."""
    event_type: str  # thinking, tool_call_start, tool_call_end, tool_result, final, error, iteration_start, iteration_end
    timestamp: str
    iteration: int
    data: Dict[str, Any] = {}


class AgentStreamRequest(BaseModel):
    """Request for agent streaming."""
    message: str
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    max_iterations: int = 10
    require_approval: bool = True
    available_tools: Optional[List[str]] = None
    system_prompt: str = ""


class AgentStreamResponse(BaseModel):
    """Response for agent stream initiation."""
    conversation_id: str
    status: str = "started"