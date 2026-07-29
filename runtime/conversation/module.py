"""
Conversation Runtime Module

Provides conversation management, message history, context management,
and streaming response capabilities for AI agents.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Callable
import asyncio
import json
import logging
import uuid

from runtime.base.module import (
    RuntimeModule,
    ModuleMetadata,
    ModuleState,
)
from runtime.events import get_event_bus
from runtime.base.events import create_event, RuntimeEventType

logger = logging.getLogger(__name__)


class MessageRole(Enum):
    """Message roles in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    FUNCTION = "function"


class MessageType(Enum):
    """Message types."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"


@dataclass
class Message:
    """Conversation message."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    role: MessageRole = MessageRole.USER
    content: str = ""
    message_type: MessageType = MessageType.TEXT
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_call_id: Optional[str] = None
    name: Optional[str] = None  # For function/tool messages
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "message_id": self.message_id,
            "role": self.role.value,
            "content": self.content,
            "type": self.message_type.value,
            "tool_calls": self.tool_calls,
            "tool_call_id": self.tool_call_id,
            "name": self.name,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create message from dictionary."""
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())[:8]),
            role=MessageRole(data.get("role", "user")),
            content=data.get("content", ""),
            message_type=MessageType(data.get("type", "text")),
            tool_calls=data.get("tool_calls", []),
            tool_call_id=data.get("tool_call_id"),
            name=data.get("name"),
            metadata=data.get("metadata", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.utcnow()
        )


@dataclass
class Conversation:
    """Conversation session."""
    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    messages: List[Message] = field(default_factory=list)
    system_prompt: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    max_messages: int = 100
    max_tokens: int = 8000

    def add_message(self, message: Message) -> None:
        """Add message to conversation."""
        self.messages.append(message)
        self.updated_at = datetime.utcnow()

        # Trim if exceeds max messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def get_messages(self, limit: Optional[int] = None, roles: Optional[List[MessageRole]] = None) -> List[Message]:
        """Get messages with optional filtering."""
        messages = self.messages
        if roles:
            messages = [m for m in messages if m.role in roles]
        if limit:
            messages = messages[-limit:]
        return messages

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "conversation_id": self.conversation_id,
            "title": self.title,
            "messages": [m.to_dict() for m in self.messages],
            "system_prompt": self.system_prompt,
            "context": self.context,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "max_messages": self.max_messages,
            "max_tokens": self.max_tokens
        }


@dataclass
class StreamingResponse:
    """Streaming response from LLM."""
    conversation_id: str
    chunk: str
    done: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "chunk": self.chunk,
            "done": self.done,
            "metadata": self.metadata
        }


class ConversationModule(RuntimeModule):
    """
    Conversation management module.

    Provides conversation lifecycle, message history, context management,
    and streaming responses for AI agents.
    """

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="conversation",
            version="1.0.0",
            description="Conversation management and message history",
            author="AIPENSA",
            dependencies=["memory", "llm"],
            provides=["conversation_management", "message_history", "context_management", "streaming"],
            tags={"conversation", "chat", "context", "streaming"}
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._conversations: Dict[str, Conversation] = {}
        self._max_conversations = self.config.get("max_conversations", 1000)
        self._default_max_messages = self.config.get("default_max_messages", 100)
        self._default_max_tokens = self.config.get("default_max_tokens", 8000)
        self._stream_handlers: Dict[str, Callable[[StreamingResponse], None]] = {}
        self._default_system_prompt = self.config.get("default_system_prompt", "")

    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        """Initialize conversation module."""
        await super().initialize(runtime, config)
        self.config = {**self.config, **config}
        self._max_conversations = self.config.get("max_conversations", self._max_conversations)
        self._default_max_messages = self.config.get("default_max_messages", self._default_max_messages)
        self._default_max_tokens = self.config.get("default_max_tokens", self._default_max_tokens)
        self._default_system_prompt = self.config.get("default_system_prompt", self._default_system_prompt)

        # Load persisted conversations if configured
        persist_path = self.config.get("persist_path")
        if persist_path:
            await self._load_conversations(persist_path)

        logger.info(f"Conversation module initialized with {len(self._conversations)} conversations")

    async def start(self) -> None:
        """Start conversation module."""
        await super().start()
        logger.info("Conversation module started")

    async def stop(self) -> None:
        """Stop conversation module."""
        await super().stop()
        logger.info("Conversation module stopped")

    async def cleanup(self) -> None:
        """Clean up resources."""
        # Save conversations if persistence enabled
        persist_path = self.config.get("persist_path")
        if persist_path:
            await self._save_conversations(persist_path)

        self._conversations.clear()
        self._stream_handlers.clear()
        await super().cleanup()
        logger.info("Conversation module cleaned up")

    async def health_check(self) -> Dict[str, Any]:
        """Health check."""
        active_conversations = len([c for c in self._conversations.values() if c.messages])
        return {
            "module": "conversation",
            "status": self._state.value,
            "healthy": self._state == ModuleState.RUNNING,
            "total_conversations": len(self._conversations),
            "active_conversations": active_conversations,
            "total_messages": sum(len(c.messages) for c in self._conversations.values())
        }

    # Conversation Management
    async def create_conversation(
        self,
        title: str = "",
        system_prompt: str = "",
        context: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None,
        max_messages: Optional[int] = None,
        max_tokens: Optional[int] = None
    ) -> Conversation:
        """Create a new conversation."""
        if len(self._conversations) >= self._max_conversations:
            # Remove oldest inactive conversation
            oldest = min(self._conversations.values(), key=lambda c: c.updated_at)
            del self._conversations[oldest.conversation_id]

        conv = Conversation(
            conversation_id=conversation_id or str(uuid.uuid4())[:8],
            title=title or f"Conversation {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            system_prompt=system_prompt or self._default_system_prompt,
            context=context or {},
            max_messages=max_messages or self._default_max_messages,
            max_tokens=max_tokens or self._default_max_tokens
        )

        self._conversations[conv.conversation_id] = conv
        logger.info(f"Created conversation: {conv.conversation_id} - {conv.title}")

        # Publish event
        event_bus = get_event_bus()
        await event_bus.publish(create_event(
            event_type=RuntimeEventType.CONVERSATION_STARTED,
            source=self.metadata.name,
            payload={
                "conversation_id": conv.conversation_id,
                "title": conv.title,
                "system_prompt": conv.system_prompt
            }
        ))

        return conv

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation by ID."""
        return self._conversations.get(conversation_id)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            logger.info(f"Deleted conversation: {conversation_id}")

            # Publish event
            event_bus = get_event_bus()
            await event_bus.publish(create_event(
                event_type=RuntimeEventType.CONVERSATION_ENDED,
                source=self.name,
                payload={"conversation_id": conversation_id}
            ))

            return True
        return False

    async def list_conversations(
        self,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "updated_at",
        descending: bool = True
    ) -> List[Conversation]:
        """List conversations with pagination."""
        conversations = list(self._conversations.values())

        if sort_by == "updated_at":
            conversations.sort(key=lambda c: c.updated_at, reverse=descending)
        elif sort_by == "created_at":
            conversations.sort(key=lambda c: c.created_at, reverse=descending)
        elif sort_by == "message_count":
            conversations.sort(key=lambda c: len(c.messages), reverse=descending)

        return conversations[offset:offset + limit]

    # Message Management
    async def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_call_id: Optional[str] = None,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Message]:
        """Add a message to a conversation."""
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            logger.warning(f"Conversation not found: {conversation_id}")
            return None

        message = Message(
            role=role,
            content=content,
            message_type=message_type,
            tool_calls=tool_calls or [],
            tool_call_id=tool_call_id,
            name=name,
            metadata=metadata or {}
        )

        conversation.add_message(message)

        # Publish event
        event_bus = get_event_bus()
        await event_bus.publish(create_event(
            event_type=RuntimeEventType.MESSAGE_RECEIVED if role == MessageRole.USER else RuntimeEventType.MESSAGE_SENT,
            source=self.name,
            payload={
                "conversation_id": conversation_id,
                "message_id": message.message_id,
                "role": role.value,
                "content": content,
                "message_type": message_type.value
            }
        ))

        return message

    async def get_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        roles: Optional[List[MessageRole]] = None,
        before_message_id: Optional[str] = None
    ) -> List[Message]:
        """Get messages from a conversation."""
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return []

        messages = conversation.messages

        if before_message_id:
            idx = next((i for i, m in enumerate(messages) if m.message_id == before_message_id), len(messages))
            messages = messages[:idx]

        if roles:
            messages = [m for m in messages if m.role in roles]

        if limit:
            messages = messages[-limit:]

        return messages

    async def clear_messages(self, conversation_id: str, keep_system: bool = True) -> int:
        """Clear messages from a conversation."""
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return 0

        count = len(conversation.messages)
        if keep_system:
            conversation.messages = [m for m in conversation.messages if m.role == MessageRole.SYSTEM]
        else:
            conversation.messages.clear()

        return count

    # Context Management
    async def update_context(self, conversation_id: str, context: Dict[str, Any]) -> bool:
        """Update conversation context."""
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return False

        conversation.context.update(context)
        conversation.updated_at = datetime.utcnow()
        return True

    async def get_context(self, conversation_id: str) -> Dict[str, Any]:
        """Get conversation context."""
        conversation = self._conversations.get(conversation_id)
        return conversation.context if conversation else {}

    # Streaming
    def register_stream_handler(self, conversation_id: str, handler: Callable[[StreamingResponse], None]) -> None:
        """Register a streaming response handler for a conversation."""
        self._stream_handlers[conversation_id] = handler

    def unregister_stream_handler(self, conversation_id: str) -> None:
        """Unregister a streaming handler."""
        self._stream_handlers.pop(conversation_id, None)

    async def stream_response(
        self,
        conversation_id: str,
        chunks: AsyncIterator[str]
    ) -> AsyncIterator[StreamingResponse]:
        """Stream a response to a conversation."""
        handler = self._stream_handlers.get(conversation_id)

        accumulated = ""
        async for chunk in chunks:
            accumulated += chunk
            response = StreamingResponse(
                conversation_id=conversation_id,
                chunk=chunk,
                done=False,
                metadata={"accumulated_length": len(accumulated)}
            )

            if handler:
                try:
                    await handler(response)
                except Exception as e:
                    logger.error(f"Stream handler error: {e}")

            yield response

        # Final chunk
        final_response = StreamingResponse(
            conversation_id=conversation_id,
            chunk="",
            done=True,
            metadata={"full_response": accumulated}
        )

        if handler:
            try:
                await handler(final_response)
            except Exception as e:
                logger.error(f"Stream handler error: {e}")

        yield final_response

        # Add assistant message to conversation
        await self.add_message(conversation_id, MessageRole.ASSISTANT, accumulated)

    # Serialization
    async def export_conversation(self, conversation_id: str) -> Optional[str]:
        """Export conversation as JSON."""
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return None

        return json.dumps(conversation.to_dict(), indent=2)

    async def import_conversation(self, json_data: str) -> Optional[Conversation]:
        """Import conversation from JSON."""
        try:
            data = json.loads(json_data)
            messages = [Message.from_dict(m) for m in data.get("messages", [])]

            conversation = Conversation(
                conversation_id=data.get("conversation_id", str(uuid.uuid4())[:8]),
                title=data.get("title", ""),
                messages=messages,
                system_prompt=data.get("system_prompt", ""),
                context=data.get("context", {}),
                metadata=data.get("metadata", {}),
                max_messages=data.get("max_messages", self._default_max_messages),
                max_tokens=data.get("max_tokens", self._default_max_tokens),
                created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow(),
                updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.utcnow()
            )

            self._conversations[conversation.conversation_id] = conversation
            return conversation
        except Exception as e:
            logger.error(f"Failed to import conversation: {e}")
            return None

    # Persistence
    async def _load_conversations(self, path: str) -> None:
        """Load conversations from disk."""
        import os
        import aiofiles

        if not os.path.exists(path):
            return

        try:
            for filename in os.listdir(path):
                if filename.endswith(".json"):
                    filepath = os.path.join(path, filename)
                    async with aiofiles.open(filepath, 'r') as f:
                        content = await f.read()
                        await self.import_conversation(content)

            logger.info(f"Loaded {len(self._conversations)} conversations from {path}")
        except Exception as e:
            logger.error(f"Failed to load conversations: {e}")

    async def _save_conversations(self, path: str) -> None:
        """Save conversations to disk."""
        import os
        import aiofiles

        os.makedirs(path, exist_ok=True)

        try:
            for conv in self._conversations.values():
                filepath = os.path.join(path, f"{conv.conversation_id}.json")
                async with aiofiles.open(filepath, 'w') as f:
                    await f.write(json.dumps(conv.to_dict(), indent=2))

            logger.info(f"Saved {len(self._conversations)} conversations to {path}")
        except Exception as e:
            logger.error(f"Failed to save conversations: {e}")

    # Module Operations
    async def execute(self, operation: str, **kwargs) -> Any:
        """Execute module operations."""
        if operation == "create_conversation":
            return await self.create_conversation(**kwargs)
        elif operation == "get_conversation":
            return await self.get_conversation(kwargs.get("conversation_id"))
        elif operation == "delete_conversation":
            return await self.delete_conversation(kwargs.get("conversation_id"))
        elif operation == "list_conversations":
            return await self.list_conversations(**kwargs)
        elif operation == "add_message":
            return await self.add_message(**kwargs)
        elif operation == "get_messages":
            return await self.get_messages(**kwargs)
        elif operation == "update_context":
            return await self.update_context(**kwargs)
        elif operation == "get_context":
            return await self.get_context(kwargs.get("conversation_id"))
        elif operation == "export_conversation":
            return await self.export_conversation(kwargs.get("conversation_id"))
        elif operation == "import_conversation":
            return await self.import_conversation(kwargs.get("json_data"))
        else:
            raise NotImplementedError(f"Operation '{operation}' not supported")


# Export
__all__ = [
    "ConversationModule",
    "Conversation",
    "Message",
    "MessageRole",
    "MessageType",
    "StreamingResponse",
]