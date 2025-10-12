import uuid
from typing import Any

from api_exception import APIException
from sqlmodel import Session, func, select

from app.core.security import get_password_hash, verify_password
from app.exceptions.sf_exceptions import SFExceptionCode
from app.models.user_model import (
    User,
    UserCreate,
    UserUpdate,
    UserUpdateMe,
)


def create_user(*, session: Session, user_create: UserCreate) -> User:
    existing_user = get_user_by_email(session=session, email=user_create.email)
    if existing_user:
        raise APIException(
            error_code=SFExceptionCode.EMAIL_ALREADY_EXISTS,
            http_status_code=409,
        )
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        return None
    if not verify_password(password, db_user.hashed_password):
        return None
    return db_user


def update_user_password(*, session: Session, user: User, new_password: str) -> User:
    hashed_password = get_password_hash(password=new_password)
    user.hashed_password = hashed_password
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_users(
    *, session: Session, skip: int = 0, limit: int = 100
) -> tuple[list[User], int]:
    count_statement = select(func.count()).select_from(User)
    count = session.exec(count_statement).one()
    statement = select(User).offset(skip).limit(limit)
    users = session.exec(statement).all()
    return list(users), count


def get_user_by_id(*, session: Session, user_id: uuid.UUID) -> User | None:
    return session.get(User, user_id)


def delete_user_by_id(*, session: Session, user_id: uuid.UUID) -> None:
    user = session.get(User, user_id)
    if not user:
        raise APIException(
            error_code=SFExceptionCode.USER_NOT_FOUND,
            http_status_code=404,
        )
    session.delete(user)
    session.commit()


def update_user_by_id(
    *, session: Session, user_id: uuid.UUID, user_in: UserUpdate
) -> User:
    db_user = session.get(User, user_id)
    if not db_user:
        raise APIException(
            error_code=SFExceptionCode.USER_NOT_FOUND,
            http_status_code=404,
        )

    if user_in.email and user_in.email != db_user.email:
        existing_user = session.exec(
            select(User).where(User.email == user_in.email)
        ).first()
        if existing_user:
            raise APIException(
                error_code=SFExceptionCode.EMAIL_ALREADY_EXISTS,
                http_status_code=409,
            )

    user_data = user_in.model_dump(exclude_unset=True)
    if user_in.password:
        user_data["hashed_password"] = get_password_hash(user_in.password)
    else:
        user_data.pop("password", None)

    db_user.sqlmodel_update(user_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def update_user_me(
    *, session: Session, current_user: User, user_in: UserUpdateMe
) -> User:
    if user_in.email and user_in.email != current_user.email:
        existing_user = session.exec(
            select(User).where(User.email == user_in.email)
        ).first()
        if existing_user:
            raise APIException(
                error_code=SFExceptionCode.EMAIL_ALREADY_EXISTS,
                http_status_code=409,
            )

    user_data = user_in.model_dump(exclude_unset=True)
    current_user.sqlmodel_update(user_data)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


def delete_user_me(*, session: Session, current_user: User) -> None:
    delete_user_by_id(session=session, user_id=current_user.id)
