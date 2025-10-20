"""
Idempotency module - Portable idempotency implementation for FastAPI

This module provides a complete idempotency solution that can be easily
integrated into any FastAPI project.

Basic Usage:
    ```python
    import redis.asyncio as aioredis
    from app.core.idempotency import idempotent, RedisIdempotencyBackend

    redis_client = aioredis.Redis(host="localhost", port=6379, db=0)
    backend = RedisIdempotencyBackend(redis_client, prefix="idem:")

    @app.post("/items")
    @idempotent(backend=backend)
    async def create_item(request: Request, response: Response, data: ItemCreate):
        return {"id": 1, "name": data.name}
    ```

Advanced Usage with Custom Callbacks:
    ```python
    from app.core.idempotency.callbacks import (
        default_on_key_missing,
        default_on_signature_mismatch,
        default_on_in_progress,
    )

    # Custom callback example
    async def my_on_key_missing(request, response):
        raise MyCustomException("Idempotency key required")

    @idempotent(
        backend=backend,
        on_key_missing=my_on_key_missing,
        on_signature_mismatch=default_on_signature_mismatch,
        on_in_progress=default_on_in_progress,
    )
    ```

Module Structure:
    - decorator.py: Main @idempotent decorator
    - handlers.py: Record handling and waiting logic
    - serializers.py: Request/response serialization
    - utils.py: Request signature and helper functions
    - callbacks.py: Error handling and callback functions
    - backends/: Storage backend implementations
    - exceptions.py: Custom exception classes
    - types.py: Type definitions
"""

from app.core.idempotency.backends.redis_backend import RedisIdempotencyBackend
from app.core.idempotency.callbacks import (
    default_on_in_progress,
    default_on_key_missing,
    default_on_signature_mismatch,
    raise_in_progress_error_async,
    raise_key_missing_error_async,
    raise_signature_mismatch_error_async,
)
from app.core.idempotency.decorator import idempotent
from app.core.idempotency.exceptions import (
    IdempotencyException,
    IdempotencyInProgressError,
    IdempotencyKeyMissingError,
    IdempotencySignatureMismatchError,
)
from app.core.idempotency.handlers import (
    apply_cached_response,
    execute_and_store,
    handle_existing_record,
    handle_wait_timeout,
    wait_and_return_result,
    wait_for_completion,
)
from app.core.idempotency.serializers import (
    deserialize_stored_response,
    serialize_result,
)
from app.core.idempotency.utils import (
    build_request_signature,
    extract_request_response,
    get_request_body_bytes,
)

__all__ = [
    # Decorator
    "idempotent",
    # Backend
    "RedisIdempotencyBackend",
    # Default callbacks
    "default_on_key_missing",
    "default_on_signature_mismatch",
    "default_on_in_progress",
    # Error handling callbacks
    "raise_key_missing_error_async",
    "raise_signature_mismatch_error_async",
    "raise_in_progress_error_async",
    # Handlers
    "wait_for_completion",
    "apply_cached_response",
    "handle_existing_record",
    "wait_and_return_result",
    "handle_wait_timeout",
    "execute_and_store",
    # Serializers
    "serialize_result",
    "deserialize_stored_response",
    # Utils
    "build_request_signature",
    "extract_request_response",
    "get_request_body_bytes",
    # Exceptions
    "IdempotencyException",
    "IdempotencyKeyMissingError",
    "IdempotencySignatureMismatchError",
    "IdempotencyInProgressError",
]
