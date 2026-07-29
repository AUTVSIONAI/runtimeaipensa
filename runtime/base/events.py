"""
AIPENSA Runtime Base - Event System

Provides event-driven communication for all runtimes.
All runtimes share the same event bus pattern for observability
and inter-runtime communication.
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


class RuntimeEventType(Enum):
    """Standard event types for all runtimes."""

    # Runtime lifecycle
    RUNTIME_STARTED = "RuntimeStarted"
    RUNTIME_STOPPED = "RuntimeStopped"
    RUNTIME_READY = "RuntimeReady"
    RUNTIME_ERROR = "RuntimeError"
    RUNTIME_MAINTENANCE = "RuntimeMaintenance"

    # Module lifecycle
    MODULE_STARTED = "ModuleStarted"
    MODULE_STOPPED = "ModuleStopped"
    MODULE_ERROR = "ModuleError"
    MODULE_INITIALIZED = "ModuleInitialized"

    # Plugin lifecycle
    PLUGIN_LOADED = "PluginLoaded"
    PLUGIN_STARTED = "PluginStarted"
    PLUGIN_STOPPED = "PluginStopped"
    PLUGIN_ERROR = "PluginError"

    # Task/Execution events
    TASK_STARTED = "TaskStarted"
    TASK_COMPLETED = "TaskCompleted"
    TASK_FAILED = "TaskFailed"
    TASK_CANCELLED = "TaskCancelled"

    # Agent events (for Agent Runtime)
    AGENT_CREATED = "AgentCreated"
    AGENT_STARTED = "AgentStarted"
    AGENT_COMPLETED = "AgentCompleted"
    AGENT_FAILED = "AgentFailed"
    AGENT_MESSAGE = "AgentMessage"

    # Conversation events (for Conversation Runtime)
    CONVERSATION_STARTED = "ConversationStarted"
    CONVERSATION_ENDED = "ConversationEnded"
    MESSAGE_RECEIVED = "MessageReceived"
    MESSAGE_SENT = "MessageSent"

    # Workflow events (for Workflow Runtime)
    WORKFLOW_STARTED = "WorkflowStarted"
    WORKFLOW_COMPLETED = "WorkflowCompleted"
    WORKFLOW_FAILED = "WorkflowFailed"
    WORKFLOW_STEP_STARTED = "WorkflowStepStarted"
    WORKFLOW_STEP_COMPLETED = "WorkflowStepCompleted"

    # Scheduler events (for Scheduler Runtime)
    JOB_SCHEDULED = "JobScheduled"
    JOB_STARTED = "JobStarted"
    JOB_COMPLETED = "JobCompleted"
    JOB_FAILED = "JobFailed"

    # Queue events (for Queue Runtime)
    QUEUE_MESSAGE_ENQUEUED = "QueueMessageEnqueued"
    QUEUE_MESSAGE_DEQUEUED = "QueueMessageDequeued"
    QUEUE_MESSAGE_PROCESSED = "QueueMessageProcessed"
    QUEUE_MESSAGE_FAILED = "QueueMessageFailed"

    # Notification events (for Notification Runtime)
    NOTIFICATION_SENT = "NotificationSent"
    NOTIFICATION_DELIVERED = "NotificationDelivered"
    NOTIFICATION_FAILED = "NotificationFailed"

    # Storage events (for Storage Runtime)
    STORAGE_READ = "StorageRead"
    STORAGE_WRITE = "StorageWrite"
    STORAGE_DELETE = "StorageDelete"

    # Auth events (for Authentication Runtime)
    AUTH_LOGIN = "AuthLogin"
    AUTH_LOGOUT = "AuthLogout"
    AUTH_FAILED = "AuthFailed"
    TOKEN_REFRESHED = "TokenRefreshed"

    # Workspace events (for Workspace Runtime)
    WORKSPACE_CREATED = "WorkspaceCreated"
    WORKSPACE_DELETED = "WorkspaceDeleted"
    WORKSPACE_MEMBER_ADDED = "WorkspaceMemberAdded"
    WORKSPACE_MEMBER_REMOVED = "WorkspaceMemberRemoved"

    # Knowledge events (for Knowledge Runtime)
    KNOWLEDGE_INDEXED = "KnowledgeIndexed"
    KNOWLEDGE_SEARCHED = "KnowledgeSearched"
    KNOWLEDGE_UPDATED = "KnowledgeUpdated"

    # Skill events (for Skill Runtime)
    SKILL_REGISTERED = "SkillRegistered"
    SKILL_EXECUTED = "SkillExecuted"
    SKILL_FAILED = "SkillFailed"

    # LLM events (for LLM Runtime)
    LLM_REQUEST = "LLMRequest"
    LLM_RESPONSE = "LLMResponse"
    LLM_ERROR = "LLMError"

    # Voice events (for Voice Runtime)
    VOICE_STARTED = "VoiceStarted"
    VOICE_STOPPED = "VoiceStopped"
    VOICE_TRANSCRIPTION = "VoiceTranscription"

    # Vision events (for Vision Runtime)
    VISION_ANALYSIS_STARTED = "VisionAnalysisStarted"
    VISION_ANALYSIS_COMPLETED = "VisionAnalysisCompleted"

    # Video events (for Video Runtime)
    VIDEO_PROCESSING_STARTED = "VideoProcessingStarted"
    VIDEO_PROCESSING_COMPLETED = "VideoProcessingCompleted"

    # Image events (for Image Runtime)
    IMAGE_GENERATED = "ImageGenerated"
    IMAGE_PROCESSED = "ImageProcessed"

    # Embedding events (for Embedding Runtime)
    EMBEDDING_GENERATED = "EmbeddingGenerated"
    EMBEDDING_SEARCH = "EmbeddingSearch"

    # RAG events (for RAG Runtime)
    RAG_QUERY = "RAGQuery"
    RAG_RETRIEVAL = "RAGRetrieval"
    RAG_GENERATION = "RAGGeneration"

    # Reasoning events (for Reasoning Runtime)
    REASONING_STARTED = "ReasoningStarted"
    REASONING_COMPLETED = "ReasoningCompleted"
    REASONING_STEP = "ReasoningStep"

    # Company Context events (Extensions Layer)
    COMPANY_PROFILE_UPDATED = "CompanyProfileUpdated"
    COMPANY_BRAND_UPDATED = "CompanyBrandUpdated"
    COMPANY_PRODUCTS_UPDATED = "CompanyProductsUpdated"
    COMPANY_CHANNELS_UPDATED = "CompanyChannelsUpdated"
    COMPANY_GOALS_UPDATED = "CompanyGoalsUpdated"
    COMPANY_KNOWLEDGE_STORED = "CompanyKnowledgeStored"
    COMPANY_KNOWLEDGE_SEARCHED = "CompanyKnowledgeSearched"

    # Employee events (Extensions Layer)
    EMPLOYEE_CREATED = "EmployeeCreated"
    EMPLOYEE_PROFILE_UPDATED = "EmployeeProfileUpdated"
    EMPLOYEE_DELETED = "EmployeeDeleted"
    EMPLOYEE_DEACTIVATED = "EmployeeDeactivated"

    # Team events (Extensions Layer)
    TEAM_CREATED = "TeamCreated"
    TEAM_MEMBER_ADDED = "TeamMemberAdded"
    TEAM_MEMBER_REMOVED = "TeamMemberRemoved"
    TEAM_MEMBER_ROLE_CHANGED = "TeamMemberRoleChanged"
    TASK_DELEGATED = "TaskDelegated"
    TEAM_WORKFLOW_STARTED = "TeamWorkflowStarted"

    # Provider events (Extensions Layer)
    PROVIDER_REGISTERED = "ProviderRegistered"
    PROVIDER_CONNECTION_CREATED = "ProviderConnectionCreated"
    PROVIDER_CONNECTION_UPDATED = "ProviderConnectionUpdated"
    PROVIDER_CAPABILITY_EXECUTED = "ProviderCapabilityExecuted"

    # Onboarding events (Extensions Layer)
    ONBOARDING_STARTED = "OnboardingStarted"
    ONBOARDING_COMPLETED = "OnboardingCompleted"
    ONBOARDING_FAILED = "OnboardingFailed"
    ONBOARDING_SOURCE_CONFIGURED = "OnboardingSourceConfigured"

    # Explorer events (Extensions Layer)
    EXPLORER_QUERY = "ExplorerQuery"

    # Sync events (Extensions Layer)
    SYNC_EXPORT_STARTED = "SyncExportStarted"
    SYNC_EXPORT_COMPLETED = "SyncExportCompleted"
    SYNC_IMPORT_STARTED = "SyncImportStarted"
    SYNC_IMPORT_COMPLETED = "SyncImportCompleted"

    # System events
    SYSTEM_ERROR = "SystemError"
    SYSTEM_WARNING = "SystemWarning"
    SYSTEM_INFO = "SystemInfo"
    METRICS_COLLECTED = "MetricsCollected"


@dataclass
class RuntimeEvent:
    """
    Base event class for all runtime events.

    Events are the primary mechanism for observability,
    debugging, and inter-component communication.
    """

    event_type: RuntimeEventType
    source: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    causation_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)

    def __post_init__(self):
        if isinstance(self.event_type, str):
            self.event_type = RuntimeEventType(self.event_type)

    def with_correlation(self, correlation_id: str) -> "RuntimeEvent":
        """Create a new event with the same correlation ID."""
        return RuntimeEvent(
            event_type=self.event_type,
            source=self.source,
            correlation_id=correlation_id,
            causation_id=self.correlation_id,
            payload=self.payload.copy(),
            metadata=self.metadata.copy(),
            tags=self.tags.copy(),
        )

    def add_tag(self, tag: str) -> "RuntimeEvent":
        """Add a tag to the event."""
        self.tags.add(tag)
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_type": self.event_type.value,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "payload": self.payload,
            "metadata": self.metadata,
            "tags": list(self.tags),
        }


class EventHandler(ABC):
    """Abstract event handler."""

    @abstractmethod
    async def handle(self, event: RuntimeEvent) -> None:
        """Handle an event."""
        pass

    @property
    @abstractmethod
    def handles_event_types(self) -> List[RuntimeEventType]:
        """Return list of event types this handler processes."""
        pass

    @property
    def priority(self) -> int:
        """Handler priority (higher = runs first)."""
        return 0


class RuntimeEventBus:
    """
    Central event bus for runtime communication.

    Features:
    - Async event processing
    - Priority-based handler ordering
    - Correlation/causation tracking
    - Event filtering
    - Dead letter queue for failed events
    - Event history for debugging
    """

    def __init__(
        self,
        max_history: int = 10000,
        enable_filters: bool = True,
    ):
        self._handlers: Dict[RuntimeEventType, List[EventHandler]] = defaultdict(list)
        self._global_handlers: List[EventHandler] = []
        self._filters: List[Callable[[RuntimeEvent], bool]] = []
        self._dead_letter: List[RuntimeEvent] = []
        self._event_history: List[RuntimeEvent] = []
        self._max_history = max_history
        self._enable_filters = enable_filters
        self._running = False
        self._queue: asyncio.Queue = asyncio.Queue()
        self._processor_task: Optional[asyncio.Task] = None

    def subscribe(
        self,
        event_type: RuntimeEventType,
        handler: EventHandler
    ) -> None:
        """Subscribe a handler to an event type."""
        self._handlers[event_type].append(handler)
        # Sort by priority (highest first)
        self._handlers[event_type].sort(key=lambda h: h.priority, reverse=True)
        logger.debug(f"Subscribed {handler.__class__.__name__} to {event_type.value}")

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe a handler to all events."""
        self._global_handlers.append(handler)
        self._global_handlers.sort(key=lambda h: h.priority, reverse=True)
        logger.debug(f"Subscribed {handler.__class__.__name__} to all events")

    def unsubscribe(
        self,
        event_type: RuntimeEventType,
        handler: EventHandler
    ) -> bool:
        """Unsubscribe a handler from an event type."""
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            return True
        return False

    def add_filter(self, filter_func: Callable[[RuntimeEvent], bool]) -> None:
        """Add a global event filter."""
        self._filters.append(filter_func)

    async def publish(self, event: RuntimeEvent) -> None:
        """Publish an event to all subscribers."""
        # Apply filters
        if self._enable_filters:
            for filter_func in self._filters:
                if not filter_func(event):
                    logger.debug(f"Event {event.event_type.value} filtered out")
                    return

        # Add to history
        self._add_to_history(event)

        # Process immediately (synchronous publish)
        await self._process_event(event)

    async def publish_background(self, event: RuntimeEvent) -> None:
        """Publish an event for background processing."""
        await self._queue.put(event)
        if not self._running:
            await self.start()

    async def _process_event(self, event: RuntimeEvent) -> None:
        """Process a single event through all handlers."""
        # Get handlers for this event type + global handlers
        handlers = (
            self._handlers.get(event.event_type, [])
            + self._global_handlers
        )

        if not handlers:
            logger.debug(f"No handlers for event type: {event.event_type.value}")
            return

        # Group handlers by priority
        priority_groups = defaultdict(list)
        for handler in handlers:
            priority_groups[handler.priority].append(handler)

        # Execute handlers by priority (highest first)
        for priority in sorted(priority_groups.keys(), reverse=True):
            group = priority_groups[priority]
            tasks = [handler.handle(event) for handler in group]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for handler, result in zip(group, results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Handler {handler.__class__.__name__} failed: {result}"
                    )
                    await self._handle_error(event, handler, result)

    async def _handle_error(
        self,
        event: RuntimeEvent,
        handler: EventHandler,
        error: Exception
    ) -> None:
        """Handle handler execution error."""
        self._dead_letter.append(event)
        if len(self._dead_letter) > 1000:
            self._dead_letter = self._dead_letter[-1000:]

    def _add_to_history(self, event: RuntimeEvent) -> None:
        """Add event to history."""
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

    async def start(self) -> None:
        """Start background event processor."""
        if self._running:
            return
        self._running = True
        self._processor_task = asyncio.create_task(self._process_queue())
        logger.info("Event bus started")

    async def stop(self) -> None:
        """Stop background event processor."""
        if not self._running:
            return
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

    def get_recent_events(
        self,
        limit: int = 100,
        event_type: Optional[RuntimeEventType] = None
    ) -> List[RuntimeEvent]:
        """Get recent events from history."""
        events = self._event_history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def get_dead_letter(self) -> List[RuntimeEvent]:
        """Get dead letter events."""
        return self._dead_letter.copy()

    def clear_dead_letter(self) -> None:
        """Clear dead letter queue."""
        self._dead_letter.clear()


