from collections.abc import AsyncGenerator
from typing import Annotated

import redis.asyncio as aioredis
from api_exception import APIException
from fastapi import Depends, Header, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.crud import apikey_crud
from app.db.session import SessionLocal
from app.exceptions.sf_exceptions import SFExceptionCode
from app.models.apikey_model import APIKey
from app.utils import is_api_key_valid


async def get_redis_client() -> Redis:
    redis = await aioredis.from_url(  # type: ignore
        f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
        max_connections=10,
        encoding="utf8",
        decode_responses=True,
    )
    return redis  # type: ignore[no-any-return]


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


AsyncSessionDep = Annotated[AsyncSession, Depends(get_db)]

# 为 OpenAPI/Swagger 提供 Bearer 安全方案，从而显示 Authorize 按钮
bearer_scheme = HTTPBearer(auto_error=False)


def get_api_key_from_header(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> str | None:
    """
    获取 API Key, 优先使用 Swagger/安全方案注入的 Bearer token
    """
    # 优先使用 Swagger/安全方案注入的 Bearer token
    if credentials and credentials.credentials:
        return credentials.credentials
    return None


async def get_current_api_key(
    session: AsyncSessionDep,
    api_key: str | None = Depends(get_api_key_from_header),
) -> APIKey:
    """
    验证 API Key 并返回 APIKey 对象（异步版本）
    """
    if not api_key:
        raise APIException(
            error_code=SFExceptionCode.UNAUTHORIZED,
            http_status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 根据 key 查找 API Key
    db_api_key = await apikey_crud.get_api_key_by_key(session=session, key=api_key)
    if not db_api_key:
        raise APIException(
            error_code=SFExceptionCode.INVALID_APIKEY,
            http_status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # 验证 API Key 是否有效
    if not is_api_key_valid(db_api_key):
        if not db_api_key.is_active:
            raise APIException(
                error_code=SFExceptionCode.APIKEY_INACTIVE,
                http_status_code=status.HTTP_401_UNAUTHORIZED,
            )
        else:  # 过期
            raise APIException(
                error_code=SFExceptionCode.APIKEY_EXPIRED,
                http_status_code=status.HTTP_401_UNAUTHORIZED,
            )

    # 更新最后使用时间
    await apikey_crud.update_last_used(session=session, api_key=db_api_key)

    return db_api_key


CurrentAPIKeyAsync = Annotated[APIKey, Depends(get_current_api_key)]


# 在文档/Swagger 中显示 Idempotency-Key 的头部输入框
def idempotency_key_header_for_docs(
    _idempotency_key: Annotated[
        str | None,
        Header(
            alias=settings.IDEMPOTENCY_KEY_HEADER,
            description="Client-supplied idempotency key used to prevent duplicate processing.",
        ),
    ] = None,
) -> None:
    # 该依赖仅用于在 OpenAPI 上展示头部输入框，真实校验由幂等性装饰器完成
    return None
