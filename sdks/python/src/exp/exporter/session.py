"""
ServerSession Module

This module provides the ServerSession class, which manages communication between the
server and client in the MCP (Model Context Protocol) framework. It is most commonly
used in MCP servers to interact with the client.

Common usage pattern:
```
    server = Server(name)

    @server.call_function()
    async def handle_function_call(ctx: RequestContext, arguments: dict[str, Any]) -> Any:
        # Check client capabilities before proceeding
        if ctx.session.check_client_capability(
            types.ClientCapabilities(experimental={"advanced_functions": dict()})
        ):
            # Perform advanced function operations
            result = await perform_advanced_function_operation(arguments)
        else:
            # Fall back to basic function operations
            result = await perform_basic_function_operation(arguments)

        return result

    @server.list_prompts()
    async def handle_list_prompts(ctx: RequestContext) -> list[types.Prompt]:
        # Access session for any necessary checks or operations
        if ctx.session.client_params:
            # Customize prompts based on client initialization parameters
            return generate_custom_prompts(ctx.session.client_params)
        else:
            return default_prompts
```

The ServerSession class is typically used internally by the Server class and should not
be instantiated directly by users of the MCP framework.
"""

from enum import Enum
from typing import TypeVar

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
import exp.types as types


from exp.shared.message import  SessionMessage
from exp.shared.session import (
    BaseSession,
    RequestResponder
)


class InitializationState(Enum):
    NotInitialized = 1
    Initializing = 2
    Initialized = 3


ServerSessionT = TypeVar("ServerSessionT", bound="ServerSession")

ServerRequestResponder = (
    RequestResponder[types.ClientRequest,
                     types.ServerResult] | Exception
)


class ServerSession(BaseSession):

    def __init__(
        self,
        read_stream: MemoryObjectReceiveStream[SessionMessage | Exception],
        write_stream: MemoryObjectSendStream[SessionMessage],
    ) -> None:
        super().__init__(read_stream, write_stream)

        self._incoming_message_stream_writer, self._incoming_message_stream_reader = anyio.create_memory_object_stream[
            ServerRequestResponder
        ](0)
        self._exit_stack.push_async_callback(
            lambda: self._incoming_message_stream_reader.aclose())

    async def _receive_loop(self) -> None:
        async with self._incoming_message_stream_writer:
            await super()._receive_loop()

    async def _handle_incoming(self, req: ServerRequestResponder) -> None:
        await self._incoming_message_stream_writer.send(req)

    @property
    def incoming_messages(
        self,
    ) -> MemoryObjectReceiveStream[ServerRequestResponder]:
        return self._incoming_message_stream_reader
