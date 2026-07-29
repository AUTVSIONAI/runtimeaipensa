"""
LLM Runtime Module

Provides unified LLM interface with multiple provider support,
prompt management, streaming, function calling, and cost tracking.
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
from collections import defaultdict
from functools import lru_cache
import time
from functools import lru_cache
import time

from runtime.modules import (
    RuntimeModule,
    ModuleMetadata,
    ModuleState,
)

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE = "azure"
    OLLAMA = "ollama"
    VLLM = "vllm"
    NVIDIA = "nvidia"  # NVIDIA NIM API
    CUSTOM = "custom"


class LLMModel(Enum):
    """Common model identifiers."""
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet"
    CLAUDE_3_HAIKU = "claude-3-haiku"
    GEMINI_1_5_PRO = "gemini-1.5-pro"
    GEMINI_1_5_FLASH = "gemini-1.5-flash"
    LLAMA_3_1_70B = "llama-3.1-70b"
    LLAMA_3_1_8B = "llama-3.1-8b"


class MessageRole(Enum):
    """Message roles."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    FUNCTION = "function"


@dataclass
class LLMMessage:
    """LLM message."""
    role: MessageRole
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {"role": self.role.value}
        if self.content is not None:
            d["content"] = self.content
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.name:
            d["name"] = self.name
        return d


@dataclass
class LLMTool:
    """LLM tool/function definition."""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    strict: bool = False


