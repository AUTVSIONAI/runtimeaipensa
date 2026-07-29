"""
Queue Runtime Module

Provides message queues with FIFO/LIFO, priority queues,
dead letter queues, and backpressure handling.
"""

from runtime.queue.module import (
    QueueModule,
    Queue,
    FifoQueue,
    LifoQueue,
    PriorityQueue,
    DelayedQueue,
    QueueMessage,
    QueueStats,
    QueueType,
    MessageStatus,
    ConsumerConfig,
)

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