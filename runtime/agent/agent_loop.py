"""
Agent Loop Orchestrator

Core agent loop that orchestrates:
1. LLM call with tools →
2. Parse tool_calls →
3. Execute tools via Tools Module →
4. Feed results back to LLM →
5. Repeat until no tool_calls or max iterations

Emits AgentEvent stream for real-time frontend updates.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union
import asyncio
import json
import logging
import uuid

from runtime.llm.module import (
    LLMModule,
    LLMMessage,
    LLMTool,
    LLMRequest,
    MessageRole,
    LLMResponse,
    LLMStreamChunk,
)
from runtime.toolcalling.local_tools import LocalToolsModule, ToolDefinition, ToolExecution
from runtime.base.module import ModuleState

logger = logging.getLogger(__name__)


class AgentEventType(Enum):
    """Types of events emitted by the agent loop."""
    THINKING = "thinking"           # LLM is thinking/streaming text
    TOOL_CALL_START = "tool_call_start"   # About to call a tool
    TOOL_CALL_END = "tool_call_end"       # Tool call completed (success or error)
    TOOL_RESULT = "tool_result"           # Tool result received
    FINAL = "final"               # Final response ready
    ERROR = "error"               # Error occurred
    ITERATION_START = "iteration_start"   # New iteration started
    ITERATION_END = "iteration_end"       # Iteration completed


@dataclass
class AgentEvent:
    """Event emitted during agent loop execution."""
    event_type: AgentEventType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    iteration: int = 0
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "iteration": self.iteration,
            "data": self.data,
        }

    def to_sse(self) -> str:
        """Format as Server-Sent Event."""
        import json
        return f"data: {json.dumps(self.to_dict(), ensure_ascii=False)}\n\n"


@dataclass
class ToolCall:
    """Represents a tool call from the LLM."""
    call_id: str
    name: str
    arguments: Dict[str, Any]
    raw_arguments: str = ""  # Raw JSON string from LLM

    @classmethod
    def from_llm_tool_call(cls, tc: Dict[str, Any]) -> "ToolCall":
        """Create from LLM tool_calls format."""
        function = tc.get("function", {})
        return cls(
            call_id=tc.get("id", str(uuid.uuid4())[:8]),
            name=function.get("name", ""),
            arguments=json.loads(function.get("arguments", "{}")) if isinstance(function.get("arguments"), str) else function.get("arguments", {}),
            raw_arguments=function.get("arguments", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LLM message format."""
        return {
            "id": self.call_id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": json.dumps(self.arguments, ensure_ascii=False)
            }
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LLM message format."""
        return {
            "id": self.call_id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": json.dumps(self.arguments, ensure_ascii=False)
            }
        }


@dataclass
class AgentLoopConfig:
    """Configuration for the agent loop."""
    max_iterations: int = 10
    max_tokens: int = 4096
    temperature: float = 0.7
    system_prompt: str = ""
    require_approval: bool = True  # Require user approval for ALL tools
    approval_callback: Optional[Callable[[ToolCall], asyncio.Future[bool]]] = None
    available_tools: List[str] = field(default_factory=list)  # Tool names to make available
    model: str = "meta/llama-3.1-70b-instruct"


class ApprovalRequired(Exception):
    """Raised when a tool requires user approval."""
    def __init__(self, tool_call: ToolCall):
        self.tool_call = tool_call
        super().__init__(f"Approval required for tool: {tool_call.name}")


class AgentLoop:
    """
    Orchestrates the agent loop: LLM → Tools → LLM → ...

    Usage:
        loop = AgentLoop(llm_module, tools_module, config)
        async for event in loop.run(messages):
            # Handle events for streaming to frontend
            pass
    """

    def __init__(
        self,
        llm_module: LLMModule,
        tools_module: LocalToolsModule,
        runtime: Any = None,
        config: Optional[AgentLoopConfig] = None,
    ):
        self.llm = llm_module
        self.tools = tools_module
        self.runtime = runtime
        self.config = config or AgentLoopConfig()
        self._iteration = 0
        self._total_tokens = 0
        self._pending_approvals: Dict[str, asyncio.Future] = {}

    async def run(
        self,
        messages: List[LLMMessage],
        conversation_id: Optional[str] = None,
    ) -> AsyncIterator[AgentEvent]:
        """
        Run the agent loop, yielding events for streaming.

        Args:
            messages: Conversation history including system prompt
            conversation_id: Optional conversation ID for tracking

        Yields:
            AgentEvent objects for each step
        """
        self._iteration = 0
        self._total_tokens = 0

        # Get available tools
        tool_definitions = await self._get_available_tools()
        if not tool_definitions:
            logger.warning("No tools available for agent loop")

        # Main agent loop
        while self._iteration < self.config.max_iterations:
            self._iteration += 1

            yield AgentEvent(
                event_type=AgentEventType.ITERATION_START,
                iteration=self._iteration,
                data={"max_iterations": self.config.max_iterations}
            )

            # Call LLM with tools
            try:
                response = await self._call_llm_with_tools(messages, tool_definitions)
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                yield AgentEvent(
                    event_type=AgentEventType.ERROR,
                    iteration=self._iteration,
                    data={"error": str(e), "stage": "llm_call"}
                )
                break

            # Process response - check for tool calls
            tool_calls = self._extract_tool_calls(response)

            if not tool_calls:
                # No tool calls - final response
                content = response.content or ""
                self._total_tokens += response.usage.get("total_tokens", 0)

                yield AgentEvent(
                    event_type=AgentEventType.FINAL,
                    iteration=self._iteration,
                    data={
                        "content": content,
                        "model": response.model,
                        "usage": response.usage,
                        "finish_reason": response.finish_reason,
                    }
                )
                break

            # We have tool calls to execute
            yield AgentEvent(
                event_type=AgentEventType.THINKING,
                iteration=self._iteration,
                data={
                    "content": response.content or "",
                    "tool_calls_count": len(tool_calls),
                }
            )

            # Add assistant message with tool_calls to history
            messages.append(LLMMessage(
                role=MessageRole.ASSISTANT,
                content=response.content,
                tool_calls=[tc.to_dict() for tc in tool_calls],
            ))

            # Execute each tool call
            for tool_call in tool_calls:
                # Check approval
                if self.config.require_approval and not await self._request_approval(tool_call):
                    # User denied - add tool result indicating denial
                    tool_result = ToolExecution(
                        tool_name=tool_call.name,
                        arguments=tool_call.arguments,
                        request_id=tool_call.call_id,
                        error="User denied tool execution",
                    )
                    messages.append(LLMMessage(
                        role=MessageRole.TOOL,
                        content=json.dumps({"error": "User denied tool execution"}),
                        tool_calls=[],
                        tool_call_id=tool_call.call_id,
                        name=tool_call.name,
                    ))
                    yield AgentEvent(
                        event_type=AgentEventType.TOOL_CALL_END,
                        iteration=self._iteration,
                        data={
                            "call_id": tool_call.call_id,
                            "name": tool_call.name,
                            "approved": False,
                            "result": {"error": "User denied tool execution"},
                        }
                    )
                    continue

                # Emit tool call start event
                yield AgentEvent(
                    event_type=AgentEventType.TOOL_CALL_START,
                    iteration=self._iteration,
                    data={
                        "call_id": tool_call.call_id,
                        "name": tool_call.name,
                        "arguments": tool_call.arguments,
                    }
                )

                # Execute tool
                try:
                    result = await self.tools.execute_tool(
                        tool_name=tool_call.name,
                        arguments=tool_call.arguments,
                        context={"conversation_id": conversation_id} if conversation_id else None,
                    )
                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    result = ToolExecution(
                        tool_name=tool_call.name,
                        arguments=tool_call.arguments,
                        request_id=tool_call.call_id,
                        error=str(e),
                    )

                # Emit tool result event
                yield AgentEvent(
                    event_type=AgentEventType.TOOL_RESULT,
                    iteration=self._iteration,
                    data={
                        "call_id": tool_call.call_id,
                        "name": tool_call.name,
                        "success": result.success,
                        "result": result.result,
                        "error": result.error,
                        "duration_ms": result.duration_ms,
                    }
                )

                # Add tool result to messages
                result_content = json.dumps(result.result) if result.success else json.dumps({"error": result.error})
                messages.append(LLMMessage(
                    role=MessageRole.TOOL,
                    content=result_content,
                    tool_calls=[],
                    tool_call_id=tool_call.call_id,
                    name=tool_call.name,
                ))

                # Emit tool call end event
                yield AgentEvent(
                    event_type=AgentEventType.TOOL_CALL_END,
                    iteration=self._iteration,
                    data={
                        "call_id": tool_call.call_id,
                        "name": tool_call.name,
                        "approved": True,
                        "success": result.success,
                        "result": result.result,
                        "error": result.error,
                    }
                )

            yield AgentEvent(
                event_type=AgentEventType.ITERATION_END,
                iteration=self._iteration,
                data={"tools_executed": len(tool_calls)}
            )

            # Check if we should continue (LLM might want to call more tools)
            # Loop will continue and call LLM again with updated messages

        # Max iterations reached
        if self._iteration >= self.config.max_iterations:
            yield AgentEvent(
                event_type=AgentEventType.ERROR,
                iteration=self._iteration,
                data={"error": f"Max iterations ({self.config.max_iterations}) reached", "stage": "max_iterations"}
            )

    async def _call_llm_with_tools(
        self,
        messages: List[LLMMessage],
        tool_definitions: List[LLMTool],
    ) -> LLMResponse:
        """Call LLM with available tools."""
        request = LLMRequest(
            messages=messages,
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            tools=tool_definitions if tool_definitions else None,
            tool_choice="auto" if tool_definitions else None,
            stream=False,
        )

        # We need to use the LLM module's complete method
        # Since LLMModule.complete is an instance method, we call it directly
        return await self.llm.complete(
            messages=messages,
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            tools=tool_definitions,
            tool_choice="auto" if tool_definitions else None,
        )

    async def _get_available_tools(self) -> Optional[List[LLMTool]]:
        """Get available tools from tools module and convert to LLMTool format."""
        if self.config.available_tools is not None:
            # Filter to only allowed tools (empty list means no tools allowed)
            all_tools = await self.tools.list_tools()
            tool_defs = [t for t in all_tools if t.name in self.config.available_tools]
        else:
            tool_defs = await self.tools.list_tools()

        if not tool_defs:
            return None

        llm_tools = []
        for td in tool_defs:
            # Check if tool requires approval
            requires_approval = getattr(td, 'requires_approval', False)

            llm_tools.append(LLMTool(
                name=td.name,
                description=td.description,
                parameters=td.parameters,
                strict=False,
            ))

        return llm_tools

    def _extract_tool_calls(self, response: LLMResponse) -> List[ToolCall]:
        """Extract tool calls from LLM response."""
        if not response.tool_calls:
            return []

        tool_calls = []
        for tc in response.tool_calls:
            try:
                tool_calls.append(ToolCall.from_llm_tool_call(tc))
            except Exception as e:
                logger.warning(f"Failed to parse tool call: {e}")

        return tool_calls

    async def _request_approval(self, tool_call: ToolCall) -> bool:
        """Request user approval for tool execution."""
        if self.config.approval_callback:
            try:
                return await self.config.approval_callback(tool_call)
            except Exception as e:
                logger.error(f"Approval callback failed: {e}")
                return False
        return False  # Default deny if no callback


class StreamingAgentLoop(AgentLoop):
    """
    Agent loop with streaming LLM responses.

    Emits THINKING events for each streaming chunk.
    """

    async def run_streaming(
        self,
        messages: List[LLMMessage],
        conversation_id: Optional[str] = None,
    ) -> AsyncIterator[AgentEvent]:
        """
        Run the agent loop with streaming LLM responses.

        Yields:
            AgentEvent objects including streaming chunks
        """
        self._iteration = 0
        self._total_tokens = 0

        # Get available tools
        tool_definitions = await self._get_available_tools()

        # DEBUG: Log messages being sent to LLM
        logger.info(f"Agent loop messages for LLM: {len(messages)} messages")
        for i, m in enumerate(messages):
            logger.info(f"  Message {i}: role={m.role}, content_len={len(m.content) if m.content else 0}")

        print(f"AgentLoop tool_definitions: {tool_definitions}")
        print(f"AgentLoop messages: {[(m.role.value if hasattr(m.role, 'value') else m.role, len(m.content) if m.content else 0) for m in messages]}")

        # Main agent loop
        while self._iteration < self.config.max_iterations:
            self._iteration += 1

            yield AgentEvent(
                event_type=AgentEventType.ITERATION_START,
                iteration=self._iteration,
                data={"max_iterations": self.config.max_iterations}
            )

            # Stream LLM response
            accumulated_content = ""
            accumulated_tool_calls: List[Dict[str, Any]] = []

            try:
                stream_request = LLMRequest(
                    messages=messages,
                    model=self.config.model,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    tools=tool_definitions if tool_definitions else None,
                    tool_choice="auto" if tool_definitions else None,
                    stream=True,
                )

                print(f"AgentLoop calling llm.stream with tools: {tool_definitions}")
                async for chunk in self.llm.stream(
                    messages=messages,
                    model=self.config.model,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    tools=tool_definitions,
                    tool_choice="auto" if tool_definitions else None,
                ):
                    # Yield thinking events for text chunks
                    if chunk.delta:
                        accumulated_content += chunk.delta
                        yield AgentEvent(
                            event_type=AgentEventType.THINKING,
                            iteration=self._iteration,
                            data={
                                "chunk": chunk.delta,
                                "accumulated_content": accumulated_content,
                            }
                        )

                    # Accumulate tool calls from streaming
                    if chunk.tool_calls:
                        # DEBUG
                        print(f"DEBUG StreamingAgentLoop: chunk.tool_calls = {chunk.tool_calls}")
                        # Merge streaming tool calls
                        # Handle both formats: with index (OpenAI) and without (some providers like NVIDIA NIM)
                        for tc in chunk.tool_calls:
                            # If tool_call has index, use it
                            if "index" in tc and tc["index"] is not None:
                                idx = tc["index"]
                            else:
                                # For backends that don't provide index (e.g., NVIDIA NIM):
                                # - If this chunk has a function.name, it's a NEW tool call (start)
                                # - If function.name is None/missing but function.arguments is a string (not None), it's a CONTINUATION of the last tool call
                                func = tc.get("function", {})
                                func_name = func.get("name") if isinstance(func, dict) else None
                                func_args = func.get("arguments") if isinstance(func, dict) else None

                                print(f"DEBUG: func_name={func_name}, func_args={func_args}, accumulated_tool_calls_len={len(accumulated_tool_calls)}")

                                if func_name:
                                    # New tool call started (even if arguments is None in first chunk)
                                    idx = len(accumulated_tool_calls)
                                elif accumulated_tool_calls and isinstance(func_args, str):
                                    # Continuation of the last tool call (arguments being streamed as string)
                                    idx = len(accumulated_tool_calls) - 1
                                else:
                                    # Fallback: treat as new tool call
                                    idx = len(accumulated_tool_calls)

                            # Ensure we have enough slots
                            while len(accumulated_tool_calls) <= idx:
                                accumulated_tool_calls.append({
                                    "id": "",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""}
                                })
                            # Safely update fields if they exist
                            if tc.get("id"):
                                try:
                                    accumulated_tool_calls[idx]["id"] = tc["id"]
                                except (IndexError, KeyError):
                                    pass
                            if tc.get("function"):
                                func = tc["function"]
                                if isinstance(func, dict):
                                    if func.get("name"):
                                        try:
                                            accumulated_tool_calls[idx]["function"]["name"] = func["name"]
                                        except (IndexError, KeyError):
                                            pass
                                    # Only concatenate if arguments is a string (not None)
                                    args = func.get("arguments")
                                    if isinstance(args, str):
                                        try:
                                            accumulated_tool_calls[idx]["function"]["arguments"] += args
                                        except (IndexError, KeyError):
                                            pass

                    if chunk.is_final:
                        # Stream finished
                        finish_reason = chunk.finish_reason
                        if chunk.usage:
                            self._total_tokens += chunk.usage.get("total_tokens", 0)
                        break

            except Exception as e:
                logger.error(f"LLM streaming failed: {e}")
                yield AgentEvent(
                    event_type=AgentEventType.ERROR,
                    iteration=self._iteration,
                    data={"error": str(e), "stage": "llm_streaming"}
                )
                break

            # Process accumulated tool calls
            tool_calls = []
            for tc in accumulated_tool_calls:
                if tc.get("function", {}).get("name"):
                    tool_calls.append(ToolCall.from_llm_tool_call(tc))

            # Add assistant message to history
            messages.append(LLMMessage(
                role=MessageRole.ASSISTANT,
                content=accumulated_content,
                tool_calls=[tc.to_dict() for tc in tool_calls] if tool_calls else None,
            ))

            if not tool_calls:
                # Final response (text only)
                yield AgentEvent(
                    event_type=AgentEventType.FINAL,
                    iteration=self._iteration,
                    data={
                        "content": accumulated_content,
                        "model": self.config.model,
                        "finish_reason": finish_reason,
                    }
                )
                break

            # Emit tool calls
            yield AgentEvent(
                event_type=AgentEventType.THINKING,
                iteration=self._iteration,
                data={
                    "content": accumulated_content,
                    "tool_calls_count": len(tool_calls),
                }
            )

            # Execute each tool
            for tool_call in tool_calls:
                # Check approval
                if self.config.require_approval and not await self._request_approval(tool_call):
                    tool_result = ToolExecution(
                        tool_name=tool_call.name,
                        arguments=tool_call.arguments,
                        request_id=tool_call.call_id,
                        error="User denied tool execution",
                    )
                    messages.append(LLMMessage(
                        role=MessageRole.TOOL,
                        content=json.dumps({"error": "User denied tool execution"}),
                        tool_calls=[],
                        tool_call_id=tool_call.call_id,
                        name=tool_call.name,
                    ))
                    yield AgentEvent(
                        event_type=AgentEventType.TOOL_CALL_END,
                        iteration=self._iteration,
                        data={
                            "call_id": tool_call.call_id,
                            "name": tool_call.name,
                            "approved": False,
                            "result": {"error": "User denied tool execution"},
                        }
                    )
                    continue

                # Tool call start
                yield AgentEvent(
                    event_type=AgentEventType.TOOL_CALL_START,
                    iteration=self._iteration,
                    data={
                        "call_id": tool_call.call_id,
                        "name": tool_call.name,
                        "arguments": tool_call.arguments,
                    }
                )

                # Execute
                try:
                    result = await self.tools.execute_tool(
                        tool_name=tool_call.name,
                        arguments=tool_call.arguments,
                        context={"conversation_id": conversation_id} if conversation_id else None,
                    )
                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    result = ToolExecution(
                        tool_name=tool_call.name,
                        arguments=tool_call.arguments,
                        request_id=tool_call.call_id,
                        error=str(e),
                    )

                # Tool result
                yield AgentEvent(
                    event_type=AgentEventType.TOOL_RESULT,
                    iteration=self._iteration,
                    data={
                        "call_id": tool_call.call_id,
                        "name": tool_call.name,
                        "success": result.success,
                        "result": result.result,
                        "error": result.error,
                        "duration_ms": result.duration_ms,
                    }
                )

                # Add to messages
                result_content = json.dumps(result.result) if result.success else json.dumps({"error": result.error})
                messages.append(LLMMessage(
                    role=MessageRole.TOOL,
                    content=result_content,
                    tool_calls=[],
                    tool_call_id=tool_call.call_id,
                    name=tool_call.name,
                ))

                # Tool call end
                yield AgentEvent(
                    event_type=AgentEventType.TOOL_CALL_END,
                    iteration=self._iteration,
                    data={
                        "call_id": tool_call.call_id,
                        "name": tool_call.name,
                        "approved": True,
                        "success": result.success,
                        "result": result.result,
                        "error": result.error,
                    }
                )

            yield AgentEvent(
                event_type=AgentEventType.ITERATION_END,
                iteration=self._iteration,
                data={"tools_executed": len(tool_calls)}
            )

        if self._iteration >= self.config.max_iterations:
            yield AgentEvent(
                event_type=AgentEventType.ERROR,
                iteration=self._iteration,
                data={"error": f"Max iterations ({self.config.max_iterations}) reached", "stage": "max_iterations"}
            )