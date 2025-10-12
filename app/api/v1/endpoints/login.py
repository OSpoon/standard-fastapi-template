from datetime import timedelta
from typing import Annotated

from api_exception import (
    APIException,
    APIResponse,
    ResponseModel,
)
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, SessionDep
from app.core import security
from app.core.config import settings
from app.crud import user_crud
from app.exceptions.sf_exceptions import SFExceptionCode
from app.models import Message, NewPassword, Token, UserPublic
from app.utils import (
    generate_password_reset_token,
    generate_reset_password_email,
    send_email,
    verify_password_reset_token,
)

router = APIRouter()


@router.post(
    "/access-token",
    response_model=Token,
    responses=APIResponse.default(),  # type: ignore
)
def login_access_token(
    session: SessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = user_crud.authenticate(
        session=session, email=form_data.username, password=form_data.password
    )
    if not user:
        raise APIException(
            error_code=SFExceptionCode.INCORRECT_EMAIL_OR_PASSWORD,
            http_status_code=400,
        )
    elif not user.is_active:
        raise APIException(
            error_code=SFExceptionCode.USER_INACTIVE,
            http_status_code=400,
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
    )


@router.post(
    "/test-token",
    response_model=ResponseModel[UserPublic],
    responses=APIResponse.default(),  # type: ignore
)
def test_token(current_user: CurrentUser) -> ResponseModel[UserPublic]:
    """
    Test access token
    """
    return ResponseModel(data=UserPublic.model_validate(current_user))


@router.post(
    "/password-recovery/{email}",
    response_model=ResponseModel[Message],
    responses=APIResponse.default(),  # type: ignore
)
def recover_password(email: str, session: SessionDep) -> ResponseModel[Message]:
    """
    Password Recovery
    """
    user = user_crud.get_user_by_email(session=session, email=email)

    if not user:
        raise APIException(
            error_code=SFExceptionCode.USER_EMAIL_NOT_FOUND,
            http_status_code=404,
        )
    password_reset_token = generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token
    )
    send_email(
        email_to=user.email,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return ResponseModel(data=Message(message="Password recovery email sent"))


@router.post(
    "/reset-password/",
    response_model=ResponseModel[Message],
    responses=APIResponse.default(),  # type: ignore
)
def reset_password(session: SessionDep, body: NewPassword) -> ResponseModel[Message]:
    """
    Reset password
    """
    email = verify_password_reset_token(token=body.token)
    if not email:
        raise APIException(
            error_code=SFExceptionCode.INVALID_TOKEN,
            http_status_code=400,
        )
    user = user_crud.get_user_by_email(session=session, email=email)
    if not user:
        raise APIException(
            error_code=SFExceptionCode.USER_EMAIL_NOT_FOUND,
            http_status_code=404,
        )
    elif not user.is_active:
        raise APIException(
            error_code=SFExceptionCode.USER_INACTIVE,
            http_status_code=400,
        )
    user = user_crud.update_user_password(
        session=session, user=user, new_password=body.new_password
    )
    return ResponseModel(data=Message(message="Password updated successfully"))
