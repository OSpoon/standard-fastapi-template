from math import ceil

from api_exception import APIException
from fastapi_limiter.depends import RateLimiter
from starlette.requests import Request
from starlette.responses import Response
from starlette.websockets import WebSocket

from app.exceptions.sf_exceptions import SFExceptionCode


# 默认限流回调
async def http_default_callback(
    request: Request,  # noqa: ARG001
    response: Response,  # noqa: ARG001
    pexpire: int,
) -> None:
    """
    default callback when too many requests
    :param request:
    :param response:
    :param pexpire: The remaining milliseconds
    :return:
    """
    expire = ceil(pexpire / 1000)
    raise APIException(
        error_code=SFExceptionCode.APIKEY_RATE_LIMIT_EXCEEDED,
        http_status_code=429,
        headers={"Retry-After": str(expire)},
    )


# 默认 WebSocket 限流回调
async def ws_default_callback(
    ws: WebSocket,  # noqa: ARG001
    pexpire: int,
) -> None:
    """
    default callback when too many requests
    :param ws:
    :param pexpire: The remaining milliseconds
    :return:
    """
    expire = ceil(pexpire / 1000)
    raise APIException(
        error_code=SFExceptionCode.APIKEY_RATE_LIMIT_EXCEEDED,
        http_status_code=429,
        headers={"Retry-After": str(expire)},
    )


# API Key 标识符函数，用于 FastAPILimiter
async def get_api_key_identifier(request: Request) -> str:
    """
    获取限流标识符
    """
    key = request.headers.get("authorization")
    if key is not None:
        return str(key)
    return request.client.host if request.client else "anonymous"


# 限流依赖：每个 API Key 每分钟最多 30 次请求
rate_limit_dependency = RateLimiter(
    times=30,
    seconds=60,
    identifier=get_api_key_identifier,
)
