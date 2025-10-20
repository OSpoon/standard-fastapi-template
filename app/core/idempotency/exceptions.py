"""
Default exceptions for idempotency module
"""

from __future__ import annotations


class IdempotencyException(Exception):
    """Base exception for idempotency errors"""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.headers = headers or {}


class IdempotencyKeyMissingError(IdempotencyException):
    """Raised when Idempotency-Key header is missing"""

    def __init__(self) -> None:
        super().__init__(
            message="Idempotency-Key header is required",
            status_code=400,
        )


class IdempotencySignatureMismatchError(IdempotencyException):
    """Raised when request signature doesn't match for the same idempotency key"""

    def __init__(self, headers: dict[str, str] | None = None) -> None:
        super().__init__(
            message="Request signature mismatch for the same Idempotency-Key",
            status_code=409,
            headers=headers,
        )


class IdempotencyInProgressError(IdempotencyException):
    """Raised when a request with the same idempotency key is being processed"""

    def __init__(self, retry_after: int, headers: dict[str, str] | None = None) -> None:
        _headers = headers or {}
        _headers["Retry-After"] = str(retry_after)
        super().__init__(
            message="A request with the same Idempotency-Key is currently being processed",
            status_code=409,
            headers=_headers,
        )
