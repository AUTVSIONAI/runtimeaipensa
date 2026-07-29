"""
Runtime Configuration for AIPENSA Runtime

Defines the configuration schema for the runtime and all its modules.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pathlib import Path
import tomllib
import os


class RuntimeType(Enum):
    """Runtime execution mode."""
    LOCAL = "local"
    CLOUD = "cloud"
    HYBRID = "hybrid"
    DOCKER = "docker"
    SERVERLESS = "serverless"


class BrowserBackend(Enum):
    """Supported browser backends."""
    PLAYWRIGHT = "playwright"
    SELENIUM = "selenium"
    PUPPETEER = "puppeteer"
    BROWSERLESS = "browserless"
    DAYTONA = "daytona"


class SandboxBackend(Enum):
    """Supported sandbox backends."""
    LOCAL = "local"
    DOCKER = "docker"
    DAYTONA = "daytona"
    FIRECRACKER = "firecracker"
    G_VISOR = "gvisor"


class MemoryBackend(Enum):
    """Supported memory/storage backends."""
    IN_MEMORY = "in_memory"
    REDIS = "redis"
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"
    CHROMA = "chroma"
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"


class LLMBackend(Enum):
    """Supported LLM backends."""
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    VLLM = "vllm"
    TOGETHER = "together"
    GROQ = "groq"
    HUGGINGFACE = "huggingface"
    BEDROCK = "bedrock"
    VERTEX = "vertex"
    CUSTOM = "custom"


class LogLevel(Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class BrowserConfig:
    """Browser runtime configuration."""
    runtime: str = "local"
    headless: bool = False
    chrome_path: str = ""
    wss_url: str = ""
    cdp_url: str = ""
    disable_security: bool = True
    extra_args: List[str] = field(default_factory=lambda: ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"])
    proxy_server: str = ""
    proxy_username: str = ""
    proxy_password: str = ""
    viewport_width: int = 1280
    viewport_height: int = 720
    new_context_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SandboxConfig:
    """Sandbox execution configuration."""
    runtime: str = "local"
    work_dir: str = "workspace"
    timeout: int = 300
    memory_limit: str = "2g"
    cpu_limit: str = "2"
    network_mode: str = "bridge"
    env: Dict[str, str] = field(default_factory=dict)
    docker_url: str = "unix:///var/run/docker.sock"


@dataclass
class MemoryConfig:
    """Memory/Storage configuration."""
    backend: str = "local"
    path: str = "runtime/memory"
    max_entries: int = 10000
    default_ttl_seconds: int = 86400


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    model: str = "gpt-4"
    temperature: float = 0.1
    max_tokens: int = 8192
    timeout: int = 60
    api_key: str = ""
    base_url: str = "https://integrate.api.nvidia.com/v1"


@dataclass
class MCPConfig:
    """MCP (Model Context Protocol) configuration."""
    enabled: bool = True
    servers: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class PluginConfig:
    """Plugin system configuration."""
    enabled: bool = True
    plugin_dirs: List[str] = field(default_factory=lambda: ["plugins", "runtime/plugins"])
    auto_discover: bool = True


@dataclass
class EventsConfig:
    """Event bus configuration."""
    enabled: bool = True
    async_handlers: bool = True
    max_history: int = 10000


@dataclass
class TelemetryConfig:
    """Telemetry configuration."""
    enabled: bool = True
    metrics_interval: int = 60
    trace_sampling: float = 0.1


@dataclass
class SecurityConfig:
    """Security configuration."""
    sandbox_enabled: bool = True
    allowed_commands: List[str] = field(default_factory=list)
    blocked_commands: List[str] = field(default_factory=lambda: ["rm -rf /", "sudo", "chmod 777"])
    max_execution_time: int = 300
    max_memory_mb: int = 1024
    network_allowed: bool = True
    file_system_allowed: bool = True


@dataclass
class ModuleConfig:
    """Module configuration."""
    name: str
    enabled: bool = True
    required: bool = False
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuntimeConfig:
    """Main runtime configuration."""
    # Runtime identity
    runtime_type: RuntimeType = RuntimeType.LOCAL
    name: str = "aipensa-runtime"
    version: str = "1.0.0"
    workspace: str = "workspace"

    # Logging
    log_level: LogLevel = LogLevel.INFO

    # Module configs
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    plugins: PluginConfig = field(default_factory=PluginConfig)
    events: EventsConfig = field(default_factory=EventsConfig)
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)

    # Module list
    modules: List[ModuleConfig] = field(default_factory=list)

    # Plugin configs
    plugin_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Feature flags
    features: Dict[str, bool] = field(default_factory=lambda: {
        "browser": True,
        "sandbox": True,
        "mcp": True,
        "planning": True,
        "memory": True,
        "telemetry": True,
        "hot_reload": False,
    })

    # Resource limits
    max_concurrent_tasks: int = 10
    max_memory_mb: int = 4096
    max_cpu_percent: float = 80.0
    task_timeout_seconds: int = 3600

    @classmethod
    def from_toml(cls, path: Path) -> "RuntimeConfig":
        """Load configuration from TOML file."""
        with open(path, "rb") as f:
            data = tomllib.load(f)
        # Expand environment variables
        data = cls._expand_env_vars(data)
        return cls.from_dict(data)

    @staticmethod
    def _expand_env_vars(data: Any) -> Any:
        """Recursively expand environment variables in configuration."""
        if isinstance(data, dict):
            return {k: RuntimeConfig._expand_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [RuntimeConfig._expand_env_vars(item) for item in data]
        elif isinstance(data, str) and data.startswith("${") and data.endswith("}"):
            # Expand ${VAR_NAME} syntax
            var_name = data[2:-1]
            return os.environ.get(var_name, data)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuntimeConfig":
        """Create config from dictionary."""
        config = cls()

        # Simple fields
        for key in ["runtime_type", "name", "version", "workspace", "log_level"]:
            if key in data:
                val = data[key]
                if key == "runtime_type":
                    config.runtime_type = RuntimeType(val)
                elif key == "log_level":
                    config.log_level = LogLevel(val)
                else:
                    setattr(config, key, val)

        # Config sections
        section_map = {
            "browser": BrowserConfig,
            "sandbox": SandboxConfig,
            "memory": MemoryConfig,
            "llm": LLMConfig,
            "mcp": MCPConfig,
            "events": EventsConfig,
            "telemetry": TelemetryConfig,
            "security": SecurityConfig,
        }

        # Handle nested runtime section
        runtime_data = data.get("runtime", {})
        main_data = {k: v for k, v in data.items() if k != "runtime"}
        main_data.update(runtime_data)

        for section, cls_type in section_map.items():
            if section in main_data:
                section_data = main_data[section].copy()  # Make a copy to avoid modifying original
                # Handle special browser context_config
                if section == "browser" and "context_config" in section_data:
                    context = section_data.pop("context_config")
                    section_data["new_context_config"] = context

                # Handle proxy in browser
                if section == "browser" and "proxy" in section_data:
                    proxy = section_data.pop("proxy")
                    section_data["proxy_server"] = proxy.get("server", "")
                    section_data["proxy_username"] = proxy.get("username", "")
                    section_data["proxy_password"] = proxy.get("password", "")

                # Handle special LLM default_model -> model
                if section == "llm" and "default_model" in section_data:
                    section_data["model"] = section_data.pop("default_model")

                # Handle special LLM models section
                if section == "llm" and "models" in section_data:
                    section_data.pop("models")  # Ignore models section for now

                setattr(config, section, cls_type(**section_data))

        # Handle plugins section specially (dict of plugin configs, not PluginConfig)
        if "plugins" in main_data:
            plugins_data = main_data["plugins"]
            # Handle both array of tables [[runtime.plugins]] and dict format
            if isinstance(plugins_data, list):
                # Convert array of tables to dict keyed by id
                config.plugin_configs = {}
                for plugin in plugins_data:
                    if isinstance(plugin, dict) and "id" in plugin:
                        plugin_id = plugin.pop("id")
                        config.plugin_configs[plugin_id] = plugin
            elif isinstance(plugins_data, dict):
                config.plugin_configs = plugins_data

        # Handle nested module structure under runtime.modules
        all_modules = []
        if "modules" in main_data and isinstance(main_data["modules"], list):
            # Flat list format: modules = [{...}, {...}]
            for mod in main_data["modules"]:
                if isinstance(mod, dict):
                    all_modules.append(ModuleConfig(**mod))
        elif "runtime" in data and "modules" in data["runtime"]:
            # Nested format: runtime.modules.browser = [...]
            runtime_modules = data["runtime"]["modules"]
            if isinstance(runtime_modules, dict):
                for module_type, modules in runtime_modules.items():
                    if isinstance(modules, list):
                        for mod in modules:
                            if isinstance(mod, dict):
                                all_modules.append(ModuleConfig(**mod))

        config.modules = all_modules

        # Features
        if "features" in main_data:
            config.features.update(main_data["features"])

        return config

    def get_module_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get module configurations as dict."""
        result = {}
        for mod in self.modules:
            result[mod.name] = {
                "enabled": mod.enabled,
                "required": mod.required,
                "config": mod.config,
            }
        return result


