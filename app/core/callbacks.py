"""
Custom idempotency callbacks for this project
"""

from api_exception import APIException
from fastapi import Request, Response

from app.exceptions.sf_exceptions import SFExceptionCode


async def on_idempotency_key_missing(
    request: Request,  # noqa: ARG001
    response: Response,  # noqa: ARG001
) -> None:
    """
    Callback when idempotency key is missing

    :param request: The request object
    :param response: The response object
    :raises APIException: With IDEMPOTENCY_KEY_MISSING error code
    """
    raise APIException(
        error_code=SFExceptionCode.IDEMPOTENCY_KEY_MISSING,
        http_status_code=400,
    )


async def on_idempotency_signature_mismatch(
    request: Request,  # noqa: ARG001
    response: Response,  # noqa: ARG001
    headers: dict[str, str],
) -> None:
    """
    Callback when request signature mismatches

    :param request: The request object
    :param response: The response object
    :param headers: Response headers to include
    :raises APIException: With IDEMPOTENCY_SIGNATURE_MISMATCH error code
    """
    raise APIException(
        error_code=SFExceptionCode.IDEMPOTENCY_SIGNATURE_MISMATCH,
        http_status_code=409,
        headers=headers,
    )


async def on_idempotency_in_progress(
    request: Request,  # noqa: ARG001
    response: Response,  # noqa: ARG001
    retry_after: int,
    headers: dict[str, str],
) -> None:
    """
    Callback when request is in progress

    :param request: The request object
    :param response: The response object
    :param retry_after: Retry after seconds
    :param headers: Response headers to include
    :raises APIException: With IDEMPOTENCY_IN_PROGRESS error code
    """
    _headers = {**headers, "Retry-After": str(retry_after)}
    raise APIException(
        error_code=SFExceptionCode.IDEMPOTENCY_IN_PROGRESS,
        http_status_code=409,
        headers=_headers,
    )
