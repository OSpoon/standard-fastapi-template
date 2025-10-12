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

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise APIException(
            error_code=SFExceptionCode.INVALID_CREDENTIALS,
            http_status_code=status.HTTP_403_FORBIDDEN,
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