def get_development_config() -> RuntimeConfig:
    """Get development configuration."""
    config = RuntimeConfig()
    config.log_level = LogLevel.DEBUG
    config.browser.headless = False
    config.debug = True

    # Enable all core modules
    config.modules = [
        ModuleConfig(name="browser", enabled=True, required=True, config={}),
        ModuleConfig(name="execution", enabled=True, required=True, config={}),
        ModuleConfig(name="tools", enabled=True, required=True, config={}),
        ModuleConfig(name="memory", enabled=True, required=True, config={}),
        ModuleConfig(name="planning", enabled=True, required=False, config={}),
        ModuleConfig(name="mcp", enabled=True, required=False, config={}),
        ModuleConfig(name="filesystem", enabled=True, required=True, config={}),
        ModuleConfig(name="network", enabled=True, required=True, config={}),
        ModuleConfig(name="docker", enabled=False, required=False, config={}),
        ModuleConfig(name="llm", enabled=True, required=True, config={}),
        ModuleConfig(name="conversation", enabled=True, required=True, config={}),
        ModuleConfig(name="agent", enabled=True, required=True, config={}),
        ModuleConfig(name="workflow", enabled=True, required=False, config={}),
        ModuleConfig(name="scheduler", enabled=True, required=False, config={}),
        ModuleConfig(name="queue", enabled=True, required=False, config={}),
        ModuleConfig(name="notification", enabled=True, required=False, config={}),
        ModuleConfig(name="storage", enabled=True, required=False, config={}),
        ModuleConfig(name="authentication", enabled=True, required=False, config={}),
        ModuleConfig(name="workspace", enabled=True, required=False, config={}),
        ModuleConfig(name="voice", enabled=False, required=False, config={}),
        ModuleConfig(name="vision", enabled=False, required=False, config={}),
        ModuleConfig(name="video", enabled=False, required=False, config={}),
        ModuleConfig(name="image", enabled=False, required=False, config={}),
        ModuleConfig(name="embedding", enabled=False, required=False, config={}),
        ModuleConfig(name="rag", enabled=False, required=False, config={}),
        ModuleConfig(name="reasoning", enabled=False, required=False, config={}),
        # Extensions Layer (NEW - compose on top of kernel)
        ModuleConfig(name="company_context", enabled=True, required=False, config={}),
        ModuleConfig(name="employee", enabled=True, required=False, config={}),
        ModuleConfig(name="team", enabled=True, required=False, config={}),
        ModuleConfig(name="provider", enabled=True, required=False, config={}),
        ModuleConfig(name="onboarding", enabled=True, required=False, config={}),
        ModuleConfig(name="explorer", enabled=True, required=False, config={}),
        ModuleConfig(name="sync", enabled=True, required=False, config={}),
    ]
    return config


def get_production_config() -> RuntimeConfig:
    """Get production configuration."""
    config = RuntimeConfig()
    config.log_level = LogLevel.INFO
    config.browser.headless = True
    config.debug = False
    return config


__all__ = [
    "RuntimeConfig",
    "RuntimeType",
    "BrowserBackend",
    "SandboxBackend",
    "MemoryBackend",
    "LLMBackend",
    "LogLevel",
    "BrowserConfig",
    "SandboxConfig",
    "MemoryConfig",
    "LLMConfig",
    "MCPConfig",
    "PluginConfig",
    "EventsConfig",
    "TelemetryConfig",
    "SecurityConfig",
    "ModuleConfig",
    "get_development_config",
    "get_production_config",
]