"""Context injection utilities for Exporter."""

from __future__ import annotations


from collections.abc import Callable
from typing import Any


def inject_context(
    fn: Callable[..., Any],
    kwargs: dict[str, Any],
    context: Any | None,
    context_kwarg: str | None,
) -> dict[str, Any]:
    """Inject context into function kwargs if needed.

    Args:
        fn: The function that will be called
        kwargs: The current keyword arguments
        context: The context object to inject (if any)
        context_kwarg: The name of the parameter to inject into

    Returns:
        Updated kwargs with context injected if applicable
    """
    if context_kwarg is not None and context is not None:
        return {**kwargs, context_kwarg: context}
    return kwargs
