from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar, cast

from api_exception import APIException
from fastapi import Request, Response
from fastapi.encoders import jsonable_encoder

from app.core.config import settings
from app.core.idempotency.backends.redis_backend import RedisIdempotencyBackend
from app.core.idempotency.types import IdempotencyRecord, StoredResponse
from app.core.idempotency.utils import build_request_signature
from app.exceptions.sf_exceptions import SFExceptionCode

P = ParamSpec("P")
R = TypeVar("R")


def _extract_request_response(
    args: tuple[Any, ...], kwargs: dict[str, Any]
) -> tuple[Request, Response | None]:
    # 允许端点签名任意位置包含 request/response
    for a in list(args) + list(kwargs.values()):
        if isinstance(a, Request):
            req = a
            resp = (
                kwargs.get("response")
                if isinstance(kwargs.get("response"), Response)
                else None
            )
            if not resp:
                for b in list(args) + list(kwargs.values()):
                    if isinstance(b, Response):
                        resp = b
                        break
            return req, resp
    # 如果没得到 request，放弃（由路由层保证）
    raise RuntimeError("Request object not found in endpoint parameters")


def idempotent(
    *,
    header_name: str | None = None,
    wait_timeout_ms: int | None = None,
) -> Callable[[Callable[P, Any]], Callable[P, Awaitable[Any]]]:
    header = (header_name or settings.IDEMPOTENCY_KEY_HEADER).lower()
    wait_timeout_ms = wait_timeout_ms or settings.IDEMPOTENCY_WAIT_TIMEOUT_MS

    def decorator(func: Callable[P, Any]) -> Callable[P, Awaitable[Any]]:
        is_coro = inspect.iscoroutinefunction(func)

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            request, response_obj = _extract_request_response(args, kwargs)

            idem_key = request.headers.get(header)
            if not idem_key:
                raise APIException(
                    error_code=SFExceptionCode.IDEMPOTENCY_KEY_MISSING,
                    http_status_code=400,
                )

            # 响应头增强：预先准备
            idempotency_headers = {
                "Idempotency-Key": idem_key,
            }

            # Redis backend - prefer the already initialized redis from app.api.deps
            from app.api.deps import get_redis_client

            redis_client = await get_redis_client()
            backend = RedisIdempotencyBackend(
                redis_client, prefix=settings.IDEMPOTENCY_REDIS_PREFIX
            )

            # Build request signature
            signature = await build_request_signature(request)

            # Step 1: check existing record
            record = await backend.get_record(idem_key)
            if record:
                idempotency_headers["X-Idempotency-Signature"] = record.signature
                # if in progress, wait for completion up to timeout
                if record.in_progress:
                    try:
                        await asyncio.wait_for(
                            _wait_for_completion(backend, idem_key, signature),
                            timeout=wait_timeout_ms / 1000,
                        )
                    except asyncio.TimeoutError:
                        raise APIException(
                            error_code=SFExceptionCode.IDEMPOTENCY_IN_PROGRESS,
                            http_status_code=409,
                            headers={
                                "Retry-After": str(int(wait_timeout_ms / 1000)),
                                **idempotency_headers,
                                "X-Idempotency-Status": "wait-timeout",
                            },
                        )
                    # re-check and possibly replay
                    latest = await backend.get_record(idem_key)
                    if latest and latest.response is not None:
                        import json as _json

                        stored = latest.response
                        if response_obj is not None:
                            for k, v in stored.headers.items():
                                response_obj.headers[k] = v
                            response_obj.status_code = stored.status_code
                            response_obj.headers.update(idempotency_headers)
                            response_obj.headers["X-Idempotency-Status"] = "hit"
                        try:
                            return _json.loads(stored.body.decode("utf-8"))
                        except Exception:
                            return stored.body.decode("utf-8")
                # if response exists and not in progress, replay it
                if record.response is not None:
                    import json as _json

                    stored = record.response
                    if response_obj is not None:
                        for k, v in stored.headers.items():
                            response_obj.headers[k] = v
                        response_obj.status_code = stored.status_code
                        response_obj.headers.update(idempotency_headers)
                        response_obj.headers["X-Idempotency-Status"] = "hit"
                    try:
                        return _json.loads(stored.body.decode("utf-8"))
                    except Exception:
                        return stored.body.decode("utf-8")
                # 签名冲突检测
                if record.signature != signature:
                    raise APIException(
                        error_code=SFExceptionCode.IDEMPOTENCY_SIGNATURE_MISMATCH,
                        http_status_code=409,
                        headers={
                            **idempotency_headers,
                            "X-Idempotency-Status": "conflict",
                        },
                    )

            # Step 2: acquire lock to mark in-progress
            locked = await backend.acquire_lock(
                idem_key, ttl_ms=settings.IDEMPOTENCY_LOCK_TTL_MS
            )
            if not locked:
                # Some other process holds the lock; behave like in-progress
                try:
                    await asyncio.wait_for(
                        _wait_for_completion(backend, idem_key, signature),
                        timeout=wait_timeout_ms / 1000,
                    )
                except asyncio.TimeoutError:
                    raise APIException(
                        error_code=SFExceptionCode.IDEMPOTENCY_IN_PROGRESS,
                        http_status_code=409,
                        headers={
                            "Retry-After": str(int(wait_timeout_ms / 1000)),
                            **idempotency_headers,
                            "X-Idempotency-Status": "wait-timeout",
                        },
                    )
                latest = await backend.get_record(idem_key)
                if latest and latest.response is not None:
                    import json as _json

                    stored = latest.response
                    if response_obj is not None:
                        for k, v in stored.headers.items():
                            response_obj.headers[k] = v
                        response_obj.status_code = stored.status_code
                        response_obj.headers.update(idempotency_headers)
                        response_obj.headers["X-Idempotency-Status"] = "hit"
                    try:
                        return _json.loads(stored.body.decode("utf-8"))
                    except Exception:
                        return stored.body.decode("utf-8")

            try:
                # Write in-progress record
                await backend.set_record(
                    idem_key,
                    IdempotencyRecord(signature=signature, in_progress=True),
                    ttl_s=settings.IDEMPOTENCY_RECORD_TTL_S,
                )

                # Execute underlying function
                if is_coro:
                    result = await cast(Callable[P, Awaitable[Any]], func)(
                        *args, **kwargs
                    )
                else:
                    result = await asyncio.to_thread(func, *args, **kwargs)

                # If the endpoint uses Response directly, capture body from return value (bytes/str/dict)
                # In general, FastAPI will serialize result; here we try to store raw if possible
                body_bytes: bytes
                if isinstance(result, (bytes, bytearray)):
                    body_bytes = bytes(result)
                elif isinstance(result, str):
                    body_bytes = result.encode("utf-8")
                elif hasattr(result, "model_dump"):
                    import json as _json

                    body_bytes = _json.dumps(
                        jsonable_encoder(result, by_alias=True)
                    ).encode("utf-8")
                elif isinstance(result, (dict, list)):
                    import json as _json

                    body_bytes = _json.dumps(jsonable_encoder(result)).encode("utf-8")
                else:
                    # As a fallback, serialize via JSON
                    import json as _json

                    body_bytes = _json.dumps(jsonable_encoder(result)).encode("utf-8")

                status_code = (
                    response_obj.status_code if response_obj is not None else 200
                )
                headers = dict(response_obj.headers) if response_obj is not None else {}

                # 响应头增强：写入 signature 和状态
                headers.update(idempotency_headers)
                headers["X-Idempotency-Signature"] = signature
                headers["X-Idempotency-Status"] = "new"

                if response_obj is not None:
                    response_obj.headers.update(headers)

                stored = StoredResponse(
                    status_code=status_code, headers=headers, body=body_bytes
                )
                await backend.set_record(
                    idem_key,
                    IdempotencyRecord(
                        signature=signature, in_progress=False, response=stored
                    ),
                    ttl_s=settings.IDEMPOTENCY_RECORD_TTL_S,
                )
                return result
            finally:
                await backend.release_lock(idem_key)

        return wrapper

    return decorator


async def _wait_for_completion(
    backend: RedisIdempotencyBackend, key: str, signature: str
) -> None:
    # Polling approach with backoff; could be replaced by pubsub in future.
    delay = 0.05
    max_delay = 0.5
    while True:
        rec = await backend.get_record(key)
        if rec and rec.signature == signature and rec.response is not None:
            return
        await asyncio.sleep(delay)
        delay = min(max_delay, delay * 1.5)
