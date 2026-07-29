"""
AIPENSA Agent Runtime - Module Implementation

Provides agent lifecycle management, message passing, and tool execution capabilities.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import asyncio
import logging
import uuid

from runtime.base.module import RuntimeModule, ModuleMetadata, ModuleState
from runtime.base.events import RuntimeEvent, RuntimeEventType
from runtime.base.runtime import Runtime

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Agent lifecycle states."""
    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class AgentRole(Enum):
    """Agent roles in the system."""
    WORKER = "worker"           # Executes tasks
    SUPERVISOR = "supervisor"   # Manages other agents
    PLANNER = "planner"         # Creates plans
    EXECUTOR = "executor"       # Executes plans
    SPECIALIST = "specialist"   # Domain expert
    COORDINATOR = "coordinator" # Coordinates multiple agents


@dataclass
class AgentMetadata:
    """Agent metadata for registration and discovery."""
    name: str
    agent_id: str = ""
    role: AgentRole = AgentRole.WORKER
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    memory_types: List[str] = field(default_factory=list)
    max_concurrent_tasks: int = 5
    timeout_seconds: int = 3600

    def __post_init__(self):
        if not self.agent_id:
            self.agent_id = str(uuid.uuid4())[:8]


@dataclass
class AgentMessage:
    """Message passed between agents."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    from_agent: str = ""
    to_agent: str = ""
    message_type: str = "request"  # request, response, notification, error
    payload: Dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    reply_to: Optional[str] = None


@dataclass
class Task:
    """Task assigned to an agent."""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    assigned_agent: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentModule(RuntimeModule):
    """
    Agent Runtime Module.

    Manages agent lifecycle, message passing, task assignment, and tool execution.
    """

    metadata = ModuleMetadata(
        name="agent",
        version="1.0.0",
        description="Agent lifecycle management and orchestration",
        author="AIPENSA",
        module_type="runtime",
        provides=["agent_management", "task_execution", "message_passing", "tool_orchestration"],
        requires=["tool", "memory", "planning"],
        tags={"agent", "orchestration", "automation"}
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._agents: Dict[str, "Agent"] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._task_queue: asyncio.Queue = asyncio.Queue()
        self._message_handlers: Dict[str, List[callable]] = {}
        self._running = False

    @property
    def agents(self) -> Dict[str, "Agent"]:
        return self._agents.copy()

    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        await super().initialize(runtime, config)
        self._config = config
        self._max_agents = config.get("max_agents", 100)
        self._default_timeout = config.get("default_timeout", 3600)
        self._message_handlers = {}
        self._logger.info(f"Agent module initialized with max_agents={self._max_agents}")

    async def start(self) -> None:
        await super().start()
        self._running = True
        # Start message processor
        asyncio.create_task(self._process_messages())
        asyncio.create_task(self._process_tasks())
        self._logger.info("Agent module started")

    async def stop(self) -> None:
        self._running = False
        # Stop all agents
        for agent in self._agents.values():
            await agent.stop()
        await super().stop()
        self._logger.info("Agent module stopped")

    async def cleanup(self) -> None:
        await super().cleanup()
        self._agents.clear()
        self._message_handlers.clear()

    async def health_check(self) -> Dict[str, Any]:
        agent_health = {}
        for name, agent in self._agents.items():
            try:
                agent_health[name] = await agent.health_check()
            except Exception as e:
                agent_health[name] = {"healthy": False, "error": str(e)}

        return {
            "module": self.name,
            "status": self.state.value,
            "healthy": self.state == ModuleState.RUNNING,
            "uptime_seconds": self.uptime_seconds,
            "details": {
                "agents": agent_health,
                "queue_sizes": {
                    "messages": self._message_queue.qsize(),
                    "tasks": self._task_queue.qsize()
                }
            }
        }

    # Agent Management
    async def create_agent(self, metadata: AgentMetadata) -> "Agent":
        """Create a new agent."""
        if len(self._agents) >= self._max_agents:
            raise RuntimeError(f"Maximum agents ({self._max_agents}) reached")

        agent = Agent(metadata, self)
        self._agents[metadata.agent_id] = agent

        await self._runtime._publish_event(RuntimeEvent(
            event_type=RuntimeEventType.AGENT_CREATED,
            source=self.name,
            payload={"agent_id": metadata.agent_id, "name": metadata.name, "role": metadata.role.value}
        ))

        self._logger.info(f"Created agent: {metadata.name} ({metadata.agent_id})")
        return agent

    async def get_agent(self, agent_id: str) -> Optional["Agent"]:
        """Get an agent by ID."""
        return self._agents.get(agent_id)

    async def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent."""
        agent = self._agents.pop(agent_id, None)
        if agent:
            await agent.cleanup()
            await self._runtime._publish_event(RuntimeEvent(
                event_type=RuntimeEventType.AGENT_FAILED,  # Using failed as closest
                source=self.name,
                payload={"agent_id": agent_id, "action": "removed"}
            ))
            return True
        return False

    # Message Passing
    async def send_message(self, message: AgentMessage) -> None:
        """Send a message to an agent."""
        await self._message_queue.put(message)

    async def broadcast_message(self, message: AgentMessage, exclude: List[str] = None) -> None:
        """Broadcast a message to all agents."""
        exclude = exclude or []
        for agent_id, agent in self._agents.items():
            if agent_id not in exclude:
                msg = AgentMessage(
                    **message.__dict__,
                    message_id=str(uuid.uuid4())[:8],
                    to_agent=agent_id
                )
                await self._message_queue.put(msg)

    def register_message_handler(self, message_type: str, handler: callable) -> None:
        """Register a message handler."""
        if message_type not in self._message_handlers:
            self._message_handlers[message_type] = []
        self._message_handlers[message_type].append(handler)

    async def _process_messages(self) -> None:
        """Process messages from queue."""
        while self._running:
            try:
                message = await asyncio.wait_for(self._message_queue.get(), timeout=1.0)
                await self._deliver_message(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self._logger.error(f"Error processing message: {e}")

    async def _deliver_message(self, message: AgentMessage) -> None:
        """Deliver message to target agent."""
        agent = self._agents.get(message.to_agent)
        if not agent:
            self._logger.warning(f"Agent not found: {message.to_agent}")
            return

        try:
            await agent.receive_message(message)
        except Exception as e:
            self._logger.error(f"Error delivering message to {message.to_agent}: {e}")
            # Send error response
            if message.reply_to:
                error_msg = AgentMessage(
                    from_agent=self.name,
                    to_agent=message.from_agent,
                    message_type="error",
                    payload={"error": str(e), "original_message_id": message.message_id},
                    correlation_id=message.correlation_id
                )
                await self._message_queue.put(error_msg)

    # Task Management
    async def submit_task(self, task: Task) -> str:
        """Submit a task for execution."""
        task.status = "queued"
        await self._task_queue.put(task)

        await self._runtime._publish_event(RuntimeEvent(
            event_type=RuntimeEventType.TASK_STARTED,
            source=self.name,
            payload={"task_id": task.task_id, "name": task.name, "assigned_agent": task.assigned_agent}
        ))

        return task.task_id

    async def assign_task(self, task: Task, agent_id: str) -> bool:
        """Assign a task to a specific agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return False

        task.assigned_agent = agent_id
        task.status = "assigned"
        await agent.assign_task(task)
        return True

    async def _process_tasks(self) -> None:
        """Process tasks from queue."""
        while self._running:
            try:
                task = await asyncio.wait_for(self._task_queue.get(), timeout=1.0)

                # Find available agent
                agent_id = task.assigned_agent
                if not agent_id:
                    # Auto-assign to available agent with matching capabilities
                    agent_id = await self._find_suitable_agent(task)

                if agent_id:
                    await self.assign_task(task, agent_id)
                else:
                    # Re-queue
                    await asyncio.sleep(1)
                    if self._running:
                        await self._task_queue.put(task)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self._logger.error(f"Error processing task: {e}")

    async def _find_suitable_agent(self, task: Task) -> Optional[str]:
        """Find an agent suitable for the task."""
        for agent_id, agent in self._agents.items():
            if agent.state == AgentState.READY and agent.can_handle_task(task):
                return agent_id
        return None

    # Module Operations
    async def execute(self, operation: str, **kwargs) -> Any:
        """Execute module operations."""
        if operation == "create_agent":
            return await self.create_agent(kwargs.get("metadata"))
        elif operation == "get_agent":
            return await self.get_agent(kwargs.get("agent_id"))
        elif operation == "send_message":
            return await self.send_message(kwargs.get("message"))
        elif operation == "submit_task":
            return await self.submit_task(kwargs.get("task"))
        elif operation == "list_agents":
            return list(self._agents.keys())
        elif operation == "get_agent_state":
            agent = self._agents.get(kwargs.get("agent_id"))
            return agent.state if agent else None
        else:
            raise NotImplementedError(f"Operation '{operation}' not supported")


class Agent:
    """
    Represents an AI agent with lifecycle management.
    """

    def __init__(self, metadata: AgentMetadata, module: AgentModule):
        self.metadata = metadata
        self._module = module
        self._runtime = module._runtime
        self._state = AgentState.CREATED
        self._current_task: Optional[Task] = None
        self._message_handlers: Dict[str, callable] = {}
        self._tools: Dict[str, Any] = {}
        self._memory: Dict[str, Any] = {}
        self._started_at: Optional[datetime] = None
        self._task_history: List[Task] = []
        self._logger = logging.getLogger(f"agent.{metadata.name}")

    @property
    def state(self) -> AgentState:
        return self._state

    @property
    def agent_id(self) -> str:
        return self.metadata.agent_id

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def uptime_seconds(self) -> float:
        if self._started_at:
            return (datetime.utcnow() - self._started_at).total_seconds()
        return 0.0

    async def initialize(self) -> None:
        """Initialize the agent."""
        self._state = AgentState.INITIALIZING

        # Load tools
        await self._load_tools()

        # Initialize memory
        await self._initialize_memory()

        self._state = AgentState.READY
        self._logger.info(f"Agent {self.name} initialized")

    async def start(self) -> None:
        """Start the agent."""
        self._state = AgentState.RUNNING
        self._started_at = datetime.utcnow()

        await self._runtime._publish_event(RuntimeEvent(
            event_type=RuntimeEventType.AGENT_STARTED,
            source=self._module.name,
            payload={"agent_id": self.agent_id, "name": self.name}
        ))
        self._logger.info(f"Agent {self.name} started")

    async def stop(self) -> None:
        """Stop the agent gracefully."""
        if self._current_task:
            # Wait for current task to complete or cancel it
            pass

        self._state = AgentState.STOPPED
        self._logger.info(f"Agent {self.name} stopped")

    async def cleanup(self) -> None:
        """Clean up agent resources."""
        self._state = AgentState.CREATED
        self._tools.clear()
        self._memory.clear()
        self._message_handlers.clear()
        self._logger.info(f"Agent {self.name} cleaned up")

    async def health_check(self) -> Dict[str, Any]:
        """Health check for the agent."""
        return {
            "agent": self.name,
            "agent_id": self.agent_id,
            "healthy": self._state in [AgentState.READY, AgentState.RUNNING],
            "state": self._state.value,
            "uptime_seconds": self.uptime_seconds,
            "current_task": self._current_task.task_id if self._current_task else None,
            "completed_tasks": len(self._task_history)
        }

    async def assign_task(self, task: Task) -> None:
        """Assign a task to this agent."""
        if self._current_task:
            raise RuntimeError("Agent already has a task")

        self._current_task = task
        task.assigned_agent = self.agent_id
        task.status = "running"
        task.started_at = datetime.utcnow()
        self._state = AgentState.RUNNING

        # Execute task asynchronously
        asyncio.create_task(self._execute_task(task))

    async def _execute_task(self, task: Task) -> None:
        """Execute the assigned task."""
        try:
            self._logger.info(f"Executing task: {task.name}")

            # Call agent's task handler
            result = await self._handle_task(task)

            task.output_data = result
            task.status = "completed"
            task.completed_at = datetime.utcnow()

            await self._runtime._publish_event(RuntimeEvent(
                event_type=RuntimeEventType.TASK_COMPLETED,
                source=self._module.name,
                payload={"task_id": task.task_id, "agent_id": self.agent_id, "result": result}
            ))

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.completed_at = datetime.utcnow()

            self._logger.error(f"Task {task.task_id} failed: {e}")

            await self._runtime._publish_event(RuntimeEvent(
                event_type=RuntimeEventType.TASK_FAILED,
                source=self._module.name,
                payload={"task_id": task.task_id, "agent_id": self.agent_id, "error": str(e)}
            ))

        finally:
            self._task_history.append(task)
            self._current_task = None
            self._state = AgentState.READY

    async def _handle_task(self, task: Task) -> Dict[str, Any]:
        """Handle task execution - override in subclasses."""
        # Default implementation uses available tools
        return {"status": "completed", "message": "Task handled by base agent"}

    async def receive_message(self, message: AgentMessage) -> None:
        """Receive a message from another agent or the system."""
        self._logger.debug(f"Received message: {message.message_type} from {message.from_agent}")

        handler = self._message_handlers.get(message.message_type)
        if handler:
            await handler(message)
        else:
            # Default handling
            await self._default_message_handler(message)

    async def _default_message_handler(self, message: AgentMessage) -> None:
        """Default message handler."""
        if message.message_type == "request":
            # Try to process as a task
            if "task" in message.payload:
                task_data = message.payload["task"]
                task = Task(**task_data)
                await self.assign_task(task)

                # Send response
                if message.reply_to:
                    response = AgentMessage(
                        from_agent=self.agent_id,
                        to_agent=message.from_agent,
                        message_type="response",
                        payload={"task_id": task.task_id, "status": "accepted"},
                        correlation_id=message.correlation_id
                    )
                    await self._module.send_message(response)

    def register_message_handler(self, message_type: str, handler: callable) -> None:
        """Register a custom message handler."""
        self._message_handlers[message_type] = handler

    def can_handle_task(self, task: Task) -> bool:
        """Check if agent can handle a task based on capabilities."""
        if not self.metadata.capabilities:
            return True  # No restrictions

        # Check if task requires capabilities we have
        required = task.metadata.get("required_capabilities", [])
        return all(cap in self.metadata.capabilities for cap in required)

    async def _load_tools(self) -> None:
        """Load tools from tool module."""
        tool_module = self._runtime.modules.get("tool")
        if tool_module:
            for tool_name in self.metadata.tools:
                tool = await tool_module.execute("get_tool", name=tool_name)
                if tool:
                    self._tools[tool_name] = tool

    async def _initialize_memory(self) -> None:
        """Initialize memory from memory module."""
        memory_module = self._runtime.modules.get("memory")
        if memory_module and self.metadata.memory_types:
            for mem_type in self.metadata.memory_types:
                self._memory[mem_type] = memory_module

    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a tool by name."""
        tool = self._tools.get(tool_name)
        if not tool:
            # Try tool module
            tool_module = self._runtime.modules.get("tool")
            if tool_module:
                return await tool_module.execute("execute_tool", tool_name=tool_name, **kwargs)
            raise ValueError(f"Tool not found: {tool_name}")

        if callable(tool):
            return await tool(**kwargs)
        return tool

    def get_capabilities(self) -> List[str]:
        """Get agent capabilities."""
        return self.metadata.capabilities.copy()

    def add_capability(self, capability: str) -> None:
        """Add a capability to the agent."""
        if capability not in self.metadata.capabilities:
            self.metadata.capabilities.append(capability)


# Export
__all__ = [
    "AgentModule",
    "Agent",
    "AgentMetadata",
    "AgentState",
    "AgentRole",
    "AgentMessage",
    "Task"
]