import logging
from collections.abc import Callable
from contextlib import AsyncExitStack
from datetime import timedelta
from types import TracebackType
from typing import Any, Generic, TypeVar

import anyio
import httpx
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from pydantic import BaseModel
from typing_extensions import Self

from exp.shared.exceptions import McpError
from exp.shared.message import MessageMetadata, SessionMessage
from exp.types import (
    CONNECTION_CLOSED,
    INVALID_PARAMS,
    ClientRequest,
    ErrorData,
    JSONRPCError,
    JSONRPCMessage,
    JSONRPCRequest,
    JSONRPCResponse,
    RequestParams,
    ServerResult
)


SendRequestT = TypeVar("SendRequestT", bound=ClientRequest)
SendResultT = TypeVar("SendResultT", bound=ServerResult)
ReceiveRequestT = TypeVar("ReceiveRequestT", bound=ClientRequest)
ReceiveResultT = TypeVar("Rec", bound=BaseModel)

RequestId = str | int

class RequestResponder(Generic[ReceiveRequestT, SendResultT]):
    """Handles responding to MCP requests and manages request lifecycle.

    This class MUST be used as a context manager to ensure proper cleanup and
    cancellation handling:

    Example:
        with request_responder as resp:
            await resp.respond(result)

    The context manager ensures:
    1. Proper cancellation scope setup and cleanup
    2. Request completion tracking
    3. Cleanup of in-flight requests
    """

    def __init__(
        self,
        request_id: RequestId,
        request: ReceiveRequestT,
        session: """BaseSession[
            SendRequestT,
            SendResultT,
            ReceiveRequestT
        ]""",
        on_complete: Callable[["RequestResponder[ReceiveRequestT, SendResultT]"], Any],
        message_metadata: MessageMetadata = None,
    ) -> None:
        self.request_id = request_id
        self.request = request
        self.message_metadata = message_metadata
        self._session = session
        self._completed = False
        self._cancel_scope = anyio.CancelScope()
        self._on_complete = on_complete
        self._entered = False  # Track if we're in a context manager

    def __enter__(self) -> "RequestResponder[ReceiveRequestT, SendResultT]":
        """Enter the context manager, enabling request cancellation tracking."""
        self._entered = True
        self._cancel_scope = anyio.CancelScope()
        self._cancel_scope.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the context manager, performing cleanup and notifying completion."""
        try:
            if self._completed:  # pragma: no branch
                self._on_complete(self)
        finally:
            self._entered = False
            if not self._cancel_scope:  # pragma: no cover
                raise RuntimeError("No active cancel scope")
            self._cancel_scope.__exit__(exc_type, exc_val, exc_tb)

    async def respond(self, response: SendResultT | ErrorData) -> None:
        """Send a response for this request.

        Must be called within a context manager block.
        Raises:
            RuntimeError: If not used within a context manager
            AssertionError: If request was already responded to
        """
        if not self._entered:  # pragma: no cover
            raise RuntimeError(
                "RequestResponder must be used as a context manager")
        assert not self._completed, "Request already responded to"

        if not self.cancelled:  # pragma: no branch
            self._completed = True

            await self._session._send_response(  # type: ignore[reportPrivateUsage]
                request_id=self.request_id, response=response
            )

    async def cancel(self) -> None:
        """Cancel this request and mark it as completed."""
        if not self._entered:  # pragma: no cover
            raise RuntimeError(
                "RequestResponder must be used as a context manager")
        if not self._cancel_scope:  # pragma: no cover
            raise RuntimeError("No active cancel scope")

        self._cancel_scope.cancel()
        self._completed = True  # Mark as completed so it's removed from in_flight
        # Send an error response to indicate cancellation
        await self._session._send_response(  # type: ignore[reportPrivateUsage]
            request_id=self.request_id,
            response=ErrorData(code=0, message="Request cancelled", data=None),
        )

    @property
    def in_flight(self) -> bool:  # pragma: no cover
        return not self._completed and not self.cancelled

    @property
    def cancelled(self) -> bool:  # pragma: no cover
        return self._cancel_scope.cancel_called


class BaseSession():
    """
    Implements an MCP "session" on top of read/write streams, including features
    like request/response linking, notifications, and progress.

    This class is an async context manager that automatically starts processing
    messages when entered.
    """

    _response_streams: dict[RequestId,
                            MemoryObjectSendStream[JSONRPCResponse | JSONRPCError]]
    _request_id: int
    _in_flight: dict[RequestId, RequestResponder[ReceiveRequestT, SendResultT]]

    def __init__(
        self,
        read_stream: MemoryObjectReceiveStream[SessionMessage | Exception],
        write_stream: MemoryObjectSendStream[SessionMessage],
        # If none, reading will never time out
        read_timeout_seconds: timedelta | None = None,
    ) -> None:
        self._read_stream = read_stream
        self._write_stream = write_stream
        self._response_streams = {}
        self._request_id = 0
        self._receive_request_type = ClientRequest
        self._session_read_timeout_seconds = read_timeout_seconds
        self._in_flight = {}
        self._progress_callbacks = {}
        self._exit_stack = AsyncExitStack()

    async def run(self) -> None:
        await self.__aenter__()

    async def stop(self) -> None:
        await self.__aexit__(None, None, None)

    async def __aenter__(self) -> Self:
        self._task_group = anyio.create_task_group()
        await self._task_group.__aenter__()
        self._task_group.start_soon(self._receive_loop)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool | None:
        await self._exit_stack.aclose()
        # Using BaseSession as a context manager should not block on exit (this
        # would be very surprising behavior), so make sure to cancel the tasks
        # in the task group.
        self._task_group.cancel_scope.cancel()
        return await self._task_group.__aexit__(exc_type, exc_val, exc_tb)

    async def send_request(
        self,
        request: SendRequestT,
        result_type: type[ReceiveResultT],
        request_read_timeout_seconds: timedelta | None = None,
        metadata: MessageMetadata = None
    ) -> ReceiveResultT:
        """
        Sends a request and wait for a response. Raises an McpError if the
        response contains an error. If a request read timeout is provided, it
        will take precedence over the session read timeout.
        """
        request_id = self._request_id
        self._request_id = request_id + 1

        response_stream, response_stream_reader = anyio.create_memory_object_stream[JSONRPCResponse | JSONRPCError](
            1)
        self._response_streams[request_id] = response_stream

        request_data = request.model_dump(
            by_alias=True, mode="json", exclude_none=True)

        try:
            jsonrpc_request = JSONRPCRequest(
                jsonrpc="2.0",
                id=request_id,
                **request_data,
            )

            await self._write_stream.send(SessionMessage(message=JSONRPCMessage(jsonrpc_request), metadata=metadata))
            # request read timeout takes precedence over session read timeout
            timeout = None
            if request_read_timeout_seconds is not None:  # pragma: no cover
                timeout = request_read_timeout_seconds.total_seconds()
            elif self._session_read_timeout_seconds is not None:  # pragma: no cover
                timeout = self._session_read_timeout_seconds.total_seconds()
            else:
                timeout = 20
            try:
                with anyio.fail_after(timeout):
                    response_or_error = await response_stream_reader.receive()
            except TimeoutError:
                raise McpError(
                    ErrorData(
                        code=httpx.codes.REQUEST_TIMEOUT,
                        message=(
                            f"Timed out while waiting for response to "
                            f"{request.__class__.__name__}. Waited "
                            f"{timeout} seconds."
                        ),
                    )
                )

            if isinstance(response_or_error, JSONRPCError):
                raise McpError(response_or_error.error)
            else:
                return result_type.model_validate(response_or_error.result)

        finally:
            self._response_streams.pop(request_id, None)
            self._progress_callbacks.pop(request_id, None)
            await response_stream.aclose()
            await response_stream_reader.aclose()

    async def _send_response(self, request_id: RequestId, response: SendResultT | ErrorData) -> None:
        if isinstance(response, ErrorData):
            jsonrpc_error = JSONRPCError(
                jsonrpc="2.0", id=request_id, error=response)
            session_message = SessionMessage(
                message=JSONRPCMessage(jsonrpc_error))
            await self._write_stream.send(session_message)
        else:
            jsonrpc_response = JSONRPCResponse(
                jsonrpc="2.0",
                id=request_id,
                result=response.model_dump(
                    by_alias=True, mode="json", exclude_none=True),
            )
            session_message = SessionMessage(
                message=JSONRPCMessage(jsonrpc_response))
            await self._write_stream.send(session_message)

    async def _receive_loop(self) -> None:
        async with (
            self._read_stream,
            self._write_stream,
        ):
            try:
                async for message in self._read_stream:
                    if isinstance(message, Exception):  # pragma: no cover
                        await self._handle_incoming(message)
                    elif isinstance(message.message.root, JSONRPCRequest):
                        try:
                            validated_request = self._receive_request_type.model_validate(
                                message.message.root.model_dump(
                                    by_alias=True, mode="json", exclude_none=True)
                            )

                            responder = RequestResponder(
                                request_id=message.message.root.id,
                                request=validated_request,
                                session=self,
                                on_complete=lambda r: self._in_flight.pop(
                                    r.request_id, None),
                                message_metadata=message.metadata,
                            )
                            self._in_flight[responder.request_id] = responder
                            # await self._received_request(responder)
                            await self._handle_incoming(responder)
                            
                        except Exception as e:
                            # For request validation errors, send a proper JSON-RPC error
                            # response instead of crashing the server
                            logging.warning(f"Failed to validate request: {e}")
                            logging.debug(
                                f"Message that failed validation: {message.message.root}")
                            error_response = JSONRPCError(
                                jsonrpc="2.0",
                                id=message.message.root.id,
                                error=ErrorData(
                                    code=INVALID_PARAMS,
                                    message=f"Failed to validate request: {e}",
                                    data="",
                                ),
                            )
                            session_message = SessionMessage(
                                message=JSONRPCMessage(error_response))
                            await self._write_stream.send(session_message)

                    else:
                        # Response or error
                        stream = self._response_streams.pop(
                            message.message.root.id, None)
                        if stream:  # pragma: no cover
                            await stream.send(message.message.root)
                        else:  # pragma: no cover
                            await self._handle_incoming(
                                RuntimeError(
                                    f"Received response with an unknown request ID: {message}")
                            )

            except anyio.ClosedResourceError:
                # This is expected when the client disconnects abruptly.
                # Without this handler, the exception would propagate up and
                # crash the server's task group.
                logging.debug(
                    "Read stream closed by client")  # pragma: no cover
            except Exception as e:  # pragma: no cover
                # Other exceptions are not expected and should be logged. We purposefully
                # catch all exceptions here to avoid crashing the server.
                logging.exception(f"Unhandled exception in receive loop: {e}")
            finally:
                # after the read stream is closed, we need to send errors
                # to any pending requests
                for id, stream in self._response_streams.items():
                    error = ErrorData(code=CONNECTION_CLOSED,
                                      message="Connection closed")
                    try:
                        await stream.send(JSONRPCError(jsonrpc="2.0", id=id, error=error))
                        await stream.aclose()
                    except Exception:  # pragma: no cover
                        # Stream might already be closed
                        pass
                self._response_streams.clear()

    async def _received_request(self, responder: RequestResponder[ReceiveRequestT, SendResultT]) -> None:
        """
        Can be overridden by subclasses to handle a request without needing to
        listen on the message stream.

        If the request is responded to within this method, it will not be
        forwarded on to the message stream.
        """

   

    async def _handle_incoming(
        self,
        req: RequestResponder[ReceiveRequestT, SendResultT] | Exception,
    ) -> None:
        """A generic handler for incoming messages. Overwritten by subclasses."""
        pass  # pragma: no cover
