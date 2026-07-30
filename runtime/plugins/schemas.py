"""
Plugin Manifest Schema - Pydantic models for plugin.yaml validation
"""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from pydantic import BaseModel, Field, field_validator
from pydantic import ConfigDict


class PluginType(str, Enum):
    """Types of plugins supported by the runtime."""
    TOOL = "tool"
    MCP = "mcp"
    BROWSER = "browser"
    RUNTIME = "runtime"
    SANDBOX = "sandbox"
    MEMORY = "memory"
    LLM = "llm"
    AUTH = "auth"
    STORAGE = "storage"
    NETWORK = "network"
    CUSTOM = "custom"


class DependencyType(str, Enum):
    """Types of dependencies a plugin can have."""
    PLUGIN = "plugin"      # plugin_type:plugin_name
    MODULE = "module"      # runtime:module_name
    SKILL = "skill"        # skill:skill_name
    PYTHON_PACKAGE = "python_package"  # pip package name


class ConfigProperty(BaseModel):
    """JSON Schema property for plugin config."""
    type: str
    title: Optional[str] = None
    description: Optional[str] = None
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
    format: Optional[str] = None  # password, uri, etc.
    properties: Optional[Dict[str, "ConfigProperty"]] = None
    required: Optional[List[str]] = None
    items: Optional["ConfigProperty"] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None


class ConfigSchema(BaseModel):
    """Plugin configuration schema (JSON Schema Draft 2020-12 subset)."""
    type: str = "object"
    properties: Dict[str, ConfigProperty] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)
    additional_properties: bool = Field(default=True, alias="additionalProperties")


class PluginDependency(BaseModel):
    """Plugin dependency specification."""
    type: DependencyType = DependencyType.PLUGIN
    name: str  # e.g., "tool:web_search" or "runtime:conversation" or "skill:llm_generation"
    version: Optional[str] = None  # SemVer constraint like ">=1.0.0,<2.0.0"
    optional: bool = False

    @property
    def plugin_type(self) -> Optional[str]:
        """Extract plugin type from name if format is type:name."""
        if ":" in self.name:
            return self.name.split(":")[0]
        return None

    @property
    def plugin_name(self) -> str:
        """Extract plugin name from name if format is type:name."""
        if ":" in self.name:
            return self.name.split(":", 1)[1]
        return self.name

    @property
    def full_spec(self) -> str:
        """Return the full dependency specification string."""
        if self.version:
            return f"{self.name}@{self.version}"
        return self.name


