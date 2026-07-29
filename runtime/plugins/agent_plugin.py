"""
AIPENSA Agent Runtime - Plugin Wrapper

Wraps the AgentModule as a plugin for dynamic loading.
"""

from runtime.base.plugin import RuntimePlugin, PluginMetadata, PluginType
from runtime.agent.module import AgentModule, AgentMetadata, AgentState, AgentRole, AgentMessage, Task
from runtime.base.runtime import Runtime

class AgentPlugin(RuntimePlugin):
    """Plugin wrapper for Agent Module."""

    metadata = PluginMetadata(
        name="agent",
        version="1.0.0",
        description="Agent lifecycle management and orchestration",
        author="AIPENSA",
        plugin_type=PluginType.CUSTOM,
        provides=["agent_management", "task_execution", "message_passing"],
        requires=["tool", "memory", "planning"],
        tags={"agent", "orchestration", "automation"}
    )

    def __init__(self, config: dict = None):
        super().__init__(config)
        self._module: AgentModule = None

    async def initialize(self, runtime: Runtime, config: dict) -> None:
        await super().initialize(runtime, config)
        self._module = AgentModule(config)

    async def start(self) -> None:
        await super().start()
        await self._module.initialize(self._runtime, self.config)
        await self._module.start()

    async def stop(self) -> None:
        await super().stop()
        if self._module:
            await self._module.stop()

    async def cleanup(self) -> None:
        await super().cleanup()
        if self._module:
            await self._module.cleanup()

    async def health_check(self) -> dict:
        if self._module:
            return await self._module.health_check()
        return {"plugin": self.name, "healthy": False, "status": self.status.value}

    async def execute(self, operation: str, **kwargs) -> any:
        """Execute plugin operations."""
        if not self._module:
            raise RuntimeError("Module not initialized")

        return await self._module.execute(operation, **kwargs)