from collections.abc import Callable
from typing import Annotated, Any, Concatenate

import annotated_types
from typing_extensions import Sentinel

__all__ = [
    "MISSING",
    "NonNegativeInt",
    "inherits_args0",
    "inherits_args1",
    "inherits_args2",
    "inherits_signature",
]

MISSING = Sentinel("MISSING")
"""Represents a missing value."""
type NonNegativeInt = Annotated[int, annotated_types.Ge(0)]
"""An integer that must be greater than or equal to zero."""


def inherits_signature[**P, R](target: Callable[P, R]):
    """Statically injects the target function's signature into the wrapper."""

    def decorator(wrapper: Callable[..., R]) -> Callable[P, R]:
        return wrapper

    return decorator


def inherits_args0[**P](target: Callable[P, Any]):
    """Statically injects the target function's signature (excluding the return type)
    into the wrapper.

    The wrapper must not have any extra args before `args`/`kwargs`.
    """

    def decorator[R](wrapper: Callable[..., R]) -> Callable[P, R]:
        return wrapper

    return decorator


def inherits_args1[**P](target: Callable[P, Any]):
    """Statically injects the target function's signature (excluding the return type)
    into the wrapper.

    The wrapper must have one extra arg before `args`/`kwargs` (e.g. `self`).
    """

    def decorator[A, R](
        wrapper: Callable[Concatenate[A, ...], R],
    ) -> Callable[Concatenate[A, P], R]:
        return wrapper

    return decorator


def inherits_args2[**P](target: Callable[P, Any]):
    """Statically injects the target function's signature (excluding the return type)
    into the wrapper.

    The wrapper must have two extra args before `args`/`kwargs`.
    """

    def decorator[A, B, R](
        wrapper: Callable[Concatenate[A, B, ...], R],
    ) -> Callable[Concatenate[A, B, P], R]:
        return wrapper

    return decorator
