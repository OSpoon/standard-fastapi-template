from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

from fastapi import Request


async def get_request_body_bytes(request: Request) -> bytes:
    # request.body() caches the body in Starlette and is safe to call once here
    return await request.body()


def _normalize_headers(headers: Iterable[tuple[str, str]]) -> dict[str, str]:
    # Lower-case header names; join multi-values with comma, keep insertion order stable
    normalized: dict[str, str] = {}
    for k, v in headers:
        lk = k.lower()
        # Skip hop-by-hop headers that shouldn't affect idempotency
        if lk in {"date", "user-agent", "connection", "keep-alive"}:
            continue
        normalized[lk] = v if lk not in normalized else ",".join([normalized[lk], v])
    return normalized


async def build_request_signature(
    request: Request,
    include_headers: Iterable[str] | None = None,
) -> str:
    # Canonical components
    method = request.method.upper()
    url = str(request.url)

    # Default header whitelist: content-type, content-md5, authorization
    include_headers = include_headers or [
        "content-type",
        "content-md5",
        "authorization",
    ]

    headers = _normalize_headers(request.headers.items())
    headers_part = {k: headers.get(k) for k in include_headers if k in headers}

    body = await get_request_body_bytes(request)

    payload = {
        "m": method,
        "u": url,
        "h": headers_part,
        "b": hashlib.sha256(body).hexdigest() if body else None,
    }
    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
