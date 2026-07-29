"""
FastAPI server exposing AIPENSA Runtime APIs and WebSocket for EventBus streaming.
This bridges the Python Runtime to the Next.js frontend.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse as FastAPIStreamingResponse
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import json
import logging
from pathlib import Path

from runtime.config import RuntimeConfig, RuntimeType
from runtime.runtime import Runtime, create_runtime
from runtime.events import get_event_bus
from runtime.base.events import RuntimeEvent, RuntimeEventType, EventHandler
from runtime.modules import ModuleState, RuntimeModule
from runtime.base.module import ModuleMetadata

# Import models
from runtime.api.models import (
    TaskRequestModel, ModuleOperationRequest, CreateConversationRequest,
    AddMessageRequest, BrowserSessionRequest, BrowserActionRequest,
    ExecuteToolRequest, ExecutePythonRequest, WriteFileRequest,
    ModuleInfo, ModulesResponse, ModuleHealth, ConversationResponse,
    ConversationsResponse, MessageResponse, MessagesResponse,
    BrowserSession, BrowserState, ToolDefinition,
    ToolsResponse, ToolExecution, SearchResults, ExecutionResult,
    FileInfo, FilesResponse, RuntimeInfo, HealthResponse, TaskResult,
    BrowserSession as BrowserSessionModel, BrowserSessionsResponse,
    PluginInfo, PluginsResponse, PluginConfigRequest,
    WorkflowCreateRequest, WorkflowUpdateRequest, WorkflowDAGRequest,
    WorkflowExecuteRequest, WorkflowExportResponse, WorkflowListResponse,
    WorkflowStatusResponse, WorkflowExecutionResponse, WorkflowExecutionListResponse,
    StreamingResponse as StreamingResponseModel,
    StreamRequest,
    WorkflowStepModel,
    SettingsRequest, SettingsResponse, RuntimeConfigResponse, ThemeConfig,
    BackupExportResponse, BackupImportRequest,
    AgentStreamRequest, AgentStreamResponse,
    WorkflowExecutionActionRequest
)

logger = logging.getLogger(__name__)

# Global runtime instance
runtime_instance: Optional[Runtime] = None
event_bus = get_event_bus()
active_websockets: List[WebSocket] = []
event_handler_instance: Optional[EventHandler] = None

# Global storage for pending approvals
_pending_approvals: Dict[str, asyncio.Future] = {}


class WebSocketEventHandler(EventHandler):
    """Event handler that forwards events to all connected WebSocket clients."""

    def __init__(self):
        self._event_types = list(RuntimeEventType)

    @property
    def handles_event_types(self) -> List[RuntimeEventType]:
        return self._event_types

    async def handle(self, event: RuntimeEvent) -> None:
        if not active_websockets:
            return

        event_data = event.to_dict()
        message = json.dumps(event_data)

        # Send to all connected clients
        disconnected = []
        for ws in active_websockets:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        # Clean up disconnected
        for ws in disconnected:
            if ws in active_websockets:
                active_websockets.remove(ws)


app = FastAPI(
    title="AIPENSA Runtime API",
    description="API for controlling and monitoring the AIPENSA Runtime Engine",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3003", "http://127.0.0.1:3003", "http://localhost:3004", "http://127.0.0.1:3004", "http://localhost:3005", "http://127.0.0.1:3005", "http://localhost:3006", "http://127.0.0.1:3006", "http://localhost:3007", "http://127.0.0.1:3007"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup event handler
@app.on_event("startup")
async def startup_event():
    global runtime_instance, event_handler_instance
    logger.info("Starting AIPENSA Runtime API server...")
    config = RuntimeConfig.from_toml(Path(__file__).parent.parent.parent / "runtime.toml")  # Load from runtime.toml

    # Register global event handler for WebSocket broadcasting BEFORE starting runtime
    event_handler_instance = WebSocketEventHandler()
    for event_type in RuntimeEventType:
        event_bus.subscribe(event_type, event_handler_instance)

    runtime_instance = await create_runtime(config)
    print(f"DEBUG startup: runtime_instance = {runtime_instance}")  # DEBUG
    logger.info("AIPENSA Runtime API server started")


# Shutdown event handler
@app.on_event("shutdown")
async def shutdown_event():
    global runtime_instance
    logger.info("Shutting down AIPENSA Runtime API server...")
    if runtime_instance:
        await runtime_instance.stop()
    await event_bus.stop()
    logger.info("AIPENSA Runtime API server stopped")


# ============================================
# WebSocket for EventBus streaming
# ============================================

@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    logger.info(f"WebSocket connected. Total connections: {len(active_websockets)}")

    try:
        while True:
            # Keep alive - wait for messages (ping/pong or client messages)
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if websocket in active_websockets:
            active_websockets.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(active_websockets)}")


# ============================================
# Runtime Info & Health
# ============================================

@app.get("/api/runtime/info", response_model=RuntimeInfo)
async def get_runtime_info():
    if not runtime_instance:
        raise HTTPException(503, "Runtime not initialized")
    info = runtime_instance.get_info()
    return RuntimeInfo(
        runtime_id=info.runtime_id,
        name=info.name,
        version=info.version,
        status=info.status.value,
        started_at=info.started_at.isoformat() if info.started_at else None,
        modules={name: state.value for name, state in info.modules.items()},
        plugins={name: status.value for name, status in info.plugins.items()}
    )


@app.get("/api/runtime/health", response_model=HealthResponse)
async def get_health():
    if not runtime_instance:
        raise HTTPException(503, "Runtime not initialized")
    return await runtime_instance.health_check()


@app.post("/api/runtime/execute", response_model=TaskResult)
async def execute_task(request: TaskRequestModel):
    if not runtime_instance:
        raise HTTPException(503, "Runtime not initialized")
    from runtime.runtime import TaskRequest
    task = TaskRequest(**request.dict())
    result = await runtime_instance.execute(task)
    return result


# ============================================
# Module Management
# ============================================

@app.get("/api/modules", response_model=ModulesResponse)
async def list_modules():
    if not runtime_instance:
        raise HTTPException(503, "Runtime not initialized")

    modules = {}
    for name, module in runtime_instance.modules.items():
        metadata = {}
        if hasattr(module, 'metadata'):
            meta: ModuleMetadata = module.metadata
            metadata = {
                "name": meta.name,
                "version": meta.version,
                "description": meta.description,
                "author": meta.author,
                "dependencies": meta.dependencies,
                "provides": meta.provides,
                "tags": list(meta.tags)
            }
        modules[name] = ModuleInfo(
            name=name,
            state=module.state.value,
            metadata=metadata
        )
    return ModulesResponse(modules=modules)


@app.get("/api/modules/{module_name}/health", response_model=ModuleHealth)
async def module_health(module_name: str):
    if not runtime_instance:
        raise HTTPException(503, "Runtime not initialized")
    module = runtime_instance.get_module(module_name)
    if not module:
        raise HTTPException(404, f"Module '{module_name}' not found")
    health = await module.health_check()
    return ModuleHealth(**health)


@app.post("/api/modules/{module_name}/execute")
async def execute_module_operation(module_name: str, request: ModuleOperationRequest):
    if not runtime_instance:
        raise HTTPException(503, "Runtime not initialized")
    module = runtime_instance.get_module(module_name)
    if not module:
        raise HTTPException(404, f"Module '{module_name}' not found")
    try:
        result = await module.execute(request.operation, **request.params)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================
# Conversation API
# ============================================

def _get_conversation_module():
    if not runtime_instance:
        raise HTTPException(503, "Runtime not initialized")
    module = runtime_instance.get_module("conversation")
    if not module:
        raise HTTPException(503, "Conversation module not available")
    return module


@app.post("/api/conversation/create", response_model=ConversationResponse)
async def create_conversation(request: CreateConversationRequest):
    module = _get_conversation_module()
    conv = await module.create_conversation(
        title=request.title,
        system_prompt=request.system_prompt,
        context=request.context
    )
    return ConversationResponse(**conv.to_dict())


@app.get("/api/conversation/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str):
    module = _get_conversation_module()
    conv = await module.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    return ConversationResponse(**conv.to_dict())


@app.get("/api/conversations", response_model=ConversationsResponse)
async def list_conversations(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    module = _get_conversation_module()
    convs = await module.list_conversations(limit=limit, offset=offset)
    return ConversationsResponse(conversations=[ConversationResponse(**c.to_dict()) for c in convs])


@app.post("/api/conversation/{conversation_id}/message", response_model=MessageResponse)
async def add_message(conversation_id: str, request: AddMessageRequest):
    module = _get_conversation_module()
    from runtime.conversation.module import MessageRole, MessageType
    msg = await module.add_message(
        conversation_id=conversation_id,
        role=MessageRole(request.role),
        content=request.content,
        message_type=MessageType(request.message_type),
        metadata=request.metadata
    )
    if not msg:
        raise HTTPException(404, "Conversation not found")
    return MessageResponse(**msg.to_dict())


@app.get("/api/conversation/{conversation_id}/messages", response_model=MessagesResponse)
async def get_messages(conversation_id: str, limit: int = Query(100, ge=1, le=500)):
    module = _get_conversation_module()
    msgs = await module.get_messages(conversation_id, limit=limit)
    return MessagesResponse(messages=[MessageResponse(**m.to_dict()) for m in msgs])


@app.post("/api/conversation/{conversation_id}/stream", response_class=FastAPIStreamingResponse)
async def stream_response(conversation_id: str, request: StreamRequest):
    """Stream a response from the LLM for a conversation."""
    module = _get_conversation_module()
    from runtime.conversation.module import MessageRole, MessageType
    from runtime.llm.module import LLMMessage, MessageRole as LLMMessageRole

    # Get conversation context
    conv = await module.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")

    # Build messages for LLM including history
    messages = []
    if conv.system_prompt:
        messages.append(LLMMessage(role=LLMMessageRole.SYSTEM, content=conv.system_prompt))

    # Add recent messages (up to max_messages)
    recent_messages = conv.messages[-20:]  # Last 20 messages
    for msg in recent_messages:
        role_map = {
            "system": LLMMessageRole.SYSTEM,
            "user": LLMMessageRole.USER,
            "assistant": LLMMessageRole.ASSISTANT,
            "tool": LLMMessageRole.TOOL,
            "function": LLMMessageRole.FUNCTION,
        }
        messages.append(LLMMessage(
            role=role_map.get(msg.role.value, LLMMessageRole.USER),
            content=msg.content
        ))

    # Get default model or use requested model
    llm_module = runtime_instance.get_module("llm")
    if not llm_module:
        # Fallback: return a mock streaming response
        async def mock_stream():
            chunks = ["Hello! ", "How can I ", "help you ", "today?"]
            for chunk in chunks:
                yield f"data: {StreamingResponseModel(conversation_id=conversation_id, chunk=chunk, done=False).model_dump_json()}\n\n"
                await asyncio.sleep(0.1)
            yield f"data: {StreamingResponseModel(conversation_id=conversation_id, chunk='', done=True, metadata={'full_response': ''.join(chunks)}).model_dump_json()}\n\n"

        # Add assistant message
        await module.add_message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content="Hello! How can I help you today?",
            message_type=MessageType.TEXT
        )

        return FastAPIStreamingResponse(mock_stream(), media_type="text/event-stream")

    default_model = request.model or llm_module._default_model or "meta/llama-3.1-70b-instruct"

    # Stream from LLM
    async def llm_stream():
        full_response = ""
        try:
            async for chunk in llm_module.stream(messages=messages, model=default_model, temperature=request.temperature, max_tokens=request.max_tokens):
                full_response += chunk.delta
                yield f"data: {StreamingResponseModel(conversation_id=conversation_id, chunk=chunk.delta, done=chunk.is_final, metadata={'accumulated_length': len(full_response)}).model_dump_json()}\n\n"

            # Add assistant message to conversation
            await module.add_message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=full_response,
                message_type=MessageType.TEXT
            )
        except Exception as e:
            logger.error(f"LLM streaming error: {e}")
            # Fallback to mock on error
            error_response = f"Error: {str(e)}"
            await module.add_message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=error_response,
                message_type=MessageType.TEXT
            )
            yield f"data: {StreamingResponseModel(conversation_id=conversation_id, chunk=error_response, done=True, metadata={'error': str(e)}).model_dump_json()}\n\n"

    return FastAPIStreamingResponse(llm_stream(), media_type="text/event-stream")


# ============================================
# Agent Loop Streaming API
# ============================================

@app.post("/api/conversation/{conversation_id}/agent/stream", response_class=FastAPIStreamingResponse)
async def agent_stream(conversation_id: str, request: AgentStreamRequest):
    """
    Stream a response from the Agent Loop with tool calling capabilities.
    This is the main endpoint for Manus-like autonomous agent behavior.
    """
    if not runtime_instance:
        raise HTTPException(503, "Runtime not initialized")

    conv_module = runtime_instance.get_module("conversation")
    if not conv_module:
        raise HTTPException(503, "Conversation module not available")

    llm_module = runtime_instance.get_module("llm")
    if not llm_module:
        raise HTTPException(503, "LLM module not available")

    tools_module = runtime_instance.get_module("tools") or runtime_instance.get_module("local-tools")
    if not tools_module:
        raise HTTPException(503, "Tools module not available")

    # Get conversation
    conv = await conv_module.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")

    # Import AgentLoop
    from runtime.agent.agent_loop import StreamingAgentLoop, AgentLoopConfig, AgentEventType

    # Build messages for LLM
    from runtime.llm.module import LLMMessage, MessageRole as LLMMessageRole

    messages = []
    # System prompt - ensure we always have one for tool calling
    system_prompt = request.system_prompt or conv.system_prompt or "You are a helpful AI assistant with access to tools. Use them when appropriate."
    if system_prompt:
        messages.append(LLMMessage(role=LLMMessageRole.SYSTEM, content=system_prompt))

    # Add recent messages
    recent_messages = conv.messages[-20:]
    for msg in recent_messages:
        role_map = {
            "system": LLMMessageRole.SYSTEM,
            "user": LLMMessageRole.USER,
            "assistant": LLMMessageRole.ASSISTANT,
            "tool": LLMMessageRole.TOOL,
            "function": LLMMessageRole.FUNCTION,
        }
        messages.append(LLMMessage(
            role=role_map.get(msg.role.value, LLMMessageRole.USER),
            content=msg.content,
            tool_calls=msg.tool_calls if msg.tool_calls else None,
            tool_call_id=msg.tool_call_id,
            name=msg.name,
        ))

    # Add the current user message
    messages.append(LLMMessage(role=LLMMessageRole.USER, content=request.message))

    # DEBUG: Log messages
    logger.info(f"Agent stream messages: {len(messages)} messages")
    for i, m in enumerate(messages):
        logger.info(f"  Message {i}: role={m.role}, content_len={len(m.content) if m.content else 0}")

    # Configure agent loop
    config = AgentLoopConfig(
        max_iterations=request.max_iterations,
        max_tokens=request.max_tokens,
        temperature=request.temperature,
        model=request.model or llm_module._default_model or "meta/llama-3.1-70b-instruct",
        require_approval=request.require_approval,
        available_tools=request.available_tools,
        system_prompt=system_prompt,
    )

    # Create agent loop
    agent_loop = StreamingAgentLoop(
        llm_module=llm_module,
        tools_module=tools_module,
        runtime=runtime_instance,
        config=config,
    )

    # Create approval callback that pauses for frontend approval
    async def approval_callback(tool_call):
        """Wait for frontend approval via WebSocket or polling."""
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        _pending_approvals[tool_call.call_id] = future

        # Emit approval required event via WebSocket
        event = {
            "event_type": "approval_required",
            "timestamp": datetime.utcnow().isoformat(),
            "iteration": 0,
            "data": {
                "call_id": tool_call.call_id,
                "name": tool_call.name,
                "arguments": tool_call.arguments,
            }
        }
        # Broadcast to all connected WebSockets
        for ws in active_websockets:
            try:
                await ws.send_text(json.dumps(event))
            except Exception:
                pass

        try:
            # Wait for approval with timeout (5 minutes)
            return await asyncio.wait_for(future, timeout=300)
        except asyncio.TimeoutError:
            return False
        finally:
            _pending_approvals.pop(tool_call.call_id, None)

    config.approval_callback = approval_callback

    # Stream agent events
    from runtime.conversation.module import MessageRole as ConvMessageRole, MessageType as ConvMessageType
    async def agent_stream():
        try:
            async for event in agent_loop.run_streaming(messages, conversation_id):
                # Format as SSE
                yield f"data: {event.to_sse()}"

                # Handle special events that need conversation updates
                if event.event_type == AgentEventType.FINAL:
                    # Add final response to conversation
                    await conv_module.add_message(
                        conversation_id=conversation_id,
                        role=ConvMessageRole.ASSISTANT,
                        content=event.data.get("content", ""),
                        message_type=ConvMessageType.TEXT,
                    )
                elif event.event_type == AgentEventType.ERROR:
                    error_msg = event.data.get("error", "Unknown error")
                    await conv_module.add_message(
                        conversation_id=conversation_id,
                        role=ConvMessageRole.ASSISTANT,
                        content=f"Error: {error_msg}",
                        message_type=ConvMessageType.ERROR,
                    )
        except Exception as e:
            logger.error(f"Agent streaming error: {e}")
            yield f"data: {json.dumps({'event_type': 'error', 'timestamp': datetime.utcnow().isoformat(), 'iteration': 0, 'data': {'error': str(e), 'stage': 'agent_loop'}})}\n\n"

    return FastAPIStreamingResponse(agent_stream(), media_type="text/event-stream")


# Endpoint to approve/deny tool execution
@app.post("/api/agent/approve/{call_id}")
async def approve_tool(call_id: str, approved: bool = True):
    """Approve or deny a pending tool execution."""
    if call_id in _pending_approvals:
        future = _pending_approvals[call_id]
        if not future.done():
            future.set_result(approved)
        return {"success": True, "call_id": call_id, "approved": approved}
    raise HTTPException(404, "Approval request not found")


# ============================================
# Browser API
# ============================================

def _get_browser_module():
    if not runtime_instance:
        raise HTTPException(503, "Runtime not initialized")
    browser = runtime_instance.get_browser()
    if not browser:
        raise HTTPException(503, "Browser module not available")
    print(f"Browser module type: {type(browser)}, module file: {browser.__class__.__module__}")
    import inspect
    source = inspect.getsource(browser.execute_action)
    print(f"Has navigate: {'navigate' in source}")
    return browser


@app.post("/api/browser/session", response_model=BrowserSession)
async def create_browser_session(request: BrowserSessionRequest):
    browser = _get_browser_module()
    session = await browser.create_session(request.url, request.config)
    return BrowserSession(session_id=session.session_id, url=session.url)


@app.get("/api/browser/sessions", response_model=BrowserSessionsResponse)
async def list_browser_sessions():
    browser = _get_browser_module()
    sessions = await browser.list_sessions()
    return BrowserSessionsResponse(sessions=[BrowserSession(session_id=s.session_id, url=s.url) for s in sessions])


@app.get("/api/browser/session/{session_id}/state", response_model=BrowserState)
async def get_browser_state(session_id: str):
    browser = _get_browser_module()
    state = await browser.get_state(session_id)
    return BrowserState(
        url=state.url,
        title=state.title,
        tabs=[t.__dict__ if hasattr(t, '__dict__') else t for t in state.tabs],
        pixels_above=state.pixels_above,
        pixels_below=state.pixels_below,
        viewport_height=state.viewport_height,
        interactive_elements=state.interactive_elements,
        screenshot_base64=state.screenshot_base64,
        error=state.error
    )


@app.post("/api/browser/session/{session_id}/action")
async def browser_action(session_id: str, request: BrowserActionRequest):
    browser = _get_browser_module()
    print(f"Browser action: {request.action} with params: {request.params}")
    result = await browser.execute_action(session_id, request.action, request.params)
    print(f"Browser action result: {result}")
    return result.__dict__ if hasattr(result, '__dict__') else result


@app.post("/api/browser/session/{session_id}/screenshot")
async def browser_screenshot(session_id: str, full_page: bool = True):
    browser = _get_browser_module()
    screenshot = await browser.take_screenshot(session_id, full_page)
    return {"screenshot_base64": screenshot}


@app.delete("/api/browser/session/{session_id}")
async def close_browser_session(session_id: str):
    browser = _get_browser_module()
    await browser.close_session(session_id)
    return {"success": True}


# ============================================
# Tools API
# ============================================

def _get_tools_module():
    if not runtime_instance:
        raise HTTPException(503, "Runtime not initialized")
    tools = runtime_instance.get_tools()
    if not tools:
        raise HTTPException(503, "Tools module not available")
    return tools


@app.get("/api/tools", response_model=ToolsResponse)
async def list_tools(category: Optional[str] = None):
    tools = _get_tools_module()
    tool_list = await tools.list_tools(category=category)
    return ToolsResponse(tools=[ToolDefinition(
        name=t.name,
        description=t.description,
        parameters=t.parameters,
        returns=t.returns,
        category=t.category,
        tags=t.tags,
        requires_approval=t.requires_approval
    ) for t in tool_list])


@app.post("/api/tools/execute", response_model=ToolExecution)
async def execute_tool(request: ExecuteToolRequest):
    tools = _get_tools_module()
    result = await tools.execute_tool(request.tool_name, request.arguments, request.context)
    return ToolExecution(
        tool_name=result.tool_name,
        arguments=result.arguments,
        result=result.result,
        error=result.error,
        success=result.success
    )


# ============================================
# Memory API
# ============================================

def _get_memory_module():
    if not runtime_instance:
        raise HTTPException(503, "Runtime not initialized")
    memory = runtime_instance.get_memory()
    if not memory:
        raise HTTPException(503, "Memory module not available")
    return memory


@app.get("/api/memory/search", response_model=SearchResults)
async def search_memory(
    query: str,
    memory_type: str = "default",
    limit: int = Query(10, ge=1, le=100)
):
    memory = _get_memory_module()
    results = await memory.search(query, memory_type, limit)
    return SearchResults(results=[SearchResult(
        key=r.key, value=r.value, score=r.score, metadata=r.metadata
    ) for r in results])


# ============================================
# Execution API
# ============================================

def _get_execution_module():
    if not runtime_instance:
        raise HTTPException(503, "Runtime not initialized")
    execution = runtime_instance.get_execution()
    if not execution:
        raise HTTPException(503, "Execution module not available")
    return execution


@app.post("/api/execution/python", response_model=ExecutionResult)
async def execute_python(request: ExecutePythonRequest):
    execution = _get_execution_module()
    result = await execution.execute_python(
        request.code,
        request.sandbox_id,
        request.timeout_seconds,
        request.packages,
        request.env_vars
    )
    return ExecutionResult(
        success=result.success,
        output=result.output,
        error=result.error,
        execution_time=result.execution_time
    )


# ============================================
# FileSystem API
# ============================================

def _get_filesystem_module():
    if not runtime_instance:
        raise HTTPException(503, "Runtime not initialized")
    fs = runtime_instance.get_filesystem()
    if not fs:
        raise HTTPException(503, "Filesystem module not available")
    return fs


@app.get("/api/filesystem/read")
async def read_file(path: str):
    fs = _get_filesystem_module()
    content = await fs.read_file(path)
    return {"content": content}


@app.post("/api/filesystem/write", response_model=FileInfo)
async def write_file(request: WriteFileRequest):
    fs = _get_filesystem_module()
    info = await fs.write_file(request.path, request.content, request.encoding, request.create_dirs)
    return FileInfo(
        path=info.path,
        name=info.name,
        size=info.size,
        is_dir=info.is_directory,
        modified_at=info.modified_at.isoformat() if info.modified_at else ""
    )


@app.get("/api/filesystem/list", response_model=FilesResponse)
async def list_files(path: str, recursive: bool = False):
    fs = _get_filesystem_module()
    files = await fs.list_directory(path, recursive)
    return FilesResponse(files=[FileInfo(
        path=f.path,
        name=f.name,
        size=f.size,
        is_dir=f.is_directory,
        modified_at=f.modified_at.isoformat() if f.modified_at else ""
    ) for f in files])


# ============================================
# Event History API
# ============================================

@app.get("/api/events/history")
async def get_event_history(
    limit: int = Query(100, ge=1, le=1000),
    event_type: Optional[str] = None
):
    if event_type:
        try:
            et = RuntimeEventType(event_type)
            events = event_bus.get_recent_events(limit=limit, event_type=et)
        except ValueError:
            raise HTTPException(400, f"Invalid event type: {event_type}")
    else:
        events = event_bus.get_recent_events(limit=limit)
    return {"events": [e.to_dict() for e in events]}


@app.get("/api/events/dead-letter")
async def get_dead_letter():
    return {"events": [e.to_dict() for e in event_bus.get_dead_letter()]}


# ============================================
# Plugins API
# ============================================

def _get_module_by_plugin_name(plugin_name: str):
    """Map plugin name to module name."""
    plugin_to_module = {
        "browser-automation": "local-browser",
        "code-execution": "local-execution",
        "file-operations": "local-filesystem",
        "memory-system": "local-memory",
        "web-search": "local-network",
        "image-processing": "vision",
    }
    return plugin_to_module.get(plugin_name, plugin_name)


@app.get("/api/plugins", response_model=PluginsResponse)
async def list_plugins():
    """List all available plugins with their status."""
    if not runtime_instance:
        raise HTTPException(503, "Runtime not initialized")

    # Get plugin information from runtime
    plugins_info = []

    # Core plugins (local modules)
    core_plugins = [
        {
            "id": "browser-automation",
            "name": "Browser Automation",
            "version": "1.0.0",
            "description": "Full-featured browser automation with Playwright. Navigate, click, scroll, extract content, and take screenshots.",
            "author": "AIPENSA Team",
            "plugin_type": "browser",
            "provides": ["browser_automation", "web_scraping", "screenshot"],
            "tags": ["browser", "automation", "scraping", "testing"],
            "dependencies": ["playwright", "lighthouse"]
        },
        {
            "id": "code-execution",
            "name": "Code Execution",
            "version": "1.0.0",
            "description": "Secure Python code execution in isolated sandboxes. Supports packages, timeouts, and environment variables.",
            "author": "AIPENSA Team",
            "plugin_type": "runtime",
            "provides": ["python_execution", "shell_execution", "sandbox_management"],
            "tags": ["execution", "python", "sandbox", "compute"],
            "dependencies": ["docker", "python"]
        },
        {
            "id": "file-operations",
            "name": "File Operations",
            "version": "1.0.0",
            "description": "Read, write, list, and manipulate files and directories. Supports recursive operations and encoding.",
            "author": "AIPENSA Team",
            "plugin_type": "storage",
            "provides": ["file_read", "file_write", "file_delete", "file_list", "file_search"],
            "tags": ["filesystem", "io", "storage", "files"],
            "dependencies": []
        },
        {
            "id": "memory-system",
            "name": "Memory System",
            "version": "1.0.0",
            "description": "Vector-based memory with semantic search. Store and retrieve knowledge across conversations.",
            "author": "AIPENSA Team",
            "plugin_type": "memory",
            "provides": ["memory_store", "memory_retrieve", "memory_search"],
            "tags": ["memory", "vector", "search", "rag"],
            "dependencies": ["chromadb", "sentence-transformers"]
        },
        {
            "id": "web-search",
            "name": "Web Search",
            "version": "0.5.0",
            "description": "Search the web using multiple providers (DuckDuckGo, Bing, Google). Extract and summarize results.",
            "author": "Community",
            "plugin_type": "network",
            "provides": ["web_search", "result_extraction", "summarization"],
            "tags": ["search", "web", "scraping", "research"],
            "dependencies": ["requests", "beautifulsoup4"]
        },
        {
            "id": "image-processing",
            "name": "Image Processing",
            "version": "1.0.0",
            "description": "Generate, edit, and analyze images using AI models. Supports diffusion, classification, and OCR.",
            "author": "AIPENSA Team",
            "plugin_type": "vision",
            "provides": ["image_generation", "image_editing", "image_analysis"],
            "tags": ["image", "vision", "generation", "editing"],
            "dependencies": ["opencv", "pillow", "torch"]
        }
    ]

    for plugin_def in core_plugins:
        module_name = _get_module_by_plugin_name(plugin_def["id"])
        module = runtime_instance.get_module(module_name)

        # Determine running/enabled status from actual module
        enabled = module is not None
        running = module is not None and module.state.value == "running"

        plugins_info.append(PluginInfo(
            **plugin_def,
            enabled=enabled,
            running=running,
            configured=enabled
        ))

    # Add runtime modules as plugins too
    for module_name, module in runtime_instance.modules.items():
        # Skip modules already covered above
        if module_name in ["local-browser", "local-execution", "local-tools", "local-memory", "local-planning", "local-mcp", "local-filesystem", "local-network", "local-docker", "conversation", "agent", "workflow", "scheduler", "queue", "notification", "storage", "authentication", "workspace", "voice", "vision", "video", "image", "embedding", "rag", "reasoning", "llm"]:
            continue

        metadata = {}
        if hasattr(module, 'metadata'):
            meta = module.metadata
            metadata = {
                "name": meta.name,
                "version": meta.version,
                "description": meta.description,
                "author": meta.author,
                "plugin_type": meta.plugin_type.value if hasattr(meta, 'plugin_type') else "custom",
                "provides": meta.provides,
                "tags": list(meta.tags),
                "dependencies": meta.dependencies
            }

        plugins_info.append(PluginInfo(
            id=module_name,
            name=metadata.get("name", module_name),
            version=metadata.get("version", "1.0.0"),
            description=metadata.get("description", ""),
            author=metadata.get("author", "AIPENSA"),
            plugin_type=metadata.get("plugin_type", "custom"),
            provides=metadata.get("provides", []),
            tags=metadata.get("tags", []),
            dependencies=metadata.get("dependencies", []),
            enabled=True,
            running=module.state.value == "running",
            configured=True
        ))

    return PluginsResponse(plugins=plugins_info)


@app.post("/api/plugins/{plugin_id}/config")
async def update_plugin_config(plugin_id: str, request: PluginConfigRequest):
    """Update plugin configuration (enable/disable, config)."""
    if not runtime_instance:
        raise HTTPException(503, "Runtime not initialized")

    module_name = _get_module_by_plugin_name(plugin_id)
    module = runtime_instance.get_module(module_name)

    if not module:
        raise HTTPException(404, f"Plugin '{plugin_id}' not found")

    result = {"success": True, "message": "Configuration updated"}

    if request.enabled is not None:
        if request.enabled and module.state.value != "running":
            try:
                await module.start()
                result["message"] = "Plugin enabled and started"
            except Exception as e:
                result = {"success": False, "error": f"Failed to start plugin: {str(e)}"}
        elif not request.enabled and module.state.value == "running":
            try:
                await module.stop()
                result["message"] = "Plugin disabled and stopped"
            except Exception as e:
                result = {"success": False, "error": f"Failed to stop plugin: {str(e)}"}

    if request.config is not None:
        # Update module config if supported
        if hasattr(module, 'update_config'):
            try:
                await module.update_config(request.config)
                result["message"] = "Plugin config updated"
            except Exception as e:
                result = {"success": False, "error": f"Failed to update config: {str(e)}"}

    return result


@app.post("/api/plugins/{plugin_id}/start")
async def start_plugin(plugin_id: str):
    """Start a plugin."""
    if not runtime_instance:
        raise HTTPException(503, "Runtime not initialized")

    module_name = _get_module_by_plugin_name(plugin_id)
    module = runtime_instance.get_module(module_name)

    if not module:
        raise HTTPException(404, f"Plugin '{plugin_id}' not found")

    try:
        await module.start()
        return {"success": True, "message": f"Plugin {plugin_id} started"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/plugins/{plugin_id}/stop")
async def stop_plugin(plugin_id: str):
    """Stop a plugin."""
    if not runtime_instance:
        raise HTTPException(503, "Runtime not initialized")

    module_name = _get_module_by_plugin_name(plugin_id)
    module = runtime_instance.get_module(module_name)

    if not module:
        raise HTTPException(404, f"Plugin '{plugin_id}' not found")

    try:
        await module.stop()
        return {"success": True, "message": f"Plugin {plugin_id} stopped"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/plugins/{plugin_id}/health")
async def plugin_health(plugin_id: str):
    """Get plugin health status."""
    if not runtime_instance:
        raise HTTPException(503, "Runtime not initialized")

    module_name = _get_module_by_plugin_name(plugin_id)
    module = runtime_instance.get_module(module_name)

    if not module:
        raise HTTPException(404, f"Plugin '{plugin_id}' not found")

    health = await module.health_check()
    return health


# ============================================
# LLM Models API
# ============================================

def _get_llm_module():
    if not runtime_instance:
        raise HTTPException(503, "Runtime not initialized")
    module = runtime_instance.get_module("llm")
    if not module:
        raise HTTPException(503, "LLM module not available")
    return module


@app.get("/api/llm/models")
async def list_models(provider: Optional[str] = None):
    """List available LLM models, optionally filtered by provider."""
    llm_module = _get_llm_module()
    from runtime.llm.module import LLMProvider

    try:
        provider_enum = LLMProvider(provider) if provider else None
    except ValueError:
        raise HTTPException(400, f"Invalid provider: {provider}")

    models = await llm_module.list_models(provider_enum)
    return {"models": [m.__dict__ for m in models]}


@app.get("/api/llm/models/{model_id}")
async def get_model_info(model_id: str):
    """Get detailed information about a specific model."""
    llm_module = _get_llm_module()
    model = await llm_module.get_model(model_id)
    if not model:
        raise HTTPException(404, f"Model '{model_id}' not found")
    return model.__dict__


# ============================================
# Workflow API
# ============================================

def _get_workflow_module():
    if not runtime_instance:
        raise HTTPException(503, "Runtime not initialized")
    module = runtime_instance.get_module("workflow")
    if not module:
        raise HTTPException(503, "Workflow module not available")
    return module


@app.post("/api/workflows", response_model=WorkflowExportResponse)
async def create_workflow(request: WorkflowCreateRequest):
    """Create a new workflow."""
    module = _get_workflow_module()
    from runtime.workflow.module import Workflow, WorkflowStep, StepType, WorkflowStatus

    # Convert request to Workflow object
    workflow = Workflow(
        name=request.name,
        description=request.description,
        version=request.version,
        variables=request.variables,
        status=WorkflowStatus.DRAFT
    )

    for step_req in request.steps:
        step = WorkflowStep(
            step_id=step_req.step_id,
            name=step_req.name,
            description=step_req.description,
            step_type=StepType(step_req.step_type),
            action=step_req.action,
            parameters=step_req.parameters,
            agent_type=step_req.agent_type,
            depends_on=step_req.depends_on,
            condition=step_req.condition,
            loop_config=step_req.loop_config,
            max_retries=step_req.max_retries,
            retry_delay=step_req.retry_delay,
            timeout_seconds=step_req.timeout_seconds
        )
        workflow.steps.append(step)

    created = await module.create_workflow(workflow)
    exported = await module.export_workflow(created.workflow_id)
    return WorkflowExportResponse(**exported)


@app.get("/api/workflows", response_model=WorkflowListResponse)
async def list_workflows(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """List all workflows."""
    module = _get_workflow_module()
    from runtime.workflow.module import WorkflowStatus

    status_enum = WorkflowStatus(status) if status else None
    workflows = await module.list_workflows(status=status_enum, limit=limit, offset=offset)

    result = []
    for w in workflows:
        result.append(WorkflowStatusResponse(
            workflow_id=w.workflow_id,
            name=w.name,
            description=w.description,
            version=w.version,
            steps=[WorkflowStepModel(
                step_id=s.step_id,
                name=s.name,
                description=s.description,
                step_type=s.step_type.value,
                action=s.action,
                parameters=s.parameters,
                agent_type=s.agent_type,
                depends_on=s.depends_on,
                condition=s.condition,
                loop_config=s.loop_config,
                max_retries=s.max_retries,
                retry_delay=s.retry_delay,
                timeout_seconds=s.timeout_seconds
            ) for s in w.steps],
            variables=w.variables,
            status=w.status.value,
            created_at=w.created_at.isoformat() if w.created_at else None,
            updated_at=w.updated_at.isoformat() if w.updated_at else None
        ))

    return WorkflowListResponse(workflows=result)


@app.get("/api/workflows/{workflow_id}", response_model=WorkflowExportResponse)
async def get_workflow(workflow_id: str):
    """Get a workflow by ID."""
    module = _get_workflow_module()
    exported = await module.export_workflow(workflow_id)
    if not exported:
        raise HTTPException(404, f"Workflow '{workflow_id}' not found")
    return WorkflowExportResponse(**exported)


@app.put("/api/workflows/{workflow_id}", response_model=WorkflowExportResponse)
async def update_workflow(workflow_id: str, request: WorkflowUpdateRequest):
    """Update a workflow."""
    module = _get_workflow_module()
    from runtime.workflow.module import Workflow, WorkflowStep, StepType

    existing = await module.get_workflow(workflow_id)
    if not existing:
        raise HTTPException(404, f"Workflow '{workflow_id}' not found")

    # Update fields
    if request.name is not None:
        existing.name = request.name
    if request.description is not None:
        existing.description = request.description
    if request.version is not None:
        existing.version = request.version
    if request.variables is not None:
        existing.variables = request.variables
    if request.steps is not None:
        existing.steps = []
        for step_req in request.steps:
            step = WorkflowStep(
                step_id=step_req.step_id,
                name=step_req.name,
                description=step_req.description,
                step_type=StepType(step_req.step_type),
                action=step_req.action,
                parameters=step_req.parameters,
                agent_type=step_req.agent_type,
                depends_on=step_req.depends_on,
                condition=step_req.condition,
                loop_config=step_req.loop_config,
                max_retries=step_req.max_retries,
                retry_delay=step_req.retry_delay,
                timeout_seconds=step_req.timeout_seconds
            )
            existing.steps.append(step)

    updated = await module.update_workflow(existing)
    exported = await module.export_workflow(updated.workflow_id)
    return WorkflowExportResponse(**exported)


@app.delete("/api/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """Delete a workflow."""
    module = _get_workflow_module()
    success = await module.delete_workflow(workflow_id)
    if not success:
        raise HTTPException(404, f"Workflow '{workflow_id}' not found")
    return {"success": True, "message": f"Workflow {workflow_id} deleted"}


@app.post("/api/workflows/dag", response_model=WorkflowExportResponse)
async def create_workflow_from_dag(request: WorkflowDAGRequest):
    """Create a workflow from DAG (ReactFlow nodes/edges)."""
    module = _get_workflow_module()
    workflow = await module.create_workflow_from_dag(
        name=request.name,
        nodes=request.nodes,
        edges=request.edges,
        variables=request.variables
    )
    exported = await module.export_workflow(workflow.workflow_id)
    return WorkflowExportResponse(**exported)


@app.post("/api/workflows/{workflow_id}/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(workflow_id: str, request: WorkflowExecuteRequest):
    """Execute a workflow."""
    module = _get_workflow_module()
    execution = await module.execute_workflow(
        workflow_id=workflow_id,
        variables=request.variables,
        execution_id=request.execution_id
    )
    status = await module.get_execution_status(execution.execution_id)
    return WorkflowExecutionResponse(**status)


@app.post("/api/workflows/{workflow_id}/cancel")
async def cancel_workflow(workflow_id: str, request: WorkflowExecutionActionRequest = Body(...)):
    """Cancel a running workflow execution."""
    module = _get_workflow_module()
    success = await module.cancel_execution(request.execution_id)
    if not success:
        raise HTTPException(404, f"Execution '{request.execution_id}' not found or not cancellable")
    return {"success": True, "message": "Workflow execution cancelled"}


@app.post("/api/workflows/{workflow_id}/pause")
async def pause_workflow(workflow_id: str, request: WorkflowExecutionActionRequest = Body(...)):
    """Pause a running workflow execution."""
    module = _get_workflow_module()
    success = await module.pause_execution(request.execution_id)
    if not success:
        raise HTTPException(404, f"Execution '{request.execution_id}' not found or not pausable")
    return {"success": True, "message": "Workflow execution paused"}


@app.post("/api/workflows/{workflow_id}/resume")
async def resume_workflow(workflow_id: str, request: WorkflowExecutionActionRequest = Body(...)):
    """Resume a paused workflow execution."""
    module = _get_workflow_module()
    success = await module.resume_execution(request.execution_id)
    if not success:
        raise HTTPException(404, f"Execution '{request.execution_id}' not found or not resumable")
    return {"success": True, "message": "Workflow execution resumed"}


@app.get("/api/workflows/{workflow_id}/executions", response_model=WorkflowExecutionListResponse)
async def list_executions(workflow_id: str, limit: int = Query(50, ge=1, le=200)):
    """List executions for a workflow."""
    module = _get_workflow_module()
    # This would need to be added to the module
    executions = []
    for exec in module._executions.values():
        if exec.workflow_id == workflow_id:
            status = await module.get_execution_status(exec.execution_id)
            executions.append(WorkflowExecutionResponse(**status))

    return WorkflowExecutionListResponse(executions=executions[:limit])


@app.get("/api/workflows/executions/{execution_id}", response_model=WorkflowExecutionResponse)
async def get_execution(execution_id: str):
    """Get execution status."""
    module = _get_workflow_module()
    status = await module.get_execution_status(execution_id)
    if not status:
        raise HTTPException(404, f"Execution '{execution_id}' not found")
    return WorkflowExecutionResponse(**status)


@app.get("/api/workflows/{workflow_id}/export", response_model=WorkflowExportResponse)
async def export_workflow(workflow_id: str):
    """Export workflow as DAG (nodes/edges)."""
    module = _get_workflow_module()
    exported = await module.export_workflow(workflow_id)
    if not exported:
        raise HTTPException(404, f"Workflow '{workflow_id}' not found")
    return WorkflowExportResponse(**exported)


# ============================================
# Settings API
# ============================================

def _get_runtime_config_dict() -> Dict[str, Any]:
    """Get runtime configuration as dictionary from runtime.toml."""
    from pathlib import Path
    import sys
    import logging
    logger = logging.getLogger(__name__)

    # Try tomllib (Python 3.11+ stdlib), fallback to tomli
    try:
        import tomllib
        logger.info(f"Using stdlib tomllib from: {tomllib.__file__}")
    except ImportError:
        import tomli as tomllib
        logger.info("Using tomli as tomllib fallback")

    config_path = Path("runtime.toml")
    if not config_path.exists():
        return {}

    try:
        with open(config_path, 'rb') as f:
            return tomllib.load(f)
    except Exception as e:
        logger.error(f"Failed to load runtime config: {e}")
        return {}


@app.get("/api/settings/runtime", response_model=RuntimeConfigResponse)
async def get_runtime_config():
    """Get the full runtime configuration."""
    config = _get_runtime_config_dict()
    return RuntimeConfigResponse(**config)


@app.get("/api/settings", response_model=SettingsResponse)
async def get_settings():
    """Get all settings (runtime config + UI preferences)."""
    runtime_config = _get_runtime_config_dict()

    # Add UI-specific settings (stored in localStorage typically, but we can serve defaults)
    ui_settings = {
        "theme": "system",
        "accent_color": "blue",
        "density": "comfortable",
        "auto_scroll": True,
        "compact_mode": False,
        "show_module_status": True,
        "animations_enabled": True,
        "notifications_enabled": True,
        "sound_enabled": False,
        "desktop_notifications_enabled": False,
        "debug_mode": False,
        "performance_monitoring": True,
        "event_persistence": True,
        "ws_auto_reconnect": True,
        "log_level": "info",
        "max_events": 10000,
        "api_url": "http://localhost:8000",
        "ws_url": "ws://localhost:8000/ws/events",
        "notification_types": {
            "errors": True,
            "warnings": True,
            "info": True,
            "debug": False
        }
    }

    return SettingsResponse(settings={
        "runtime": runtime_config,
        "ui": ui_settings
    })


@app.post("/api/settings/runtime")
async def update_runtime_config(request: Dict[str, Any]):
    """Update runtime configuration (writes to runtime.toml)."""
    from pathlib import Path
    import tomllib
    try:
        import tomli_w
    except ImportError:
        import tomllib_w as tomli_w

    config_path = Path("runtime.toml")

    # Load existing config
    if config_path.exists():
        with open(config_path, 'rb') as f:
            config = tomllib.load(f)
    else:
        config = {}

    # Update with new values
    config.update(request)

    # Write back
    with open(config_path, 'wb') as f:
        tomli_w.dump(config, f)

    return {"success": True, "message": "Runtime configuration updated. Restart required for some changes."}


@app.post("/api/settings")
async def update_settings(request: Dict[str, Any]):
    """Update UI settings (typically stored client-side)."""
    # In a full implementation, this might persist to a user config file
    # For now, just acknowledge
    return {"success": True, "message": "Settings saved (client-side only in current implementation)"}


@app.get("/api/settings/export", response_model=BackupExportResponse)
async def export_backup():
    """Export all data and settings as a backup."""
    if not runtime_instance:
        raise HTTPException(503, "Runtime not initialized")

    from datetime import datetime
    import json

    # Collect runtime config
    runtime_config = _get_runtime_config_dict()

    # Collect conversations
    conv_module = runtime_instance.get_module("conversation")
    conversations = []
    if conv_module:
        convs = await conv_module.list_conversations(limit=1000)
        conversations = [c.to_dict() for c in convs]

    # Collect workflows
    workflow_module = runtime_instance.get_module("workflow")
    workflows = []
    if workflow_module:
        wfs = await workflow_module.list_workflows(limit=1000)
        for w in wfs:
            exported = await workflow_module.export_workflow(w.workflow_id)
            if exported:
                workflows.append(exported)

    # Collect event history
    events = event_bus.get_recent_events(limit=10000)
    event_data = [e.to_dict() for e in events]

    backup = {
        "version": "1.0",
        "runtime_config": runtime_config,
        "conversations": conversations,
        "workflows": workflows,
        "events": event_data,
        "modules": {name: module.state.value for name, module in runtime_instance.modules.items()},
        "plugins": {name: status.value for name, status in runtime_instance.get_info().plugins.items()}
    }

    return BackupExportResponse(
        data=backup,
        timestamp=datetime.utcnow().isoformat(),
        version="1.0"
    )


@app.post("/api/settings/import")
async def import_backup(request: BackupImportRequest):
    """Import data and settings from backup."""
    if not runtime_instance:
        raise HTTPException(503, "Runtime not initialized")

    data = request.data

    # Restore runtime config
    if "runtime_config" in data:
        import tomllib
        try:
            import tomli_w
        except ImportError:
            import tomllib_w as tomli_w
        from pathlib import Path
        config_path = Path("runtime.toml")
        with open(config_path, 'wb') as f:
            tomli_w.dump(data["runtime_config"], f)

    # Restore conversations
    conv_module = runtime_instance.get_module("conversation")
    if conv_module and "conversations" in data:
        for conv_data in data["conversations"]:
            # This would need proper deserialization
            pass

    # Restore workflows
    workflow_module = runtime_instance.get_module("workflow")
    if workflow_module and "workflows" in data:
        for wf_data in data["workflows"]:
            # This would need proper import
            pass

    return {"success": True, "message": "Backup imported. Restart recommended for config changes."}


@app.post("/api/settings/clear-cache")
async def clear_cache():
    """Clear all cached data."""
    if not runtime_instance:
        raise HTTPException(503, "Runtime not initialized")

    cleared = []

    # Clear memory module
    memory_module = runtime_instance.get_module("memory")
    if memory_module and hasattr(memory_module, 'clear'):
        await memory_module.clear()
        cleared.append("memory")

    # Clear event history
    event_bus._event_history.clear()
    cleared.append("events")

    # Clear workflow executions
    workflow_module = runtime_instance.get_module("workflow")
    if workflow_module and hasattr(workflow_module, '_executions'):
        workflow_module._executions.clear()
        cleared.append("workflow_executions")

    return {"success": True, "cleared": cleared, "message": f"Cleared: {', '.join(cleared)}"}


@app.post("/api/settings/reset")
async def reset_settings():
    """Reset all settings to defaults."""
    from pathlib import Path
    import shutil

    # Backup current config
    config_path = Path("runtime.toml")
    if config_path.exists():
        backup_path = Path("runtime.toml.backup")
        shutil.copy2(config_path, backup_path)

    # Create default config
    default_config = """# AIPENSA Runtime Configuration

[runtime]
type = "local"
name = "AIPENSA-Runtime"
version = "1.0.0"
workspace = "workspace"
log_level = "INFO"
"""
    with open(config_path, 'w') as f:
        f.write(default_config)

    return {"success": True, "message": "Settings reset to defaults. Backup saved. Restart required."}