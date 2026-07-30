"""
NVIDIA NIM LLM Provider Plugin

Provides access to NVIDIA NIM inference models via OpenAI-compatible API.
"""

from typing import Any, Dict, List, Optional, AsyncGenerator
import logging

from runtime.plugins.base import Plugin, PluginMetadata, PluginType
from runtime.llm.base import ModelConfig, LLMRequest, LLMResponse, LLMStreamChunk

logger = logging.getLogger(__name__)


class NvidiaNIMPlugin(Plugin):
    """NVIDIA NIM LLM Provider Plugin."""

    metadata = PluginMetadata(
        name="nvidia_nim",
        version="2.1.0",
        description="NVIDIA NIM LLM Provider Plugin",
        author="aipensa",
        plugin_type=PluginType.LLM,
        provides=["chat_completion", "completion", "streaming", "function_calling"],
        dependencies=["network:httpx", "runtime:conversation", "skill:llm_generation"],
        tags={"llm", "nvidia", "nim", "inference"},
        entry_point="nvidia_nim.py",
        config_schema={
            "type": "object",
            "properties": {
                "api_key": {"type": "string", "format": "password", "description": "NVIDIA API Key"},
                "base_url": {"type": "string", "format": "uri", "default": "https://integrate.api.nvidia.com/v1"},
                "organization": {"type": "string", "description": "Organization ID"},
                "default_model": {"type": "string", "default": "meta/llama-3.1-70b-instruct"},
                "timeout_seconds": {"type": "integer", "minimum": 10, "maximum": 300, "default": 120},
                "max_retries": {"type": "integer", "minimum": 0, "maximum": 10, "default": 3}
            },
            "required": ["api_key"]
        }
    )

    SUPPORTED_MODELS = [
        "meta/llama-3.1-405b-instruct",
        "meta/llama-3.1-70b-instruct",
        "meta/llama-3.1-8b-instruct",
        "meta/llama-3.2-90b-vision-instruct",
        "meta/llama-3.2-11b-vision-instruct",
        "nvidia/nemotron-3-ultra",
        "nvidia/nemotron-4-340b-instruct",
        "mistralai/mistral-7b-instruct-v0.3",
        "mistralai/mixtral-8x7b-instruct-v0.1",
        "google/gemma-2-27b-it",
        "google/gemma-2-9b-it",
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_key = config.get("api_key") if config else None
        self.base_url = config.get("base_url", "https://integrate.api.nvidia.com/v1") if config else "https://integrate.api.nvidia.com/v1"
        self.organization = config.get("organization") if config else None
        self.default_model = config.get("default_model", "meta/llama-3.1-70b-instruct") if config else "meta/llama-3.1-70b-instruct"
        self.timeout = config.get("timeout_seconds", 120) if config else 120
        self.max_retries = config.get("max_retries", 3) if config else 3
        self._client = None

    async def initialize(self, runtime: Any) -> None:
        """Initialize the plugin with runtime reference."""
        self.runtime = runtime
        await self._initialize_client()
        logger.info("NvidiaNIMPlugin initialized")

    async def _initialize_client(self) -> None:
        """Initialize the OpenAI-compatible client."""
        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                organization=self.organization,
                timeout=self.timeout,
                max_retries=self.max_retries,
            )
        except ImportError:
            logger.error("openai package not installed. Run: pip install openai>=1.0.0")
            raise

    async def start(self) -> None:
        """Start the plugin."""
        logger.info("NvidiaNIMPlugin started")

    async def stop(self) -> None:
        """Stop the plugin."""
        if self._client:
            await self._client.close()
        logger.info("NvidiaNIMPlugin stopped")

    async def cleanup(self) -> None:
        """Clean up resources."""
        await self.stop()
        logger.info("NvidiaNIMPlugin cleaned up")

    def get_supported_models(self) -> List[ModelConfig]:
        """Get list of supported models with their configs."""
        return [
            ModelConfig(
                model_id=model,
                provider="nvidia_nim",
                capabilities=["chat", "completion", "streaming", "function_calling", "vision"] if "vision" in model else ["chat", "completion", "streaming", "function_calling"],
                context_window=128000 if "llama-3.1" in model or "llama-3.2" in model else 8192,
                max_output_tokens=4096,
                cost_per_1k_input=0.0,  # NIM is typically free tier or internal
                cost_per_1k_output=0.0,
            )
            for model in self.SUPPORTED_MODELS
        ]

    async def chat_completion(self, request: LLMRequest) -> LLMResponse:
        """Execute chat completion."""
        if not self._client:
            await self._initialize_client()

        model = request.model or self.default_model

        # Convert messages to OpenAI format
        messages = []
        for msg in request.messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # Prepare request
        completion_args = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature or 0.7,
            "max_tokens": request.max_tokens or 2048,
            "top_p": request.top_p or 1.0,
            "stream": False,
        }

        if request.tools:
            completion_args["tools"] = self._convert_tools(request.tools)
            if request.tool_choice:
                completion_args["tool_choice"] = request.tool_choice

        try:
            response = await self._client.chat.completions.create(**completion_args)

            return LLMResponse(
                id=response.id,
                model=response.model,
                content=response.choices[0].message.content or "",
                role="assistant",
                tool_calls=self._convert_tool_calls(response.choices[0].message.tool_calls) if response.choices[0].message.tool_calls else None,
                finish_reason=response.choices[0].finish_reason,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                }
            )
        except Exception as e:
            logger.error(f"Chat completion failed: {e}")
            raise

    async def stream_chat_completion(self, request: LLMRequest) -> AsyncGenerator[LLMStreamChunk, None]:
        """Execute streaming chat completion."""
        if not self._client:
            await self._initialize_client()

        model = request.model or self.default_model

        messages = []
        for msg in request.messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        completion_args = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature or 0.7,
            "max_tokens": request.max_tokens or 2048,
            "top_p": request.top_p or 1.0,
            "stream": True,
        }

        if request.tools:
            completion_args["tools"] = self._convert_tools(request.tools)
            if request.tool_choice:
                completion_args["tool_choice"] = request.tool_choice

        try:
            stream = await self._client.chat.completions.create(**completion_args)
            async for chunk in stream:
                if chunk.choices:
                    choice = chunk.choices[0]
                    yield LLMStreamChunk(
                        id=chunk.id,
                        model=chunk.model,
                        content=choice.delta.content or "",
                        role="assistant",
                        tool_calls=self._convert_tool_calls(choice.delta.tool_calls) if choice.delta.tool_calls else None,
                        finish_reason=choice.finish_reason,
                    )
        except Exception as e:
            logger.error(f"Streaming chat completion failed: {e}")
            raise

    def _convert_tools(self, tools: List[Dict]) -> List[Dict]:
        """Convert tool definitions to OpenAI format."""
        openai_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["function"]["name"],
                        "description": tool["function"]["description"],
                        "parameters": tool["function"]["parameters"]
                    }
                })
        return openai_tools

    def _convert_tool_calls(self, tool_calls) -> List[Dict]:
        """Convert OpenAI tool calls to our format."""
        if not tool_calls:
            return []
        return [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            }
            for tc in tool_calls
        ]


__all__ = ["NvidiaNIMPlugin"]