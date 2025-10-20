"""
Default callbacks for idempotency error handling
"""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from app.core.idempotency.exceptions import (
    IdempotencyInProgressError,
    IdempotencyKeyMissingError,
    IdempotencySignatureMismatchError,
)


async def raise_key_missing_error_async(
    request: Request,
    response: Response,
    override_cb: Callable[[Request, Response], Awaitable[None]] | None = None,
) -> None:
    """Raise idempotency key missing error (async version) with optional override callback"""
    if override_cb is not None:
        await override_cb(request, response)
        return
    # Use default exception
    raise IdempotencyKeyMissingError()


async def raise_signature_mismatch_error_async(
    request: Request,
    response: Response,
    headers: dict[str, str],
    override_cb: (
        Callable[[Request, Response, dict[str, str]], Awaitable[None]] | None
    ) = None,
) -> None:
    """Raise signature mismatch error (async version) with optional override callback"""
    if override_cb is not None:
        await override_cb(request, response, headers)
        return
    # Use default exception
    raise IdempotencySignatureMismatchError(headers=headers)


async def raise_in_progress_error_async(
    request: Request,
    response: Response,
    retry_after: int,
    headers: dict[str, str],
    override_cb: (
        Callable[[Request, Response, int, dict[str, str]], Awaitable[None]] | None
    ) = None,
) -> None:
    """Raise in progress error (async version) with optional override callback"""
    if override_cb is not None:
        await override_cb(request, response, retry_after, headers)
        return
    # Use default exception
    raise IdempotencyInProgressError(retry_after=retry_after, headers=headers)


async def default_on_key_missing(
    request: Request,  # noqa: ARG001
    response: Response,  # noqa: ARG001
) -> None:
    """
    Default callback when idempotency key is missing

    :param request: The request object
    :param response: The response object
    :raises IdempotencyKeyMissingError: Always raises this error
    """
    raise IdempotencyKeyMissingError()


async def default_on_signature_mismatch(
    request: Request,  # noqa: ARG001
    response: Response,  # noqa: ARG001
    headers: dict[str, str],
) -> None:
    """
    Default callback when request signature mismatches

    :param request: The request object
    :param response: The response object
    :param headers: Response headers to include
    :raises IdempotencySignatureMismatchError: Always raises this error
    """
    raise IdempotencySignatureMismatchError(headers=headers)


async def default_on_in_progress(
    request: Request,  # noqa: ARG001
    response: Response,  # noqa: ARG001
    retry_after: int,
    headers: dict[str, str],
) -> None:
    """
    Default callback when request is in progress

    :param request: The request object
    :param response: The response object
    :param retry_after: Retry after seconds
    :param headers: Response headers to include
    :raises IdempotencyInProgressError: Always raises this error
    """
    raise IdempotencyInProgressError(retry_after=retry_after, headers=headers)
