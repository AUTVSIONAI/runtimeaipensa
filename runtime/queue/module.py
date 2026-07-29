"""
Queue Runtime Module

Provides message queues with FIFO/LIFO, priority queues,
dead letter queues, and backpressure handling.
"""

from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Deque
import asyncio
import heapq
import logging
import uuid
from sortedcontainers import SortedDict

from runtime.modules import (
    RuntimeModule,
    ModuleMetadata,
    ModuleState,
)

logger = logging.getLogger(__name__)


class QueueType(Enum):
    """Queue implementation type."""
    FIFO = "fifo"
    LIFO = "lifo"
    PRIORITY = "priority"
    DELAYED = "delayed"  # Messages become available after delay


class MessageStatus(Enum):
    """Message processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    RETRYING = "retrying"


@dataclass
class QueueMessage:
    """Queue message."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    payload: Any = None
    priority: int = 0  # Higher = more priority
    status: MessageStatus = MessageStatus.PENDING
    queue_name: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_at: Optional[datetime] = None  # For delayed queues
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)

    def __lt__(self, other: "QueueMessage") -> bool:
        """For priority queue ordering (higher priority first)."""
        if self.priority != other.priority:
            return self.priority > other.priority
        return self.scheduled_at < other.scheduled_at


@dataclass
class QueueStats:
    """Queue statistics."""
    queue_name: str
    queue_type: QueueType
    pending_count: int = 0
    processing_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    dead_letter_count: int = 0
    total_enqueued: int = 0
    total_dequeued: int = 0
    avg_processing_time_ms: float = 0.0
    oldest_pending_age_seconds: float = 0.0


@dataclass
class ConsumerConfig:
    """Consumer configuration."""
    consumer_id: str
    queue_name: str
    handler: Callable[[QueueMessage], Any]
    concurrency: int = 1
    prefetch_count: int = 10
    auto_ack: bool = True
    retry_policy: Optional[Dict[str, Any]] = None
    filter_fn: Optional[Callable[[QueueMessage], bool]] = None


