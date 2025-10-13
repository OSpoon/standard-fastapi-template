"""
自定义异常处理器
"""

from api_exception import APIException
from fastapi import HTTPException

from app.exceptions.sf_exceptions import SFExceptionCode


async def http_exception_handler(_, exc: HTTPException):  # type: ignore
    """
    HTTP异常处理器，拦截fastapi-limiter的429响应并转换为标准APIException格式
    """
    # 拦截fastapi-limiter的429响应，转换为标准APIException格式
    if exc.status_code == 429:
        raise APIException(
            error_code=SFExceptionCode.APIKEY_RATE_LIMIT_EXCEEDED,
            http_status_code=429,
        )
    # 其他HTTPException继续抛出，交给默认处理器
    raise exc
