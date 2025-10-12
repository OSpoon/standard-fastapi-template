from collections.abc import Generator
from typing import Annotated

import jwt
from api_exception import APIException
from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.exceptions.sf_exceptions import SFExceptionCode
from app.models.common_model import TokenPayload
from app.models.user_model import User

# 注意：默认 OAuth2PasswordBearer 会在缺失 Authorization 头时直接抛出 HTTPException(401, "Not authenticated")
# 这会绕过我们统一的异常结构。通过设置 auto_error=False，让其在缺失时返回 None，由我们自行抛出 APIException。
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token",
    auto_error=False,
)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str | None, Depends(reusable_oauth2)]


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    # 缺失或空 token：统一返回 401 与自定义错误码
    if not token:
        raise APIException(
            error_code=SFExceptionCode.UNAUTHORIZED,
            http_status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        # 无效 token：根据预期返回 401 Unauthorized，而不是 403
        raise APIException(
            error_code=SFExceptionCode.UNAUTHORIZED,
            http_status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = session.get(User, token_data.sub)
    if not user:
        raise APIException(
            error_code=SFExceptionCode.USER_NOT_FOUND, http_status_code=404
        )
    if not user.is_active:
        raise APIException(
            error_code=SFExceptionCode.USER_INACTIVE, http_status_code=400
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if not current_user.is_superuser:
        raise APIException(
            error_code=SFExceptionCode.INSUFFICIENT_PRIVILEGES,
            http_status_code=403,
        )
    return current_user
