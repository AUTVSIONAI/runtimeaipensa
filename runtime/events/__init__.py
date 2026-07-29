"""
Event Bus for AIPENSA Runtime

Provides event-driven communication between components.
All system events flow through here for observability and decoupling.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type
import asyncio
import logging
import uuid
from collections import defaultdict

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """Event processing priority."""

    LOW = 0
    NORMAL = 50
    HIGH = 100
    CRITICAL = 200


class EventType(Enum):
    """Standard event types for the runtime."""

    # Runtime lifecycle
    RUNTIME_STARTED = "RuntimeStarted"
    RUNTIME_SHUTDOWN = "RuntimeShutdown"
    RUNTIME_ERROR = "RuntimeError"

    # Module events
    MODULE_STARTED = "ModuleStarted"
    MODULE_STOPPED = "ModuleStopped"
    MODULE_ERROR = "ModuleError"

    # Tool events
    TOOL_REGISTERED = "ToolRegistered"
    TOOL_EXECUTED = "ToolExecuted"
    TOOL_FAILED = "ToolFailed"

    # Task events
    TASK_STARTED = "TaskStarted"
    TASK_COMPLETED = "TaskCompleted"
    TASK_FAILED = "TaskFailed"
    TASK_CANCELLED = "TaskCancelled"

    # Browser events
    BROWSER_OPENED = "BrowserOpened"
    BROWSER_CLOSED = "BrowserClosed"
    BROWSER_NAVIGATED = "BrowserNavigated"
    BROWSER_ACTION = "BrowserAction"
    BROWSER_SCREENSHOT = "BrowserScreenshot"

    # Memory events
    MEMORY_STORED = "MemoryStored"
    MEMORY_RETRIEVED = "MemoryRetrieved"
    MEMORY_DELETED = "MemoryDeleted"
    MEMORY_CLEARED = "MemoryCleared"

    # Planning events
    PLAN_CREATED = "PlanCreated"
    PLAN_STARTED = "PlanStarted"
    PLAN_COMPLETED = "PlanCompleted"
    PLAN_FAILED = "PlanFailed"
    PLAN_STEP_STARTED = "PlanStepStarted"
    PLAN_STEP_COMPLETED = "PlanStepCompleted"
    PLAN_STEP_FAILED = "PlanStepFailed"

    # MCP events
    MCP_CONNECTED = "MCPConnected"
    MCP_DISCONNECTED = "MCPDisconnected"
    MCP_TOOL_CALLED = "MCPToolCalled"

    # Sandbox/Execution events
    SANDBOX_STARTED = "SandboxStarted"
    SANDBOX_STOPPED = "SandboxStopped"
    SANDBOX_COMMAND_EXECUTED = "SandboxCommandExecuted"

    # File system events
    FILE_READ = "FileRead"
    FILE_WRITE = "FileWrite"
    FILE_DELETED = "FileDeleted"

    # Network events
    HTTP_REQUEST = "HttpRequest"
    HTTP_RESPONSE = "HttpResponse"
    FILE_DOWNLOAD = "FileDownload"

    # Docker events
    CONTAINER_STARTED = "ContainerStarted"
    CONTAINER_STOPPED = "ContainerStopped"
    CONTAINER_LOGS = "ContainerLogs"

    # System events
    SYSTEM_ERROR = "SystemError"
    SYSTEM_WARNING = "SystemWarning"
    SYSTEM_INFO = "SystemInfo"


@dataclass
class Event:
    """Base event class."""

    event_type: str
    source: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    causation_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: EventPriority = EventPriority.NORMAL

    def __post_init__(self):
        if not self.event_type:
            self.event_type = self.__class__.__name__

    def with_correlation(self, correlation_id: str) -> "Event":
        """Create a new event with same correlation ID."""
        new_event = Event(
            event_type=self.event_type,
            source=self.source,
            correlation_id=correlation_id,
            causation_id=self.correlation_id,
            payload=self.payload.copy(),
            metadata=self.metadata.copy(),
            priority=self.priority,
        )
        return new_event


# Convenience functions for creating standard events
def create_event(event_type: EventType, source: str, payload: Dict[str, Any] = None, **kwargs) -> Event:
    """Create a standard event."""
    return Event(
        event_type=event_type.value,
        source=source,
        payload=payload or {},
        **kwargs
    )


class EventHandler(ABC):
    """Abstract event handler."""

    @abstractmethod
    async def handle(self, event: Event) -> None:
        pass

    @property
    @abstractmethod
    def handles_event_types(self) -> List[str]:
        """Return list of event types this handler processes."""
        pass

    @property
    def priority(self) -> EventPriority:
        return EventPriority.NORMAL


class EventBus:
    """
    Central event bus for the runtime.

    Features:
    - Async event processing
    - Priority-based ordering
    - Correlation/causation tracking
    - Event filtering
    - Dead letter queue for failed events
    """

    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = defaultdict(list)
        self._global_handlers: List[EventHandler] = []
        self._filters: List[Callable[[Event], bool]] = []
        self._dead_letter: List[Event] = []
        self._running = False
        self._queue: asyncio.Queue = asyncio.Queue()
        self._processor_task: Optional[asyncio.Task] = None
        self._event_log: List[Event] = []
        self._max_log_size = 10000

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe a handler to an event type."""
        self._handlers[event_type].append(handler)
        # Sort by priority
        self._handlers[event_type].sort(key=lambda h: h.priority, reverse=True)
        logger.debug(f"Subscribed {handler.__class__.__name__} to {event_type}")

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe a handler to all events."""
        self._global_handlers.append(handler)
        self._global_handlers.sort(key=lambda h: h.priority, reverse=True)
        logger.debug(f"Subscribed {handler.__class__.__name__} to all events")

    def unsubscribe(self, event_type: str, handler: EventHandler) -> bool:
        """Unsubscribe a handler from an event type."""
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            return True
        return False

    def add_filter(self, filter_func: Callable[[Event], bool]) -> None:
        """Add a global event filter."""
        self._filters.append(filter_func)

    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
        # Apply filters
        for filter_func in self._filters:
            if not filter_func(event):
                logger.debug(f"Event {event.event_type} filtered out")
                return

        # Log event
        self._log_event(event)

        # Process immediately (synchronous publish)
        await self._process_event(event)

    async def publish_background(self, event: Event) -> None:
        """Publish an event for background processing."""
        await self._queue.put(event)
        if not self._running:
            await self.start()

    async def _process_event(self, event: Event) -> None:
        """Process a single event through all handlers."""
        handlers = self._handlers.get(event.event_type, []) + self._global_handlers

        if not handlers:
            logger.debug(f"No handlers for event type: {event.event_type}")
            return

        # Execute handlers concurrently by priority groups
        priority_groups = defaultdict(list)
        for handler in handlers:
            priority_groups[handler.priority].append(handler)

        def _priority_value(p):
            return p.value if hasattr(p, 'value') else p

        for priority in sorted(priority_groups.keys(), key=_priority_value, reverse=True):
            group = priority_groups[priority]
            tasks = [handler.handle(event) for handler in group]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for handler, result in zip(group, results):
                if isinstance(result, Exception):
                    logger.error(f"Handler {handler.__class__.__name__} failed: {result}")
                    await self._handle_handler_error(event, handler, result)

    async def _handle_handler_error(self, event: Event, handler: EventHandler, error: Exception) -> None:
        """Handle handler execution error."""
        self._dead_letter.append(event)
        if len(self._dead_letter) > 1000:
            self._dead_letter = self._dead_letter[-1000:]

    def _log_event(self, event: Event) -> None:
        """Log event for debugging/audit."""
        self._event_log.append(event)
        if len(self._event_log) > self._max_log_size:
            self._event_log = self._event_log[-self._max_log_size:]

    async def start(self) -> None:
        """Start background event processor."""
        if self._running:
            return
        self._running = True
        self._processor_task = asyncio.create_task(self._process_queue())
        logger.info("Event bus started")

    async def stop(self) -> None:
        """Stop background event processor."""
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        logger.info("Event bus stopped")

    async def _process_queue(self) -> None:
        """Process queued events."""
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._process_event(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing queued event: {e}")

    def get_recent_events(self, limit: int = 100, event_type: Optional[str] = None) -> List[Event]:
        """Get recent events from log."""
        events = self._event_log
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def get_dead_letter(self) -> List[Event]:
        """Get dead letter events."""
        return self._dead_letter.copy()

    def clear_dead_letter(self) -> None:
        """Clear dead letter queue."""
        self._dead_letter.clear()


# Convenience function for creating event handlers
def event_handler(*event_types: str, priority: EventPriority = EventPriority.NORMAL):
    """Decorator to create event handlers."""
    def decorator(func: Callable[[Event], Any]) -> EventHandler:
        class _DecoratedHandler(EventHandler):
            def __init__(self):
                self._func = func
                self._event_types = list(event_types)
                self._priority = priority

            @property
            def handles_event_types(self) -> List[str]:
                return self._event_types

            @property
            def priority(self) -> EventPriority:
                return self._priority

            async def handle(self, event: Event) -> None:
                await self._func(event)

        return _DecoratedHandler()
    return decorator


# Global event bus instance
_global_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def set_event_bus(bus: EventBus) -> None:
    """Set the global event bus instance."""
    global _global_event_bus
    _global_event_bus = bus


__all__ = [
    "EventBus",
    "Event",
    "EventType",
    "EventPriority",
    "EventHandler",
    "get_event_bus",
    "set_event_bus",
    "event_handler",
    "create_event",
]