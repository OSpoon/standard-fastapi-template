from collections.abc import Generator
from typing import Annotated

from api_exception import APIException
from fastapi import Depends, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.db import engine
from app.crud import apikey_crud
from app.exceptions.sf_exceptions import SFExceptionCode
from app.models.apikey_model import APIKey


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]

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


def get_current_api_key(
    session: SessionDep,
    api_key: str | None = Depends(get_api_key_from_header),
) -> APIKey:
    """
    验证 API Key 并返回 APIKey 对象
    """
    if not api_key:
        raise APIException(
            error_code=SFExceptionCode.UNAUTHORIZED,
            http_status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 根据 key 查找 API Key
    db_api_key = apikey_crud.get_api_key_by_key(session=session, key=api_key)
    if not db_api_key:
        raise APIException(
            error_code=SFExceptionCode.INVALID_APIKEY,
            http_status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # 验证 API Key 是否有效
    if not apikey_crud.is_api_key_valid(db_api_key):
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
    apikey_crud.update_last_used(session=session, api_key=db_api_key)

    return db_api_key


CurrentAPIKey = Annotated[APIKey, Depends(get_current_api_key)]
