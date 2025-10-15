from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict
from typing import Any

from app.core.idempotency.types import IdempotencyRecord, StoredResponse


class BaseIdempotencyBackend(ABC):
    @abstractmethod
    async def acquire_lock(
        self, key: str, ttl_ms: int
    ) -> bool:  # returns True if acquired
        raise NotImplementedError

    @abstractmethod
    async def release_lock(self, key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_record(self, key: str) -> IdempotencyRecord | None:
        raise NotImplementedError

    @abstractmethod
    async def set_record(self, key: str, record: IdempotencyRecord, ttl_s: int) -> None:
        raise NotImplementedError

    @staticmethod
    def serialize_response(resp: StoredResponse) -> str:
        return json.dumps(asdict(resp))

    @staticmethod
    def deserialize_response(data: str) -> StoredResponse:
        d = json.loads(data)
        return StoredResponse(
            status_code=int(d["status_code"]),
            headers=d["headers"],
            body=bytes(d["body"]),
        )

    @staticmethod
    def serialize_record(record: IdempotencyRecord) -> str:
        payload: dict[str, Any] = {
            "signature": record.signature,
            "in_progress": record.in_progress,
            "meta": record.meta or {},
            "response": None,
        }
        if record.response is not None:
            payload["response"] = {
                "status_code": record.response.status_code,
                "headers": dict(record.response.headers),
                "body": list(record.response.body),  # store bytes as list of ints
            }
        return json.dumps(payload, separators=(",", ":"))

    @staticmethod
    def deserialize_record(data: str) -> IdempotencyRecord:
        d = json.loads(data)
        resp = d.get("response")
        stored = None
        if resp is not None:
            # 兜底处理：某些情况下可能出现 status_code 为 None 或缺字段
            if isinstance(resp, str):
                # 兼容历史字符串存储
                resp = json.loads(resp)
            sc = resp.get("status_code", 200)
            if sc is None:
                sc = 200
            hdrs_raw = resp.get("headers") or {}
            try:
                hdrs = {str(k): str(v) for k, v in dict(hdrs_raw).items()}
            except Exception:
                hdrs = {}
            body_raw = resp.get("body") or []
            try:
                body_bytes = bytes(body_raw)
            except Exception:
                body_bytes = b""
            stored = StoredResponse(
                status_code=int(sc),
                headers=hdrs,
                body=body_bytes,
            )
        return IdempotencyRecord(
            signature=str(d["signature"]),
            response=stored,
            in_progress=bool(d.get("in_progress", False)),
            meta=d.get("meta"),
        )
