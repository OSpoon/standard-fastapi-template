from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any


@dataclass
class StoredResponse:
    status_code: int
    headers: Mapping[str, str]
    body: bytes


@dataclass
class IdempotencyRecord:
    # A canonical signature of the request content (method, url, headers subset, body)
    signature: str
    # Optional stored response for replay
    response: StoredResponse | None = None
    # Processing flag to indicate in-flight request
    in_progress: bool = False
    # Opaque extra metadata
    meta: MutableMapping[str, Any] | None = None