# Convenience function for creating event handlers
def event_handler(
    *event_types: RuntimeEventType,
    priority: int = 0
):
    """Decorator to create event handlers."""
    def decorator(func: Callable[[RuntimeEvent], Any]) -> EventHandler:
        class _DecoratedHandler(EventHandler):
            def __init__(self):
                self._func = func
                self._event_types = list(event_types)
                self._priority = priority

            @property
            def handles_event_types(self) -> List[RuntimeEventType]:
                return self._event_types

            @property
            def priority(self) -> int:
                return self._priority

            async def handle(self, event: RuntimeEvent) -> None:
                await self._func(event)

        return _DecoratedHandler()
    return decorator


# Convenience functions for creating standard events
def create_event(
    event_type: RuntimeEventType,
    source: str,
    payload: Dict[str, Any] = None,
    **kwargs
) -> RuntimeEvent:
    """Create a standard runtime event."""
    return RuntimeEvent(
        event_type=event_type,
        source=source,
        payload=payload or {},
        **kwargs
    )


__all__ = [
    "RuntimeEventType",
    "RuntimeEvent",
    "EventHandler",
    "RuntimeEventBus",
    "event_handler",
    "create_event",
    "get_event_bus",
]


# Global event bus instance
_global_event_bus: Optional[RuntimeEventBus] = None


def get_event_bus() -> RuntimeEventBus:
    """Get the global event bus instance."""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = RuntimeEventBus()
    return _global_event_bus


def set_event_bus(bus: RuntimeEventBus) -> None:
    """Set the global event bus instance."""
    global _global_event_bus
    _global_event_bus = bus