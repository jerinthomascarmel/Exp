from exp.importer.stdio import StdioClient, StdioServerParameters
from exp.importer.session import ClientSession
from typing import Any
from datetime import timedelta
import exp.types as types


class MCPClient:
    def __init__(
        self,
        server: StdioServerParameters
    ) -> None:
        self._stdio_client = StdioClient(server=server)
        self._session: ClientSession = None

    async def run(self) -> None:
        """Run the MCP client using stdio transport."""
        read_stream, write_stream = await self._stdio_client.start()
        self._session = ClientSession(
            read_stream=read_stream,
            write_stream=write_stream,
        )
        await self._session.run()

    async def close(self) -> None:
        """Stop the MCP client."""
        if self._session:
            await self._session.stop()

        if self._stdio_client.is_started:
            await self._stdio_client.stop()

    async def call_function(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        read_timeout_seconds: timedelta | None = None,
        *,
        meta: dict[str, Any] | None = None,
    ) -> types.CallFunctionResult:
        """Call a function by name with arguments."""
        if self._session is None:
            raise RuntimeError("MCP client is not running")

        return await self._session.call_function(
            name,
            arguments=arguments or {},
            read_timeout_seconds=read_timeout_seconds,
            meta=meta
        )

    async def list_functions(self) -> types.ListFunctionsResult:
    
        return await self._session.list_functions()

    async def initialize(self) -> None:
        """Send an initialize request to the server."""
        if self._session is None:
            raise RuntimeError("MCP client is not running")
        await self._session.initialize()
