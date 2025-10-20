from __future__ import annotations

import asyncio
import time
from typing import Any

import redis.asyncio as aioredis

from app.core.idempotency.backends.base import BaseIdempotencyBackend
from app.core.idempotency.types import IdempotencyRecord


class RedisIdempotencyBackend(BaseIdempotencyBackend):
    def __init__(self, client: Any, prefix: str = "idem:") -> None:
        self.client = client
        self.prefix = prefix if prefix.endswith(":") else prefix + ":"

    def _k(self, suffix: str) -> str:
        return f"{self.prefix}{suffix}"

    # Lock key per idem key: lock:{idem_key}
    def _lock_key(self, k: str) -> str:
        return self._k(f"lock:{k}")

    def _rec_key(self, k: str) -> str:
        return self._k(f"rec:{k}")

    def _is_async(self) -> bool:
        # 优先用类型判断（redis.asyncio.Redis 实例）
        try:
            if aioredis is not None:
                AsyncRedis = aioredis.Redis
                if isinstance(self.client, AsyncRedis):
                    return True
        except Exception:
            pass
        # 回退：检测方法是否为协程函数
        get_attr = getattr(self.client, "get", None)
        set_attr = getattr(self.client, "set", None)
        return asyncio.iscoroutinefunction(get_attr) or asyncio.iscoroutinefunction(
            set_attr
        )

    async def acquire_lock(self, key: str, ttl_ms: int) -> bool:
        k = self._lock_key(key)
        if self._is_async():
            # SET NX PX
            res = await self.client.set(k, str(time.time()), px=ttl_ms, nx=True)
            return bool(res)
        else:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None,
                lambda: bool(self.client.set(k, str(time.time()), px=ttl_ms, nx=True)),
            )

    async def release_lock(self, key: str) -> None:
        k = self._lock_key(key)
        if self._is_async():
            await self.client.delete(k)
        else:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: self.client.delete(k))

    async def get_record(self, key: str) -> IdempotencyRecord | None:
        k = self._rec_key(key)
        if self._is_async():
            data = await self.client.get(k)
        else:
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(None, lambda: self.client.get(k))
            # 防守式处理：如果返回的是协程（误判客户端类型），则再 await 一次
            if asyncio.iscoroutine(data):
                data = await data
        if not data:
            return None
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        from app.core.idempotency.backends.base import BaseIdempotencyBackend

        return BaseIdempotencyBackend.deserialize_record(data)

    async def set_record(self, key: str, record: IdempotencyRecord, ttl_s: int) -> None:
        k = self._rec_key(key)
        from app.core.idempotency.backends.base import BaseIdempotencyBackend

        data = BaseIdempotencyBackend.serialize_record(record)
        if self._is_async():
            await self.client.set(k, data, ex=ttl_s)
        else:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: self.client.set(k, data, ex=ttl_s))
