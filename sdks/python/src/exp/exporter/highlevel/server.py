"""Exporter - A more ergonomic interface for MCP servers."""

from __future__ import annotations as _annotations

from collections.abc import (
    Callable,
    Sequence
)

from typing import Any, Literal

import anyio
from pydantic_settings import BaseSettings, SettingsConfigDict


from exp.exporter.highlevel.functions import FunctionManager
from exp.exporter.highlevel.utilities.logging import configure_logging, get_logger

from exp.exporter.lowlevel.server import Server as MCPServer
from exp.exporter.stdio import stdio_server
from exp.types import AnyFunction, ContentBlock
from exp.types import FunctionT as MCPFunction

logger = get_logger(__name__)


class Settings(BaseSettings):
    """Exporter server settings.

    All settings can be configured via environment variables with the prefix Exporter_.
    For example, Exporter_DEBUG=true will set debug=True.
    """
    model_config = SettingsConfigDict(
        env_prefix="Exporter_",
        env_file=".env",
        env_nested_delimiter="__",
        nested_model_default_partial_update=True,
        extra="ignore",
    )

    # Server settings
    debug: bool
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    # function settings
    warn_on_duplicate_functions: bool


class Exporter:
    def __init__(  # noqa: PLR0913
        self,
        debug: bool = False,
        log_level: Literal["DEBUG", "INFO",
            "WARNING", "ERROR", "CRITICAL"] = "INFO",
        warn_on_duplicate_functions: bool = True,
    ):

        self.settings = Settings(
            debug=debug,
            log_level=log_level,
            warn_on_duplicate_functions=warn_on_duplicate_functions,
        )

        self._mcp_server = MCPServer()
        self._function_manager = FunctionManager(
            functions=None, warn_on_duplicate_functions=self.settings.warn_on_duplicate_functions)

        # Set up MCP protocol handlersdsec
        self._setup_handlers()
        # Configure logging
        configure_logging(self.settings.log_level)

    def run(
        self
    ) -> None:
        """Run the Exporter server. Note this is a synchronous function.

        Args:
            transport: Transport protocol to use ("stdio", "sse", or "streamable-http")
            mount_path: Optional mount path for SSE transport
        """
        """Run the server using stdio transport."""

        async def run_stdio_async() -> None:
            async with stdio_server() as (read_stream, write_stream):
                await self._mcp_server.run(
                    read_stream,
                    write_stream
                )

        anyio.run(run_stdio_async)

    def _setup_handlers(self) -> None:
        """Set up core MCP protocol handlers."""
        self._mcp_server.list_functions()(self.list_functions)
        # Note: we disable the lowlevel server's input validation.
        # Exporter does ad hoc conversion of incoming data before validating -
        # for now we preserve this for backwards compatibility.
        self._mcp_server.call_function(validate_input=True)(self.call_function)
        self._mcp_server.set_init()(self.list_functions)

        # assigning get function method directly to MCP server instance
        self._mcp_server.get_function = self.get_function

    async def list_functions(self) -> list[MCPFunction]:
        """List all available functions."""
        functions = self._function_manager.list_functions()
        return [
            MCPFunction(
                name=info.name,
                title=info.title,
                description=info.description,
                inputSchema=info.parameters,
                outputSchema=info.output_schema
            )
            for info in functions
        ]

    async def call_function(self, name: str, arguments: dict[str, Any]) -> Sequence[ContentBlock] | dict[str, Any]:
        """Call a function by name with arguments."""
        return await self._function_manager.call_function(name, arguments, convert_result=True)

    async def get_function(self, name: str) -> MCPFunction | None:
        """Get function by name. """
        function = self._function_manager.get_function(name)

        if function:
            return MCPFunction(
                name=function.name,
                title=function.title,
                description=function.description,
                inputSchema=function.parameters,
                outputSchema=function.output_schema
            )
        return None

    def add_function(
        self,
        fn: AnyFunction,
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        structured_output: bool | None = None,
    ) -> None:
        """Add a function to the server.

        The function function can optionally request a Context object by adding a parameter
        with the Context type annotation. See the @function decorator for examples.

        Args:
            fn: The function to register as a function
            name: Optional name for the function (defaults to function name)
            title: Optional human-readable title for the function
            description: Optional description of what the function does

            structured_output: Controls whether the function's output is structured or unstructured
                - If None, auto-detects based on the function's return type annotation
                - If True, creates a structured function (return type annotation permitting)
                - If False, unconditionally creates an unstructured function
        """
        self._function_manager.add_function(
            fn,
            name=name,
            title=title,
            description=description,
            structured_output=structured_output
        )

    def remove_function(self, name: str) -> None:
        """Remove a function from the server by name.

        Args:
            name: The name of the function to remove

        Raises:
            FunctionError: If the function does not exist
        """
        self._function_manager.remove_function(name)

    def function(
        self,
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        structured_output: bool | None = None,
    ) -> Callable[[AnyFunction], AnyFunction]:
        """Decorator to register a function.

        Functions can optionally request a Context object by adding a parameter with the
        Context type annotation. The context provides access to MCP capabilities like
        logging, progress reporting, and resource access.

        Args:
            name: Optional name for the function (defaults to function name)
            title: Optional human-readable title for the function
            description: Optional description of what the function does
            structured_output: Controls whether the function's output is structured or unstructured
                - If None, auto-detects based on the function's return type annotation
                - If True, creates a structured function (return type annotation permitting)
                - If False, unconditionally creates an unstructured function

        Example:
            @server.function()
            def my_function(x: int) -> str:
                return str(x)

            @server.function()
            def function_with_context(x: int, ctx: Context) -> str:
                ctx.info(f"Processing {x}")
                return str(x)

            @server.function()
            async def async_function(x: int, context: Context) -> str:
                await context.report_progress(50, 100)
                return str(x)
        """
        # Check if user passed function directly instead of calling decorator
        if callable(name):
            raise TypeError(
                "The @function decorator was used incorrectly. Did you forget to call it? Use @function() instead of @function"
            )

        def decorator(fn: AnyFunction) -> AnyFunction:
            self.add_function(
                fn,
                name=name,
                title=title,
                description=description,
                structured_output=structured_output,
            )
            return fn

        return decorator
