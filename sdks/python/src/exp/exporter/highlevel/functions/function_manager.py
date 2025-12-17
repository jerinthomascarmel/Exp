from __future__ import annotations as _annotations

from collections.abc import Callable
from typing import Any

from exp.exporter.highlevel.exceptions import FunctionError
from exp.exporter.highlevel.functions.base import FunctionT
from exp.exporter.highlevel.utilities.logging import get_logger


logger = get_logger(__name__)


class FunctionManager:
    """Manages FastMCP functions."""

    def __init__(
        self,
        warn_on_duplicate_functions: bool = True,
        *,
        functions: list[FunctionT] | None = None,
    ):
        self._functions: dict[str, FunctionT] = {}
        if functions is not None:
            for function in functions:
                if warn_on_duplicate_functions and function.name in self._functions:
                    logger.warning(f"Function already exists: {function.name}")
                self._functions[function.name] = function

        self.warn_on_duplicate_functions = warn_on_duplicate_functions

    def get_function(self, name: str) -> FunctionT | None:
        """Get function by name."""
        return self._functions.get(name)

    def list_functions(self) -> list[FunctionT]:
        """List all registered functions."""
        return list(self._functions.values())

    def add_function(
        self,
        fn: Callable[..., Any],
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        structured_output: bool | None = None,
    ) -> FunctionT:
        """Add a function to the server."""
        function = FunctionT.from_function(
            fn,
            name=name,
            title=title,
            description=description,
            structured_output=structured_output,
        )
        existing = self._functions.get(function.name)
        if existing:
            if self.warn_on_duplicate_functions:
                logger.warning(f"Function already exists: {function.name}")
            return existing
        self._functions[function.name] = function
        return function

    def remove_function(self, name: str) -> None:
        """Remove a function by name."""
        if name not in self._functions:
            raise FunctionError(f"Unknown function: {name}")
        del self._functions[name]

    async def call_function(
        self,
        name: str,
        arguments: dict[str, Any],
        convert_result: bool = False,
    ) -> Any:
        """Call a function by name with arguments."""
        function = self.get_function(name)
        if not function:
            raise FunctionError(f"Unknown function: {name}")

        return await function.run(arguments, convert_result=convert_result)
