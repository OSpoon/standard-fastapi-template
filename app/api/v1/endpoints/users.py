import uuid

from api_exception import (
    APIException,
    ResponseModel,
)
from fastapi import APIRouter, Depends

from app.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.core.config import settings
from app.core.security import verify_password
from app.crud import user_crud
from app.exceptions.sf_exceptions import SFExceptionCode
from app.models import (
    Message,
    UpdatePassword,
    UserCreate,
    UserPublic,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
)
from app.utils import generate_new_account_email, send_email

router = APIRouter()


@router.get(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=ResponseModel[UsersPublic],
)
def read_users(
    session: SessionDep, skip: int = 0, limit: int = 100
) -> ResponseModel[UsersPublic]:
    """
    Retrieve users.
    """

    users, count = user_crud.get_users(session=session, skip=skip, limit=limit)

    return ResponseModel(data=UsersPublic(items=users, count=count))


@router.post(
    "/",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=ResponseModel[UserPublic],
)
def create_user(
    *, session: SessionDep, user_in: UserCreate
) -> ResponseModel[UserPublic]:
    """
    Create new user.
    """
    user = user_crud.create_user(session=session, user_create=user_in)
    if settings.emails_enabled and user_in.email:
        email_data = generate_new_account_email(
            email_to=user_in.email, username=user_in.email, password=user_in.password
        )
        send_email(
            email_to=user_in.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return ResponseModel(data=UserPublic.model_validate(user))


@router.patch("/me", response_model=ResponseModel[UserPublic])
def update_user_me(
    *, session: SessionDep, user_in: UserUpdateMe, current_user: CurrentUser
) -> ResponseModel[UserPublic]:
    """
    Update own user.
    """
    user = user_crud.update_user_me(
        session=session, current_user=current_user, user_in=user_in
    )
    return ResponseModel(data=UserPublic.model_validate(user))


@router.patch("/me/password", response_model=ResponseModel[Message])
def update_password_me(
    *, session: SessionDep, body: UpdatePassword, current_user: CurrentUser
) -> ResponseModel[Message]:
    """
    Update own password.
    """
    if not verify_password(body.current_password, current_user.hashed_password):
        raise APIException(
            error_code=SFExceptionCode.INVALID_CREDENTIALS,
            http_status_code=400,
        )
    if body.current_password == body.new_password:
        raise APIException(
            error_code=SFExceptionCode.NEW_PASSWORD_SAME_AS_CURRENT,
            http_status_code=400,
        )
    user_crud.update_user_password(
        session=session, user=current_user, new_password=body.new_password
    )
    return ResponseModel(message="Password updated successfully")


@router.get("/me", response_model=ResponseModel[UserPublic])
def read_user_me(current_user: CurrentUser) -> ResponseModel[UserPublic]:
    """
    Get current user.
    """
    return ResponseModel(data=UserPublic.model_validate(current_user))


@router.delete("/me", response_model=ResponseModel[Message])
def delete_user_me(
    session: SessionDep, current_user: CurrentUser
) -> ResponseModel[Message]:
    """
    Delete own user.
    """
    if current_user.is_superuser:
        raise APIException(
            error_code=SFExceptionCode.INSUFFICIENT_PRIVILEGES,
            http_status_code=403,
        )
    user_crud.delete_user_me(session=session, current_user=current_user)
    return ResponseModel(message="User deleted successfully")


@router.post("/register", response_model=ResponseModel[UserPublic])
def register_user(
    session: SessionDep, user_in: UserRegister
) -> ResponseModel[UserPublic]:
    """
    Create new user without the need to be logged in.
    """
    user = user_crud.create_user(
        session=session, user_create=UserCreate.model_validate(user_in)
    )
    return ResponseModel(data=UserPublic.model_validate(user))


@router.get("/{user_id}", response_model=ResponseModel[UserPublic])
def read_user_by_id(
    user_id: uuid.UUID, session: SessionDep, current_user: CurrentUser
) -> ResponseModel[UserPublic]:
    """
    Get a specific user by id.
    """
    user = user_crud.get_user_by_id(session=session, user_id=user_id)
    if not user:
        raise APIException(
            error_code=SFExceptionCode.USER_NOT_FOUND,
            http_status_code=404,
        )
    if user.id == current_user.id:
        return ResponseModel(data=UserPublic.model_validate(user))
    if not current_user.is_superuser:
        raise APIException(
            error_code=SFExceptionCode.INSUFFICIENT_PRIVILEGES,
            http_status_code=403,
        )
    return ResponseModel(data=UserPublic.model_validate(user))


@router.patch(
    "/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=ResponseModel[UserPublic],
)
def update_user(
    *,
    session: SessionDep,
    user_id: uuid.UUID,
    user_in: UserUpdate,
) -> ResponseModel[UserPublic]:
    """
    Update a user.
    """
    user = user_crud.update_user_by_id(
        session=session, user_id=user_id, user_in=user_in
    )
    return ResponseModel(data=UserPublic.model_validate(user))


@router.delete(
    "/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=ResponseModel[Message],
)
def delete_user(session: SessionDep, user_id: uuid.UUID) -> ResponseModel[Message]:
    """
    Delete a user.
    """
    user_crud.delete_user_by_id(session=session, user_id=user_id)
    return ResponseModel(message="User deleted successfully")
