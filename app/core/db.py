from sqlmodel import Session, create_engine

from app.core.config import settings

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


def init_db(session: Session) -> None:
    # 数据库初始化逻辑
    # 可以在这里添加初始的 API Key 或其他初始化数据
    pass
