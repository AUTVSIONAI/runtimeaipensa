"""
Local MCP Module Implementation

Provides Model Context Protocol (MCP) client capabilities for connecting
to MCP servers and calling their tools.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import asyncio
import logging

from runtime.modules import (
    RuntimeModule,
    ModuleMetadata,
    ModuleState,
    MCPModule,
    MCPServer,
)

logger = logging.getLogger(__name__)


@dataclass
class _MCPConnection:
    """Internal MCP server connection."""
    server_id: str
    name: str
    transport: str  # "sse" or "stdio"
    endpoint: str
    process: Optional[asyncio.subprocess.Process] = None
    session: Any = None
    status: str = "disconnected"
    tools: List[Dict[str, Any]] = field(default_factory=list)
    connected_at: Optional[datetime] = None


class LocalMCPModule(MCPModule):
    """
    Local MCP client implementation.

    Supports connecting to MCP servers via SSE or stdio transport.
    """

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="mcp",
            version="1.0.0",
            description="Model Context Protocol client",
            author="AIPENSA",
            dependencies=[],
            provides=["mcp_connect", "mcp_call_tool", "mcp_list_tools"],
            tags={"local", "mcp", "protocol"},
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self._config = config or {}
        self._connections: Dict[str, _MCPConnection] = {}
        self._mcp_available = False

    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        self._runtime = runtime
        self._config = {**self._config, **config}

        # Check if MCP SDK is available
        try:
            import mcp
            self._mcp_available = True
        except ImportError:
            logger.warning("MCP SDK not available - install 'mcp' package for MCP support")
            self._mcp_available = False

        self.state = ModuleState.INITIALIZED
        logger.info("LocalMCPModule initialized")

    async def start(self) -> None:
        self.state = ModuleState.RUNNING
        logger.info("LocalMCPModule started")

    async def stop(self) -> None:
        # Disconnect all servers
        for server_id in list(self._connections.keys()):
            await self.disconnect_server(server_id)
        self.state = ModuleState.STOPPED
        logger.info("LocalMCPModule stopped")

    async def cleanup(self) -> None:
        self._connections.clear()
        self.state = ModuleState.UNINITIALIZED
        logger.info("LocalMCPModule cleaned up")

    async def health_check(self) -> Dict[str, Any]:
        return {
            "module": "mcp",
            "status": self.state.value,
            "healthy": self.state == ModuleState.RUNNING,
            "mcp_sdk_available": self._mcp_available,
            "connected_servers": len([c for c in self._connections.values() if c.status == "connected"]),
        }

    async def connect_server(
        self,
        server_id: str,
        config: Dict[str, Any]
    ) -> MCPServer:
        """Connect to an MCP server."""
        if not self._mcp_available:
            raise RuntimeError("MCP SDK not available - install 'mcp' package")

        if server_id in self._connections:
            raise ValueError(f"Server already connected: {server_id}")

        name = config.get("name", server_id)
        transport = config.get("transport", "stdio")
        endpoint = config.get("endpoint", "")

        connection = _MCPConnection(
            server_id=server_id,
            name=name,
            transport=transport,
            endpoint=endpoint,
        )

        self._connections[server_id] = connection

        try:
            if transport == "stdio":
                await self._connect_stdio(connection, config)
            elif transport == "sse":
                await self._connect_sse(connection, config)
            else:
                raise ValueError(f"Unsupported transport: {transport}")

            # Get available tools
            await self._fetch_tools(connection)

            connection.status = "connected"
            connection.connected_at = datetime.utcnow()

            logger.info(f"Connected to MCP server: {name} ({server_id})")

            server = MCPServer(
                server_id=server_id,
                name=name,
                transport=transport,
                endpoint=endpoint,
                status="connected",
                tools=connection.tools,
                connected_at=connection.connected_at,
            )

            # Publish tool registration event
            if self._runtime:
                from runtime.events import Event, EventType
                await self._runtime.event_bus.publish(Event(
                    event_type=EventType.TOOL_REGISTERED,
                    source="mcp",
                    payload={"server_id": server_id, "tools": [t.get("name") for t in connection.tools]}
                ))

            return server

        except Exception as e:
            connection.status = "error"
            del self._connections[server_id]
            logger.error(f"Failed to connect to MCP server {server_id}: {e}")
            raise

    async def _connect_stdio(self, connection: _MCPConnection, config: Dict[str, Any]) -> None:
        """Connect via stdio transport."""
        import mcp
        from mcp.client.stdio import stdio_client
        from mcp import ClientSession

        command = config.get("command")
        args = config.get("args", [])
        env = config.get("env", {})

        if not command:
            raise ValueError("command required for stdio transport")

        # Start process
        connection.process = await asyncio.create_subprocess_exec(
            command, *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        # Create client session
        from mcp.client.session import ClientSession
        from mcp.client.stdio import stdio_client as mcp_stdio_client

        # Use stdio client to create session
        read_transport, write_transport = await connection.process.stdout, connection.process.stdin
        connection.session = ClientSession(read_transport, write_transport)

        # Initialize session
        await connection.session.initialize()

    async def _connect_sse(self, connection: _MCPConnection, config: Dict[str, Any]) -> None:
        """Connect via SSE transport."""
        import mcp
        from mcp.client.sse import sse_client
        from mcp import ClientSession

        if not connection.endpoint:
            raise ValueError("endpoint required for SSE transport")

        # Create SSE client
        connection.session = sse_client(connection.endpoint).__enter__()

        # Initialize session
        await connection.session.initialize()

    async def _fetch_tools(self, connection: _MCPConnection) -> None:
        """Fetch tools from connected server."""
        if connection.session:
            tools = await connection.session.list_tools()
            connection.tools = [
                {
                    "name": t.name,
                    "description": t.description,
                    "inputSchema": t.inputSchema,
                }
                for t in tools
            ]

    async def disconnect_server(self, server_id: str) -> bool:
        """Disconnect from MCP server."""
        if server_id not in self._connections:
            return False

        connection = self._connections[server_id]

        try:
            if connection.session:
                await connection.session.close()

            if connection.process:
                connection.process.terminate()
                try:
                    await asyncio.wait_for(connection.process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    connection.process.kill()
                    await connection.process.wait()

        except Exception as e:
            logger.warning(f"Error disconnecting from {server_id}: {e}")

        del self._connections[server_id]
        logger.info(f"Disconnected from MCP server: {server_id}")
        return True

    async def call_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Any:
        """Call MCP tool."""
        if server_id not in self._connections:
            raise ValueError(f"Server not connected: {server_id}")

        connection = self._connections[server_id]

        if connection.status != "connected":
            raise RuntimeError(f"Server not connected: {server_id}")

        if not connection.session:
            raise RuntimeError(f"No active session for {server_id}")

        try:
            result = await connection.session.call_tool(tool_name, arguments)
            return result
        except Exception as e:
            logger.error(f"MCP tool call failed: {e}")
            raise

    async def list_servers(self) -> List[MCPServer]:
        """List connected servers."""
        return [
            MCPServer(
                server_id=c.server_id,
                name=c.name,
                transport=c.transport,
                endpoint=c.endpoint,
                status=c.status,
                tools=c.tools,
                connected_at=c.connected_at,
            )
            for c in self._connections.values()
        ]

    async def get_server(self, server_id: str) -> Optional[MCPServer]:
        """Get server info."""
        if server_id not in self._connections:
            return None

        c = self._connections[server_id]
        return MCPServer(
            server_id=c.server_id,
            name=c.name,
            transport=c.transport,
            endpoint=c.endpoint,
            status=c.status,
            tools=c.tools,
            connected_at=c.connected_at,
        )

    async def get_server_tools(self, server_id: str) -> List[Dict[str, Any]]:
        """Get available tools from server."""
        if server_id not in self._connections:
            return []

        return self._connections[server_id].tools.copy()

    # Compatibility method for tools module
    async def call_tool(self, call) -> Any:
        """Legacy call_tool method for compatibility."""
        return await self.call_tool(call.server_id, call.tool_name, call.arguments)