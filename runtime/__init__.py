"""
Runtime Package

Provides core runtime functionality and modules for AIPENSA OS.
"""

# Base runtime
from runtime.events import EventBus, Event, EventType
from runtime.plugins import Plugin, PluginManager, PluginRegistry, PluginType, PluginStatus
from runtime.di import Container, ServiceProvider, inject, singleton, transient
from runtime.config import RuntimeConfig, RuntimeType
from runtime.runtime import Runtime

# Core module interfaces
from runtime.modules import (
    RuntimeModule,
    ModuleMetadata,
    ModuleState,
    ModuleRegistry,
    BrowserModule,
    BrowserSession,
    BrowserState,
    ExecutionModule,
    ExecutionResult,
    SandboxInfo,
    ToolModule,
    ToolDefinition,
    ToolExecution,
    MemoryModule,
    MemoryEntry,
    SearchResult,
    PlanningModule,
    Plan,
    PlanStep,
    PlanStatus,
    StepStatus,
    MCPModule,
    MCPServer,
    FileSystemModule,
    FileInfo,
    NetworkModule,
    NetworkRequest,
    NetworkResponse,
    DockerModule,
    ContainerInfo,
)

# Specialized Runtime Modules
from runtime.agent import AgentModule
from runtime.tool import ToolModule as ToolRuntimeModule
from runtime.conversation import ConversationModule
from runtime.workflow import WorkflowModule
from runtime.scheduler import SchedulerModule
from runtime.queue import QueueModule
from runtime.notification import NotificationModule
from runtime.storage import StorageModule
from runtime.authentication import AuthenticationModule
from runtime.workspace import WorkspaceModule
from runtime.knowledge import KnowledgeModule
from runtime.skill import SkillModule
from runtime.llm import LLMModule

# AI Capability Runtime Modules
from runtime.voice import VoiceModule
from runtime.vision import VisionModule
from runtime.video import VideoModule
from runtime.image import ImageModule
from runtime.embedding import EmbeddingModule
from runtime.rag import RAGModule
from runtime.reasoning import ReasoningModule

__all__ = [
    # Base runtime
    "EventBus",
    "Event",
    "EventType",
    "Plugin",
    "PluginManager",
    "PluginRegistry",
    "PluginType",
    "PluginStatus",
    "Container",
    "ServiceProvider",
    "inject",
    "singleton",
    "transient",
    "Runtime",
    "RuntimeConfig",
    "RuntimeType",
    # Core module interfaces
    "RuntimeModule",
    "ModuleMetadata",
    "ModuleState",
    "ModuleRegistry",
    "BrowserModule",
    "BrowserSession",
    "BrowserState",
    "ExecutionModule",
    "ExecutionResult",
    "SandboxInfo",
    "ToolModule",
    "ToolDefinition",
    "ToolExecution",
    "MemoryModule",
    "MemoryEntry",
    "SearchResult",
    "PlanningModule",
    "Plan",
    "PlanStep",
    "PlanStatus",
    "StepStatus",
    "MCPModule",
    "MCPServer",
    "FileSystemModule",
    "FileInfo",
    "NetworkModule",
    "NetworkRequest",
    "NetworkResponse",
    "DockerModule",
    "ContainerInfo",
    # Specialized Runtime Modules (Core)
    "AgentModule",
    "ToolRuntimeModule",
    "ConversationModule",
    "WorkflowModule",
    "SchedulerModule",
    "QueueModule",
    "NotificationModule",
    "StorageModule",
    "AuthenticationModule",
    "WorkspaceModule",
    "KnowledgeModule",
    "SkillModule",
    "LLMModule",
    # AI Capability Runtime Modules
    "VoiceModule",
    "VisionModule",
    "VideoModule",
    "ImageModule",
    "EmbeddingModule",
    "RAGModule",
    "ReasoningModule",
]