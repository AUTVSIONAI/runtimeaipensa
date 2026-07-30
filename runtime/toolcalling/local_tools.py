"""
Local Tools Module Implementation

Provides tool registration and execution with support for both local functions
and MCP tools.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Awaitable
import asyncio
import inspect
import logging
import json

from runtime.modules import (
    RuntimeModule,
    ModuleMetadata,
    ModuleState,
    ToolModule,
    ToolDefinition,
    ToolExecution,
)

logger = logging.getLogger(__name__)


@dataclass
class _RegisteredTool:
    """Internal tool registration."""
    definition: ToolDefinition
    handler: Callable[..., Awaitable[Any]]
    schema: Dict[str, Any]


class LocalToolsModule(ToolModule):
    """
    Local tools module for registering and executing tools.

    Supports:
    - Function-based tools with automatic schema generation
    - Async and sync handlers
    - Tool categories and tagging
    - Approval workflows
    - MCP tool integration
    """

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="tools",
            version="1.0.0",
            description="Local tool registry and execution",
            author="AIPENSA",
            dependencies=[],
            provides=["tool_registry", "tool_execution", "function_calling"],
            tags={"local", "tools", "functions"},
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self._config = config or {}
        self._tools: Dict[str, _RegisteredTool] = {}
        self._mcp_tools: Dict[str, List[ToolDefinition]] = {}
        self._approval_callback: Optional[Callable[[ToolExecution], Awaitable[bool]]] = None

    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        self._runtime = runtime
        self._config = {**self._config, **config}
        self.state = ModuleState.INITIALIZED

        # Register built-in tools
        await self._register_builtin_tools()

        logger.info("LocalToolsModule initialized")

    async def _register_builtin_tools(self) -> None:
        """Register built-in tools."""

        # File operations
        await self.register_tool(
            ToolDefinition(
                name="read_file",
                description="Read a file from the workspace",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path relative to workspace"},
                        "encoding": {"type": "string", "description": "File encoding", "default": "utf-8"},
                    },
                    "required": ["path"],
                },
                returns={"type": "object", "properties": {"content": {"type": "string"}}},
                category="filesystem",
                tags=["file", "read"],
            ),
            self._tool_read_file,
        )

        await self.register_tool(
            ToolDefinition(
                name="write_file",
                description="Write content to a file in the workspace",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path relative to workspace"},
                        "content": {"type": "string", "description": "Content to write"},
                        "encoding": {"type": "string", "description": "File encoding", "default": "utf-8"},
                        "create_dirs": {"type": "boolean", "description": "Create parent directories", "default": True},
                    },
                    "required": ["path", "content"],
                },
                returns={"type": "object", "properties": {"path": {"type": "string"}, "size": {"type": "integer"}}},
                category="filesystem",
                tags=["file", "write"],
            ),
            self._tool_write_file,
        )

        await self.register_tool(
            ToolDefinition(
                name="list_files",
                description="List files in a directory",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory path", "default": "."},
                        "recursive": {"type": "boolean", "description": "List recursively", "default": False},
                        "pattern": {"type": "string", "description": "Glob pattern filter"},
                    },
                },
                returns={"type": "object", "properties": {"files": {"type": "array"}}},
                category="filesystem",
                tags=["file", "list"],
            ),
            self._tool_list_files,
        )

        # Shell execution
        await self.register_tool(
            ToolDefinition(
                name="execute_shell",
                description="Execute a shell command",
                parameters={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Shell command to execute"},
                        "timeout_seconds": {"type": "integer", "description": "Timeout in seconds", "default": 60},
                        "working_dir": {"type": "string", "description": "Working directory"},
                    },
                    "required": ["command"],
                },
                returns={"type": "object", "properties": {"stdout": {"type": "string"}, "stderr": {"type": "string"}, "exit_code": {"type": "integer"}}},
                category="execution",
                tags=["shell", "command"],
                requires_approval=True,
            ),
            self._tool_execute_shell,
        )

        # Python execution
        await self.register_tool(
            ToolDefinition(
                name="execute_python",
                description="Execute Python code",
                parameters={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Python code to execute"},
                        "timeout_seconds": {"type": "integer", "description": "Timeout in seconds", "default": 30},
                    },
                    "required": ["code"],
                },
                returns={"type": "object", "properties": {"stdout": {"type": "string"}, "stderr": {"type": "string"}, "result": {"type": "string"}}},
                category="execution",
                tags=["python", "code"],
            ),
            self._tool_execute_python,
        )

        # HTTP requests
        await self.register_tool(
            ToolDefinition(
                name="http_get",
                description="Make HTTP GET request",
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to request"},
                        "headers": {"type": "object", "description": "HTTP headers"},
                        "timeout_seconds": {"type": "integer", "description": "Timeout", "default": 30},
                    },
                    "required": ["url"],
                },
                returns={"type": "object", "properties": {"status": {"type": "integer"}, "body": {"type": "string"}, "headers": {"type": "object"}}},
                category="network",
                tags=["http", "get"],
            ),
            self._tool_http_get,
        )

        await self.register_tool(
            ToolDefinition(
                name="http_post",
                description="Make HTTP POST request",
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to request"},
                        "headers": {"type": "object", "description": "HTTP headers"},
                        "json": {"type": "object", "description": "JSON body"},
                        "data": {"type": "string", "description": "Raw body data"},
                        "timeout_seconds": {"type": "integer", "description": "Timeout", "default": 30},
                    },
                    "required": ["url"],
                },
                returns={"type": "object", "properties": {"status": {"type": "integer"}, "body": {"type": "string"}, "headers": {"type": "object"}}},
                category="network",
                tags=["http", "post"],
            ),
            self._tool_http_post,
        )

        # Web search
        await self.register_tool(
            ToolDefinition(
                name="web_search",
                description="Search the web",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "num_results": {"type": "integer", "description": "Number of results", "default": 5},
                    },
                    "required": ["query"],
                },
                returns={"type": "object", "properties": {"results": {"type": "array"}}},
                category="search",
                tags=["web", "search"],
            ),
            self._tool_web_search,
        )

        # Browser automation tools
        await self.register_tool(
            ToolDefinition(
                name="browser_navigate",
                description="Navigate browser to URL",
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to navigate to"},
                        "session_id": {"type": "string", "description": "Browser session ID (optional, creates new if not provided)"},
                    },
                    "required": ["url"],
                },
                returns={"type": "object", "properties": {"session_id": {"type": "string"}, "url": {"type": "string"}, "title": {"type": "string"}}},
                category="browser",
                tags=["browser", "navigate"],
            ),
            self._tool_browser_navigate,
        )

        await self.register_tool(
            ToolDefinition(
                name="browser_click",
                description="Click element by index or selector",
                parameters={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Browser session ID"},
                        "index": {"type": "integer", "description": "Element index (from browser_get_state)"},
                        "selector": {"type": "string", "description": "CSS selector (alternative to index)"},
                    },
                    "required": ["session_id"],
                },
                returns={"type": "object", "properties": {"success": {"type": "boolean"}, "message": {"type": "string"}}},
                category="browser",
                tags=["browser", "click"],
            ),
            self._tool_browser_click,
        )

        await self.register_tool(
            ToolDefinition(
                name="browser_type",
                description="Type text into element",
                parameters={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Browser session ID"},
                        "index": {"type": "integer", "description": "Element index"},
                        "text": {"type": "string", "description": "Text to type"},
                    },
                    "required": ["session_id", "index", "text"],
                },
                returns={"type": "object", "properties": {"success": {"type": "boolean"}, "message": {"type": "string"}}},
                category="browser",
                tags=["browser", "type", "input"],
            ),
            self._tool_browser_type,
        )

        await self.register_tool(
            ToolDefinition(
                name="browser_screenshot",
                description="Take screenshot of current page",
                parameters={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Browser session ID"},
                        "full_page": {"type": "boolean", "description": "Capture full page", "default": True},
                    },
                    "required": ["session_id"],
                },
                returns={"type": "object", "properties": {"screenshot_base64": {"type": "string"}}},
                category="browser",
                tags=["browser", "screenshot"],
            ),
            self._tool_browser_screenshot,
        )

        await self.register_tool(
            ToolDefinition(
                name="browser_get_state",
                description="Get current browser state (interactive elements, URL, title)",
                parameters={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Browser session ID"},
                    },
                    "required": ["session_id"],
                },
                returns={"type": "object", "properties": {"url": {"type": "string"}, "title": {"type": "string"}, "interactive_elements": {"type": "array"}, "screenshot_base64": {"type": "string"}}},
                category="browser",
                tags=["browser", "state"],
            ),
            self._tool_browser_get_state,
        )

        await self.register_tool(
            ToolDefinition(
                name="browser_scroll",
                description="Scroll page up or down",
                parameters={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Browser session ID"},
                        "direction": {"type": "string", "description": "Scroll direction", "enum": ["up", "down"]},
                        "amount": {"type": "integer", "description": "Pixels to scroll", "default": 500},
                    },
                    "required": ["session_id", "direction"],
                },
                returns={"type": "object", "properties": {"success": {"type": "boolean"}, "message": {"type": "string"}}},
                category="browser",
                tags=["browser", "scroll"],
            ),
            self._tool_browser_scroll,
        )

    async def start(self) -> None:
        self.state = ModuleState.RUNNING
        logger.info("LocalToolsModule started")

    async def stop(self) -> None:
        self.state = ModuleState.STOPPED
        logger.info("LocalToolsModule stopped")

    async def cleanup(self) -> None:
        self._tools.clear()
        self._mcp_tools.clear()
        self.state = ModuleState.UNINITIALIZED
        logger.info("LocalToolsModule cleaned up")

    async def health_check(self) -> Dict[str, Any]:
        return {
            "module": "tools",
            "status": self.state.value,
            "healthy": self.state == ModuleState.RUNNING,
            "registered_tools": len(self._tools),
            "mcp_servers": len(self._mcp_tools),
        }

    # ============================================
    # Tool Registration
    # ============================================

    async def register_tool(
        self,
        definition: ToolDefinition,
        handler: Callable[..., Awaitable[Any]]
    ) -> bool:
        """Register a tool with its handler."""
        # Generate schema for function calling
        schema = self._generate_tool_schema(definition)

        tool = _RegisteredTool(
            definition=definition,
            handler=handler,
            schema=schema,
        )

        self._tools[definition.name] = tool
        logger.debug(f"Registered tool: {definition.name}")
        return True

    def _generate_tool_schema(self, definition: ToolDefinition) -> Dict[str, Any]:
        """Generate function calling schema."""
        return {
            "type": "function",
            "function": {
                "name": definition.name,
                "description": definition.description,
                "parameters": definition.parameters,
            },
        }

    async def unregister_tool(self, tool_name: str) -> bool:
        if tool_name in self._tools:
            del self._tools[tool_name]
            return True
        return False

    # ============================================
    # Tool Execution
    # ============================================

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolExecution:
        """Execute a tool."""
        request_id = f"req_{datetime.utcnow().timestamp()}"
        start_time = datetime.utcnow()

        # Check if local tool
        if tool_name in self._tools:
            tool = self._tools[tool_name]

            # Check approval
            if tool.definition.requires_approval and self._approval_callback:
                execution = ToolExecution(
                    tool_name=tool_name,
                    arguments=arguments,
                    request_id=request_id,
                )
                approved = await self._approval_callback(execution)
                if not approved:
                    return ToolExecution(
                        tool_name=tool_name,
                        arguments=arguments,
                        request_id=request_id,
                        error="Tool execution not approved",
                    )

            try:
                # Execute handler
                if inspect.iscoroutinefunction(tool.handler):
                    result = await tool.handler(**arguments, context=context)
                else:
                    result = tool.handler(**arguments, context=context)

                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

                return ToolExecution(
                    tool_name=tool_name,
                    arguments=arguments,
                    request_id=request_id,
                    result=result,
                    duration_ms=duration_ms,
                )

            except Exception as e:
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                logger.error(f"Tool {tool_name} failed: {e}")
                return ToolExecution(
                    tool_name=tool_name,
                    arguments=arguments,
                    request_id=request_id,
                    error=str(e),
                    duration_ms=duration_ms,
                )

        # Check MCP tools
        for server_id, tools in self._mcp_tools.items():
            for tool_def in tools:
                if tool_def.name == tool_name:
                    mcp = self._runtime.get_mcp()
                    if mcp:
                        try:
                            result = await mcp.call_tool(server_id, tool_name, arguments)
                            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                            return ToolExecution(
                                tool_name=tool_name,
                                arguments=arguments,
                                request_id=request_id,
                                result=result,
                                duration_ms=duration_ms,
                            )
                        except Exception as e:
                            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                            return ToolExecution(
                                tool_name=tool_name,
                                arguments=arguments,
                                request_id=request_id,
                                error=str(e),
                                duration_ms=duration_ms,
                            )

        return ToolExecution(
            tool_name=tool_name,
            arguments=arguments,
            request_id=request_id,
            error=f"Tool not found: {tool_name}",
        )

    async def get_tool(self, tool_name: str) -> Optional[ToolDefinition]:
        if tool_name in self._tools:
            return self._tools[tool_name].definition

        # Check MCP tools
        for tools in self._mcp_tools.values():
            for tool in tools:
                if tool.name == tool_name:
                    return tool

        return None

    async def list_tools(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[ToolDefinition]:
        tools = list(self._tools.values())

        if category:
            tools = [t for t in tools if t.definition.category == category]

        if tags:
            tools = [t for t in tools if any(tag in t.definition.tags for tag in tags)]

        # Add MCP tools
        for server_tools in self._mcp_tools.values():
            tools.extend([_RegisteredTool(definition=t, handler=None, schema={}) for t in server_tools])

        return [t.definition for t in tools]

    async def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        if tool_name in self._tools:
            return self._tools[tool_name].schema

        for tools in self._mcp_tools.values():
            for tool in tools:
                if tool.name == tool_name:
                    return {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.parameters,
                        },
                    }
        return None

    def set_approval_callback(self, callback: Callable[[ToolExecution], Awaitable[bool]]) -> None:
        """Set approval callback for tools requiring approval."""
        self._approval_callback = callback

    def register_mcp_tools(self, server_id: str, tools: List[ToolDefinition]) -> None:
        """Register tools from an MCP server."""
        self._mcp_tools[server_id] = tools
        logger.info(f"Registered {len(tools)} MCP tools from {server_id}")

    def unregister_mcp_tools(self, server_id: str) -> None:
        """Unregister tools from an MCP server."""
        if server_id in self._mcp_tools:
            del self._mcp_tools[server_id]

    # ============================================
    # Built-in Tool Handlers
    # ============================================

    async def _tool_read_file(self, path: str, encoding: str = "utf-8", context: Optional[Dict] = None) -> Dict[str, Any]:
        fs = self._runtime.get_filesystem()
        if not fs:
            raise RuntimeError("Filesystem module not available")
        content = await fs.read_file(path, encoding)
        return {"content": content}

    async def _tool_write_file(
        self,
        path: str,
        content: str,
        encoding: str = "utf-8",
        create_dirs: bool = True,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        fs = self._runtime.get_filesystem()
        if not fs:
            raise RuntimeError("Filesystem module not available")
        info = await fs.write_file(path, content, encoding, create_dirs)
        return {"path": info.path, "size": info.size}

    async def _tool_list_files(
        self,
        path: str = ".",
        recursive: bool = False,
        pattern: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        fs = self._runtime.get_filesystem()
        if not fs:
            raise RuntimeError("Filesystem module not available")
        files = await fs.list_directory(path, recursive, pattern)
        return {"files": [{"path": f.path, "name": f.name, "size": f.size, "is_dir": f.is_directory} for f in files]}

    async def _tool_execute_shell(
        self,
        command: str,
        timeout_seconds: int = 60,
        working_dir: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        execution = self._runtime.get_execution()
        if not execution:
            raise RuntimeError("Execution module not available")
        result = await execution.execute_shell(command, timeout_seconds=timeout_seconds, working_dir=working_dir)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
        }

    async def _tool_execute_python(
        self,
        code: str,
        timeout_seconds: int = 30,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        execution = self._runtime.get_execution()
        if not execution:
            raise RuntimeError("Execution module not available")
        result = await execution.execute_python(code, timeout_seconds=timeout_seconds)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "result": result.stdout if result.success else result.stderr,
        }

    async def _tool_http_get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout_seconds: int = 30,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        network = self._runtime.get_network()
        if not network:
            raise RuntimeError("Network module not available")
        from runtime.modules import NetworkRequest
        request = NetworkRequest(url=url, method="GET", headers=headers or {}, timeout_seconds=timeout_seconds)
        response = await network.request(request)
        return {
            "status": response.status_code,
            "body": response.body if isinstance(response.body, str) else response.body.decode(),
            "headers": dict(response.headers),
        }

    async def _tool_http_post(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict] = None,
        data: Optional[str] = None,
        timeout_seconds: int = 30,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        network = self._runtime.get_network()
        if not network:
            raise RuntimeError("Network module not available")
        from runtime.modules import NetworkRequest
        request = NetworkRequest(url=url, method="POST", headers=headers or {}, body=json or data, timeout_seconds=timeout_seconds)
        response = await network.request(request)
        return {
            "status": response.status_code,
            "body": response.body if isinstance(response.body, str) else response.body.decode(),
            "headers": dict(response.headers),
        }

    async def _tool_web_search(
        self,
        query: str,
        num_results: int = 5,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        from app.tool.web_search import WebSearch
        tool = WebSearch()
        result = await tool.execute(query=query, num_results=num_results)
        return {"results": [r.model_dump() for r in result.results]}

    # ============================================
    # Browser Tool Handlers
    # ============================================

    async def _tool_browser_navigate(
        self,
        url: str,
        session_id: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        browser = self._runtime.get_browser()
        if not browser:
            raise RuntimeError("Browser module not available")

        # Create new session if not provided
        if not session_id:
            session = await browser.create_session(url)
            session_id = session.session_id
        else:
            # Navigate existing session
            result = await browser.execute_action(session_id, "navigate", {"url": url})
            if not result.success:
                raise RuntimeError(f"Navigation failed: {result.error}")

            state = await browser.get_state(session_id)
            return {"session_id": session_id, "url": state.url, "title": state.title}

        session = await browser.get_state(session_id)
        return {"session_id": session_id, "url": session.url, "title": session.title}

    async def _tool_browser_click(
        self,
        session_id: str,
        index: Optional[int] = None,
        selector: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        browser = self._runtime.get_browser()
        if not browser:
            raise RuntimeError("Browser module not available")

        if index is not None:
            action = "click_element_by_index"
            params = {"index": index}
        elif selector:
            action = "click"
            params = {"selector": selector}
        else:
            raise ValueError("Either index or selector must be provided")

        result = await browser.execute_action(session_id, action, params)
        return {"success": result.success, "message": result.error or "Clicked successfully"}

    async def _tool_browser_type(
        self,
        session_id: str,
        index: int,
        text: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        browser = self._runtime.get_browser()
        if not browser:
            raise RuntimeError("Browser module not available")

        result = await browser.execute_action(session_id, "type", {"index": index, "text": text})
        return {"success": result.success, "message": result.error or "Typed successfully"}

    async def _tool_browser_screenshot(
        self,
        session_id: str,
        full_page: bool = True,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        browser = self._runtime.get_browser()
        if not browser:
            raise RuntimeError("Browser module not available")

        screenshot = await browser.take_screenshot(session_id, full_page)
        return {"screenshot_base64": screenshot}

    async def _tool_browser_get_state(
        self,
        session_id: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        browser = self._runtime.get_browser()
        if not browser:
            raise RuntimeError("Browser module not available")

        state = await browser.get_state(session_id)
        return {
            "session_id": session_id,
            "url": state.url,
            "title": state.title,
            "interactive_elements": state.interactive_elements,
            "screenshot_base64": state.screenshot_base64,
        }

    async def _tool_browser_scroll(
        self,
        session_id: str,
        direction: str,
        amount: int = 500,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        browser = self._runtime.get_browser()
        if not browser:
            raise RuntimeError("Browser module not available")

        result = await browser.execute_action(session_id, "scroll", {"direction": direction, "amount": amount})
        return {"success": result.success, "message": result.error or "Scrolled successfully"}