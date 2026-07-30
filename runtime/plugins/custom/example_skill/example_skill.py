"""
Example Skill Plugin - Demonstrates the plugin system
"""

from typing import Any, Dict, List, Optional
from runtime.plugins.base import Plugin, PluginMetadata, PluginType


class ExampleSkillPlugin(Plugin):
    """Example custom skill plugin."""

    metadata = PluginMetadata(
        name="example_skill",
        version="1.0.0",
        description="Example custom skill plugin demonstrating the plugin system",
        author="aipensa",
        plugin_type=PluginType.CUSTOM,
        provides=["example_task", "data_processing"],
        dependencies=["runtime:conversation", "skill:llm_generation"],
        tags={"example", "skill", "demo", "custom"},
        entry_point="example_skill.py",
        config_schema={
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean", "default": True, "description": "Enable this example skill"},
                "max_items": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 100},
                "api_endpoint": {"type": "string", "format": "uri", "description": "Optional external API endpoint"}
            },
            "required": ["enabled"]
        }
    )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.enabled = config.get("enabled", True) if config else True
        self.max_items = config.get("max_items", 100) if config else 100
        self.api_endpoint = config.get("api_endpoint") if config else None
        self._data_store: List[Dict] = []

    @classmethod
    def get_metadata(cls) -> PluginMetadata:
        return cls.metadata

    async def initialize(self, runtime: Any) -> None:
        """Initialize the plugin with runtime reference."""
        self.runtime = runtime
        self._initialized = True
        logger.info("ExampleSkillPlugin initialized")

    async def start(self) -> None:
        """Start the plugin (activate subscriptions, connections, etc.)."""
        self._data_store.clear()
        logger.info("ExampleSkillPlugin started")

    async def stop(self) -> None:
        """Stop the plugin gracefully."""
        logger.info("ExampleSkillPlugin stopped")

    async def cleanup(self) -> None:
        """Clean up resources."""
        self._data_store.clear()
        self._initialized = False
        logger.info("ExampleSkillPlugin cleaned up")

    def validate_config(self) -> bool:
        """Validate plugin configuration."""
        if self.max_items < 1 or self.max_items > 1000:
            return False
        return True

    async def execute_task(self, task_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task by name with given parameters."""
        if not self.enabled:
            return {"error": "Plugin not enabled"}

        if task_name == "example_task":
            return await self._handle_example_task(params)
        elif task_name == "data_processing":
            return await self._handle_data_processing(params)
        else:
            return {"error": f"Unknown task: {task_name}"}

    async def _handle_example_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle example task."""
        message = params.get("message", "Hello from Example Skill!")
        count = params.get("count", 1)

        results = []
        for i in range(min(count, self.max_items)):
            results.append({
                "id": i + 1,
                "message": f"{message} ({i + 1})",
                "timestamp": "2026-01-01T00:00:00Z"
            })

        self._data_store.extend(results)

        return {
            "success": True,
            "results": results,
            "count": len(results)
        }

    async def _handle_data_processing(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data processing task."""
        data = params.get("data", [])
        operation = params.get("operation", "transform")

        if operation == "transform":
            # Transform each item
            processed = [{"processed": True, **item} for item in data]
            self._data_store.extend(processed)
            return {"success": True, "processed": len(processed), "data": processed}
        elif operation == "filter":
            # Filter items based on condition
            condition = params.get("condition", {})
            filtered = [
                item for item in data
                if all(item.get(k) == v for k, v in condition.items())
            ]
            return {"success": True, "filtered": len(filtered), "data": filtered}
        elif operation == "aggregate":
            # Aggregate numeric fields
            field = params.get("field")
            agg_type = params.get("agg_type", "sum")
            if field:
                values = [item.get(field, 0) for item in data if field in item]
                if agg_type == "sum":
                    result = sum(values)
                elif agg_type == "avg":
                    result = sum(values) / len(values) if values else 0
                elif agg_type == "min":
                    result = min(values) if values else 0
                elif agg_type == "max":
                    result = max(values) if values else 0
                else:
                    result = sum(values)
                return {"success": True, "field": field, "operation": agg_type, "result": result}
            return {"error": "Field required for aggregation"}
        else:
            return {"error": f"Unknown operation: {operation}"}

    def get_stored_data(self) -> List[Dict]:
        """Get all stored data."""
        return self._data_store


logger = __import__("logging").getLogger(__name__)