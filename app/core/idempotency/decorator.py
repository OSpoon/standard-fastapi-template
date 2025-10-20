from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from fastapi import Request, Response

from app.core.idempotency.backends.base import BaseIdempotencyBackend
from app.core.idempotency.callbacks import raise_key_missing_error_async
from app.core.idempotency.handlers import (
    execute_and_store,
    handle_existing_record,
    wait_and_return_result,
)
from app.core.idempotency.utils import build_request_signature, extract_request_response

P = ParamSpec("P")
R = TypeVar("R")


def idempotent(
    *,
    backend: BaseIdempotencyBackend | None = None,
    header_name: str = "Idempotency-Key",
    wait_timeout_ms: int = 3000,
    lock_ttl_ms: int = 5000,
    record_ttl_ms: int = 86400000,  # 24小时 = 86400秒 = 86400000毫秒
    on_key_missing: Callable[[Request, Response], Awaitable[None]] | None = None,
    on_signature_mismatch: (
        Callable[[Request, Response, dict[str, str]], Awaitable[None]] | None
    ) = None,
    on_in_progress: (
        Callable[[Request, Response, int, dict[str, str]], Awaitable[None]] | None
    ) = None,
) -> Callable[[Callable[P, Any]], Callable[P, Awaitable[Any]]]:
    """
    幂等性装饰器，确保相同请求不会被重复处理

    Args:
        backend: 幂等性后端存储实例（必需）
        header_name: 幂等性 key 的请求头名称
        wait_timeout_ms: 等待其他请求完成的超时时间（毫秒）
        lock_ttl_ms: 分布式锁的 TTL（毫秒）
        record_ttl_ms: 幂等性记录的 TTL（毫秒）
        on_key_missing: 缺少幂等性 key 时的回调
        on_signature_mismatch: 请求签名不匹配时的回调
        on_in_progress: 请求正在处理中时的回调
    """
    header = header_name.lower()

    def decorator(func: Callable[P, Any]) -> Callable[P, Awaitable[Any]]:
        is_coro = inspect.iscoroutinefunction(func)

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            request, response_obj = extract_request_response(args, kwargs)

            idem_key = request.headers.get(header)
            if not idem_key:
                await raise_key_missing_error_async(
                    request, response_obj or Response(), on_key_missing
                )

            assert idem_key is not None  # noqa: S101

            idempotency_headers: dict[str, str] = {"Idempotency-Key": idem_key}

            if backend is None:
                raise RuntimeError(
                    "Idempotency backend not configured. Please pass 'backend' to @idempotent(...)."
                )

            # 构建请求签名
            signature = await build_request_signature(request)

            # 步骤 1: 检查已存在的记录
            record = await backend.get_record(idem_key)
            if record:
                result = await handle_existing_record(
                    record,
                    signature,
                    idem_key,
                    request,
                    response_obj,
                    idempotency_headers,
                    backend,
                    wait_timeout_ms,
                    on_signature_mismatch,
                    on_in_progress,
                )
                if result is not None:
                    return result

            # 步骤 2: 获取锁以标记处理中
            locked = await backend.acquire_lock(idem_key, ttl_ms=lock_ttl_ms)
            if not locked:
                # 其他进程持有锁，等待完成
                return await wait_and_return_result(
                    backend,
                    idem_key,
                    signature,
                    wait_timeout_ms,
                    request,
                    response_obj,
                    idempotency_headers,
                    on_signature_mismatch,
                    on_in_progress,
                )

            # 步骤 3: 执行函数并存储结果
            try:
                return await execute_and_store(
                    func,
                    is_coro,
                    args,
                    kwargs,
                    backend,
                    idem_key,
                    signature,
                    record_ttl_ms,
                    response_obj,
                    idempotency_headers,
                )
            finally:
                await backend.release_lock(idem_key)

        return wrapper

    return decorator
