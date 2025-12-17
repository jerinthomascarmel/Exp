from __future__ import annotations as _annotations

import functools
import inspect
from collections.abc import Callable
from functools import cached_property
from typing import Any
from pydantic import BaseModel, Field
from exp.exporter.highlevel.exceptions import FunctionError
from exp.exporter.highlevel.utilities.func_metadata import FuncMetadata, func_metadata


class FunctionT(BaseModel):
    """Internal function registration info."""

    fn: Callable[..., Any] = Field(exclude=True)
    name: str = Field(description="Name of the function")
    title: str | None = Field(
        None, description="Human-readable title of the function")
    description: str = Field(
        description="Description of what the function does")
    parameters: dict[str, Any] = Field(
        description="JSON schema for function parameters")
    fn_metadata: FuncMetadata = Field(
        description="Metadata about the function including a pydantic model for function arguments"
    )
    is_async: bool = Field(description="Whether the function is async")

    @cached_property
    def output_schema(self) -> dict[str, Any] | None:
        return self.fn_metadata.output_schema

    @classmethod
    def from_function(
        cls,
        fn: Callable[..., Any],
        name: str | None = None,
        title: str | None = None,
        description: str | None = None,
        structured_output: bool | None = None,
    ) -> FunctionT:
        """Create a Function from a function."""
        func_name = name or fn.__name__

        if func_name == "<lambda>":
            raise ValueError("You must provide a name for lambda functions")

        func_doc = description or fn.__doc__ or ""
        is_async = _is_async_callable(fn)

        func_arg_metadata = func_metadata(
            fn,
            skip_names=[],
            structured_output=structured_output,
        )

        parameters = func_arg_metadata.arg_model.model_json_schema(
            by_alias=True)

        return cls(
            fn=fn,
            name=func_name,
            title=title,
            description=func_doc,
            parameters=parameters,
            fn_metadata=func_arg_metadata,
            is_async=is_async
        )

    async def run(
        self,
        arguments: dict[str, Any],
        convert_result: bool = False,
    ) -> Any:
        """Run the function with arguments."""
        try:
            result = await self.fn_metadata.call_fn_with_arg_validation(
                self.fn,
                self.is_async,
                arguments
            )

            if convert_result:
                result = self.fn_metadata.convert_result(result)

            return result
        except Exception as e:
            raise FunctionError(
                f"Error executing function {self.name}: {e}") from e


def _is_async_callable(obj: Any) -> bool:
    while isinstance(obj, functools.partial):  # pragma: no cover
        obj = obj.func

    return inspect.iscoroutinefunction(obj) or (
        callable(obj) and inspect.iscoroutinefunction(
            getattr(obj, "__call__", None))
    )
