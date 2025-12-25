from exp.importer.stdio import StdioClient, StdioParameters
from exp.importer.session import ClientSession
from typing import Any
from datetime import timedelta
import exp.types as types
from typing import Callable, Awaitable


class Importer:
    def __init__(
        self,
        server: StdioParameters
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

    def call_function(
        self,
        name: str
    ) -> Callable[..., Awaitable[types.CallFunctionResult]]:
        """Call a function by name with arguments."""

        async def func(*args, **kwargs) -> types.CallFunctionResult:
            if len(args) != 0:
                raise RuntimeError(
                    "you should call with kwargs , not with args ")

            arguments: dict[str, Any] | None = kwargs

            if self._session is None:
                raise RuntimeError("MCP client is not running")

            return await self._session.call_function(
                name,
                arguments=arguments or {},
                meta=None
            )
        return func

    def get_function(self, name: str) -> Callable[[str], Callable[..., Awaitable[types.CallFunctionResult]]]:
        return self.call_function(name=name)

    async def list_functions(self) -> types.ListFunctionsResult:
        return await self._session.list_functions()

    async def initialize(self) -> None:
        """Send an initialize request to the server."""
        if self._session is None:
            raise RuntimeError("MCP client is not running")
        await self._session.initialize()
