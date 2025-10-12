from sqlmodel import Session, create_engine, select

from app.core.config import settings
from app.crud import user_crud
from app.models.user_model import User, UserCreate

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


def init_db(session: Session) -> None:
    user = session.exec(select(User).where(User.email == settings.SUPERUSER)).first()
    if not user:
        user_in = UserCreate(
            email=settings.SUPERUSER,
            password=settings.SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        user = user_crud.create_user(session=session, user_create=user_in)
