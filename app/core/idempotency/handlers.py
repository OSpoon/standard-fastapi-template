"""
幂等性记录处理逻辑
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response

from app.core.idempotency.backends.base import BaseIdempotencyBackend
from app.core.idempotency.callbacks import (
    raise_in_progress_error_async,
    raise_signature_mismatch_error_async,
)
from app.core.idempotency.serializers import deserialize_stored_response
from app.core.idempotency.types import IdempotencyRecord, StoredResponse


async def wait_for_completion(
    backend: BaseIdempotencyBackend, key: str, expected_signature: str
) -> IdempotencyRecord | None:
    """
    等待请求完成处理

    Args:
        backend: 后端存储
        key: 幂等性 key
        expected_signature: 期望的请求签名

    Returns:
        IdempotencyRecord | None: 如果签名匹配且有响应则返回记录,否则返回 None

    Raises:
        会在内部检测到签名不匹配时不返回记录
    """
    # Polling approach with backoff; could be replaced by pubsub in future.
    delay = 0.05
    max_delay = 0.5
    max_iterations = 200  # 防止无限循环(0.05s * 200 = 10s 最大)
    iterations = 0

    while iterations < max_iterations:
        rec = await backend.get_record(key)
        if rec:
            # 如果签名不匹配,立即返回 None(调用方需要处理签名冲突)
            if rec.signature != expected_signature:
                return None
            # 如果签名匹配且有响应,返回记录
            if rec.response is not None:
                return rec
        # 如果记录不存在(可能过期),也继续等待(锁可能还在)
        # 但要设置最大迭代次数防止无限等待
        await asyncio.sleep(delay)
        delay = min(max_delay, delay * 1.5)
        iterations += 1

    # 达到最大迭代次数,返回 None(让调用方处理超时)
    return None


def apply_cached_response(
    response_obj: Response | None,
    stored: StoredResponse,
    idempotency_headers: dict[str, str],
    status: str = "hit",
) -> Any:
    """应用缓存的响应到 response 对象并返回反序列化的 body"""
    if response_obj is not None:
        for k, v in stored.headers.items():
            response_obj.headers[k] = v
        response_obj.status_code = stored.status_code
        response_obj.headers.update(idempotency_headers)
        response_obj.headers["X-Idempotency-Status"] = status
    return deserialize_stored_response(stored)


async def handle_existing_record(
    record: IdempotencyRecord,
    signature: str,
    idem_key: str,
    request: Request,
    response_obj: Response | None,
    idempotency_headers: dict[str, str],
    backend: BaseIdempotencyBackend,
    wait_timeout_ms: int,
    local_on_signature_mismatch: Callable[
        [Request, Response, dict[str, str]], Awaitable[None]
    ]
    | None,
    local_on_in_progress: Callable[
        [Request, Response, int, dict[str, str]], Awaitable[None]
    ]
    | None,
) -> Any | None:
    """
    处理已存在的幂等性记录

    Returns:
        如果有缓存响应则返回结果,否则返回 None 继续处理
    """
    idempotency_headers["X-Idempotency-Signature"] = record.signature

    # 检查签名是否匹配
    if record.signature != signature:
        await raise_signature_mismatch_error_async(
            request,
            response_obj or Response(),
            headers={**idempotency_headers, "X-Idempotency-Status": "conflict"},
            override_cb=local_on_signature_mismatch,
        )

    # 如果正在处理中,等待完成
    if record.in_progress:
        return await wait_and_return_result(
            backend,
            idem_key,
            signature,
            wait_timeout_ms,
            request,
            response_obj,
            idempotency_headers,
            local_on_signature_mismatch,
            local_on_in_progress,
        )

    # 如果有缓存的响应,直接返回
    if record.response is not None:
        return apply_cached_response(response_obj, record.response, idempotency_headers)

    return None


async def wait_and_return_result(
    backend: BaseIdempotencyBackend,
    idem_key: str,
    signature: str,
    wait_timeout_ms: int,
    request: Request,
    response_obj: Response | None,
    idempotency_headers: dict[str, str],
    local_on_signature_mismatch: Callable[
        [Request, Response, dict[str, str]], Awaitable[None]
    ]
    | None,
    local_on_in_progress: Callable[
        [Request, Response, int, dict[str, str]], Awaitable[None]
    ]
    | None,
) -> Any:
    """等待处理完成并返回结果"""
    try:
        completed_record = await asyncio.wait_for(
            wait_for_completion(backend, idem_key, signature),
            timeout=wait_timeout_ms / 1000,
        )

        if completed_record is None:
            await handle_wait_timeout(
                backend,
                idem_key,
                signature,
                wait_timeout_ms,
                request,
                response_obj,
                idempotency_headers,
                local_on_signature_mismatch,
                local_on_in_progress,
            )

        assert completed_record is not None  # noqa: S101

        if completed_record.response is not None:
            return apply_cached_response(
                response_obj, completed_record.response, idempotency_headers
            )
        else:
            await raise_in_progress_error_async(
                request,
                response_obj or Response(),
                retry_after=int(wait_timeout_ms / 1000),
                headers={**idempotency_headers, "X-Idempotency-Status": "wait-timeout"},
            )
    except asyncio.TimeoutError:
        await handle_wait_timeout(
            backend,
            idem_key,
            signature,
            wait_timeout_ms,
            request,
            response_obj,
            idempotency_headers,
            local_on_signature_mismatch,
            local_on_in_progress,
        )


async def handle_wait_timeout(
    backend: BaseIdempotencyBackend,
    idem_key: str,
    signature: str,
    wait_timeout_ms: int,
    request: Request,
    response_obj: Response | None,
    idempotency_headers: dict[str, str],
    local_on_signature_mismatch: Callable[
        [Request, Response, dict[str, str]], Awaitable[None]
    ]
    | None,
    local_on_in_progress: Callable[
        [Request, Response, int, dict[str, str]], Awaitable[None]
    ]
    | None,
) -> Any:
    """处理等待超时情况,可能返回缓存结果或抛出异常"""
    latest = await backend.get_record(idem_key)
    if latest:
        if latest.signature != signature:
            await raise_signature_mismatch_error_async(
                request,
                response_obj or Response(),
                headers={**idempotency_headers, "X-Idempotency-Status": "conflict"},
                override_cb=local_on_signature_mismatch,
            )
        if latest.response is not None:
            return apply_cached_response(
                response_obj, latest.response, idempotency_headers
            )

    await raise_in_progress_error_async(
        request,
        response_obj or Response(),
        retry_after=int(wait_timeout_ms / 1000),
        headers={**idempotency_headers, "X-Idempotency-Status": "wait-timeout"},
        override_cb=local_on_in_progress,
    )


async def execute_and_store(
    func: Callable[..., Any],
    is_coro: bool,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    backend: BaseIdempotencyBackend,
    idem_key: str,
    signature: str,
    record_ttl_ms: int,
    response_obj: Response | None,
    idempotency_headers: dict[str, str],
) -> Any:
    """执行函数并存储结果"""
    from typing import cast

    from app.core.idempotency.serializers import serialize_result

    # 转换毫秒为秒(后端存储使用秒)
    record_ttl_s = record_ttl_ms // 1000

    # 写入处理中记录
    await backend.set_record(
        idem_key,
        IdempotencyRecord(signature=signature, in_progress=True),
        ttl_s=record_ttl_s,
    )

    # 执行底层函数
    if is_coro:
        result = await cast(Callable[..., Awaitable[Any]], func)(*args, **kwargs)
    else:
        result = await asyncio.to_thread(func, *args, **kwargs)

    # 序列化结果
    body_bytes = serialize_result(result)

    status_code = response_obj.status_code if response_obj is not None else 200
    headers = dict(response_obj.headers) if response_obj is not None else {}

    # 响应头增强
    headers.update(idempotency_headers)
    headers["X-Idempotency-Signature"] = signature
    headers["X-Idempotency-Status"] = "new"

    if response_obj is not None:
        response_obj.headers.update(headers)

    # 存储响应
    stored = StoredResponse(status_code=status_code, headers=headers, body=body_bytes)
    await backend.set_record(
        idem_key,
        IdempotencyRecord(signature=signature, in_progress=False, response=stored),
        ttl_s=record_ttl_s,
    )
    return result
