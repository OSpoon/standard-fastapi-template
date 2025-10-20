"""
序列化和反序列化工具函数
"""

from __future__ import annotations

from typing import Any

from fastapi.encoders import jsonable_encoder

from app.core.idempotency.types import StoredResponse


def deserialize_stored_response(stored: StoredResponse) -> Any:
    """反序列化存储的响应体"""
    import json as _json

    try:
        return _json.loads(stored.body.decode("utf-8"))
    except Exception:
        return stored.body.decode("utf-8")


def serialize_result(result: Any) -> bytes:
    """序列化函数执行结果为 bytes"""
    if isinstance(result, (bytes, bytearray)):
        return bytes(result)
    elif isinstance(result, str):
        return result.encode("utf-8")

    import json as _json

    if hasattr(result, "model_dump"):
        return _json.dumps(jsonable_encoder(result, by_alias=True)).encode("utf-8")
    elif isinstance(result, (dict, list)):
        return _json.dumps(jsonable_encoder(result)).encode("utf-8")
    else:
        return _json.dumps(jsonable_encoder(result)).encode("utf-8")
