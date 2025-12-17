
from __future__ import annotations as _annotations


import json
import logging
import warnings
from collections.abc import Awaitable, Callable, Iterable
from contextlib import AsyncExitStack
from typing import Any, Generic, TypeAlias, cast

import anyio
import jsonschema
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from pydantic import AnyUrl
from typing_extensions import TypeVar
import exp.types as types

from exp.exporter.lowlevel.func_inspection import create_call_wrapper
from exp.exporter.session import ServerSession
from exp.shared.exceptions import McpError
from exp.shared.message import  SessionMessage
from exp.shared.session import RequestResponder

logger = logging.getLogger(__name__)

RequestT = TypeVar("RequestT", default=Any)

# type aliases for function call results
StructuredContent: TypeAlias = dict[str, Any]
UnstructuredContent: TypeAlias = Iterable[types.ContentBlock]
CombinationContent: TypeAlias = tuple[UnstructuredContent, StructuredContent]


class Server(Generic[RequestT]):
    def __init__(
        self
    ):
        self.request_handlers: dict[type, Callable[...,
                                                   Awaitable[types.ServerResult]]] = {}
        logger.debug("Initializing server ")

    def list_functions(self):
        def decorator(
            func: Callable[[], Awaitable[list[types.FunctionT]]]
            | Callable[[types.ListFunctionsRequest], Awaitable[types.ListFunctionsResult]],
        ):
            logger.debug("Registering handler for ListfucntionsRequest")

            wrapper = create_call_wrapper(func, types.ListFunctionsRequest)

            async def handler(req: types.ListFunctionsRequest):
                result = await wrapper(req)

                # Handle both old style (list[Function]) and new style (ListFunctionsResult)
                if isinstance(result, types.ListFunctionsResult):  # pragma: no cover
                    return types.ServerResult(result)
                else:
                    # Old style returns list[Function]
                    # Clear and refresh the entire function cache
                    return types.ServerResult(types.ListFunctionsResult(functions=result))

            self.request_handlers[types.ListFunctionsRequest] = handler
            return func

        return decorator

    def set_init(self):
        def decorator(
            func: Callable[[], Awaitable[list[types.FunctionT]]]
        ):
            logger.debug("Registering handler for ListFunctionsRequest")

            wrapper = create_call_wrapper(func, types.ListFunctionsRequest)

            async def handler(req: types.InitializeRequest):
                functions: list[types.FunctionT] = await wrapper(req)

                return types.ServerResult(
                    types.InitializeResult(
                        capabilities=types.ServerCapabilities(
                            functions={
                                function.name: function for function in functions},
                            classes={}
                        )
                    )
                )

            self.request_handlers[types.InitializeRequest] = handler
            return func

        return decorator

    def _make_error_result(self, error_message: str) -> types.ServerResult:
        """Create a ServerResult with an error CallFunctionResult."""
        return types.ServerResult(
            types.CallFunctionResult(
                content=[types.TextContent(type="text", text=error_message)],
                isError=True,
            )
        )

    def call_function(self, *, validate_input: bool = True):
        """Register a function call handler.

        Args:
            validate_input: If True, validates input against inputSchema. Default is True.

        The handler validates input against inputSchema (if validate_input=True), calls the function function,
        and builds a CallFunctionResult with the results:
        - Unstructured content (iterable of ContentBlock): returned in content
        - Structured content (dict): returned in structuredContent, serialized JSON text returned in content
        - Both: returned in content and structuredContent

        If outputSchema is defined, validates structuredContent or errors if missing.
        """

        def decorator(
            func: Callable[
                ...,
                Awaitable[UnstructuredContent | StructuredContent |
                          CombinationContent | types.CallFunctionResult],
            ],
        ):
            logger.debug("Registering handler for CallFunctionRequest")

            async def handler(req: types.CallFunctionRequest):
                try:
                    function_name = req.params.name
                    arguments = req.params.arguments or {}
                    function = await self._get_function(function_name)

                    # input validation
                    if validate_input and function:
                        try:
                            jsonschema.validate(
                                instance=arguments, schema=function.inputSchema)
                        except jsonschema.ValidationError as e:
                            return self._make_error_result(f"Input validation error: {e.message}")

                    # function call
                    results = await func(function_name, arguments)

                    # output normalization
                    unstructured_content: UnstructuredContent
                    maybe_structured_content: StructuredContent | None
                    if isinstance(results, types.CallFunctionResult):
                        return types.ServerResult(results)
                    elif isinstance(results, tuple) and len(results) == 2:
                        # function returned both structured and unstructured content
                        unstructured_content, maybe_structured_content = cast(
                            CombinationContent, results)
                    elif isinstance(results, dict):
                        # function returned structured content only
                        maybe_structured_content = cast(
                            StructuredContent, results)
                        unstructured_content = [types.TextContent(
                            type="text", text=json.dumps(results, indent=2))]
                    elif hasattr(results, "__iter__"):  # pragma: no cover
                        # function returned unstructured content only
                        unstructured_content = cast(
                            UnstructuredContent, results)
                        maybe_structured_content = None
                    else:  # pragma: no cover
                        return self._make_error_result(f"Unexpected return type from function: {type(results).__name__}")

                    # output validation
                    if function and function.outputSchema is not None:
                        if maybe_structured_content is None:
                            return self._make_error_result(
                                "Output validation error: outputSchema defined but no structured output returned"
                            )
                        else:
                            try:
                                jsonschema.validate(
                                    instance=maybe_structured_content, schema=function.outputSchema)
                            except jsonschema.ValidationError as e:
                                return self._make_error_result(f"Output validation error: {e.message}")

                    # result
                    return types.ServerResult(
                        types.CallFunctionResult(
                            content=list(unstructured_content),
                            structuredContent=maybe_structured_content,
                            isError=False,
                        )
                    )
                except Exception as e:
                    return self._make_error_result(str(e))

            self.request_handlers[types.CallFunctionRequest] = handler
            return func

        return decorator

    async def run(
        self,
        read_stream: MemoryObjectReceiveStream[SessionMessage | Exception],
        write_stream: MemoryObjectSendStream[SessionMessage],
        # When False, exceptions are returned as messages to the client.
        # When True, exceptions are raised, which will cause the server to shut down
        # but also make tracing exceptions much easier during testing and when using
        # in-process servers.
        raise_exceptions: bool = False,

    ):
        async with AsyncExitStack() as stack:
            session = await stack.enter_async_context(
                ServerSession(
                    read_stream,
                    write_stream
                )
            )

            async with anyio.create_task_group() as tg:
                async for message in session.incoming_messages:
                    logger.debug("Received message: %s", message)

                    tg.start_soon(
                        self._handle_message,
                        message,
                        session,
                        raise_exceptions,
                    )

    async def _handle_message(
        self,
        message: RequestResponder[types.ClientRequest, types.ServerResult] | types.ClientNotification | Exception,
        session: ServerSession,
        raise_exceptions: bool = False,
    ):

        with warnings.catch_warnings(record=True) as w:
            match message:
                case RequestResponder(request=types.ClientRequest(root=req)) as responder:
                    with responder:
                        await self._handle_request(message, req, session, raise_exceptions)
                case types.ClientNotification(root=notify):
                    # await self._handle_notification(notify)
                    # do nothing
                    pass
                case Exception():  # pragma: no cover
                    logger.error(f"Received exception from stream: {message}")
                    await session.send_log_message(
                        level="error",
                        data="Internal Server Error",
                        logger="mcp.server.exception_handler",
                    )
                    if raise_exceptions:
                        raise message

            for warning in w:  # pragma: no cover
                logger.info("Warning: %s: %s",
                            warning.category.__name__, warning.message)

    async def _handle_request(
        self,
        message: RequestResponder[types.ClientRequest, types.ServerResult],
        req: Any,
        session: ServerSession,
        raise_exceptions: bool,
    ):

        logger.info("Processing request of type %s", type(req).__name__)
        if handler := self.request_handlers.get(type(req)):  # type: ignore
            logger.debug("Dispatching request of type %s", type(req).__name__)

            try:
                response = await handler(req)
            except McpError as err:  # pragma: no cover
                response = err.error
            except anyio.get_cancelled_exc_class():  # pragma: no cover
                logger.info(
                    "Request %s cancelled - duplicate response suppressed",
                    message.request_id,
                )
                return
            except Exception as err:  # pragma: no cover
                if raise_exceptions:
                    raise err
                response = types.ErrorData(code=0, message=str(err), data=None)

            await message.respond(response)
        else:  # pragma: no cover
            await message.respond(
                types.ErrorData(
                    code=types.METHOD_NOT_FOUND,
                    message="Method not found",
                )
            )

        logger.debug("Response sent")

    async def _get_function(self, name: str) -> types.FunctionT | None:
        """Get assigned by the higlevel server while calling setup_handler()."""
        pass
