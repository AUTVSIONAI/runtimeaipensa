"""
AIPENSA Tool Runtime - Tool Module

Provides tool execution capabilities including function calling,
built-in tools, and tool management.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type
import asyncio
import inspect
import json
import logging
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runtime.base.module import ModuleContext
    from runtime.base.runtime import Runtime
else:
    from runtime.base.module import ModuleContext, RuntimeModule, ModuleState, ModuleMetadata
    from runtime.base.runtime import Runtime
    from runtime.base.events import RuntimeEvent

logger = logging.getLogger(__name__)


from runtime.base.module import RuntimeModule, ModuleState, ModuleMetadata
from runtime.base.runtime import Runtime


class ToolCategory(Enum):
    """Categories of tools."""
    BUILTIN = "builtin"
    FUNCTION = "function"
    API = "api"
    CUSTOM = "custom"
    MCP = "mcp"


@dataclass
class ToolSchema:
    """JSON Schema for tool parameters."""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)
    returns: Dict[str, Any] = field(default_factory=dict)
    category: ToolCategory = ToolCategory.CUSTOM
    examples: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ToolResult:
    """Result of tool execution."""
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    call_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Tool(ABC):
    """Base class for all tools."""

    def __init__(self, name: str = "", config: Optional[Dict[str, Any]] = None):
        self.name = name or self.__class__.__name__
        self.config = config or {}
        self._schema: Optional[ToolSchema] = None
        self._enabled = True

    @property
    @abstractmethod
    def schema(self) -> ToolSchema:
        """Return tool schema."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool."""
        pass

    def validate_args(self, args: Dict[str, Any]) -> bool:
        """Validate arguments against schema."""
        if not self._schema:
            return True

        # Check required fields
        for req in self._schema.required:
            if req not in args:
                raise ValueError(f"Missing required argument: {req}")

        # Check types (basic)
        for key, value in args.items():
            if key in self._schema.parameters:
                param_schema = self._schema.parameters[key]
                expected_type = param_schema.get("type")
                if expected_type and not self._check_type(value, expected_type):
                    raise TypeError(f"Argument '{key}' must be of type {expected_type}")

        return True

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type."""
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        expected = type_map.get(expected_type)
        if expected:
            return isinstance(value, expected)
        return True

    def enable(self) -> None:
        """Enable the tool."""
        self._enabled = True

    def disable(self) -> None:
        """Disable the tool."""
        self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled


class FunctionTool(Tool):
    """Tool wrapping a Python function."""

    def __init__(
        self,
        func: Callable,
        name: str = "",
        description: str = "",
        schema: Optional[ToolSchema] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(name or func.__name__, config)
        self._func = func
        self._description = description or func.__doc__ or ""
        self._custom_schema = schema

    @property
    def schema(self) -> ToolSchema:
        if self._custom_schema:
            return self._custom_schema

        # Auto-generate schema from function signature
        sig = inspect.signature(self._func)
        params = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls", "kwargs", "args"):
                continue

            param_info = {
                "type": "string",  # default
                "description": f"Parameter {param_name}"
            }

            # Try to infer type from annotation
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == str:
                    param_info["type"] = "string"
                elif param.annotation in (int, float):
                    param_info["type"] = "number"
                elif param.annotation == bool:
                    param_info["type"] = "boolean"
                elif param.annotation in (list, List):
                    param_info["type"] = "array"
                elif param.annotation in (dict, Dict):
                    param_info["type"] = "object"

            params[param_name] = param_info

            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        return ToolSchema(
            name=self.name,
            description=self._description,
            parameters=params,
            required=required,
            category=ToolCategory.FUNCTION
        )

    async def execute(self, **kwargs) -> Any:
        """Execute the wrapped function."""
        # Handle both sync and async functions
        result = self._func(**kwargs)
        if inspect.iscoroutine(result):
            result = await result
        return result


class ToolModule(RuntimeModule):
    """Module for tool management and execution."""

    metadata = ModuleMetadata(
        name="tool",
        version="1.0.0",
        description="Tool execution and management module",
        author="AIPENSA",
        module_type="core",
        provides=["tool_execution", "function_calling", "tool_management"],
        requires=["memory"]
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._tools: Dict[str, Tool] = {}
        self._tool_schemas: Dict[str, ToolSchema] = {}
        self._execution_history: List[ToolResult] = []
        self._max_history = config.get("max_history", 1000) if config else 1000

    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        await super().initialize(runtime, config)

        # Register built-in tools
        await self._register_builtin_tools()

        # Load tools from config
        if config.get("tools"):
            await self._load_configured_tools(config["tools"])

        self._logger.info(f"Tool module initialized with {len(self._tools)} tools")

    async def start(self) -> None:
        await super().start()

    async def stop(self) -> None:
        await super().stop()

    async def cleanup(self) -> None:
        await super().cleanup()
        self._tools.clear()
        self._tool_schemas.clear()

    async def health_check(self) -> Dict[str, Any]:
        return {
            "module": self.name,
            "healthy": self.state == ModuleState.RUNNING,
            "state": self.state.value,
            "tools_registered": len(self._tools),
            "execution_history_size": len(self._execution_history)
        }

    # Tool Registration
    async def register_tool(self, tool: Tool) -> None:
        """Register a tool."""
        if tool.name in self._tools:
            self._logger.warning(f"Tool {tool.name} already registered, overwriting")

        tool._schema = tool.schema  # Cache schema
        self._tools[tool.name] = tool
        self._tool_schemas[tool.name] = tool.schema
        self._logger.info(f"Registered tool: {tool.name}")

    async def unregister_tool(self, name: str) -> bool:
        """Unregister a tool."""
        if name in self._tools:
            del self._tools[name]
            del self._tool_schemas[name]
            self._logger.info(f"Unregistered tool: {name}")
            return True
        return False

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self, category: Optional[ToolCategory] = None) -> List[str]:
        """List all registered tools."""
        if category:
            return [
                name for name, schema in self._tool_schemas.items()
                if schema.category == category
            ]
        return list(self._tools.keys())

    def get_tool_schemas(self) -> List[ToolSchema]:
        """Get all tool schemas for function calling."""
        return list(self._tool_schemas.values())

    def get_tool_schema(self, name: str) -> Optional[ToolSchema]:
        """Get schema for a specific tool."""
        return self._tool_schemas.get(name)

    # Tool Execution
    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        call_id: Optional[str] = None
    ) -> ToolResult:
        """Execute a tool by name with arguments."""
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool not found: {tool_name}",
                call_id=call_id or str(uuid.uuid4())[:8]
            )

        if not tool.enabled:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool disabled: {tool_name}",
                call_id=call_id or str(uuid.uuid4())[:8]
            )

        call_id = call_id or str(uuid.uuid4())[:8]
        start_time = datetime.utcnow()

        try:
            # Validate arguments
            tool.validate_args(arguments)

            # Execute
            self._logger.debug(f"Executing tool {tool_name} with args: {arguments}")
            result = await tool.execute(**arguments)

            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            tool_result = ToolResult(
                tool_name=tool_name,
                success=True,
                result=result,
                execution_time_ms=execution_time,
                call_id=call_id
            )

            self._execution_history.append(tool_result)
            if len(self._execution_history) > self._max_history:
                self._execution_history = self._execution_history[-self._max_history:]

            self._logger.debug(f"Tool {tool_name} executed successfully in {execution_time:.2f}ms")
            return tool_result

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            tool_result = ToolResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
                execution_time_ms=execution_time,
                call_id=call_id
            )
            self._execution_history.append(tool_result)
            self._logger.error(f"Tool {tool_name} failed: {e}")
            return tool_result

    async def execute_tools_batch(
        self,
        tool_calls: List[Dict[str, Any]]
    ) -> List[ToolResult]:
        """Execute multiple tools in batch."""
        tasks = []
        for call in tool_calls:
            tasks.append(
                self.execute_tool(
                    call["name"],
                    call.get("arguments", {}),
                    call.get("call_id")
                )
            )
        return await asyncio.gather(*tasks)

    # Built-in Tools
    async def _register_builtin_tools(self) -> None:
        """Register built-in tools."""
        # JSON operations
        await self.register_tool(FunctionTool(
            func=self._json_tool,
            name="json",
            description="Parse, stringify, or query JSON data",
            category=ToolCategory.BUILTIN
        ))

        # Text operations
        await self.register_tool(FunctionTool(
            func=self._text_tool,
            name="text",
            description="Text processing operations",
            category=ToolCategory.BUILTIN
        ))

        # Date/Time
        await self.register_tool(FunctionTool(
            func=self._datetime_tool,
            name="datetime",
            description="Get current date/time or format dates",
            category=ToolCategory.BUILTIN
        ))

        # Math
        await self.register_tool(FunctionTool(
            func=self._math_tool,
            name="math",
            description="Mathematical operations",
            category=ToolCategory.BUILTIN
        ))

    async def _json_tool(self, operation: str, data: Any = None, **kwargs) -> Any:
        """JSON operations tool."""
        if operation == "stringify":
            return json.dumps(data, **kwargs)
        elif operation == "parse":
            return json.loads(data)
        elif operation == "query":
            # Simple path query
            path = kwargs.get("path", "")
            # Implementation would use jsonpath
            return {"path": path, "result": "Query not implemented"}
        else:
            raise ValueError(f"Unknown JSON operation: {operation}")

    async def _text_tool(self, operation: str, text: str, **kwargs) -> Any:
        """Text processing tool."""
        if operation == "uppercase":
            return text.upper()
        elif operation == "lowercase":
            return text.lower()
        elif operation == "trim":
            return text.strip()
        elif operation == "length":
            return len(text)
        elif operation == "replace":
            old = kwargs.get("old", "")
            new = kwargs.get("new", "")
            return text.replace(old, new)
        elif operation == "split":
            separator = kwargs.get("separator", " ")
            return text.split(separator)
        else:
            raise ValueError(f"Unknown text operation: {operation}")

    async def _datetime_tool(self, operation: str = "now", **kwargs) -> Any:
        """Date/time tool."""
        now = datetime.utcnow()

        if operation == "now":
            format_str = kwargs.get("format", "%Y-%m-%d %H:%M:%S")
            return now.strftime(format_str)
        elif operation == "timestamp":
            return int(now.timestamp())
        elif operation == "format":
            dt = kwargs.get("datetime")
            format_str = kwargs.get("format", "%Y-%m-%d %H:%M:%S")
            if isinstance(dt, (int, float)):
                dt = datetime.fromtimestamp(dt)
            elif isinstance(dt, str):
                dt = datetime.fromisoformat(dt)
            return dt.strftime(format_str)
        else:
            raise ValueError(f"Unknown datetime operation: {operation}")

    async def _math_tool(self, operation: str, **kwargs) -> Any:
        """Math operations tool."""
        import math

        if operation == "add":
            return sum(kwargs.get("values", []))
        elif operation == "multiply":
            result = 1
            for v in kwargs.get("values", []):
                result *= v
            return result
        elif operation == "divide":
            a = kwargs.get("a", 0)
            b = kwargs.get("b", 1)
            if b == 0:
                raise ValueError("Division by zero")
            return a / b
        elif operation == "power":
            return kwargs.get("base", 1) ** kwargs.get("exponent", 0)
        elif operation == "sqrt":
            return math.sqrt(kwargs.get("value", 0))
        elif operation == "sin":
            return math.sin(kwargs.get("value", 0))
        elif operation == "cos":
            return math.cos(kwargs.get("value", 0))
        elif operation == "random":
            import random
            return random.uniform(kwargs.get("min", 0), kwargs.get("max", 1))
        else:
            raise ValueError(f"Unknown math operation: {operation}")

    async def _load_configured_tools(self, tools_config: List[Dict[str, Any]]) -> None:
        """Load tools from configuration."""
        for tool_config in tools_config:
            tool_type = tool_config.get("type", "function")
            if tool_type == "function":
                # Would load from module path
                pass
            elif tool_type == "mcp":
                # Would connect to MCP server
                pass

    # Module Operations
    async def execute(self, operation: str, **kwargs) -> Any:
        """Execute module operations."""
        if operation == "execute_tool":
            return await self.execute_tool(kwargs["tool_name"], kwargs.get("arguments", {}), kwargs.get("call_id"))
        elif operation == "get_tool":
            return self.get_tool(kwargs.get("name"))
        elif operation == "list_tools":
            return self.list_tools(kwargs.get("category"))
        elif operation == "get_schemas":
            return self.get_tool_schemas()
        elif operation == "register_tool":
            tool = kwargs.get("tool")
            if tool:
                await self.register_tool(tool)
        else:
            raise NotImplementedError(f"Operation '{operation}' not supported")


# Export
__all__ = [
    "ToolModule",
    "Tool",
    "FunctionTool",
    "ToolSchema",
    "ToolResult",
    "ToolCategory",
]