class Queue(ABC):
    """Abstract queue interface."""

    def __init__(self, name: str, queue_type: QueueType):
        self.name = name
        self.queue_type = queue_type
        self._pending: Any = self._create_storage()
        self._processing: Dict[str, QueueMessage] = {}
        self._dead_letter: Deque[QueueMessage] = deque(maxlen=1000)
        self._stats = QueueStats(queue_name=name, queue_type=queue_type)
        self._lock = asyncio.Lock()

    @abstractmethod
    def _create_storage(self) -> Any:
        """Create internal storage."""
        pass

    @abstractmethod
    async def _enqueue_internal(self, message: QueueMessage) -> None:
        """Enqueue message to storage."""
        pass

    @abstractmethod
    async def _dequeue_internal(self, count: int, filter_fn: Optional[Callable] = None) -> List[QueueMessage]:
        """Dequeue messages from storage."""
        pass

    @abstractmethod
    async def _requeue_internal(self, message: QueueMessage) -> None:
        """Requeue message to storage."""
        pass

    @abstractmethod
    async def _remove_internal(self, message_id: str) -> bool:
        """Remove message from storage."""
        pass

    @abstractmethod
    async def _peek_internal(self, count: int) -> List[QueueMessage]:
        """Peek at messages without removing."""
        pass

    @abstractmethod
    async def _get_pending_count(self) -> int:
        """Get pending message count."""
        pass

    async def enqueue(
        self,
        payload: Any,
        priority: int = 0,
        scheduled_at: Optional[datetime] = None,
        max_retries: int = 3,
        metadata: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> QueueMessage:
        """Enqueue a message."""
        message = QueueMessage(
            payload=payload,
            priority=priority,
            queue_name=self.name,
            scheduled_at=scheduled_at,
            max_retries=max_retries,
            metadata=metadata or {},
            headers=headers or {}
        )

        # For delayed queues, schedule for future
        if self.queue_type == QueueType.DELAYED and scheduled_at and scheduled_at > datetime.utcnow():
            pass  # Will be handled by delayed processor

        await self._enqueue_internal(message)

        async with self._lock:
            self._stats.pending_count += 1
            self._stats.total_enqueued += 1

        logger.debug(f"Enqueued message {message.message_id} to queue {self.name}")
        return message

    async def dequeue(
        self,
        count: int = 1,
        filter_fn: Optional[Callable[[QueueMessage], bool]] = None
    ) -> List[QueueMessage]:
        """Dequeue messages for processing."""
        # Check for delayed messages that are ready
        if self.queue_type == QueueType.DELAYED:
            await self._process_delayed_messages()

        messages = await self._dequeue_internal(count, filter_fn)

        if messages:
            async with self._lock:
                self._stats.pending_count -= len(messages)
                self._stats.processing_count += len(messages)
                self._stats.total_dequeued += len(messages)

            for msg in messages:
                msg.status = MessageStatus.PROCESSING
                msg.started_at = datetime.utcnow()
                self._processing[msg.message_id] = msg

        return messages

    async def ack(self, message_id: str) -> bool:
        """Acknowledge successful processing."""
        async with self._lock:
            message = self._processing.pop(message_id, None)
            if message:
                message.status = MessageStatus.COMPLETED
                message.completed_at = datetime.utcnow()
                self._stats.processing_count -= 1
                self._stats.completed_count += 1

                # Update avg processing time
                if message.started_at:
                    duration = (message.completed_at - message.started_at).total_seconds() * 1000
                    self._stats.avg_processing_time_ms = (
                        (self._stats.avg_processing_time_ms * (self._stats.completed_count - 1) + duration)
                        / self._stats.completed_count
                    )

                return True
        return False

    async def nack(
        self,
        message_id: str,
        error: str = "",
        requeue: bool = True
    ) -> bool:
        """Negative acknowledgment - retry or dead letter."""
        async with self._lock:
            message = self._processing.pop(message_id, None)
            if not message:
                return False

            message.retry_count += 1
            message.error = error

            if requeue and message.retry_count <= message.max_retries:
                message.status = MessageStatus.RETRYING
                self._stats.processing_count -= 1
                await self._requeue_internal(message)
                self._stats.pending_count += 1
            else:
                message.status = MessageStatus.DEAD_LETTER
                message.completed_at = datetime.utcnow()
                self._stats.processing_count -= 1
                self._stats.failed_count += 1
                self._stats.dead_letter_count += 1
                self._dead_letter.append(message)

            return True

    async def get_stats(self) -> QueueStats:
        """Get queue statistics."""
        async with self._lock:
            # Update oldest pending age
            if self._pending:
                if hasattr(self._pending, 'peek_oldest'):
                    oldest = self._pending.peek_oldest()
                elif hasattr(self._pending, 'first'):
                    oldest = self._pending.first()
                else:
                    oldest = None

                if oldest and hasattr(oldest, 'created_at'):
                    self._stats.oldest_pending_age_seconds = (
                        datetime.utcnow() - oldest.created_at
                    ).total_seconds()

            return QueueStats(
                queue_name=self._stats.queue_name,
                queue_type=self._stats.queue_type,
                pending_count=self._stats.pending_count,
                processing_count=self._stats.processing_count,
                completed_count=self._stats.completed_count,
                failed_count=self._stats.failed_count,
                dead_letter_count=self._stats.dead_letter_count,
                total_enqueued=self._stats.total_enqueued,
                total_dequeued=self._stats.total_dequeued,
                avg_processing_time_ms=self._stats.avg_processing_time_ms,
                oldest_pending_age_seconds=self._stats.oldest_pending_age_seconds
            )

    async def get_dead_letter(self, limit: int = 100) -> List[QueueMessage]:
        """Get dead letter messages."""
        return list(self._dead_letter)[:limit]

    async def clear_dead_letter(self) -> int:
        """Clear dead letter queue."""
        count = len(self._dead_letter)
        self._dead_letter.clear()
        return count

    async def purge(self) -> int:
        """Purge all pending messages."""
        count = 0
        if hasattr(self._pending, 'clear'):
            count = len(self._pending)
            self._pending.clear()
        elif hasattr(self._pending, '__len__'):
            count = len(self._pending)
            self._pending = self._create_storage()

        async with self._lock:
            self._stats.pending_count = 0
        return count

    async def _process_delayed_messages(self) -> None:
        """Move ready delayed messages to pending."""
        now = datetime.utcnow()
        ready = []

        # This would need to be implemented per queue type
        pass


class FifoQueue(Queue):
    """First-In-First-Out queue."""

    def _create_storage(self) -> Deque[QueueMessage]:
        return deque()

    async def _enqueue_internal(self, message: QueueMessage) -> None:
        self._pending.append(message)

    async def _dequeue_internal(
        self,
        count: int,
        filter_fn: Optional[Callable] = None
    ) -> List[QueueMessage]:
        messages = []
        for _ in range(min(count, len(self._pending))):
            msg = self._pending.popleft()
            if filter_fn and not filter_fn(msg):
                # Put back if filtered out
                self._pending.appendleft(msg)
                break
            messages.append(msg)
        return messages

    async def _requeue_internal(self, message: QueueMessage) -> None:
        self._pending.appendleft(message)

    async def _remove_internal(self, message_id: str) -> bool:
        for i, msg in enumerate(self._pending):
            if msg.message_id == message_id:
                del self._pending[i]
                return True
        return False

    async def _peek_internal(self, count: int) -> List[QueueMessage]:
        return list(self._pending)[:count]

    async def _get_pending_count(self) -> int:
        return len(self._pending)


class LifoQueue(Queue):
    """Last-In-First-Out queue (stack)."""

    def _create_storage(self) -> List[QueueMessage]:
        return []

    async def _enqueue_internal(self, message: QueueMessage) -> None:
        self._pending.append(message)

    async def _dequeue_internal(
        self,
        count: int,
        filter_fn: Optional[Callable] = None
    ) -> List[QueueMessage]:
        messages = []
        for _ in range(min(count, len(self._pending))):
            if not self._pending:
                break
            msg = self._pending.pop()
            if filter_fn and not filter_fn(msg):
                self._pending.append(msg)
                break
            messages.append(msg)
        return messages

    async def _requeue_internal(self, message: QueueMessage) -> None:
        self._pending.append(message)

    async def _remove_internal(self, message_id: str) -> bool:
        for i, msg in enumerate(self._pending):
            if msg.message_id == message_id:
                del self._pending[i]
                return True
        return False

    async def _peek_internal(self, count: int) -> List[QueueMessage]:
        return list(reversed(self._pending))[:count]

    async def _get_pending_count(self) -> int:
        return len(self._pending)


class PriorityQueue(Queue):
    """Priority queue (highest priority first)."""

    def _create_storage(self) -> List[QueueMessage]:
        return []

    async def _enqueue_internal(self, message: QueueMessage) -> None:
        heapq.heappush(self._pending, message)

    async def _dequeue_internal(
        self,
        count: int,
        filter_fn: Optional[Callable] = None
    ) -> List[QueueMessage]:
        messages = []
        temp = []

        for _ in range(min(count, len(self._pending))):
            if not self._pending:
                break
            msg = heapq.heappop(self._pending)
            if filter_fn and not filter_fn(msg):
                temp.append(msg)
                continue
            messages.append(msg)

        # Put filtered messages back
        for msg in temp:
            heapq.heappush(self._pending, msg)

        return messages

    async def _requeue_internal(self, message: QueueMessage) -> None:
        heapq.heappush(self._pending, message)

    async def _remove_internal(self, message_id: str) -> bool:
        for i, msg in enumerate(self._pending):
            if msg.message_id == message_id:
                self._pending.pop(i)
                heapq.heapify(self._pending)
                return True
        return False

    async def _peek_internal(self, count: int) -> List[QueueMessage]:
        return sorted(self._pending, key=lambda m: (-m.priority, m.scheduled_at))[:count]

    async def _get_pending_count(self) -> int:
        return len(self._pending)


class DelayedQueue(PriorityQueue):
    """Delayed queue - messages become available after scheduled time."""

    async def _process_delayed_messages(self) -> None:
        now = datetime.utcnow()
        ready = []

        # Extract ready messages
        while self._pending and self._pending[0].scheduled_at and self._pending[0].scheduled_at <= now:
            ready.append(heapq.heappop(self._pending))

        # Re-insert with normal priority (they'll be dequeued normally)
        for msg in ready:
            msg.scheduled_at = None  # Clear scheduled time
            heapq.heappush(self._pending, msg)


class QueueModule(RuntimeModule):
    """
    Queue module for message queuing.

    Supports multiple queue types:
    - FIFO: First-in-first-out
    - LIFO: Last-in-first-out (stack)
    - PRIORITY: Priority-based ordering
    - DELAYED: Scheduled delivery
    """

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="queue",
            version="1.0.0",
            description="Message queue with multiple queue types and backpressure",
            author="AIPENSA",
            dependencies=[],
            provides=["message_queue", "priority_queue", "delayed_queue", "dead_letter_queue"],
            tags={"queue", "messaging", "async", "backpressure"}
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._queues: Dict[str, Queue] = {}
        self._consumers: Dict[str, ConsumerConfig] = {}
        self._consumer_tasks: Dict[str, asyncio.Task] = {}
        self._default_queue_type = QueueType(config.get("default_queue_type", "fifo")) if config else QueueType.FIFO
        self._max_queue_size = config.get("max_queue_size", 10000) if config else 10000
        self._backpressure_threshold = config.get("backpressure_threshold", 0.8) if config else 0.8
        self._delayed_processor_task: Optional[asyncio.Task] = None

    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        """Initialize queue module."""
        self._runtime = runtime
        self._config = {**self._config, **config}
        self._default_queue_type = QueueType(self._config.get("default_queue_type", self._default_queue_type.value))
        self._max_queue_size = self._config.get("max_queue_size", self._max_queue_size)
        self._backpressure_threshold = self._config.get("backpressure_threshold", self._backpressure_threshold)

        # Create default queues from config
        for queue_config in self._config.get("queues", []):
            await self.create_queue(**queue_config)

        self.state = ModuleState.INITIALIZED
        logger.info(f"Queue module initialized with {len(self._queues)} queues")

    async def start(self) -> None:
        """Start queue module."""
        self.state = ModuleState.RUNNING
        # Start delayed message processor
        self._delayed_processor_task = asyncio.create_task(self._delayed_processor())
        logger.info("Queue module started")

    async def stop(self) -> None:
        """Stop queue module."""
        # Stop consumers
        for consumer_id in list(self._consumer_tasks.keys()):
            await self.stop_consumer(consumer_id)

        # Stop delayed processor
        if self._delayed_processor_task:
            self._delayed_processor_task.cancel()
            try:
                await self._delayed_processor_task
            except asyncio.CancelledError:
                pass

        self.state = ModuleState.STOPPED
        logger.info("Queue module stopped")

    async def cleanup(self) -> None:
        """Clean up resources."""
        await self.stop()
        self._queues.clear()
        self._consumers.clear()
        self.state = ModuleState.UNINITIALIZED
        logger.info("Queue module cleaned up")

    async def health_check(self) -> Dict[str, Any]:
        """Health check."""
        queue_stats = {}
        total_pending = 0
        for name, queue in self._queues.items():
            stats = await queue.get_stats()
            queue_stats[name] = {
                "type": stats.queue_type.value,
                "pending": stats.pending_count,
                "processing": stats.processing_count,
                "completed": stats.completed_count,
                "dead_letter": stats.dead_letter_count
            }
            total_pending += stats.pending_count

        return {
            "module": "queue",
            "status": self.state.value,
            "healthy": self.state == ModuleState.RUNNING,
            "queue_count": len(self._queues),
            "consumer_count": len(self._consumers),
            "total_pending": total_pending,
            "queues": queue_stats
        }

    def _create_queue(self, name: str, queue_type: QueueType) -> Queue:
        """Create queue instance based on type."""
        if queue_type == QueueType.FIFO:
            return FifoQueue(name, queue_type)
        elif queue_type == QueueType.LIFO:
            return LifoQueue(name, queue_type)
        elif queue_type == QueueType.PRIORITY:
            return PriorityQueue(name, queue_type)
        elif queue_type == QueueType.DELAYED:
            return DelayedQueue(name, queue_type)
        else:
            raise ValueError(f"Unknown queue type: {queue_type}")

    # Queue Management
    async def create_queue(
        self,
        name: str,
        queue_type: QueueType = QueueType.FIFO,
        max_size: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Queue:
        """Create a new queue."""
        if name in self._queues:
            raise ValueError(f"Queue already exists: {name}")

        queue = self._create_queue(name, queue_type)
        self._queues[name] = queue
        logger.info(f"Created queue: {name} ({queue_type.value})")
        return queue

    async def get_queue(self, name: str) -> Optional[Queue]:
        """Get queue by name."""
        return self._queues.get(name)

    async def delete_queue(self, name: str) -> bool:
        """Delete a queue."""
        if name in self._queues:
            del self._queues[name]
            logger.info(f"Deleted queue: {name}")
            return True
        return False

    async def list_queues(self) -> List[str]:
        """List all queue names."""
        return list(self._queues.keys())

    async def get_queue_stats(self, name: str) -> Optional[QueueStats]:
        """Get queue statistics."""
        queue = self._queues.get(name)
        if queue:
            return await queue.get_stats()
        return None

    async def get_all_stats(self) -> Dict[str, QueueStats]:
        """Get all queue statistics."""
        stats = {}
        for name, queue in self._queues.items():
            stats[name] = await queue.get_stats()
        return stats

    # Message Operations
    async def enqueue(
        self,
        queue_name: str,
        payload: Any,
        priority: int = 0,
        scheduled_at: Optional[datetime] = None,
        max_retries: int = 3,
        metadata: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> QueueMessage:
        """Enqueue a message to a queue."""
        queue = self._queues.get(queue_name)
        if not queue:
            raise ValueError(f"Queue not found: {queue_name}")

        # Check backpressure
        stats = await queue.get_stats()
        max_size = self._max_queue_size
        if stats.pending_count >= max_size * self._backpressure_threshold:
            logger.warning(f"Queue {queue_name} approaching capacity: {stats.pending_count}/{max_size}")

        return await queue.enqueue(payload, priority, scheduled_at, max_retries, metadata, headers)

    async def dequeue(
        self,
        queue_name: str,
        count: int = 1,
        filter_fn: Optional[Callable[[QueueMessage], bool]] = None
    ) -> List[QueueMessage]:
        """Dequeue messages from a queue."""
        queue = self._queues.get(queue_name)
        if not queue:
            raise ValueError(f"Queue not found: {queue_name}")
        return await queue.dequeue(count, filter_fn)

    async def ack(self, queue_name: str, message_id: str) -> bool:
        """Acknowledge message."""
        queue = self._queues.get(queue_name)
        if queue:
            return await queue.ack(message_id)
        return False

    async def nack(
        self,
        queue_name: str,
        message_id: str,
        error: str = "",
        requeue: bool = True
    ) -> bool:
        """Negative acknowledge message."""
        queue = self._queues.get(queue_name)
        if queue:
            return await queue.nack(message_id, error, requeue)
        return False

    async def get_dead_letter(self, queue_name: str, limit: int = 100) -> List[QueueMessage]:
        """Get dead letter messages."""
        queue = self._queues.get(queue_name)
        if queue:
            return await queue.get_dead_letter(limit)
        return []

    async def purge_queue(self, queue_name: str) -> int:
        """Purge all messages from queue."""
        queue = self._queues.get(queue_name)
        if queue:
            return await queue.purge()
        return 0

    # Consumer Management
    async def register_consumer(self, config: ConsumerConfig) -> str:
        """Register a message consumer."""
        if config.consumer_id in self._consumers:
            raise ValueError(f"Consumer already exists: {config.consumer_id}")

        queue = self._queues.get(config.queue_name)
        if not queue:
            raise ValueError(f"Queue not found: {config.queue_name}")

        self._consumers[config.consumer_id] = config
        await self._start_consumer(config.consumer_id)
        logger.info(f"Registered consumer: {config.consumer_id} for queue {config.queue_name}")
        return config.consumer_id

    async def _start_consumer(self, consumer_id: str) -> None:
        """Start consumer task."""
        config = self._consumers[consumer_id]
        queue = self._queues[config.queue_name]

        async def consumer_loop():
            while True:
                try:
                    # Check concurrency limit
                    # For simplicity, we just process messages
                    messages = await queue.dequeue(config.prefetch_count)

                    if not messages:
                        await asyncio.sleep(0.1)
                        continue

                    # Process messages
                    for msg in messages:
                        try:
                            if config.filter_fn and not config.filter_fn(msg):
                                await queue.nack(msg.message_id, "Filtered out", requeue=False)
                                continue

                            result = await config.handler(msg)

                            if config.auto_ack:
                                await queue.ack(msg.message_id)
                            # Otherwise handler must call ack/nack

                        except Exception as e:
                            logger.error(f"Consumer {consumer_id} error: {e}")
                            await queue.nack(msg.message_id, str(e))

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Consumer {consumer_id} loop error: {e}")
                    await asyncio.sleep(1)

        self._consumer_tasks[consumer_id] = asyncio.create_task(consumer_loop())

    async def stop_consumer(self, consumer_id: str) -> bool:
        """Stop a consumer."""
        if consumer_id in self._consumer_tasks:
            self._consumer_tasks[consumer_id].cancel()
            try:
                await self._consumer_tasks[consumer_id]
            except asyncio.CancelledError:
                pass
            del self._consumer_tasks[consumer_id]
            del self._consumers[consumer_id]
            logger.info(f"Stopped consumer: {consumer_id}")
            return True
        return False

    async def list_consumers(self) -> List[str]:
        """List consumer IDs."""
        return list(self._consumers.keys())

    async def _delayed_processor(self) -> None:
        """Process delayed messages."""
        while True:
            try:
                for queue in self._queues.values():
                    if isinstance(queue, DelayedQueue):
                        await queue._process_delayed_messages()
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Delayed processor error: {e}")
                await asyncio.sleep(1)

    # Module Operations
    async def execute(self, operation: str, **kwargs) -> Any:
        """Execute module operations."""
        if operation == "create_queue":
            return await self.create_queue(**kwargs)
        elif operation == "get_queue":
            return await self.get_queue(kwargs.get("name"))
        elif operation == "delete_queue":
            return await self.delete_queue(kwargs.get("name"))
        elif operation == "list_queues":
            return await self.list_queues()
        elif operation == "get_queue_stats":
            return await self.get_queue_stats(kwargs.get("name"))
        elif operation == "get_all_stats":
            return await self.get_all_stats()
        elif operation == "enqueue":
            return await self.enqueue(**kwargs)
        elif operation == "dequeue":
            return await self.dequeue(**kwargs)
        elif operation == "ack":
            return await self.ack(kwargs.get("queue_name"), kwargs.get("message_id"))
        elif operation == "nack":
            return await self.nack(kwargs.get("queue_name"), kwargs.get("message_id"), kwargs.get("error", ""), kwargs.get("requeue", True))
        elif operation == "get_dead_letter":
            return await self.get_dead_letter(kwargs.get("queue_name"), kwargs.get("limit", 100))
        elif operation == "purge_queue":
            return await self.purge_queue(kwargs.get("queue_name"))
        elif operation == "register_consumer":
            return await self.register_consumer(kwargs.get("config"))
        elif operation == "stop_consumer":
            return await self.stop_consumer(kwargs.get("consumer_id"))
        elif operation == "list_consumers":
            return await self.list_consumers()
        else:
            raise NotImplementedError(f"Operation '{operation}' not supported")


__all__ = [
    "QueueModule",
    "Queue",
    "FifoQueue",
    "LifoQueue",
    "PriorityQueue",
    "DelayedQueue",
    "QueueMessage",
    "QueueStats",
    "QueueType",
    "MessageStatus",
    "ConsumerConfig",
]