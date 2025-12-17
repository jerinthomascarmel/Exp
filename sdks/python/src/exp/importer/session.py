import logging
from datetime import timedelta
from typing import Any


from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream


import exp.types as types
from exp.shared.message import SessionMessage
from exp.shared.session import BaseSession


logger = logging.getLogger("client")


class ClientSession(BaseSession):
    def __init__(
        self,
        read_stream: MemoryObjectReceiveStream[SessionMessage | Exception],
        write_stream: MemoryObjectSendStream[SessionMessage]
    ) -> None:
        super().__init__(
            read_stream,
            write_stream
        )

        self._server_capabilities: types.ServerCapabilities | None = None

    async def initialize(self) -> types.InitializeResult:

        result = await self.send_request(
            types.ClientRequest(
                types.InitializeRequest(method="initialize", params={})
            ),
            types.InitializeResult,
        )

        self._server_capabilities = result.capabilities

        return result

    def get_server_capabilities(self) -> types.ServerCapabilities | None:
        """Return the server capabilities received during initialization.

        Returns None if the session has not been initialized yet.
        """
        return self._server_capabilities

    async def call_function(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        read_timeout_seconds: timedelta | None = None,
        *,
        meta: dict[str, Any] | None = None,
    ) -> types.CallFunctionResult:
        """Send a functions/call request with optional progress callback support."""

        _meta: types.RequestParams.Meta | None = None
        if meta is not None:
            _meta = types.RequestParams.Meta(**meta)
        print('p2')
        result = await self.send_request(
            types.ClientRequest(
                types.CallFunctionRequest(
                    params=types.CallFunctionRequestParams(
                        name=name, arguments=arguments, _meta=_meta),
                )
            ),
            types.CallFunctionResult,
            request_read_timeout_seconds=read_timeout_seconds,
        )

        print('p3')

        if not result.isError:
            await self._validate_function_result(name, result)

        return result

    async def _validate_function_result(self, name: str, result: types.CallFunctionResult) -> None:
        """Validate the structured content of a function result against its output schema."""
        if not self._server_capabilities:
            # get refresh output schema
            await self.initialize()

        if name not in self._server_capabilities.functions.keys():
            raise RuntimeError('result schema not found !')

        output_schema = None
        if name in self._server_capabilities.functions:
            output_schema = self._server_capabilities.functions.get(
                name).outputSchema
        else:
            logger.warning(
                f"Function {name} not listed by server, cannot validate any structured content")

        if output_schema is not None:
            from jsonschema import SchemaError, ValidationError, validate

            if result.structuredResult is None:
                raise RuntimeError(
                    f"Function {name} has an output schema but did not return structured content"
                )  # pragma: no cover
            try:
                validate(result.structuredResult, output_schema)
            except ValidationError as e:
                raise RuntimeError(
                    f"Invalid structured content returned by function {name}: {e}")  # pragma: no cover
            except SchemaError as e:  # pragma: no cover
                raise RuntimeError(
                    f"Invalid schema for function {name}: {e}")  # pragma: no cover

    async def list_functions(
        self
    ) -> types.ListFunctionsResult:
        """Send a functions/list request.
        Args:
            params: Full pagination parameters including cursor and any future fields
        """

        request_params = None

        result = await self.send_request(
            types.ClientRequest(
                types.ListFunctionsRequest(params=request_params)),
            types.ListFunctionsResult,
        )

        return result