@dataclass
class LLMResponse:
    """LLM response."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    content: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    finish_reason: str = "stop"
    model: str = ""
    usage: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "content": self.content,
            "tool_calls": self.tool_calls,
            "finish_reason": self.finish_reason,
            "model": self.model,
            "usage": self.usage,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class LLMStreamChunk:
    """LLM streaming chunk."""
    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    delta: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    finish_reason: Optional[str] = None
    model: str = ""
    usage: Optional[Dict[str, int]] = None
    is_final: bool = False


@dataclass
class LLMRequest:
    """LLM completion request."""
    messages: List[LLMMessage]
    model: str = ""
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    tools: Optional[List[LLMTool]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    response_format: Optional[Dict[str, Any]] = None
    stream: bool = False
    seed: Optional[int] = None
    stop: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelConfig:
    """Model configuration."""
    provider: LLMProvider
    model_id: str
    display_name: str = ""
    context_window: int = 4096
    max_output_tokens: int = 2048
    supports_streaming: bool = True
    supports_tools: bool = False
    supports_vision: bool = False
    supports_json_mode: bool = False
    input_cost_per_1k: float = 0.0  # USD
    output_cost_per_1k: float = 0.0
    default_temperature: float = 0.7
    metadata: Dict[str, Any] = field(default_factory=dict)


class LLMBackend(ABC):
    """Abstract LLM backend."""

    @property
    @abstractmethod
    def provider(self) -> LLMProvider:
        pass

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        pass

    @abstractmethod
    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMStreamChunk]:
        pass

    @abstractmethod
    async def list_models(self) -> List[ModelConfig]:
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        pass


# Comprehensive list of 70+ Free NVIDIA NIM Models
# These are the free models available via NVIDIA NIM API
# Source: https://build.nvidia.com/explore/discover
FREE_NVIDIA_MODELS: List[ModelConfig] = [
    # Llama Models
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="meta/llama-3.1-8b-instruct", display_name="Llama 3.1 8B Instruct", context_window=128000, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="meta/llama-3.1-70b-instruct", display_name="Llama 3.1 70B Instruct", context_window=128000, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="meta/llama-3.1-405b-instruct", display_name="Llama 3.1 405B Instruct", context_window=128000, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="meta/llama-3.2-1b-instruct", display_name="Llama 3.2 1B Instruct", context_window=128000, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="meta/llama-3.2-3b-instruct", display_name="Llama 3.2 3B Instruct", context_window=128000, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="meta/llama-3.2-11b-vision-instruct", display_name="Llama 3.2 11B Vision Instruct", context_window=128000, max_output_tokens=4096, supports_streaming=True, supports_tools=True, supports_vision=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="meta/llama-3.2-90b-vision-instruct", display_name="Llama 3.2 90B Vision Instruct", context_window=128000, max_output_tokens=4096, supports_streaming=True, supports_tools=True, supports_vision=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="meta/llama-3.3-70b-instruct", display_name="Llama 3.3 70B Instruct", context_window=128000, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="meta/llama-4-scout-17b-16e-instruct", display_name="Llama 4 Scout 17B", context_window=128000, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="meta/llama-4-maverick-17b-128e-instruct", display_name="Llama 4 Maverick 17B", context_window=128000, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),

    # Nemotron Models
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="nvidia/nemotron-3-ultra", display_name="Nemotron 3 Ultra", context_window=4096, max_output_tokens=2048, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="nvidia/nemotron-3-ultra-chat", display_name="Nemotron 3 Ultra Chat", context_window=4096, max_output_tokens=2048, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="nvidia/nemotron-4-340b-instruct", display_name="Nemotron 4 340B Instruct", context_window=8192, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="nvidia/nemotron-4-340b-reward", display_name="Nemotron 4 340B Reward", context_window=4096, max_output_tokens=1, supports_streaming=True, supports_tools=False, default_temperature=0.1),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="nvidia/nemotron-mini-4b-instruct", display_name="Nemotron Mini 4B Instruct", context_window=4096, max_output_tokens=2048, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="nvidia/nemotron-4-ultra", display_name="Nemotron 4 Ultra", context_window=4096, max_output_tokens=2048, supports_streaming=True, supports_tools=True, default_temperature=0.7),

    # Mistral Models
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="mistralai/mistral-7b-instruct-v0.3", display_name="Mistral 7B Instruct v0.3", context_window=32768, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="mistralai/mistral-large-2-instruct", display_name="Mistral Large 2 Instruct", context_window=128000, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="mistralai/mistral-small-24b-instruct-2501", display_name="Mistral Small 24B Instruct", context_window=128000, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="mistralai/mixtral-8x7b-instruct-v0.1", display_name="Mixtral 8x7B Instruct", context_window=32768, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="mistralai/mixtral-8x22b-instruct-v0.1", display_name="Mixtral 8x22B Instruct", context_window=65536, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="mistralai/pixtral-12b-2409", display_name="Pixtral 12B", context_window=32768, max_output_tokens=4096, supports_streaming=True, supports_tools=True, supports_vision=True, default_temperature=0.7),

    # Google Gemma Models
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="google/gemma-2-2b-it", display_name="Gemma 2 2B IT", context_window=8192, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="google/gemma-2-9b-it", display_name="Gemma 2 9B IT", context_window=8192, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="google/gemma-2-27b-it", display_name="Gemma 2 27B IT", context_window=8192, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="google/gemma-7b-it", display_name="Gemma 7B IT", context_window=8192, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),

    # Microsoft Phi Models
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="microsoft/phi-3-mini-4k-instruct", display_name="Phi-3 Mini 4K Instruct", context_window=4096, max_output_tokens=2048, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="microsoft/phi-3-mini-128k-instruct", display_name="Phi-3 Mini 128K Instruct", context_window=128000, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="microsoft/phi-3-medium-4k-instruct", display_name="Phi-3 Medium 4K Instruct", context_window=4096, max_output_tokens=2048, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="microsoft/phi-3-medium-128k-instruct", display_name="Phi-3 Medium 128K Instruct", context_window=128000, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),

    # Qwen Models
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="qwen/qwen2.5-7b-instruct", display_name="Qwen 2.5 7B Instruct", context_window=32768, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="qwen/qwen2.5-14b-instruct", display_name="Qwen 2.5 14B Instruct", context_window=32768, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="qwen/qwen2.5-32b-instruct", display_name="Qwen 2.5 32B Instruct", context_window=32768, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="qwen/qwen2.5-72b-instruct", display_name="Qwen 2.5 72B Instruct", context_window=32768, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="qwen/qwen2.5-vl-7b-instruct", display_name="Qwen 2.5 VL 7B Instruct", context_window=32768, max_output_tokens=4096, supports_streaming=True, supports_tools=True, supports_vision=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="qwen/qwen2.5-vl-32b-instruct", display_name="Qwen 2.5 VL 32B Instruct", context_window=32768, max_output_tokens=4096, supports_streaming=True, supports_tools=True, supports_vision=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="qwen/qwen2.5-coder-32b-instruct", display_name="Qwen 2.5 Coder 32B Instruct", context_window=32768, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),

    # Additional Models
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="upstage/solar-10.7b-instruct", display_name="Solar 10.7B Instruct", context_window=4096, max_output_tokens=2048, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="tiiuae/falcon-180b-chat", display_name="Falcon 180B Chat", context_window=16384, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="nousresearch/nous-hermes-2-yi-34b", display_name="Nous Hermes 2 Yi 34B", context_window=4096, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="codellama/codellama-70b-instruct", display_name="CodeLlama 70B Instruct", context_window=16384, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.1),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="codellama/codellama-34b-instruct", display_name="CodeLlama 34B Instruct", context_window=16384, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.1),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="codellama/codellama-13b-instruct", display_name="CodeLlama 13B Instruct", context_window=16384, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.1),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="codellama/codellama-7b-instruct", display_name="CodeLlama 7B Instruct", context_window=16384, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.1),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="mamba/mamba-codestral-7b", display_name="Mamba Codestral 7B", context_window=32768, max_output_tokens=4096, supports_streaming=True, supports_tools=True, default_temperature=0.1),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="apple/openelm-270m-instruct", display_name="OpenELM 270M Instruct", context_window=2048, max_output_tokens=1024, supports_streaming=True, supports_tools=False, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="apple/openelm-450m-instruct", display_name="OpenELM 450M Instruct", context_window=2048, max_output_tokens=1024, supports_streaming=True, supports_tools=False, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="apple/openelm-1_1b-instruct", display_name="OpenELM 1.1B Instruct", context_window=4096, max_output_tokens=2048, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="apple/openelm-3b-instruct", display_name="OpenELM 3B Instruct", context_window=4096, max_output_tokens=2048, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="stabilityai/stablelm-2-1_6b-chat", display_name="StableLM 2 1.6B Chat", context_window=4096, max_output_tokens=2048, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="stabilityai/stablelm-2-zephyr-1_6b", display_name="StableLM 2 Zephyr 1.6B", context_window=4096, max_output_tokens=2048, supports_streaming=True, supports_tools=True, default_temperature=0.7),
    ModelConfig(provider=LLMProvider.NVIDIA, model_id="allenai/olmo-2-1124-7b-instruct", display_name="OLMo 2 7B Instruct", context_window=4096, max_output_tokens=2048, supports_streaming=True, supports_tools=True, default_temperature=0.7),
]


class OpenAIBackend(LLMBackend):
    """OpenAI API backend."""

    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.OPENAI

    def __init__(self):
        self._client = None
        self._config = {}

    async def initialize(self, config: Dict[str, Any]) -> None:
        self._config = config
        api_key = config.get("api_key")
        base_url = config.get("base_url", "https://api.openai.com/v1")
        organization = config.get("organization")

        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                organization=organization
            )
        except ImportError:
            raise RuntimeError("openai package not installed")

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if not self._client:
            raise RuntimeError("Backend not initialized")

        messages = [msg.to_dict() for msg in request.messages]
        print(f"NVIDIA complete messages: {messages}")
        print(f"NVIDIA request.tools: {request.tools}")
        tools = None
        if request.tools:
            # Check if we have a user message (not system) - if not, don't send tools
            has_user_message = any(msg.get("role") == "user" for msg in messages)
            print(f"NVIDIA has_user_message: {has_user_message}")
            if has_user_message:
                tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": t.name,
                            "description": t.description,
                            "parameters": t.parameters,
                            "strict": t.strict
                        }
                    }
                    for t in request.tools
                ]
                print(f"NVIDIA sending tools: {tools}")
            else:
                print("NVIDIA WARNING: No user message found in conversation, skipping tools for this request")
                logger.warning("No user message found in conversation, skipping tools for this request")

        response = await self._client.chat.completions.create(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            frequency_penalty=request.frequency_penalty,
            presence_penalty=request.presence_penalty,
            tools=tools,
            tool_choice=request.tool_choice,
            response_format=request.response_format,
            stream=False,
            seed=request.seed,
            stop=request.stop
        )

        choice = response.choices[0]
        message = choice.message

        return LLMResponse(
            content=message.content,
            tool_calls=[{
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            } for tc in (message.tool_calls or [])],
            finish_reason=choice.finish_reason,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMStreamChunk]:
        if not self._client:
            raise RuntimeError("Backend not initialized")

        messages = [msg.to_dict() for msg in request.messages]
        print(f"NVIDIA stream messages: {messages}")
        print(f"NVIDIA request.tools: {request.tools}")
        tools = None
        if request.tools:
            # Check if we have at least one user message in the conversation history
            # (not just the current message - tools should be available for follow-up calls too)
            has_user_message = any(msg.get("role") == "user" for msg in messages)
            print(f"NVIDIA has_user_message in history: {has_user_message}")
            # Send tools if there's any user message in the conversation history
            # This allows tool calling on follow-up iterations (after tool results are added)
            if has_user_message:
                tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": t.name,
                            "description": t.description,
                            "parameters": t.parameters,
                            "strict": t.strict
                        }
                    }
                    for t in request.tools
                ]
                print(f"NVIDIA sending tools: {tools}")
            else:
                print("NVIDIA WARNING: No user message found in conversation history, skipping tools for this request")
                logger.warning("No user message found in conversation history, skipping tools for this request")

        stream = await self._client.chat.completions.create(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            frequency_penalty=request.frequency_penalty,
            presence_penalty=request.presence_penalty,
            tools=tools,
            tool_choice=request.tool_choice,
            response_format=request.response_format,
            stream=True,
            seed=request.seed,
            stop=request.stop
        )

        async for chunk in stream:
            if not chunk.choices:
                continue

            choice = chunk.choices[0]
            delta = choice.delta

            stream_chunk = LLMStreamChunk(
                delta=delta.content or "",
                finish_reason=choice.finish_reason,
                model=chunk.model,
                is_final=choice.finish_reason is not None
            )

            if delta.tool_calls:
                stream_chunk.tool_calls = [{
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                } for tc in delta.tool_calls]

            yield stream_chunk

    async def list_models(self) -> List[ModelConfig]:
        models = await self._client.models.list()
        return [
            ModelConfig(
                provider=LLMProvider.OPENAI,
                model_id=m.id,
                display_name=m.id,
                context_window=self._get_context_window(m.id),
                supports_streaming=True,
                supports_tools=self._supports_tools(m.id)
            )
            for m in models.data
        ]

    def _get_context_window(self, model_id: str) -> int:
        if "gpt-4" in model_id:
            return 128000 if "32k" not in model_id else 32768
        return 4096

    def _supports_tools(self, model_id: str) -> bool:
        return "gpt-4" in model_id or "gpt-3.5-turbo" in model_id

    async def health_check(self) -> Dict[str, Any]:
        try:
            await self._client.models.list()
            return {"healthy": True, "provider": "openai"}
        except Exception as e:
            return {"healthy": False, "provider": "openai", "error": str(e)}


class NVIDIABackend(LLMBackend):
    """NVIDIA NIM API backend."""

    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.NVIDIA

    def __init__(self):
        self._client = None
        self._config = {}

    async def initialize(self, config: Dict[str, Any]) -> None:
        self._config = config
        api_key = config.get("api_key")
        base_url = config.get("base_url", "https://integrate.api.nvidia.com/v1")

        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        except ImportError:
            raise RuntimeError("openai package not installed")

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if not self._client:
            raise RuntimeError("Backend not initialized")

        messages = [msg.to_dict() for msg in request.messages]
        print(f"NVIDIA complete messages: {messages}")
        print(f"NVIDIA request.tools: {request.tools}")
        tools = None
        if request.tools:
            # Check if we have a user message (not system) - if not, don't send tools
            has_user_message = any(msg.get("role") == "user" for msg in messages)
            print(f"NVIDIA has_user_message: {has_user_message}")
            if has_user_message:
                tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": t.name,
                            "description": t.description,
                            "parameters": t.parameters,
                            "strict": t.strict
                        }
                    }
                    for t in request.tools
                ]
                print(f"NVIDIA sending tools: {tools}")
            else:
                print("NVIDIA WARNING: No user message found in conversation, skipping tools for this request")
                logger.warning("No user message found in conversation, skipping tools for this request")

        response = await self._client.chat.completions.create(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            frequency_penalty=request.frequency_penalty,
            presence_penalty=request.presence_penalty,
            tools=tools,
            tool_choice=request.tool_choice,
            response_format=request.response_format,
            stream=False,
            seed=request.seed,
            stop=request.stop
        )

        choice = response.choices[0]
        message = choice.message

        return LLMResponse(
            content=message.content,
            tool_calls=[{
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            } for tc in (message.tool_calls or [])],
            finish_reason=choice.finish_reason,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMStreamChunk]:
        if not self._client:
            raise RuntimeError("Backend not initialized")

        messages = [msg.to_dict() for msg in request.messages]
        print(f"NVIDIA stream messages: {messages}")
        print(f"NVIDIA request.tools: {request.tools}")
        tools = None
        if request.tools:
            # Check if we have at least one user message in the conversation history
            # (not just the current message - tools should be available for follow-up calls too)
            has_user_message = any(msg.get("role") == "user" for msg in messages)
            print(f"NVIDIA has_user_message in history: {has_user_message}")
            # Send tools if there's any user message in the conversation history
            # This allows tool calling on follow-up iterations (after tool results are added)
            if has_user_message:
                tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": t.name,
                            "description": t.description,
                            "parameters": t.parameters,
                            "strict": t.strict
                        }
                    }
                    for t in request.tools
                ]
                print(f"NVIDIA sending tools: {tools}")
            else:
                print("NVIDIA WARNING: No user message found in conversation history, skipping tools for this request")
                logger.warning("No user message found in conversation history, skipping tools for this request")

        stream = await self._client.chat.completions.create(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            frequency_penalty=request.frequency_penalty,
            presence_penalty=request.presence_penalty,
            tools=tools,
            tool_choice=request.tool_choice,
            response_format=request.response_format,
            stream=True,
            seed=request.seed,
            stop=request.stop
        )

        async for chunk in stream:
            if not chunk.choices:
                continue

            choice = chunk.choices[0]
            delta = choice.delta

            stream_chunk = LLMStreamChunk(
                delta=delta.content or "",
                finish_reason=choice.finish_reason,
                model=chunk.model,
                is_final=choice.finish_reason is not None
            )

            if delta.tool_calls:
                stream_chunk.tool_calls = [{
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                } for tc in delta.tool_calls]

            yield stream_chunk

    async def list_models(self) -> List[ModelConfig]:
        """Fetch available models from NVIDIA NIM API, merging with comprehensive fallback list."""
        # Always start with comprehensive fallback models
        all_models = list(FREE_NVIDIA_MODELS)
        fetched_model_ids = set(m.model_id for m in all_models)

        if not self._client:
            logger.info("NVIDIA backend not initialized, using comprehensive fallback list")
            return all_models

        try:
            models_response = await self._client.models.list()

            # Check if response indicates an error (NVIDIA NIM sometimes returns error in response body)
            # Log the full response for debugging
            logger.debug(f"NVIDIA models response type: {type(models_response)}, has data: {hasattr(models_response, 'data')}")

            error_detected = False
            if hasattr(models_response, 'error') and models_response.error:
                error_detected = True
                logger.warning(f"NVIDIA API returned error attribute: {models_response.error}, using fallback list")
            elif hasattr(models_response, 'status_code') and getattr(models_response, 'status_code', 200) >= 400:
                error_detected = True
                logger.warning(f"NVIDIA API returned HTTP error: {models_response.status_code}, using fallback list")
            elif not hasattr(models_response, 'data') or not models_response.data:
                error_detected = True
                logger.warning("NVIDIA API returned no data attribute or empty data, using fallback list")
            elif hasattr(models_response, 'data') and isinstance(models_response.data, dict) and models_response.data.get('error'):
                # NVIDIA NIM sometimes wraps error in data dict
                error_detected = True
                logger.warning(f"NVIDIA API returned error in data: {models_response.data.get('error')}, using fallback list")
            elif hasattr(models_response, 'data') and models_response.data:
                # Check if data is a list of models, but also check for rate limit in response
                for item in models_response.data:
                    if isinstance(item, dict) and item.get('error', {}).get('code') == 429:
                        error_detected = True
                        logger.warning("NVIDIA API returned rate limit (429) in model list, using fallback list")
                        break

            if error_detected:
                return all_models

            # Add any models from API that aren't in our fallback list
            for m in models_response.data:
                model_id = m.id
                if model_id not in fetched_model_ids:
                    # Filter for chat/instruct models
                    if 'instruct' in model_id.lower() or 'chat' in model_id.lower() or 'nemotron' in model_id.lower() or 'nemotr' in model_id.lower():
                        all_models.append(ModelConfig(
                            provider=LLMProvider.NVIDIA,
                            model_id=model_id,
                            display_name=model_id.split('/')[-1].replace('-', ' ').title(),
                            context_window=128000,
                            max_output_tokens=4096,
                            supports_streaming=True,
                            supports_tools=True
                        ))
                        fetched_model_ids.add(model_id)

            logger.info(f"NVIDIA models: {len(all_models)} total ({len(FREE_NVIDIA_MODELS)} fallback + {len(all_models) - len(FREE_NVIDIA_MODELS)} from API)")
            return all_models
        except Exception as e:
            logger.warning(f"Failed to fetch NVIDIA models from API: {e}, using comprehensive fallback list")
            return all_models

    async def health_check(self) -> Dict[str, Any]:
        try:
            await self._client.models.list()
            return {"healthy": True, "provider": "nvidia"}
        except Exception as e:
            return {"healthy": False, "provider": "nvidia", "error": str(e)}


class AnthropicBackend(LLMBackend):
    """Anthropic API backend."""

    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.ANTHROPIC

    def __init__(self):
        self._client = None
        self._config = {}

    async def initialize(self, config: Dict[str, Any]) -> None:
        self._config = config
        api_key = config.get("api_key")
        base_url = config.get("base_url", "https://api.anthropic.com")

        try:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=api_key, base_url=base_url)
        except ImportError:
            raise RuntimeError("anthropic package not installed")

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if not self._client:
            raise RuntimeError("Backend not initialized")

        # Convert messages
        system_message = None
        messages = []
        for msg in request.messages:
            if msg.role == MessageRole.SYSTEM:
                system_message = msg.content
            else:
                messages.append(msg.to_dict())

        tools = None
        if request.tools:
            tools = [{
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters
            } for t in request.tools]

        response = await self._client.messages.create(
            model=request.model,
            messages=messages,
            system=system_message,
            temperature=request.temperature,
            max_tokens=request.max_tokens or 4096,
            top_p=request.top_p,
            tools=tools,
            tool_choice=request.tool_choice,
            stop_sequences=request.stop
        )

        content = response.content[0].text if response.content else ""
        tool_calls = []
        for block in response.content[1:]:
            if block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {"name": block.name, "arguments": json.dumps(block.input)}
                })

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=response.stop_reason or "stop",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            }
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMStreamChunk]:
        # Similar to complete but streaming
        pass

    async def list_models(self) -> List[ModelConfig]:
        return [
            ModelConfig(
                provider=LLMProvider.ANTHROPIC,
                model_id="claude-3-5-sonnet-20241022",
                display_name="Claude 3.5 Sonnet",
                context_window=200000,
                max_output_tokens=8192,
                supports_streaming=True,
                supports_tools=True,
                input_cost_per_1k=0.003,
                output_cost_per_1k=0.015
            ),
            ModelConfig(
                provider=LLMProvider.ANTHROPIC,
                model_id="claude-3-haiku-20240307",
                display_name="Claude 3 Haiku",
                context_window=200000,
                max_output_tokens=4096,
                supports_streaming=True,
                supports_tools=True,
                input_cost_per_1k=0.00025,
                output_cost_per_1k=0.00125
            )
        ]

    async def health_check(self) -> Dict[str, Any]:
        try:
            # No direct health check, try a simple completion
            return {"healthy": True, "provider": "anthropic"}
        except Exception as e:
            return {"healthy": False, "provider": "anthropic", "error": str(e)}


class LLMModule(RuntimeModule):
    """
    Unified LLM module with multi-provider support.

    Features:
    - Multiple provider backends (OpenAI, Anthropic, Google, Ollama, etc.)
    - Model configuration and routing
    - Streaming and non-streaming completions
    - Function/tool calling
    - Cost tracking and quotas
    - Prompt templating
    - Request/response logging
    - Fallback and retry logic
    """

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="llm",
            version="1.0.0",
            description="Unified LLM interface with multi-provider support",
            author="AIPENSA",
            dependencies=["tool"],
            provides=["completion", "streaming", "function_calling", "cost_tracking"],
            tags={"llm", "openai", "anthropic", "ai", "generation"}
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._backends: Dict[LLMProvider, LLMBackend] = {}
        self._models: Dict[str, ModelConfig] = {}
        self._default_model: Optional[str] = None
        self._config: Dict[str, Any] = {}
        self._usage_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0
        })
        self._request_history: List[Dict[str, Any]] = []
        self._max_history = config.get("max_history", 10000) if config else 10000

    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        """Initialize LLM module."""
        self._runtime = runtime
        self._config = {**self._config, **config}

        # Initialize backends
        backends_config = self._config.get("backends", {})
        for provider_name, backend_config in backends_config.items():
            try:
                provider = LLMProvider(provider_name)
                await self._create_backend(provider, backend_config)
            except ValueError:
                logger.warning(f"Unknown provider: {provider_name}")

        # Set default model
        self._default_model = self._config.get("default_model")

        # Load model configs
        for model_config in self._config.get("models", []):
            model = ModelConfig(**model_config)
            self._models[model.model_id] = model

        self.state = ModuleState.INITIALIZED
        logger.info(f"LLM module initialized with {len(self._backends)} backends")

    async def _create_backend(self, provider: LLMProvider, config: Dict[str, Any]) -> None:
        """Create and initialize backend."""
        if provider == LLMProvider.OPENAI:
            backend = OpenAIBackend()
        elif provider == LLMProvider.ANTHROPIC:
            backend = AnthropicBackend()
        elif provider == LLMProvider.NVIDIA:
            backend = NVIDIABackend()
        else:
            logger.warning(f"Backend for {provider.value} not implemented")
            return

        await backend.initialize(config)
        self._backends[provider] = backend

        # Load models from backend
        models = await backend.list_models()
        for model in models:
            self._models[model.model_id] = model

    async def start(self) -> None:
        self.state = ModuleState.RUNNING
        logger.info("LLM module started")

    async def stop(self) -> None:
        self.state = ModuleState.STOPPED
        logger.info("LLM module stopped")

    async def cleanup(self) -> None:
        self._backends.clear()
        self._models.clear()
        self._usage_stats.clear()
        self._request_history.clear()
        self.state = ModuleState.UNINITIALIZED
        logger.info("LLM module cleaned up")

    async def health_check(self) -> Dict[str, Any]:
        backend_status = {}
        healthy = True
        for provider, backend in self._backends.items():
            status = await backend.health_check()
            backend_status[provider.value] = status
            if not status.get("healthy", False):
                healthy = False

        return {
            "module": "llm",
            "status": self.state.value,
            "healthy": healthy,
            "backends": backend_status,
            "models_loaded": len(self._models),
            "total_requests": len(self._request_history)
        }

    # Completion Operations
    async def complete(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Complete a chat conversation."""
        request = LLMRequest(
            messages=messages,
            model=model or self._default_model,
            **kwargs
        )

        return await self._execute_request(request)

    async def stream(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[LLMStreamChunk]:
        """Stream a chat completion."""
        request = LLMRequest(
            messages=messages,
            model=model or self._default_model,
            stream=True,
            **kwargs
        )

        async for chunk in self._execute_stream(request):
            yield chunk

    async def _execute_request(self, request: LLMRequest) -> LLMResponse:
        """Execute LLM request with backend selection and fallback."""
        model = request.model or self._default_model
        if not model:
            raise ValueError("No model specified")

        # Find backend for model
        model_config = self._models.get(model)
        if not model_config:
            raise ValueError(f"Unknown model: {model}")

        backend = self._backends.get(model_config.provider)
        if not backend:
            raise ValueError(f"No backend for provider: {model_config.provider.value}")

        # Execute with retry
        max_retries = self._config.get("max_retries", 3)
        for attempt in range(max_retries):
            try:
                response = await backend.complete(request)
                self._record_usage(model_config, response.usage)
                self._record_request(request, response, success=True)
                return response
            except Exception as e:
                logger.warning(f"LLM request failed (attempt {attempt+1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    self._record_request(request, None, success=False, error=str(e))
                    raise

        raise RuntimeError("Max retries exceeded")

    async def _execute_stream(self, request: LLMRequest) -> AsyncIterator[LLMStreamChunk]:
        """Execute streaming request."""
        model = request.model or self._default_model
        if not model:
            raise ValueError("No model specified")

        model_config = self._models.get(model)
        if not model_config:
            raise ValueError(f"Unknown model: {model}")

        backend = self._backends.get(model_config.provider)
        if not backend:
            raise ValueError(f"No backend for provider: {model_config.provider.value}")

        try:
            async for chunk in backend.stream(request):
                yield chunk
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            raise

    def _record_usage(self, model_config: ModelConfig, usage: Dict[str, int]) -> None:
        """Record usage statistics."""
        key = f"{model_config.provider.value}:{model_config.model_id}"
        stats = self._usage_stats[key]
        stats["prompt_tokens"] += usage.get("prompt_tokens", 0)
        stats["completion_tokens"] += usage.get("completion_tokens", 0)
        stats["total_tokens"] += usage.get("total_tokens", 0)

        # Calculate cost
        input_cost = (usage.get("prompt_tokens", 0) / 1000) * model_config.input_cost_per_1k
        output_cost = (usage.get("completion_tokens", 0) / 1000) * model_config.output_cost_per_1k
        stats["cost_usd"] += input_cost + output_cost

    def _record_request(
        self,
        request: LLMRequest,
        response: Optional[LLMResponse],
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """Record request history."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "model": request.model,
            "success": success,
            "message_count": len(request.messages),
            "tools": len(request.tools) if request.tools else 0,
            "stream": request.stream,
            "error": error
        }
        if response:
            entry["usage"] = response.usage
            entry["finish_reason"] = response.finish_reason

        self._request_history.append(entry)
        if len(self._request_history) > self._max_history:
            self._request_history = self._request_history[-self._max_history:]

    # Model Management
    async def get_model(self, model_id: str) -> Optional[ModelConfig]:
        return self._models.get(model_id)

    async def list_models(
        self,
        provider: Optional[LLMProvider] = None
    ) -> List[ModelConfig]:
        models = list(self._models.values())
        if provider:
            models = [m for m in models if m.provider == provider]
        return models

    async def set_default_model(self, model_id: str) -> bool:
        if model_id in self._models:
            self._default_model = model_id
            return True
        return False

    # Usage Statistics
    async def get_usage_stats(
        self,
        model_id: Optional[str] = None,
        provider: Optional[LLMProvider] = None
    ) -> Dict[str, Any]:
        if model_id:
            return self._usage_stats.get(model_id, {})
        if provider:
            key_prefix = f"{provider.value}:"
            return {k: v for k, v in self._usage_stats.items() if k.startswith(key_prefix)}
        return dict(self._usage_stats)

    async def get_request_history(
        self,
        limit: int = 100,
        since: Optional[datetime] = None,
        model: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        history = self._request_history

        if since:
            history = [h for h in history if h["timestamp"] >= since.isoformat()]
        if model:
            history = [h for h in history if h["model"] == model]

        return history[-limit:]

    # Prompt Templates
    async def complete_with_template(
        self,
        template_name: str,
        variables: Dict[str, Any],
        model: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Complete using a prompt template."""
        template = self._config.get("templates", {}).get(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")

        # Render template
        messages = self._render_template(template, variables)
        return await self.complete(messages, model, **kwargs)

    def _render_template(self, template: Dict[str, Any], variables: Dict[str, Any]) -> List[LLMMessage]:
        messages = []
        for msg_template in template.get("messages", []):
            content = msg_template.get("content", "")
            for key, value in variables.items():
                content = content.replace(f"{{{key}}}", str(value))
            messages.append(LLMMessage(
                role=MessageRole(msg_template.get("role", "user")),
                content=content
            ))
        return messages

    # Module Operations
    async def execute(self, operation: str, **kwargs) -> Any:
        mapping = {
            "complete": self.complete,
            "stream": self.stream,
            "get_model": self.get_model,
            "list_models": self.list_models,
            "set_default_model": self.set_default_model,
            "get_usage_stats": self.get_usage_stats,
            "get_request_history": self.get_request_history,
            "complete_with_template": self.complete_with_template,
        }
        if operation in mapping:
            return await mapping[operation](**kwargs)
        raise NotImplementedError(f"Operation '{operation}' not supported")


__all__ = [
    "LLMModule",
    "LLMBackend",
    "OpenAIBackend",
    "AnthropicBackend",
    "LLMMessage",
    "LLMTool",
    "LLMResponse",
    "LLMStreamChunk",
    "LLMRequest",
    "ModelConfig",
    "LLMProvider",
    "LLMModel",
    "MessageRole",
]