class PluginManifest(BaseModel):
    """
    Complete plugin manifest schema matching ENGINE_PLUGIN_GUIDE.md specification.

    This is the plugin.yaml file that MUST exist in every plugin directory.
    """
    # Core identification (required)
    name: str = Field(..., description="Unique plugin name, snake_case, max 64 chars",
                      min_length=1, max_length=64, pattern=r'^[a-z][a-z0-9_]*$')
    version: str = Field(..., description="Semantic version (SemVer)", pattern=r'^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$')
    type: PluginType
    class_name: str = Field(..., description="Main plugin class name")
    entry_point: str = Field(..., description="Python file containing the class (relative to plugin root)")
    description: str = Field(..., min_length=10, max_length=500)
    author: str = Field(default="", max_length=100)
    license: str = Field(default="MIT", max_length=50)
    homepage: Optional[str] = Field(default=None, pattern=r'^https?://')
    repository: Optional[str] = Field(default=None, pattern=r'^https?://')
    tags: List[str] = Field(default_factory=list)

    # Dependencies - can be string format "type:name" or full object
    dependencies: List[Union[str, PluginDependency]] = Field(default_factory=list)

    # Capabilities provided by this plugin
    capabilities: List[str] = Field(default_factory=list)

    # Configuration schema (JSON Schema Draft 2020-12)
    config_schema: Optional[ConfigSchema] = Field(default=None, alias="config_schema")

    # Runtime compatibility
    min_runtime_version: str = Field(default="1.0.0", alias="min_runtime_version")
    max_runtime_version: Optional[str] = Field(default=None, alias="max_runtime_version")

    # Python requirements
    python_requires: str = Field(default=">=3.10", alias="python_requires")
    install_requires: List[str] = Field(default_factory=list, alias="install_requires")

    # Entry points for CLI/commands (optional)
    entry_points: Dict[str, str] = Field(default_factory=dict, alias="entry_points")

    # Optional: Health check configuration
    health_check: Optional[Dict[str, Any]] = Field(default=None)

    # Optional: Marketplace metadata
    marketplace: Optional[Dict[str, Any]] = Field(default=None)

    # Optional: Permissions required
    permissions_required: List[str] = Field(default_factory=list, alias="permissions_required")

    # Optional: Rate limits
    rate_limits: Optional[Dict[str, Any]] = Field(default=None, alias="rate_limits")

    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",  # Allow extra fields for extensibility
        validate_assignment=True
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.replace('_', '').isalnum():
            raise ValueError("Plugin name must be alphanumeric with underscores only")
        if v.startswith('_') or v.endswith('_'):
            raise ValueError("Plugin name cannot start or end with underscore")
        return v

    @field_validator('version')
    @classmethod
    def validate_version(cls, v: str) -> str:
        parts = v.split('.')
        if len(parts) < 3:
            raise ValueError("Version must be at least major.minor.patch")
        for part in parts[:3]:
            if not part.isdigit():
                raise ValueError("Version parts must be numeric")
        return v

    @field_validator('dependencies', mode='before')
    @classmethod
    def parse_dependencies(cls, v: Any) -> List[PluginDependency]:
        """Parse dependency strings into PluginDependency objects."""
        if not v:
            return []

        result = []
        for dep in v:
            if isinstance(dep, str):
                # Parse "plugin_type:plugin_name" or "plugin_type:plugin_name@version"
                parts = dep.split('@')
                dep_spec = parts[0]
                version = parts[1] if len(parts) > 1 else None

                if ':' in dep_spec:
                    dep_type_str, dep_name = dep_spec.split(':', 1)
                    try:
                        dep_type = DependencyType(dep_type_str)
                    except ValueError:
                        # Unknown type, treat as plugin
                        dep_type = DependencyType.PLUGIN
                        dep_name = dep_spec
                else:
                    # Just name without type - assume plugin
                    dep_type = DependencyType.PLUGIN
                    dep_name = dep_spec

                result.append(PluginDependency(
                    type=dep_type,
                    name=dep_name,
                    version=version
                ))
            elif isinstance(dep, dict):
                result.append(PluginDependency(**dep))
            else:
                result.append(dep)
        return result


class PluginManifestSummary(BaseModel):
    """Lightweight summary for plugin listing."""
    name: str
    version: str
    type: PluginType
    description: str
    author: str
    tags: List[str] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list)
    status: str = "discovered"
    plugin_dir: str = ""
    manifest_path: str = ""


# Type alias for forward reference
ConfigProperty.model_rebuild()


def load_manifest(manifest_path: Union[str, Path]) -> PluginManifest:
    """Load and validate a plugin.yaml manifest file."""
    import yaml
    path = Path(manifest_path)
    if not path.exists():
        raise FileNotFoundError(f"Plugin manifest not found: {manifest_path}")

    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    if not data:
        raise ValueError(f"Empty manifest file: {manifest_path}")

    return PluginManifest(**data)


def validate_manifest_dict(data: Dict[str, Any]) -> PluginManifest:
    """Validate a manifest dictionary."""
    return PluginManifest(**data)


# Re-export for convenience
__all__ = [
    "PluginType",
    "DependencyType",
    "ConfigProperty",
    "ConfigSchema",
    "PluginDependency",
    "PluginManifest",
    "PluginManifestSummary",
    "load_manifest",
    "validate_manifest_dict",
]